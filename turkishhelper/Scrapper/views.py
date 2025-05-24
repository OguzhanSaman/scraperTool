from django.http import JsonResponse
from .utils import scrape_resmi_gazete_content
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def scrape_resmi_gazete(request):
    logger.info("Scrape request received")
    
    try:
        content = scrape_resmi_gazete_content()
        
        if content is None:
            logger.error("Scraping failed - no content returned")
            return JsonResponse(
                {"error": "Failed to scrape content from Resmi Gazete"}, 
                status=500,
                json_dumps_params={'ensure_ascii': False}
            )
        
        logger.info("Successfully scraped content")
        
        # Using JsonResponse with ensure_ascii=False to preserve Turkish characters
        return JsonResponse(
            {'content': content}, 
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