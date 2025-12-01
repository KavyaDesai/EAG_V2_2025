"""Conversation state management with memory and context."""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from core.logger import get_logger

logger = get_logger()


@dataclass
class ConversationState:
    """Manages conversation history and session context."""
    
    message_history: List[Dict[str, str]] = field(default_factory=list)
    max_history: int = 20
    
    # Session context
    last_task_type: Optional[str] = None
    last_url: Optional[str] = None
    last_folder: Optional[str] = None
    last_search_query: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add a message to history."""
        self.message_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if too long
        if len(self.message_history) > self.max_history * 2:  # *2 for user+assistant pairs
            # Keep last max_history pairs
            self.message_history = self.message_history[-self.max_history * 2:]
        
        logger.debug(
            f"Added {role} message (history length: {len(self.message_history)})",
            component="ConversationState"
        )
    
    def get_recent_messages(self, n: int = 10) -> List[Dict[str, str]]:
        """Get last N messages."""
        return self.message_history[-n:]
    
    def get_formatted_history(self, max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """Get formatted message history for LLM."""
        messages = self.message_history
        if max_messages:
            messages = messages[-max_messages:]
        
        # Format for LLM (remove timestamp)
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return formatted
    
    def update_context(self, task_type: Optional[str] = None, url: Optional[str] = None,
                      folder: Optional[str] = None, search_query: Optional[str] = None):
        """Update session context."""
        if task_type:
            self.last_task_type = task_type
        if url:
            self.last_url = url
        if folder:
            self.last_folder = folder
        if search_query:
            self.last_search_query = search_query
        
        logger.debug(
            f"Updated context: task_type={task_type}, url={url}, folder={folder}",
            component="ConversationState"
        )
    
    def clear_history(self):
        """Clear message history."""
        self.message_history = []
        logger.info("Cleared conversation history", component="ConversationState")
    
    def get_context_summary(self) -> Dict[str, Optional[str]]:
        """Get summary of current context."""
        return {
            "last_task_type": self.last_task_type,
            "last_url": self.last_url,
            "last_folder": self.last_folder,
            "last_search_query": self.last_search_query,
            "message_count": len(self.message_history)
        }

