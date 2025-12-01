"""Code execution agent with sandboxed Python execution."""

import ast
import io
import sys
import time
from typing import Optional, Dict, Any, List
from contextlib import redirect_stdout, redirect_stderr
from core.logger import get_logger

logger = get_logger()


class CodeAgent:
    """Safe Python code execution agent."""
    
    # Allowed imports (moderate strictness - allows requests)
    ALLOWED_IMPORTS = {
        "math", "numpy", "scipy", "requests", "duckduckgo_search",
        "re", "json", "datetime", "time", "random", "statistics",
        "collections", "itertools", "functools", "operator"
    }
    
    # Blocked operations
    BLOCKED_ATTRIBUTES = {
        "open": ["__call__"],  # Block file operations
        "os": ["system", "popen", "execv", "execve"],
        "subprocess": ["call", "run", "Popen"],
        "shutil": ["rmtree", "move"],
    }
    
    def __init__(self, timeout: int = 10):
        """
        Initialize CodeAgent.
        
        Args:
            timeout: Execution timeout in seconds
        """
        self.timeout = timeout
        logger.info(f"Initialized CodeAgent with timeout: {timeout}s", component="CodeAgent")
    
    def execute(self, code: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute Python code safely.
        
        Args:
            code: Python code to execute
            context: Optional context variables to inject
            
        Returns:
            Dict with 'result', 'output', 'error', 'execution_time'
        """
        start_time = time.time()
        
        try:
            # Validate code
            self._validate_code(code)
            
            # Create restricted namespace
            namespace = self._create_namespace(context)
            
            # Capture output
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            # Execute code
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, namespace)
            
            execution_time = time.time() - start_time
            
            # Get result (look for 'result' variable or last expression)
            result = namespace.get("result", None)
            output = stdout_capture.getvalue()
            error = stderr_capture.getvalue()
            
            logger.info(
                f"Code executed successfully in {execution_time:.2f}s",
                component="CodeAgent",
                execution_time=execution_time
            )
            
            return {
                "result": result,
                "output": output,
                "error": error if error else None,
                "execution_time": execution_time,
                "success": True
            }
            
        except SyntaxError as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Code syntax error: {str(e)}",
                component="CodeAgent",
                error_type="SYNTAX_ERROR",
                code_snippet=code[:200]
            )
            return {
                "result": None,
                "output": "",
                "error": f"Syntax error: {str(e)}",
                "execution_time": execution_time,
                "success": False
            }
            
        except SecurityError as e:
            execution_time = time.time() - start_time
            logger.critical(
                f"Security violation: {str(e)}",
                component="CodeAgent",
                error_type="SECURITY_VIOLATION",
                code_snippet=code[:200]
            )
            return {
                "result": None,
                "output": "",
                "error": "Operation not allowed for security reasons.",
                "execution_time": execution_time,
                "success": False
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Code execution error: {str(e)}",
                component="CodeAgent",
                error_type="RUNTIME_ERROR",
                code_snippet=code[:200]
            )
            return {
                "result": None,
                "output": "",
                "error": f"Runtime error: {str(e)}",
                "execution_time": execution_time,
                "success": False
            }
    
    def _validate_code(self, code: str):
        """Validate code for security."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(f"Invalid Python syntax: {e}")
        
        # Check for dangerous operations
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._check_import(node)
            
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                self._check_call(node)
            
            # Check for file operations
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "open":
                    # Check if it's a write operation
                    if len(node.args) > 1:
                        mode = self._get_string_value(node.args[1])
                        if mode and ('w' in mode or 'a' in mode or '+' in mode):
                            raise SecurityError("File write operations are not allowed")
    
    def _check_import(self, node: ast.AST):
        """Check if import is allowed."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in self.ALLOWED_IMPORTS:
                    raise SecurityError(f"Import '{alias.name}' is not allowed")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split('.')[0] not in self.ALLOWED_IMPORTS:
                raise SecurityError(f"Import from '{node.module}' is not allowed")
    
    def _check_call(self, node: ast.Call):
        """Check if function call is allowed."""
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                if module_name in self.BLOCKED_ATTRIBUTES:
                    if attr_name in self.BLOCKED_ATTRIBUTES[module_name]:
                        raise SecurityError(f"Call to {module_name}.{attr_name} is not allowed")
    
    def _get_string_value(self, node: ast.AST) -> Optional[str]:
        """Get string value from AST node."""
        if isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None
    
    def _create_namespace(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create restricted execution namespace."""
        # Import __import__ for dynamic imports (needed for duckduckgo_search)
        import builtins
        safe_builtins = {
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "sum": sum,
            "max": max,
            "min": min,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "reversed": reversed,
            "ord": ord,  # ASCII value of character
            "chr": chr,  # Character from ASCII value
            "hex": hex,  # Hexadecimal representation
            "bin": bin,  # Binary representation
            "oct": oct,  # Octal representation
            "__import__": __import__,  # Allow imports for duckduckgo_search
        }
        
        namespace = {
            "__builtins__": safe_builtins
        }
        
        # Add allowed imports
        import math
        namespace["math"] = math
        
        try:
            import numpy
            namespace["numpy"] = numpy
        except ImportError:
            pass
        
        try:
            import scipy
            namespace["scipy"] = scipy
        except ImportError:
            pass
        
        try:
            import requests
            namespace["requests"] = requests
        except ImportError:
            pass
        
        try:
            from duckduckgo_search import DDGS
            namespace["DDGS"] = DDGS
            # Also make the module available
            import duckduckgo_search
            namespace["duckduckgo_search"] = duckduckgo_search
        except ImportError:
            pass
        
        import re
        namespace["re"] = re
        
        import json
        namespace["json"] = json
        
        # Add context variables
        if context:
            namespace.update(context)
        
        return namespace


class SecurityError(Exception):
    """Security violation exception."""
    pass

