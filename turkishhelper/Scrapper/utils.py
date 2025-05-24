import requests
from bs4 import BeautifulSoup
import logging
from datetime import date

logger = logging.getLogger(__name__)

def scrape_resmi_gazete_content():
    """
    Fetches and parses the main content from the Resmi Gazete homepage.
    Returns the parsed HTML content (as a string) or None if an error occurs.
    """
    url = "https://www.resmigazete.gov.tr/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # IMPORTANT: verify=False bypasses SSL certificate verification.
        # This is insecure for production. For a production system, ensure your
        # server's CA certificates are up to date or the target site has a valid SSL cert.
        # For development/testing on a trusted site, this can be a temporary workaround.
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        
        # Ensure the content is decoded correctly (Resmi Gazete uses UTF-8)
        response.encoding = response.apparent_encoding # Detect encoding or default to UTF-8
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- Content Extraction Logic ---
        # Find the specific div containing the daily publication list
        content_area = soup.find('div', id='html-content') 
        
        if content_area:
            # --- Clean up unwanted trailing elements within the content_area ---
            elements_to_remove = []
            first_hr_found = False
            for element in content_area.contents: # Iterate direct children
                if not first_hr_found and element.name == 'hr':
                    first_hr_found = True
                    elements_to_remove.append(element)
                elif first_hr_found:
                    # If it's the specific text node or another hr, mark for removal
                    if isinstance(element, str) and 'Resmî Gazete\'nin kurumsal mobil uygulaması' in element:
                        elements_to_remove.append(element)
                    elif element.name == 'hr':
                        elements_to_remove.append(element)
                    # Add other specific tags to remove here if needed

            # Decompose the marked elements
            for el in elements_to_remove:
                el.decompose()
            # --- End clean up ---

            # Apply styling modifications directly to the parsed elements
            # Make headers bold
            for header in content_area.find_all('div', class_=[ 'card-title', 'html-subtitle']):
                if header.string:
                    header.string.wrap(soup.new_tag('strong'))
            
            # Remove underline from links, dim color, and ensure they open in a new tab
            for link in content_area.find_all('a'):
                link['style'] = 'text-decoration: none; color: #555555;' # Added dim color
                link['target'] = '_blank' # Good practice for external links in emails

            # Return the modified HTML content as a string
            return str(content_area) 
        else:
            logger.warning("Could not find the div with id='html-content' on Resmi Gazete.")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"An error occurred during scraping: {e}")
        return None

if __name__ == '__main__':
    # Example usage when running the script directly
    content = scrape_resmi_gazete_content()
    if content:
        print("Successfully scraped content (first 500 chars):")
        print(content[:500] + "...")
    else:
        print("Failed to scrape content.")