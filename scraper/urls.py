from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/chart/', views.generate_chart, name='generate_chart'),
    path('jobs/delete/<int:job_id>/', views.job_delete, name='job_delete'),
    path('articles/<int:article_id>/', views.article_detail, name='article_detail'),
]