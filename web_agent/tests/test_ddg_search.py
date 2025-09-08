import pytest
from unittest.mock import patch, MagicMock
from analysis.tools.ddg_tool import DuckDuckGoSearchTool, DuckDuckGoSearchResultsTool
from langchain_community.utilities.duckduckgo_search import DuckDuckGoSearchAPIWrapper

def test_ddg_search_tool_initialization():
    """Test initialization of DuckDuckGoSearchTool with default parameters"""
    tool = DuckDuckGoSearchTool()
    
    assert tool.name == "duckduckgo_search"
    assert tool.description == "A wrapper around DuckDuckGo Search. Useful for when you need to answer questions about current events. Input should be a search query."
    assert tool.max_results == 4
    assert tool.backend == "text"
    assert tool.output_format == "string"
    assert tool.max_attempts == 5
    assert tool.min_wait == 2
    assert tool.max_wait == 60

def test_ddg_search_tool_custom_initialization():
    """Test initialization of DuckDuckGoSearchTool with custom parameters"""
    tool = DuckDuckGoSearchTool(
        name="custom_search",
        description="Custom search tool",
        max_results=10,
        backend="news",
        output_format="json",
        max_attempts=3,
        min_wait=1,
        max_wait=30
    )
    
    assert tool.name == "custom_search"
    assert tool.description == "Custom search tool"
    assert tool.max_results == 10
    assert tool.backend == "news"
    assert tool.output_format == "json"
    assert tool.max_attempts == 3
    assert tool.min_wait == 1
    assert tool.max_wait == 30

def test_ddg_search_results_tool_initialization():
    """Test initialization of DuckDuckGoSearchResultsTool"""
    tool = DuckDuckGoSearchResultsTool()
    
    assert tool.name == "duckduckgo_results_json"
    assert tool.output_format == "list"
    assert isinstance(tool.api_wrapper, DuckDuckGoSearchAPIWrapper)

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_string_output(mock_api_wrapper):
    """Test DuckDuckGo search with string output format"""
    # Mock search results
    mock_results = [
        {"title": "Test Result 1", "link": "https://example1.com", "snippet": "Snippet 1"},
        {"title": "Test Result 2", "link": "https://example2.com", "snippet": "Snippet 2"}
    ]
    mock_api_wrapper.return_value.results.return_value = mock_results
    
    tool = DuckDuckGoSearchTool(output_format="string")
    result = tool._run("test query")
    
    assert isinstance(result, str)
    assert "Test Result 1" in result
    assert "https://example1.com" in result
    assert "Snippet 1" in result
    assert "Test Result 2" in result
    assert "https://example2.com" in result
    assert "Snippet 2" in result

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_json_output(mock_api_wrapper):
    """Test DuckDuckGo search with JSON output format"""
    # Mock search results
    mock_results = [
        {"title": "Test Result 1", "link": "https://example1.com", "snippet": "Snippet 1"},
        {"title": "Test Result 2", "link": "https://example2.com", "snippet": "Snippet 2"}
    ]
    mock_api_wrapper.return_value.results.return_value = mock_results
    
    tool = DuckDuckGoSearchTool(output_format="json")
    result = tool._run("test query")
    
    assert isinstance(result, str)
    import json
    parsed_result = json.loads(result)
    assert len(parsed_result) == 2
    assert parsed_result[0]["title"] == "Test Result 1"
    assert parsed_result[1]["title"] == "Test Result 2"

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_list_output(mock_api_wrapper):
    """Test DuckDuckGo search with list output format"""
    # Mock search results
    mock_results = [
        {"title": "Test Result 1", "link": "https://example1.com", "snippet": "Snippet 1"},
        {"title": "Test Result 2", "link": "https://example2.com", "snippet": "Snippet 2"}
    ]
    mock_api_wrapper.return_value.results.return_value = mock_results
    
    tool = DuckDuckGoSearchTool(output_format="list")
    result = tool._run("test query")
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Test Result 1"
    assert result[1]["title"] == "Test Result 2"

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_with_keys_to_include(mock_api_wrapper):
    """Test DuckDuckGo search with specific keys to include"""
    # Mock search results
    mock_results = [
        {"title": "Test Result 1", "link": "https://example1.com", "snippet": "Snippet 1", "extra": "data"},
        {"title": "Test Result 2", "link": "https://example2.com", "snippet": "Snippet 2", "extra": "data"}
    ]
    mock_api_wrapper.return_value.results.return_value = mock_results
    
    tool = DuckDuckGoSearchTool(keys_to_include=["title", "link"], output_format="list")
    result = tool._run("test query")
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert set(result[0].keys()) == {"title", "link"}
    assert "snippet" not in result[0]
    assert "extra" not in result[0]

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_error_handling(mock_api_wrapper):
    """Test DuckDuckGo search error handling"""
    mock_api_wrapper.return_value.results.side_effect = Exception("Search failed")
    
    tool = DuckDuckGoSearchTool()
    with pytest.raises(Exception) as exc_info:
        tool._run("test query")
    
    assert "Search failed" in str(exc_info.value)

@patch('analysis.tools.ddg_tool.DuckDuckGoSearchAPIWrapper')
def test_ddg_search_with_custom_separator(mock_api_wrapper):
    """Test DuckDuckGo search with custom results separator"""
    # Mock search results
    mock_results = [
        {"title": "Test Result 1", "link": "https://example1.com", "snippet": "Snippet 1"},
        {"title": "Test Result 2", "link": "https://example2.com", "snippet": "Snippet 2"}
    ]
    mock_api_wrapper.return_value.results.return_value = mock_results
    
    tool = DuckDuckGoSearchTool(results_separator=" | ", output_format="string")
    result = tool._run("test query")
    
    assert isinstance(result, str)
    assert " | " in result
    assert result.count(" | ") == 1  # Should have one separator between two results
