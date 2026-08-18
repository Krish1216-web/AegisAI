import os
import docx
from docx.document import Document as DocxDoc
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument, SectionData
from app.core.document_exceptions import InvalidFile

class DOCXExtractor(BaseDocumentExtractor):
    def _iter_block_items(self, parent):
        """
        Yields each paragraph and table in the document in order of appearance.
        """
        if isinstance(parent, DocxDoc):
            parent_elm = parent.element.body
        else:
            raise ValueError("Invalid parent type for block item iteration.")

        for child in parent_elm.iterchildren():
            if isinstance(child, CT_P):
                yield DocxParagraph(child, parent)
            elif isinstance(child, CT_Tbl):
                yield DocxTable(child, parent)

    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("DOCX file does not exist on disk.")

        try:
            doc = docx.Document(file_path)
            sections_data = []
            full_text_parts = []
            
            current_section_title = "Root"
            current_section_text = []

            for item in self._iter_block_items(doc):
                if isinstance(item, DocxParagraph):
                    text = item.text.strip()
                    if not text:
                        continue
                        
                    # Detect Heading styles
                    is_heading = item.style.name.startswith("Heading")
                    if is_heading:
                        # Flush previous section
                        if current_section_text:
                            sec_text = "\n".join(current_section_text)
                            sections_data.append(
                                SectionData(
                                    title=current_section_title,
                                    text=sec_text,
                                    metadata={"heading_style": item.style.name}
                                )
                            )
                            full_text_parts.append(f"\n# {current_section_title}\n{sec_text}")
                            
                        # Start new section
                        current_section_title = text
                        current_section_text = []
                    else:
                        current_section_text.append(text)
                        
                elif isinstance(item, DocxTable):
                    # Format table structure textually: Row-by-Row separated by Pipes
                    table_rows = []
                    for row in item.rows:
                        row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                        table_rows.append(" | ".join(row_cells))
                        
                    table_text = "\n".join(table_rows)
                    if table_text.strip():
                        current_section_text.append(f"\n[Table]\n{table_text}\n")

            # Flush final section
            if current_section_text or current_section_title != "Root":
                sec_text = "\n".join(current_section_text)
                sections_data.append(
                    SectionData(
                        title=current_section_title,
                        text=sec_text,
                        metadata={}
                    )
                )
                full_text_parts.append(f"\n# {current_section_title}\n{sec_text}")

            full_text = "\n".join(full_text_parts).strip()
            char_count = len(full_text)
            word_count = len(full_text.split())

            # Read document properties
            metadata = {}
            try:
                props = doc.core_properties
                metadata = {
                    "title": props.title or "",
                    "author": props.author or "",
                    "created": str(props.created) if props.created else "",
                    "modified": str(props.modified) if props.modified else ""
                }
            except Exception as e:
                logger.warning(f"Failed to read DOCX properties: {e}")

            return ExtractedDocument(
                text=full_text,
                pages=[],  # Word docs don't have natural page boundaries without layout engines
                sections=sections_data,
                metadata=metadata,
                page_count=1,  # Default to 1 logical document page
                character_count=char_count,
                word_count=word_count
            )

        except Exception as e:
            logger.error(f"Failed to parse DOCX document: {e}")
            raise InvalidFile(f"Failed to parse DOCX document: {str(e)}")
