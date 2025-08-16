"""
Multi-model test configuration for safety testing across different LLMs.
This module defines configurations for testing with various model providers.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ModelProvider(Enum):
    """Enum for model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    name: str                      # Display name for the model
    provider: ModelProvider        # Provider type
    model_name: str               # Actual model identifier
    api_key_env: str              # Environment variable for API key
    base_url: str                 # API base URL
    enabled: bool = True          # Whether to include in tests
    timeout: int = 120            # Request timeout in seconds
    max_retries: int = 3          # Max retry attempts
    temperature: float = 1.0      # Model temperature
    additional_params: Optional[Dict[str, Any]] = None  # Extra parameters


# Model configurations for testing
MODEL_CONFIGS: List[ModelConfig] = [
    
    # OpenAI Models
    ModelConfig(
        name="GPT-4 Turbo",
        provider=ModelProvider.OPENAI,
        model_name="gpt-4-turbo-preview",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        enabled=True
    ),
    ModelConfig(
        name="GPT-4",
        provider=ModelProvider.OPENAI,
        model_name="gpt-4",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        enabled=False  # Disabled by default due to cost
    ),
    ModelConfig(
        name="GPT-3.5 Turbo",
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        api_key_env="OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        enabled=True
    ),
    
    # Azure OpenAI Models
    ModelConfig(
        name="Azure GPT-4",
        provider=ModelProvider.AZURE,
        model_name="azure/gpt-4o",
        api_key_env="AZURE_OPENAI_API_KEY",
        base_url="https://litellm-stg.aip.gov.sg",  # From .env.sample
        enabled=False  # Enable if Azure is configured
    ),
    
    # Anthropic Models (via OpenAI-compatible endpoint)
    ModelConfig(
        name="Claude 3 Opus",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-opus-20240229",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com/v1",
        enabled=False,  # Enable if Anthropic API is available
        additional_params={"anthropic_version": "2024-01-01"}
    ),
    ModelConfig(
        name="Claude 3 Sonnet",
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        api_key_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com/v1",
        enabled=False,
        additional_params={"anthropic_version": "2024-01-01"}
    ),
    
    # Local/Custom Models
    ModelConfig(
        name="Local LLM",
        provider=ModelProvider.LOCAL,
        model_name="local-model",
        api_key_env="LOCAL_API_KEY",  # May not be needed
        base_url="http://localhost:8000",
        enabled=False  # Enable if local model is running
    ),
    
    # Work-specific configuration (from current test)
    ModelConfig(
        name="Work GPT-4 Nano",
        provider=ModelProvider.OPENAI,
        model_name="gpt-4.1-nano",
        api_key_env="WORK_OPENAI_API_KEY",
        base_url="https://api.openai.com/v1",
        enabled=True  # This was in the original test
    ),
]


def get_enabled_configs() -> List[ModelConfig]:
    """Get list of enabled model configurations."""
    return [config for config in MODEL_CONFIGS if config.enabled]


def get_config_by_name(name: str) -> Optional[ModelConfig]:
    """Get a specific model configuration by name."""
    for config in MODEL_CONFIGS:
        if config.name == name:
            return config
    return None


def validate_config(config: ModelConfig) -> bool:
    """
    Validate that a model configuration has required API key.
    
    Args:
        config: Model configuration to validate
        
    Returns:
        True if configuration is valid and can be used
    """
    # Check if API key environment variable exists
    api_key = os.getenv(config.api_key_env)
    if not api_key:
        return False
    
    # Additional validation could go here
    # e.g., checking if endpoint is reachable
    
    return True


def get_valid_configs() -> List[ModelConfig]:
    """Get list of enabled and valid model configurations."""
    valid_configs = []
    for config in get_enabled_configs():
        if validate_config(config):
            valid_configs.append(config)
        else:
            print(f"⚠️ Skipping {config.name}: Missing {config.api_key_env}")
    
    return valid_configs


def create_llm_config(model_config: ModelConfig) -> Dict[str, Any]:
    """
    Create LLMClient configuration dictionary from ModelConfig.
    
    Args:
        model_config: Model configuration
        
    Returns:
        Dictionary suitable for LLMClient initialization
    """
    config = {
        "MODEL_NAME": model_config.model_name,
        "API_KEY": os.getenv(model_config.api_key_env),
        "BASE_URL": model_config.base_url,
    }
    
    # Add any additional parameters
    if model_config.additional_params:
        config.update(model_config.additional_params)
    
    return config


# Test fixture selection
TEST_CASE_SELECTION = {
    "quick_test": ["websearch_00003"],  # Single test for quick validation
    "full_test": None,  # Use all available test fixtures
    "safety_critical": ["websearch_00003", "websearch_00004"],  # Critical safety tests
}


# Results configuration
RESULTS_CONFIG = {
    "output_dir": "tests/agentic_testing/results",
    "csv_filename_template": "multi_model_results_{timestamp}.csv",
    "json_summary_template": "summary_report_{timestamp}.json",
    "detailed_logs": True,
    "save_individual_reports": True,
}