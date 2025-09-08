from typing import Any, Dict
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from langchain_openai import ChatOpenAI
import openai

# Configuration constants
RETRY_CONFIG = {
    "MAX_RETRIES": 5,
    "MIN_RETRY_DELAY": 2,
    "MAX_RETRY_DELAY": 60,
    "URL_CONTENT_LIMIT": 5000,
    "REQUEST_TIMEOUT": 5,
}

class LLMClient:
    """Client for interacting with the language model with retry capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM client with configuration."""
        self.config = config
        self.llm = ChatOpenAI(
            model=self.config["MODEL_NAME"],
            # temperature=0,
            api_key=self.config["API_KEY"],
            base_url=self.config["BASE_URL"],
            default_headers=self.config["DEFAULT_HEADERS"] if "DEFAULT_HEADERS" in self.config else {}
        )
    
    @retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIError, openai.APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=RETRY_CONFIG["MIN_RETRY_DELAY"], max=RETRY_CONFIG["MAX_RETRY_DELAY"]),
        stop=stop_after_attempt(RETRY_CONFIG["MAX_RETRIES"])
    )
    def call_with_retry(self, func, *args, **kwargs):
        """Call a function with retry logic for handling rate limit errors."""
        return func(*args, **kwargs)
    
    def invoke(self, messages):
        """Invoke the LLM with the given messages."""
        return self.call_with_retry(self.llm.invoke, messages)