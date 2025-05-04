from django.db import models
from django.contrib.auth.models import User


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