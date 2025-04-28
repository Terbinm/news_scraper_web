from django.contrib import admin
from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis, SentimentAnalysis, CategorySentimentSummary

@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'article', 'sentiment', 'positive_score', 'negative_score')
    list_filter = ('sentiment', 'job')
    search_fields = ('article__title',)

@admin.register(CategorySentimentSummary)
class CategorySentimentSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'category', 'positive_count', 'negative_count', 'average_positive_score')
    list_filter = ('job', 'category')

@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'status', 'categories', 'limit_per_category')
    list_filter = ('status', 'created_at', 'user')
    search_fields = ('categories', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'date', 'author', 'job')
    list_filter = ('category', 'date', 'job')
    search_fields = ('title', 'content', 'author')
    readonly_fields = ('item_id', 'link')
    date_hierarchy = 'date'

    def get_queryset(self, request):
        # 優化查詢，減少數據庫查詢
        return super().get_queryset(request).select_related('job')


@admin.register(KeywordAnalysis)
class KeywordAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'word', 'pos', 'frequency', 'category', 'job')
    list_filter = ('category', 'pos', 'created_at', 'job')
    search_fields = ('word',)
    list_per_page = 100  # 每頁顯示更多記錄

    def get_queryset(self, request):
        # 優化查詢，減少數據庫查詢
        return super().get_queryset(request).select_related('job')


@admin.register(NamedEntityAnalysis)
class NamedEntityAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'entity', 'entity_type', 'frequency', 'category', 'job')
    list_filter = ('category', 'entity_type', 'created_at', 'job')
    search_fields = ('entity',)
    list_per_page = 100  # 每頁顯示更多記錄

    def get_queryset(self, request):
        # 優化查詢，減少數據庫查詢
        return super().get_queryset(request).select_related('job')