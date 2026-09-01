type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface RealtimeEvent {
  event_id: string;
  event_type: string;
  channel: string;
  scope: string;
  workspace_id: string;
  actor_id?: string | null;
  timestamp: string;
  correlation_id: string;
  data: Record<string, any>;
}

export type EventHandler = (event: RealtimeEvent) => void;
export type StatusHandler = (status: ConnectionStatus) => void;

class RealtimeClient {
  private socket: WebSocket | null = null;
  private status: ConnectionStatus = 'disconnected';
  private subscriptions: Set<string> = new Set();
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private statusHandlers: Set<StatusHandler> = new Set();
  private reconnectAttempt = 0;
  private reconnectTimer: any = null;
  private heartbeatTimer: any = null;
  private processedEvents: Set<string> = new Set();
  private token: string | null = null;

  public connect(token: string) {
    this.token = token;
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setStatus('connecting');
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws?token=${encodeURIComponent(token)}`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.setStatus('connected');
        this.reconnectAttempt = 0;
        this.startHeartbeat();
        // Restore active subscriptions
        for (const channel of this.subscriptions) {
          this.sendRaw({ type: 'subscribe', channel });
        }
      };

      this.socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          this.handleMessage(msg);
        } catch (err) {
          console.warn('[RealtimeClient] Malformed message', err);
        }
      };

      this.socket.onclose = () => {
        this.stopHeartbeat();
        if (this.status !== 'disconnected') {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = (err) => {
        console.warn('[RealtimeClient] Socket error', err);
        if (this.socket) {
          this.socket.close();
        }
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.setStatus('disconnected');
    this.stopHeartbeat();
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  public subscribe(channel: string, handler?: EventHandler) {
    this.subscriptions.add(channel);
    if (handler) {
      if (!this.eventHandlers.has(channel)) {
        this.eventHandlers.set(channel, new Set());
      }
      this.eventHandlers.get(channel)!.add(handler);
    }
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.sendRaw({ type: 'subscribe', channel });
    }
  }

  public unsubscribe(channel: string, handler?: EventHandler) {
    if (handler) {
      const handlers = this.eventHandlers.get(channel);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.eventHandlers.delete(channel);
          this.subscriptions.delete(channel);
        }
      }
    } else {
      this.eventHandlers.delete(channel);
      this.subscriptions.delete(channel);
    }

    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.sendRaw({ type: 'unsubscribe', channel });
    }
  }

  public onStatusChange(handler: StatusHandler) {
    this.statusHandlers.add(handler);
    handler(this.status);
    return () => {
      this.statusHandlers.delete(handler);
    };
  }

  public getStatus(): ConnectionStatus {
    return this.status;
  }

  private setStatus(s: ConnectionStatus) {
    this.status = s;
    for (const h of this.statusHandlers) {
      try {
        h(s);
      } catch (err) {
        console.error('[RealtimeClient] Status handler error', err);
      }
    }
  }

  private handleMessage(msg: any) {
    if (msg.type === 'event' && msg.event_id) {
      // Deduplicate
      if (this.processedEvents.has(msg.event_id)) return;
      this.processedEvents.add(msg.event_id);
      if (this.processedEvents.size > 2000) {
        const arr = Array.from(this.processedEvents);
        this.processedEvents = new Set(arr.slice(1000));
      }

      const evt: RealtimeEvent = {
        event_id: msg.event_id,
        event_type: msg.event_type || 'COLLABORATION_EVENT',
        channel: msg.channel,
        scope: msg.scope,
        workspace_id: msg.workspace_id,
        actor_id: msg.actor_id,
        timestamp: msg.timestamp,
        correlation_id: msg.correlation_id,
        data: msg.data || {},
      };

      // Dispatch to channel handlers
      const channelHandlers = this.eventHandlers.get(evt.channel);
      if (channelHandlers) {
        for (const h of channelHandlers) {
          try {
            h(evt);
          } catch (e) {
            console.error('[RealtimeClient] Handler error', e);
          }
        }
      }

      // Also wildcard listeners
      const allHandlers = this.eventHandlers.get('*');
      if (allHandlers) {
        for (const h of allHandlers) {
          try {
            h(evt);
          } catch (e) {
            console.error('[RealtimeClient] Wildcard handler error', e);
          }
        }
      }
    }
  }

  private scheduleReconnect() {
    this.setStatus('reconnecting');
    this.reconnectAttempt++;
    const delay = Math.min(30000, Math.pow(2, this.reconnectAttempt - 1) * 1000);
    this.reconnectTimer = setTimeout(() => {
      if (this.token) {
        this.connect(this.token);
      }
    }, delay);
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.sendRaw({ type: 'ping' });
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private sendRaw(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }
}

export const realtimeClient = new RealtimeClient();
