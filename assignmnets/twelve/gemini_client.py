"""
Gemini API client for interacting with Google's Gemini 2.0 Flash model.
Handles all communication with the Gemini API for form analysis and decision-making.
"""

import os
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from prompts import (
    SYSTEM_PROMPT,
    FORM_ANALYSIS_PROMPT,
    FIELD_VALUE_PROMPT,
    FORM_FILLING_STRATEGY,
    ERROR_HANDLING_PROMPT
)

# Load environment variables
load_dotenv()


class GeminiClient:
    """Client for interacting with Google Gemini 2.0 Flash API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Gemini API key. If not provided, will try to load from .env file.
        """
        # Try multiple possible environment variable names
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it in .env file as GEMINI_API_KEY=your_key_here"
            )
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize the model (Gemini 2.0 Flash)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
    def analyze_form(self, form_structure: str, form_fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze form structure and get filling instructions.
        
        Args:
            form_structure: HTML or text representation of the form
            form_fields: List of detected form fields
            
        Returns:
            Dictionary with field analysis and filling strategy
        """
        form_fields_str = json.dumps(form_fields, indent=2)
        
        prompt = FORM_ANALYSIS_PROMPT.format(
            form_structure=form_structure[:5000],  # Limit length
            form_fields=form_fields_str
        )
        
        try:
            response = self.model.generate_content(
                SYSTEM_PROMPT + "\n\n" + prompt
            )
            
            # Try to extract JSON from response
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                # Fallback: return structured response
                return {
                    "fields": form_fields,
                    "strategy": response_text,
                    "raw_response": response_text
                }
        except Exception as e:
            print(f"Error analyzing form: {e}")
            return {
                "fields": form_fields,
                "strategy": "Fill all required fields with appropriate values",
                "error": str(e)
            }
    
    def get_field_value(
        self,
        field_label: str,
        field_type: str,
        field_options: Optional[List[str]] = None,
        is_required: bool = True,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the value to fill in a specific field.
        
        Args:
            field_label: Label or description of the field
            field_type: Type of field (text, dropdown, radio, etc.)
            field_options: Available options for dropdown/radio fields
            is_required: Whether the field is required
            context: Additional context about the form
            
        Returns:
            Dictionary with value and reasoning
        """
        options_str = ", ".join(field_options) if field_options else "N/A"
        
        prompt = FIELD_VALUE_PROMPT.format(
            field_label=field_label,
            field_type=field_type,
            field_options=options_str,
            is_required=is_required,
            context=context or "No additional context"
        )
        
        try:
            response = self.model.generate_content(
                SYSTEM_PROMPT + "\n\n" + prompt
            )
            
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                # Fallback: extract value from text
                return {
                    "value": self._extract_value_from_text(response_text, field_options),
                    "reasoning": response_text
                }
        except Exception as e:
            print(f"Error getting field value: {e}")
            return {
                "value": None,
                "reasoning": f"Error: {str(e)}"
            }
    
    def get_filling_strategy(self, form_url: str, form_fields_summary: str) -> str:
        """
        Get overall strategy for filling the form.
        
        Args:
            form_url: URL of the form
            form_fields_summary: Summary of form fields
            
        Returns:
            Strategy description
        """
        prompt = FORM_FILLING_STRATEGY.format(
            form_url=form_url,
            form_fields_summary=form_fields_summary
        )
        
        try:
            response = self.model.generate_content(
                SYSTEM_PROMPT + "\n\n" + prompt
            )
            return response.text
        except Exception as e:
            print(f"Error getting strategy: {e}")
            return "Fill all required fields in order."
    
    def handle_error(
        self,
        error_message: str,
        current_field: Optional[str] = None,
        form_state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get recovery instructions for an error.
        
        Args:
            error_message: Description of the error
            current_field: Field where error occurred
            form_state: Current state of the form
            
        Returns:
            Recovery instructions
        """
        prompt = ERROR_HANDLING_PROMPT.format(
            error_message=error_message,
            current_field=current_field or "Unknown",
            form_state=form_state or "Unknown"
        )
        
        try:
            response = self.model.generate_content(
                SYSTEM_PROMPT + "\n\n" + prompt
            )
            return {
                "recovery_instructions": response.text,
                "should_retry": True
            }
        except Exception as e:
            return {
                "recovery_instructions": f"Error occurred: {str(e)}",
                "should_retry": False
            }
    
    def _extract_value_from_text(self, text: str, options: Optional[List[str]] = None) -> Optional[str]:
        """Extract a value from text response, matching options if available."""
        if options:
            text_lower = text.lower()
            for option in options:
                if option.lower() in text_lower:
                    return option
        
        # Try to find quoted values
        import re
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            return quoted[0]
        
        return None

