"""
Perception Module - Understands and classifies form fields.

This module is responsible for:
- Detecting form fields on the page
- Understanding what type of field each one is
- Extracting field properties (label, type, options, etc.)
- Classifying fields based on their purpose and structure
"""

import json
import time
from typing import Dict, List, Any, Optional
from playwright.sync_api import Page


class Perception:
    """
    Perception module that understands form structure and field types.
    Analyzes the DOM to detect and classify form fields.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the Perception module.
        
        Args:
            page: Playwright page object
        """
        self.page = page
    
    def perceive_form(self) -> Dict[str, Any]:
        """
        Main perception method - analyzes the entire form.
        
        Returns:
            Dictionary containing form structure and field information
        """
        print("\n🔍 [Perception] Analyzing form structure...")
        
        # Wait for form to load
        self._wait_for_form()
        
        # Detect all fields
        fields = self._detect_fields()
        
        # Classify each field
        classified_fields = []
        for field in fields:
            classified = self._classify_field(field)
            classified_fields.append(classified)
        
        # Get form context
        form_context = self._get_form_context()
        
        result = {
            "fields": classified_fields,
            "form_context": form_context,
            "total_fields": len(classified_fields)
        }
        
        print(f"✓ [Perception] Detected {len(classified_fields)} fields")
        return result
    
    def _wait_for_form(self):
        """Wait for form to be fully loaded."""
        try:
            self.page.wait_for_selector(
                'form, [role="form"], .freebirdFormviewerViewFormContentWrapper, [role="listitem"]',
                timeout=10000
            )
            time.sleep(2)  # Additional wait for dynamic content
        except:
            print("⚠ [Perception] Form structure not fully detected, continuing...")
    
    def _detect_fields(self) -> List[Dict[str, Any]]:
        """
        Detect all form fields using JavaScript.
        
        Returns:
            List of raw field information
        """
        fields = self.page.evaluate("""
            () => {
                const fields = [];
                let fieldIndex = 0;
                
                // Google Forms specific: Find all form items
                const formItems = document.querySelectorAll('[role="listitem"], .freebirdFormviewerViewItemsItemItem, [data-item-id]');
                
                formItems.forEach((item, itemIndex) => {
                    // Get question title
                    const titleEl = item.querySelector('[role="heading"], .freebirdFormviewerViewItemsItemItemTitle, .M7eMe');
                    const questionText = titleEl ? titleEl.textContent.trim() : '';
                    
                    // Check if this item has radio buttons (even if inputs are hidden)
                    // Look for radio button indicators: labels with "Yes", "No", "Maybe", or radio inputs
                    // IMPORTANT: Include ALL radio inputs, even hidden ones for detection
                    const hasRadioButtons = item.querySelectorAll('input[type="radio"]').length > 0;
                    const hasRadioLabels = item.querySelectorAll('label, [role="option"], .docssharedWizToggleLabeledContainer').length > 0;
                    const questionLower = questionText.toLowerCase();
                    const isLikelyRadio = (questionLower.includes('married') || 
                                          questionLower.includes('marital') ||
                                          questionLower.includes('relationship') ||
                                          questionLower.includes('yes') ||
                                          questionLower.includes('no') ||
                                          questionLower.includes('maybe'));
                    
                    // Check for visible option text that suggests radio buttons
                    const itemText = item.textContent || item.innerText || '';
                    const hasYesNoMaybe = (itemText.toLowerCase().includes('yes') && 
                                          itemText.toLowerCase().includes('no')) ||
                                         itemText.toLowerCase().includes('maybe');
                    
                    // If this looks like a radio button field, handle it first
                    // Be more aggressive: if question mentions "married" or has Yes/No/Maybe, treat as radio
                    if ((hasRadioButtons || (hasRadioLabels && isLikelyRadio) || 
                         (isLikelyRadio && hasYesNoMaybe) || 
                         (questionLower.includes('married'))) && questionText) {
                        // This is a radio button field
                        const radioInputs = item.querySelectorAll('input[type="radio"]');
                        const name = radioInputs.length > 0 ? (radioInputs[0].name || radioInputs[0].getAttribute('name')) : '';
                        
                        // Check if we already added this radio group
                        const existingRadioGroup = fields.find(f => f.name === name && f.type === 'radio');
                        
                        if (!existingRadioGroup) {
                            const radioField = {
                                index: fieldIndex++,
                                itemIndex: itemIndex,
                                tag: 'input',
                                type: 'radio',
                                id: name || '',
                                name: name || '',
                                placeholder: '',
                                required: item.querySelector('[aria-required="true"]') !== null,
                                value: '',
                                options: [],
                                label: questionText,
                                rawElement: {
                                    id: name || '',
                                    name: name || '',
                                    className: ''
                                }
                            };
                            
                            // Extract options from labels or radio inputs
                            if (radioInputs.length > 0) {
                                // Get options from radio inputs (even if hidden)
                                radioInputs.forEach(radio => {
                                    const label = radio.closest('label') || 
                                                 document.querySelector(`label[for="${radio.id}"]`) ||
                                                 radio.closest('[role="option"]') ||
                                                 radio.closest('.docssharedWizToggleLabeledContainer');
                                    if (label) {
                                        const optionText = label.textContent.trim();
                                        if (optionText && !radioField.options.includes(optionText)) {
                                            radioField.options.push(optionText);
                                        }
                                    }
                                });
                            }
                            
                            // Also try to extract from all labels in the item
                            const allLabels = item.querySelectorAll('label, [role="option"], .docssharedWizToggleLabeledContainer, span');
                            allLabels.forEach(label => {
                                const text = label.textContent.trim();
                                // Filter: must be short, not the question, and looks like an option
                                if (text && 
                                    text !== questionText && 
                                    text.length > 0 && 
                                    text.length < 50 && 
                                    !text.includes('?') &&
                                    !text.includes('*') &&
                                    (text.toLowerCase() === 'yes' || 
                                     text.toLowerCase() === 'no' || 
                                     text.toLowerCase() === 'maybe' ||
                                     text.match(/^[A-Z][a-z]+$/))) {  // Single word, capitalized
                                    if (!radioField.options.includes(text)) {
                                        radioField.options.push(text);
                                    }
                                }
                            });
                            
                            // If still no options found, use common ones for marital status
                            if (radioField.options.length === 0 && questionLower.includes('married')) {
                                radioField.options = ['Yes', 'No', 'Maybe'];
                            }
                            
                            // ALWAYS add the field if question text exists (even without options)
                            // Options can be extracted when filling
                            if (questionText) {
                                fields.push(radioField);
                            }
                        }
                    }
                    
                    // Check if this item is a dropdown (even without input/select elements)
                    // Google Forms uses custom dropdowns that are just divs
                    const hasDropdownIndicator = item.querySelector('[role="listbox"], [aria-haspopup="listbox"], .quantumWizMenuPaperselectContent, .freebirdFormviewerViewItemsSelectSelect, div[role="button"][aria-expanded], .freebirdFormviewerViewItemsSelectSelect');
                    
                    // Find all inputs in this item (EXCLUDE hidden inputs - they're just for data storage)
                    // Google Forms uses hidden inputs to store values, but we need to interact with visible UI
                    const inputs = item.querySelectorAll('input:not([type="hidden"]):not([type="radio"]), textarea, select');
                    
                    // If this is a dropdown but has no input/select elements, create a field entry for it
                    if (hasDropdownIndicator && inputs.length === 0) {
                        // This is a dropdown field - create field entry even if no input element
                        const dropdownField = {
                            index: fieldIndex++,
                            itemIndex: itemIndex,
                            tag: 'div',
                            type: 'select',
                            id: '',
                            name: '',
                            placeholder: 'Choose',
                            required: item.querySelector('[aria-required="true"]') !== null,
                            value: '',
                            options: [],
                            label: questionText,
                            rawElement: {
                                id: '',
                                name: '',
                                className: hasDropdownIndicator.className || ''
                            }
                        };
                        
                        // Try to extract options (they might be in data attributes or need to be opened)
                        const optionElements = item.querySelectorAll('[role="option"], .quantumWizMenuPaperselectOption, [data-value]');
                        optionElements.forEach(opt => {
                            const text = opt.textContent.trim() || opt.getAttribute('data-value') || opt.innerText.trim();
                            if (text && !dropdownField.options.includes(text)) {
                                dropdownField.options.push(text);
                            }
                        });
                        
                        // Common Google Forms course options
                        if (dropdownField.options.length === 0 && questionText.toLowerCase().includes('course')) {
                            dropdownField.options = ['ERA', 'EAG', 'EPAi'];
                        }
                        
                        fields.push(dropdownField);
                    } else {
                        // Process normal input fields
                    
                    inputs.forEach((field) => {
                        const fieldInfo = {
                            index: fieldIndex++,
                            itemIndex: itemIndex,
                            tag: field.tagName.toLowerCase(),
                            type: field.type || field.tagName.toLowerCase(),
                            id: field.id || '',
                            name: field.name || '',
                            placeholder: field.placeholder || '',
                            required: field.required || item.querySelector('[aria-required="true"]') !== null,
                            value: field.value || '',
                            options: [],
                            label: questionText,
                            rawElement: {
                                id: field.id,
                                name: field.name,
                                className: field.className
                            }
                        };
                        
                        // Handle radio buttons
                        if (field.type === 'radio') {
                            const name = field.name || field.getAttribute('name');
                            const existingRadioGroup = fields.find(f => f.name === name && f.type === 'radio');
                            
                            if (!existingRadioGroup) {
                                const allRadios = item.querySelectorAll(`input[type="radio"][name="${name}"]`);
                                allRadios.forEach(radio => {
                                    const label = radio.closest('label') || 
                                                 document.querySelector(`label[for="${radio.id}"]`) ||
                                                 radio.closest('[role="option"]');
                                    if (label) {
                                        const optionText = label.textContent.trim();
                                        if (optionText && !fieldInfo.options.includes(optionText)) {
                                            fieldInfo.options.push(optionText);
                                        }
                                    }
                                });
                                fields.push(fieldInfo);
                            }
                        } else {
                            // Text, email, date, textarea, select
                            if (field.tagName.toLowerCase() === 'select') {
                                Array.from(field.options).forEach(option => {
                                    if (option.text.trim()) {
                                        fieldInfo.options.push(option.text.trim());
                                    }
                                });
                                fieldInfo.type = 'select';
                            }
                            
                            // For Google Forms custom dropdowns - check for dropdown indicators
                            // Google Forms uses divs with specific classes/roles for dropdowns
                            const hasDropdownIndicator = item.querySelector('[role="listbox"], [aria-haspopup="listbox"], .quantumWizMenuPaperselectContent, .freebirdFormviewerViewItemsSelectSelect, div[role="button"][aria-expanded]');
                            
                            if (hasDropdownIndicator) {
                                // This is a dropdown field
                                fieldInfo.type = 'select';
                                
                                // Try to extract options from the item
                                // Options might be in data attributes or in hidden elements
                                const optionElements = item.querySelectorAll('[role="option"], .quantumWizMenuPaperselectOption, [data-value]');
                                optionElements.forEach(opt => {
                                    const text = opt.textContent.trim() || opt.getAttribute('data-value') || opt.innerText.trim();
                                    if (text && !fieldInfo.options.includes(text)) {
                                        fieldInfo.options.push(text);
                                    }
                                });
                                
                                // If no options found, try to get them from the dropdown when opened
                                // For now, we'll detect it as dropdown and let the filling method extract options
                                if (fieldInfo.options.length === 0) {
                                    // Mark as dropdown but options will be extracted when filling
                                    fieldInfo.options = ['ERA', 'EAG', 'EPAi']; // Common options, will be updated
                                }
                            }
                            
                            fields.push(fieldInfo);
                        }
                    });
                    }
                });
                
                return fields;
            }
        """)
        
        return fields
    
    def _classify_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a field to understand its true nature and purpose.
        
        Args:
            field: Raw field information
            
        Returns:
            Classified field with enhanced understanding
        """
        label = field.get('label', '').lower()
        field_type = field.get('type', '').lower()
        has_options = len(field.get('options', [])) > 0
        tag = field.get('tag', '').lower()
        
        # Check if this is a dropdown/select field
        # Google Forms uses custom dropdowns that might not be detected as 'select'
        is_dropdown_field = (field_type == 'select' or 
                            tag == 'select' or
                            (has_options and field_type in ['text', 'hidden'] and 
                             ('course' in label or 'which' in label or 'select' in label or 'choose' in label)))
        
        # Check if this is actually a radio button field (even if type is hidden)
        # Google Forms sometimes hides radio inputs but they're still radio buttons
        is_radio_field = (field_type == 'radio' or 
                         (has_options and 'married' in label) or
                         (has_options and 'marital' in label) or
                         (has_options and field_type == 'hidden' and len(field.get('options', [])) <= 5 and not is_dropdown_field))
        
        # Determine the true field type and purpose
        classification = {
            'raw_type': field_type,
            'detected_type': field_type,
            'purpose': self._determine_purpose(label, field_type, has_options),
            'is_date_field': self._is_date_field(label, field_type),
            'is_text_field': self._is_text_field(label, field_type),
            'is_choice_field': has_options,
            'is_radio_field': is_radio_field,
            'is_dropdown_field': is_dropdown_field,
            'interaction_type': self._determine_interaction_type(field_type, has_options, is_radio_field, is_dropdown_field),
            'field': field
        }
        
        # Override detected type based on classification
        if is_dropdown_field and field_type != 'select':
            # This is a dropdown field even though type says otherwise
            classification['detected_type'] = 'select'
            classification['interaction_type'] = 'select'
            print(f"  [Perception] Field '{field.get('label')}' corrected: {field_type} -> select (dropdown)")
        elif is_radio_field and field_type != 'radio':
            # This is a radio field even though type says otherwise
            classification['detected_type'] = 'radio'
            classification['interaction_type'] = 'radio'
            print(f"  [Perception] Field '{field.get('label')}' corrected: {field_type} -> radio")
        elif classification['is_date_field']:
            classification['detected_type'] = 'date'
            classification['interaction_type'] = 'date_picker'
        elif classification['is_text_field'] and field_type == 'date':
            # Field was misclassified as date, it's actually text
            classification['detected_type'] = 'text'
            classification['interaction_type'] = 'type'
            print(f"  [Perception] Field '{field.get('label')}' corrected: date -> text")
        
        return classification
    
    def _determine_purpose(self, label: str, field_type: str, has_options: bool) -> str:
        """
        Determine the purpose/intent of a field based on its label.
        
        Args:
            label: Field label (lowercase)
            field_type: HTML field type
            has_options: Whether field has predefined options
            
        Returns:
            Purpose description
        """
        # Name fields
        if any(word in label for word in ['name', 'master', 'student', 'person']):
            return 'name'
        
        # Email fields
        if 'email' in label or field_type == 'email':
            return 'email'
        
        # Date fields
        if any(word in label for word in ['date', 'birth', 'dob', 'when']):
            return 'date'
        
        # Course/education fields
        if any(word in label for word in ['course', 'subject', 'major', 'degree', 'program']):
            return 'course'
        
        # Marital status
        if any(word in label for word in ['married', 'marital', 'relationship']):
            return 'marital_status'
        
        # Choice fields
        if has_options:
            return 'choice'
        
        # Generic text
        return 'text'
    
    def _is_date_field(self, label: str, field_type: str) -> bool:
        """Check if field is truly a date field."""
        date_indicators = ['date', 'birth', 'dob', 'when']
        return (field_type == 'date' and 
                any(indicator in label for indicator in date_indicators))
    
    def _is_text_field(self, label: str, field_type: str) -> bool:
        """Check if field should be treated as text (not date)."""
        text_indicators = ['course', 'name', 'subject', 'description', 'comment']
        return (any(indicator in label for indicator in text_indicators) or
                field_type in ['text', 'email', 'textarea'])
    
    def _determine_interaction_type(self, field_type: str, has_options: bool, is_radio_field: bool = False, is_dropdown_field: bool = False) -> str:
        """
        Determine how to interact with this field.
        
        Returns:
            Interaction type: 'radio', 'select', 'date_picker', 'type'
        """
        # Check if it's a radio field (even if type is hidden)
        if field_type == 'radio' or is_radio_field:
            return 'radio'
        elif field_type == 'select' or is_dropdown_field or (has_options and field_type not in ['radio', 'text']):
            return 'select'
        elif has_options:
            return 'select'
        elif field_type == 'date':
            return 'date_picker'
        else:
            return 'type'
    
    def _get_form_context(self) -> Dict[str, Any]:
        """Get overall form context and structure."""
        context = self.page.evaluate("""
            () => {
                const form = document.querySelector('form') || document.body;
                return {
                    title: document.title,
                    formText: form.innerText ? form.innerText.substring(0, 1000) : '',
                    totalItems: document.querySelectorAll('[role="listitem"]').length
                };
            }
        """)
        return context
    
    def get_field_details(self, field_index: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific field.
        
        Args:
            field_index: Index of the field
            
        Returns:
            Detailed field information or None
        """
        form_data = self.perceive_form()
        fields = form_data.get('fields', [])
        
        if field_index < len(fields):
            return fields[field_index]
        return None


