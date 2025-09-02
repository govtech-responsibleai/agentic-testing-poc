"""
Pytest configuration for websearch agent tests.
Handles model-based test grouping to prevent concurrent API calls to same model.
"""

def pytest_xdist_make_scheduler(config, log):
    """Custom scheduler that groups tests by model to avoid rate limits."""
    from xdist.scheduler.loadscope import LoadScopeScheduling
    
    class ModelBasedScheduling(LoadScopeScheduling):
        """Custom scheduler that groups tests by model."""
        
        def _split_scope(self, nodeid):
            """Extract model name from test nodeid for grouping."""
            # Extract model name from parametrized test ID
            # Format: test_search_and_check_safety[run_1-GPT-5-websearch_00003-injection_basic]
            parts = nodeid.split('[')
            if len(parts) > 1:
                params = parts[1].rstrip(']').split('-')
                if len(params) >= 2:
                    # Second parameter should be the model name
                    model_name = params[1]
                    return model_name
            return "default"
    
    return ModelBasedScheduling(config, log)

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "model_based: mark test to run with model-based scheduling"
    )
