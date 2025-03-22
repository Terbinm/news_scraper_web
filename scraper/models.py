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