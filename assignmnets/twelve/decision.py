"""
Decision Module - Makes intelligent decisions about what to fill in form fields.

This module is responsible for:
- Analyzing field purpose and context
- Deciding appropriate values to fill
- Using AI to make intelligent choices
- Handling edge cases and validation
"""

import json
from typing import Dict, List, Any, Optional
from gemini_client import GeminiClient
from prompts import (
    SYSTEM_PROMPT,
    FIELD_VALUE_PROMPT,
    ERROR_HANDLING_PROMPT
)


class Decision:
    """
    Decision module that determines what values to fill in form fields.
    Uses AI and context to make intelligent decisions.
    """
    
    def __init__(self, gemini_client: GeminiClient):
        """
        Initialize the Decision module.
        
        Args:
            gemini_client: Gemini client for AI decision-making
        """
        self.gemini_client = gemini_client
    
    def decide_field_value(
        self,
        field_classification: Dict[str, Any],
        form_context: Dict[str, Any],
        all_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Decide what value to fill in a specific field.
        
        Args:
            field_classification: Classified field from Perception
            form_context: Overall form context
            all_fields: All fields in the form for context
            
        Returns:
            Decision result with value and reasoning
        """
        field = field_classification.get('field', {})
        purpose = field_classification.get('purpose', 'text')
        detected_type = field_classification.get('detected_type', 'text')
        label = field.get('label', 'Unknown')
        options = field.get('options', [])
        is_required = field.get('required', False)
        
        print(f"\n🤖 [Decision] Deciding value for: '{label}'")
        print(f"   Purpose: {purpose}, Type: {detected_type}")
        
        # Use AI to make decision
        decision = self._ai_decide(
            label=label,
            field_type=detected_type,
            purpose=purpose,
            options=options,
            is_required=is_required,
            form_context=form_context
        )
        
        # Validate and refine decision
        validated_decision = self._validate_decision(
            decision=decision,
            field_classification=field_classification,
            options=options
        )
        
        return validated_decision
    
    def _ai_decide(
        self,
        label: str,
        field_type: str,
        purpose: str,
        options: List[str],
        is_required: bool,
        form_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use AI to decide what value to fill.
        
        Args:
            label: Field label
            field_type: Detected field type
            purpose: Field purpose (from Perception)
            options: Available options (if any)
            is_required: Whether field is required
            form_context: Form context
            
        Returns:
            AI decision with value and reasoning
        """
        # Build context string
        context_parts = [
            f"Field purpose: {purpose}",
            f"Field type: {field_type}",
            f"Form context: {json.dumps(form_context, indent=2)[:500]}"
        ]
        context = "\n".join(context_parts)
        
        # Enhance prompt based on purpose
        enhanced_prompt = self._build_enhanced_prompt(
            label=label,
            field_type=field_type,
            purpose=purpose,
            options=options,
            is_required=is_required,
            context=context
        )
        
        try:
            response = self.gemini_client.model.generate_content(
                SYSTEM_PROMPT + "\n\n" + enhanced_prompt
            )
            
            # Parse response
            response_text = response.text
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                return {
                    "value": result.get("value"),
                    "reasoning": result.get("reasoning", response_text),
                    "confidence": "high"
                }
            else:
                # Fallback: extract value from text
                return {
                    "value": self._extract_value_from_text(response_text, options, purpose),
                    "reasoning": response_text,
                    "confidence": "medium"
                }
        except Exception as e:
            print(f"  ⚠ [Decision] AI decision error: {e}")
            return {
                "value": self._fallback_decision(purpose, options),
                "reasoning": f"Fallback due to error: {str(e)}",
                "confidence": "low"
            }
    
    def _build_enhanced_prompt(
        self,
        label: str,
        field_type: str,
        purpose: str,
        options: List[str],
        is_required: bool,
        context: str
    ) -> str:
        """Build an enhanced prompt based on field purpose."""
        
        # Base prompt
        base_prompt = FIELD_VALUE_PROMPT.format(
            field_label=label,
            field_type=field_type,
            field_options=", ".join(options) if options else "N/A",
            is_required=is_required,
            context=context
        )
        
        # Add purpose-specific guidance
        purpose_guidance = {
            'name': "Provide a realistic person's name (first and last name). Example: 'John Doe', 'Jane Smith'.",
            'email': "Provide a REALISTIC, VALID email address. Examples: 'john.doe@email.com', 'jane.smith@example.com'. NEVER use placeholder text like 'TEXT' or 'email@example.com' - use a proper email format with a name.",
            'date': "Provide a date in format YYYY-MM-DD or MM/DD/YYYY. Use a realistic date.",
            'course': "Provide a course name or subject (e.g., 'Computer Science', 'Mathematics'). DO NOT use date formats.",
            'marital_status': f"Choose from available options: {', '.join(options) if options else 'Yes, No, Maybe'}. Match the EXACT option text.",
            'choice': f"Select from available options: {', '.join(options)}. Match the EXACT option text."
        }
        
        guidance = purpose_guidance.get(purpose, "Provide an appropriate value for this field.")
        
        enhanced = f"""{base_prompt}

SPECIFIC GUIDANCE FOR THIS FIELD:
- Purpose: {purpose}
- {guidance}
- IMPORTANT: If this is a text field (not date), provide TEXT, NOT date formats like mm/dd/yyyy.
- If this is a choice field (dropdown/radio), the value MUST exactly match one of the options."""
        
        return enhanced
    
    def _validate_decision(
        self,
        decision: Dict[str, Any],
        field_classification: Dict[str, Any],
        options: List[str]
    ) -> Dict[str, Any]:
        """
        Validate and refine the decision.
        
        Args:
            decision: AI decision
            field_classification: Field classification from Perception
            options: Available options
            
        Returns:
            Validated decision
        """
        value = decision.get("value")
        purpose = field_classification.get("purpose")
        detected_type = field_classification.get("detected_type")
        
        if not value:
            return decision
        
        # Validate email fields - reject placeholder values
        if purpose == 'email' or detected_type == 'email':
            value_str = str(value).lower().strip()
            # Reject placeholder values
            if value_str in ['text', 'example', 'placeholder', 'email', 'email@example.com', 'text@example.com']:
                # Generate a proper email
                import random
                names = ['john', 'jane', 'mike', 'sarah', 'david', 'emily', 'robert', 'lisa']
                domains = ['email.com', 'example.com', 'test.com', 'mail.com', 'gmail.com']
                value = f"{random.choice(names)}.{random.choice(names)}@{random.choice(domains)}"
                decision["value"] = value
                decision["validated"] = True
                decision["corrected"] = "Replaced placeholder with realistic email"
                print(f"   ✓ Corrected email: Generated '{value}'")
        
        # Validate text fields - reject placeholder values
        if detected_type == 'text' and purpose != 'email':
            value_str = str(value).upper().strip()
            if value_str in ['TEXT', 'EXAMPLE', 'PLACEHOLDER', 'SAMPLE']:
                # Use fallback based on purpose
                value = self._fallback_decision(purpose, options)
                decision["value"] = value
                decision["validated"] = True
                decision["corrected"] = "Replaced placeholder with realistic value"
                print(f"   ✓ Corrected text: Generated '{value}'")
        
        # Validate against options (for choice fields)
        if options and detected_type in ['radio', 'select']:
            # Check if value matches any option (case-insensitive)
            value_lower = str(value).lower().strip()
            matching_option = None
            
            for option in options:
                if (value_lower == option.lower().strip() or 
                    value_lower in option.lower() or 
                    option.lower() in value_lower):
                    matching_option = option
                    break
            
            if matching_option:
                decision["value"] = matching_option  # Use exact option text
                decision["validated"] = True
                print(f"   ✓ Validated: Using exact option '{matching_option}'")
            else:
                print(f"   ⚠ Value '{value}' doesn't match options: {options}")
                # Try to use first option as fallback
                if options:
                    decision["value"] = options[0]
                    decision["validated"] = False
                    decision["fallback_used"] = True
        
        # Validate date format
        if detected_type == 'date' and value:
            if '/' not in str(value) and '-' not in str(value):
                print(f"   ⚠ Date value '{value}' doesn't look like a date format")
        
        # Validate text field doesn't have date format
        if detected_type == 'text' and value:
            if ('/' in str(value) or '-' in str(value)) and len(str(value).split('/')) == 3:
                print(f"   ⚠ Text field got date-like value '{value}', this might be wrong")
        
        return decision
    
    def _extract_value_from_text(self, text: str, options: List[str], purpose: str) -> Optional[str]:
        """Extract value from AI text response."""
        text_lower = text.lower()
        
        # For choice fields, try to match options
        if options:
            for option in options:
                if option.lower() in text_lower:
                    return option
        
        # Try to find quoted values
        import re
        quoted = re.findall(r'"([^"]+)"', text)
        if quoted:
            return quoted[0]
        
        # Try to find value after "value:" or "answer:"
        patterns = [
            r'value[:\s]+([^\n,]+)',
            r'answer[:\s]+([^\n,]+)',
            r'fill[:\s]+([^\n,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _fallback_decision(self, purpose: str, options: List[str]) -> Optional[str]:
        """Generate fallback value when AI fails."""
        fallbacks = {
            'name': 'John Doe',
            'email': 'example@email.com',
            'course': 'Computer Science',
            'marital_status': options[0] if options else 'Yes',
            'choice': options[0] if options else None,
            'date': '1990-01-01',
            'text': 'Sample text'
        }
        
        return fallbacks.get(purpose, options[0] if options else 'N/A')
    
    def decide_filling_strategy(
        self,
        form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Decide overall strategy for filling the form.
        
        Args:
            form_data: Complete form perception data
            
        Returns:
            Filling strategy
        """
        fields = form_data.get('fields', [])
        
        strategy = {
            'order': list(range(len(fields))),
            'dependencies': [],
            'notes': []
        }
        
        # Analyze field dependencies
        for i, field_class in enumerate(fields):
            purpose = field_class.get('purpose', '')
            if purpose == 'course':
                strategy['notes'].append(f"Field {i}: Course field - ensure text value, not date")
        
        return strategy


