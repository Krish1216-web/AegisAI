# Import all SQL models for metadata discovery by Alembic
from app.database.base_class import Base  # noqa

# Authentication
from app.models.user import User, Role, Permission, UserSession  # noqa

# Workspaces
from app.models.workspace import Organization, Workspace, WorkspaceMember  # noqa

# Conversations
from app.models.conversation import Conversation, Message, ConversationParticipant  # noqa

# AI Agents
from app.models.ai import Agent, AgentExecution, AgentLog, AIRequestLog, ProviderHealthStatus, Execution, ExecutionEvent, ExecutionCheckpoint, ToolExecution  # noqa

# Memory
from app.models.memory import Memory, MemoryEmbedding, MemoryCategory, AgentMemory  # noqa

# Workflows
from app.models.workflow import Workflow, WorkflowNode, WorkflowExecution, WorkflowLog  # noqa

# Documents
from app.models.document import Document, DocumentChunk, DocumentEmbedding  # noqa
from app.models.rag import RAGQuery  # noqa

# Knowledge Graph
from app.models.knowledge_graph import KnowledgeGraphNode, KnowledgeGraphEdge  # noqa

# Tasks
from app.models.task import Task, TaskExecution  # noqa

# Notifications
from app.models.notification import Notification, NotificationPreference  # noqa

# Model Context Protocol (MCP)
from app.models.mcp import MCPServer, MCPCapability  # noqa

# Analytics
from app.models.analytics import AnalyticsEvent, UsageMetrics, APIUsage  # noqa

# Audit Logs
from app.models.audit import AuditLog, ActivityLog  # noqa
