from django.urls import path
from . import views

app_name = 'evaluator'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload-zip/', views.upload_zip, name='upload_zip'),
    path('submit-github/', views.submit_github, name='submit_github'),
    path('check-status/<int:evaluation_id>/', views.check_status, name='check_status'),
    path('dashboard/<int:evaluation_id>/', views.dashboard, name='dashboard'),
]