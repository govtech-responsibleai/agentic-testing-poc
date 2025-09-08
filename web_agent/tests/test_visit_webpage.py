import pytest
from unittest.mock import patch, MagicMock
from analysis.tools.visit_page_tool import fetch_url_content

def test_fetch_url_content_success():
    """Test successful URL content fetching"""
    # Mock response with HTML content
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <body>
            <p>First paragraph</p>
            <p>Second paragraph</p>
            <div>Not a paragraph</div>
        </body>
    </html>
    """
    
    with patch('requests.get', return_value=mock_response):
        result = fetch_url_content.run("https://example.com")
        
        assert result is not None
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "Not a paragraph" not in result
        assert result.startswith("Full Content:")

def test_fetch_url_content_char_limit():
    """Test character limit functionality"""
    # Mock response with long content
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><p>" + "a" * 10000 + "</p></body></html>"
    
    with patch('requests.get', return_value=mock_response):
        result = fetch_url_content.run("https://example.com")
        
        assert result is not None
        assert len(result) <= 5000 + len("Full Content: ...")  # Default char_limit is 5000
        assert result.endswith("...")

def test_fetch_url_content_empty_paragraphs():
    """Test handling of pages with no paragraphs"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><div>No paragraphs here</div></body></html>"
    
    with patch('requests.get', return_value=mock_response):
        result = fetch_url_content.run("https://example.com")
        
        assert result is None

def test_fetch_url_content_invalid_url():
    """Test handling of invalid URL"""
    with patch('requests.get', side_effect=Exception("Invalid URL")):
        result = fetch_url_content.run("invalid-url")
        
        assert result is None

def test_fetch_url_content_request_timeout():
    """Test handling of request timeout"""
    with patch('requests.get', side_effect=Exception("Timeout")):
        result = fetch_url_content.run("https://example.com")
        
        assert result is None

def test_fetch_url_content_http_error():
    """Test handling of HTTP errors"""
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch('requests.get', return_value=mock_response):
        result = fetch_url_content.run("https://example.com")
        
        assert result is None
