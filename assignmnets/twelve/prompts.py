"""
Prompt templates for the browser agent.
This file separates prompting logic from the main code for better maintainability.
"""

# System prompt for Gemini to understand its role
SYSTEM_PROMPT = """You are an intelligent browser agent that helps fill out web forms.
Your task is to analyze form fields and provide structured instructions on how to fill them.

When analyzing a form, you should:
1. Identify all form fields and their types (text, dropdown, radio, checkbox, etc.)
2. Understand what information is required
3. Provide clear, actionable instructions for filling each field
4. Consider the context and relationships between fields

Return your analysis in a structured format that can be easily parsed."""

# Prompt for analyzing the form structure
FORM_ANALYSIS_PROMPT = """Analyze the following form structure and provide instructions for filling it out.

Form HTML/Structure:
{form_structure}

Available form fields detected:
{form_fields}

Please provide a JSON response with the following structure:
{{
    "fields": [
        {{
            "field_id": "unique identifier for the field",
            "field_type": "text|dropdown|radio|checkbox|date",
            "field_label": "label or description of the field",
            "instructions": "how to fill this field",
            "value": "the value to fill (if determinable)",
            "required": true/false
        }}
    ],
    "strategy": "overall strategy for filling the form"
}}

If you cannot determine a value, use null for the "value" field."""

# Prompt for determining what value to fill in a specific field
FIELD_VALUE_PROMPT = """Given the following form field information, determine what value should be filled in.

Field Label: {field_label}
Field Type: {field_type}
Field Options: {field_options}
Is Required: {is_required}
Context: {context}

IMPORTANT RULES:
1. If the field type is "email", provide a VALID EMAIL ADDRESS (e.g., "john.doe@example.com", "user@email.com"). NEVER use placeholder text like "TEXT" or "email@example.com" - use a realistic email.
2. If the field type is "text" (not email), provide a TEXT value (NOT a date format like mm/dd/yyyy)
3. Only use date formats (mm/dd/yyyy, yyyy-mm-dd) if the field type is explicitly "date" AND the label mentions date/birth/dob
4. For "course" fields, provide a course name (e.g., "Computer Science", "Mathematics"), NOT a date
5. For dropdown or radio buttons, the value MUST match one of the available options exactly
6. For radio button slecet one from available options eg: "Yes" or "No", or this or that, 1/2/3/4/5/6/7/8/9/10, etc.
7. NEVER use placeholder values like "TEXT", "EXAMPLE", "PLACEHOLDER" - always provide realistic, actual values

Provide a JSON response:
{{
    "value": "the value to fill",
    "reasoning": "why this value was chosen"
}}

If this is a dropdown or radio button, make sure the value matches one of the available options exactly."""

# Prompt for form filling strategy
FORM_FILLING_STRATEGY = """You are about to fill out a Google Form. Here's what you know:

Form URL: {form_url}
Form Fields: {form_fields_summary}

Provide step-by-step instructions for filling this form. Consider:
1. The order of fields
2. Dependencies between fields
3. Required vs optional fields
4. Validation rules

Return instructions in a clear, actionable format."""

# Error handling prompt
ERROR_HANDLING_PROMPT = """An error occurred while filling the form:

Error: {error_message}
Current Field: {current_field}
Form State: {form_state}

Suggest how to recover from this error and continue filling the form."""

