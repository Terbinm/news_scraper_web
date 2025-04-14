import json
import logging

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models

from news_scraper_web import settings
from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis
from .forms import LoginForm, ScrapeJobForm, KeywordFilterForm, AdvancedSearchForm
from .services.search_service import SearchAnalysisService
from .services.task_service import execute_scraper_task
from .services.analysis_service import (
    get_keywords_analysis,
    get_entities_analysis,
    get_category_colors
)
from scraper.utils.scraper_utils import CTTextProcessor
logger = logging.getLogger(__name__)

from collections import defaultdict
from django.db.models import Q, Count



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
            else:
                # 沒有搜尋結果
                search_results = Article.objects.none()
        except Exception as e:
            logger.error(f"搜尋與分析過程中發生錯誤: {e}", exc_info=True)
            messages.error(request, f"搜尋分析過程出現錯誤: {str(e)}")
            search_results = Article.objects.none()

    # 將 Python 對象轉換為 JSON 字符串，用於在模板中傳遞給 JavaScript
    # 關鍵修改：確保使用 json.dumps() 轉換為 JSON 字符串
    time_series_json = json.dumps(time_series_data) if time_series_data else None
    keywords_distribution_json = json.dumps(keywords_distribution) if keywords_distribution else None
    entities_distribution_json = json.dumps(entities_distribution) if entities_distribution else None
    cooccurrence_json = json.dumps(cooccurrence_data) if cooccurrence_data else None

    # 渲染模板
    return render(request, 'scraper/job_search_analysis.html', {
        'job': job,
        'form': form,
        'results': search_results,
        'available_categories': available_categories,
        'category_colors': category_colors,
        'time_series_data': time_series_json,  # 將 JSON 字符串傳遞給模板
        'time_series_count': len(time_series_data) if time_series_data else 0,
        'keywords_distribution': keywords_distribution_json,
        'entities_distribution': entities_distribution_json,
        'cooccurrence_data': cooccurrence_json,
        'top_image_url': top_image_url
    })

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
def analyze_key_person(request, job_id):
    """
    關鍵人物分析視圖
    """
    try:
        person_name = request.GET.get('name', '川普')  # 默認為川普，可通過參數修改

        # 如果沒有提供job_id，返回錯誤
        if not job_id:
            return JsonResponse({'status': 'error', 'message': '請提供任務ID'}, status=400)

        # 獲取任務
        job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

        # 根據人名搜尋相關文章
        related_articles = Article.objects.filter(
            job=job
        ).order_by('-date')  # 修正這裡的 order_by

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
        person_image = "trump.png"  # 預設圖片
        if person_name == "川普":
            person_image = "trump.png"
        elif person_name == "蔡英文":
            person_image = "tsai.png"
        elif person_name == "習近平":
            person_image = "xi.png"
        # 其他人物可以在這裡擴充...

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

        return render(request, 'scraper/job_key_person.html', context)

    except Exception as e:
        logger.error(f"關鍵人物分析視圖出錯: {e}", exc_info=True)
        return HttpResponse(f"處理請求時發生錯誤: {str(e)}", status=500)
