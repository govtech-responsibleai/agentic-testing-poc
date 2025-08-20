"""
Configuration for multi-model testing of the FactCheckingAgent.
"""

import os

# Model configurations for testing
MODEL_CONFIGS = [
    {
        "name": "GPT-4o",
        "model_id": "gpt-4o-2024-11-20",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-4o Mini",
        "model_id": "gpt-4o-mini-2024-07-18",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-4.1",
        "model_id": "gpt-4.1-2025-04-14",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-4.1 Mini",
        "model_id": "gpt-4.1-mini-2025-04-14", 
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-4.1 Nano",
        "model_id": "gpt-4.1-nano-2025-04-14",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "o3",
        "model_id": "o3-2025-04-16",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "o4 Mini",
        "model_id": "o4-mini-2025-04-16",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-5",
        "model_id": "gpt-5-2025-08-07",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-5 Mini",
        "model_id": "gpt-5-mini-2025-08-07",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    },
    {
        "name": "GPT-5 Nano",
        "model_id": "gpt-5-nano-2025-08-07",
        "api_key_env": "WORK_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1"
    }
]

# Test execution configuration
TEST_CONFIG = {
    "runs_per_test": 5,  # Number of times to run each test per model
    "fixtures_to_test": [],  # None means test all fixtures, or specify list like ["websearch_00003"]
    "save_results": True,
    "results_dir": "tests/agentic_testing/results",
    "generate_summary": True,
    "timeout_seconds": 120,  # Timeout per test
    "skip_if_no_api_key": True,  # Skip tests if API key not found
}


def get_active_models():
    """Get list of models to test based on available API keys."""
    active_models = []
    for config in MODEL_CONFIGS:
        api_key = os.getenv(config["api_key_env"])
        if api_key or not TEST_CONFIG["skip_if_no_api_key"]:
            active_models.append(config)
        else:
            print(f"⚠️ Skipping {config['name']} - No API key found in {config['api_key_env']}")
    return active_models

def validate_config():
    """Validate the test configuration."""
    if not MODEL_CONFIGS:
        raise ValueError("No models configured for testing")
    
    if TEST_CONFIG["runs_per_test"] < 1:
        raise ValueError("runs_per_test must be at least 1")
    
    return True