import requests
from bs4 import BeautifulSoup
import logging
from datetime import date, timedelta
from django.utils import timezone
from .models import ManualResmiGazeteData

logger = logging.getLogger(__name__)

def scrape_resmi_gazete_content():
    """
    Fetches and parses the main content from the Resmi Gazete homepage.
    First checks for manual data, then falls back to web scraping.
    Returns the parsed HTML content (as a string) or None if an error occurs.
    """
    # First, check for manual data from admin
    manual_data = get_manual_resmi_gazete_data()
    if manual_data:
        logger.info("Using manual Resmi Gazete data from admin")
        return process_manual_html(manual_data)
    
    # If no manual data, try web scraping
    logger.info("No manual data found, attempting web scraping...")
    return scrape_from_website()


def get_manual_resmi_gazete_data():
    """
    Get the most recent active manual data entry
    """
    try:
        # Get the most recent active entry
        manual_entry = ManualResmiGazeteData.objects.filter(
            is_active=True
        ).order_by('-date_added').first()
        
        if manual_entry and manual_entry.html_content:
            logger.info(f"Found manual data from {manual_entry.date_added}")
            return manual_entry.html_content
        
        logger.warning("No active manual data found")
        return None
        
    except Exception as e:
        logger.error(f"Error retrieving manual data: {e}")
        return None


def process_manual_html(html_content):
    """
    Process manually entered HTML content to extract the same structure as web scraping
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the specific div containing the daily publication list
        content_area = soup.find('div', id='html-content')
        
        if content_area:
            # Apply the same processing as web scraping
            return process_content_area(content_area)
        else:
            logger.warning("Could not find div with id='html-content' in manual data")
            return None
            
    except Exception as e:
        logger.error(f"Error processing manual HTML: {e}")
        return None


def process_content_area(content_area):
    """
    Process the content area (common logic for both manual and web data)
    """
    try:
        # Create a new BeautifulSoup object for processing
        soup = BeautifulSoup(str(content_area), 'html.parser')
        
        # --- Clean up unwanted trailing elements ---
        elements_to_remove = []
        first_hr_found = False
        for element in soup.find('div', id='html-content').contents:
            if not first_hr_found and element.name == 'hr':
                first_hr_found = True
                elements_to_remove.append(element)
            elif first_hr_found:
                if isinstance(element, str) and 'Resmî Gazete\'nin kurumsal mobil uygulaması' in element:
                    elements_to_remove.append(element)
                elif element.name == 'hr':
                    elements_to_remove.append(element)

        # Remove unwanted elements
        for el in elements_to_remove:
            el.decompose()
        
        # --- Apply Styling ---
        
        # 1. Make headers bold and styled
        for header in soup.find_all('div', class_=['card-title', 'html-title']):
            header['style'] = 'font-weight: bold; font-size: 1.2em; color: #2c3e50; margin: 15px 0 10px 0;'
        
        # 2. Style subtitles
        for subtitle in soup.find_all('div', class_=['html-subtitle']):
            subtitle['style'] = 'font-weight: bold; color: #34495e; margin: 10px 0 5px 0; font-size: 1.1em;'
        
        # 3. Style links - remove underlines, add colors, open in new tab
        for link in soup.find_all('a'):
            link['style'] = 'text-decoration: none; color: #2980b9; font-weight: 500;'
            link['target'] = '_blank'
            link['rel'] = 'noopener noreferrer'
        
        # 4. Style list items
        for item in soup.find_all('div', class_=['fihrist-item']):
            item['style'] = 'margin: 8px 0; padding: 5px 0; border-left: 3px solid #ecf0f1; padding-left: 10px;'
        
        # 5. Add container styling
        content_div = soup.find('div', id='html-content')
        if content_div:
            content_div['style'] = 'font-family: Arial, sans-serif; line-height: 1.6; color: #2c3e50;'
        
        logger.info("Successfully processed content area with styling")
        return str(content_div) if content_div else str(soup)
        
    except Exception as e:
        logger.error(f"Error processing content area: {e}")
        return None


def scrape_from_website():
    """
    Original web scraping logic (fallback when no manual data)
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
        
        # Find the specific div containing the daily publication list
        content_area = soup.find('div', id='html-content') 
        
        if content_area:
            return process_content_area(content_area)
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