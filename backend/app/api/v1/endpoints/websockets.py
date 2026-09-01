import uuid
import json
import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from sqlalchemy.orm import Session
from loguru import logger

from app.database.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.core.security import decode_token
from app.core.collaboration.realtime import (
    RealtimeConnectionManager,
    MAX_WS_MESSAGE_SIZE
)

router = APIRouter(tags=["Real-Time Collaboration"])

@router.websocket("/ws")
async def websocket_gateway(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication JWT Token"),
    db: Session = Depends(get_db)
):
    await websocket.accept()
    
    # 1. Authenticate JWT token
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        await websocket.send_text(json.dumps({
            "type": "error",
            "code": "AUTHENTICATION_FAILED",
            "message": "Invalid or expired authentication token"
        }))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id_str = payload.get("sub")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Resolve User and primary workspace from DB
    user = db.query(User).filter(User.id == user_id, User.is_active == True, User.is_deleted == False).first()
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    ws_member = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == user.id).first()
    if not ws_member:
        await websocket.send_text(json.dumps({
            "type": "error",
            "code": "WORKSPACE_MEMBERSHIP_REQUIRED",
            "message": "User does not belong to any workspace"
        }))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    workspace_id = ws_member.workspace_id
    username = user.username

    # 3. Register Connection
    manager = RealtimeConnectionManager.get_instance()
    connection_id = f"conn_{uuid.uuid4().hex[:12]}"
    try:
        conn_info = manager.register_connection(
            connection_id=connection_id,
            user_id=user_id,
            workspace_id=workspace_id,
            username=username,
            websocket=websocket
        )
    except ValueError as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "code": "CONNECTION_LIMIT_EXCEEDED",
            "message": str(e)
        }))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Broadcast initial presence joined
    manager.update_presence(connection_id, "online")

    # Send Welcome / Ack
    await websocket.send_text(json.dumps({
        "type": "connected",
        "connection_id": connection_id,
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "channel": f"workspace:{workspace_id}",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }))

    # 4. Message Loop
    try:
        while True:
            raw_data = await websocket.receive_text()
            if len(raw_data) > MAX_WS_MESSAGE_SIZE:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "MESSAGE_TOO_LARGE",
                    "message": f"Message exceeded limit of {MAX_WS_MESSAGE_SIZE} bytes"
                }))
                continue

            try:
                msg_data = json.loads(raw_data)
            except Exception:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Malformed JSON payload"
                }))
                continue

            msg_type = str(msg_data.get("type", "")).strip().lower()
            conn_info.last_seen = datetime.datetime.now(datetime.timezone.utc)

            if msg_type == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }))

            elif msg_type == "subscribe":
                channel = str(msg_data.get("channel", "")).strip()
                success, err = manager.authorize_and_subscribe(connection_id, channel, db)
                if success:
                    await websocket.send_text(json.dumps({
                        "type": "subscription_ack",
                        "channel": channel,
                        "status": "subscribed"
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "SUBSCRIPTION_DENIED",
                        "channel": channel,
                        "message": err or "Subscription authorization denied"
                    }))

            elif msg_type == "unsubscribe":
                channel = str(msg_data.get("channel", "")).strip()
                manager.unsubscribe_channel(connection_id, channel)
                await websocket.send_text(json.dumps({
                    "type": "subscription_ack",
                    "channel": channel,
                    "status": "unsubscribed"
                }))

            elif msg_type == "presence":
                p_status = str(msg_data.get("status", "online")).strip()
                manager.update_presence(connection_id, p_status)
                await websocket.send_text(json.dumps({
                    "type": "presence_ack",
                    "status": p_status
                }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "code": "UNKNOWN_MESSAGE_TYPE",
                    "message": f"Unsupported message type '{msg_type}'"
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.warning(f"WebSocket loop exception for {connection_id}: {e}")
    finally:
        manager.update_presence(connection_id, "offline")
        manager.unregister_connection(connection_id)
