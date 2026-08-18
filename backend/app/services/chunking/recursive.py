from typing import List, Optional, Tuple
from app.services.chunking.base import BaseChunker, BaseTokenizer, ChunkResult
from app.services.extractors.base import ExtractedDocument
from app.core.config import settings

class RecursiveCharacterChunker(BaseChunker):
    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.delimiters = ["\n\n", "\n", " ", ""]

    def _split_to_atomic_pieces(
        self, text: str, delimiters: List[str], max_tokens: int, tokenizer: BaseTokenizer, base_offset: int
    ) -> List[Tuple[str, int, int, int]]:
        """
        Recursively splits text using delimiters and returns list of (content, start_offset, end_offset, token_count).
        """
        token_count = tokenizer.count_tokens(text)
        if token_count <= max_tokens or not delimiters:
            return [(text, base_offset, base_offset + len(text), token_count)]

        delim = delimiters[0]
        next_delims = delimiters[1:]
        
        # Split using the current delimiter
        if delim == "":
            # Character fallback split
            pieces = [text[i] for i in range(len(text))]
        else:
            pieces = text.split(delim)

        atomic_pieces = []
        current_offset = base_offset

        for i, piece in enumerate(pieces):
            # Restore delimiter if it's not the last element
            piece_text = piece
            if delim != "" and i < len(pieces) - 1:
                piece_text += delim
                
            if not piece_text:
                continue

            piece_tokens = tokenizer.count_tokens(piece_text)
            
            if piece_tokens <= max_tokens:
                atomic_pieces.append((piece_text, current_offset, current_offset + len(piece_text), piece_tokens))
            else:
                # Recursively split the large piece
                sub_pieces = self._split_to_atomic_pieces(
                    piece_text, next_delims, max_tokens, tokenizer, current_offset
                )
                atomic_pieces.extend(sub_pieces)

            current_offset += len(piece_text)

        return atomic_pieces

    def _chunk_text_block(
        self, text: str, page_number: Optional[int], section_title: Optional[str], tokenizer: BaseTokenizer, global_index_start: int
    ) -> Tuple[List[ChunkResult], int]:
        """
        Chunks a contiguous block of text (like a page or section) and returns (list of ChunkResults, next global index).
        """
        if not text or not text.strip():
            return [], global_index_start

        # 1. Split block into atomic pieces of size <= chunk_size
        pieces = self._split_to_atomic_pieces(text, self.delimiters, self.chunk_size, tokenizer, 0)
        
        chunks = []
        current_pieces = []
        current_tokens = 0
        chunk_idx = global_index_start

        i = 0
        while i < len(pieces):
            piece_text, p_start, p_end, p_tokens = pieces[i]
            
            # If adding this piece exceeds chunk size and we already have pieces, finalize current chunk
            if current_tokens + p_tokens > self.chunk_size and current_pieces:
                # Build finalized chunk content
                chunk_content = "".join([p[0] for p in current_pieces])
                start_off = current_pieces[0][1]
                end_off = current_pieces[-1][2]
                
                chunks.append(
                    ChunkResult(
                        content=chunk_content,
                        chunk_index=chunk_idx,
                        page_number=page_number,
                        section_title=section_title,
                        start_offset=start_off,
                        end_offset=end_off,
                        token_count=current_tokens,
                        character_count=len(chunk_content)
                    )
                )
                chunk_idx += 1
                
                # Backtrack to handle overlap
                overlap_tokens = 0
                overlap_pieces = []
                # Backtrack from i - 1 to start of current chunk
                j = i - 1
                while j >= 0:
                    prev_piece = pieces[j]
                    if overlap_tokens + prev_piece[3] <= self.chunk_overlap:
                        overlap_pieces.insert(0, prev_piece)
                        overlap_tokens += prev_piece[3]
                        j -= 1
                    else:
                        break
                        
                current_pieces = overlap_pieces
                current_tokens = overlap_tokens
                # Continue loop without incrementing i so we process pieces[i] in the next iteration
                continue
            
            current_pieces.append((piece_text, p_start, p_end, p_tokens))
            current_tokens += p_tokens
            i += 1

        # Flush any remaining pieces
        if current_pieces:
            chunk_content = "".join([p[0] for p in current_pieces])
            start_off = current_pieces[0][1]
            end_off = current_pieces[-1][2]
            
            chunks.append(
                ChunkResult(
                    content=chunk_content,
                    chunk_index=chunk_idx,
                    page_number=page_number,
                    section_title=section_title,
                    start_offset=start_off,
                    end_offset=end_off,
                    token_count=current_tokens,
                    character_count=len(chunk_content)
                )
            )
            chunk_idx += 1

        return chunks, chunk_idx

    def chunk(self, doc: ExtractedDocument, tokenizer: BaseTokenizer) -> List[ChunkResult]:
        """
        Chunks the document, preserving page or section partitions where available.
        """
        all_chunks = []
        global_idx = 0

        # Case A: Document has extracted pages (like PDF, PPTX)
        if doc.pages:
            for page in doc.pages:
                page_chunks, next_idx = self._chunk_text_block(
                    page.text, page.page_number, None, tokenizer, global_idx
                )
                all_chunks.extend(page_chunks)
                global_idx = next_idx

        # Case B: Document has extracted sections (like DOCX, XLSX sheets)
        elif doc.sections:
            for section in doc.sections:
                sec_chunks, next_idx = self._chunk_text_block(
                    section.text, None, section.title, tokenizer, global_idx
                )
                all_chunks.extend(sec_chunks)
                global_idx = next_idx

        # Case C: Fallback flat text chunking
        else:
            flat_chunks, _ = self._chunk_text_block(doc.text, 1, None, tokenizer, global_idx)
            all_chunks.extend(flat_chunks)

        return all_chunks
