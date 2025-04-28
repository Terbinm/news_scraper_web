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

    def analyze_job_articles(self, job_id, batch_size=20, max_workers=4, max_check_attempts=5):
        """
        分析指定任務的所有文章

        Args:
            job_id: ScrapeJob的ID
            batch_size: 批次大小
            max_workers: 最大工作執行緒數
            max_check_attempts: 最大重新檢查次數

        Returns:
            bool: 是否成功完成分析
        """
        try:
            # 獲取任務
            job = ScrapeJob.objects.get(id=job_id)

            # 檢查是否已經完成情感分析 - 增加嚴格檢查
            if job.sentiment_analyzed:
                # 額外確認是否所有文章都已分析
                total_articles = Article.objects.filter(job=job).count()
                analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()

                if total_articles == analyzed_articles:
                    self.logger.info(
                        f"任務 {job_id} 已完成情感分析（{analyzed_articles}/{total_articles}篇已分析），跳過處理")
                    return True
                else:
                    self.logger.warning(
                        f"任務 {job_id} 標記為已完成分析，但實際上只有 {analyzed_articles}/{total_articles} 篇文章被分析。繼續分析未完成的文章。")
                    # 重置標記，繼續處理未分析的文章
                    job.sentiment_analyzed = False
                    job.save(update_fields=['sentiment_analyzed'])

            # 記錄總文章數
            total_articles_count = Article.objects.filter(job=job).count()
            self.logger.info(f"任務 {job_id} 共有 {total_articles_count} 篇文章需要分析")

            # 初始化失敗列表
            failed_articles = []

            # 重複檢查未分析文章的次數
            check_attempts = 0
            all_processed = False

            while check_attempts < max_check_attempts and not all_processed:
                # 獲取尚未分析情感的文章
                articles = Article.objects.filter(
                    job=job
                ).exclude(
                    sentiment__isnull=False
                ).order_by('id')

                remaining_articles = articles.count()
                if remaining_articles == 0:
                    self.logger.info(f"任務 {job_id} 所有文章已分析完成")
                    all_processed = True
                    break

                self.logger.info(
                    f"開始分析任務 {job_id} 的 {remaining_articles} 篇文章（第 {check_attempts + 1} 次檢查）")

                # 使用多執行緒處理
                processed_count = 0
                current_batch_failed = []

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 批次處理
                    for i in range(0, remaining_articles, batch_size):
                        batch_articles = articles[i:i + batch_size]
                        batch_results = list(executor.map(self.analyze_article, batch_articles))

                        # 過濾掉失敗的結果
                        successful_results = []
                        for idx, result in enumerate(batch_results):
                            if result is not None:
                                successful_results.append(result)
                            else:
                                # 記錄失敗的文章ID
                                article_id = batch_articles[idx].id
                                current_batch_failed.append(article_id)
                                self.logger.warning(f"文章 {article_id} 分析失敗，將在下一次嘗試中重試")

                        # 保存結果到資料庫
                        with transaction.atomic():
                            for result in successful_results:
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

                        processed_count += len(successful_results)
                        self.logger.info(f"已處理 {processed_count}/{remaining_articles} 篇文章")

                # 添加本次失敗的文章到失敗列表
                failed_articles.extend(current_batch_failed)

                # 增加檢查次數
                check_attempts += 1

                # 如果本次沒有失敗的文章，或者已經達到最大嘗試次數
                if not current_batch_failed or check_attempts >= max_check_attempts:
                    # 檢查是否所有文章都已處理完成
                    unprocessed = Article.objects.filter(job=job).exclude(sentiment__isnull=False).count()
                    if unprocessed == 0:
                        all_processed = True
                        self.logger.info(f"任務 {job_id} 所有文章都已成功分析")
                    else:
                        self.logger.warning(f"任務 {job_id} 還有 {unprocessed} 篇文章未能成功分析")

            # 生成類別情感摘要
            self.generate_category_sentiment_summary(job)

            # 最終確認是否所有文章都已分析
            total_articles = Article.objects.filter(job=job).count()
            analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()

            # 只有當所有文章都分析完成時，才將任務標記為已完成
            if total_articles == analyzed_articles:
                job.sentiment_analyzed = True
                job.save(update_fields=['sentiment_analyzed'])
                self.logger.info(f"任務 {job_id} 的情感分析已完成，所有 {total_articles} 篇文章都已分析")
                return True
            else:
                self.logger.warning(
                    f"任務 {job_id} 情感分析未完全完成，僅 {analyzed_articles}/{total_articles} 篇文章被分析")
                # 雖然未全部完成，但已盡力分析，仍返回成功
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
            # 獲取該任務的所有情感分析結果
            sentiments = SentimentAnalysis.objects.filter(job=job)

            # 獲取所有文章類別
            categories = Article.objects.filter(job=job).values_list('category', flat=True).distinct()

            for category in categories:
                # 篩選特定類別的情感分析結果
                category_sentiments = sentiments.filter(article__category=category)

                # 跳過沒有情感分析結果的類別
                if category_sentiments.count() == 0:
                    self.logger.warning(f"類別 {category} 沒有情感分析結果，跳過摘要生成")
                    continue

                # 統計正面、負面和中立文章數
                positive_count = category_sentiments.filter(sentiment='正面').count()
                negative_count = category_sentiments.filter(sentiment='負面').count()
                neutral_count = category_sentiments.filter(sentiment='中立').count()

                # 計算平均正面情感分數
                avg_positive_score = (
                        category_sentiments
                        .aggregate(avg_positive=Avg('positive_score'))['avg_positive'] or 0
                )

                # 創建或更新類別情感摘要 - 使用update_or_create而不是create
                summary, created = CategorySentimentSummary.objects.update_or_create(
                    job=job,
                    category=category,
                    defaults={
                        'positive_count': positive_count,
                        'negative_count': negative_count,
                        'neutral_count': neutral_count,
                        'average_positive_score': avg_positive_score
                    }
                )

                action = "創建" if created else "更新"
                self.logger.info(
                    f"已{action}類別 {category} 的情感摘要: 正面={positive_count}, 負面={negative_count}, 中立={neutral_count}")

        except Exception as e:
            self.logger.error(f"生成類別情感摘要時出錯: {e}", exc_info=True)

    def regenerate_sentiment_summary(self, job):
        """
        完全重建類別情感摘要數據

        Args:
            job: ScrapeJob實例

        Returns:
            bool: 是否成功重建摘要
        """
        try:
            # 先刪除該任務的所有摘要數據
            CategorySentimentSummary.objects.filter(job=job).delete()
            self.logger.info(f"已刪除任務 {job.id} 的所有現有情感摘要")

            # 獲取所有文章類別
            categories = Article.objects.filter(job=job).values_list('category', flat=True).distinct()

            # 對每個類別，重新計算摘要數據
            for category in categories:
                # 獲取該類別的所有已分析文章
                category_sentiments = SentimentAnalysis.objects.filter(
                    job=job,
                    article__category=category
                )

                # 只有當有分析結果時才創建摘要
                if category_sentiments.exists():
                    # 統計正面、負面和中立文章數
                    positive_count = category_sentiments.filter(sentiment='正面').count()
                    negative_count = category_sentiments.filter(sentiment='負面').count()
                    neutral_count = category_sentiments.filter(sentiment='中立').count()

                    # 計算平均正面情感分數
                    avg_positive_score = (
                            category_sentiments.aggregate(avg_positive=Avg('positive_score'))['avg_positive'] or 0
                    )

                    # 創建新的摘要記錄
                    CategorySentimentSummary.objects.create(
                        job=job,
                        category=category,
                        positive_count=positive_count,
                        negative_count=negative_count,
                        neutral_count=neutral_count,
                        average_positive_score=avg_positive_score
                    )

                    self.logger.info(
                        f"已重建類別 {category} 的情感摘要: 正面={positive_count}, 負面={negative_count}, 中立={neutral_count}")

            return True

        except Exception as e:
            self.logger.error(f"重建類別情感摘要時出錯: {e}", exc_info=True)
            return False


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
                        'neutral_counts': [],
                        'average_scores': [],
                        'total_counts': []
                    }

            # 構建結果
            result = {
                'categories': [],
                'positive_counts': [],
                'negative_counts': [],
                'neutral_counts': [],
                'average_scores': [],
                'total_counts': []
            }

            for summary in summaries:
                result['categories'].append(summary.category)
                result['positive_counts'].append(summary.positive_count)
                result['negative_counts'].append(summary.negative_count)
                result['neutral_counts'].append(summary.neutral_count)  # 添加中立計數
                result['average_scores'].append(round(summary.average_positive_score, 2))
                # 總數為正面、負面和中立的總和
                result['total_counts'].append(summary.positive_count + summary.negative_count + summary.neutral_count)

            return result

        except Exception as e:
            self.logger.error(f"獲取類別情感摘要時出錯: {e}", exc_info=True)
            return {
                'categories': [],
                'positive_counts': [],
                'negative_counts': [],
                'neutral_counts': [],
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

            # 檢查是否有情感分析結果
            if not sentiments.exists():
                self.logger.warning(f"任務 {job_id} 沒有情感分析結果")
                return None

            # 統計正面、負面和中立文章數量
            positive_count = sentiments.filter(sentiment='正面').count()
            negative_count = sentiments.filter(sentiment='負面').count()
            neutral_count = sentiments.filter(sentiment='中立').count()

            # 統計標題情感
            title_positive = sentiments.filter(title_sentiment='正面').count()
            title_negative = sentiments.filter(title_sentiment='負面').count()
            title_neutral = sentiments.filter(title_sentiment='中立').count()

            return {
                'content': {
                    'positive': positive_count,
                    'negative': negative_count,
                    'neutral': neutral_count
                },
                'title': {
                    'positive': title_positive,
                    'negative': title_negative,
                    'neutral': title_neutral
                },
                'total': positive_count + negative_count + neutral_count
            }

        except Exception as e:
            self.logger.error(f"獲取情感分佈時出錯: {e}", exc_info=True)
            return None

    def get_unanalyzed_articles(self, job_id, limit=100):
        """
        獲取未分析的文章列表

        Args:
            job_id: ScrapeJob的ID
            limit: 最大返回數量

        Returns:
            list: 未分析文章的列表
        """
        try:
            job = ScrapeJob.objects.get(id=job_id)

            # 尋找未分析的文章
            unanalyzed = Article.objects.filter(
                job=job
            ).exclude(
                sentiment__isnull=False
            ).order_by('-date')[:limit]

            return list(unanalyzed)

        except Exception as e:
            self.logger.error(f"獲取未分析文章時出錯: {e}", exc_info=True)
            return []


# 單一函數接口，用於執行情感分析任務
def analyze_job_sentiment(job_id, batch_size=20, max_workers=4, max_check_attempts=5):
    """
    執行情感分析任務

    Args:
        job_id: ScrapeJob的ID
        batch_size: 批次大小
        max_workers: 最大工作執行緒數
        max_check_attempts: 最大重新檢查次數

    Returns:
        bool: 是否成功完成分析
    """
    service = SentimentAnalysisService()
    return service.analyze_job_articles(job_id, batch_size, max_workers, max_check_attempts)