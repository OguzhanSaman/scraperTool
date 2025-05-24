from django.urls import path
from .views import scrape_resmi_gazete

urlpatterns = [
    path('fetch-gazette/', scrape_resmi_gazete, name='fetch_gazette_data'),
]
