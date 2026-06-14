"""
Vector store module — ChromaDB integration for semantic search
over maintenance knowledge documents.
"""

import chromadb
from chromadb.config import Settings
from config import CHROMA_DIR

try:
    from chromadb.telemetry.product.posthog import Posthog
    Posthog._direct_capture = lambda self, event: None
except Exception:
    pass

_client = None
_collections = {}


def get_client():
    """Get or create the ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
    return _client


def get_collection(name: str):
    """Get or create a named collection."""
    if name not in _collections:
        client = get_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )
    return _collections[name]


def add_documents(collection_name: str, documents: list, metadatas: list, ids: list):
    """
    Add documents to a collection.
    
    Args:
        collection_name: Name of the collection
        documents: List of text chunks
        metadatas: List of metadata dicts per chunk
        ids: List of unique IDs per chunk
    """
    collection = get_collection(collection_name)
    
    # ChromaDB handles batching internally, but we chunk to avoid memory issues
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_metas = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        
        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
    
    print(f"  [OK] Added {len(documents)} chunks to collection '{collection_name}'")


def search(collection_name: str, query: str, n_results: int = 5, where: dict = None):
    """
    Search a collection for relevant documents.
    
    Args:
        collection_name: Name of the collection to search
        query: Search query text
        n_results: Number of results to return
        where: Optional metadata filter
        
    Returns:
        List of dicts with 'document', 'metadata', 'distance'
    """
    collection = get_collection(collection_name)
    
    kwargs = {
        "query_texts": [query],
        "n_results": min(n_results, collection.count()) if collection.count() > 0 else 1,
    }
    
    if where:
        kwargs["where"] = where
    
    if collection.count() == 0:
        return []
    
    results = collection.query(**kwargs)
    
    output = []
    if results and results["documents"] and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            output.append({
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
    
    return output


def search_all_collections(query: str, n_results: int = 5):
    """
    Search across all collections and merge results.
    
    Returns:
        List of dicts sorted by relevance (lowest distance first)
    """
    all_results = []
    client = get_client()
    
    for col in client.list_collections():
        col_results = search(col.name, query, n_results)
        for r in col_results:
            r["collection"] = col.name
        all_results.extend(col_results)
    
    # Sort by distance (lower = more similar for cosine)
    all_results.sort(key=lambda x: x["distance"])
    
    return all_results[:n_results]


def get_collection_stats():
    """Get statistics about all collections."""
    client = get_client()
    stats = {}
    for col in client.list_collections():
        stats[col.name] = {
            "count": col.count(),
        }
    return stats


def delete_collection(name: str):
    """Delete a collection."""
    client = get_client()
    client.delete_collection(name)
    if name in _collections:
        del _collections[name]
