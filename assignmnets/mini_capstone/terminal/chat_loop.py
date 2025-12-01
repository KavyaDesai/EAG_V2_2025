"""Terminal chat loop with error handling and logging."""

import asyncio
import sys
from typing import Optional
from core.conversation import ConversationState
from core.gemini_client import GeminiClient
from core.mcp_client import MCPClient
from core.code_agent import CodeAgent
from core.logger import get_logger
from agents.router import RouterAgent
from agents.planner import PlannerAgent
from agents.validator import ValidatorAgent
from agents.local_rag import LocalRAGAgent
from agents.math_code import MathAndCodeAgent
from agents.web_page import WebPageAgent
from agents.web_search import WebSearchAgent
from agents.general_qa import GeneralQAAgent
from core.prompts import Prompts

logger = get_logger()


class TerminalChatLoop:
    """Terminal-based chat interface."""
    
    def __init__(self, gemini_client: GeminiClient, mcp_client: MCPClient, 
                 code_agent: CodeAgent, debug_mode: bool = False):
        """Initialize TerminalChatLoop."""
        self.state = ConversationState()
        self.debug_mode = debug_mode
        
        # Initialize agents
        self.router = RouterAgent(gemini_client)
        self.planner = PlannerAgent(gemini_client)
        self.validator = ValidatorAgent(gemini_client)
        
        self.local_rag = LocalRAGAgent(mcp_client, gemini_client)
        self.math_code = MathAndCodeAgent(code_agent, gemini_client)
        self.web_page = WebPageAgent(mcp_client, gemini_client, code_agent)
        self.web_search = WebSearchAgent(code_agent, gemini_client, self.web_page)
        self.general_qa = GeneralQAAgent(gemini_client)
        
        logger.info("Initialized TerminalChatLoop", component="TerminalChatLoop")
    
    async def run(self):
        """Run the chat loop."""
        print("=" * 60)
        print("Chatbot System - Multi-Agent Architecture")
        print("=" * 60)
        print("Type 'help' for commands, 'exit' to quit")
        print("=" * 60)
        print()
        
        try:
            while True:
                try:
                    # Get user input
                    user_input = input("> ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Handle commands
                    if user_input.lower() in ["exit", "quit"]:
                        print("Goodbye!")
                        break
                    elif user_input.lower() == "help":
                        self._show_help()
                        continue
                    elif user_input.lower() == "clear":
                        self.state.clear_history()
                        print("Conversation history cleared.")
                        continue
                    elif user_input.lower() == "debug":
                        self.debug_mode = not self.debug_mode
                        print(f"Debug mode: {'ON' if self.debug_mode else 'OFF'}")
                        continue
                    elif user_input.lower().startswith("debug "):
                        # Toggle debug for specific component
                        self.debug_mode = True
                        print("Debug mode enabled")
                        continue
                    
                    # Process query
                    await self._process_query(user_input)
                    
                except KeyboardInterrupt:
                    print("\n\nInterrupted. Type 'exit' to quit.")
                except EOFError:
                    print("\n\nGoodbye!")
                    break
                except Exception as e:
                    logger.error(
                        f"Unexpected error in chat loop: {str(e)}",
                        component="TerminalChatLoop",
                        error_type="CHAT_LOOP_ERROR"
                    )
                    print(f"An error occurred: {str(e)}")
                    print("Please try again or type 'exit' to quit.")
        
        except Exception as e:
            logger.critical(
                f"Fatal error in chat loop: {str(e)}",
                component="TerminalChatLoop",
                error_type="FATAL_ERROR"
            )
            print(f"Fatal error: {str(e)}")
    
    async def _process_query(self, query: str):
        """Process a user query."""
        try:
            # Add user message to history
            self.state.add_message("user", query)
            
            # Route query
            decision = self.router.route(query, self.state)
            
            if self.debug_mode:
                print(f"\n[DEBUG] Router Decision:")
                print(f"  Task Type: {decision.task_type}")
                print(f"  Confidence: {decision.confidence:.2f}")
                print(f"  Needs Planning: {decision.needs_planning}")
                print(f"  Reasoning: {decision.reasoning}")
                print()
            
            # Handle multi-step tasks
            if decision.needs_planning:
                answer = await self._handle_multi_step(query, decision)
            else:
                # Single-step: route to appropriate agent
                answer = await self._handle_single_step(query, decision)
            
            # Optional validation (for RAG and web tasks)
            if decision.task_type in ["local_rag", "web_page_ops", "web_search"]:
                validation = self.validator.validate(query, answer)
                if not validation["is_valid"] or validation["confidence"] < 0.7:
                    if validation.get("final_answer"):
                        answer = validation["final_answer"]
                    elif validation.get("improvements"):
                        if self.debug_mode:
                            print(f"[DEBUG] Validation improvements: {validation['improvements']}")
            
            # Add assistant response to history
            self.state.add_message("assistant", answer)
            
            # Print response
            print(f"\n{answer}\n")
            
        except Exception as e:
            logger.error(
                f"Query processing failed: {str(e)}",
                component="TerminalChatLoop",
                error_type="QUERY_PROCESSING_ERROR"
            )
            error_msg = "I encountered an error processing your query. Please try again."
            print(f"\n{error_msg}\n")
            self.state.add_message("assistant", error_msg)
    
    async def _handle_single_step(self, query: str, decision) -> str:
        """Handle single-step query."""
        task_type = decision.task_type
        
        if task_type == "local_rag":
            return await self.local_rag.handle(query, self.state)
        elif task_type == "math":
            return self.math_code.handle(query, self.state)
        elif task_type == "web_page_ops":
            return await self.web_page.handle(query, self.state)
        elif task_type == "web_search":
            return await self.web_search.handle(query, self.state)
        else:
            # Default to general QA
            return self.general_qa.handle(query, self.state)
    
    async def _handle_multi_step(self, query: str, decision) -> str:
        """Handle multi-step query using planner."""
        # Create plan
        plan = self.planner.plan(query, decision.task_type)
        
        if self.debug_mode:
            print(f"[DEBUG] Execution Plan:")
            for step in plan:
                print(f"  Step {step['step']}: {step['agent']} - {step['action']}")
            print()
        
        # Execute steps
        results = []
        for step in plan:
            agent_name = step.get("agent", "")
            action_input = step.get("input", query)
            
            # Extract clean query if input is too verbose
            if len(action_input) > 200:
                # Try to extract the core question
                action_input = query
            
            try:
                if agent_name == "WebSearchAgent" or "WebSearch" in agent_name:
                    result = await self.web_search.handle(action_input, self.state)
                elif agent_name == "WebPageAgent" or "WebPage" in agent_name:
                    result = await self.web_page.handle(action_input, self.state)
                elif agent_name == "LocalRAGAgent" or "LocalRAG" in agent_name or "RAG" in agent_name:
                    result = await self.local_rag.handle(action_input, self.state)
                elif agent_name == "MathAndCodeAgent" or "Math" in agent_name or "Code" in agent_name:
                    result = self.math_code.handle(action_input, self.state)
                else:
                    result = self.general_qa.handle(action_input, self.state)
                
                results.append(f"Step {step['step']}: {result}")
                
            except Exception as e:
                logger.error(
                    f"Step {step['step']} failed: {str(e)}",
                    component="TerminalChatLoop",
                    error_type="STEP_EXECUTION_ERROR"
                )
                results.append(f"Step {step['step']} failed: {str(e)}")
        
        # Combine results
        combined = "\n\n".join(results)
        
        # Use Gemini to synthesize final answer
        synthesis_prompt = Prompts.synthesis_final_answer(query, combined)
        
        try:
            final_answer = self.general_qa.gemini_client.generate(synthesis_prompt, temperature=0.7)
            return final_answer
        except:
            return combined
    
    def _show_help(self):
        """Show help message."""
        print("""
Available Commands:
  help          - Show this help message
  clear         - Clear conversation history
  debug         - Toggle debug mode (show routing decisions)
  exit / quit   - Exit the chatbot

Example Queries:
  - "Search my notes for RAG architecture"
  - "What is 37^5?"
  - "Summarize https://example.com"
  - "Search the web for Python tutorials"
  - "How many times is 'transformer' in this page?"
        """)

