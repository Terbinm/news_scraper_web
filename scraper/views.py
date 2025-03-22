import logging

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.db import models

from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis
from .forms import LoginForm, ScrapeJobForm, KeywordFilterForm
from .services.task_service import execute_scraper_task
from .services.analysis_service import (
    get_keywords_analysis,
    get_entities_analysis,
    get_category_colors
)

logger = logging.getLogger(__name__)


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
    recent_articles = Article.objects.filter(job=job).order_by('-date')[:5]

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

    # 獲取該任務下所有存在的類別
    available_categories = KeywordAnalysis.objects.filter(job=job).values_list('category', flat=True).distinct()

    # 處理篩選表單
    form = KeywordFilterForm(request.GET)

    # 設置初始表單數據
    if not request.GET:
        form = KeywordFilterForm(initial={
            'selected_categories': list(available_categories),
            'analysis_type': 'keywords'
        })

    # 根據請求參數獲取關鍵詞分析結果
    result = get_keywords_analysis(job, form, available_categories)

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'keywords': result['keywords'],
        'form': form,
        'available_categories': available_categories,
        'is_cross_category': result['is_cross_category'],
        'category_colors': get_category_colors(),
    }

    return render(request, 'scraper/job_keywords.html', context)


@login_required
def job_entities_analysis(request, job_id):
    """命名實體分析視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 獲取該任務下所有存在的類別
    available_categories = NamedEntityAnalysis.objects.filter(job=job).values_list('category', flat=True).distinct()

    # 處理篩選表單
    form = KeywordFilterForm(request.GET)

    # 設置初始表單數據
    if not request.GET:
        form = KeywordFilterForm(initial={
            'selected_categories': list(available_categories),
            'analysis_type': 'entities'
        })

    # 根據請求參數獲取命名實體分析結果
    result = get_entities_analysis(job, form, available_categories)

    # 將分析結果添加到上下文
    context = {
        'job': job,
        'entities': result['entities'],
        'form': form,
        'available_categories': available_categories,
        'is_cross_category': result['is_cross_category'],
        'category_colors': get_category_colors(),
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