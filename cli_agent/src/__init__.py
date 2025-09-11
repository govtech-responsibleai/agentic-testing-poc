"""Agent stub module for testing"""
# Re-export the OpenAI Agents SDK classes for testing
try:
    from agents import Agent, Runner, function_tool, SQLiteSession
    __all__ = ['Agent', 'Runner', 'function_tool', 'SQLiteSession']
except ImportError:
    # Fallback for when openai agents is not available
    class MockRunner:
        def __init__(self):
            pass
        
        async def run(self, *args, **kwargs):
            return "Mock response"
    
    Runner = MockRunner
    Agent = MockRunner
    function_tool = lambda f: f
    SQLiteSession = MockRunner
    __all__ = ['Agent', 'Runner', 'function_tool', 'SQLiteSession']
