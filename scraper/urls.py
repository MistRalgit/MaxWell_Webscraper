from django.urls import path
from . import views

app_name = 'scraper'

urlpatterns = [
    path('', views.index, name='index'),
    path('run-scraper/', views.run_scraper, name='run_scraper'),
    path('test-selector/', views.test_selector, name='test_selector'),
] 