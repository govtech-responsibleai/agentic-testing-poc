
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool


# Try to fetch content from the URL
@tool
def fetch_url_content(url: str, char_limit: int = 5000) -> str:
    """
    Fetch content from a given URL.
    
    Args:
        url (str): The URL to fetch content from.
        char_limit (int, optional): Maximum number of characters to return. Defaults to 5000.
        
    Returns:
        str: The extracted text content from the URL, limited to char_limit characters.
             Returns None if the URL is invalid or content cannot be fetched.
    """
    try:        
        if url:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract text from paragraphs
                paragraphs = soup.find_all('p')
                page_content = "\n".join([p.get_text() for p in paragraphs])
                if page_content:
                        return f"Full Content: {page_content[:char_limit]}..." # Limit content length
                else:
                    return None
        else:
            raise ValueError(f"URL must be valid. Current URL: {url}")
        
    except Exception as e:
        print(f"Failed to fetch URL content: {str(e)}")
        return None