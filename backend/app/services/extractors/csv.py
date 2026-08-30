import os
import csv
from loguru import logger

from app.services.extractors.base import BaseDocumentExtractor, ExtractedDocument
from app.core.document_exceptions import InvalidFile

MAX_CSV_ROWS = 2000

class CSVExtractor(BaseDocumentExtractor):
    def _detect_delimiter(self, sample_line: str) -> str:
        candidates = [",", ";", "\t", "|"]
        # Basic heuristic count
        counts = {c: sample_line.count(c) for c in candidates}
        best = max(counts, key=counts.get)
        if counts[best] > 0:
            return best
        return ","

    def extract(self, file_path: str) -> ExtractedDocument:
        if not os.path.exists(file_path):
            raise InvalidFile("CSV file does not exist on disk.")

        # Read first line to detect delimiter and encoding
        encodings = ["utf-8", "latin-1", "cp1252"]
        sample_line = ""
        used_encoding = "utf-8"
        
        try:
            with open(file_path, "rb") as f:
                head_bytes = f.readline()
                
            for enc in encodings:
                try:
                    sample_line = head_bytes.decode(enc)
                    used_encoding = enc
                    break
                except Exception:
                    continue
        except Exception as e:
            raise InvalidFile(f"Failed to read file: {e}")

        delimiter = self._detect_delimiter(sample_line)
        
        try:
            rows = []
            col_count = 0
            row_count = 0
            
            with open(file_path, "r", encoding=used_encoding, errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for r in reader:
                    row_count += 1
                    if row_count > MAX_CSV_ROWS:
                        logger.warning(f"CSV exceeded row limit {MAX_CSV_ROWS}, truncating.")
                        rows.append(["[Truncated: row limit reached]"])
                        break
                        
                    if not col_count:
                        col_count = len(r)
                        
                    # Format as pipe-separated string row representation
                    row_str = [cell.replace("\n", " ").strip() for cell in r]
                    rows.append(row_str)
                    
            # Build textual layout: first row as headers, subsequent rows as columns
            text_lines = []
            if rows:
                headers = rows[0]
                text_lines.append(f"Headers: {' | '.join(headers)}")
                for r in rows[1:]:
                    text_lines.append(" | ".join(r))
                    
            full_text = "\n".join(text_lines)
            char_count = len(full_text)
            word_count = len(full_text.split())
            
            return ExtractedDocument(
                text=full_text,
                pages=[],
                sections=[],
                metadata={
                    "delimiter": delimiter,
                    "encoding": used_encoding,
                    "column_count": col_count,
                    "row_count": row_count
                },
                page_count=1,
                character_count=char_count,
                word_count=word_count
            )

        except Exception as e:
            logger.error(f"Failed to parse CSV file: {e}")
            raise InvalidFile(f"Failed to parse CSV file: {str(e)}")
