"""
Feedback Agent — Manages the feedback loop for continuous improvement.
Stores user corrections, tracks accuracy, and incorporates feedback
into future responses.
"""

from data.database import insert_feedback, get_feedback_stats, get_recent_feedback


def process_feedback(conversation_id: str, message_index: int, rating: str, correction: str = None) -> dict:
    """
    Process user feedback on a system response.
    
    Args:
        conversation_id: ID of the conversation
        message_index: Index of the message being rated
        rating: 'positive' or 'negative'
        correction: Optional correction text from the user
        
    Returns:
        dict with feedback status and updated stats
    """
    insert_feedback(conversation_id, message_index, rating, correction)
    
    stats = get_feedback_stats()
    
    return {
        "status": "recorded",
        "message": f"Thank you for your feedback! {'Your correction has been recorded and will help improve future recommendations.' if correction else 'Your rating has been recorded.'}",
        "stats": stats,
    }


def get_feedback_context() -> str:
    """
    Get recent feedback as context for improving future responses.
    Returns a formatted string of recent corrections that agents can use.
    """
    recent = get_recent_feedback(limit=10)
    
    if not recent:
        return ""
    
    corrections = [f for f in recent if f.get("correction")]
    
    if not corrections:
        return ""
    
    context = "RECENT USER CORRECTIONS (use these to improve your responses):\n"
    for fb in corrections[:5]:
        context += f"- Correction: {fb['correction']}\n"
    
    return context


def get_system_accuracy() -> dict:
    """Get the system's accuracy metrics based on feedback."""
    return get_feedback_stats()
