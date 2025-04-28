import logging
import os
import json
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.conf import settings
from django.db.models import Count, Avg, F, Q

from ..models import ScrapeJob, Article, SentimentAnalysis, CategorySentimentSummary
from ..utils.sentiment_analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class SentimentAnalysisService:
    """提供文章情感分析服務"""

    def __init__(self, cache_dir=None):
        """
        初始化情感分析服務

        Args:
            cache_dir: 模型快取目錄，預設使用settings.MEDIA_ROOT下的models目錄
        """
        if cache_dir is None:
            cache_dir = os.path.join(settings.MEDIA_ROOT, 'models')
            os.makedirs(cache_dir, exist_ok=True)

        self.analyzer = SentimentAnalyzer(cache_dir=cache_dir)
        self.logger = logging.getLogger(__name__)

    def analyze_article(self, article):
        """
        分析單篇文章情感

        Args:
            article: Article實例

        Returns:
            dict: 包含情感分析結果的字典
        """
        try:
            # 分析文章內容
            content_result = self.analyzer.analyze(article.content)

            # 分析文章標題
            title_result = self.analyzer.analyze(article.title)

            # 合併結果
            result = {
                'article_id': article.id,
                'content': content_result,
                'title': title_result
            }

            return result
        except Exception as e:
            self.logger.error(f"分析文章 {article.id} 時出錯: {e}", exc_info=True)
            return None

    def analyze_job_articles(self, job_id, batch_size=20, max_workers=4):
        """
        分析指定任務的所有文章

        Args:
            job_id: ScrapeJob的ID
            batch_size: 批次大小
            max_workers: 最大工作執行緒數

        Returns:
            bool: 是否成功完成分析
        """
        try:
            # 獲取任務
            job = ScrapeJob.objects.get(id=job_id)

            # 檢查是否已經完成情感分析
            if job.sentiment_analyzed:
                self.logger.info(f"任務 {job_id} 已完成情感分析，跳過處理")
                return True

            # 獲取尚未分析情感的文章
            articles = Article.objects.filter(
                job=job
            ).exclude(
                sentiment__isnull=False
            ).order_by('id')

            total_articles = articles.count()
            if total_articles == 0:
                self.logger.info(f"任務 {job_id} 沒有新文章需要分析")

                # 更新任務狀態
                job.sentiment_analyzed = True
                job.save()

                return True

            self.logger.info(f"開始分析任務 {job_id} 的 {total_articles} 篇文章")

            # 使用多執行緒處理
            processed_count = 0

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 批次處理
                for i in range(0, total_articles, batch_size):
                    batch_articles = articles[i:i + batch_size]
                    batch_results = list(executor.map(self.analyze_article, batch_articles))

                    # 過濾掉失敗的結果
                    batch_results = [r for r in batch_results if r is not None]

                    # 保存結果到資料庫
                    with transaction.atomic():
                        for result in batch_results:
                            article_id = result['article_id']
                            article = Article.objects.get(id=article_id)

                            # 創建或更新情感分析記錄
                            sentiment, created = SentimentAnalysis.objects.update_or_create(
                                article=article,
                                job=job,
                                defaults={
                                    'positive_score': result['content']['positive'],
                                    'negative_score': result['content']['negative'],
                                    'sentiment': result['content']['sentiment'],
                                    'title_sentiment': result['title']['sentiment'],
                                    'title_positive_score': result['title']['positive'],
                                    'title_negative_score': result['title']['negative']
                                }
                            )

                    processed_count += len(batch_results)
                    self.logger.info(f"已處理 {processed_count}/{total_articles} 篇文章")

            # 生成類別情感摘要
            self.generate_category_sentiment_summary(job)

            # 更新任務狀態
            job.sentiment_analyzed = True
            job.save()

            self.logger.info(f"任務 {job_id} 的情感分析已完成")
            return True

        except Exception as e:
            self.logger.error(f"分析任務 {job_id} 時出錯: {e}", exc_info=True)
            return False

    def generate_category_sentiment_summary(self, job):
        """
        生成各類別情感分析摘要

        Args:
            job: ScrapeJob實例
        """
        try:
            # 按類別統計情感分析結果
            categories = Article.objects.filter(
                job=job
            ).values_list('category', flat=True).distinct()

            for category in categories:
                # 獲取該類別的所有文章
                articles = Article.objects.filter(
                    job=job,
                    category=category
                )

                # 獲取已有情感分析結果的文章
                sentiments = SentimentAnalysis.objects.filter(
                    job=job,
                    article__category=category
                )

                # 如果該類別有文章但沒有情感分析，跳過
                if articles.count() > 0 and sentiments.count() == 0:
                    self.logger.info(f"類別 {category} 的文章尚未分析情感，跳過生成摘要")
                    continue

                # 統計正面和負面文章數量
                positive_count = sentiments.filter(sentiment='正面').count()
                negative_count = sentiments.filter(sentiment='負面').count()

                # 計算平均正面情感分數，避免除以零的錯誤
                if positive_count > 0:
                    avg_positive = sentiments.filter(sentiment='正面').aggregate(avg=Avg('positive_score'))['avg'] or 0
                else:
                    avg_positive = 0

                # 創建或更新類別情感摘要
                CategorySentimentSummary.objects.update_or_create(
                    job=job,
                    category=category,
                    defaults={
                        'positive_count': positive_count,
                        'negative_count': negative_count,
                        'average_positive_score': avg_positive
                    }
                )

            self.logger.info(f"已生成任務 {job.id} 的類別情感摘要")

        except Exception as e:
            self.logger.error(f"生成類別情感摘要時出錯: {e}", exc_info=True)

    def get_category_sentiment_summary(self, job_id):
        """
        獲取任務的類別情感摘要

        Args:
            job_id: ScrapeJob的ID

        Returns:
            dict: 包含類別情感摘要的字典
        """
        try:
            # 獲取類別情感摘要
            summaries = CategorySentimentSummary.objects.filter(job_id=job_id)

            if not summaries.exists():
                self.logger.warning(f"任務 {job_id} 沒有情感摘要數據")
                # 嘗試自動生成摘要
                job = ScrapeJob.objects.get(id=job_id)
                self.generate_category_sentiment_summary(job)
                summaries = CategorySentimentSummary.objects.filter(job_id=job_id)

                # 如果仍然沒有數據，返回空結果
                if not summaries.exists():
                    return {
                        'categories': [],
                        'positive_counts': [],
                        'negative_counts': [],
                        'average_scores': [],
                        'total_counts': []
                    }

            # 構建結果
            result = {
                'categories': [],
                'positive_counts': [],
                'negative_counts': [],
                'average_scores': [],
                'total_counts': []
            }

            for summary in summaries:
                result['categories'].append(summary.category)
                result['positive_counts'].append(summary.positive_count)
                result['negative_counts'].append(summary.negative_count)
                result['average_scores'].append(round(summary.average_positive_score, 2))
                # 總數為正面和負面的總和
                result['total_counts'].append(summary.positive_count + summary.negative_count)

            return result

        except Exception as e:
            self.logger.error(f"獲取類別情感摘要時出錯: {e}", exc_info=True)
            return {
                'categories': [],
                'positive_counts': [],
                'negative_counts': [],
                'average_scores': [],
                'total_counts': []
            }

    def get_sentiment_distribution(self, job_id):
        """
        獲取任務的情感分佈

        Args:
            job_id: ScrapeJob的ID

        Returns:
            dict: 包含情感分佈的字典
        """
        try:
            # 獲取情感分析結果
            sentiments = SentimentAnalysis.objects.filter(job_id=job_id)

            # 統計正面和負面文章數量
            positive_count = sentiments.filter(sentiment='正面').count()
            negative_count = sentiments.filter(sentiment='負面').count()

            # 統計標題情感
            title_positive = sentiments.filter(title_sentiment='正面').count()
            title_negative = sentiments.filter(title_sentiment='負面').count()

            # 構建結果
            result = {
                'content': {
                    'positive': positive_count,
                    'negative': negative_count
                },
                'title': {
                    'positive': title_positive,
                    'negative': title_negative
                }
            }

            return result

        except Exception as e:
            self.logger.error(f"獲取情感分佈時出錯: {e}", exc_info=True)
            return None


# 單一函數接口，用於執行情感分析任務
def analyze_job_sentiment(job_id, batch_size=20, max_workers=4):
    """
    執行情感分析任務

    Args:
        job_id: ScrapeJob的ID
        batch_size: 批次大小
        max_workers: 最大工作執行緒數

    Returns:
        bool: 是否成功完成分析
    """
    service = SentimentAnalysisService()
    return service.analyze_job_articles(job_id, batch_size, max_workers)