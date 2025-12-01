# Routing Decision Architecture: RAG vs Web Search

## Overview

The router needs to intelligently decide when to use **Local RAG** (search local documents) vs **Web Search** (search the internet). This document explains the decision criteria and architecture.

## Decision Criteria

### When to Use Local RAG

**High Confidence (0.9-0.95):**
1. **Explicit RAG requests:**
   - "RAG search", "using RAG", "check using rag"
   - User explicitly wants local document search

2. **Document location indicators:**
   - "in my notes", "in my documents", "in the folder", "in files", "in docs"
   - References to local storage

3. **Document-specific questions:**
   - "How much did X pay?" (specific transaction)
   - "What does document Y say?" (references specific document)
   - "According to my notes..." (references local content)
   - "Which file mentions X?" (file search)

**Medium Confidence (0.7-0.8):**
4. **Factual queries that might be in documents:**
   - Questions about specific people/companies/transactions
   - Historical data that might be archived
   - Internal information (not public knowledge)

5. **Context-based:**
   - Previous query was RAG → follow-up likely RAG
   - "same folder" → continue with RAG

### When to Use Web Search

**High Confidence (0.9-0.95):**
1. **Explicit web search requests:**
   - "search the web", "google", "find article", "look up"
   - User explicitly wants internet search

2. **Current events / public information:**
   - "current AQI", "latest news", "today's weather"
   - General knowledge questions
   - Public information not in local docs

3. **No document indicators:**
   - Query doesn't mention documents, notes, files
   - General question without local context

**Medium Confidence (0.7-0.8):**
4. **Ambiguous queries without RAG keywords:**
   - General questions that could be either
   - Default to web search if no RAG indicators

## Decision Flow

```
Query Input
    ↓
Check for URL?
    ├─ Yes → web_page_ops
    └─ No → Continue
        ↓
Check for explicit RAG keywords?
    ├─ Yes → local_rag (confidence: 0.95)
    └─ No → Continue
        ↓
Check for document location keywords?
    ├─ Yes → local_rag (confidence: 0.9)
    └─ No → Continue
        ↓
Check for document-specific question patterns?
    ├─ Yes → local_rag (confidence: 0.8)
    └─ No → Continue
        ↓
Check for web search keywords?
    ├─ Yes → web_search (confidence: 0.9)
    └─ No → Continue
        ↓
Check for math indicators?
    ├─ Yes → math
    └─ No → Use LLM classification
```

## Examples

### Should Use RAG:
- ✅ "How much did Anmol Singh pay for DLF apartment via Capbridge?" → Document-specific fact
- ✅ "What does the DLF document say about pricing?" → References specific document
- ✅ "Search my notes for RAG architecture" → Explicit local search
- ✅ "In my documents, what is mentioned about cricket?" → Location indicator
- ✅ "RAG search: Anmol Singh DLF" → Explicit RAG request

### Should Use Web Search:
- ✅ "What is the current AQI in Bangalore?" → Current/public information
- ✅ "Search the web for Python tutorials" → Explicit web search
- ✅ "What is the latest news about AI?" → Current events
- ✅ "How does RAG work?" → General knowledge question

### Ambiguous (LLM decides):
- ⚠️ "Tell me about Anmol Singh" → Could be in docs or web
- ⚠️ "What is DLF?" → Could be in docs or general knowledge
- ⚠️ "Explain RAG" → General explanation (web) vs document search (RAG)

## LLM Classification Prompt

When heuristics are uncertain, the LLM uses this reasoning:

1. **Is this information likely in local documents?**
   - Specific facts, transactions, internal data → RAG
   - General knowledge, current events → Web

2. **Does the query reference local storage?**
   - "my notes", "documents", "files" → RAG
   - No local references → Web

3. **Is this a document-specific question?**
   - "How much did X pay?" → Likely in documents → RAG
   - "What is X?" → General knowledge → Web

## Architecture Improvements

### Current Implementation:
- ✅ Rule-based heuristics (fast path)
- ✅ LLM classification (when uncertain)
- ✅ Context awareness (last task, folder)

### Future Enhancements:
- 🔄 Confidence threshold tuning
- 🔄 User preference learning
- 🔄 Hybrid search (try RAG first, fallback to web)
- 🔄 Result quality feedback loop

## Configuration

Key parameters in `agents/router.py`:
- `explicit_rag_keywords`: High confidence RAG triggers
- `location_keywords`: Medium confidence RAG triggers  
- `document_question_patterns`: Pattern-based RAG detection
- `search_keywords`: Web search triggers

## Testing Scenarios

1. **Explicit RAG**: "RAG search: Anmol Singh" → Should route to local_rag
2. **Document question**: "How much did X pay?" → Should route to local_rag
3. **Web search**: "Current AQI in Bangalore" → Should route to web_search
4. **Ambiguous**: "Tell me about Anmol Singh" → LLM decides based on context

