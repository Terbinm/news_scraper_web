from django.urls import path
from . import views

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),

    # path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    # path('jobs/<int:job_id>/chart/', views.generate_keyword_chart, name='generate_chart'),
    path('jobs/delete/<int:job_id>/', views.job_delete, name='job_delete'),
    path('articles/<int:article_id>/', views.article_detail, name='article_detail'),

    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/keywords/', views.job_keywords_analysis, name='job_keywords'),
    path('jobs/<int:job_id>/entities/', views.job_entities_analysis, name='job_entities'),
    path('jobs/<int:job_id>/articles/', views.job_articles, name='job_articles'),
    path('jobs/<int:job_id>/search-analysis/', views.job_search_analysis, name='job_search_analysis'),
]