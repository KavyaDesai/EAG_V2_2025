"""Centralized prompt templates for all agents."""


class Prompts:
    """Prompt templates for the chatbot system."""
    
    # Router Agent Prompts
    @staticmethod
    def router_classification(query: str, context_summary: dict, heuristic_result: dict) -> str:
        """Prompt for router classification."""
        return f"""Classify this query into ONE category based on the following criteria:

**Categories:**
- web_page_ops: Operations on a specific web page (summarize, count words, extract URLs). REQUIRES a URL in the query.
- web_search: Search the internet for general/public information, current events, or information not in local documents
- local_rag: Query local documents/folders. Use when:
  * Query mentions "RAG", "documents", "notes", "files", "my documents", "local"
  * Query asks about specific facts that might be in indexed documents (e.g., "How much did X pay?", "What does document Y say?")
  * Query references specific people/companies/transactions that might be in local files
  * User explicitly wants to search local documents
- math: Mathematical calculations, code execution, or numerical computations
- general: General Q&A, explanations, or conceptual questions
- mixed: Requires multiple steps/agents (e.g., "search web then summarize")

**Decision Rules:**
1. If query has a URL → web_page_ops
2. If query mentions "RAG", "documents", "notes", "files" → local_rag
3. If query asks about specific facts/transactions/people that might be in documents → local_rag
4. If query asks about current events, general knowledge, or public information → web_search
5. If query has math operators or asks for calculations → math
6. If query is ambiguous, prefer local_rag if it seems document-specific, otherwise web_search

Query: "{query}"

Context:
- Last task: {context_summary.get('last_task_type', 'None')}
- Last URL: {context_summary.get('last_url', 'None')}
- Last folder: {context_summary.get('last_folder', 'None')}

Heuristic suggestion: {heuristic_result.get('task_type', 'general')} (confidence: {heuristic_result.get('confidence', 0.0):.2f})

Analyze the query and respond with JSON:
{{
  "task_type": "one of the categories above",
  "confidence": 0.0-1.0,
  "needs_planning": true/false,
  "tool_hints": ["list", "of", "tools"],
  "reasoning": "explain why this category - specifically address: is this likely in local documents or needs web search?"
}}"""
    
    # Planner Agent Prompts
    @staticmethod
    def planner_task_decomposition(query: str, task_type: str) -> str:
        """Prompt for task decomposition."""
        return f"""Break this task into 2-3 simple steps. Each step should use one agent:
- WebSearchAgent: Search the web
- WebPageAgent: Operate on a web page (summarize, count, extract)
- LocalRAGAgent: Query local documents (use this if query mentions "RAG", "documents", "notes", or "files")
- MathAndCodeAgent: Calculate or execute code
- GeneralQAAgent: General reasoning

IMPORTANT: If the query mentions "RAG", "RAG Search", "documents", "notes", or "files", you MUST use LocalRAGAgent.

Task: "{query}"
Task type: {task_type}

Respond with JSON only (max 3 steps):
{{
  "steps": [
    {{
      "step": 1,
      "agent": "AgentName",
      "action": "brief description",
      "input": "what to pass to the agent"
    }}
  ]
}}"""
    
    # Validator Agent Prompts
    @staticmethod
    def validator_quality_check(user_query: str, answer: str, evidence: str = None) -> str:
        """Prompt for answer validation."""
        evidence_text = f"\nEvidence:\n{evidence}" if evidence else ""
        return f"""Check if this answer correctly addresses the user's query.

User query: "{user_query}"
Answer: "{answer}"
{evidence_text}

Respond with JSON only:
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "improvements": "suggestions or null",
  "final_answer": "improved answer or null"
}}"""
    
    # Local RAG Agent Prompts
    @staticmethod
    def rag_answer(context: str, query: str) -> str:
        """Prompt for RAG-based answering."""
        return f"""Context from documents:
{context}

Question: {query}

Answer based on the context above. If the information is not found in the context, explicitly state that the information is not available in the documents. Include source citations when possible (e.g., [Source: filename, chunk_id: ...])."""
    
    # Math/Code Agent Prompts
    @staticmethod
    def code_generation(query: str) -> str:
        """Prompt for code generation."""
        return f"""Generate Python code to solve this problem: {query}

Requirements:
- Use only allowed libraries: math, numpy, scipy, requests, re, json
- For web search, use DDGS class (already imported, don't import again)
- Store the result in a variable named 'result'
- Print the result if it's a simple value
- Code should be safe and executable
- DO NOT use import statements - all libraries are pre-imported

Available in namespace:
- math, numpy, scipy, requests, re, json
- DDGS (from duckduckgo_search, already imported)

Respond with ONLY the Python code, no explanations:"""
    
    # Web Page Agent Prompts
    @staticmethod
    def webpage_summarize(markdown: str, query: str) -> str:
        """Prompt for web page summarization."""
        return f"""Summarize this web page content:

{markdown[:3000]}

User's specific request: {query}

Provide a concise summary focusing on the main points."""
    
    @staticmethod
    def url_filter(urls: list, topic: str) -> str:
        """Prompt for filtering URLs by topic."""
        return f"""From these URLs, select only those related to "{topic}":

{chr(10).join(urls[:50])}

Respond with JSON array of relevant URLs only:"""
    
    # Web Search Agent Prompts
    # (Uses code generation, no separate prompt needed)
    
    # General QA Agent
    # (Uses chat interface, no separate prompt template)
    
    # Terminal Chat Loop Prompts
    @staticmethod
    def synthesis_final_answer(query: str, step_results: str) -> str:
        """Prompt for synthesizing final answer from multi-step results."""
        return f"""User's original query: {query}

Step results:
{step_results}

Synthesize a coherent final answer that addresses the user's query:"""

