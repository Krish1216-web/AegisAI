# AegisAI — Phase 9.7: Notifications & Real-Time Delivery

## 1. Executive Summary & Architecture
Phase 9.7 introduces the persistent notification layer and real-time delivery channels to AegisAI:
- **Notifications**: Server-generated in response to domain events (`MENTION`, `COMMENT_REPLY`, `PROJECT_MEMBER_ADDED`, `TEAM_MEMBER_ADDED`, `TEAM_INVITATION`).
- **Real-Time Delivery**: Leverages Phase 9.5 `RealtimeConnectionManager` and `PlatformEventDispatcher` to broadcast `NOTIFICATION_CREATED` and live unread counts directly over WebSockets.
- **Email Dispatch Provider**: Modular `EmailProvider` with mock support for deterministic testing and resilient background dispatch.
- **Per-User Preferences**: Configurable in-app and email delivery toggles per notification category.
- **Self-Notification Defense**: Prevents users from receiving notifications for their own actions.
- **Deduplication**: Suppresses duplicate alerts within a configurable sliding window (60s).

---

## 2. Domain Models & Database Migration
- **Table `notifications`**:
  - `id`: UUID (PK)
  - `workspace_id`: UUID (FK `workspaces.id`, ondelete='CASCADE', indexed)
  - `recipient_user_id`: UUID (FK `users.id`, ondelete='CASCADE', indexed)
  - `actor_user_id`: Optional[UUID] (FK `users.id`, ondelete='SET NULL', indexed)
  - `type`: VARCHAR(50) (indexed)
  - `title`: VARCHAR(255)
  - `body`: Text
  - `resource_type`: Optional[VARCHAR(50)]
  - `resource_id`: Optional[VARCHAR(255)]
  - `project_id`: Optional[UUID] (FK `projects.id`, ondelete='CASCADE', indexed)
  - `team_id`: Optional[UUID] (FK `teams.id`, ondelete='CASCADE', indexed)
  - `comment_id`: Optional[UUID] (FK `comments.id`, ondelete='CASCADE', indexed)
  - `mention_id`: Optional[UUID] (FK `comment_mentions.id`, ondelete='CASCADE', indexed)
  - `status`: VARCHAR(20) (`unread`, `read`, indexed, default="unread")
  - `read_at`: Optional[TIMESTAMPTZ]
  - `created_at`, `updated_at`
- **Table `notification_preferences`**:
  - `id`: UUID (PK)
  - `user_id`: UUID (FK `users.id`, ondelete='CASCADE', indexed)
  - `workspace_id`: Optional[UUID] (FK `workspaces.id`, ondelete='CASCADE', nullable=True)
  - `notification_type`: VARCHAR(50) (default="all")
  - `in_app_enabled`: bool (default=True)
  - `email_enabled`: bool (default=True)
  - `push_enabled`: bool (default=True)
  - `UNIQUE(user_id, workspace_id, notification_type)`
- **Migration**: `018_notifications_realtime.py` (down revision `017_comments_mentions`).

---

## 3. Event Mapping & Recipient Resolution
| Trigger Event | Notification Type | Recipient |
|---|---|---|
| `MENTION_CREATED` | `MENTION` | Mentioned user(s) |
| `COMMENT_REPLY` | `COMMENT_REPLY` | Parent comment author |
| `PROJECT_MEMBER_ADDED` | `PROJECT_MEMBER_ADDED` | Added project member |
| `PROJECT_MEMBER_REMOVED` | `PROJECT_MEMBER_REMOVED` | Removed project member |
| `TEAM_MEMBER_ADDED` | `TEAM_MEMBER_ADDED` | Added team member |
| `TEAM_MEMBER_REMOVED` | `TEAM_MEMBER_REMOVED` | Removed team member |
| `TEAM_INVITATION` | `TEAM_INVITATION` | Invited user email/user |

---

## 4. Email Infrastructure & Sanitization
- Implements `EmailProvider` with HTML and special character escaping (`html.escape`).
- Email failures do not block database persistence or in-app notification delivery.
- Credentials and SMTP configuration are managed through environment settings.

---

## 5. REST APIs
- `GET /api/v1/notifications`: Paginated list of notifications for the authenticated user.
- `GET /api/v1/notifications/unread-count`: Returns `{ "unread_count": N }`.
- `POST /api/v1/notifications/{id}/read`: Marks single notification as read.
- `POST /api/v1/notifications/read-all`: Marks all unread notifications as read.
- `GET /api/v1/notifications/preferences`: Retrieves user preference settings.
- `PUT /api/v1/notifications/preferences`: Updates user preference settings.

---

## 6. Frontend Notification Center
- **Page**: [`frontend/src/pages/user/UserNotifications.jsx`](file:///d:/CP/AegisAI/frontend/src/pages/user/UserNotifications.jsx)
  - Notification list with unread indicators and deep links.
  - Mark read and Mark all read actions.
  - Notification Preferences modal with In-App and Email toggles.
- **Navbar Bell**: [`frontend/src/App.jsx`](file:///d:/CP/AegisAI/frontend/src/App.jsx)
  - Dynamic navigation to Notification Center.

---

## 7. Deferred Features
- **Phase 9.8**: Collaboration Analytics & Engagement Dashboards.
- **Phase 9.9**: Final Security Hardening & Penetration Testing.
