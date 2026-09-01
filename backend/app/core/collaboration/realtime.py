import uuid
import datetime
import asyncio
import json
from typing import Dict, Set, Optional, Any, List, Tuple
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from loguru import logger

from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.team import Team, TeamMembership
from app.models.project import Project, ProjectMembership
from app.services.authorization import AuthorizationService
from app.core.platform.events import PlatformEventDispatcher, PlatformEvent, PlatformEventType
from app.schemas.realtime import RealtimeEventEnvelope, WSServerMessage

# Safe Bounded Settings
MAX_WS_CONNECTIONS_PER_USER = 10
MAX_WS_CONNECTIONS_PER_WORKSPACE = 200
MAX_WS_SUBSCRIPTIONS_PER_CONNECTION = 50
MAX_WS_MESSAGE_SIZE = 65536 # 64 KB
HEARTBEAT_TIMEOUT_SECONDS = 120

class ConnectionInfo:
    def __init__(
        self,
        connection_id: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        username: str,
        websocket: Optional[WebSocket] = None
    ):
        self.connection_id = connection_id
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.username = username
        self.websocket = websocket
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.datetime.now(datetime.timezone.utc)
        self.last_seen = datetime.datetime.now(datetime.timezone.utc)
        self.presence_status = "online"

class RealtimeConnectionManager:
    _instance: Optional["RealtimeConnectionManager"] = None

    def __init__(self):
        # connection_id -> ConnectionInfo
        self.active_connections: Dict[str, ConnectionInfo] = {}
        # channel -> Set[connection_id]
        self.channel_subscribers: Dict[str, Set[str]] = {}
        # workspace_id -> Set[connection_id]
        self.workspace_connections: Dict[uuid.UUID, Set[str]] = {}
        # user_id -> Set[connection_id]
        self.user_connections: Dict[uuid.UUID, Set[str]] = {}
        
        # Subscribe to PlatformEventDispatcher
        PlatformEventDispatcher.subscribe(
            PlatformEventType.COLLABORATION_EVENT,
            self._handle_platform_collaboration_event
        )

    @classmethod
    def get_instance(cls) -> "RealtimeConnectionManager":
        if cls._instance is None:
            cls._instance = RealtimeConnectionManager()
        return cls._instance

    def register_connection(
        self,
        connection_id: str,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        username: str,
        websocket: Optional[WebSocket] = None
    ) -> ConnectionInfo:
        # Check connection limits
        user_conns = self.user_connections.get(user_id, set())
        if len(user_conns) >= MAX_WS_CONNECTIONS_PER_USER:
            raise ValueError(f"Max connections per user ({MAX_WS_CONNECTIONS_PER_USER}) exceeded.")

        ws_conns = self.workspace_connections.get(workspace_id, set())
        if len(ws_conns) >= MAX_WS_CONNECTIONS_PER_WORKSPACE:
            raise ValueError(f"Max connections per workspace ({MAX_WS_CONNECTIONS_PER_WORKSPACE}) exceeded.")

        conn_info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            workspace_id=workspace_id,
            username=username,
            websocket=websocket
        )

        self.active_connections[connection_id] = conn_info
        
        if workspace_id not in self.workspace_connections:
            self.workspace_connections[workspace_id] = set()
        self.workspace_connections[workspace_id].add(connection_id)

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        # Auto-subscribe to personal workspace channel
        ws_channel = f"workspace:{workspace_id}"
        self.subscribe_channel(connection_id, ws_channel)

        return conn_info

    def unregister_connection(self, connection_id: str) -> Optional[ConnectionInfo]:
        conn_info = self.active_connections.pop(connection_id, None)
        if not conn_info:
            return None

        # Clean from channels
        for channel in list(conn_info.subscriptions):
            subscribers = self.channel_subscribers.get(channel)
            if subscribers and connection_id in subscribers:
                subscribers.remove(connection_id)
                if not subscribers:
                    self.channel_subscribers.pop(channel, None)

        # Clean from workspace connections
        ws_conns = self.workspace_connections.get(conn_info.workspace_id)
        if ws_conns and connection_id in ws_conns:
            ws_conns.remove(connection_id)
            if not ws_conns:
                self.workspace_connections.pop(conn_info.workspace_id, None)

        # Clean from user connections
        u_conns = self.user_connections.get(conn_info.user_id)
        if u_conns and connection_id in u_conns:
            u_conns.remove(connection_id)
            if not u_conns:
                self.user_connections.pop(conn_info.user_id, None)

        return conn_info

    def authorize_and_subscribe(
        self,
        connection_id: str,
        channel: str,
        db: Session
    ) -> Tuple[bool, Optional[str]]:
        conn = self.active_connections.get(connection_id)
        if not conn:
            return False, "Connection not found"

        if len(conn.subscriptions) >= MAX_WS_SUBSCRIPTIONS_PER_CONNECTION:
            return False, f"Maximum subscriptions ({MAX_WS_SUBSCRIPTIONS_PER_CONNECTION}) reached"

        if not channel or ":" not in channel:
            return False, "Invalid channel format. Expected scope:id"

        scope, res_id_str = channel.split(":", 1)
        scope = scope.strip().lower()

        try:
            res_id = uuid.UUID(res_id_str.strip())
        except ValueError:
            return False, "Invalid channel target UUID"

        auth_service = AuthorizationService(db)

        if scope == "workspace":
            if res_id != conn.workspace_id:
                return False, "Cross-workspace subscription denied"
            self.subscribe_channel(connection_id, channel)
            return True, None

        elif scope == "team":
            team = db.query(Team).filter(
                Team.id == res_id,
                Team.workspace_id == conn.workspace_id,
                Team.status == "active"
            ).first()
            if not team:
                return False, "Team not found in workspace"

            # Check if user is workspace owner/admin or team member
            ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == conn.workspace_id,
                WorkspaceMember.user_id == conn.user_id
            ).first()
            if ws_member and ws_member.role in ["owner", "admin"]:
                self.subscribe_channel(connection_id, channel)
                return True, None

            team_member = db.query(TeamMembership).filter(
                TeamMembership.team_id == team.id,
                TeamMembership.user_id == conn.user_id,
                TeamMembership.status == "active"
            ).first()
            if not team_member:
                return False, "User is not an active team member"

            self.subscribe_channel(connection_id, channel)
            return True, None

        elif scope == "project":
            project = db.query(Project).filter(
                Project.id == res_id,
                Project.workspace_id == conn.workspace_id,
                Project.status == "active"
            ).first()
            if not project:
                return False, "Project not found in workspace"

            # Check if user is workspace owner/admin or project member
            ws_member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == conn.workspace_id,
                WorkspaceMember.user_id == conn.user_id
            ).first()
            if ws_member and ws_member.role in ["owner", "admin"]:
                self.subscribe_channel(connection_id, channel)
                return True, None

            proj_member = db.query(ProjectMembership).filter(
                ProjectMembership.project_id == project.id,
                ProjectMembership.user_id == conn.user_id,
                ProjectMembership.status == "active"
            ).first()
            if not proj_member:
                return False, "User is not an active project member"

            self.subscribe_channel(connection_id, channel)
            return True, None

        return False, f"Unsupported channel scope '{scope}'"

    def subscribe_channel(self, connection_id: str, channel: str) -> None:
        conn = self.active_connections.get(connection_id)
        if conn:
            conn.subscriptions.add(channel)
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(connection_id)

    def unsubscribe_channel(self, connection_id: str, channel: str) -> None:
        conn = self.active_connections.get(connection_id)
        if conn and channel in conn.subscriptions:
            conn.subscriptions.remove(channel)
        subscribers = self.channel_subscribers.get(channel)
        if subscribers and connection_id in subscribers:
            subscribers.remove(connection_id)
            if not subscribers:
                self.channel_subscribers.pop(channel, None)

    def revoke_user_channel(self, workspace_id: uuid.UUID, user_id: uuid.UUID, channel: str) -> None:
        """
        Immediately revokes an active channel subscription for a specific user across all their connections.
        """
        user_conns = self.user_connections.get(user_id, set())
        for conn_id in list(user_conns):
            conn = self.active_connections.get(conn_id)
            if conn and conn.workspace_id == workspace_id:
                self.unsubscribe_channel(conn_id, channel)
                # Send server unsubscription notification if socket is alive
                if conn.websocket:
                    try:
                        asyncio.create_task(conn.websocket.send_text(json.dumps({
                            "type": "subscription_revoked",
                            "channel": channel,
                            "reason": "access_revoked"
                        })))
                    except Exception:
                        pass

    def update_presence(self, connection_id: str, status: str) -> Optional[Dict[str, Any]]:
        conn = self.active_connections.get(connection_id)
        if not conn:
            return None
        conn.presence_status = status
        conn.last_seen = datetime.datetime.now(datetime.timezone.utc)
        
        presence_payload = {
            "user_id": str(conn.user_id),
            "username": conn.username,
            "status": status,
            "workspace_id": str(conn.workspace_id),
            "timestamp": conn.last_seen.isoformat()
        }
        
        ws_channel = f"workspace:{conn.workspace_id}"
        self.broadcast_to_channel(
            channel=ws_channel,
            message={
                "type": "presence",
                "channel": ws_channel,
                "data": presence_payload
            },
            workspace_id=conn.workspace_id
        )
        return presence_payload

    def broadcast_to_channel(
        self,
        channel: str,
        message: Dict[str, Any],
        workspace_id: uuid.UUID
    ) -> int:
        """
        Broadcasts a message to all subscribers of a channel within the specific workspace.
        """
        subscribers = self.channel_subscribers.get(channel, set())
        sent_count = 0
        raw_text = json.dumps(message)

        for conn_id in list(subscribers):
            conn = self.active_connections.get(conn_id)
            if conn and conn.workspace_id == workspace_id and conn.websocket:
                try:
                    asyncio.create_task(conn.websocket.send_text(raw_text))
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Error sending message to {conn_id}: {e}")
        return sent_count

    def _handle_platform_collaboration_event(self, event: PlatformEvent) -> None:
        """
        PlatformEventDispatcher subscriber: automatically bridges COLLABORATION_EVENT to WebSocket channels.
        """
        try:
            workspace_id = event.workspace_id
            payload = event.payload or {}
            action = payload.get("action", "COLLABORATION_EVENT")
            
            project_id = payload.get("project_id")
            team_id = payload.get("team_id")
            
            envelope = RealtimeEventEnvelope(
                event_type=action,
                scope="project" if project_id else ("team" if team_id else "workspace"),
                workspace_id=workspace_id,
                channel=f"project:{project_id}" if project_id else (f"team:{team_id}" if team_id else f"workspace:{workspace_id}"),
                actor_id=event.user_id,
                correlation_id=event.correlation_id,
                payload=payload
            )

            server_msg = {
                "type": "event",
                "event_id": envelope.event_id,
                "event_type": envelope.event_type,
                "channel": envelope.channel,
                "scope": envelope.scope,
                "workspace_id": str(envelope.workspace_id),
                "actor_id": str(envelope.actor_id) if envelope.actor_id else None,
                "timestamp": envelope.timestamp.isoformat(),
                "correlation_id": envelope.correlation_id,
                "data": envelope.payload
            }

            # Broadcast to specific channel
            self.broadcast_to_channel(envelope.channel, server_msg, workspace_id)
            
            # If it's a project/team event, also broadcast summary to workspace channel for directory updates
            if envelope.channel != f"workspace:{workspace_id}":
                self.broadcast_to_channel(f"workspace:{workspace_id}", server_msg, workspace_id)
        except Exception as e:
            logger.warning(f"Failed to bridge platform collaboration event to real-time socket: {e}")
