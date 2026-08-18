import os
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument, PageData
from app.core.document_exceptions import InvalidFile

class PDFExtractor(BaseDocumentExtractor):
    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("PDF file does not exist on disk.")

        try:
            reader = PdfReader(file_path)
            
            # Check password protection
            if reader.is_encrypted:
                raise InvalidFile("PDF is password-protected or encrypted.")
                
            page_count = len(reader.pages)
            pages_data = []
            full_text_list = []
            
            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    text = ""
                    
                pages_data.append(
                    PageData(
                        page_number=page_num,
                        text=text,
                        metadata={"page_index": idx}
                    )
                )
                full_text_list.append(text)
                
            full_text = "\n--- PAGE BREAK ---\n".join(full_text_list)
            char_count = len(full_text)
            word_count = len(full_text.split())
            
            # Extract basic PDF metadata
            pdf_metadata = {}
            if reader.metadata:
                for k, v in reader.metadata.items():
                    # Clean metadata key names (remove leading slashes)
                    key = k.lstrip("/")
                    pdf_metadata[key] = str(v)
                    
            if not full_text.strip():
                pdf_metadata["ocr_required"] = True
                logger.info(f"PDF contains no extractable text, flagging OCR required: {file_path}")
                
            return ExtractedDocument(
                text=full_text,
                pages=pages_data,
                sections=[],
                metadata=pdf_metadata,
                page_count=page_count,
                character_count=char_count,
                word_count=word_count
            )
            
        except (FileNotDecryptedError, PdfReadError) as e:
            logger.error(f"Failed to read PDF file: {e}")
            raise InvalidFile(f"Corrupt or encrypted PDF file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error parsing PDF: {e}")
            raise InvalidFile(f"Failed to parse PDF document: {str(e)}")
