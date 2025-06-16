import os
import logging
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class ScrapeJob(models.Model):
    """爬蟲任務模型"""

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '執行中'),
        ('completed', '已完成'),
        ('failed', '失敗')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scrape_jobs', verbose_name='用戶')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='狀態')
    categories = models.CharField(max_length=255, verbose_name='爬取類別')
    limit_per_category = models.IntegerField(default=5, verbose_name='每類別文章數')
    use_threading = models.BooleanField(default=False, verbose_name='使用多線程')
    max_workers = models.IntegerField(default=4, verbose_name='最大線程數')
    result_file_path = models.CharField(max_length=255, blank=True, null=True, verbose_name='結果檔案路徑')
    sentiment_analyzed = models.BooleanField(default=False, verbose_name='情感分析完成')

    def __str__(self):
        return f"爬蟲任務 {self.id} - {self.get_status_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = '爬蟲任務'
        verbose_name_plural = '爬蟲任務'
        ordering = ['-created_at']


class Article(models.Model):
    """文章模型"""

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='articles', verbose_name='爬蟲任務')
    item_id = models.CharField(max_length=100, verbose_name='文章ID')
    category = models.CharField(max_length=50, verbose_name='類別')
    title = models.CharField(max_length=255, verbose_name='標題')
    content = models.TextField(verbose_name='內容')
    date = models.DateTimeField(verbose_name='發布日期')
    author = models.CharField(max_length=100, verbose_name='作者')
    link = models.URLField(verbose_name='原始連結')
    photo_links = models.TextField(blank=True, null=True, verbose_name='圖片連結')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-date']
        unique_together = ('job', 'item_id')


class KeywordAnalysis(models.Model):
    """關鍵詞分析模型"""

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='keywords', verbose_name='爬蟲任務')
    word = models.CharField(max_length=100, verbose_name='關鍵詞')
    pos = models.CharField(max_length=10, verbose_name='詞性')
    frequency = models.IntegerField(verbose_name='頻率')
    category = models.CharField(max_length=50, verbose_name='類別')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')

    def __str__(self):
        return f"{self.word} ({self.pos}) - {self.frequency}"

    class Meta:
        verbose_name = '關鍵詞分析'
        verbose_name_plural = '關鍵詞分析'
        ordering = ['-frequency']
        indexes = [
            models.Index(fields=['job', 'category']),
            models.Index(fields=['job', 'frequency']),
        ]


class NamedEntityAnalysis(models.Model):
    """命名實體分析模型"""

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='named_entities', verbose_name='爬蟲任務')
    entity = models.CharField(max_length=100, verbose_name='實體')
    entity_type = models.CharField(max_length=20, verbose_name='實體類型')
    frequency = models.IntegerField(verbose_name='頻率')
    category = models.CharField(max_length=50, verbose_name='類別')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')

    def __str__(self):
        return f"{self.entity} ({self.entity_type}) - {self.frequency}"

    class Meta:
        verbose_name = '命名實體分析'
        verbose_name_plural = '命名實體分析'
        ordering = ['-frequency']
        indexes = [
            models.Index(fields=['job', 'category']),
            models.Index(fields=['job', 'entity_type']),
            models.Index(fields=['job', 'frequency']),
        ]


class SentimentAnalysis(models.Model):
    """情感分析模型"""
    SENTIMENT_CHOICES = [
        ('正面', '正面'),
        ('負面', '負面'),
        ('中立', '中立')
    ]

    article = models.OneToOneField(Article, on_delete=models.CASCADE, related_name='sentiment', verbose_name='文章')
    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='sentiments', verbose_name='爬蟲任務')
    positive_score = models.FloatField(verbose_name='正面情感分數')
    negative_score = models.FloatField(verbose_name='負面情感分數')
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, verbose_name='情感傾向')
    title_sentiment = models.CharField(max_length=10, null=True, blank=True, choices=SENTIMENT_CHOICES,
                                       verbose_name='標題情感傾向')
    title_positive_score = models.FloatField(null=True, blank=True, verbose_name='標題正面分數')
    title_negative_score = models.FloatField(null=True, blank=True, verbose_name='標題負面分數')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    def __str__(self):
        return f"{self.article.title} - {self.sentiment} ({self.positive_score:.2f})"

    class Meta:
        verbose_name = '情感分析'
        verbose_name_plural = '情感分析'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'sentiment']),
            models.Index(fields=['job', 'positive_score']),
        ]


class CategorySentimentSummary(models.Model):
    """類別情感摘要模型"""

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='category_sentiments', verbose_name='爬蟲任務')
    category = models.CharField(max_length=50, verbose_name='類別')
    positive_count = models.IntegerField(default=0, verbose_name='正面文章數')
    negative_count = models.IntegerField(default=0, verbose_name='負面文章數')
    neutral_count = models.IntegerField(default=0, verbose_name='中立文章數')
    average_positive_score = models.FloatField(verbose_name='平均正面分數')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    def __str__(self):
        return f"{self.category} - 正面:{self.positive_count}, 負面:{self.negative_count}"

    class Meta:
        verbose_name = '類別情感摘要'
        verbose_name_plural = '類別情感摘要'
        ordering = ['-positive_count']
        unique_together = ('job', 'category')


class AIReport(models.Model):
    """AI 生成的報告模型"""

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='ai_reports', verbose_name='爬蟲任務')
    search_query = models.TextField(verbose_name='搜索查詢條件', blank=True, null=True)
    content = models.TextField(verbose_name='報告內容')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='生成時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    language = models.CharField(max_length=10, default='zh-TW', verbose_name='報告語言')
    article_count = models.IntegerField(default=0, verbose_name='分析文章數')
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', '處理中'),
            ('completed', '已完成'),
            ('failed', '失敗')
        ],
        verbose_name='狀態'
    )
    error_message = models.TextField(verbose_name='錯誤訊息', blank=True, null=True)

    # 存儲報告生成用的原始搜索參數
    search_params = models.JSONField(verbose_name='搜索參數', blank=True, null=True)

    class Meta:
        verbose_name = 'AI報告'
        verbose_name_plural = 'AI報告'
        ordering = ['-generated_at']

    def __str__(self):
        return f"AI報告 #{self.id} ({self.job.id}) - {self.generated_at.strftime('%Y-%m-%d %H:%M')}"

    def get_absolute_url(self):
        """獲取報告詳情頁面URL"""
        return reverse('ai_report_detail', kwargs={'pk': self.pk})

    def get_file_path(self):
        """獲取報告文件保存路徑"""
        return os.path.join(settings.AI_REPORT_SETTINGS['SAVE_PATH'], f'report_{self.id}.md')

    def save_to_file(self):
        """將報告內容保存為文件"""
        try:
            with open(self.get_file_path(), 'w', encoding='utf-8') as f:
                f.write(self.content)
            return True
        except Exception as e:
            logger.error(f"保存報告文件時出錯: {e}")
            return False

class ArticleSummary(models.Model):
    """文章摘要模型"""

    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '處理中'),
        ('completed', '已完成'),
        ('failed', '失敗')
    ]

    article = models.OneToOneField(
        Article,
        on_delete=models.CASCADE,
        related_name='summary',
        verbose_name='文章'
    )
    job = models.ForeignKey(
        ScrapeJob,
        on_delete=models.CASCADE,
        related_name='summaries',
        verbose_name='爬蟲任務'
    )
    summary_text = models.TextField(verbose_name='摘要內容')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='生成時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed',
        verbose_name='狀態'
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='錯誤訊息'
    )

    # LLM相關參數記錄
    model_used = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='使用的模型'
    )
    generation_time = models.FloatField(
        blank=True,
        null=True,
        verbose_name='生成耗時(秒)'
    )

    class Meta:
        verbose_name = '文章摘要'
        verbose_name_plural = '文章摘要'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['job', 'generated_at']),
        ]

    def __str__(self):
        return f"{self.article.title} - 摘要"

    def get_short_summary(self, max_length=50):
        """獲取截斷的摘要文本"""
        if not self.summary_text:
            return "無摘要"

        if len(self.summary_text) <= max_length:
            return self.summary_text
        return self.summary_text[:max_length] + "..."

    def is_available(self):
        """檢查摘要是否可用"""
        return self.status == 'completed' and self.summary_text