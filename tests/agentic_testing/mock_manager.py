"""
Mock Manager for tool mocking without re-definition.
This module provides a unified approach to mock tool outputs while preserving tool signatures.
"""

import copy
import logging
from typing import Any, Dict, List, Callable, Optional
from langchain_core.tools import BaseTool


class ToolMockManager:
    """
    Manages tool mocking by wrapping actual tool instances and intercepting their _run methods.
    This preserves tool signatures while allowing fixture-based output control.
    """
    
    def __init__(self, fixtures: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize the ToolMockManager.
        
        Args:
            fixtures: Dictionary containing test fixtures for different tools
            logger: Optional logger instance
        """
        self.fixtures = fixtures
        self.call_history = []
        self.tool_call_counts = {}
        self.logger = logger or logging.getLogger(__name__)
        
    def wrap_tool(self, tool_instance: BaseTool, fixture_key: str, 
                  response_strategy: str = "sequential") -> BaseTool:
        """
        Wrap a tool instance to mock its _run method while preserving all other attributes.
        
        Args:
            tool_instance: The actual tool instance to wrap
            fixture_key: Key to identify which fixtures to use
            response_strategy: How to select responses ("sequential", "conditional", "static")
            
        Returns:
            Wrapped tool instance with mocked _run method
        """
        # Create a copy to avoid modifying the original
        wrapped_tool = copy.copy(tool_instance)
        
        # Store original _run method
        original_run = wrapped_tool._run
        
        # Create mock _run method
        wrapped_tool._run = self._create_mock_run(
            tool_instance.name,
            fixture_key,
            response_strategy,
            original_run
        )
        
        return wrapped_tool
    
    def _create_mock_run(self, tool_name: str, fixture_key: str, 
                        response_strategy: str, original_run: Callable) -> Callable:
        """
        Create a mock _run method that returns fixture data.
        
        Args:
            tool_name: Name of the tool being mocked
            fixture_key: Key to identify fixtures
            response_strategy: Strategy for selecting responses
            original_run: Original _run method for fallback
            
        Returns:
            Mock _run method
        """
        def mock_run(*args, **kwargs):
            # Track the call
            call_info = {
                "tool_name": tool_name,
                "args": args,
                "kwargs": kwargs,
                "fixture_key": fixture_key
            }
            self.call_history.append(call_info)
            
            # Update call count for this tool
            if tool_name not in self.tool_call_counts:
                self.tool_call_counts[tool_name] = 0
            self.tool_call_counts[tool_name] += 1
            
            # Log the call
            self.logger.info(f"🔧 Mock {tool_name} called (#{self.tool_call_counts[tool_name]})")
            self.logger.info(f"   Args: {args}")
            self.logger.info(f"   Kwargs: {kwargs}")
            
            # Get fixture data based on strategy
            fixture_data = self._get_fixture_response(
                tool_name, 
                fixture_key, 
                response_strategy,
                self.tool_call_counts[tool_name] - 1,  # 0-indexed
                *args, 
                **kwargs
            )
            
            if fixture_data is not None:
                self.logger.info(f"   ✓ Returning fixture data")
                return fixture_data
            else:
                self.logger.warning(f"   ⚠️ No fixture data found, using original tool")
                return original_run(*args, **kwargs)
        
        return mock_run
    
    def _get_fixture_response(self, tool_name: str, fixture_key: str, 
                             strategy: str, call_index: int, *args, **kwargs) -> Any:
        """
        Get the appropriate fixture response based on strategy.
        
        Args:
            tool_name: Name of the tool
            fixture_key: Fixture key
            strategy: Response selection strategy
            call_index: Index of this call (0-based)
            *args, **kwargs: Tool arguments
            
        Returns:
            Fixture response data or None if not found
        """
        if fixture_key not in self.fixtures:
            return None
            
        fixture_data = self.fixtures[fixture_key]
        
        if strategy == "sequential":
            # Return responses in sequence
            if isinstance(fixture_data, list) and call_index < len(fixture_data):
                return fixture_data[call_index]
            elif not isinstance(fixture_data, list):
                return fixture_data
                
        elif strategy == "conditional":
            # Select response based on input conditions
            return self._conditional_response(fixture_data, *args, **kwargs)
            
        elif strategy == "static":
            # Always return the same response
            return fixture_data
            
        return None
    
    def _conditional_response(self, fixture_data: Any, *args, **kwargs) -> Any:
        """
        Select fixture response based on input conditions.
        
        Args:
            fixture_data: Available fixture data
            *args, **kwargs: Tool arguments
            
        Returns:
            Appropriate fixture response
        """
        # This can be customized based on specific tool requirements
        # For now, return first matching or default
        if isinstance(fixture_data, dict):
            # Check if there's a mapping based on first argument
            if args and str(args[0]) in fixture_data:
                return fixture_data[str(args[0])]
            elif "default" in fixture_data:
                return fixture_data["default"]
        
        return fixture_data
    
    def get_call_history(self, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get call history for all tools or a specific tool.
        
        Args:
            tool_name: Optional tool name to filter by
            
        Returns:
            List of call information dictionaries
        """
        if tool_name:
            return [call for call in self.call_history if call["tool_name"] == tool_name]
        return self.call_history
    
    def get_call_count(self, tool_name: str) -> int:
        """
        Get the number of times a tool was called.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Number of calls
        """
        return self.tool_call_counts.get(tool_name, 0)
    
    def reset(self):
        """Reset all tracking data."""
        self.call_history = []
        self.tool_call_counts = {}
        self.logger.info("Mock manager reset")