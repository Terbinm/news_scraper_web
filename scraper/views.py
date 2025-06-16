import json
import logging
import os

from datetime import datetime

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models

from news_scraper_web import settings
from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis, SentimentAnalysis, \
    CategorySentimentSummary, AIReport, ArticleSummary
from .forms import LoginForm, ScrapeJobForm, KeywordFilterForm, AdvancedSearchForm
from .services.search_service import SearchAnalysisService
from .services.task_service import execute_scraper_task
from .services.sentiment_service import analyze_job_sentiment, SentimentAnalysisService
from .services.analysis_service import (
    get_keywords_analysis,
    get_entities_analysis,
    get_category_colors
)
from scraper.utils.scraper_utils import CTTextProcessor
logger = logging.getLogger(__name__)

from collections import defaultdict
from django.db.models import Count, Avg, F, Q
from .services.summary_service import SummaryAnalysisService, analyze_job_summaries_async


def login_view(request):
    """登入視圖"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('job_list')
            else:
                messages.error(request, '用戶名或密碼錯誤')
    else:
        form = LoginForm()

    return render(request, 'scraper/login.html', {'form': form})


@login_required
def logout_view(request):
    """登出視圖"""
    logout(request)
    return redirect('login')


@login_required
def job_list(request):
    """爬蟲任務列表"""
    jobs = ScrapeJob.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'scraper/job_list.html', {'jobs': jobs})


@login_required
def job_create(request):
    """創建新爬蟲任務"""
    if request.method == 'POST':
        form = ScrapeJobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.user = request.user
            job.status = 'pending'
            job.save()

            # 啟動爬蟲任務
            execute_scraper_task(job.id)

            messages.success(request, '爬蟲任務已創建並開始執行')
            return redirect('job_list')
    else:
        form = ScrapeJobForm()

    return render(request, 'scraper/job_create.html', {'form': form})


@login_required
def job_detail(request, job_id):
    """爬蟲任務概覽頁面 - 顯示基本信息和導航選項"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取任務統計信息
    articles_count = Article.objects.filter(job=job).count()
    keywords_count = KeywordAnalysis.objects.filter(job=job).count()
    entities_count = NamedEntityAnalysis.objects.filter(job=job).count()

    # 獲取情感分析狀態
    sentiment_count = SentimentAnalysis.objects.filter(job=job).count()
    sentiment_progress = 0
    if articles_count > 0:
        sentiment_progress = int((sentiment_count / articles_count) * 100)

    # 獲取每個類別的文章數量
    category_stats = (Article.objects
                      .filter(job=job)
                      .values('category')
                      .annotate(count=models.Count('id'))
                      .order_by('-count'))

    # 獲取最新的幾篇文章
    recent_articles = Article.objects.filter(job=job).order_by('-date')[:15]

    return render(request, 'scraper/job_detail.html', {
        'job': job,
        'articles_count': articles_count,
        'keywords_count': keywords_count,
        'entities_count': entities_count,
        'category_stats': category_stats,
        'recent_articles': recent_articles,
        'sentiment_count': sentiment_count,
        'sentiment_progress': sentiment_progress,
    })


@login_required
def job_keywords_analysis(request, job_id):
    """關鍵詞分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務下所有實際存在的類別 - 使用 set 去重
    available_categories = set(KeywordAnalysis.objects.filter(job=job).values_list('category', flat=True))
    available_categories = list(available_categories)  # 轉換為列表並排序
    available_categories.sort()

    # 獲取所有存在的詞性
    available_pos = set(KeywordAnalysis.objects.filter(job=job).values_list('pos', flat=True))
    available_pos = list(available_pos)
    available_pos.sort()

    # 詞性名稱映射
    pos_names = {
        'Na': '普通名詞 (Na)',
        'Nb': '專有名詞 (Nb)',
        'Nc': '地方名詞 (Nc)'
    }

    # 詞性顏色映射
    pos_colors = {
        'Na': {'bg': 'rgba(23, 162, 184, 0.7)', 'border': 'rgba(23, 162, 184, 1)'},
        'Nb': {'bg': 'rgba(40, 167, 69, 0.7)', 'border': 'rgba(40, 167, 69, 1)'},
        'Nc': {'bg': 'rgba(255, 193, 7, 0.7)', 'border': 'rgba(255, 193, 7, 1)'}
    }

    # 處理篩選表單
    form = KeywordFilterForm(request.GET)

    # 設置初始表單數據
    if not request.GET:
        form = KeywordFilterForm(initial={
            'selected_categories': available_categories,
            'analysis_type': 'keywords'
        })

    # 根據請求參數獲取關鍵詞分析結果
    result = get_keywords_analysis(job, form, available_categories)

    # 檢查類別數量是否為1，如果為1則禁用跨類別分析功能
    disable_cross_category = len(available_categories) <= 1

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'keywords': result['keywords'],
        'form': form,
        'available_categories': available_categories,
        'available_pos': available_pos,
        'pos_names': pos_names,
        'pos_colors': pos_colors,
        'is_cross_category': result['is_cross_category'],
        'category_colors': get_category_colors(),
        'disable_cross_category': disable_cross_category,
        'selected_pos': request.GET.getlist('pos', [])
    }

    return render(request, 'scraper/job_keywords.html', context)

@login_required
def job_entities_analysis(request, job_id):
    """命名實體分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務下所有實際存在的類別 - 使用 set 去重
    available_categories = set(NamedEntityAnalysis.objects.filter(job=job).values_list('category', flat=True))
    available_categories = list(available_categories)  # 轉換為列表並排序
    available_categories.sort()


    # 實體類型名稱映射
    entity_type_names = {
        'PERSON': '人物 (PERSON)',
        'LOC': '地點 (LOC)',
        'ORG': '組織 (ORG)',
        'TIME': '時間 (TIME)',
        'MISC': '其他 (MISC)'
    }

    # 獲取所有存在的實體類型
    # available_entity_types = set(NamedEntityAnalysis.objects.filter(job=job).values_list('entity_type', flat=True))
    # available_entity_types = list(available_entity_types)
    available_entity_types = list(entity_type_names)
    available_entity_types.sort()

    # 實體類型顏色映射
    entity_type_colors = {
        'PERSON': {'bg': 'rgba(255, 99, 132, 0.7)', 'border': 'rgba(255, 99, 132, 1)'},
        'LOC': {'bg': 'rgba(54, 162, 235, 0.7)', 'border': 'rgba(54, 162, 235, 1)'},
        'ORG': {'bg': 'rgba(255, 206, 86, 0.7)', 'border': 'rgba(255, 206, 86, 1)'},
        'TIME': {'bg': 'rgba(75, 192, 192, 0.7)', 'border': 'rgba(75, 192, 192, 1)'},
        'MISC': {'bg': 'rgba(153, 102, 255, 0.7)', 'border': 'rgba(153, 102, 255, 1)'}
    }

    # 處理篩選表單
    form = KeywordFilterForm(request.GET)

    # 設置初始表單數據
    if not request.GET:
        form = KeywordFilterForm(initial={
            'selected_categories': available_categories,
            'analysis_type': 'entities'
        })

    # 根據請求參數獲取命名實體分析結果
    result = get_entities_analysis(job, form, available_categories)

    # 檢查類別數量是否為1，如果為1則禁用跨類別分析功能
    disable_cross_category = len(available_categories) <= 1

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'entities': result['entities'],
        'form': form,
        'available_categories': available_categories,
        'available_entity_types': available_entity_types,
        'entity_type_names': entity_type_names,
        'entity_type_colors': entity_type_colors,
        'is_cross_category': result['is_cross_category'],
        'category_colors': get_category_colors(),
        'disable_cross_category': disable_cross_category,
        'selected_entity_types': request.GET.getlist('entity_type', [])
    }

    return render(request, 'scraper/job_entities.html', context)

@login_required
def job_articles(request, job_id):
    """文章列表視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務的所有文章
    articles_query = Article.objects.filter(job=job)

    # 從任務中獲取實際存在的類別
    available_categories = {}
    categories_used = articles_query.values_list('category', flat=True).distinct()

    # 建立類別與顏色的對應關係
    category_colors = get_category_colors()
    for category in categories_used:
        if category in category_colors:
            available_categories[category] = category_colors[category]

    # 處理搜尋關鍵字
    search_keyword = request.GET.get('keyword', '')
    content_only = 'content_only' in request.GET

    if search_keyword:
        if content_only:
            # 僅搜尋內容
            articles_query = articles_query.filter(content__icontains=search_keyword)
        else:
            # 搜尋標題、內容和作者
            articles_query = articles_query.filter(
                models.Q(title__icontains=search_keyword) |
                models.Q(content__icontains=search_keyword) |
                models.Q(author__icontains=search_keyword)
            )

    # 處理類別篩選
    selected_categories = request.GET.getlist('categories', [])
    if selected_categories:
        articles_query = articles_query.filter(category__in=selected_categories)

    # 處理排序
    sort_by = request.GET.get('sort', 'date_desc')
    if sort_by == 'date_desc':
        articles_query = articles_query.order_by('-date')
    elif sort_by == 'date_asc':
        articles_query = articles_query.order_by('date')
    elif sort_by == 'title':
        articles_query = articles_query.order_by('title')
    else:
        articles_query = articles_query.order_by('-date')  # 默認排序

    # 準備分頁
    paginator = Paginator(articles_query, 12)  # 每頁顯示12篇文章
    page = request.GET.get('page')

    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        # 如果頁碼不是整數，返回第一頁
        articles = paginator.page(1)
    except EmptyPage:
        # 如果頁碼超出範圍，返回最後一頁
        articles = paginator.page(paginator.num_pages)

    # 構建查詢參數字符串，用於分頁連結
    search_params = request.GET.copy()
    if 'page' in search_params:
        search_params.pop('page')
    search_params_str = search_params.urlencode()

    context = {
        'job': job,
        'articles': articles,
        'articles_len': articles_query.count(),
        'available_categories': available_categories,
        'selected_categories': selected_categories,
        'search_keyword': search_keyword,
        'content_only': content_only,
        'sort_by': sort_by,
        'search_params': search_params_str
    }

    return render(request, 'scraper/job_articles.html', context)

@login_required
def article_detail(request, article_id):
    """文章詳情視圖"""
    article = get_object_or_404(Article, id=article_id, job__user=request.user)
    return render(request, 'scraper/article_detail.html', {'article': article})

@login_required
def job_delete(request, job_id):
    """刪除爬蟲任務"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 記錄任務 ID 用於消息提示
    job_id_display = job.id

    # 刪除任務
    job.delete()

    # 提示成功消息
    messages.success(request, f'爬蟲任務 #{job_id_display} 已成功刪除')

    # 重定向到任務列表
    return redirect('job_list')


##########################################
@login_required
def job_search_analysis(request, job_id):
    """進階搜尋與分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取所有可用類別
    available_categories = set(Article.objects.filter(job=job).values_list('category', flat=True))
    available_categories = sorted(list(available_categories))

    # 從 services.analysis_service 引入類別顏色映射
    category_colors = get_category_colors()

    # 初始化表單
    form = AdvancedSearchForm(request.GET or None)

    # 設置類別選項
    category_choices = [(cat, cat) for cat in available_categories]
    if hasattr(form.fields['categories'], 'choices'):
        form.fields['categories'].choices = category_choices

    # 初始化分析結果變量
    search_results = None
    time_series_data = None
    keywords_distribution = None
    entities_distribution = None
    cooccurrence_data = None
    top_image_url = None
    sentiment_distribution = None
    sentiment_time_data = None

    # 處理AJAX計算請求 - 只返回匹配數量而不執行完整搜索
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.POST.get('calculate_only') == 'true':
            try:
                # 使用表單數據進行查詢但不實際執行
                search_service = SearchAnalysisService(job)

                # 創建表單實例並手動設置數據
                temp_form = AdvancedSearchForm(request.POST)
                if temp_form.is_valid():
                    # 獲取匹配計數
                    query = search_service.build_search_query(temp_form.cleaned_data)
                    count = query.count()
                    return JsonResponse({'count': count, 'status': 'success'})
                else:
                    return JsonResponse({'count': 0, 'status': 'error', 'message': '表單驗證失敗'})
            except Exception as e:
                logger.error(f"計算匹配數量時出錯: {e}")
                return JsonResponse({'count': 0, 'status': 'error', 'message': str(e)})

    # 如果是搜尋請求且表單有效
    if request.GET and form.is_valid():
        try:
            # 實例化搜尋服務
            search_service = SearchAnalysisService(job)

            # 執行搜尋
            search_results = search_service.search(form.cleaned_data)

            if search_results and search_results.exists():
                # 生成時間軸數據
                time_series_data = search_service.generate_time_series(
                    search_results,
                    form.cleaned_data.get('time_grouping', 'day')
                )

                # 生成關鍵詞分布
                keywords_distribution = search_service.get_keywords_distribution(search_results)

                # 生成實體分布
                entities_distribution = search_service.get_entity_distribution(search_results)

                # 生成關鍵詞/實體共現數據
                cooccurrence_data = search_service.generate_cooccurrence_data(search_results)

                # 獲取頂部圖片
                top_image_url = search_service.get_top_article_image(search_results)

                # 獲取情緒分布數據
                sentiment_distribution = {
                    'positive_count': SentimentAnalysis.objects.filter(article__in=search_results,
                                                                       sentiment='正面').count(),
                    'negative_count': SentimentAnalysis.objects.filter(article__in=search_results,
                                                                       sentiment='負面').count(),
                    'neutral_count': SentimentAnalysis.objects.filter(article__in=search_results,
                                                                      sentiment='中立').count()
                }

                # 獲取情緒隨時間變化趨勢數據
                sentiment_time_data = {}

                # 按時間和情感分組獲取文章計數
                from django.db.models import Count
                from django.db.models.functions import TruncDate

                time_sentiment_stats = (
                    SentimentAnalysis.objects
                    .filter(article__in=search_results)
                    .annotate(date=TruncDate('article__date'))
                    .values('date', 'sentiment')
                    .annotate(count=Count('id'))
                    .order_by('date', 'sentiment')
                )

                # 將結果格式化為適合圖表的格式
                for stat in time_sentiment_stats:
                    date_str = stat['date'].isoformat()
                    if date_str not in sentiment_time_data:
                        sentiment_time_data[date_str] = {'positive': 0, 'negative': 0, 'neutral': 0}

                    sentiment_type = stat['sentiment']
                    count = stat['count']

                    if sentiment_type == '正面':
                        sentiment_time_data[date_str]['positive'] = count
                    elif sentiment_type == '負面':
                        sentiment_time_data[date_str]['negative'] = count
                    elif sentiment_type == '中立':
                        sentiment_time_data[date_str]['neutral'] = count
            else:
                # 沒有搜尋結果
                search_results = Article.objects.none()
                sentiment_distribution = None
                sentiment_time_data = None
        except Exception as e:
            logger.error(f"搜尋與分析過程中發生錯誤: {e}", exc_info=True)
            messages.error(request, f"搜尋分析過程出現錯誤: {str(e)}")
            search_results = Article.objects.none()
            sentiment_distribution = None
            sentiment_time_data = None

    # 獲取現有AI報告列表
    ai_reports = AIReport.objects.filter(job=job).order_by('-generated_at')[:5]

    # 將 Python 對象轉換為 JSON 字符串，用於在模板中傳遞給 JavaScript
    time_series_json = json.dumps(time_series_data) if time_series_data else None
    keywords_distribution_json = json.dumps(keywords_distribution) if keywords_distribution else None
    entities_distribution_json = json.dumps(entities_distribution) if entities_distribution else None
    cooccurrence_json = json.dumps(cooccurrence_data) if cooccurrence_data else None
    sentiment_distribution_json = json.dumps(sentiment_distribution) if sentiment_distribution else None
    sentiment_time_data_json = json.dumps(sentiment_time_data) if sentiment_time_data else None

    # 渲染模板
    context = {
        'job': job,
        'form': form,
        'results': search_results,
        'available_categories': available_categories,
        'category_colors': category_colors,
        'time_series_data': time_series_json,
        'time_series_count': len(time_series_data) if time_series_data else 0,
        'keywords_distribution': keywords_distribution_json,
        'entities_distribution': entities_distribution_json,
        'cooccurrence_data': cooccurrence_json,
        'top_image_url': top_image_url,
        'sentiment_distribution': sentiment_distribution_json,
        'sentiment_time_data': sentiment_time_data_json,
        'ai_reports': ai_reports,
        'has_search_results': search_results is not None and search_results.exists(),
        'ollama_settings': {
            'available': True,  # 您可以實現檢測Ollama服務是否可用的邏輯
            'model': settings.OLLAMA_SETTINGS.get('MODEL')
        }
    }

    return render(request, 'scraper/job_search_analysis.html', context)

# 添加這個新的視圖函數用於分析搜索詞
@login_required
def analyze_search_terms(request):
    """API視圖：分析搜索詞並返回斷詞、關鍵詞和命名實體"""
    if request.method != 'POST' or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': '僅支持AJAX POST請求'})

    try:
        # 解析JSON請求
        data = json.loads(request.body)
        search_terms = data.get('terms', '')
        # 獲取是否去重的參數，預設為 True
        remove_duplicates = data.get('remove_duplicates', True)

        if not search_terms:
            return JsonResponse({'status': 'error', 'message': '未提供搜索詞'})

        processor = CTTextProcessor(output_dir=settings.MEDIA_ROOT)

        # 進行斷詞
        segmented_terms = processor.segment_text(search_terms)

        # 提取斷詞結果
        if remove_duplicates:
            # 去重後的斷詞結果
            segmented_words = list(dict.fromkeys([word for word, _ in segmented_terms]))

            # 去重後的關鍵詞
            keywords_dict = {}
            for word, pos in segmented_terms:
                key = f"{word}_{pos}"
                if key not in keywords_dict:
                    keywords_dict[key] = {'word': word, 'pos': pos}
            keywords = list(keywords_dict.values())

            # 提取命名實體並去重
            entities = processor.identify_named_entities(search_terms)
            entities_dict = {}
            for entity in entities:
                key = f"{entity.word}_{entity.ner}"
                if key not in entities_dict:
                    entities_dict[key] = {'entity': entity.word, 'entity_type': entity.ner}
            entities_data = list(entities_dict.values())
        else:
            # 不去重的情況
            segmented_words = [word for word, _ in segmented_terms]
            keywords = [{'word': word, 'pos': pos} for word, pos in segmented_terms]
            entities = processor.identify_named_entities(search_terms)
            entities_data = [{'entity': entity.word, 'entity_type': entity.ner} for entity in entities]

        return JsonResponse({
            'status': 'success',
            'segmented_terms': segmented_words,
            'keywords': keywords,
            'entities': entities_data,
            'remove_duplicates': remove_duplicates  # 返回是否去重的設定
        })

    except Exception as e:
        logger.error(f"分析搜索詞時出錯: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def key_person_selection(request, job_id):
    """領導人選擇路由頁面"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 定義可選擇的領導人
    leaders = [
        {
            'id': 'trump',
            'name': '川普',
            'image': 'leader/trump.png',
            'title': '美國現任總統',
            'description': '第47任美國總統，共和黨人物。'
        },
        {
            'id': 'biden',
            'name': '拜登',
            'image': 'leader/biden.png',
            'title': '美國前任總統',
            'description': '第46任美國總統，民主黨人物。'
        },
        {
            'id': 'xi',
            'name': '習近平',
            'image': 'leader/xi.png',
            'title': '中國國家主席',
            'description': '中國共產黨總書記，中華人民共和國主席。'
        },
        {
            'id': 'tsai',
            'name': '蔡英文',
            'image': 'leader/tsai.png',
            'title': '台灣前任總統',
            'description': '中華民國第14、15任總統，民主進步黨前主席。'
        },
        {
            'id': 'lai',
            'name': '賴清德',
            'image': 'leader/lai.png',
            'title': '台灣現任總統',
            'description': '中華民國第16任總統，民主進步黨黨員。'
        }
    ]

    # 檢查是否為比較模式
    compare_mode = request.GET.get('compare', 'false') == 'true'

    # 獲取已選擇的領導人
    selected_leaders = request.GET.getlist('selected')

    # 檢查是否已經提交選擇
    if 'analyze' in request.GET and selected_leaders:
        if len(selected_leaders) == 1:
            # 單一領導人模式
            leader_name = selected_leaders[0]
            return redirect('analyze_key_person_with_name', job_id=job_id, person_name=leader_name)
        else:
            # 比較模式
            return redirect('compare_key_persons', job_id=job_id, person_names=','.join(selected_leaders))

    return render(request, 'scraper/key_person_selection.html', {
        'job': job,
        'leaders': leaders,
        'compare_mode': compare_mode,
        'selected_leaders': selected_leaders
    })


@login_required
def analyze_key_person(request, job_id, person_name=None):
    """
    關鍵人物分析視圖
    """
    try:
        if person_name is None:
            person_name = request.GET.get('name', '川普')  # 默認為川普，可通過參數修改

        # 如果沒有提供job_id，返回錯誤
        if not job_id:
            return JsonResponse({'status': 'error', 'message': '請提供任務ID'}, status=400)

        # 獲取任務
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 根據人名搜尋相關文章
        # 這裡可以加入內容過濾邏輯，例如在標題或內容中搜尋人名
        related_articles = Article.objects.filter(
            job=job,
            content__icontains=person_name  # 在內容中搜尋人名
        ).order_by('-date')

        # 計算總出現次數
        total_occurrences = related_articles.count()

        # 按類別統計出現次數
        category_stats = (
            related_articles.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 提取類別和計數資料用於圖表
        category_labels = []
        category_data = []

        for stat in category_stats:
            category_labels.append(stat['category'])
            category_data.append(stat['count'])

        # 確定主要出現類別
        main_category = category_labels[0] if category_labels else "無"

        # 按時間統計趨勢
        time_stats = defaultdict(int)

        for article in related_articles:
            date_str = article.date.strftime('%Y-%m-%d')
            time_stats[date_str] += 1

        # 排序時間數據
        time_labels = []
        time_data = []

        for date_str, count in sorted(time_stats.items()):
            time_labels.append(date_str)
            time_data.append(count)

        # 確定圖片檔名
        person_image = "leader/default_person.jpg"  # 預設圖片

        if person_name == "川普":
            person_image = "leader/trump.png"
        elif person_name == "蔡英文":
            person_image = "leader/tsai.png"
        elif person_name == "習近平":
            person_image = "leader/xi.png"
        elif person_name == "拜登":
            person_image = "leader/biden.png"
        elif person_name == "賴清德":
            person_image = "leader/lai.png"

        # 準備上下文資料
        context = {
            'job': job,
            'person_name': person_name,
            'person_image': person_image,
            'total_occurrences': total_occurrences,
            'main_category': main_category,
            'related_articles': related_articles,
            'category_colors': get_category_colors(),
            'category_labels': json.dumps(category_labels),
            'category_data': json.dumps(category_data),
            'time_labels': json.dumps(time_labels),
            'time_data': json.dumps(time_data)
        }

        return render(request, 'scraper/key_a_person.html', context)

    except Exception as e:
        logger.error(f"關鍵人物分析視圖出錯: {e}", exc_info=True)
        return HttpResponse(f"處理請求時發生錯誤: {str(e)}", status=500)


@login_required
def compare_key_persons(request, job_id, person_names):
    """比較多位關鍵人物視圖"""
    try:
        # 獲取任務
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 分割人名字符串
        persons = person_names.split(',')

        # 儲存每位人物的分析結果
        persons_data = []

        # 數據匯總
        all_category_labels = set()
        all_time_labels = set()
        combined_time_data = {}

        # 預設顏色
        colors = [
            'rgba(54, 162, 235, 0.7)',  # 藍色
            'rgba(255, 99, 132, 0.7)',  # 紅色
            'rgba(255, 206, 86, 0.7)',  # 黃色
            'rgba(75, 192, 192, 0.7)',  # 綠色
            'rgba(153, 102, 255, 0.7)'  # 紫色
        ]

        # 分析每位人物
        for i, person_name in enumerate(persons):
            # 根據人名搜尋相關文章
            related_articles = Article.objects.filter(
                job=job,
                content__icontains=person_name
            )

            # 計算文章提及數量
            article_count = related_articles.count()

            # 計算總出現次數 (匹配次數)
            # 這裡需要實際遍歷所有文章內容並計算人名出現次數
            total_mentions = 0
            for article in related_articles:
                # 計算內容中人名出現的次數
                content_mentions = article.content.lower().count(person_name.lower())
                total_mentions += content_mentions

            # 按類別統計出現次數
            category_stats = (
                related_articles.values('category')
                .annotate(count=Count('id'))
                .order_by('-count')
            )

            # 提取類別和計數資料
            category_data = {}
            for stat in category_stats:
                category = stat['category']
                count = stat['count']
                category_data[category] = count
                all_category_labels.add(category)

            # 按時間統計趨勢
            time_data = defaultdict(int)
            for article in related_articles:
                date_str = article.date.strftime('%Y-%m-%d')
                time_data[date_str] += 1
                all_time_labels.add(date_str)

                # 儲存到合併數據中
                if date_str not in combined_time_data:
                    combined_time_data[date_str] = {}
                combined_time_data[date_str][person_name] = time_data[date_str]

            # 情緒分析數據
            # 獲取正面、中立、負面文章
            positive_articles = related_articles.filter(sentiment__sentiment='正面')
            neutral_articles = related_articles.filter(sentiment__sentiment='中立')
            negative_articles = related_articles.filter(sentiment__sentiment='負面')

            # 獲取各情緒文章數量
            positive_count = positive_articles.count()
            neutral_count = neutral_articles.count()
            negative_count = negative_articles.count()
            analyzed_count = positive_count + neutral_count + negative_count

            # 計算情緒百分比
            if analyzed_count > 0:
                positive_percent = round((positive_count / analyzed_count) * 100)
                neutral_percent = round((neutral_count / analyzed_count) * 100)
                negative_percent = round((negative_count / analyzed_count) * 100)
            else:
                positive_percent = neutral_percent = negative_percent = 0

            # 按時間統計情緒趨勢
            positive_time_data = defaultdict(int)
            neutral_time_data = defaultdict(int)
            negative_time_data = defaultdict(int)

            # 正面情緒時間趨勢
            for article in positive_articles:
                date_str = article.date.strftime('%Y-%m-%d')
                positive_time_data[date_str] += 1
                all_time_labels.add(date_str)

            # 中立情緒時間趨勢
            for article in neutral_articles:
                date_str = article.date.strftime('%Y-%m-%d')
                neutral_time_data[date_str] += 1
                all_time_labels.add(date_str)

            # 負面情緒時間趨勢
            for article in negative_articles:
                date_str = article.date.strftime('%Y-%m-%d')
                negative_time_data[date_str] += 1
                all_time_labels.add(date_str)

            # 確定圖片檔名
            person_image = "leader/default_person.png"  # 預設圖片
            if person_name == "川普":
                person_image = "leader/trump.png"
            elif person_name == "蔡英文":
                person_image = "leader/tsai.png"
            elif person_name == "習近平":
                person_image = "leader/xi.png"
            elif person_name == "拜登":
                person_image = "leader/biden.png"
            elif person_name == "賴清德":
                person_image = "leader/lai.png"

            # 主要出現類別
            main_category = next(iter(category_stats))['category'] if category_stats else "無"

            # 添加人物數據
            persons_data.append({
                'name': person_name,
                'image': person_image,
                'article_count': article_count,  # 文章提及數量
                'total_mentions': total_mentions,  # 總出現次數
                'main_category': main_category,
                'category_data': category_data,
                'time_data': time_data,
                'color': colors[i % len(colors)],
                'sentiment_data': {
                    'positive_count': positive_count,
                    'neutral_count': neutral_count,
                    'negative_count': negative_count,
                    'positive_percent': positive_percent,
                    'neutral_percent': neutral_percent,
                    'negative_percent': negative_percent,
                    'positive_time_data': positive_time_data,
                    'neutral_time_data': neutral_time_data,
                    'negative_time_data': negative_time_data
                }
            })

        # 準備類別比較圖表數據
        all_category_labels = sorted(list(all_category_labels))
        category_datasets = []

        for person in persons_data:
            dataset = {
                'label': person['name'],
                'data': [person['category_data'].get(cat, 0) for cat in all_category_labels],
                'backgroundColor': person['color'],
                'borderColor': person['color'].replace('0.7', '1'),
                'borderWidth': 1
            }
            category_datasets.append(dataset)

        # 準備時間趨勢圖表數據
        all_time_labels = sorted(list(all_time_labels))
        time_datasets = []

        for person in persons_data:
            dataset = {
                'label': person['name'],
                'data': [person['time_data'].get(date, 0) for date in all_time_labels],
                'fill': False,
                'backgroundColor': person['color'],
                'borderColor': person['color'].replace('0.7', '1'),
                'tension': 0.4
            }
            time_datasets.append(dataset)

        # 準備情緒時間趨勢圖表數據
        positive_time_datasets = []
        neutral_time_datasets = []
        negative_time_datasets = []

        for person in persons_data:
            # 正面情緒時間趨勢
            positive_time_datasets.append({
                'label': person['name'],
                'data': [person['sentiment_data']['positive_time_data'].get(date, 0) for date in all_time_labels],
                'fill': False,
                'backgroundColor': person['color'],
                'borderColor': person['color'].replace('0.7', '1'),
                'tension': 0.4
            })

            # 中立情緒時間趨勢
            neutral_time_datasets.append({
                'label': person['name'],
                'data': [person['sentiment_data']['neutral_time_data'].get(date, 0) for date in all_time_labels],
                'fill': False,
                'backgroundColor': person['color'],
                'borderColor': person['color'].replace('0.7', '1'),
                'tension': 0.4
            })

            # 負面情緒時間趨勢
            negative_time_datasets.append({
                'label': person['name'],
                'data': [person['sentiment_data']['negative_time_data'].get(date, 0) for date in all_time_labels],
                'fill': False,
                'backgroundColor': person['color'],
                'borderColor': person['color'].replace('0.7', '1'),
                'tension': 0.4
            })

        # 準備上下文資料
        context = {
            'job': job,
            'persons': persons_data,
            'all_category_labels': json.dumps(all_category_labels),
            'category_datasets': json.dumps(category_datasets),
            'all_time_labels': json.dumps(all_time_labels),
            'time_datasets': json.dumps(time_datasets),
            'positive_time_datasets': json.dumps(positive_time_datasets),
            'neutral_time_datasets': json.dumps(neutral_time_datasets),
            'negative_time_datasets': json.dumps(negative_time_datasets)
        }

        return render(request, 'scraper/key_compare_persons.html', context)

    except Exception as e:
        logger.error(f"比較關鍵人物視圖出錯: {e}", exc_info=True)
        return HttpResponse(f"處理請求時發生錯誤: {str(e)}", status=500)

###########################################
@login_required
def job_sentiment_analysis(request, job_id):
    """情感分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 檢查是否需要執行情感分析
    analyze_now = request.GET.get('analyze', False)

    if analyze_now:
        # 啟動情感分析
        messages.info(request, '情感分析已啟動，這可能需要一些時間...')
        analyze_job_sentiment(job_id)
        return redirect('job_sentiment_analysis', job_id=job_id)

    # 獲取情感分析服務
    sentiment_service = SentimentAnalysisService()

    # 獲取情感分析統計
    total_articles = Article.objects.filter(job=job).count()
    analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()

    # 獲取未分析的文章
    unanalyzed_articles = None
    if total_articles > analyzed_articles:
        unanalyzed_articles = sentiment_service.get_unanalyzed_articles(job_id, limit=50)

    # 獲取類別情感摘要
    category_summary = sentiment_service.get_category_sentiment_summary(job_id)

    # 獲取整體情感分布
    sentiment_distribution = sentiment_service.get_sentiment_distribution(job_id)

    # 獲取情感極性最強的文章 (正面和負面各5篇)
    top_positive_articles = SentimentAnalysis.objects.filter(
        job=job,
        sentiment='正面'
    ).order_by('-positive_score')[:5]

    top_negative_articles = SentimentAnalysis.objects.filter(
        job=job,
        sentiment='負面'
    ).order_by('-negative_score')[:5]

    # 檢查是否所有文章都已分析
    all_analyzed = total_articles == analyzed_articles and total_articles > 0
    analysis_progress = int((analyzed_articles / total_articles * 100) if total_articles > 0 else 0)

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'category_summary': category_summary,
        'sentiment_distribution': sentiment_distribution,
        'top_positive_articles': top_positive_articles,
        'top_negative_articles': top_negative_articles,
        'total_articles': total_articles,
        'analyzed_articles': analyzed_articles,
        'all_analyzed': all_analyzed,
        'analysis_progress': analysis_progress,
        'unanalyzed_articles': unanalyzed_articles,
    }

    return render(request, 'scraper/job_sentiment_analysis.html', context)



@login_required
def analyze_article_sentiment(request, article_id):
    """分析單篇文章情感"""
    article = get_object_or_404(Article, id=article_id, job__user=request.user)

    # 檢查是否已分析
    try:
        sentiment = SentimentAnalysis.objects.get(article=article)
        # 文章已分析，返回結果
        return JsonResponse({
            'status': 'success',
            'already_analyzed': True,
            'result': {
                'positive_score': sentiment.positive_score,
                'negative_score': sentiment.negative_score,
                'sentiment': sentiment.sentiment,
                'title_sentiment': sentiment.title_sentiment,
                'title_positive_score': sentiment.title_positive_score,
                'title_negative_score': sentiment.title_negative_score
            }
        })
    except SentimentAnalysis.DoesNotExist:
        # 文章未分析，執行分析
        sentiment_service = SentimentAnalysisService()
        result = sentiment_service.analyze_article(article)

        if result:
            # 保存分析結果
            sentiment = SentimentAnalysis.objects.create(
                article=article,
                job=article.job,
                positive_score=result['content']['positive'],
                negative_score=result['content']['negative'],
                sentiment=result['content']['sentiment'],
                title_sentiment=result['title']['sentiment'],
                title_positive_score=result['title']['positive'],
                title_negative_score=result['title']['negative']
            )

            return JsonResponse({
                'status': 'success',
                'already_analyzed': False,
                'result': {
                    'positive_score': sentiment.positive_score,
                    'negative_score': sentiment.negative_score,
                    'sentiment': sentiment.sentiment,
                    'title_sentiment': sentiment.title_sentiment,
                    'title_positive_score': sentiment.title_positive_score,
                    'title_negative_score': sentiment.title_negative_score
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '分析失敗'
            })


@login_required
def start_sentiment_analysis(request, job_id):
    """啟動情感分析任務"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '僅支持POST請求'})

    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 檢查任務是否已完成
    if job.status != 'completed':
        return JsonResponse({
            'status': 'error',
            'message': '只能分析已完成的爬蟲任務'
        })

    # 獲取情感分析統計
    total_articles = Article.objects.filter(job=job).count()
    analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()

    # 啟動情感分析
    import threading
    thread = threading.Thread(target=analyze_job_sentiment, args=(job_id,))
    thread.daemon = True
    thread.start()

    return JsonResponse({
        'status': 'success',
        'message': '情感分析任務已啟動',
        'total_articles': total_articles,
        'analyzed_articles': analyzed_articles,
        'remaining': total_articles - analyzed_articles
    })


@login_required
def regenerate_sentiment_summary(request, job_id):
    """重新生成情感分析摘要"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '只接受POST請求'})

    try:
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 檢查是否有足夠的情感分析數據
        articles_count = Article.objects.filter(job=job).count()
        analyzed_count = SentimentAnalysis.objects.filter(job=job).count()

        if analyzed_count == 0:
            return JsonResponse({
                'status': 'error',
                'message': '尚未進行情感分析，無法生成摘要'
            })

        # 建立情感分析服務
        sentiment_service = SentimentAnalysisService()

        # 使用新的regenerate_sentiment_summary方法徹底重建摘要
        success = sentiment_service.regenerate_sentiment_summary(job)

        if success:
            # 返回成功訊息
            return JsonResponse({
                'status': 'success',
                'message': '情感分析摘要已重新生成',
                'analyzed_count': analyzed_count,
                'total_count': articles_count
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '摘要生成失敗，請查看日誌'
            })

    except Exception as e:
        logger.error(f"重新生成情感摘要時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })


@login_required
def get_sentiment_stats(request, job_id):
    """獲取情感分析統計數據"""
    try:
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 建立情感分析服務
        sentiment_service = SentimentAnalysisService()

        # 獲取情感分析統計
        total_articles = Article.objects.filter(job=job).count()
        analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()
        analysis_progress = int((analyzed_articles / total_articles * 100) if total_articles > 0 else 0)

        # 獲取整體情感分布
        sentiment_distribution = sentiment_service.get_sentiment_distribution(job_id)

        # 獲取類別情感摘要
        category_summary = sentiment_service.get_category_sentiment_summary(job_id)

        return JsonResponse({
            'status': 'success',
            'total_articles': total_articles,
            'analyzed_articles': analyzed_articles,
            'analysis_progress': analysis_progress,
            'sentiment_distribution': sentiment_distribution if sentiment_distribution else {},
            'category_summary': category_summary
        })

    except Exception as e:
        logger.error(f"獲取情感分析統計時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })

@login_required
def analyze_single_article(request, job_id, article_id):
    """手動分析單篇文章情感"""
    try:
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
        article = get_object_or_404(Article, id=article_id, job=job)

        # 檢查是否已分析
        existing_analysis = SentimentAnalysis.objects.filter(article=article).first()

        if existing_analysis:
            return JsonResponse({
                'status': 'success',
                'message': '該文章已分析過',
                'already_analyzed': True
            })

        # 執行分析
        sentiment_service = SentimentAnalysisService()
        result = sentiment_service.analyze_article(article)

        if result:
            # 保存分析結果
            SentimentAnalysis.objects.create(
                article=article,
                job=job,
                positive_score=result['content']['positive'],
                negative_score=result['content']['negative'],
                sentiment=result['content']['sentiment'],
                title_sentiment=result['title']['sentiment'],
                title_positive_score=result['title']['positive'],
                title_negative_score=result['title']['negative']
            )

            # 獲取更新後的統計
            total_articles = Article.objects.filter(job=job).count()
            analyzed_articles = SentimentAnalysis.objects.filter(job=job).count()

            return JsonResponse({
                'status': 'success',
                'message': '文章分析成功',
                'already_analyzed': False,
                'total_articles': total_articles,
                'analyzed_articles': analyzed_articles,
                'analysis_progress': int((analyzed_articles / total_articles * 100) if total_articles > 0 else 0)
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '文章分析失敗'
            })

    except Exception as e:
        logger.error(f"手動分析文章時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })



@login_required
def ai_report_view(request, job_id):
    """AI報告頁面視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務的所有報告，按時間倒序排序
    reports = AIReport.objects.filter(job=job).order_by('-generated_at')

    context = {
        'job': job,
        'reports': reports,
        'report_count': reports.count(),
        'ollama_settings': {
            'model': settings.OLLAMA_SETTINGS.get('MODEL'),
            'max_tokens': settings.OLLAMA_SETTINGS.get('MAX_TOKENS')
        }
    }

    return render(request, 'scraper/ai_report_list.html', context)


@login_required
def ai_report_detail(request, job_id, report_id):
    """AI報告詳情頁面視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    report = get_object_or_404(AIReport, id=report_id, job=job)

    # 獲取報告內容並進行Markdown渲染
    import markdown

    # 如果報告已完成並有內容，則渲染為HTML
    rendered_content = ''
    if report.status == 'completed' and report.content:
        # 使用Python-Markdown進行渲染
        rendered_content = markdown.markdown(
            report.content,
            extensions=['tables', 'fenced_code', 'nl2br', 'toc']
        )

    context = {
        'job': job,
        'report': report,
        'rendered_content': rendered_content,
        'is_completed': report.status == 'completed'
    }

    return render(request, 'scraper/ai_report_detail.html', context)


@login_required
def ai_report_download(request, job_id, report_id):
    """下載AI報告文件"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    report = get_object_or_404(AIReport, id=report_id, job=job)

    # 只允許下載已完成的報告
    if report.status != 'completed':
        messages.error(request, '報告尚未生成完成，無法下載')
        return redirect('ai_report_detail', job_id=job_id, report_id=report_id)

    # 獲取報告內容
    content = report.content

    # 設置下載文件名
    filename = f"AI_Report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"

    # 創建HTTP響應
    response = HttpResponse(content, content_type='text/markdown')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@login_required
def regenerate_ai_report(request, job_id, report_id):
    """重新生成AI報告"""
    if request.method != 'POST':
        return redirect('ai_report_detail', job_id=job_id, report_id=report_id)

    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    report = get_object_or_404(AIReport, id=report_id, job=job)

    # 檢查報告是否可以重新生成（非處理中狀態）
    if report.status == 'pending' or report.status == 'running':
        messages.error(request, '報告正在生成中，無法重新生成')
        return redirect('ai_report_detail', job_id=job_id, report_id=report_id)

    # 重置報告狀態
    report.status = 'pending'
    report.error_message = None
    report.save()

    # 獲取原始搜索參數
    search_params = report.search_params or {}

    # 執行搜索獲取最新結果
    search_service = SearchAnalysisService(job)
    search_results = search_service.search(search_params)

    # 啟動非同步任務重新生成報告
    from .services.ai_service import generate_report_async
    generate_report_async(report.id, search_params, search_results)

    messages.success(request, '報告重新生成請求已提交，請稍後查看')
    return redirect('ai_report_detail', job_id=job_id, report_id=report_id)


@login_required
def delete_ai_report(request, job_id, report_id):
    """刪除 AI 報告"""
    if request.method != 'POST':
        return redirect('ai_report_view', job_id=job_id)

    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    report = get_object_or_404(AIReport, id=report_id, job=job)

    try:
        # 如果有報告文件，則刪除文件
        report_file_path = report.get_file_path()
        if os.path.exists(report_file_path):
            os.remove(report_file_path)

        # 刪除資料庫記錄
        report.delete()

        messages.success(request, f'報告 #{report_id} 已成功刪除')
    except Exception as e:
        logger.error(f"刪除報告時出錯: {e}")
        messages.error(request, f'刪除報告失敗: {str(e)}')

    return redirect('ai_report_view', job_id=job_id)


@login_required
def job_summary_analysis(request, job_id):
    """摘要分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 檢查是否需要執行摘要分析
    analyze_now = request.GET.get('analyze', False)

    if analyze_now:
        # 啟動摘要分析
        messages.info(request, '摘要分析已啟動，這可能需要一些時間...')
        analyze_job_summaries_async(job_id)
        return redirect('job_summary_analysis', job_id=job_id)

    # 獲取摘要分析服務
    summary_service = SummaryAnalysisService()

    # 獲取摘要分析統計
    stats = summary_service.get_summary_statistics(job_id)

    # 獲取未分析的文章
    unanalyzed_articles = None
    if stats['pending_summaries'] > 0:
        unanalyzed_articles = summary_service.get_unanalyzed_articles(job_id, limit=50)

    # 獲取最近生成的摘要（正面示例）
    recent_summaries = ArticleSummary.objects.filter(
        job=job,
        status='completed'
    ).select_related('article').order_by('-generated_at')[:10]

    # 獲取失敗的摘要
    failed_summaries = ArticleSummary.objects.filter(
        job=job,
        status='failed'
    ).select_related('article').order_by('-updated_at')[:5]

    # 檢查是否所有文章都已分析
    all_analyzed = stats['pending_summaries'] == 0 and stats['total_articles'] > 0

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'stats': stats,
        'recent_summaries': recent_summaries,
        'failed_summaries': failed_summaries,
        'all_analyzed': all_analyzed,
        'unanalyzed_articles': unanalyzed_articles,
    }

    return render(request, 'scraper/job_summary_analysis.html', context)


@login_required
def start_summary_analysis(request, job_id):
    """啟動摘要分析任務"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '僅支持POST請求'})

    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 檢查任務是否已完成
    if job.status != 'completed':
        return JsonResponse({
            'status': 'error',
            'message': '只能分析已完成的爬蟲任務'
        })

    # 獲取摘要分析統計
    service = SummaryAnalysisService()
    stats = service.get_summary_statistics(job_id)

    # 檢查是否有正在進行的分析
    pending_summaries = ArticleSummary.objects.filter(
        job=job,
        status__in=['pending', 'running']
    ).count()

    if pending_summaries > 0:
        return JsonResponse({
            'status': 'error',
            'message': '摘要分析任務已在進行中，請稍後再試'
        })

    # 啟動摘要分析
    thread = analyze_job_summaries_async(job_id)

    return JsonResponse({
        'status': 'success',
        'message': '摘要分析任務已啟動',
        'total_articles': stats['total_articles'],
        'analyzed_summaries': stats['analyzed_summaries'],
        'remaining': stats['pending_summaries']
    })


@login_required
def generate_article_summary(request, article_id):
    """生成單篇文章摘要"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '只接受POST請求'})

    try:
        article = get_object_or_404(Article, id=article_id, job__user=request.user)

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
                'summary_text': existing_summary.summary_text,
                'generated_at': existing_summary.generated_at.isoformat()
            })

        # 生成摘要
        service = SummaryAnalysisService()
        success = service.regenerate_summary(article_id)

        if success:
            # 獲取新生成的摘要
            summary = ArticleSummary.objects.get(article=article)
            return JsonResponse({
                'status': 'success',
                'message': '摘要生成成功',
                'already_exists': False,
                'summary_text': summary.summary_text,
                'generated_at': summary.generated_at.isoformat(),
                'generation_time': summary.generation_time
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '摘要生成失敗'
            })

    except Exception as e:
        logger.error(f"生成文章摘要時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })


@login_required
def get_summary_stats(request, job_id):
    """獲取摘要分析統計數據"""
    try:
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 建立摘要分析服務
        summary_service = SummaryAnalysisService()

        # 獲取統計數據
        stats = summary_service.get_summary_statistics(job_id)

        return JsonResponse({
            'status': 'success',
            **stats
        })

    except Exception as e:
        logger.error(f"獲取摘要分析統計時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })


@login_required
def regenerate_article_summary(request, article_id):
    """重新生成文章摘要"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': '只接受POST請求'})

    try:
        article = get_object_or_404(Article, id=article_id, job__user=request.user)

        # 執行重新生成
        service = SummaryAnalysisService()
        success = service.regenerate_summary(article_id)

        if success:
            # 獲取更新後的摘要
            summary = ArticleSummary.objects.get(article=article)

            return JsonResponse({
                'status': 'success',
                'message': '摘要重新生成成功',
                'summary_text': summary.summary_text,
                'generated_at': summary.generated_at.isoformat(),
                'generation_time': summary.generation_time
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': '摘要重新生成失敗'
            })

    except Exception as e:
        logger.error(f"重新生成摘要時出錯: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'處理請求時發生錯誤: {str(e)}'
        })


# 修改現有的 job_articles 視圖以包含摘要信息
# 注意：這是對現有函數的建議修改，需要在原有的 job_articles 函數中加入摘要查詢

def job_articles_with_summaries(request, job_id):
    """文章列表視圖（包含摘要信息）- 這是對現有 job_articles 的增強版本"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務的所有文章，並預載入摘要信息
    articles_query = Article.objects.filter(job=job).select_related('summary')

    # 從任務中獲取實際存在的類別
    available_categories = {}
    categories_used = articles_query.values_list('category', flat=True).distinct()

    # 建立類別與顏色的對應關係
    category_colors = get_category_colors()
    for category in categories_used:
        if category in category_colors:
            available_categories[category] = category_colors[category]

    # 處理搜尋關鍵字
    search_keyword = request.GET.get('keyword', '')
    content_only = 'content_only' in request.GET

    if search_keyword:
        if content_only:
            # 僅搜尋內容
            articles_query = articles_query.filter(content__icontains=search_keyword)
        else:
            # 搜尋標題、內容和作者
            articles_query = articles_query.filter(
                models.Q(title__icontains=search_keyword) |
                models.Q(content__icontains=search_keyword) |
                models.Q(author__icontains=search_keyword)
            )

    # 處理類別篩選
    selected_categories = request.GET.getlist('categories', [])
    if selected_categories:
        articles_query = articles_query.filter(category__in=selected_categories)

    # 處理排序
    sort_by = request.GET.get('sort', 'date_desc')
    if sort_by == 'date_desc':
        articles_query = articles_query.order_by('-date')
    elif sort_by == 'date_asc':
        articles_query = articles_query.order_by('date')
    elif sort_by == 'title':
        articles_query = articles_query.order_by('title')
    else:
        articles_query = articles_query.order_by('-date')  # 默認排序

    # 準備分頁
    paginator = Paginator(articles_query, 12)  # 每頁顯示12篇文章
    page = request.GET.get('page')

    try:
        articles = paginator.page(page)
    except PageNotAnInteger:
        articles = paginator.page(1)
    except EmptyPage:
        articles = paginator.page(paginator.num_pages)

    # 獲取摘要統計
    summary_service = SummaryAnalysisService()
    summary_stats = summary_service.get_summary_statistics(job_id)

    # 構建查詢參數字符串，用於分頁連結
    search_params = request.GET.copy()
    if 'page' in search_params:
        search_params.pop('page')
    search_params_str = search_params.urlencode()

    context = {
        'job': job,
        'articles': articles,
        'articles_len': articles_query.count(),
        'available_categories': available_categories,
        'selected_categories': selected_categories,
        'search_keyword': search_keyword,
        'content_only': content_only,
        'sort_by': sort_by,
        'search_params': search_params_str,
        'summary_stats': summary_stats,  # 新增摘要統計信息
    }

    return render(request, 'scraper/job_articles.html', context)
