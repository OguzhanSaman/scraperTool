from django.urls import path
from . import views

app_name = 'decisions'

urlpatterns = [
    # Class-based view for searching decisions
    path('search/', views.YargitaySearchView.as_view(), name='search_decisions'),
    
    # Function-based view alternative
    path('search-api/', views.search_decisions_api, name='search_decisions_api'),
    
    # Get decision content by ID (POST method)
    path('content/', views.get_decision_content, name='get_decision_content'),
    
    # Get decision content by ID (GET method)
    path('content-get/', views.get_decision_content_get, name='get_decision_content_get'),
]

