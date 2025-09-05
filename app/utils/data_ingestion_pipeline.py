"""
PDF Data Ingestion Pipeline

This module handles the extraction and processing of content from PDF files for the RAG pipeline.
It extracts text, tables, and graphs from PDFs and converts them into normalized document chunks
suitable for embedding generation.

Features:
- Text extraction and intelligent chunking using LangChain
- Table extraction using Camelot (preferred) and pdfplumber (fallback)
- Graph/image OCR using Tesseract with fallback to placeholder text
- Year extraction from filenames for disaster data organization
- Normalization of all content types into text format for embedding

The pipeline processes:
1. Text content: Extracted and chunked with overlap for context preservation
2. Tables: Converted to normalized key-value format (e.g., "Year: 2019 | State: Kerala")
3. Graphs: OCR text extraction or placeholder descriptions
4. Metadata: Includes source file, page number, content type, and extracted year

Author: RAG Pipeline Team
Version: 0.1.0
"""

from dataclasses import dataclass
from typing import Any, Dict, List

import re
import os

import pdfplumber
from PIL import Image

try:
    import camelot
    CAMEL0T_AVAILABLE = True
except Exception:
    CAMEL0T_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Document:
    """
    Document chunk with content and metadata.
    
    Attributes:
        content (str): The text content of the document chunk
        metadata (Dict[str, Any]): Metadata including type, source, page, year
    """
    content: str
    metadata: Dict[str, Any]


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _chunk_text(text: str, source: str, page_number: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", ", ", " "]
    )
    chunks = splitter.split_text(text)
    return [
        Document(content=chunk, metadata={"type": "text", "source": source, "page": page_number})
        for chunk in chunks if chunk.strip()
    ]


def _year_from_path(path: str) -> int | None:
    basename = os.path.basename(path)
    m = re.search(r"(19|20)\d{2}", basename)
    return int(m.group(0)) if m else None


def _extract_tables_with_camelot(pdf_path: str) -> List[List[List[str]]]:
    if not CAMEL0T_AVAILABLE:
        return []
    tables: List[List[List[str]]] = []
    try:
        # First try lattice (ruled tables), then stream
        for flavor in ("lattice", "stream"):
            try:
                tb = camelot.read_pdf(pdf_path, pages="all", flavor=flavor)
                for t in tb:
                    tables.append(t.df.values.tolist())
            except Exception:
                continue
    except Exception:
        pass
    return tables


def _normalize_table_rows(rows: List[List[str]]) -> List[str]:
    normalized: List[str] = []
    headers: List[str] = []
    if rows:
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    for row in rows[1:] if headers else rows:
        fields = []
        for idx, cell in enumerate(row):
            key = headers[idx] if idx < len(headers) and headers[idx] else f"col_{idx}"
            value = str(cell).strip() if cell is not None else ""
            fields.append(f"{key}: {value}")
        normalized.append(" | ".join(fields))
    return normalized


def _group_rows_as_chunks(rows_text: List[str], source: str, page: int, group_size: int = 4) -> List[Document]:
    chunks: List[Document] = []
    for i in range(0, len(rows_text), group_size):
        group = rows_text[i:i + group_size]
        if not group:
            continue
        content = "\n".join(group)
        chunks.append(Document(content=content, metadata={"type": "table", "source": source, "page": page}))
    return chunks


def _ocr_image(pil_image: Image.Image) -> str:
    if not TESSERACT_AVAILABLE:
        return ""
    try:
        text = pytesseract.image_to_string(pil_image)
        return _clean_text(text)
    except Exception:
        return ""


def parse_pdf_to_documents(pdf_path: str) -> List[Document]:
    documents: List[Document] = []

    # Extract tables with camelot first (spans pages)
    camelot_tables = _extract_tables_with_camelot(pdf_path)
    file_year = _year_from_path(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            source = f"{pdf_path}#page={page_index}"

            # 1) Text extraction and chunking
            text = page.extract_text() or ""
            text = _clean_text(text)
            if text:
                text_docs = _chunk_text(text, source, page_index)
                # augment with year
                for d in text_docs:
                    d.metadata["year"] = file_year
                documents.extend(text_docs)

            # 2) Table extraction fallback or per-page normalization
            page_tables_text_chunks: List[Document] = []
            # Fallback using pdfplumber simple tables
            try:
                extracted_tables = page.extract_tables() or []
                for tbl in extracted_tables:
                    rows_text = _normalize_table_rows(tbl)
                    page_tables_text_chunks.extend(_group_rows_as_chunks(rows_text, source, page_index))
            except Exception:
                pass

            # add year to table chunks
            for d in page_tables_text_chunks:
                d.metadata["year"] = file_year
            documents.extend(page_tables_text_chunks)

            # 3) Graphs/images OCR
            try:
                if page.images:
                    page_image = page.to_image(resolution=200)
                    for img in page.images:
                        # pdf coordinate system: x0,y0,x1,y1
                        bbox = (img.get("x0", 0), img.get("top", 0), img.get("x1", 0), img.get("bottom", 0))
                        try:
                            cropped = page_image.original.crop(bbox)
                        except Exception:
                            cropped = page_image.original
                        ocr_text = _ocr_image(cropped)
                        if not ocr_text:
                            ocr_text = "Chart or graph detected; content relates to nearby text and labels."
                        documents.append(
                            Document(
                                content=ocr_text,
                                metadata={"type": "graph", "source": source, "page": page_index, "year": file_year},
                            )
                        )
            except Exception:
                pass

    # Add camelot tables normalized (if any)
    if camelot_tables:
        for idx, table in enumerate(camelot_tables, start=1):
            rows_text = _normalize_table_rows(table)
            tbl_docs = _group_rows_as_chunks(rows_text, source=f"{pdf_path}#camelot_table={idx}", page=0)
            for d in tbl_docs:
                d.metadata["year"] = file_year
            documents.extend(tbl_docs)

    return documents


