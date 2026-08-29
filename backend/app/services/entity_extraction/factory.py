from typing import Optional, Any
from app.services.entity_extraction.base import BaseEntityExtractor
from app.services.entity_extraction.rule_based import RuleBasedEntityExtractor
from app.services.entity_extraction.llm_extractor import LLMEntityExtractor
from app.services.entity_extraction.models import ExtractionConfig

class EntityExtractionFactory:
    """
    Factory resolving the active Entity Extractor instance.
    """
    @staticmethod
    def get_extractor(
        provider: str = "rule_based",
        ai_service: Optional[Any] = None,
        config: Optional[ExtractionConfig] = None
    ) -> BaseEntityExtractor:
        cfg = config or ExtractionConfig(provider=provider)

        if provider == "llm" and ai_service is not None:
            return LLMEntityExtractor(ai_service=ai_service, config=cfg)
        else:
            return RuleBasedEntityExtractor(config=cfg)
