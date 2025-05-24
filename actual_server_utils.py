import requests
from bs4 import BeautifulSoup
import logging
from datetime import date
import random
import re # Added import

logger = logging.getLogger(__name__)

# ---- START ADDITION: Helper function to extract year ----
def extract_year_from_li(li_tag):
    if not li_tag:
        return 0 # Default for missing tags
    text = li_tag.get_text(strip=True)
    match = re.match(r"^\s*(\d{3,4})", text) # Matches 3 or 4 digit year at the start
    if match:
        return int(match.group(1))
    return 0 # Default if no year is found at the beginning
# ---- END ADDITION ----

def scrape_resmi_gazete():
    """
    Fetches and parses the main content from the Resmi Gazete homepage.
    Returns the parsed HTML content (as a string) or None if an error occurs.
    """
    url = "https://www.resmigazete.gov.tr/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # WARNING: verify=False bypasses SSL certificate verification.
        # This is insecure and should ONLY be used for temporary local testing 
        # if you trust the target site and understand the risks. 
        # Do NOT use verify=False in production.
        # The proper solution is to fix the local certificate store.
        response = requests.get(url, headers=headers, timeout=60, verify=False) # Add User-Agent header
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        
        # Ensure the content is decoded correctly (Resmi Gazete uses UTF-8)
        response.encoding = response.apparent_encoding # Detect encoding or default to UTF-8

        # ---- START ADDITION: Log raw HTML ----
        logger.info(f"Raw HTML from Resmi Gazete: {response.text}")
        # ---- END ADDITION ----

        # ---- START ADDITION: Direct print for shell debugging ----
        try:
            print(response.text)
        except Exception as e:
            print(f"Error printing raw HTML for shell debug: {e}")
        # ---- END ADDITION ----
        
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
    # ---- START ADDITION: Basic logging configuration for script execution ----
    import logging # Make sure logging is imported if not already at top level for this block
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # ---- END ADDITION ----

    # Example usage when running the script directly
    content = scrape_resmi_gazete()
    if content:
        print("Successfully scraped content (first 500 chars):")
        print(content[:500] + "...")
    else:
        print("Failed to scrape content.") 

MONTH_TRANSLATIONS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

def get_wikipedia_today_in_history_url():
    """
    Generates the Turkish Wikipedia URL for "Today in History" for the current date.
    Example: https://tr.wikipedia.org/wiki/23_Mayıs
    """
    today = date.today()
    day = today.day
    month_name = MONTH_TRANSLATIONS_TR[today.month]
    return f"https://tr.wikipedia.org/wiki/{day}_{month_name}"

def scrape_wikipedia_today_in_history():
    """
    Fetches and parses the "Today in History" content from Turkish Wikipedia.
    Extracts H2 headings for "Olaylar", "Doğumlar", "Ölümler" (within their parent div.mw-heading) 
    and their subsequent UL/LI content.
    Returns the parsed HTML content as a string or None if an error occurs.
    """
    url = get_wikipedia_today_in_history_url()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', class_='mw-parser-output')
        if not content_div:
            logger.warning(f"Could not find the main content div 'mw-parser-output' on {url}")
            return "<i>Tarihte bugün içeriği için ana bölüm bulunamadı.</i>"

        extracted_html_parts = []
        # Target H2 IDs as they appear in the HTML
        target_h2_ids = ["Olaylar", "Doğumlar", "Ölümler"]

        # Find H2 tags by their ID, then work with their parent div and subsequent ul
        for h2_tag in content_div.find_all('h2', id=target_h2_ids):
            parent_div = h2_tag.parent
            # Check if the parent is the div.mw-heading structure described by the user
            if parent_div and parent_div.name == 'div' and \
               any(cls.startswith('mw-heading') for cls in parent_div.get('class', [])):
                
                # ---- START ADDITION: Remove edit section links ----
                for edit_section_span in parent_div.find_all('span', class_='mw-editsection'):
                    edit_section_span.decompose()
                # ---- END ADDITION ----

                # Add the whole <div class="mw-heading...">...</div> as the section header
                extracted_html_parts.append(str(parent_div))

                # Find the <ul> that is the next sibling of this parent_div
                ul_element = parent_div.find_next_sibling('ul')
                if ul_element:
                    ul_content_parts = ["<ul>"]
                    original_li_tags = ul_element.find_all('li', recursive=False)
                    
                    selected_tags = []
                    if len(original_li_tags) <= 10:
                        selected_tags = original_li_tags
                    else:
                        # Keep the 3 items listed last on Wikipedia for the section
                        latest_three_on_page = original_li_tags[-3:]
                        pool_for_random = original_li_tags[:-3]
                        randomly_selected_others = random.sample(pool_for_random, 7)
                        selected_tags = randomly_selected_others + latest_three_on_page

                    items_with_years = []
                    for tag in selected_tags:
                        year = extract_year_from_li(tag)
                        items_with_years.append({'tag': tag, 'year': year})
                    
                    # Sort the selected items by year, newest first
                    sorted_items = sorted(items_with_years, key=lambda x: x['year'], reverse=True)
                    
                    final_li_tags_for_display = [item['tag'] for item in sorted_items]

                    for li_tag in final_li_tags_for_display:
                        for a_tag in li_tag.find_all('a'):
                            if a_tag.has_attr('href') and a_tag['href'].startswith('/wiki/'):
                                a_tag['href'] = 'https://tr.wikipedia.org' + a_tag['href']
                            a_tag['target'] = '_blank'
                            # ---- START ADDITION: Style Wikipedia links ----
                            a_tag['style'] = 'color: #000000; text-decoration: underline;'
                            # ---- END ADDITION ----
                            # Clean up potential redirect class if it causes style issues
                            if 'class' in a_tag.attrs and 'mw-redirect' in a_tag.attrs['class']:
                                a_tag.attrs['class'].remove('mw-redirect')
                                if not a_tag.attrs['class']: 
                                    del a_tag.attrs['class']
                        ul_content_parts.append(str(li_tag))
                    ul_content_parts.append("</ul>")
                    extracted_html_parts.append("".join(ul_content_parts))
                else:
                    logger.warning(f"Found heading '{h2_tag.get("id")}' but no subsequent <ul> list.")
            else:
                # This case means an H2 with a target ID was found but not in the expected div.mw-heading parent.
                # Could log this or decide to still include the H2 if that makes sense.
                logger.warning(f"Found H2 with id '{h2_tag.get("id")}' but not within the expected div.mw-heading parent structure.")

        if not extracted_html_parts:
            return "<i>Tarihte bugün için belirtilen bölümler (Olaylar, Doğumlar, Ölümler) ve listeleri bulunamadı.</i>"
            
        return "".join(extracted_html_parts)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return "<i>Tarihte bugün içeriği alınırken bir bağlantı hatası oluştu.</i>"
    except Exception as e:
        logger.error(f"An error occurred during Wikipedia scraping: {e}", exc_info=True)
        return "<i>Tarihte bugün içeriği işlenirken bir hata oluştu.</i>"

if __name__ == '__main__':
    # Example usage when running the script directly
    content = scrape_resmi_gazete()
    if content:
        print("Successfully scraped Resmi Gazete content (first 500 chars):")
        print(content)
    else:
        print("Failed to scrape Resmi Gazete content.")
    
    print("\\n--- Wikipedia Today in History ---")
    wiki_content = scrape_wikipedia_today_in_history()
