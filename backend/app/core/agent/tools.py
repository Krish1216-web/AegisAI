import abc
import time
import json
import hashlib
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger

from app.core.agent.exceptions import (
    ToolNotFound, ToolDisabled, ToolPermissionDenied, ToolArgumentValidationError,
    ToolExecutionError, ToolTimeout, ToolConfirmationRequired, ToolConfirmationInvalid,
    ToolAlreadyExecuted, ToolRegistryError
)

class ToolCategory(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    COMMUNICATION = "COMMUNICATION"
    CODE = "CODE"
    DATABASE = "DATABASE"
    FILE_SYSTEM = "FILE_SYSTEM"
    NETWORK = "NETWORK"
    SYSTEM = "SYSTEM"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ToolExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    DENIED = "DENIED"
    REQUIRES_CONFIRMATION = "REQUIRES_CONFIRMATION"
    VALIDATION_ERROR = "VALIDATION_ERROR"

class ToolDefinition(BaseModel):
    tool_id: str
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    required_permissions: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    requires_confirmation: bool = False
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionRequest(BaseModel):
    execution_id: str
    tool_id: str
    user_id: str
    workspace_id: str
    arguments: Dict[str, Any]
    requested_by_agent: str
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None
    timeout: float = 30.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionResult(BaseModel):
    execution_id: str
    tool_id: str
    status: ToolExecutionStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

def generate_confirmation_token(
    execution_id: str,
    tool_id: str,
    user_id: str,
    workspace_id: str,
    arguments: Dict[str, Any]
) -> str:
    """
    Cryptographically binds confirmation requests to execution boundaries.
    """
    arg_hash = hashlib.sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
    raw = f"{execution_id}:{tool_id}:{user_id}:{workspace_id}:{arg_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()

class BaseTool(abc.ABC):
    @abc.abstractmethod
    def definition(self) -> ToolDefinition:
        pass

    @abc.abstractmethod
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def health_check(self) -> bool:
        pass

class MockCalculatorTool(BaseTool):
    """
    Deterministic calculator mock tool avoiding arbitrary python code execution.
    """
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="calculator",
            name="Mock Calculator",
            description="Performs simple arithmetic without running unsafe eval strings.",
            category=ToolCategory.CODE,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            },
            risk_level=RiskLevel.LOW,
            requires_confirmation=False
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        op = arguments.get("operation")
        if op not in ["add", "subtract", "multiply", "divide"]:
            raise ToolArgumentValidationError(f"Unsupported operation: {op}")
        if "a" not in arguments or "b" not in arguments:
            raise ToolArgumentValidationError("Parameters 'a' and 'b' are required.")

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        op = arguments["operation"]
        a = arguments["a"]
        b = arguments["b"]
        
        if op == "add":
            res = a + b
        elif op == "subtract":
            res = a - b
        elif op == "multiply":
            res = a * b
        elif op == "divide":
            if b == 0:
                raise ToolExecutionError("Division by zero is undefined.")
            res = a / b
            
        return {"result": res}

    def health_check(self) -> bool:
        return True

class MockSearchTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="mock_search",
            name="Mock Search",
            description="Returns mock search listings.",
            category=ToolCategory.NETWORK,
            risk_level=RiskLevel.LOW
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        if "query" not in arguments:
            raise ToolArgumentValidationError("Search parameter 'query' is required.")

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"results": [f"Mock search result details for: {arguments['query']}"]}

    def health_check(self) -> bool:
        return True

class MockDocumentReaderTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="doc_reader",
            name="Mock Doc Reader",
            description="Reads workspace document contents.",
            category=ToolCategory.FILE_SYSTEM,
            risk_level=RiskLevel.MEDIUM
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        if "path" not in arguments:
            raise ToolArgumentValidationError("Path parameter is required.")

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"content": f"Mock file content payload for path: {arguments['path']}"}

    def health_check(self) -> bool:
        return True

class MockWeatherTool(BaseTool):
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="weather",
            name="Weather fetcher",
            description="High risk weather config modifier.",
            category=ToolCategory.SYSTEM,
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True
        )

    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        if "location" not in arguments:
            raise ToolArgumentValidationError("Location parameter is required.")

    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"temp": 72, "status": "Sunny"}

    def health_check(self) -> bool:
        return True

class ToolRegistry:
    """
    Central tool definitions repository.
    """
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        defn = tool.definition()
        if defn.tool_id in self.tools:
            raise ToolRegistryError(f"Tool with ID {defn.tool_id} is already registered.")
        if not defn.name:
            raise ToolRegistryError("Tool name cannot be empty.")
        self.tools[defn.tool_id] = tool

    def unregister(self, tool_id: str) -> None:
        if tool_id not in self.tools:
            raise ToolNotFound()
        del self.tools[tool_id]

    def get(self, tool_id: str) -> BaseTool:
        if tool_id not in self.tools:
            raise ToolNotFound()
        return self.tools[tool_id]

    def list_tools(self) -> List[ToolDefinition]:
        return [t.definition() for t in self.tools.values()]

    def check_availability(self, tool_id: str) -> bool:
        if tool_id not in self.tools:
            return False
        return self.tools[tool_id].definition().enabled
