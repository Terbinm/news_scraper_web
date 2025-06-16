import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from django.db import transaction
from django.conf import settings
from django.db.models import Count, Q, Avg
from django.db import models

from ..models import ScrapeJob, Article, ArticleSummary
from .ai_service import OllamaClient

logger = logging.getLogger(__name__)


class SummaryAnalysisService:
    """提供文章摘要分析服務"""

    def __init__(self):
        """初始化摘要分析服務"""
        self.logger = logging.getLogger(__name__)
        # 復用現有的 OllamaClient
        self.llm_client = OllamaClient()

    def generate_summary_prompt(self, article):
        """
        生成摘要提示詞

        Args:
            article: Article實例

        Returns:
            str: 格式化的提示詞
        """
        prompt = f"""請為以下新聞文章生成一句話摘要，要求：
1. 簡潔明瞭，控制在30字以內
2. 突出文章核心重點
3. 使用繁體中文
4. 適合作為副標題使用

文章標題：{article.title}
文章內容：{article.content[:1000]}...

摘要："""

        return prompt

    def analyze_article(self, article):
        """
        分析單篇文章生成摘要

        Args:
            article: Article實例

        Returns:
            dict: 包含摘要分析結果的字典
        """
        try:
            start_time = time.time()

            # 生成提示詞
            prompt = self.generate_summary_prompt(article)

            # 調用LLM生成摘要
            summary_text = self.llm_client.generate(
                prompt,
                temperature=0.3,  # 較低的溫度以獲得更一致的結果
                max_tokens=100  # 限制輸出長度
            )

            # 清理摘要文本
            summary_text = summary_text.strip()
            # 移除可能的引號
            summary_text = summary_text.strip('"\'')

            generation_time = time.time() - start_time

            result = {
                'article_id': article.id,
                'summary_text': summary_text,
                'model_used': self.llm_client.model,
                'generation_time': generation_time,
                'status': 'completed'
            }

            self.logger.info(f"成功生成文章 {article.id} 的摘要，耗時 {generation_time:.2f}秒")
            return result

        except Exception as e:
            self.logger.error(f"分析文章 {article.id} 時出錯: {e}", exc_info=True)
            return {
                'article_id': article.id,
                'summary_text': '',
                'error_message': str(e),
                'status': 'failed'
            }

    def analyze_job_articles(self, job_id, batch_size=10, max_workers=2, max_check_attempts=3):
        """
        分析指定任務的所有文章摘要

        Args:
            job_id: ScrapeJob的ID
            batch_size: 批次大小
            max_workers: 最大工作執行緒數（LLM處理建議較少線程）
            max_check_attempts: 最大重新檢查次數

        Returns:
            bool: 是否成功完成分析
        """
        try:
            # 獲取任務
            job = ScrapeJob.objects.get(id=job_id)

            # 檢查是否已經完成摘要分析
            total_articles = Article.objects.filter(job=job).count()
            analyzed_articles = ArticleSummary.objects.filter(job=job, status='completed').count()

            if total_articles == analyzed_articles and total_articles > 0:
                self.logger.info(f"任務 {job_id} 已完成摘要分析（{analyzed_articles}/{total_articles}篇已分析），跳過處理")
                return True

            self.logger.info(f"任務 {job_id} 共有 {total_articles} 篇文章需要分析摘要")

            # 初始化失敗列表
            failed_articles = []

            # 重複檢查未分析文章的次數
            check_attempts = 0
            all_processed = False

            while check_attempts < max_check_attempts and not all_processed:
                # 獲取尚未分析摘要的文章
                articles = Article.objects.filter(
                    job=job
                ).exclude(
                    summary__status='completed'
                ).order_by('id')

                remaining_articles = articles.count()
                if remaining_articles == 0:
                    self.logger.info(f"任務 {job_id} 所有文章摘要已分析完成")
                    all_processed = True
                    break

                self.logger.info(
                    f"開始分析任務 {job_id} 的 {remaining_articles} 篇文章摘要（第 {check_attempts + 1} 次檢查）")

                # 使用較少的多執行緒處理（LLM處理通常IO密集）
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
                            if result and result.get('status') == 'completed':
                                successful_results.append(result)
                            else:
                                # 記錄失敗的文章ID
                                article_id = batch_articles[idx].id
                                current_batch_failed.append(article_id)
                                self.logger.warning(f"文章 {article_id} 摘要分析失敗，將在下一次嘗試中重試")

                        # 保存結果到資料庫
                        with transaction.atomic():
                            for result in successful_results:
                                article_id = result['article_id']
                                article = Article.objects.get(id=article_id)

                                # 創建或更新摘要記錄
                                summary, created = ArticleSummary.objects.update_or_create(
                                    article=article,
                                    job=job,
                                    defaults={
                                        'summary_text': result['summary_text'],
                                        'model_used': result.get('model_used', ''),
                                        'generation_time': result.get('generation_time', 0),
                                        'status': result['status'],
                                        'error_message': result.get('error_message', '')
                                    }
                                )

                        processed_count += len(successful_results)
                        self.logger.info(f"已處理 {processed_count}/{remaining_articles} 篇文章摘要")

                        # 在批次之間添加短暫延遲，避免過度請求LLM服務
                        time.sleep(1)

                # 添加本次失敗的文章到失敗列表
                failed_articles.extend(current_batch_failed)

                # 增加檢查次數
                check_attempts += 1

                # 如果本次沒有失敗的文章，或者已經達到最大嘗試次數
                if not current_batch_failed or check_attempts >= max_check_attempts:
                    # 檢查是否所有文章都已處理完成
                    unprocessed = Article.objects.filter(job=job).exclude(
                        summary__status='completed'
                    ).count()
                    if unprocessed == 0:
                        all_processed = True
                        self.logger.info(f"任務 {job_id} 所有文章摘要都已成功分析")
                    else:
                        self.logger.warning(f"任務 {job_id} 還有 {unprocessed} 篇文章摘要未能成功分析")

            # 最終確認是否所有文章都已分析
            total_articles = Article.objects.filter(job=job).count()
            analyzed_articles = ArticleSummary.objects.filter(job=job, status='completed').count()

            self.logger.info(f"任務 {job_id} 的摘要分析完成，{analyzed_articles}/{total_articles} 篇文章已分析")
            return True

        except Exception as e:
            self.logger.error(f"分析任務 {job_id} 摘要時出錯: {e}", exc_info=True)
            return False

    def get_summary_statistics(self, job_id):
        """
        獲取任務的摘要統計信息

        Args:
            job_id: ScrapeJob的ID

        Returns:
            dict: 包含摘要統計的字典
        """
        try:
            job = ScrapeJob.objects.get(id=job_id)

            # 獲取統計數據
            total_articles = Article.objects.filter(job=job).count()
            analyzed_summaries = ArticleSummary.objects.filter(job=job, status='completed').count()
            failed_summaries = ArticleSummary.objects.filter(job=job, status='failed').count()
            pending_summaries = total_articles - analyzed_summaries - failed_summaries

            # 計算平均生成時間
            avg_generation_time = (ArticleSummary.objects
                                   .filter(job=job, status='completed', generation_time__isnull=False)
                                   .aggregate(avg_time=Avg('generation_time'))['avg_time'] or 0)

            return {
                'total_articles': total_articles,
                'analyzed_summaries': analyzed_summaries,
                'failed_summaries': failed_summaries,
                'pending_summaries': pending_summaries,
                'analysis_progress': int((analyzed_summaries / total_articles * 100) if total_articles > 0 else 0),
                'avg_generation_time': round(avg_generation_time, 2)
            }

        except Exception as e:
            self.logger.error(f"獲取摘要統計時出錯: {e}", exc_info=True)
            return {
                'total_articles': 0,
                'analyzed_summaries': 0,
                'failed_summaries': 0,
                'pending_summaries': 0,
                'analysis_progress': 0,
                'avg_generation_time': 0
            }

    def get_unanalyzed_articles(self, job_id, limit=100):
        """
        獲取未分析摘要的文章列表

        Args:
            job_id: ScrapeJob的ID
            limit: 最大返回數量

        Returns:
            list: 未分析摘要文章的列表
        """
        try:
            job = ScrapeJob.objects.get(id=job_id)

            # 尋找未分析摘要的文章
            unanalyzed = Article.objects.filter(
                job=job
            ).exclude(
                summary__status='completed'
            ).order_by('-date')[:limit]

            return list(unanalyzed)

        except Exception as e:
            self.logger.error(f"獲取未分析摘要文章時出錯: {e}", exc_info=True)
            return []

    def regenerate_summary(self, article_id):
        """
        重新生成特定文章的摘要

        Args:
            article_id: Article的ID

        Returns:
            bool: 是否成功重新生成
        """
        try:
            article = Article.objects.get(id=article_id)

            # 分析文章
            result = self.analyze_article(article)

            if result and result.get('status') == 'completed':
                # 更新或創建摘要記錄
                summary, created = ArticleSummary.objects.update_or_create(
                    article=article,
                    job=article.job,
                    defaults={
                        'summary_text': result['summary_text'],
                        'model_used': result.get('model_used', ''),
                        'generation_time': result.get('generation_time', 0),
                        'status': result['status'],
                        'error_message': ''
                    }
                )

                action = "創建" if created else "更新"
                self.logger.info(f"成功{action}文章 {article_id} 的摘要")
                return True
            else:
                self.logger.error(f"重新生成文章 {article_id} 摘要失敗")
                return False

        except Exception as e:
            self.logger.error(f"重新生成文章 {article_id} 摘要時出錯: {e}", exc_info=True)
            return False


# 單一函數接口，用於執行摘要分析任務
def analyze_job_summaries(job_id, batch_size=10, max_workers=2, max_check_attempts=3):
    """
    執行摘要分析任務

    Args:
        job_id: ScrapeJob的ID
        batch_size: 批次大小
        max_workers: 最大工作執行緒數
        max_check_attempts: 最大重新檢查次數

    Returns:
        bool: 是否成功完成分析
    """
    service = SummaryAnalysisService()
    return service.analyze_job_articles(job_id, batch_size, max_workers, max_check_attempts)


def analyze_job_summaries_async(job_id, batch_size=10, max_workers=2):
    """
    非同步執行摘要分析任務

    Args:
        job_id: ScrapeJob的ID
        batch_size: 批次大小
        max_workers: 最大工作執行緒數

    Returns:
        threading.Thread: 啟動的線程實例
    """
    thread = threading.Thread(
        target=analyze_job_summaries,
        args=(job_id, batch_size, max_workers)
    )
    thread.daemon = True
    thread.start()
    logger.info(f"啟動摘要分析任務 {job_id} 的執行線程")
    return thread