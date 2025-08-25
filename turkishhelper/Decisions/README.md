# Yargıtay Decisions Search API

This Django app provides API endpoints for searching Turkish Supreme Court (Yargıtay) decisions from the official website `karararama.yargitay.gov.tr`.

## Features

- **Real-time Search**: Search decisions directly from the Yargıtay website
- **Rate Limiting**: Built-in rate limiting to respect the server's limits
- **Content Fetching**: Optional document content retrieval
- **Pagination**: Support for paginated results
- **Error Handling**: Comprehensive error handling and retry logic
- **Individual Decision Content**: Fetch full document content for specific decisions

## API Endpoints

### 1. Class-based View: `/decisions/search/`

**POST Request**
```json
{
    "keyword": "işveren",
    "page_number": 1,
    "page_size": 10,
    "fetch_content": false
}
```

**GET Request**
```
GET /decisions/search/?keyword=işveren&page_number=1&page_size=10&fetch_content=false
```

### 2. Function-based View: `/decisions/search-api/`

**POST Request Only**
```json
{
    "keyword": "işveren",
    "page_number": 1,
    "page_size": 10,
    "fetch_content": false
}
```

### 3. Get Decision Content: `/decisions/content/`

**POST Request**
```json
{
    "decision_id": "12345"
}
```

**GET Request**
```
GET /decisions/content-get/?decision_id=12345
```

## Parameters

### Search Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `keyword` | string | Yes | - | Search term for decisions |
| `page_number` | integer | No | 1 | Page number (1-based) |
| `page_size` | integer | No | 10 | Results per page (valid values: 10, 25, 50, 100) |
| `fetch_content` | boolean | No | false | Whether to fetch document content |

### Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `total_results` | integer | Number of decisions in current page |
| `total_records` | integer | Total number of decisions available (from Yargıtay API) |
| `filtered_records` | integer | Number of decisions after filtering (from Yargıtay API) |

### Content Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `decision_id` | string | Yes | - | Decision ID to fetch content for |

## Response Format

### Search Success Response
```json
{
    "success": true,
    "keyword": "işveren",
    "page_number": 1,
    "page_size": 10,
    "total_results": 5,
    "total_records": 307417,
    "filtered_records": 307417,
    "decisions": [
        {
            "id": "12345",
            "daire": "Hukuk Genel Kurulu",
            "esasNo": "2023/123",
            "kararNo": "2023/456",
            "kararTarihi": "2023-01-15",
            "arananKelime": "işveren",
            "index": "test index",
            "siraNo": 1,
            "document_content": "..." // Only if fetch_content=true
        }
    ]
}
```

### Content Success Response
```json
{
    "success": true,
    "decision_id": "12345",
    "content": "Full document content...",
    "content_length": 1500
}
```

### Error Response
```json
{
    "error": "Error message"
}
```

## Usage Examples

### JavaScript/Fetch API

#### Search for Decisions
```javascript
// Search for decisions
const searchDecisions = async (keyword) => {
    const response = await fetch('/decisions/search/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            keyword: keyword,
            page_number: 1,
            page_size: 10,
            fetch_content: false
        })
    });
    
    const data = await response.json();
    return data;
};

// Usage
searchDecisions('işveren').then(result => {
    console.log('Found', result.total_results, 'decisions');
    result.decisions.forEach(decision => {
        console.log(`${decision.daire}: ${decision.esasNo}/${decision.kararNo}`);
    });
});
```

#### Get Decision Content
```javascript
// Get decision content by ID
const getDecisionContent = async (decisionId) => {
    const response = await fetch('/decisions/content/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            decision_id: decisionId
        })
    });
    
    const data = await response.json();
    return data;
};

// Usage
getDecisionContent('12345').then(result => {
    if (result.success) {
        console.log('Content length:', result.content_length);
        console.log('Content:', result.content);
    } else {
        console.error('Failed to fetch content:', result.error);
    }
});
```

### Python/Requests

#### Search for Decisions
```python
import requests
import json

def search_decisions(keyword, page_number=1, page_size=10, fetch_content=False):
    url = 'http://localhost:8000/decisions/search/'
    data = {
        'keyword': keyword,
        'page_number': page_number,
        'page_size': page_size,
        'fetch_content': fetch_content
    }
    
    response = requests.post(url, json=data)
    return response.json()

# Usage
result = search_decisions('işveren')
print(f"Found {result['total_results']} decisions")
for decision in result['decisions']:
    print(f"{decision['daire']}: {decision['esasNo']}/{decision['kararNo']}")
```

#### Get Decision Content
```python
def get_decision_content(decision_id):
    url = 'http://localhost:8000/decisions/content/'
    data = {
        'decision_id': decision_id
    }
    
    response = requests.post(url, json=data)
    return response.json()

# Usage
result = get_decision_content('12345')
if result['success']:
    print(f"Content length: {result['content_length']}")
    print(f"Content: {result['content']}")
else:
    print(f"Failed to fetch content: {result['error']}")
```

## Typical Workflow

1. **Search for decisions** using the search endpoint
2. **Display results** to the user
3. **When user clicks on a decision**, use the content endpoint to fetch the full document
4. **Display the content** in your UI

```javascript
// Example workflow
const handleDecisionClick = async (decisionId) => {
    try {
        const contentResult = await getDecisionContent(decisionId);
        if (contentResult.success) {
            // Display the content in a modal, new page, etc.
            displayDecisionContent(contentResult.content);
        } else {
            alert('Failed to load decision content');
        }
    } catch (error) {
        console.error('Error fetching decision content:', error);
    }
};
```

## Rate Limiting

The API implements rate limiting to respect the Yargıtay server's limits:
- Minimum delay between requests: 2 seconds
- Maximum delay: 5 seconds
- Exponential backoff for rate limit errors
- Automatic retry on rate limit responses

## Error Handling

The API handles various error scenarios:
- **400 Bad Request**: Missing or invalid parameters
- **404 Not Found**: Decision content not found
- **429 Too Many Requests**: Rate limit exceeded (handled automatically)
- **500 Internal Server Error**: Unexpected server errors

## Testing

Run the tests with:
```bash
python manage.py test Decisions.test_views
```

## Notes

- The API doesn't persist any data - it's a pure search interface
- Document content fetching is optional and increases response time
- All requests are made to the official Yargıtay website
- The API respects the server's rate limits automatically
- Content endpoints are separate from search to optimize performance
- **Page Size Validation**: The Yargıtay API only accepts specific page sizes (10, 25, 50, 100). If you provide any other value, it will automatically use the closest valid size.
