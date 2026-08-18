from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class PageData(BaseModel):
    page_number: int
    text: str
    metadata: Optional[Dict[str, Any]] = None

class SectionData(BaseModel):
    title: str
    text: str
    metadata: Optional[Dict[str, Any]] = None

class ExtractedDocument(BaseModel):
    text: str
    pages: List[PageData] = []
    sections: List[SectionData] = []
    metadata: Dict[str, Any] = {}
    page_count: int = 0
    character_count: int = 0
    word_count: int = 0

class BaseDocumentExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> ExtractedDocument:
        """
        Extracts content from a file and returns an ExtractedDocument object.
        """
        pass
