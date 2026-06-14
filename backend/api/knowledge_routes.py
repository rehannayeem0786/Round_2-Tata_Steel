"""
Knowledge base API routes — Document upload, search, and management.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from knowledge.vector_store import search_all_collections, get_collection_stats
from knowledge.document_processor import process_uploaded_file

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/stats")
async def knowledge_stats():
    """Get knowledge base statistics."""
    stats = get_collection_stats()
    return {"success": True, "data": stats}


@router.get("/search")
async def search_knowledge(q: str, n: int = 5):
    """Search the knowledge base."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    results = search_all_collections(q, n_results=n)
    
    formatted = []
    for r in results:
        formatted.append({
            "text": r["document"][:500] + "..." if len(r["document"]) > 500 else r["document"],
            "full_text": r["document"],
            "source": r["metadata"].get("source_file", "unknown"),
            "category": r["metadata"].get("category", "unknown"),
            "collection": r.get("collection", "unknown"),
            "relevance": round(1 - r["distance"], 3),
        })
    
    return {"success": True, "data": formatted}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="uploaded")
):
    """Upload a document to the knowledge base."""
    if not file.filename.endswith(('.txt', '.md', '.log', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="Only .txt, .md, .log, and .csv files are supported"
        )
    
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        
        chunks = process_uploaded_file(file.filename, text_content, category)
        
        return {
            "success": True,
            "data": {
                "filename": file.filename,
                "chunks_created": chunks,
                "category": category,
                "message": f"Successfully indexed '{file.filename}' into {chunks} chunks"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
