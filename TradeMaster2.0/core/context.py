"""
Context Manager for TradeMaster 2.0

This module manages user conversation contexts to maintain continuity
in conversations and provide more relevant responses.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json

logger = logging.getLogger("TradeMaster.Context")

class ContextManager:
    """
    Manages user conversation contexts for TradeMaster.
    
    This class handles storing and retrieving user context information,
    including conversation history, user preferences, and interaction patterns.
    """
    
    def __init__(self, max_history: int = 10, context_expiry: int = 24):
        """
        Initialize the context manager.
        
        Args:
            max_history: Maximum number of messages to store in history
            context_expiry: Hours after which context expires
        """
        # Dictionary to store user contexts
        self.contexts: Dict[str, Dict[str, Any]] = {}
        
        # Configuration
        self.max_history = max_history
        self.context_expiry = timedelta(hours=context_expiry)
        
        logger.info("Context Manager initialized")
    
    def update_last_message(self, user_id: str, message: str):
        """
        Update a user's context with their latest message.
        
        Args:
            user_id: The user's ID
            message: The user's message
        """
        # Get or create user context
        context = self.get_context(user_id)
        
        # Update last message
        context['last_message'] = message
        context['last_active'] = datetime.now().isoformat()
        
        # Update message history
        if 'message_history' not in context:
            context['message_history'] = []
        
        # Add message to history with timestamp
        context['message_history'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Trim history if it gets too long
        if len(context['message_history']) > self.max_history:
            context['message_history'] = context['message_history'][-self.max_history:]
        
        # Store updated context
        self.contexts[user_id] = context
    
    def add_bot_response(self, user_id: str, response: str):
        """
        Add a bot response to the user's context.
        
        Args:
            user_id: The user's ID
            response: The bot's response
        """
        context = self.get_context(user_id)
        
        # Update last bot response
        context['last_bot_response'] = response
        context['last_interaction_time'] = datetime.now().isoformat()
        
        # Add response to message history
        if 'message_history' in context:
            context['message_history'].append({
                'role': 'assistant', 
                'content': response,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get a user's context, creating a new one if it doesn't exist.
        
        Args:
            user_id: The user's ID
            
        Returns:
            The user's context dictionary
        """
        # Create empty context if it doesn't exist
        if user_id not in self.contexts:
            self.contexts[user_id] = {}
        
        return self.contexts[user_id]
    
    def get_conversation_history(self, user_id: str, 
                                 max_messages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get a user's conversation history in a format suitable for LLMs.
        
        Args:
            user_id: The user's ID
            max_messages: Maximum number of messages to include
            
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        context = self.get_context(user_id)
        history = context.get('message_history', [])
        
        # If max_messages specified, trim history
        if max_messages and len(history) > max_messages:
            history = history[-max_messages:]
        
        # Format for LLM (remove timestamps)
        formatted_history = [
            {'role': msg['role'], 'content': msg['content']}
            for msg in history
        ]
        
        return formatted_history
    
    def clean_expired_contexts(self):
        """
        Remove expired user contexts to free up memory.
        """
        now = datetime.now()
        expired_users = []
        
        for user_id, context in self.contexts.items():
            last_active = context.get('last_active')
            if last_active:
                try:
                    active_time = datetime.fromisoformat(last_active)
                    if now - active_time > self.context_expiry:
                        expired_users.append(user_id)
                except (ValueError, TypeError):
                    # If we can't parse the timestamp, consider it expired
                    expired_users.append(user_id)
        
        # Remove expired contexts
        for user_id in expired_users:
            del self.contexts[user_id]
        
        if expired_users:
            logger.info(f"Cleaned {len(expired_users)} expired user contexts")
    
    def update_user_info(self, user_id: str, **kwargs):
        """
        Update user information in the context.
        
        Args:
            user_id: The user's ID
            **kwargs: Key-value pairs to update
        """
        context = self.get_context(user_id)
        
        # Update user info
        if 'user_info' not in context:
            context['user_info'] = {}
        
        context['user_info'].update(kwargs)
    
    def extract_topics(self, user_id: str) -> List[str]:
        """
        Extract likely conversation topics from recent history.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of potential conversation topics
        """
        # This is a placeholder for future ML-based topic extraction
        # For now, just return the last 3 messages
        context = self.get_context(user_id)
        history = context.get('message_history', [])
        
        if not history:
            return []
        
        # Get last few user messages
        recent_messages = [
            msg['content'] for msg in history[-5:] 
            if msg['role'] == 'user'
        ]
        
        return recent_messages