"""
Document processor — Ingests text files, chunks them, and indexes
them into the ChromaDB vector store for RAG retrieval.
"""

import os
import hashlib
from pathlib import Path
from knowledge.vector_store import add_documents, get_collection
from config import KNOWLEDGE_DIR, CHUNK_SIZE, CHUNK_OVERLAP


# Mapping of directory names to collection names
COLLECTION_MAP = {
    "equipment_manuals": "equipment_manuals",
    "sops": "standard_operating_procedures",
    "maintenance_records": "maintenance_records",
    "failure_reports": "failure_reports",
}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Split text into overlapping chunks by character count,
    respecting sentence boundaries where possible.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        
        # Try to break at a paragraph boundary
        para_break = text.rfind('\n\n', start, end)
        if para_break > start + chunk_size // 2:
            end = para_break
        else:
            # Try to break at a sentence boundary
            for sep in ['. ', '.\n', '\n']:
                sent_break = text.rfind(sep, start + chunk_size // 2, end)
                if sent_break > start:
                    end = sent_break + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


def extract_metadata(filepath: str, directory_name: str) -> dict:
    """Extract metadata from a file based on its location and name."""
    filename = os.path.basename(filepath)
    name_parts = filename.replace('.txt', '').replace('_', ' ').title()
    
    category_map = {
        "equipment_manuals": "Equipment Manual",
        "sops": "Standard Operating Procedure",
        "maintenance_records": "Maintenance Record",
        "failure_reports": "Failure Analysis Report",
    }
    
    return {
        "source_file": filename,
        "category": category_map.get(directory_name, "Unknown"),
        "title": name_parts,
        "directory": directory_name,
    }


def process_file(filepath: str, collection_name: str, directory_name: str):
    """Process a single text file: chunk and index it."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not content.strip():
        return 0
    
    # Extract metadata
    metadata = extract_metadata(filepath, directory_name)
    
    # Chunk the text
    chunks = chunk_text(content)
    
    # Generate unique IDs based on file and chunk position
    file_hash = hashlib.md5(filepath.encode()).hexdigest()[:8]
    ids = [f"{file_hash}_chunk_{i}" for i in range(len(chunks))]
    
    # Add chunk index to metadata
    metadatas = []
    for i, chunk in enumerate(chunks):
        meta = metadata.copy()
        meta["chunk_index"] = i
        meta["total_chunks"] = len(chunks)
        metadatas.append(meta)
    
    # Index into vector store
    add_documents(collection_name, chunks, metadatas, ids)
    
    return len(chunks)


def process_uploaded_file(filename: str, content: str, category: str = "uploaded"):
    """Process an uploaded file and add to the knowledge base."""
    collection_name = "uploaded_documents"
    
    chunks = chunk_text(content)
    
    file_hash = hashlib.md5(f"{filename}_{content[:100]}".encode()).hexdigest()[:8]
    ids = [f"upload_{file_hash}_chunk_{i}" for i in range(len(chunks))]
    
    metadatas = []
    for i, chunk in enumerate(chunks):
        metadatas.append({
            "source_file": filename,
            "category": category,
            "title": filename.replace('.txt', '').replace('_', ' ').title(),
            "directory": "uploads",
            "chunk_index": i,
            "total_chunks": len(chunks),
        })
    
    add_documents(collection_name, chunks, metadatas, ids)
    return len(chunks)


def load_knowledge_base():
    """Load all knowledge documents from the sample_knowledge directory."""
    if not KNOWLEDGE_DIR.exists():
        print("[WARN] Knowledge directory not found, skipping...")
        return
    
    total_chunks = 0
    total_files = 0
    
    print("[KB] Loading knowledge base...")
    
    for dir_name, collection_name in COLLECTION_MAP.items():
        dir_path = KNOWLEDGE_DIR / dir_name
        if not dir_path.exists():
            continue
        
        # Check if collection already has documents
        col = get_collection(collection_name)
        if col.count() > 0:
            print(f"  [SKIP] Collection '{collection_name}' already loaded ({col.count()} chunks)")
            total_chunks += col.count()
            continue
        
        for filename in os.listdir(dir_path):
            if filename.endswith('.txt'):
                filepath = str(dir_path / filename)
                chunks = process_file(filepath, collection_name, dir_name)
                total_chunks += chunks
                total_files += 1
                print(f"  [DOC] {filename}: {chunks} chunks")
    
    print(f"[OK] Knowledge base loaded: {total_files} files, {total_chunks} total chunks")
    return {"files": total_files, "chunks": total_chunks}
