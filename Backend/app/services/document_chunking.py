"""
Document text chunking service.
Cleans raw text and splits it into ordered chunks with configurable size and overlap.
"""
import re
from typing import Any, Dict, List


class ChunkingError(Exception):
    """Raised when chunking validation or processing fails."""
    pass


def clean_text(text: str) -> str:
    """
    Clean text before chunking without modifying original extracted text in DB:
    - Normalize line endings to \\n
    - Strip trailing spaces from each line
    - Reduce 3+ consecutive newlines to double newlines (preserving paragraphs)
    - Strip outer whitespace
    """
    if not text:
        return ""
    # Normalize line endings
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in normalized.split("\n")]
    joined = "\n".join(lines)
    # Collapse 3+ newlines to 2
    cleaned = re.sub(r"\n{3,}", "\n\n", joined)
    return cleaned.strip()


def _split_text_recursive(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: List[str] = None,
) -> List[str]:
    """
    Recursively split text using a sequence of separators.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    if len(text) <= chunk_size:
        return [text] if text else []

    # Find the highest-priority separator present in text
    chosen_sep = ""
    for sep in separators:
        if sep == "":
            chosen_sep = ""
            break
        if sep in text:
            chosen_sep = sep
            break

    if chosen_sep != "":
        splits = text.split(chosen_sep)
    else:
        # Fallback: character-level split if no separator matches
        splits = list(text)

    # Merge splits into chunks respecting chunk_size and chunk_overlap
    final_chunks: List[str] = []
    current_doc: List[str] = []
    current_len = 0

    for split in splits:
        piece = split if chosen_sep == "" else split + chosen_sep
        piece_len = len(piece)

        # If a single piece exceeds chunk_size, recursively split it with remaining separators
        if piece_len > chunk_size:
            # First flush current accumulated doc if any
            if current_doc:
                accumulated = "".join(current_doc).strip()
                if accumulated:
                    final_chunks.append(accumulated)
                current_doc = []
                current_len = 0

            next_seps = separators[separators.index(chosen_sep) + 1 :] if chosen_sep in separators else [""]
            sub_chunks = _split_text_recursive(piece, chunk_size, chunk_overlap, next_seps)
            final_chunks.extend(sub_chunks)
            continue

        if current_len + piece_len > chunk_size and current_doc:
            accumulated = "".join(current_doc).strip()
            if accumulated:
                final_chunks.append(accumulated)
            
            # Calculate overlap buffer
            overlap_buffer: List[str] = []
            overlap_len = 0
            for item in reversed(current_doc):
                if overlap_len + len(item) <= chunk_overlap:
                    overlap_buffer.insert(0, item)
                    overlap_len += len(item)
                else:
                    break
            
            current_doc = overlap_buffer + [piece]
            current_len = sum(len(x) for x in current_doc)
        else:
            current_doc.append(piece)
            current_len += piece_len

    if current_doc:
        accumulated = "".join(current_doc).strip()
        if accumulated and (not final_chunks or final_chunks[-1] != accumulated):
            final_chunks.append(accumulated)

    return final_chunks


def chunk_text(
    raw_text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Clean text and partition it into indexed chunk dictionaries.
    
    Returns:
        List of dicts: [
            {
                "chunk_index": 0,
                "text": "chunk text...",
                "start_char": 0,
                "end_char": 950
            }, ...
        ]
    """
    if chunk_size <= 0:
        raise ChunkingError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ChunkingError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ChunkingError("chunk_overlap must be strictly less than chunk_size")

    cleaned = clean_text(raw_text)
    if not cleaned:
        return []

    raw_chunks = _split_text_recursive(cleaned, chunk_size, chunk_overlap)
    
    # Format into structured list with sequential index and character offsets
    results: List[Dict[str, Any]] = []
    current_search_idx = 0

    for idx, chunk_str in enumerate(raw_chunks):
        chunk_str_clean = chunk_str.strip()
        if not chunk_str_clean:
            continue
            
        start_char = cleaned.find(chunk_str_clean, current_search_idx)
        if start_char == -1:
            start_char = cleaned.find(chunk_str_clean)
        if start_char == -1:
            start_char = 0
            end_char = len(chunk_str_clean)
        else:
            end_char = start_char + len(chunk_str_clean)
            # Advance search pointer moderately for next chunk, considering overlap
            current_search_idx = max(start_char + 1, end_char - chunk_overlap)

        results.append({
            "chunk_index": len(results),
            "text": chunk_str_clean,
            "start_char": start_char,
            "end_char": end_char,
        })

    return results
