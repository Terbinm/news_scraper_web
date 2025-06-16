import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View

from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis, AIReport, ArticleSummary
from .utils.scraper_utils import CTTextProcessor
from .services.summary_service import SummaryAnalysisService, analyze_job_summaries_async

logger = logging.getLogger(__name__)


@method_decorator(login_required, name='dispatch')
class BaseAPIView(View):
    """基本API視圖類，提供共用功能"""

    def get_error_response(self, message, status=400):
        """返回錯誤響應"""
        return JsonResponse({'status': 'error', 'message': message}, status=status)

    def get_success_response(self, data, status=200):
        """返回成功響應"""
        response_data = {'status': 'success'}
        response_data.update(data)
        return JsonResponse(response_data, status=status)


@method_decorator(login_required, name='dispatch')
class SearchTermsAnalysisView(BaseAPIView):
    """搜索詞分析API"""

    def post(self, request):
        """處理POST請求，分析搜索詞"""
        try:
            # 解析請求數據
            try:
                data = json.loads(request.body)
                search_terms = data.get('terms', '')
            except json.JSONDecodeError:
                return self.get_error_response('無效的JSON數據')

            if not search_terms:
                return self.get_error_response('未提供搜索詞')

            # 創建CTTextProcessor實例
            processor = CTTextProcessor(output_dir=settings.MEDIA_ROOT)

            # 分析搜索詞
            analysis_results = self.analyze_terms(processor, search_terms)

            return self.get_success_response(analysis_results)

        except Exception as e:
            logger.error(f"分析搜索詞時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)

    def analyze_terms(self, processor, search_terms):
        """分析搜索詞，返回分析結果"""
        # 進行斷詞和詞性標註
        segmented_terms = processor.segment_text(search_terms)

        # 分離詞和詞性
        segmented_words = [word for word, _ in segmented_terms]

        # 提取詞性信息
        keywords = []
        for word, pos in segmented_terms:
            keywords.append({
                'word': word,
                'pos': pos
            })

        # 識別命名實體
        named_entities = processor.identify_named_entities(search_terms)
        entities_data = []
        for entity in named_entities:
            entities_data.append({
                'entity': entity.word,
                'entity_type': entity.ner
            })

        # 返回結果
        return {
            'segmented_terms': segmented_words,
            'keywords': keywords,
            'entities': entities_data
        }


@method_decorator(login_required, name='dispatch')
class ArticleStatisticsView(BaseAPIView):
    """文章統計信息API"""

    def get(self, request, job_id):
        """獲取特定任務下的文章統計信息"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 獲取統計信息
            stats = self.get_job_statistics(job)

            return self.get_success_response(stats)

        except Exception as e:
            logger.error(f"獲取任務統計信息時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)

    def get_job_statistics(self, job):
        """獲取任務統計信息"""
        from django.db.models import Count, Min, Max

        # 獲取文章總數
        article_count = Article.objects.filter(job=job).count()

        # 獲取類別分布
        category_stats = (Article.objects
                          .filter(job=job)
                          .values('category')
                          .annotate(count=Count('id'))
                          .order_by('-count'))

        # 獲取日期範圍
        date_range = Article.objects.filter(job=job).aggregate(
            min_date=Min('date'),
            max_date=Max('date')
        )

        # 獲取關鍵詞和實體總數
        keywords_count = KeywordAnalysis.objects.filter(job=job).count()
        entities_count = NamedEntityAnalysis.objects.filter(job=job).count()

        # 返回結果
        return {
            'article_count': article_count,
            'category_stats': list(category_stats),
            'date_range': {
                'min_date': date_range['min_date'].isoformat() if date_range['min_date'] else None,
                'max_date': date_range['max_date'].isoformat() if date_range['max_date'] else None
            },
            'keywords_count': keywords_count,
            'entities_count': entities_count
        }


@method_decorator(login_required, name='dispatch')
class SearchPreviewView(BaseAPIView):
    """搜索預覽API，返回搜索條件匹配的文章計數"""

    def post(self, request, job_id):
        """處理POST請求，計算匹配的文章數量"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 解析搜索條件
            try:
                search_params = json.loads(request.body)
            except json.JSONDecodeError:
                return self.get_error_response('無效的JSON數據')

            # 從搜索條件構建查詢
            from .services.search_service import SearchAnalysisService
            search_service = SearchAnalysisService(job)

            # 構建查詢但不執行
            query = search_service.build_search_query(search_params)

            # 計算匹配數量
            count = query.count()

            return self.get_success_response({
                'count': count,
                'job_id': job_id
            })

        except Exception as e:
            logger.error(f"計算搜索匹配數量時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)


# 簡易函數式API視圖，可用於快速測試
@login_required
@require_http_methods(["POST"])
def analyze_search_terms_api(request):
    """API函數：分析搜索詞並返回結果"""
    try:
        # 解析JSON請求
        data = json.loads(request.body)
        search_terms = data.get('terms', '')

        if not search_terms:
            return JsonResponse({'status': 'error', 'message': '未提供搜索詞'})

        # 使用CTTextProcessor進行分析
        processor = CTTextProcessor(output_dir=settings.MEDIA_ROOT)

        # 進行斷詞
        segmented_terms = processor.segment_text(search_terms)

        # 提取所有斷詞結果（僅詞，不含詞性）
        segmented_words = [word for word, _ in segmented_terms]

        # 提取關鍵詞（帶詞性）
        keywords = [{'word': word, 'pos': pos} for word, pos in segmented_terms]

        # 提取命名實體
        entities = processor.identify_named_entities(search_terms)
        entities_data = [{'entity': entity.word, 'entity_type': entity.ner} for entity in entities]

        return JsonResponse({
            'status': 'success',
            'segmented_terms': segmented_words,
            'keywords': keywords,
            'entities': entities_data
        })

    except Exception as e:
        logger.error(f"分析搜索詞時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@method_decorator(login_required, name='dispatch')
class AIReportAPIView(BaseAPIView):
    """AI報告生成API"""

    def post(self, request, job_id):
        """處理POST請求，生成AI報告"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 解析請求數據
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return self.get_error_response('無效的JSON數據')

            # 獲取搜索參數
            search_params = data.get('search_params', {})

            # 獲取分析結果
            search_results = data.get('search_results', [])

            # 獲取報告語言
            language = data.get('language', settings.AI_REPORT_SETTINGS['DEFAULT_LANGUAGE'])

            # 创建AI報告記錄
            report = AIReport.objects.create(
                job=job,
                search_query=search_params.get('search_terms', ''),
                language=language,
                article_count=len(search_results) if isinstance(search_results, list) else 0,
                status='pending',
                search_params=search_params
            )

            # 啟動非同步任務生成報告
            from .services.ai_service import generate_report_async
            generate_report_async(report.id, search_params, search_results)

            return self.get_success_response({
                'message': '已啟動報告生成任務，請稍後查看',
                'report_id': report.id,
                'status': 'pending'
            })

        except Exception as e:
            logger.error(f"生成AI報告時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)

    def get(self, request, job_id, report_id=None):
        """獲取報告狀態或內容"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 如果提供了特定報告ID，返回該報告詳情
            if report_id:
                try:
                    report = AIReport.objects.get(id=report_id, job=job)
                    return self.get_success_response({
                        'id': report.id,
                        'status': report.status,
                        'content': report.content if report.status == 'completed' else '',
                        'error': report.error_message,
                        'generated_at': report.generated_at.isoformat(),
                        'article_count': report.article_count
                    })
                except AIReport.DoesNotExist:
                    return self.get_error_response('報告不存在', status=404)

            # 否則返回該任務的所有報告列表
            reports = AIReport.objects.filter(job=job).order_by('-generated_at')
            return self.get_success_response({
                'reports': [
                    {
                        'id': report.id,
                        'status': report.status,
                        'search_query': report.search_query,
                        'generated_at': report.generated_at.isoformat(),
                        'article_count': report.article_count
                    }
                    for report in reports
                ]
            })

        except Exception as e:
            logger.error(f"獲取AI報告時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)


@method_decorator(login_required, name='dispatch')
class SummaryAnalysisAPIView(BaseAPIView):
    """摘要分析API"""

    def post(self, request, job_id):
        """處理POST請求，啟動摘要分析任務"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 解析請求數據
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}

            # 獲取分析參數
            batch_size = data.get('batch_size', 10)
            max_workers = data.get('max_workers', 2)

            # 檢查參數範圍
            batch_size = max(1, min(50, batch_size))  # 限制在1-50之間
            max_workers = max(1, min(4, max_workers))  # 限制在1-4之間

            # 檢查是否已有文章
            total_articles = Article.objects.filter(job=job).count()
            if total_articles == 0:
                return self.get_error_response('該任務沒有文章可分析')

            # 檢查是否已經在分析中
            pending_summaries = ArticleSummary.objects.filter(
                job=job,
                status__in=['pending', 'running']
            ).count()

            if pending_summaries > 0:
                return self.get_error_response('摘要分析任務已在進行中，請稍後再試')

            # 獲取當前統計
            analyzed_summaries = ArticleSummary.objects.filter(job=job, status='completed').count()

            # 啟動非同步摘要分析任務
            thread = analyze_job_summaries_async(job_id, batch_size, max_workers)

            return self.get_success_response({
                'message': '摘要分析任務已啟動',
                'job_id': job_id,
                'total_articles': total_articles,
                'analyzed_summaries': analyzed_summaries,
                'remaining': total_articles - analyzed_summaries,
                'batch_size': batch_size,
                'max_workers': max_workers
            })

        except Exception as e:
            logger.error(f"啟動摘要分析時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)

    def get(self, request, job_id):
        """獲取摘要分析統計信息"""
        try:
            # 檢查任務是否存在並屬於當前用戶
            try:
                job = ScrapeJob.objects.get(id=job_id, user=request.user)
            except ScrapeJob.DoesNotExist:
                return self.get_error_response('任務不存在或無權訪問', status=404)

            # 獲取摘要統計
            service = SummaryAnalysisService()
            stats = service.get_summary_statistics(job_id)

            return self.get_success_response(stats)

        except Exception as e:
            logger.error(f"獲取摘要統計時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)


@method_decorator(login_required, name='dispatch')
class ArticleSummaryAPIView(BaseAPIView):
    """單篇文章摘要API"""

    def post(self, request, article_id):
        """為單篇文章生成摘要"""
        try:
            # 檢查文章是否存在並屬於當前用戶
            try:
                article = Article.objects.get(id=article_id, job__user=request.user)
            except Article.DoesNotExist:
                return self.get_error_response('文章不存在或無權訪問', status=404)

            # 檢查是否已有摘要
            existing_summary = ArticleSummary.objects.filter(article=article).first()

            # 解析請求數據
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}

            force_regenerate = data.get('force_regenerate', False)

            if existing_summary and existing_summary.status == 'completed' and not force_regenerate:
                return self.get_success_response({
                    'message': '該文章已有摘要',
                    'already_exists': True,
                    'summary': {
                        'text': existing_summary.summary_text,
                        'generated_at': existing_summary.generated_at.isoformat(),
                        'model_used': existing_summary.model_used,
                        'generation_time': existing_summary.generation_time
                    }
                })

            # 生成摘要
            service = SummaryAnalysisService()
            success = service.regenerate_summary(article_id)

            if success:
                # 獲取新生成的摘要
                summary = ArticleSummary.objects.get(article=article)
                return self.get_success_response({
                    'message': '摘要生成成功',
                    'already_exists': False,
                    'summary': {
                        'text': summary.summary_text,
                        'generated_at': summary.generated_at.isoformat(),
                        'model_used': summary.model_used,
                        'generation_time': summary.generation_time
                    }
                })
            else:
                return self.get_error_response('摘要生成失敗')

        except Exception as e:
            logger.error(f"生成文章摘要時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)

    def get(self, request, article_id):
        """獲取單篇文章的摘要"""
        try:
            # 檢查文章是否存在並屬於當前用戶
            try:
                article = Article.objects.get(id=article_id, job__user=request.user)
            except Article.DoesNotExist:
                return self.get_error_response('文章不存在或無權訪問', status=404)

            # 獲取摘要
            try:
                summary = ArticleSummary.objects.get(article=article)
                return self.get_success_response({
                    'has_summary': True,
                    'summary': {
                        'text': summary.summary_text,
                        'status': summary.status,
                        'generated_at': summary.generated_at.isoformat(),
                        'model_used': summary.model_used,
                        'generation_time': summary.generation_time,
                        'error_message': summary.error_message
                    }
                })
            except ArticleSummary.DoesNotExist:
                return self.get_success_response({
                    'has_summary': False,
                    'message': '該文章尚未生成摘要'
                })

        except Exception as e:
            logger.error(f"獲取文章摘要時出錯: {e}", exc_info=True)
            return self.get_error_response(f"處理請求時發生錯誤: {str(e)}", status=500)


# 簡易函數式API視圖，用於快速摘要生成
@login_required
@require_http_methods(["POST"])
def generate_article_summary_api(request, article_id):
    """API函數：為單篇文章生成摘要"""
    try:
        # 檢查文章是否存在並屬於當前用戶
        article = Article.objects.get(id=article_id, job__user=request.user)

        # 解析請求數據
        data = json.loads(request.body) if request.body else {}
        force_regenerate = data.get('force_regenerate', False)

        # 檢查是否已有摘要
        existing_summary = ArticleSummary.objects.filter(article=article).first()

        if existing_summary and existing_summary.status == 'completed' and not force_regenerate:
            return JsonResponse({
                'status': 'success',
                'message': '該文章已有摘要',
                'already_exists': True,
                'summary_text': existing_summary.summary_text
            })

        # 生成摘要
        service = SummaryAnalysisService()
        result = service.analyze_article(article)

        if result and result.get('status') == 'completed':
            # 保存摘要
            summary, created = ArticleSummary.objects.update_or_create(
                article=article,
                job=article.job,
                defaults={
                    'summary_text': result['summary_text'],
                    'model_used': result.get('model_used', ''),
                    'generation_time': result.get('generation_time', 0),
                    'status': result['status']
                }
            )

            return JsonResponse({
                'status': 'success',
                'message': '摘要生成成功',
                'already_exists': False,
                'summary_text': summary.summary_text,
                'generation_time': summary.generation_time
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '摘要生成失敗',
                'error': result.get('error_message', '未知錯誤')
            })

    except Article.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '文章不存在或無權訪問'
        }, status=404)
    except Exception as e:
        logger.error(f"生成文章摘要時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)