# 在scraper/urls.py文件中添加以下URL配置
from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('', views.job_list, name='job_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/delete/<int:job_id>/', views.job_delete, name='job_delete'),
    path('articles/<int:article_id>/', views.article_detail, name='article_detail'),

    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/keywords/', views.job_keywords_analysis, name='job_keywords'),
    path('jobs/<int:job_id>/entities/', views.job_entities_analysis, name='job_entities'),
    path('jobs/<int:job_id>/articles/', views.job_articles, name='job_articles'),
    path('jobs/<int:job_id>/search-analysis/', views.job_search_analysis, name='job_search_analysis'),

    # 關鍵人物分析相關路由
    path('jobs/<int:job_id>/key_person_selection/', views.key_person_selection, name='key_person_selection'),
    path('jobs/<int:job_id>/analyze_key_person/', views.analyze_key_person, name='analyze_key_person'),
    path('jobs/<int:job_id>/analyze_key_person/<str:person_name>/', views.analyze_key_person,
         name='analyze_key_person_with_name'),
    path('jobs/<int:job_id>/compare_key_persons/<str:person_names>/', views.compare_key_persons,
         name='compare_key_persons'),

    path('api/analyze_search_terms/', views.analyze_search_terms, name='analyze_search_terms'),

    path('jobs/<int:job_id>/sentiment/', views.job_sentiment_analysis, name='job_sentiment_analysis'),
    path('articles/<int:article_id>/analyze-sentiment/', views.analyze_article_sentiment,
         name='analyze_article_sentiment'),
    path('jobs/<int:job_id>/start-sentiment-analysis/', views.start_sentiment_analysis,
         name='start_sentiment_analysis'),
    path('jobs/<int:job_id>/regenerate-sentiment-summary/', views.regenerate_sentiment_summary,
         name='regenerate_sentiment_summary'),



    # AI 報告相關路由
    path('jobs/<int:job_id>/ai-report/', views.ai_report_view, name='ai_report_view'),
    path('jobs/<int:job_id>/ai-report/<int:report_id>/', views.ai_report_detail, name='ai_report_detail'),
    path('jobs/<int:job_id>/ai-report/<int:report_id>/download/', views.ai_report_download, name='ai_report_download'),
    path('jobs/<int:job_id>/ai-report/<int:report_id>/regenerate/', views.regenerate_ai_report,
         name='regenerate_ai_report'),

    # AI 報告API
    path('api/jobs/<int:job_id>/ai-report/', api.AIReportAPIView.as_view(), name='api_ai_report'),
    path('api/jobs/<int:job_id>/ai-report/<int:report_id>/', api.AIReportAPIView.as_view(),
         name='api_ai_report_detail'),
    path('jobs/<int:job_id>/ai-report/<int:report_id>/delete/', views.delete_ai_report, name='delete_ai_report'),

]