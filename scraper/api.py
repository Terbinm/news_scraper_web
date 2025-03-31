import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View

from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis
from .utils.scraper_utils import CTTextProcessor

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