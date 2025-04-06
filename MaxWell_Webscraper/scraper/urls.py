from django.urls import path
from . import views

app_name = 'scraper'

urlpatterns = [
    path('', views.index, name='index'),
    path('scrape/', views.scrape, name='scrape'),
    path('export-csv/', views.export_csv, name='export_csv'),
    path('test-selector/', views.test_selector, name='test_selector'),
    path('save-data/', views.save_data, name='save_data'),
    path('load-data/<int:data_id>/', views.load_data, name='load_data'),
    path('delete-data/<int:data_id>/', views.delete_data, name='delete_data'),
    path('get-logs/', views.get_logs, name='get_logs'),
    path('clear-logs/', views.clear_logs, name='clear_logs'),
] 