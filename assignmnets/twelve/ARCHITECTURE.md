# Architecture Documentation

## Overview

This browser agent uses a **Perception-Decision-Execution** architecture that separates concerns into three distinct phases:

1. **Perception**: Understands what fields exist and what they are
2. **Decision**: Determines what values to fill based on intent
3. **Execution**: Actually fills the form fields in the browser

This architecture provides clear separation of concerns, making the system more maintainable, testable, and extensible.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Orchestration Layer)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                               │
┌───────▼────────┐          ┌─────────▼──────────┐
│ BrowserAgent   │          │   GeminiClient     │
│                │          │                     │
│ - Browser      │          │ - API Communication│
│   Automation   │          │ - Model Interface   │
│ - Execution    │          │                     │
│   (Filling)    │          └─────────┬───────────┘
└───────┬────────┘                      │
        │                               │
        │ Uses                          │ Uses
        │                               │
┌───────▼────────┐          ┌───────────▼──────────┐
│  Perception    │          │      Decision        │
│                │          │                      │
│ - Field        │          │ - Value Decision     │
│   Detection    │          │ - AI Integration    │
│ - Classification│         │ - Validation        │
│ - Understanding│          │ - Context Analysis  │
└────────────────┘          └──────────────────────┘
        │                               │
        │                               │
        └───────────┬───────────────────┘
                    │
            ┌───────▼────────┐
            │   Playwright   │
            │   (Browser)    │
            └────────────────┘
```

## Architecture Phases

### Phase 1: PERCEPTION 🔍

**Module**: `perception.py`  
**Responsibility**: Understand what the form fields are

**What it does**:
- Detects all form fields on the page
- Classifies each field (text, date, dropdown, radio, etc.)
- Understands the **purpose** of each field (name, email, course, marital status, etc.)
- Extracts field properties (label, options, required status)
- Determines interaction type (how to fill the field)

**Key Methods**:
- `perceive_form()`: Main method - analyzes entire form
- `_detect_fields()`: Detects fields using JavaScript
- `_classify_field()`: Classifies and understands each field
- `_determine_purpose()`: Determines field purpose/intent
- `_determine_interaction_type()`: Determines how to interact

**Output**: Structured data about all fields with their classifications

**Example**:
```python
{
    "fields": [
        {
            "purpose": "name",
            "detected_type": "text",
            "interaction_type": "type",
            "field": {...}
        },
        {
            "purpose": "marital_status",
            "detected_type": "radio",
            "interaction_type": "radio",
            "field": {...}
        }
    ]
}
```

### Phase 2: DECISION 🤖

**Module**: `decision.py`  
**Responsibility**: Decide what values to fill

**What it does**:
- Takes field classifications from Perception
- Uses AI (Gemini) to decide appropriate values
- Validates decisions against field constraints
- Handles edge cases and fallbacks
- Provides reasoning for decisions

**Key Methods**:
- `decide_field_value()`: Main method - decides value for a field
- `_ai_decide()`: Uses AI to make decision
- `_validate_decision()`: Validates and refines decision
- `_build_enhanced_prompt()`: Builds context-aware prompts
- `decide_filling_strategy()`: Overall form filling strategy

**Output**: Decision with value, reasoning, and confidence

**Example**:
```python
{
    "value": "Yes",
    "reasoning": "Field asks about marital status, options are Yes/No/Maybe",
    "confidence": "high",
    "validated": True
}
```

### Phase 3: EXECUTION ✏️

**Module**: `browser_agent.py`  
**Responsibility**: Actually fill the form fields

**What it does**:
- Takes decisions from Decision module
- Executes browser actions (click, type, select)
- Handles different field types appropriately
- Provides multiple fallback strategies
- Manages browser state and timing

**Key Methods**:
- `fill_form_with_ai()`: Main orchestration method
- `fill_form_field_from_classification()`: Fills based on classification
- `fill_text_field()`, `fill_dropdown_google_forms()`, etc.: Type-specific methods

## Component Details

### 1. Main Entry Point (`main.py`)

**Responsibility**: Orchestrates the entire form-filling process

**Key Functions**:
- Loads environment configuration
- Initializes all components
- Coordinates the workflow
- Handles errors and cleanup

### 2. Perception Module (`perception.py`)

**Responsibility**: Understands form structure and field types

**Key Classes**:
- `Perception`: Main perception class

**Key Features**:
- **Field Detection**: Uses JavaScript to detect all form fields
- **Smart Classification**: Determines true field type (not just HTML type)
- **Purpose Detection**: Understands field intent (name, email, course, etc.)
- **Type Correction**: Fixes misclassifications (e.g., date vs text)

**Design Decisions**:

#### Why Separate Perception?
- **Single Responsibility**: Only focuses on understanding, not decision-making
- **Testable**: Can test field detection independently
- **Reusable**: Perception logic can be used for other purposes
- **Clear Interface**: Clean API for field information

#### Smart Type Detection:
- Checks field labels, not just HTML attributes
- Prevents "course" fields from being treated as dates
- Understands context and purpose

### 3. Decision Module (`decision.py`)

**Responsibility**: Makes intelligent decisions about what to fill

**Key Classes**:
- `Decision`: Main decision-making class

**Key Features**:
- **AI-Powered**: Uses Gemini AI for intelligent decisions
- **Context-Aware**: Considers form context and field relationships
- **Purpose-Specific**: Different logic for different field purposes
- **Validation**: Validates decisions against field constraints
- **Fallbacks**: Provides fallback values when AI fails

**Design Decisions**:

#### Why Separate Decision?
- **Separation of Concerns**: Decision logic separate from execution
- **AI Abstraction**: Can swap AI models without changing execution
- **Testable**: Can test decision logic with mock AI
- **Extensible**: Easy to add new decision strategies

#### Purpose-Based Decisions:
- Different prompts for different purposes (name, email, course, etc.)
- Validates against available options
- Provides specific guidance for each field type

### 4. Browser Agent (`browser_agent.py`)

**Responsibility**: Executes form filling in the browser

**Key Classes**:
- `BrowserAgent`: Main browser automation class

**Key Features**:
- **Browser Management**: Handles browser lifecycle
- **Field Filling**: Executes actual form filling
- **Multiple Strategies**: Fallback strategies for reliability
- **Type-Specific Methods**: Different methods for different field types

**Design Decisions**:

#### Why Playwright?
- **Modern**: Built for modern web apps
- **Reliable**: Better handling of dynamic content
- **Fast**: Better performance than Selenium
- **Rich API**: Better Python interface

#### Execution Strategies:
- Multiple fallback strategies per field type
- Handles Google Forms specific structures
- Robust error handling

### 5. Gemini Client (`gemini_client.py`)

**Responsibility**: Manages AI API interactions

**Key Classes**:
- `GeminiClient`: Wrapper for Gemini API

**Design Decisions**:

#### Why Gemini 2.0 Flash?
- **Speed**: Fast responses
- **Cost-Effective**: More affordable
- **Capable**: Sufficient for form analysis
- **Structured Output**: Can provide JSON responses

## Data Flow

```
1. User runs main.py
   │
   ├─> Initialize BrowserAgent
   │   ├─> Start Playwright browser
   │   ├─> Initialize Perception (with page)
   │   └─> Initialize Decision (with GeminiClient)
   │
   ├─> Navigate to form URL
   │
   ├─> PHASE 1: PERCEPTION
   │   │
   │   ├─> perception.perceive_form()
   │   │   ├─> _detect_fields() → Raw field data
   │   │   ├─> _classify_field() → Classified fields
   │   │   └─> _get_form_context() → Form context
   │   │
   │   └─> Output: Form structure with classified fields
   │
   ├─> PHASE 2: DECISION
   │   │
   │   ├─> For each field:
   │   │   ├─> decision.decide_field_value()
   │   │   │   ├─> _ai_decide() → AI decision
   │   │   │   └─> _validate_decision() → Validated decision
   │   │   │
   │   │   └─> Output: Value to fill + reasoning
   │   │
   │   └─> Output: Decisions for all fields
   │
   └─> PHASE 3: EXECUTION
       │
       ├─> For each field:
       │   ├─> fill_form_field_from_classification()
       │   │   ├─> Determine interaction type
       │   │   ├─> Call appropriate fill method
       │   │   └─> Execute browser action
       │   │
       │   └─> Field filled in browser
       │
       └─> Form completed
```

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Each module has a single, clear responsibility
- Easy to understand what each part does
- Changes to one module don't affect others

### 2. **Testability**
- Can test Perception independently (mock page)
- Can test Decision independently (mock AI)
- Can test Execution independently (mock decisions)

### 3. **Maintainability**
- Clear boundaries between modules
- Easy to locate and fix bugs
- Easy to add new features

### 4. **Extensibility**
- Easy to add new field types to Perception
- Easy to add new decision strategies to Decision
- Easy to add new execution methods to BrowserAgent

### 5. **Debugging**
- Clear phase boundaries make debugging easier
- Can inspect output at each phase
- Clear error messages from each module

## Example Workflow

```
Form: "What is your name?"
│
├─> PERCEPTION:
│   - Detects: input field
│   - Classifies: type="text", purpose="name"
│   - Interaction: "type"
│
├─> DECISION:
│   - AI decides: "John Doe"
│   - Reasoning: "Realistic person name"
│   - Validated: Yes
│
└─> EXECUTION:
    - Finds input field
    - Types "John Doe"
    - ✓ Field filled
```

## Technology Choices

### Browser Automation: Playwright
- Modern, fast, reliable
- Better for dynamic content
- Good Python API

### AI: Gemini 2.0 Flash
- Fast responses
- Cost-effective
- Good structured output

### Architecture Pattern: Perception-Decision-Execution
- Clear separation of concerns
- Easy to test and maintain
- Extensible and flexible

## Future Enhancements

1. **Enhanced Perception**:
   - Image-based field detection
   - Multi-language support
   - Form template recognition

2. **Smarter Decisions**:
   - Learning from user corrections
   - Context-aware value generation
   - Multi-field dependencies

3. **Better Execution**:
   - Parallel field filling
   - Smart retry strategies
   - Form validation handling

## Conclusion

This Perception-Decision-Execution architecture provides a clean, maintainable, and extensible foundation for intelligent form filling. Each phase has a clear responsibility, making the system easier to understand, test, and improve.
