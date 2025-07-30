"""
Retry wrappers for various tools to handle rate limiting and other transient errors.
"""

from typing import List, Dict, Any, Optional, Union, Type, Literal, Callable
import json
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
import requests
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import BaseTool, ToolException
from analysis.pydantic_models import DDGInput



# class DuckDuckGoSearchTool(BaseTool):
#     """
#     A DuckDuckGo search tool with built-in retry functionality using tenacity.
#     This implementation inherits from langchain's BaseTool to be compatible with LangGraph.
    
#     Setup:
#         Install ``duckduckgo-search`` and ``tenacity``.

#         .. code-block:: bash

#             pip install -U duckduckgo-search tenacity
#     """
    
#     name: str = "duckduckgo_search"
#     description: str = "A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events. Input should be a search query."
#     args_schema: Type[BaseModel] = DDGInput
    
#     # Define additional fields
#     max_results: int = 4
#     backend: str = "text"
#     keys_to_include: Optional[List[str]] = None
#     results_separator: str = ", "
#     output_format: Literal["string", "json", "list"] = "string"
#     max_attempts: int = 5
#     min_wait: int = 2
#     max_wait: int = 60
#     api_wrapper: Any = None
#     domains: Optional[List[str]] = None
    
#     def __init__(
#         self,
#         name: str = "duckduckgo_search",
#         description: str = "A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events. Input should be a search query.",
#         max_results: int = 4,
#         backend: str = "text",
#         keys_to_include: Optional[List[str]] = None,
#         results_separator: str = ", ",
#         output_format: Literal["string", "json", "list"] = "string",
#         max_attempts: int = 5,
#         min_wait: int = 2,
#         max_wait: int = 60,
#         # domains: Optional[List[str]] = None,
#         **api_wrapper_kwargs
#     ):
#         """
#         Initialize the DuckDuckGoSearchTool with retry functionality.
        
#         Args:
#             name: The name of the tool
#             description: The description of the tool
#             max_results: Maximum number of results to return
#             backend: The backend to use for search ("text", "news", "images")
#             keys_to_include: Which keys from each result to include. If None all keys are included.
#             results_separator: Character for separating results.
#             output_format: Output format of the search results ("string", "json", "list")
#             max_attempts: Maximum number of retry attempts
#             min_wait: Minimum wait time between retries in seconds
#             max_wait: Maximum wait time between retries in seconds
#             **api_wrapper_kwargs: Additional arguments to pass to DuckDuckGoSearchAPIWrapper
#             # domains: List of domains to restrict search to
#         """
#         super().__init__(name=name, description=description)
#         self.max_results = max_results
#         self.backend = backend
#         self.keys_to_include = keys_to_include
#         self.results_separator = results_separator
#         self.output_format = output_format
#         self.max_attempts = max_attempts
#         self.min_wait = min_wait
#         self.max_wait = max_wait
#         # self.domains = domains
#         # Initialize the API wrapper
#         self.api_wrapper = DuckDuckGoSearchAPIWrapper(**api_wrapper_kwargs)
    
#     @retry(
#         retry=retry_if_exception_type((
#             requests.exceptions.RequestException,
#             requests.exceptions.Timeout,
#             requests.exceptions.ConnectionError,
#             requests.exceptions.HTTPError,
#             requests.exceptions.TooManyRedirects,
#             Exception  # Catch-all for any other exceptions
#         )),
#         wait=wait_exponential(multiplier=1, min=2, max=60),
#         stop=stop_after_attempt(5),
#         reraise=True
#     )
#     def _get_results(self, query: str) -> List[Dict[str, str]]:
#         """
#         Get search results with retry logic.
        
#         Args:
#             query: The search query
            
#         Returns:
#             List of search result dictionaries
#         """
#         # if self.domains is not None:
#         #     query += " "  + " site:".join(self.domains)
        
#         # print(f"Query: {query}")
#         return self.api_wrapper.results(query, self.max_results, source=self.backend, )
    
#     def _run(self, query: str) -> Union[List[Dict], str]:
#         """
#         Run the DuckDuckGo search tool.
        
#         Args:
#             query: The search query
            
#         Returns:
#             The search results in the specified output format
#         """
#         try:
#             # Apply retry logic to the API call
#             @retry(
#                 retry=retry_if_exception_type((
#                     requests.exceptions.RequestException,
#                     requests.exceptions.Timeout,
#                     requests.exceptions.ConnectionError,
#                     requests.exceptions.HTTPError,
#                     requests.exceptions.TooManyRedirects,
#                     Exception  # Catch-all for any other exceptions
#                 )),
#                 wait=wait_exponential(multiplier=1, min=self.min_wait, max=self.max_wait),
#                 stop=stop_after_attempt(self.max_attempts),
#                 reraise=True
#             )
#             def _run_with_retry():
#                 raw_results = self.api_wrapper.results(
#                     query, self.max_results, source=self.backend
#                 )
#                 return raw_results
            
#             # Get results with retry
#             raw_results = _run_with_retry()
            
#             # Filter results based on keys_to_include
#             results = [
#                 {
#                     k: v
#                     for k, v in d.items()
#                     if not self.keys_to_include or k in self.keys_to_include
#                 }
#                 for d in raw_results
#             ]
            
#             # Format results based on output_format
#             if self.output_format == "list":
#                 return results
#             elif self.output_format == "json":
#                 return json.dumps(results)
#             elif self.output_format == "string":
#                 res_strs = [", ".join([f"{k}: {v}" for k, v in d.items()]) for d in results]
#                 return self.results_separator.join(res_strs)
#             else:
#                 raise ValueError(
#                     f"Invalid output_format: {self.output_format}. "
#                     "Needs to be one of 'string', 'json', 'list'."
#                 )
#         except Exception as e:
#             raise ToolException(f"Error in DuckDuckGo search: {str(e)}")


# class DuckDuckGoSearchResultsTool(DuckDuckGoSearchTool):
#     """
#     A DuckDuckGo search tool that returns results in JSON format.
#     This is a convenience class that sets different defaults.
#     """
    
#     name: str = "duckduckgo_results_json"
#     description: str = "A wrapper around Duck Duck Go Search. Useful for when you need to answer questions about current events. Input should be a search query."
#     # domains: Optional[List[str]] = None
    
#     def __init__(
#         self,
#         name: str = "duckduckgo_results_json",
#         description: str = "A wrapper around Duck Duck Go Search. Useful for when you need to answer questions about current events. Input should be a search query.",
#         output_format: Literal["string", "json", "list"] = "list",
#         # domains: Optional[List[str]] = None,
#         **kwargs
#     ):
#         """
#         Initialize the DuckDuckGoSearchResultsTool.
        
#         Args:
#             name: The name of the tool
#             description: The description of the tool
#             output_format: Output format of the search results
#             **kwargs: Additional arguments to pass to DuckDuckGoSearchTool
#         """
#         super().__init__(
#             name=name,
#             description=description,
#             output_format=output_format,
#             # domains=domains,
#             **kwargs
#         )


# # For backward compatibility with existing code
# RetryDuckDuckGoSearchResults = DuckDuckGoSearchResultsTool
# RetryDuckDuckGoSearchTool = DuckDuckGoSearchTool