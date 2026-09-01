class PlatformExecutionError(Exception):
    """Base exception for all Phase 8 platform execution errors."""
    def __init__(self, message: str, code: str = "PLATFORM_EXECUTION_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class CapabilityNotFound(PlatformExecutionError):
    def __init__(self, capability_id: str):
        super().__init__(
            message=f"Capability '{capability_id}' was not found in registry.",
            code="CAPABILITY_NOT_FOUND",
            status_code=404
        )

class CapabilityDisabled(PlatformExecutionError):
    def __init__(self, capability_id: str):
        super().__init__(
            message=f"Capability '{capability_id}' is currently disabled.",
            code="CAPABILITY_DISABLED",
            status_code=400
        )

class CapabilityPermissionDenied(PlatformExecutionError):
    def __init__(self, message: str = "Caller lacks required permissions for this capability."):
        super().__init__(
            message=message,
            code="CAPABILITY_PERMISSION_DENIED",
            status_code=403
        )

class TenantIsolationError(PlatformExecutionError):
    def __init__(self, message: str = "Cross-tenant access violation."):
        super().__init__(
            message=message,
            code="TENANT_ISOLATION_ERROR",
            status_code=403
        )

class InvalidExecutionInput(PlatformExecutionError):
    def __init__(self, message: str = "Invalid or malformed execution input."):
        super().__init__(
            message=message,
            code="INVALID_EXECUTION_INPUT",
            status_code=400
        )

class InvalidExecutionOutput(PlatformExecutionError):
    def __init__(self, message: str = "Capability output failed validation."):
        super().__init__(
            message=message,
            code="INVALID_EXECUTION_OUTPUT",
            status_code=502
        )

class ExecutionTimeout(PlatformExecutionError):
    def __init__(self, timeout_seconds: int):
        super().__init__(
            message=f"Execution exceeded configured timeout limit of {timeout_seconds}s.",
            code="EXECUTION_TIMEOUT",
            status_code=504
        )

class ExecutionCancelled(PlatformExecutionError):
    def __init__(self, reason: str = "Execution was cancelled by user."):
        super().__init__(
            message=reason,
            code="EXECUTION_CANCELLED",
            status_code=499
        )

class ExecutionConcurrencyLimit(PlatformExecutionError):
    def __init__(self, limit: int):
        super().__init__(
            message=f"Execution rejected: Workspace concurrency limit of {limit} active tasks reached.",
            code="CONCURRENCY_LIMIT_EXCEEDED",
            status_code=429
        )

class ExecutionStateError(PlatformExecutionError):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="EXECUTION_STATE_ERROR",
            status_code=409
        )
