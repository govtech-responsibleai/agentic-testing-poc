"""
Configuration for multi-model testing of the FactCheckingAgent.
"""

import os

# Model configurations for testing
MODEL_CONFIGS = [
    {
        "name": "GPT-4o",
        "model_id": "azure/gpt-4o-eastus",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-4o Mini",
        "model_id": "azure/gpt-4o-mini-eastus",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-4.1",
        "model_id": "azure/gpt-4.1-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-4.1 Mini",
        "model_id": "azure/gpt-4.1-mini-southeastasia",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-4.1 Nano",
        "model_id": "azure/gpt-4.1-nano-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "o3 Mini",
        "model_id": "azure/o3-mini-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    # {
    #     "name": "o4 Mini", # Not added to LiteLLM proxy yet
    #     "model_id": "o4-mini-2025-04-16",
    #     "api_key_env": "LITELLM_PROXY_API_KEY",
    #     "base_url": "https://litellm-stg.aip.gov.sg/",
    # },
    {
        "name": "GPT-5",
        "model_id": "azure/gpt-5-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-5 Mini",
        "model_id": "azure/gpt-5-mini-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-5 Nano",
        "model_id": "azure/gpt-5-nano-eastus2",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-OSS 20b",
        "model_id": "openai.gpt-oss-20b-1:0",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "GPT-OSS 120b",
        "model_id": "openai.gpt-oss-120b-1:0",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Gemini 2.0 Flash 001",
        "model_id": "gemini-2.0-flash-001",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Gemini 2.5 Flash Lite",
        "model_id": "gemini-2.5-flash-lite",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Gemini 2.5 Flash",
        "model_id": "gemini-2.5-flash",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Claude 3.5 Haiku",
        "model_id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Claude 4 Sonnet",
        "model_id": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
    {
        "name": "Claude 4.1 Opus",
        "model_id": "us.anthropic.claude-opus-4-1-20250805-v1:0",
        "api_key_env": "LITELLM_PROXY_API_KEY",
        "base_url": "https://litellm-stg.aip.gov.sg/",
    },
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
            print(
                f"⚠️ Skipping {config['name']} - No API key found in {config['api_key_env']}"
            )
    return active_models


def validate_config():
    """Validate the test configuration."""
    if not MODEL_CONFIGS:
        raise ValueError("No models configured for testing")

    if TEST_CONFIG["runs_per_test"] < 1:
        raise ValueError("runs_per_test must be at least 1")

    return True
