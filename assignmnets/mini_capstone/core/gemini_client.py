"""Gemini 2.0 Flash API client with retry logic and error handling."""

import os
import time
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from pathlib import Path
from core.logger import get_logger

logger = get_logger()


class GeminiClient:
    """Client for Gemini 2.0 Flash API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-exp"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            model: Model name (default: gemini-2.0-flash-exp)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY environment variable must be set")
        
        genai.configure(api_key=self.api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # Exponential backoff
        
        logger.info(f"Initialized Gemini client with model: {model}", component="GeminiClient")
    
    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate text using Gemini API with retry logic.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system instruction
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
            
        Raises:
            Exception: If all retries fail
        """
        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        for attempt in range(self.max_retries):
            try:
                logger.log_api_call(
                    "generate",
                    component="GeminiClient",
                    attempt=attempt + 1,
                    model=self.model_name
                )
                
                start_time = time.time()
                
                # Configure model with system instruction if provided
                model = self.model
                if system_instruction:
                    model = genai.GenerativeModel(
                        self.model_name,
                        system_instruction=system_instruction
                    )
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                duration = time.time() - start_time
                logger.log_execution_time("generate", duration, "GeminiClient")
                
                if not response.text:
                    raise ValueError("Empty response from Gemini API")
                
                return response.text
                
            except Exception as e:
                error_type = self._classify_error(e)
                logger.error(
                    f"Gemini API call failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}",
                    component="GeminiClient",
                    error_type=error_type,
                    attempt=attempt + 1
                )
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(
                        f"Retrying in {delay}s...",
                        component="GeminiClient"
                    )
                    time.sleep(delay)
                else:
                    # All retries failed
                    user_message = self._get_user_friendly_error(error_type)
                    raise Exception(f"{user_message} Original error: {str(e)}")
        
        raise Exception("Failed to generate response after all retries")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Chat with Gemini using message history.
        
        Args:
            messages: List of messages in format [{"role": "user", "content": "..."}, ...]
            system_instruction: Optional system instruction
            temperature: Temperature for generation
            
        Returns:
            Assistant's response
        """
        # Convert messages to Gemini format
        # Gemini uses 'user' and 'model' roles
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "model"
            chat_messages.append({
                "role": role,
                "parts": [msg["content"]]
            })
        
        # Use generate for now (Gemini SDK handles chat differently)
        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n\n".join(prompt_parts) + "\n\nAssistant:"
        
        return self.generate(prompt, system_instruction, temperature)
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for logging."""
        error_str = str(error).lower()
        if "api_key" in error_str or "invalid" in error_str:
            return "API_KEY_INVALID"
        elif "quota" in error_str or "rate limit" in error_str:
            return "RATE_LIMIT"
        elif "timeout" in error_str:
            return "TIMEOUT"
        elif "quota" in error_str:
            return "QUOTA_EXCEEDED"
        else:
            return "UNKNOWN_ERROR"
    
    def _get_user_friendly_error(self, error_type: str) -> str:
        """Get user-friendly error message."""
        error_messages = {
            "API_KEY_INVALID": "API key is invalid. Please check your .env file.",
            "RATE_LIMIT": "API rate limit exceeded. Please try again in a moment.",
            "QUOTA_EXCEEDED": "API quota exceeded. Please check your usage limits.",
            "TIMEOUT": "Request timed out. Please try again.",
            "UNKNOWN_ERROR": "Unable to process request. Please try again."
        }
        return error_messages.get(error_type, "An error occurred. Please try again.")

