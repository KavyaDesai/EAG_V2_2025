"""
Browser agent for automating form filling using Playwright.
Handles browser interactions, form field detection, and form submission.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv
from gemini_client import GeminiClient
from perception import Perception
from decision import Decision

load_dotenv()


class BrowserAgent:
    """Browser automation agent for filling web forms."""
    
    def __init__(
        self,
        headless: bool = False,
        timeout: int = 30000,
        gemini_client: Optional[GeminiClient] = None
    ):
        """
        Initialize the browser agent.
        
        Args:
            headless: Run browser in headless mode
            timeout: Timeout for browser operations (milliseconds)
            gemini_client: Gemini client instance for AI decision-making
        """
        self.headless = headless
        self.timeout = timeout
        self.gemini_client = gemini_client or GeminiClient()
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Initialize Perception and Decision modules (will be set after browser starts)
        self.perception: Optional[Perception] = None
        self.decision: Optional[Decision] = None
        
    def start_browser(self):
        """Start the browser and create a new page."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--start-maximized', '--disable-blink-features=AutomationControlled']
        )
        # Create context with user data (not incognito)
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        # Remove webdriver property to avoid detection
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Initialize Perception and Decision modules
        self.perception = Perception(self.page)
        self.decision = Decision(self.gemini_client)
        
    def close_browser(self):
        """Close the browser and cleanup."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
    
    def navigate_to_form(self, url: str):
        """
        Navigate to the form URL.
        
        Args:
            url: URL of the form to fill
        """
        if not self.page:
            raise RuntimeError("Browser not started. Call start_browser() first.")
        
        print(f"Navigating to: {url}")
        self.page.goto(url, wait_until='networkidle', timeout=60000)
        time.sleep(3)  # Wait for form to fully load
        
        # Wait for form content to be visible
        try:
            self.page.wait_for_selector('form, [role="form"], .freebirdFormviewerViewFormContentWrapper, [role="listitem"]', timeout=10000)
            print("✓ Form loaded successfully")
        except:
            print("⚠ Form structure not detected, continuing anyway...")
        
    def detect_form_fields(self) -> List[Dict[str, Any]]:
        """
        Detect all form fields on the page.
        
        Returns:
            List of dictionaries containing field information
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        
        # Wait for form to load
        self.page.wait_for_selector('form, [role="form"], .freebirdFormviewerViewFormContentWrapper', timeout=10000)
        time.sleep(2)  # Additional wait for dynamic content
        
        # Get form structure using JavaScript - improved for Google Forms
        fields = self.page.evaluate("""
            () => {
                const fields = [];
                let fieldIndex = 0;
                
                // Google Forms specific: Find all form items
                const formItems = document.querySelectorAll('[role="listitem"], .freebirdFormviewerViewItemsItemItem, [data-item-id]');
                
                formItems.forEach((item, itemIndex) => {
                    // Find input/textarea/select within this item
                    const inputs = item.querySelectorAll('input[type="text"], input[type="email"], input[type="date"], textarea, input[type="radio"], select');
                    
                    // Get question title
                    const titleEl = item.querySelector('[role="heading"], .freebirdFormviewerViewItemsItemItemTitle, .M7eMe');
                    const questionText = titleEl ? titleEl.textContent.trim() : '';
                    
                    // Handle text inputs
                    inputs.forEach((field) => {
                        if (field.type === 'radio') {
                            // Radio buttons - group them
                            const name = field.name || field.getAttribute('name');
                            const existingRadioGroup = fields.find(f => f.name === name && f.type === 'radio');
                            
                            if (!existingRadioGroup) {
                                // Get all radio options for this group
                                const allRadios = item.querySelectorAll(`input[type="radio"][name="${name}"]`);
                                const options = [];
                                allRadios.forEach(radio => {
                                    const label = radio.closest('label') || 
                                                 document.querySelector(`label[for="${radio.id}"]`) ||
                                                 radio.closest('[role="option"]');
                                    if (label) {
                                        const optionText = label.textContent.trim();
                                        if (optionText && !options.includes(optionText)) {
                                            options.push(optionText);
                                        }
                                    }
                                });
                                
                                fields.push({
                                    index: fieldIndex++,
                                    tag: 'input',
                                    type: 'radio',
                                    id: name || '',
                                    name: name || '',
                                    label: questionText,
                                    required: field.required || item.querySelector('[aria-required="true"]') !== null,
                                    options: options,
                                    itemElement: true
                                });
                            }
                        } else {
                            // Text, email, date, textarea, select
                            let fieldType = field.type || field.tagName.toLowerCase();
                            
                            // Smart type detection: Don't mark as date unless it's actually a date field
                            // Check if question text suggests it's a date field
                            const isDateField = questionText.toLowerCase().includes('date') || 
                                              questionText.toLowerCase().includes('birth') ||
                                              questionText.toLowerCase().includes('dob') ||
                                              questionText.toLowerCase().includes('when') ||
                                              (fieldType === 'date');
                            
                            // If it's not clearly a date field, treat as text
                            if (fieldType === 'date' && !isDateField) {
                                fieldType = 'text';
                            }
                            
                            const fieldInfo = {
                                index: fieldIndex++,
                                tag: field.tagName.toLowerCase(),
                                type: fieldType,
                                id: field.id || '',
                                name: field.name || '',
                                placeholder: field.placeholder || '',
                                required: field.required || item.querySelector('[aria-required="true"]') !== null,
                                value: field.value || '',
                                options: [],
                                label: questionText,
                                itemElement: true
                            };
                            
                            // Get options for select/dropdown
                            if (field.tagName.toLowerCase() === 'select') {
                                Array.from(field.options).forEach(option => {
                                    if (option.text.trim()) {
                                        fieldInfo.options.push(option.text.trim());
                                    }
                                });
                            }
                            
                            // For Google Forms dropdowns (custom select)
                            if (field.hasAttribute('role') && field.getAttribute('role') === 'listbox') {
                                const options = item.querySelectorAll('[role="option"]');
                                options.forEach(opt => {
                                    const text = opt.textContent.trim();
                                    if (text) fieldInfo.options.push(text);
                                });
                            }
                            
                            fields.push(fieldInfo);
                        }
                    });
                });
                
                // Fallback: if no items found, try standard approach
                if (fields.length === 0) {
                    document.querySelectorAll('input, textarea, select').forEach((field, index) => {
                        const fieldInfo = {
                            index: index,
                            tag: field.tagName.toLowerCase(),
                            type: field.type || field.tagName.toLowerCase(),
                            id: field.id || '',
                            name: field.name || '',
                            placeholder: field.placeholder || '',
                            required: field.required || false,
                            value: field.value || '',
                            options: []
                        };
                        
                        let label = '';
                        if (field.id) {
                            const labelEl = document.querySelector(`label[for="${field.id}"]`);
                            if (labelEl) label = labelEl.textContent.trim();
                        }
                        if (!label) {
                            const parent = field.closest('[role="group"], .freebirdFormviewerViewItemsItemItem');
                            if (parent) {
                                const labelEl = parent.querySelector('[role="heading"], .freebirdFormviewerViewItemsItemItemTitle');
                                if (labelEl) label = labelEl.textContent.trim();
                            }
                        }
                        fieldInfo.label = label;
                        fields.push(fieldInfo);
                    });
                }
                
                return fields;
            }
        """)
        
        print(f"Detected fields: {json.dumps(fields, indent=2)}")
        return fields
    
    def get_form_structure(self) -> str:
        """
        Get a text representation of the form structure.
        
        Returns:
            String representation of form HTML/structure
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        
        structure = self.page.evaluate("""
            () => {
                const form = document.querySelector('form') || document.body;
                return form.innerText || form.textContent || '';
            }
        """)
        
        return structure[:5000]  # Limit length
    
    def fill_text_field(self, field_selector: str, value: str):
        """
        Fill a text input field.
        
        Args:
            field_selector: CSS selector or field identifier
            value: Value to fill
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        
        try:
            # Try multiple selector strategies
            selectors = [
                f'input[placeholder*="{field_selector}"]',
                f'textarea[placeholder*="{field_selector}"]',
                f'input[name*="{field_selector}"]',
                f'textarea[name*="{field_selector}"]',
                field_selector
            ]
            
            filled = False
            for selector in selectors:
                try:
                    element = self.page.query_selector(selector)
                    if element:
                        element.fill(value)
                        filled = True
                        print(f"✓ Filled field '{field_selector}' with '{value}'")
                        break
                except:
                    continue
            
            if not filled:
                # Try by index
                try:
                    inputs = self.page.query_selector_all('input, textarea')
                    index = int(field_selector) if field_selector.isdigit() else None
                    if index is not None and index < len(inputs):
                        inputs[index].fill(value)
                        filled = True
                        print(f"✓ Filled field at index {index} with '{value}'")
                except:
                    pass
            
            if not filled:
                print(f"⚠ Could not fill field: {field_selector}")
                
        except Exception as e:
            print(f"Error filling text field {field_selector}: {e}")
    
    def fill_dropdown_google_forms(self, field_index: int, value: str, field_label: str):
        """Fill Google Forms dropdown."""
        try:
            print(f"  Attempting to fill dropdown '{field_label}' with value '{value}'")
            
            # Find the form item by index
            form_items = self.page.query_selector_all('[role="listitem"], .freebirdFormviewerViewItemsItemItem')
            if field_index >= len(form_items):
                print(f"  ⚠ Field index {field_index} out of range (found {len(form_items)} items)")
                # Try finding by label text as fallback
                try:
                    item = self.page.query_selector(f'text="{field_label}"')
                    if item:
                        item = item.evaluate_handle("""
                            (el) => {
                                let parent = el;
                                for (let i = 0; i < 5; i++) {
                                    parent = parent.parentElement;
                                    if (parent && (parent.hasAttribute('role') && parent.getAttribute('role') === 'listitem' || 
                                        parent.classList.contains('freebirdFormviewerViewItemsItemItem'))) {
                                        return parent;
                                    }
                                }
                                return null;
                            }
                        """)
                except:
                    item = None
            else:
                item = form_items[field_index]
            
            if not item:
                print(f"  ⚠ Could not find form item for dropdown '{field_label}'")
                return
            
            item.scroll_into_view_if_needed()
            time.sleep(0.5)
            
            # IMPORTANT: Don't look for hidden inputs - look for the VISIBLE dropdown trigger
            # Google Forms uses hidden inputs to store values, but we need to click the visible UI
            dropdown = None
            dropdown_selectors = [
                'div[role="button"][aria-expanded]',  # Dropdown button (visible)
                'div[role="button"]:not([type="hidden"])',  # Any visible button
                '.quantumWizMenuPaperselectDropDown',  # Google Forms dropdown class
                '.freebirdFormviewerViewItemsSelectSelect',  # Google Forms select class
                '[aria-haspopup="listbox"]',  # Element that opens listbox
                '.quantumWizMenuPaperselectContent',  # Dropdown content area
                '[role="listbox"]'  # The listbox itself
            ]
            
            # Try to find visible dropdown trigger (NOT hidden inputs)
            for selector in dropdown_selectors:
                try:
                    # Only get visible elements, not hidden ones
                    elements = item.query_selector_all(selector)
                    for elem in elements:
                        # Check if element is visible (not hidden)
                        is_visible = elem.evaluate("""
                            (el) => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       style.opacity !== '0' &&
                                       el.offsetWidth > 0 && 
                                       el.offsetHeight > 0;
                            }
                        """)
                        if is_visible:
                            dropdown = elem
                            print(f"  Found visible dropdown using selector: {selector}")
                            break
                    if dropdown:
                        break
                except:
                    continue
            
            # If still not found, try finding any clickable div in the item (but not hidden inputs)
            if not dropdown:
                try:
                    # Get all clickable elements, filter out hidden ones
                    clickables = item.query_selector_all('div[role="button"], button, .quantumWizMenuPaperselectDropDown')
                    for clickable in clickables:
                        is_visible = clickable.evaluate("""
                            (el) => {
                                const style = window.getComputedStyle(el);
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       el.offsetWidth > 0 && 
                                       el.offsetHeight > 0;
                            }
                        """)
                        if is_visible:
                            dropdown = clickable
                            print(f"  Found visible clickable dropdown trigger")
                            break
                except:
                    pass
            
            if dropdown:
                # Click to open dropdown
                dropdown.scroll_into_view_if_needed()
                time.sleep(0.3)
                dropdown.click()
                print(f"  Clicked dropdown, waiting for options to appear...")
                time.sleep(1.5)  # Wait for dropdown menu to appear
                
                # Wait for options to be visible
                try:
                    self.page.wait_for_selector('[role="option"], .quantumWizMenuPaperselectOption', timeout=3000)
                except:
                    pass
                
                # Find and click the option - try multiple strategies
                option_found = False
                
                # Strategy 1: Use locator with has-text
                try:
                    option_locator = self.page.locator(f'[role="option"]:has-text("{value}")')
                    count = option_locator.count()
                    if count > 0:
                        option_locator.first.scroll_into_view_if_needed()
                        time.sleep(0.2)
                        option_locator.first.click()
                        option_found = True
                        print(f"  ✓ Selected option using locator strategy")
                except Exception as e:
                    print(f"  Locator strategy failed: {e}")
                
                # Strategy 2: Find all options and match by text
                if not option_found:
                    try:
                        options = self.page.query_selector_all('[role="option"], .quantumWizMenuPaperselectOption, .exportSelectPopupOption')
                        print(f"  Found {len(options)} options in dropdown")
                        
                        for opt in options:
                            try:
                                opt_text = opt.text_content() or opt.inner_text() or ""
                                opt_text = opt_text.strip()
                                
                                # Check for exact match or partial match
                                if opt_text.lower() == value.lower() or value.lower() in opt_text.lower():
                                    opt.scroll_into_view_if_needed()
                                    time.sleep(0.2)
                                    opt.click()
                                    option_found = True
                                    print(f"  ✓ Selected option: '{opt_text}'")
                                    break
                            except Exception as e:
                                continue
                    except Exception as e:
                        print(f"  Option search failed: {e}")
                
                # Strategy 3: Use JavaScript to find and click
                if not option_found:
                    try:
                        result = self.page.evaluate(f"""
                            (searchValue) => {{
                                const options = document.querySelectorAll('[role="option"], .quantumWizMenuPaperselectOption');
                                for (let opt of options) {{
                                    const text = opt.textContent || opt.innerText || '';
                                    if (text.toLowerCase().includes(searchValue.toLowerCase())) {{
                                        opt.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                        """, value)
                        
                        if result:
                            option_found = True
                            print(f"  ✓ Selected option using JavaScript")
                    except Exception as e:
                        print(f"  JavaScript strategy failed: {e}")
                
                if option_found:
                    time.sleep(0.5)  # Wait for selection to register
                    print(f"✓ Selected '{value}' in dropdown '{field_label}'")
                    return
                else:
                    print(f"⚠ Option '{value}' not found in dropdown. Available options may differ.")
                    # List available options for debugging
                    try:
                        options = self.page.query_selector_all('[role="option"]')
                        available = [opt.text_content().strip() for opt in options[:5]]
                        print(f"  First few available options: {available}")
                    except:
                        pass
            else:
                print(f"⚠ Dropdown trigger not found for field: {field_label}")
                # Try alternative: direct select element
                try:
                    select = item.query_selector('select')
                    if select:
                        self.page.select_option(f'select', label=value)
                        print(f"✓ Selected '{value}' using select element")
                        return
                except:
                    pass
                    
        except Exception as e:
            print(f"Error filling dropdown: {e}")
            import traceback
            traceback.print_exc()
    
    def fill_dropdown(self, field_selector: str, value: str):
        """
        Fill a dropdown/select field (legacy method).
        
        Args:
            field_selector: CSS selector or field identifier
            value: Value to select
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        
        try:
            # Try to find select element
            select = self.page.query_selector(f'select{field_selector}')
            if select:
                self.page.select_option(f'select{field_selector}', label=value)
                print(f"✓ Selected '{value}' in dropdown '{field_selector}'")
                return
            
            print(f"⚠ Could not select '{value}' in dropdown: {field_selector}")
            
        except Exception as e:
            print(f"Error filling dropdown {field_selector}: {e}")
    
    def fill_date_field_google_forms(self, field_index: int, value: str, field_label: str):
        """Fill Google Forms date field."""
        try:
            print(f"  Attempting to fill date field '{field_label}' with value '{value}'")
            
            # Find the form item
            form_items = self.page.query_selector_all('[role="listitem"], .freebirdFormviewerViewItemsItemItem')
            if field_index >= len(form_items):
                print(f"  ⚠ Field index {field_index} out of range")
                return
            
            item = form_items[field_index]
            item.scroll_into_view_if_needed()
            time.sleep(0.5)
            
            # Google Forms date fields can be:
            # 1. Single input with type="date"
            # 2. Multiple inputs (day, month, year)
            # 3. Custom date picker
            
            # Try to find date input
            date_input = item.query_selector('input[type="date"]')
            if date_input:
                date_input.scroll_into_view_if_needed()
                time.sleep(0.3)
                date_input.click()
                time.sleep(0.3)
                date_input.fill(value)
                print(f"✓ Filled date field '{field_label}' with '{value}'")
                return
            
            # Try separate day/month/year inputs
            day_input = item.query_selector('input[aria-label*="Day"], input[aria-label*="day"]')
            month_input = item.query_selector('input[aria-label*="Month"], input[aria-label*="month"]')
            year_input = item.query_selector('input[aria-label*="Year"], input[aria-label*="year"]')
            
            if day_input and month_input and year_input:
                # Parse date value (format: YYYY-MM-DD or DD/MM/YYYY or MM/DD/YYYY)
                try:
                    if '-' in value:
                        parts = value.split('-')
                        if len(parts) == 3:
                            year, month, day = parts
                        else:
                            day, month, year = parts
                    elif '/' in value:
                        parts = value.split('/')
                        if len(parts) == 3:
                            # Try to determine format
                            if len(parts[0]) == 4:  # YYYY/MM/DD
                                year, month, day = parts
                            else:  # DD/MM/YYYY or MM/DD/YYYY
                                month, day, year = parts
                        else:
                            print(f"  ⚠ Could not parse date: {value}")
                            return
                    
                    # Fill the inputs
                    day_input.scroll_into_view_if_needed()
                    time.sleep(0.2)
                    day_input.click()
                    time.sleep(0.2)
                    day_input.fill(day)
                    
                    month_input.click()
                    time.sleep(0.2)
                    month_input.fill(month)
                    
                    year_input.click()
                    time.sleep(0.2)
                    year_input.fill(year)
                    
                    print(f"✓ Filled date field '{field_label}' with '{value}'")
                    return
                except Exception as e:
                    print(f"  Error parsing date: {e}")
            
            # Fallback: try any input in the item
            inputs = item.query_selector_all('input')
            if inputs:
                # Try filling the first input with the full date
                first_input = inputs[0]
                first_input.scroll_into_view_if_needed()
                time.sleep(0.3)
                first_input.click()
                time.sleep(0.3)
                first_input.fill(value)
                print(f"✓ Filled date field '{field_label}' with '{value}' (fallback)")
                return
            
            print(f"⚠ Could not find date input for field: {field_label}")
            
        except Exception as e:
            print(f"Error filling date field: {e}")
            import traceback
            traceback.print_exc()
    
    def fill_radio_button_google_forms(self, field_index: int, field_name: str, value: str, field_label: str):
        """Fill Google Forms radio button."""
        try:
            print(f"  Attempting to select radio button '{value}' for '{field_label}'")
            
            # Find the form item by index
            form_items = self.page.query_selector_all('[role="listitem"], .freebirdFormviewerViewItemsItemItem')
            if field_index >= len(form_items):
                print(f"  ⚠ Field index {field_index} out of range (found {len(form_items)} items)")
                # Try to find by label text as fallback
                try:
                    item_locator = self.page.locator(f'text="{field_label}"')
                    if item_locator.count() > 0:
                        # Find parent item
                        item_handle = item_locator.first.evaluate_handle("""
                            (el) => {
                                let parent = el;
                                for (let i = 0; i < 10; i++) {
                                    parent = parent.parentElement;
                                    if (parent && (parent.getAttribute('role') === 'listitem' || 
                                        parent.classList.contains('freebirdFormviewerViewItemsItemItem'))) {
                                        return parent;
                                    }
                                }
                                return null;
                            }
                        """)
                        if item_handle:
                            item = item_handle
                        else:
                            return
                    else:
                        return
                except:
                    return
            else:
                item = form_items[field_index]
            
            item.scroll_into_view_if_needed()
            time.sleep(0.5)
            
            # IMPORTANT: Don't rely on finding visible radio inputs
            # Google Forms often uses hidden inputs, but the labels/text are clickable
            # Strategy: Click the option text directly
            
            # Strategy 1: Click the option text directly using JavaScript (BEST approach)
            option_found = False
            try:
                # Use JavaScript to find and click the exact option text
                # IMPORTANT: Must match exactly "Yes", "No", or "Maybe" - not the question
                # Pass arguments directly to the function
                result = item.evaluate("""
                    (searchValue, questionText) => {
                        const searchLower = searchValue.toLowerCase().trim();
                        const questionLower = questionText.toLowerCase();
                        
                        // Find all clickable elements
                        const clickables = this.querySelectorAll('label, [role="option"], span, div, button, input[type="radio"]');
                        const candidates = [];
                        
                        for (let el of clickables) {
                            const text = (el.textContent || el.innerText || '').trim();
                            const textLower = text.toLowerCase();
                            
                            // Must be exact match or very close, and NOT the question
                            const isExactMatch = textLower === searchLower;
                            const isShortMatch = (textLower.includes(searchLower) && text.length <= searchValue.length + 2);
                            const isNotQuestion = !textLower.includes(questionLower) && text.length < 50;
                            const noQuestionMark = !text.includes('?');
                            
                            if ((isExactMatch || isShortMatch) && isNotQuestion && noQuestionMark && text.length > 0) {
                                // Additional check: make sure it's not a parent containing the question
                                let parent = el.parentElement;
                                let containsQuestion = false;
                                for (let i = 0; i < 3; i++) {
                                    if (parent && (parent.textContent || '').toLowerCase().includes(questionLower)) {
                                        containsQuestion = true;
                                        break;
                                    }
                                    parent = parent ? parent.parentElement : null;
                                }
                                
                                if (!containsQuestion) {
                                    candidates.push({element: el, text: text, score: isExactMatch ? 1 : 0});
                                }
                            }
                        }
                        
                        // Sort by exact match first
                        candidates.sort((a, b) => b.score - a.score);
                        
                        // Click the best match
                        if (candidates.length > 0) {
                            candidates[0].element.click();
                            return true;
                        }
                        
                        return false;
                    }
                """, value, field_label)
                
                if result:
                    print(f"  ✓ Clicked option text '{value}' directly using JavaScript")
                    option_found = True
                    time.sleep(0.5)
            except Exception as e:
                print(f"  Direct text click failed: {e}")
            
            # Strategy 2: Find and click labels containing ONLY the value (not the whole question)
            if not option_found:
                try:
                    # Get all labels and clickable elements in the item
                    labels = item.query_selector_all('label, [role="option"], span, div, button')
                    for label in labels:
                        try:
                            label_text = label.evaluate("el => el.textContent.trim()")
                            if label_text:
                                label_lower = label_text.lower().strip()
                                value_lower = value.lower().strip()
                                question_lower = field_label.lower()
                                
                                # IMPORTANT: Must be exact match or very close, and NOT contain the question
                                is_exact_match = (label_lower == value_lower)
                                is_short_match = (value_lower in label_lower and len(label_text) <= len(value) + 2)
                                does_not_contain_question = question_lower not in label_lower
                                no_question_mark = '?' not in label_text
                                is_short = len(label_text) < 20
                                
                                # Must match exactly or be a short match, and definitely not the question
                                if (is_exact_match or (is_short_match and is_short)) and does_not_contain_question and no_question_mark:
                                    # Double check: make sure it's not the whole question
                                    if label_text.lower() != question_lower:
                                        label.scroll_into_view_if_needed()
                                        time.sleep(0.3)
                                        label.click()
                                        print(f"  ✓ Clicked label '{label_text}' (matched '{value}')")
                                        option_found = True
                                        time.sleep(0.5)
                                        break
                        except Exception as e:
                            continue
                except Exception as e:
                    print(f"  Label clicking failed: {e}")
            
            # Strategy 3: Use JavaScript to find and click
            if not option_found:
                try:
                    result = item.evaluate(f"""
                        (searchValue) => {{
                            // Find all clickable elements with text
                            const elements = this.querySelectorAll('label, [role="option"], span, div, button');
                            for (let el of elements) {{
                                const text = el.textContent || el.innerText || '';
                                if (text.toLowerCase().includes(searchValue.toLowerCase()) || 
                                    searchValue.toLowerCase().includes(text.toLowerCase())) {{
                                    // Check if it's a valid option (not the question itself)
                                    if (text.length < 50 && !text.includes('?') && text.trim().length > 0) {{
                                        el.click();
                                        return true;
                                    }}
                                }}
                            }}
                            return false;
                        }}
                    """, value)
                    
                    if result:
                        print(f"  ✓ Clicked option using JavaScript")
                        option_found = True
                        time.sleep(0.5)
                except Exception as e:
                    print(f"  JavaScript click failed: {e}")
            
            # Strategy 4: Try finding radio inputs (even if hidden) and click their labels
            if not option_found:
                try:
                    # Get ALL radio inputs (including hidden)
                    radios = item.query_selector_all('input[type="radio"]')
                    print(f"  Found {len(radios)} radio inputs (including hidden)")
                    
                    for radio in radios:
                        try:
                            # Get the label for this radio
                            label_element = radio.evaluate_handle("""
                                (radio) => {
                                    let label = radio.closest('label');
                                    if (label) return label;
                                    
                                    label = document.querySelector(`label[for="${radio.id}"]`);
                                    if (label) return label;
                                    
                                    return radio.parentElement;
                                }
                            """)
                            
                            if label_element:
                                label_text = label_element.evaluate("el => el.textContent.trim()")
                                if label_text:
                                    label_lower = label_text.lower().strip()
                                    value_lower = value.lower().strip()
                                    
                                    if (label_lower == value_lower or 
                                        value_lower in label_lower or 
                                        label_lower in value_lower):
                                        label_element.scroll_into_view_if_needed()
                                        time.sleep(0.3)
                                        label_element.click()
                                        print(f"  ✓ Clicked radio label '{label_text}'")
                                        option_found = True
                                        time.sleep(0.5)
                                        break
                        except:
                            continue
                except Exception as e:
                    print(f"  Radio label clicking failed: {e}")
            
            if option_found:
                print(f"✓ Selected radio option '{value}' for '{field_label}'")
                return
            else:
                print(f"⚠ Could not select radio option '{value}' for '{field_label}'")
                # List what we found for debugging
                try:
                    item_text = item.text_content()[:200] if hasattr(item, 'text_content') else item.inner_text()[:200]
                    print(f"  Item text preview: {item_text}...")
                except:
                    pass
                return
            
            # Try multiple strategies to find and click the right radio
            option_found = False
            
            # Strategy 1: Click the label/option text directly (BEST for Google Forms)
            # Google Forms allows clicking the text, not just the radio input
            try:
                # Try to find and click the option text directly
                option_text_locator = item.locator(f'text="{value}"')
                if option_text_locator.count() > 0:
                    # Click the text/label directly
                    option_text_locator.first.scroll_into_view_if_needed()
                    time.sleep(0.3)
                    option_text_locator.first.click()
                    print(f"  ✓ Clicked option text '{value}' directly")
                    option_found = True
                    time.sleep(0.5)
            except Exception as e:
                print(f"  Direct text click failed: {e}")
            
            # Strategy 2: Match by label text and click the label (not the input)
            if not option_found:
                for radio in radios:
                    try:
                        # Get the label element (the clickable part)
                        label_element = radio.evaluate_handle("""
                            (radio) => {
                                // Try multiple ways to find the label element
                                let label = radio.closest('label');
                                if (label) return label;
                                
                                label = document.querySelector(`label[for="${radio.id}"]`);
                                if (label) return label;
                                
                                label = radio.closest('[role="option"]');
                                if (label) return label;
                                
                                // Try parent div
                                let parent = radio.parentElement;
                                if (parent && parent.textContent.trim().length < 100) {
                                    return parent;
                                }
                                
                                return null;
                            }
                        """)
                        
                        if label_element:
                            # Get the text content
                            label_text = label_element.evaluate("el => el.textContent.trim()")
                            
                            # Check for match
                            if label_text:
                                label_lower = label_text.lower().strip()
                                value_lower = value.lower().strip()
                                
                                # Exact match or contains match
                                if (label_lower == value_lower or 
                                    value_lower in label_lower or 
                                    label_lower in value_lower or
                                    any(word in label_lower for word in value_lower.split() if len(word) > 2)):
                                    
                                    # Click the LABEL, not the radio input
                                    label_element.scroll_into_view_if_needed()
                                    time.sleep(0.3)
                                    label_element.click()
                                    print(f"  ✓ Clicked label '{label_text}' (matched '{value}')")
                                    option_found = True
                                    time.sleep(0.5)
                                    break
                    except Exception as e:
                        print(f"  Error checking radio label: {e}")
                        continue
            
            # Strategy 3: Fallback - click the radio input itself (if label click didn't work)
            if not option_found:
                for radio in radios:
                    try:
                        # Get the label text for this radio
                        label_text = radio.evaluate("""
                            (radio) => {
                                let label = radio.closest('label');
                                if (label) return label.textContent.trim();
                                
                                label = document.querySelector(`label[for="${radio.id}"]`);
                                if (label) return label.textContent.trim();
                                
                                return '';
                            }
                        """)
                        
                        # Check for match
                        if label_text:
                            label_lower = label_text.lower().strip()
                            value_lower = value.lower().strip()
                            
                            if (label_lower == value_lower or 
                                value_lower in label_lower or 
                                label_lower in value_lower):
                                
                                radio.scroll_into_view_if_needed()
                                time.sleep(0.3)
                                radio.click()
                                print(f"  ✓ Selected radio input: '{label_text}' (matched '{value}')")
                                option_found = True
                                time.sleep(0.5)
                                break
                    except Exception as e:
                        continue
            
            # Strategy 4: Use locator to find by text (proximity-based)
            if not option_found:
                try:
                    # Try to find the option text directly on the page
                    option_locator = item.locator(f'text="{value}"')
                    if option_locator.count() > 0:
                        # Find the radio near this text
                        for radio in radios:
                            try:
                                # Check if radio is near the text
                                radio_rect = radio.bounding_box()
                                option_rect = option_locator.first.bounding_box()
                                
                                if radio_rect and option_rect:
                                    # If they're close, click the radio
                                    distance = ((radio_rect['x'] - option_rect['x'])**2 + 
                                               (radio_rect['y'] - option_rect['y'])**2)**0.5
                                    if distance < 200:  # Within 200px
                                        radio.scroll_into_view_if_needed()
                                        time.sleep(0.3)
                                        radio.click()
                                        print(f"  ✓ Selected radio near text '{value}'")
                                        option_found = True
                                        time.sleep(0.5)
                                        break
                            except:
                                continue
                except Exception as e:
                    print(f"  Locator strategy failed: {e}")
            
            # Strategy 5: Click by index if value matches common options
            if not option_found:
                try:
                    # Common patterns: Yes/No, True/False, etc.
                    value_lower = value.lower().strip()
                    for i, radio in enumerate(radios):
                        # Get all option texts
                        all_texts = []
                        for r in radios:
                            try:
                                label = r.evaluate("""
                                    (radio) => {
                                        const label = radio.closest('label') || 
                                                     document.querySelector(`label[for="${radio.id}"]`);
                                        return label ? label.textContent.trim() : '';
                                    }
                                """)
                                if label:
                                    all_texts.append(label.lower())
                            except:
                                pass
                        
                        # If value matches first option and it's Yes/True, click first
                        # If value matches second option and it's No/False, click second
                        if len(all_texts) >= 2:
                            if (value_lower in ['yes', 'true', 'y'] and 
                                any(x in all_texts[0] for x in ['yes', 'true', 'y'])):
                                radios[0].click()
                                option_found = True
                                print(f"  ✓ Selected first option (Yes/True)")
                                break
                            elif (value_lower in ['no', 'false', 'n', 'maybe'] and 
                                  any(x in all_texts[1] for x in ['no', 'false', 'n', 'maybe'])):
                                if len(radios) > 1:
                                    radios[1].click()
                                    option_found = True
                                    print(f"  ✓ Selected second option (No/False/Maybe)")
                                    break
                except Exception as e:
                    print(f"  Index strategy failed: {e}")
            
            if option_found:
                print(f"✓ Selected radio option '{value}' for '{field_label}'")
                return
            else:
                print(f"⚠ Could not find radio option '{value}' for '{field_label}'")
                # List available options for debugging
                try:
                    available = []
                    for radio in radios:
                        label = radio.evaluate("""
                            (radio) => {
                                const label = radio.closest('label') || 
                                             document.querySelector(`label[for="${radio.id}"]`);
                                return label ? label.textContent.trim() : '';
                            }
                        """)
                        if label:
                            available.append(label)
                    print(f"  Available options: {available}")
                except:
                    pass
                    
        except Exception as e:
            print(f"Error selecting radio button: {e}")
            import traceback
            traceback.print_exc()
    
    def fill_radio_button(self, field_name: str, value: str):
        """
        Select a radio button option (legacy method).
        
        Args:
            field_name: Name of the radio button group
            value: Label text of the option to select
        """
        if not self.page:
            raise RuntimeError("Browser not started.")
        
        try:
            # Try to find radio by label text
            radio = self.page.query_selector(f'text="{value}"')
            if radio:
                radio.click()
                print(f"✓ Selected radio option '{value}'")
                return
            
            # Try by name attribute
            radios = self.page.query_selector_all(f'input[type="radio"][name*="{field_name}"]')
            for radio in radios:
                label = self.page.evaluate("""
                    (radio) => {
                        const label = radio.closest('label') || 
                                     document.querySelector(`label[for="${radio.id}"]`);
                        return label ? label.textContent.trim() : '';
                    }
                """, radio)
                
                if value.lower() in label.lower() or label.lower() in value.lower():
                    radio.click()
                    print(f"✓ Selected radio option '{value}'")
                    return
            
            print(f"⚠ Could not select radio option '{value}'")
            
        except Exception as e:
            print(f"Error selecting radio button: {e}")
    
    def fill_form_field(self, field_info: Dict[str, Any], value: str):
        """
        Fill a form field based on its type.
        
        Args:
            field_info: Dictionary containing field information
            value: Value to fill
        """
        if not value:
            print(f"⚠ No value provided for field: {field_info.get('label', 'Unknown')}")
            return
        
        field_type = field_info.get('type', '').lower()
        field_label_raw = field_info.get('label', '')
        field_label = field_label_raw.lower()
        field_index = field_info.get('index', 0)
        field_name = field_info.get('name', '')
        field_id = field_info.get('id', '')
        
        # Smart type detection: Check label to determine if it's really a date field
        # Don't treat as date unless label explicitly mentions date/birth/dob
        is_really_date = (field_type == 'date' and 
                         ('date' in field_label or 'birth' in field_label or 'dob' in field_label or 'when' in field_label))
        
        # If field was detected as date but label suggests it's text (like "course"), treat as text
        if field_type == 'date' and not is_really_date:
            print(f"  ⚠ Field '{field_label_raw}' was detected as date but label suggests text. Treating as text field.")
            field_type = 'text'
        
        # Also check if value looks like a date but field is not a date field
        if field_type != 'date' and ('/' in value or '-' in value) and len(value.split('/')) == 3:
            # Value looks like date but field is not date - this is wrong, it's probably text
            print(f"  ⚠ Value '{value}' looks like date but field '{field_label_raw}' is not a date field. Using as-is.")
        
        try:
            # Special handling for date fields (only if it's really a date field)
            if field_type == 'date' and is_really_date:
                self.fill_date_field_google_forms(field_index, value, field_label_raw)
                return
            
            if field_type in ['text', 'email', 'textarea']:
                # Try multiple strategies for Google Forms
                filled = False
                
                # Strategy 1: Find by item index (Google Forms specific)
                # IMPORTANT: Exclude hidden inputs - Google Forms uses them for data storage
                try:
                    form_items = self.page.query_selector_all('[role="listitem"], .freebirdFormviewerViewItemsItemItem')
                    if field_index < len(form_items):
                        item = form_items[field_index]
                        # Get all inputs, then filter out hidden ones
                        all_inputs = item.query_selector_all('input, textarea')
                        input_field = None
                        for inp in all_inputs:
                            # Skip hidden inputs
                            inp_type = inp.evaluate("el => el.type")
                            if inp_type == 'hidden':
                                continue
                            # Check if visible
                            is_visible = inp.evaluate("""
                                (el) => {
                                    const style = window.getComputedStyle(el);
                                    return style.display !== 'none' && 
                                           style.visibility !== 'hidden' && 
                                           el.offsetWidth > 0 && 
                                           el.offsetHeight > 0;
                                }
                            """)
                            if is_visible and inp_type in ['text', 'email']:
                                input_field = inp
                                break
                        
                        if input_field:
                            input_field.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            input_field.click()
                            time.sleep(0.3)
                            input_field.fill(value)
                            filled = True
                            print(f"✓ Filled '{field_label}' with '{value}'")
                except Exception as e:
                    print(f"  Strategy 1 failed: {e}")
                
                # Strategy 2: Find by name or id
                if not filled and (field_name or field_id):
                    try:
                        selector = f'input[name="{field_name}"]' if field_name else f'input#{field_id}'
                        element = self.page.query_selector(selector)
                        if element:
                            element.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            element.click()
                            time.sleep(0.3)
                            element.fill(value)
                            filled = True
                            print(f"✓ Filled '{field_label}' with '{value}'")
                    except Exception as e:
                        print(f"  Strategy 2 failed: {e}")
                
                # Strategy 3: Find by index in all visible inputs (EXCLUDE hidden)
                if not filled:
                    try:
                        # Get all inputs, filter out hidden ones
                        all_inputs = self.page.query_selector_all('input, textarea')
                        visible_inputs = []
                        for inp in all_inputs:
                            inp_type = inp.evaluate("el => el.type")
                            if inp_type == 'hidden':
                                continue  # Skip hidden inputs - they're just for data storage
                            # Check if visible
                            is_visible = inp.evaluate("""
                                (el) => {
                                    const style = window.getComputedStyle(el);
                                    return style.display !== 'none' && 
                                           style.visibility !== 'hidden' && 
                                           el.offsetWidth > 0 && 
                                           el.offsetHeight > 0;
                                }
                            """)
                            if is_visible and inp_type in ['text', 'email', 'date']:
                                visible_inputs.append(inp)
                        
                        if field_index < len(visible_inputs):
                            element = visible_inputs[field_index]
                            element.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            element.click()
                            time.sleep(0.3)
                            element.fill(value)
                            filled = True
                            print(f"✓ Filled '{field_label}' with '{value}'")
                    except Exception as e:
                        print(f"  Strategy 3 failed: {e}")
                
                if not filled:
                    print(f"⚠ Could not fill text field: {field_label}")
                    
            elif field_type == 'select' or 'dropdown' in field_label.lower():
                self.fill_dropdown_google_forms(field_index, value, field_label)
                
            elif field_type == 'radio':
                self.fill_radio_button_google_forms(field_index, field_name, value, field_label)
                
            else:
                # Generic fill attempt
                inputs = self.page.query_selector_all('input, textarea, select')
                if field_index < len(inputs):
                    inputs[field_index].fill(value)
                    print(f"✓ Filled '{field_label}' with '{value}'")
                    
        except Exception as e:
            print(f"Error filling field '{field_label}': {e}")
            import traceback
            traceback.print_exc()
    
    def fill_form_with_ai(self, form_url: str) -> bool:
        """
        Fill the form using Perception and Decision architecture.
        
        Args:
            form_url: URL of the form
            
        Returns:
            True if form was filled successfully
        """
        try:
            # Navigate to form
            self.navigate_to_form(form_url)
            
            # STEP 1: PERCEPTION - Understand the form
            print("\n" + "="*60)
            print("STEP 1: PERCEPTION - Understanding Form Structure")
            print("="*60)
            form_data = self.perception.perceive_form()
            
            fields = form_data.get('fields', [])
            form_context = form_data.get('form_context', {})
            
            print(f"\n✓ [Perception] Analyzed {len(fields)} fields")
            for i, field_class in enumerate(fields):
                field = field_class.get('field', {})
                print(f"   Field {i}: '{field.get('label', 'Unknown')}' - {field_class.get('purpose', 'unknown')} ({field_class.get('detected_type', 'unknown')})")
            
            # STEP 2: DECISION - Decide what to fill
            print("\n" + "="*60)
            print("STEP 2: DECISION - Deciding What to Fill")
            print("="*60)
            
            # Get filling strategy
            strategy = self.decision.decide_filling_strategy(form_data)
            
            # STEP 3: EXECUTION - Fill the form
            print("\n" + "="*60)
            print("STEP 3: EXECUTION - Filling Form Fields")
            print("="*60)
            
            filled_count = 0
            for i, field_classification in enumerate(fields):
                field = field_classification.get('field', {})
                field_label = field.get('label', 'Unknown')
                
                # Decision: What value to fill?
                decision_result = self.decision.decide_field_value(
                    field_classification=field_classification,
                    form_context=form_context,
                    all_fields=fields
                )
                
                value = decision_result.get('value')
                reasoning = decision_result.get('reasoning', '')
                
                if value:
                    print(f"\n📝 Filling field {i+1}/{len(fields)}: '{field_label}'")
                    print(f"   Decision: '{value}'")
                    if reasoning:
                        print(f"   Reasoning: {reasoning[:100]}...")
                    
                    # Execute: Fill the field
                    self.fill_form_field_from_classification(field_classification, value)
                    filled_count += 1
                    time.sleep(1)  # Wait between fields
                else:
                    print(f"\n⚠ Skipping field '{field_label}': No value decided")
            
            print("\n" + "="*60)
            print(f"✅ Form filling completed! Filled {filled_count}/{len(fields)} fields")
            print("="*60)
            return True
            
        except Exception as e:
            print(f"\n❌ Error filling form: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def fill_form_field_from_classification(
        self,
        field_classification: Dict[str, Any],
        value: str
    ):
        """
        Fill a form field based on its classification from Perception.
        
        Args:
            field_classification: Classified field from Perception module
            value: Value to fill (from Decision module)
        """
        field = field_classification.get('field', {})
        detected_type = field_classification.get('detected_type', 'text')
        interaction_type = field_classification.get('interaction_type', 'type')
        field_index = field.get('index', 0)
        field_label = field.get('label', 'Unknown')
        field_name = field.get('name', '')
        
        # Use the appropriate filling method based on interaction type
        if interaction_type == 'radio':
            self.fill_radio_button_google_forms(field_index, field_name, value, field_label)
        elif interaction_type == 'select':
            self.fill_dropdown_google_forms(field_index, value, field_label)
        elif detected_type == 'date':
            self.fill_date_field_google_forms(field_index, value, field_label)
        else:
            # Text, email, textarea
            self.fill_form_field(field, value)
    
    def take_screenshot(self, filename: str = "form_screenshot.png"):
        """Take a screenshot of the current page."""
        if self.page:
            self.page.screenshot(path=filename)
            print(f"Screenshot saved to {filename}")

