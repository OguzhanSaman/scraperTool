from django.http import JsonResponse
from .utils import scrape_resmi_gazete_content
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Add parent directory to path to import actual_server_utils
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
try:
    from actual_server_utils import scrape_wikipedia_today_in_history, get_wikipedia_today_in_history_url
except ImportError as e:
    logger.error(f"Failed to import wiki scraping functions: {e}")
    scrape_wikipedia_today_in_history = None

@api_view(['GET'])
def scrape_resmi_gazete(request):
    logger.info("Scrape request received")
    
    try:
        # Scrape both gazette and wikipedia content
        content = scrape_resmi_gazete_content()
        wikipedia_content = None
        
        # Try to get Wikipedia content
        if scrape_wikipedia_today_in_history is not None:
            try:
                wikipedia_content = scrape_wikipedia_today_in_history()
                if wikipedia_content:
                    logger.info(f"Successfully scraped Wikipedia content (length: {len(wikipedia_content)})")
                else:
                    logger.warning("Wikipedia scraping returned None or empty")
            except Exception as wiki_error:
                logger.error(f"Error scraping Wikipedia content: {wiki_error}", exc_info=True)
                wikipedia_content = None
        else:
            logger.warning("Wikipedia scraping function not available")
        
        if content is None:
            logger.error("No content available - neither manual data nor web scraping succeeded")
            return JsonResponse(
                {
                    "error": "No Resmi Gazete data available",
                    "message": "Please ensure manual data has been entered in the admin panel, or try again later",
                    "admin_url": "/admin/Scrapper/manualresmigazetedata/"
                }, 
                status=400,
                json_dumps_params={'ensure_ascii': False}
            )
        
        logger.info("Successfully scraped gazette content")
        
        # Return both gazette and wikipedia content
        response_data = {
            'content': content,
        }
        
        if wikipedia_content:
            response_data['wikipedia_content'] = wikipedia_content
        else:
            response_data['wikipedia_content'] = None
            logger.warning("Wikipedia content not included in response")
        
        # Using JsonResponse with ensure_ascii=False to preserve Turkish characters
        return JsonResponse(
            response_data, 
            json_dumps_params={'ensure_ascii': False},
            content_type='application/json; charset=utf-8'
        )
        
    except Exception as e:
        logger.exception("Unexpected error in scrape_resmi_gazete view")
        return JsonResponse(
            {"error": "An unexpected server error occurred", "detail": str(e)}, 
            status=500,
            json_dumps_params={'ensure_ascii': False}
        )


@api_view(['GET'])
def scrape_wikipedia(request):
    """Test endpoint for Wikipedia 'Today in History' scraping"""
    logger.info("Wikipedia scrape request received")
    
    if scrape_wikipedia_today_in_history is None:
        return JsonResponse(
            {
                "error": "Wikipedia scraping function not available",
                "message": "Failed to import scrape_wikipedia_today_in_history"
            },
            status=500,
            json_dumps_params={'ensure_ascii': False}
        )
    
    try:
        url = get_wikipedia_today_in_history_url()
        logger.info(f"Scraping Wikipedia URL: {url}")
        
        content = scrape_wikipedia_today_in_history()
        
        if content is None:
            logger.error("Wikipedia scraping returned None")
            return JsonResponse(
                {
                    "error": "Wikipedia content is None",
                    "url": url
                },
                status=400,
                json_dumps_params={'ensure_ascii': False}
            )
        
        logger.info(f"Successfully scraped Wikipedia content (length: {len(content)})")
        
        return JsonResponse(
            {
                'content': content,
                'url': url,
                'content_length': len(content)
            },
            json_dumps_params={'ensure_ascii': False},
            content_type='application/json; charset=utf-8'
        )
        
    except Exception as e:
        logger.exception("Unexpected error in scrape_wikipedia view")
        return JsonResponse(
            {"error": "An unexpected server error occurred", "detail": str(e)},
            status=500,
            json_dumps_params={'ensure_ascii': False}
        )