#!/usr/bin/env python3
"""
Create a RAG knowledge base from any text file.

Usage:
    python create_rag_from_text.py don_quixote.txt
    python create_rag_from_text.py don_quixote.txt -o rag_don_quixote
    python create_rag_from_text.py notes.txt -o rag_notes --name "My Study Notes"

This script:
1. Creates a rag_<name>/ folder structure
2. Generates all necessary config and source files
3. Chunks the text and creates embeddings
4. Stores everything in LanceDB

The resulting folder can be copied to your anthropic_chat_cli.py location
and used with: python anthropic_chat_cli.py --rag rag_<name>
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path


def create_folder_structure(output_dir: str) -> None:
    """Create the RAG folder structure."""
    os.makedirs(os.path.join(output_dir, "src"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "databases"), exist_ok=True)
    print(f"Created folder structure: {output_dir}/")


def write_config_file(output_dir: str, table_name: str) -> None:
    """Write the rag_config.toml file."""
    config_content = f'''[embeddings]
# Device for computation: "cuda", "cpu", "mps" (Apple Silicon)
device = "cpu"

# Similarity function
metric = "cosine"

# Let LanceDB handle embeddings (required for hybrid search)
emb_manual = false

model_provider = "sentence-transformers"
# Pretrained model for semantic search
model_name = "multi-qa-MiniLM-L6-cos-v1"
n_dim_vec = 384

# Token limits (model trained on up to 250 word pieces)
n_token_max = 250

# Chunk settings
n_char_max = 1500  # Larger chunks for narrative content
overlap = 150

[knowledge_base]
uri = "databases/lancedb"
table_name = "{table_name}"

[retriever]
# Number of text chunks to retrieve after reranking
n_retrieve = 10
# Number of top sections to return
n_titles = 5
# Enrich first result with surrounding context
enrich_first = true
# Cross-encoder reranker
reranker.device = "cpu"
reranker.model_name = "cross-encoder/ms-marco-MiniLM-L-2-v2"
'''
    with open(os.path.join(output_dir, "rag_config.toml"), "w") as f:
        f.write(config_content)
    print("  Created rag_config.toml")


def write_init_file(output_dir: str) -> None:
    """Write the __init__.py file."""
    with open(os.path.join(output_dir, "src", "__init__.py"), "w") as f:
        f.write("# RAG package\n")
    print("  Created src/__init__.py")


def write_constants_file(output_dir: str) -> None:
    """Write the constants.py file."""
    constants_content = '''import os
import tomllib
from typing import Any

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Config file path
CONFIG_PATH = os.path.join(PROJECT_ROOT, "rag_config.toml")

# LanceDB URI (relative to project root)
LANCEDB_URI = os.path.join(PROJECT_ROOT, "databases", "lancedb")


def get_rag_config() -> dict[str, Any]:
    """Load and return the RAG configuration from TOML file."""
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)
'''
    with open(os.path.join(output_dir, "src", "constants.py"), "w") as f:
        f.write(constants_content)
    print("  Created src/constants.py")


def write_retrieval_file(output_dir: str) -> None:
    """Write the retrieval.py file."""
    retrieval_content = '''from typing import Any

import lancedb
import numpy as np
import pandas as pd
from lancedb.db import DBConnection
from lancedb.table import Table
from sentence_transformers import SentenceTransformer, CrossEncoder

from src.constants import LANCEDB_URI, get_rag_config

# Cache models at module level
_embedding_model = None
_reranker_model = None


def get_embedding_model():
    """Get or create the embedding model."""
    global _embedding_model
    if _embedding_model is None:
        config = get_rag_config()
        model_name = config["embeddings"]["model_name"]
        _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def get_reranker_model(model_name: str):
    """Get or create the reranker model."""
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = CrossEncoder(model_name)
    return _reranker_model


def connect_to_lancedb_table(uri: str, table_name: str) -> Table:
    """Connect to a LanceDB table."""
    db: DBConnection = lancedb.connect(uri=uri)
    return db.open_table(table_name)


def get_knowledge_base(table_name: str | None = None) -> Table:
    """Get the knowledge base table."""
    db: DBConnection = lancedb.connect(uri=LANCEDB_URI)
    _table_name: str = table_name or get_rag_config()["knowledge_base"]["table_name"]
    return db.open_table(_table_name)


def retrieve_context(
    k_base: Table,
    query_text: str,
    reranker: dict,
    n_retrieve: int = 10,
) -> list[dict]:
    """Retrieve most relevant text chunks using vector search and reranking."""
    embedding_model = get_embedding_model()
    query_vector = embedding_model.encode(query_text)

    n_candidates = min(n_retrieve * 3, 50)

    results = (
        k_base.search(query_vector)
        .limit(n_candidates)
        .to_list()
    )

    if not results:
        return []

    rr_model_name: str = reranker["model_name"]
    reranker_model = get_reranker_model(rr_model_name)

    pairs = [(query_text, r["text"]) for r in results]
    scores = reranker_model.predict(pairs)

    for r, score in zip(results, scores):
        r["_relevance_score"] = float(score)

    results.sort(key=lambda x: x["_relevance_score"], reverse=True)

    return results[:n_retrieve]


def group_chunks_by_section(resp: list[dict], n_sections: int = 5) -> list[dict]:
    """Group retrieved text chunks by section."""
    if not resp:
        return []

    return (
        pd.DataFrame(resp)
        .drop_duplicates(subset="hash_doc")
        .groupby("section")
        .agg(
            section_num=("section_num", "first"),
            n_docs=("n_docs", "first"),
            chunks=("text", list),
            rank_abs=("rank_abs", list),
            score_sum=("_relevance_score", "sum"),
            n_chunks=("text", "count"),
        )
        .reset_index()
        .sort_values(by="score_sum", ascending=False)
        .iloc[:n_sections]
        .to_dict("records")
    )


def format_context(resp: list[dict]) -> str:
    """Format the context into a readable string."""
    if not resp:
        return "No context found."

    output_lines: list[str] = []
    overlap: int = get_rag_config()["embeddings"]["overlap"]

    for i, row in enumerate(resp):
        section: str = row.get("section", "Unknown")
        output_lines.append(f"{i + 1}. {section}:")

        chunks: list[str] = row.get("chunks", [])
        rank_abs: list[int] = row.get("rank_abs", [])

        if not chunks:
            output_lines.append("\\t- No content available.")
        else:
            previous_rank: int = -1
            for r_current, chunk in zip(rank_abs, chunks):
                if r_current - previous_rank > 1:
                    output_lines.append(f"\\t- {chunk}")
                elif len(chunk) > overlap:
                    output_lines[-1] += chunk[overlap:]
                previous_rank = r_current

    return "\\n".join(output_lines)


def enrich_text_chunks(k_base: Table, chunks_of_section: dict[str, Any], window_size: int = 1) -> dict[str, Any]:
    """Fetch surrounding chunks for context."""
    original_ranks: list[int] = chunks_of_section["rank_abs"]
    section: str = chunks_of_section["section"]

    new_ranks: set[int] = set()
    for r in original_ranks:
        for step in range(1, window_size + 1):
            new_ranks.add(r - step)
            new_ranks.add(r + step)
    new_ranks.difference_update(original_ranks)

    if not new_ranks:
        return chunks_of_section

    new_ranks_str: str = ",".join(map(str, sorted(new_ranks)))
    query_text: str = f"section = \\'{section}\\' AND rank_abs IN ({new_ranks_str})"

    fields: list[str] = ["rank_abs", "text", "n_docs"]
    try:
        new_chunks: pd.DataFrame = k_base.search().where(query_text).to_pandas()[fields]
    except Exception:
        return chunks_of_section

    if new_chunks.empty:
        return chunks_of_section

    text_dict: dict[int, str] = dict(zip(original_ranks, chunks_of_section["chunks"]))
    text_dict.update({c["rank_abs"]: c["text"] for c in new_chunks.to_dict("records")})

    enriched: dict[str, Any] = chunks_of_section.copy()
    updated_ranks: list[int] = sorted(text_dict)
    enriched["rank_abs"] = updated_ranks
    enriched["chunks"] = [text_dict[r] for r in updated_ranks]
    enriched["enriched"] = True
    if "n_chunks" in enriched:
        enriched["n_chunks"] = len(updated_ranks)

    return enriched


def get_context(
    k_base: Table,
    query_text: str,
    n_titles: int = 5,
    n_retrieve: int = 10,
    enrich_first: bool = False,
    **kwargs
) -> str:
    """Retrieve and format context based on query."""
    cxt_raw: list[dict] = retrieve_context(
        k_base=k_base, query_text=query_text, n_retrieve=n_retrieve, **kwargs
    )

    cxt_grouped: list[dict] = group_chunks_by_section(cxt_raw, n_sections=n_titles)

    if enrich_first and cxt_grouped:
        cxt_grouped[0] = enrich_text_chunks(k_base=k_base, chunks_of_section=cxt_grouped[0])

    return format_context(cxt_grouped)
'''
    with open(os.path.join(output_dir, "src", "retrieval.py"), "w") as f:
        f.write(retrieval_content)
    print("  Created src/retrieval.py")


def write_requirements_file(output_dir: str) -> None:
    """Write the requirements.txt file."""
    requirements_content = '''# Core dependencies for RAG system
lancedb>=0.4.0
sentence-transformers>=2.2.0
pandas>=2.0.0
numpy>=1.24.0
tantivy
'''
    with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
        f.write(requirements_content)
    print("  Created requirements.txt")


def parse_sections(text: str, book_name: str) -> list[dict]:
    """
    Parse text into sections. Tries multiple strategies:
    1. Study guide format (Part 1, Chapter 1 Summary) - SuperSummary, SparkNotes, etc.
    2. Part + Chapter markers (Part 1, Chapter 1) - for books like Don Quixote
    3. Chapter markers (Chapter X, CHAPTER X)
    4. Part markers (Part X, PART X)
    5. Section markers (Section X, numbered sections like "1.", "I.")
    6. Page markers (PAGE X, === separators)
    7. Falls back to paragraph-based chunking
    """
    sections = []

    # Clean up common PDF artifacts
    text = re.sub(r'\d+ minute[s]? left in chapter \d+%', '', text)
    text = re.sub(r'PAGE \d+ - [^\n]+\n={10,}\n', '\n', text)
    text = re.sub(r'={10,}\n', '\n', text)
    text = re.sub(r'STUDY GUIDE:[^\n]+\n', '\n', text)

    # Strategy 0: Markdown headers (# or ## at start of line)
    # Matches: "# Title", "## Section Name", "### Subsection"
    md_header_pattern = r'^(#{1,3})\s+(.+)$'
    md_matches = list(re.finditer(md_header_pattern, text, re.MULTILINE))

    if len(md_matches) >= 3:
        print(f"  Detected markdown headers: {len(md_matches)} sections")

        # Add intro if exists before first header
        if md_matches[0].start() > 100:
            intro = text[:md_matches[0].start()].strip()
            if intro and len(intro) > 50:
                sections.append({
                    "section": "Introduction",
                    "section_num": 0,
                    "content": intro
                })

        for i, match in enumerate(md_matches):
            header_level = len(match.group(1))  # 1, 2, or 3
            section_name = match.group(2).strip()

            start = match.end()
            end = md_matches[i + 1].start() if i + 1 < len(md_matches) else len(text)
            content = text[start:end].strip()

            if content and len(content) > 30:
                sections.append({
                    "section": section_name,
                    "section_num": i + 1,
                    "content": content
                })

        if sections:
            return sections

    # Strategy 1: Study guide format "Part X, Chapter Y Summary" or "Part X, Prologue Summary"
    study_guide_pattern = r'(Part\s+(\d+),\s*(Prologue|Chapter\s+(\d+)|Chapters?\s+[\d\-]+))\s*(Summary|Analysis)?'
    study_matches = list(re.finditer(study_guide_pattern, text, re.IGNORECASE))

    if len(study_matches) >= 5:
        print(f"  Detected study guide format: {len(study_matches)} sections")

        # Add intro/overview if exists before first match
        if study_matches[0].start() > 100:
            intro = text[:study_matches[0].start()].strip()
            if intro and len(intro) > 50:
                sections.append({
                    "section": "Overview",
                    "section_num": 0,
                    "content": intro
                })

        for i, match in enumerate(study_matches):
            section_name = match.group(1).strip()
            suffix = match.group(5) or ""
            if suffix:
                section_name += f" {suffix}"

            start = match.end()
            end = study_matches[i + 1].start() if i + 1 < len(study_matches) else len(text)
            content = text[start:end].strip()

            if content and len(content) > 30:
                sections.append({
                    "section": section_name,
                    "section_num": i + 1,
                    "content": content
                })

        if sections:
            return sections

    # Strategy 2: Act/Scene structure for plays (Shakespeare, etc.)
    # Handles: "Act I, Scene II", "ACT 1, SCENE 2", "Act II, PROLOGUE-SCENE I"
    act_scene_pattern = r'(Act\s+([IVX]+|\d+)[,:\s]+(Scene|SCENE|Prologue|PROLOGUE)[\s\-]*([IVX]*|\d*))'
    act_scene_matches = list(re.finditer(act_scene_pattern, text, re.IGNORECASE))

    if len(act_scene_matches) >= 5:
        print(f"  Detected play structure: {len(act_scene_matches)} scenes")

        # Add intro if exists before first act
        if act_scene_matches[0].start() > 100:
            intro = text[:act_scene_matches[0].start()].strip()
            if intro and len(intro) > 50:
                sections.append({
                    "section": "Introduction & Context",
                    "section_num": 0,
                    "content": intro
                })

        for i, match in enumerate(act_scene_matches):
            act_num = match.group(2)
            scene_type = match.group(3)  # Scene or Prologue
            scene_num = match.group(4) if match.group(4) else ""

            if scene_num:
                section_name = f"Act {act_num}, {scene_type} {scene_num}"
            else:
                section_name = f"Act {act_num}, {scene_type}"

            start = match.end()
            end = act_scene_matches[i + 1].start() if i + 1 < len(act_scene_matches) else len(text)
            content = text[start:end].strip()

            if content and len(content) > 50:
                sections.append({
                    "section": section_name,
                    "section_num": i + 1,
                    "content": content
                })

        if sections:
            return sections

    # Strategy 3: Weekly study guide format (WEEK 1: Title + Chapter One)
    week_pattern = r'(WEEK\s+(\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)[:\s]+([^\n]+))'
    week_matches = list(re.finditer(week_pattern, text, re.IGNORECASE))

    if len(week_matches) >= 3:
        print(f"  Detected weekly study guide: {len(week_matches)} weeks")

        # Add intro if exists before first week
        if week_matches[0].start() > 100:
            intro = text[:week_matches[0].start()].strip()
            if intro and len(intro) > 50:
                sections.append({
                    "section": "Introduction",
                    "section_num": 0,
                    "content": intro
                })

        for i, match in enumerate(week_matches):
            week_num = match.group(2)
            week_title = match.group(3).strip()
            # Use "Chapter" instead of "Week" for better querying
            section_name = f"Chapter {week_num}: {week_title[:50]}"

            start = match.end()
            end = week_matches[i + 1].start() if i + 1 < len(week_matches) else len(text)
            content = text[start:end].strip()

            if content and len(content) > 50:
                sections.append({
                    "section": section_name,
                    "section_num": i + 1,
                    "content": content
                })

        if sections:
            return sections

    # Strategy 3: Part + Chapter structure (e.g., traditional novels)
    part_pattern = r'(?:^|\n)\s*(Part|PART|Book|BOOK|Volume|VOLUME)\s+(\d+|[IVXLC]+|One|Two|Three|Four|First|Second|Third|Fourth)[\s:.\-]*([^\n]*)'
    part_matches = list(re.finditer(part_pattern, text, re.IGNORECASE))

    # Include spelled-out chapter numbers (One, Two, Three, etc.)
    chapter_pattern = r'(?:^|\n)\s*(Chapter|CHAPTER|Ch\.?)\s+(\d+|[IVXLC]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve)[\s:.\-]*([^\n]*)'
    chapter_matches = list(re.finditer(chapter_pattern, text, re.IGNORECASE))

    # If we have both parts AND chapters, use hierarchical structure
    if len(part_matches) >= 2 and len(chapter_matches) >= 3:
        print(f"  Detected hierarchical structure: {len(part_matches)} parts, {len(chapter_matches)} chapters")

        # Build a list of all markers (parts and chapters) sorted by position
        all_markers = []
        for m in part_matches:
            all_markers.append({
                "type": "part",
                "match": m,
                "pos": m.start(),
                "id": m.group(2),
                "title": m.group(3).strip() if m.group(3) else ""
            })
        for m in chapter_matches:
            all_markers.append({
                "type": "chapter",
                "match": m,
                "pos": m.start(),
                "id": m.group(2),
                "title": m.group(3).strip() if m.group(3) else ""
            })

        all_markers.sort(key=lambda x: x["pos"])

        # Track current part
        current_part = ""
        current_part_num = 0
        section_num = 0

        # Add intro if exists before first marker
        if all_markers and all_markers[0]["pos"] > 100:
            intro = text[:all_markers[0]["pos"]].strip()
            if intro:
                sections.append({
                    "section": "Introduction",
                    "section_num": 0,
                    "content": intro
                })

        for i, marker in enumerate(all_markers):
            start = marker["match"].end()
            end = all_markers[i + 1]["pos"] if i + 1 < len(all_markers) else len(text)
            content = text[start:end].strip()

            if marker["type"] == "part":
                current_part = f"Part {marker['id']}"
                current_part_num += 1
                if marker["title"]:
                    current_part += f": {marker['title'][:40]}"

                # Only add part as section if it has substantial content before next chapter
                if content and len(content) > 200:
                    section_num += 1
                    sections.append({
                        "section": current_part,
                        "section_num": section_num,
                        "content": content
                    })

            elif marker["type"] == "chapter":
                section_num += 1
                chapter_name = f"Chapter {marker['id']}"
                if marker["title"]:
                    chapter_name += f": {marker['title'][:40]}"

                # Prepend part info
                if current_part:
                    full_name = f"Part {current_part_num}, {chapter_name}"
                else:
                    full_name = chapter_name

                if content:
                    sections.append({
                        "section": full_name,
                        "section_num": section_num,
                        "content": content
                    })

        if sections:
            return sections

    # Try Chapter-only pattern (no parts)
    if len(chapter_matches) >= 3:
        print(f"  Detected chapter structure: {len(chapter_matches)} chapters")
        for i, match in enumerate(chapter_matches):
            chapter_id = match.group(2)
            chapter_title = match.group(3).strip() if match.group(3) else ""
            start = match.end()
            end = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else len(text)

            section_name = f"Chapter {chapter_id}"
            if chapter_title:
                section_name += f": {chapter_title[:50]}"

            content = text[start:end].strip()
            if content:
                sections.append({
                    "section": section_name,
                    "section_num": i + 1,
                    "content": content
                })

        # Add intro if exists
        if chapter_matches[0].start() > 100:
            intro = text[:chapter_matches[0].start()].strip()
            sections.insert(0, {
                "section": "Introduction",
                "section_num": 0,
                "content": intro
            })

        return sections

    # Try PAGE markers (common in PDF extracts)
    page_pattern = r'(?:={10,}\n)?PAGE\s+(\d+)\n(?:={10,}\n)?'
    matches = list(re.finditer(page_pattern, text, re.IGNORECASE))

    if len(matches) >= 3:
        for i, match in enumerate(matches):
            page_num = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            content = text[start:end].strip()
            # Clean up page separators
            content = re.sub(r'={10,}', '', content).strip()

            if content and len(content) > 50:
                sections.append({
                    "section": f"Page {page_num}",
                    "section_num": int(page_num),
                    "content": content
                })
        return sections

    # Try numbered sections (1., 2., etc.)
    numbered_pattern = r'\n(\d+)\.\s+([A-Z][^\n]+)'
    matches = list(re.finditer(numbered_pattern, text))

    if len(matches) >= 3:
        for i, match in enumerate(matches):
            num = match.group(1)
            title = match.group(2).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            content = text[start:end].strip()
            if content:
                sections.append({
                    "section": f"{num}. {title[:50]}",
                    "section_num": int(num),
                    "content": content
                })
        return sections

    # Fallback: split by double newlines into logical paragraphs, then group
    paragraphs = re.split(r'\n\s*\n', text)
    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 50]

    # Group paragraphs into ~2000 char sections
    current_section = []
    current_len = 0
    section_num = 1

    for para in paragraphs:
        current_section.append(para)
        current_len += len(para)

        if current_len >= 2000:
            content = "\n\n".join(current_section)
            # Try to extract a title from first sentence
            first_line = content.split('.')[0][:60] if '.' in content else content[:60]
            sections.append({
                "section": f"Section {section_num}: {first_line}...",
                "section_num": section_num,
                "content": content
            })
            current_section = []
            current_len = 0
            section_num += 1

    # Add remaining content
    if current_section:
        content = "\n\n".join(current_section)
        first_line = content.split('.')[0][:60] if '.' in content else content[:60]
        sections.append({
            "section": f"Section {section_num}: {first_line}...",
            "section_num": section_num,
            "content": content
        })

    if not sections:
        # Ultimate fallback: treat entire text as one section
        sections.append({
            "section": book_name,
            "section_num": 1,
            "content": text
        })

    return sections


def chunk_text(text: str, max_chars: int = 1500, overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_chars

        if end < len(text):
            search_start = max(end - 200, start)
            last_period = text.rfind('. ', search_start, end)
            if last_period > start:
                end = last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < len(text) else end

    return chunks


def create_documents(sections: list[dict], max_chars: int = 1500, overlap: int = 150) -> list[dict]:
    """Create document records for LanceDB."""
    documents = []

    for section_data in sections:
        section = section_data["section"]
        section_num = section_data["section_num"]
        content = section_data["content"]

        chunks = chunk_text(content, max_chars, overlap)
        n_docs = len(chunks)

        hash_title = hashlib.md5(section.encode()).hexdigest()[:16]

        for rank, chunk in enumerate(chunks):
            hash_doc = hashlib.md5(f"{section}_{rank}_{chunk[:50]}".encode()).hexdigest()[:16]

            documents.append({
                "text": chunk,
                "section": section,
                "section_num": section_num,
                "hash_title": hash_title,
                "hash_doc": hash_doc,
                "rank_abs": rank,
                "rank_rel": rank / max(n_docs, 1),
                "n_docs": n_docs,
            })

    return documents


def ingest_to_lancedb(documents: list[dict], output_dir: str, table_name: str) -> None:
    """Ingest documents into LanceDB with embeddings."""
    from sentence_transformers import SentenceTransformer
    import lancedb

    model_name = "multi-qa-MiniLM-L6-cos-v1"

    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)

    print("Generating embeddings...")
    texts = [doc["text"] for doc in documents]
    embeddings = model.encode(texts, show_progress_bar=True)

    for doc, vec in zip(documents, embeddings):
        doc["vector"] = vec.tolist()

    db_path = os.path.join(output_dir, "databases", "lancedb")
    print(f"Connecting to LanceDB at: {db_path}")

    db = lancedb.connect(db_path)

    try:
        db.drop_table(table_name)
        print(f"Dropped existing table: {table_name}")
    except Exception:
        pass

    print(f"Creating table '{table_name}' with {len(documents)} chunks...")
    table = db.create_table(table_name, data=documents)

    print("Creating full-text search index...")
    try:
        table.create_fts_index("text", replace=True)
        print("FTS index created successfully")
    except Exception as e:
        print(f"Warning: Could not create FTS index: {e}")

    print(f"\nIngestion complete! Table '{table_name}' has {table.count_rows()} rows")


def main():
    parser = argparse.ArgumentParser(
        description="Create a RAG knowledge base from any text file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_rag_from_text.py don_quixote.txt
  python create_rag_from_text.py don_quixote.txt -o rag_don_quixote
  python create_rag_from_text.py notes.pdf.txt -o rag_notes --name "Study Notes"

After creation, copy the folder to your anthropic_chat_cli.py location:
  cp -r rag_don_quixote /path/to/streamlit_apps/
  python anthropic_chat_cli.py --rag rag_don_quixote
        """
    )
    parser.add_argument(
        "input_file",
        help="Path to the text file to process"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output folder name (default: rag_<filename>)"
    )
    parser.add_argument(
        "--name",
        help="Display name for the knowledge base (default: filename)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show detected sections, don't create RAG database"
    )
    args = parser.parse_args()

    # Check input file
    if not os.path.exists(args.input_file):
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)

    # Determine output folder name
    input_path = Path(args.input_file)
    base_name = input_path.stem.lower().replace(" ", "_").replace("-", "_")
    output_dir = args.output or f"rag_{base_name}"

    # Determine table name
    table_name = base_name.replace(".", "_")

    # Display name
    display_name = args.name or input_path.stem

    if args.dry_run:
        print(f"=" * 60)
        print(f"  DRY RUN: Testing demarcations for {display_name}")
        print(f"=" * 60)
    else:
        print(f"=" * 60)
        print(f"  Creating RAG: {display_name}")
        print(f"=" * 60)
        print(f"Input: {args.input_file}")
        print(f"Output: {output_dir}/")
    print()

    if not args.dry_run:
        # Step 1: Create folder structure
        print("Step 1: Creating folder structure...")
        create_folder_structure(output_dir)

        # Step 2: Write config and source files
        print("\nStep 2: Writing config and source files...")
        write_config_file(output_dir, table_name)
        write_init_file(output_dir)
        write_constants_file(output_dir)
        write_retrieval_file(output_dir)
        write_requirements_file(output_dir)

    # Read and parse text
    print(f"Reading {args.input_file}...")
    with open(args.input_file, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    print(f"  Read {len(text):,} characters")

    # Parse into sections
    print("\nParsing sections...")
    sections = parse_sections(text, display_name)
    print(f"\n  Found {len(sections)} sections:")

    # Show more sections in dry-run mode
    show_count = len(sections) if args.dry_run else 10
    for s in sections[:show_count]:
        print(f"    - {s['section'][:60]}... ({len(s['content']):,} chars)")
    if len(sections) > show_count:
        print(f"    ... and {len(sections) - show_count} more")

    if args.dry_run:
        print()
        print("=" * 60)
        print("  DRY RUN COMPLETE - No files created")
        print("=" * 60)
        print()
        print("To create the RAG, run without --dry-run:")
        print(f"  python create_rag_from_text.py {args.input_file} -o {output_dir}")
        return

    # Step 5: Create document chunks
    print("\nStep 5: Creating document chunks...")
    documents = create_documents(sections)
    print(f"  Created {len(documents)} chunks")

    # Step 6: Ingest to LanceDB
    print("\nStep 6: Ingesting to LanceDB...")
    ingest_to_lancedb(documents, output_dir, table_name)

    # Done!
    print()
    print("=" * 60)
    print(f"  SUCCESS! RAG created at: {output_dir}/")
    print("=" * 60)
    print()
    print("To use with anthropic_chat_cli.py:")
    print(f"  1. cp -r {output_dir} /path/to/streamlit_apps/")
    print(f"  2. python anthropic_chat_cli.py --rag {output_dir}")
    print()


if __name__ == "__main__":
    main()
