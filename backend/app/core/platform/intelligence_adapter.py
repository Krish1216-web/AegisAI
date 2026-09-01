import uuid
from typing import Dict, Any
from app.core.platform.context import PlatformContext
from app.core.platform.adapter import BaseCapabilityExecutor
from app.core.platform.intelligence.models import ExecutionMode

class IntelligenceCapabilityAdapter(BaseCapabilityExecutor):
    """
    Phase 8.7 Intelligence Capability Adapter.
    Executes adaptive multi-capability plans via AdvancedIntelligenceService.
    """

    def execute(self, context: PlatformContext, input_data: Dict[str, Any]) -> Dict[str, Any]:
        query = input_data.get("query") or input_data.get("prompt") or "Synthesize platform intelligence"
        mode_str = str(input_data.get("mode", "adaptive")).lower()
        
        mode = ExecutionMode.ADAPTIVE
        if mode_str == "sequential":
            mode = ExecutionMode.SEQUENTIAL
        elif mode_str == "parallel":
            mode = ExecutionMode.PARALLEL

        # Retrieve DB session from context metadata or context.security_context
        # Note: If no db in context, instantiate execution with existing database engine or mock session
        from app.database.session import SessionLocal
        from app.core.platform.intelligence.engine import AdvancedIntelligenceService
        db = SessionLocal() if SessionLocal else None

        try:
            service = AdvancedIntelligenceService(db)
            result = service.execute_intelligent_query(
                query=query,
                context=context,
                mode=mode,
                input_data=input_data
            )
            return result
        finally:
            if db:
                db.close()
