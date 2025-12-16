from django.urls import path
from .views import scrape_resmi_gazete, scrape_wikipedia

urlpatterns = [
    path('fetch-gazette/', scrape_resmi_gazete, name='fetch_gazette_data'),
    path('fetch-wikipedia/', scrape_wikipedia, name='fetch_wikipedia_data'),
]
