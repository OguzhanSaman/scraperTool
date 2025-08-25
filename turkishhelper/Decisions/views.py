import requests
import json
import time
import random
from typing import List, Dict, Any, Optional
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import logging

# Setup logging
logger = logging.getLogger(__name__)

class YargitaySearchView(View):
    """Django view for searching Turkish Supreme Court (Yargıtay) decisions"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://karararama.yargitay.gov.tr"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        })
        
        # Rate limiting
        self.min_delay = 2.0
        self.max_delay = 5.0
        self.last_request_time = 0
        self.retry_delay = 10
    
    def _rate_limit(self):
        """Implement rate limiting to be respectful to the server"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last + random.uniform(0, 1.0)
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _handle_rate_limit(self, response):
        """Handle rate limiting errors"""
        if response.status_code == 429 or "TOO MANY REQUESTS" in response.text.upper():
            logger.warning(f"Rate limit hit, waiting {self.retry_delay} seconds...")
            time.sleep(self.retry_delay)
            self.retry_delay *= 2  # Exponential backoff
            return True
        else:
            self.retry_delay = 10  # Reset delay
            return False
    
    def search_decisions(self, keyword: str, page_number: int = 1, page_size: int = 10) -> tuple[List[Dict[str, Any]], int, int]:
        """
        Search for decisions using the actual API endpoint
        
        Args:
            keyword: Search keyword
            page_number: Page number (1-based)
            page_size: Number of results per page
            
        Returns:
            Tuple of (decisions, total_records, filtered_records)
            - decisions: List of decision dictionaries
            - total_records: Total number of records available
            - filtered_records: Number of records after filtering
        """
        self._rate_limit()
        
        url = f"{self.base_url}/aramalist"
        
        # Payload based on the actual API structure
        payload = {
            "data": {
                "aranan": keyword,
                "arananKelime": keyword,
                "pageSize": page_size,
                "pageNumber": page_number
            }
        }
        
        try:
            logger.info(f"Searching for '{keyword}' - page {page_number} with page_size {page_size}")
            logger.info(f"API payload: {json.dumps(payload, ensure_ascii=False)}")
            
            response = self.session.post(url, json=payload, timeout=30)
            
            # Handle rate limiting
            if self._handle_rate_limit(response):
                return self.search_decisions(keyword, page_number, page_size)  # Retry
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for success response
            if 'data' in data and 'data' in data['data']:
                decisions = data['data']['data']
                total_records = data['data'].get('recordsTotal', len(decisions))
                filtered_records = data['data'].get('recordsFiltered', len(decisions))
                logger.info(f"Found {len(decisions)} decisions out of {total_records} total")
                return decisions, total_records, filtered_records
            # Check for error response in metadata
            elif 'metadata' in data and data.get('metadata', {}).get('FMTY') == 'ERROR':
                error_msg = data.get('metadata', {}).get('FMTE', 'Unknown error')
                logger.error(f"Search failed: {error_msg}")
                return [], 0, 0
            # Check for other error conditions
            elif 'metadata' in data and data.get('metadata', {}).get('FMTY') is not None:
                error_msg = data.get('metadata', {}).get('FMTE', 'Unknown error')
                logger.error(f"Search failed with status {data.get('metadata', {}).get('FMTY')}: {error_msg}")
                return [], 0, 0
            else:
                logger.error(f"Unexpected response format: {data}")
                return [], 0, 0
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return [], 0, 0
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return [], 0, 0
    
    def fetch_document_content(self, decision_id: str) -> Optional[str]:
        """
        Fetch document content using GET request with query parameter
        
        Args:
            decision_id: Decision ID
            
        Returns:
            Document content or None if failed
        """
        self._rate_limit()
        
        url = f"{self.base_url}/getDokuman"
        params = {"id": decision_id}
        
        try:
            logger.info(f"Fetching content for decision {decision_id}")
            
            response = self.session.get(url, params=params, timeout=30)
            
            # Handle rate limiting
            if self._handle_rate_limit(response):
                return self.fetch_document_content(decision_id)  # Retry
            
            response.raise_for_status()
            
            data = response.json()
            
            # Check for success response
            if data.get('metadata', {}).get('FMTY') == 'SUCCESS':
                content = data.get('data', '')
                logger.info(f"Content fetched successfully: {len(content)} characters")
                return content
            # Check for error response
            elif data.get('metadata', {}).get('FMTY') == 'ERROR':
                error_msg = data.get('metadata', {}).get('FMTE', 'Unknown error')
                logger.error(f"Document fetch failed: {error_msg}")
                return None
            # Check for other error conditions
            elif data.get('metadata', {}).get('FMTY') is not None:
                error_msg = data.get('metadata', {}).get('FMTE', 'Unknown error')
                logger.error(f"Document fetch failed with status {data.get('metadata', {}).get('FMTY')}: {error_msg}")
                return None
            else:
                logger.error(f"Unexpected response format: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {decision_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {decision_id}: {e}")
            return None

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for searching decisions
        
        Expected JSON payload:
        {
            "keyword": "search term",
            "page_number": 1,
            "page_size": 10,
            "fetch_content": false
        }
        """
        try:
            data = json.loads(request.body)
            keyword = data.get('keyword', '').strip()
            
            if not keyword:
                return JsonResponse({
                    'error': 'Keyword is required'
                }, status=400)
            
            page_number = data.get('page_number', 1)
            page_size = data.get('page_size', 10)
            fetch_content = data.get('fetch_content', False)
            
            # Validate parameters
            if page_number < 1:
                page_number = 1
            
            # Yargıtay API only accepts specific page sizes: 10, 25, 50, 100
            valid_page_sizes = [10, 25, 50, 100]
            if page_size not in valid_page_sizes:
                # Find the closest valid page size
                closest_size = min(valid_page_sizes, key=lambda x: abs(x - page_size))
                logger.info(f"Page size {page_size} not valid. Using closest valid size: {closest_size}")
                page_size = closest_size
            
            # Search for decisions
            decisions, total_records, filtered_records = self.search_decisions(keyword, page_number, page_size)
            
            # Fetch content if requested
            if fetch_content and decisions:
                for decision in decisions:
                    decision_id = decision.get('id')
                    if decision_id:
                        content = self.fetch_document_content(decision_id)
                        if content:
                            decision['document_content'] = content
            
            return JsonResponse({
                'success': True,
                'keyword': keyword,
                'page_number': page_number,
                'page_size': page_size,
                'total_results': len(decisions),
                'total_records': total_records,
                'filtered_records': filtered_records,
                'decisions': decisions
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON payload'
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in search view: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)

    @method_decorator(csrf_exempt)
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests for searching decisions
        
        Query parameters:
        - keyword: Search term (required)
        - page_number: Page number (optional, default: 1)
        - page_size: Results per page (optional, default: 10)
        - fetch_content: Whether to fetch document content (optional, default: false)
        """
        try:
            keyword = request.GET.get('keyword', '').strip()
            
            if not keyword:
                return JsonResponse({
                    'error': 'Keyword parameter is required'
                }, status=400)
            
            page_number = int(request.GET.get('page_number', 1))
            page_size = int(request.GET.get('page_size', 10))
            fetch_content = request.GET.get('fetch_content', 'false').lower() == 'true'
            
            # Debug logging
            logger.info(f"Received page_size: {page_size}")
            
            # Validate parameters
            if page_number < 1:
                page_number = 1
            
            # Yargıtay API only accepts specific page sizes: 10, 25, 50, 100
            valid_page_sizes = [10, 25, 50, 100]
            if page_size not in valid_page_sizes:
                # Find the closest valid page size
                closest_size = min(valid_page_sizes, key=lambda x: abs(x - page_size))
                logger.info(f"Page size {page_size} not valid. Using closest valid size: {closest_size}")
                page_size = closest_size
            
            logger.info(f"Final page_size being sent to API: {page_size}")
            
            # Search for decisions
            decisions, total_records, filtered_records = self.search_decisions(keyword, page_number, page_size)
            
            # Fetch content if requested
            if fetch_content and decisions:
                for decision in decisions:
                    decision_id = decision.get('id')
                    if decision_id:
                        content = self.fetch_document_content(decision_id)
                        if content:
                            decision['document_content'] = content
            
            return JsonResponse({
                'success': True,
                'keyword': keyword,
                'page_number': page_number,
                'page_size': page_size,
                'total_results': len(decisions),
                'total_records': total_records,
                'filtered_records': filtered_records,
                'decisions': decisions
            })
            
        except ValueError as e:
            return JsonResponse({
                'error': f'Invalid parameter value: {str(e)}'
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in search view: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def search_decisions_api(request):
    """
    Alternative function-based view for searching decisions
    
    This is a simpler alternative to the class-based view above
    """
    try:
        data = json.loads(request.body)
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return JsonResponse({
                'error': 'Keyword is required'
            }, status=400)
        
        page_number = data.get('page_number', 1)
        page_size = data.get('page_size', 10)
        fetch_content = data.get('fetch_content', False)
        
        # Validate parameters
        if page_number < 1:
            page_number = 1
        
        # Yargıtay API only accepts specific page sizes: 10, 25, 50, 100
        valid_page_sizes = [10, 25, 50, 100]
        if page_size not in valid_page_sizes:
            # Find the closest valid page size
            closest_size = min(valid_page_sizes, key=lambda x: abs(x - page_size))
            logger.info(f"Page size {page_size} not valid. Using closest valid size: {closest_size}")
            page_size = closest_size
        
        # Create scraper instance
        scraper = YargitaySearchView()
        
        # Search for decisions
        decisions, total_records, filtered_records = scraper.search_decisions(keyword, page_number, page_size)
        
        # Fetch content if requested
        if fetch_content and decisions:
            for decision in decisions:
                decision_id = decision.get('id')
                if decision_id:
                    content = scraper.fetch_document_content(decision_id)
                    if content:
                        decision['document_content'] = content
        
        return JsonResponse({
            'success': True,
            'keyword': keyword,
            'page_number': page_number,
            'page_size': page_size,
            'total_results': len(decisions),
            'total_records': total_records,
            'filtered_records': filtered_records,
            'decisions': decisions
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in search API: {e}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def get_decision_content(request):
    """
    Fetch document content for a specific decision by ID
    
    Expected JSON payload:
    {
        "decision_id": "12345"
    }
    
    Returns:
    {
        "success": true,
        "decision_id": "12345",
        "content": "Full document content...",
        "content_length": 1500
    }
    """
    try:
        data = json.loads(request.body)
        decision_id = data.get('decision_id', '').strip()
        
        if not decision_id:
            return JsonResponse({
                'error': 'Decision ID is required'
            }, status=400)
        
        # Create scraper instance
        scraper = YargitaySearchView()
        
        # Fetch document content
        content = scraper.fetch_document_content(decision_id)
        
        if content is not None:
            return JsonResponse({
                'success': True,
                'decision_id': decision_id,
                'content': content,
                'content_length': len(content)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch document content',
                'decision_id': decision_id
            }, status=404)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in get_decision_content: {e}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_decision_content_get(request):
    """
    Fetch document content for a specific decision by ID (GET method)
    
    Query parameters:
    - decision_id: Decision ID (required)
    
    Returns:
    {
        "success": true,
        "decision_id": "12345",
        "content": "Full document content...",
        "content_length": 1500
    }
    """
    try:
        decision_id = request.GET.get('decision_id', '').strip()
        
        if not decision_id:
            return JsonResponse({
                'error': 'Decision ID parameter is required'
            }, status=400)
        
        # Create scraper instance
        scraper = YargitaySearchView()
        
        # Fetch document content
        content = scraper.fetch_document_content(decision_id)
        
        if content is not None:
            return JsonResponse({
                'success': True,
                'decision_id': decision_id,
                'content': content,
                'content_length': len(content)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to fetch document content',
                'decision_id': decision_id
            }, status=404)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_decision_content_get: {e}")
        return JsonResponse({
            'error': 'Internal server error'
        }, status=500)
