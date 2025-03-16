import matplotlib
matplotlib.use('Agg')  # 使用非交互式後端，避免tkinter錯誤

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl
from matplotlib.font_manager import FontProperties


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings

import json
import os
import threading

import pandas as pd
from .models import ScrapeJob, Article, KeywordAnalysis
from .forms import LoginForm, ScrapeJobForm, KeywordFilterForm
from .services import run_scraper
import platform
import os



# 設置中文字體
def set_matplotlib_chinese_font():
    # 直接使用字體文件路徑
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'MantouSans-Regular.ttf')

    # 確認字體文件存在
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"找不到字體文件: {font_path}")

    # 不要設置font.family和font.sans-serif
    # 直接返回字體屬性對象給每個需要顯示中文的地方使用
    return FontProperties(fname=font_path)


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

def get_category_colors():
    """生成類別顏色映射"""
    category_colors = {
        '財經': {'bg': 'rgba(54, 162, 235, 0.7)', 'border': 'rgba(54, 162, 235, 1)'},
        '政治': {'bg': 'rgba(255, 99, 132, 0.7)', 'border': 'rgba(255, 99, 132, 1)'},
        '社會': {'bg': 'rgba(255, 159, 64, 0.7)', 'border': 'rgba(255, 159, 64, 1)'},
        '科技': {'bg': 'rgba(75, 192, 192, 0.7)', 'border': 'rgba(75, 192, 192, 1)'},
        '國際': {'bg': 'rgba(153, 102, 255, 0.7)', 'border': 'rgba(153, 102, 255, 1)'},
        '娛樂': {'bg': 'rgba(255, 205, 86, 0.7)', 'border': 'rgba(255, 205, 86, 1)'},
        '生活': {'bg': 'rgba(201, 203, 207, 0.7)', 'border': 'rgba(201, 203, 207, 1)'},
        '言論': {'bg': 'rgba(0, 204, 150, 0.7)', 'border': 'rgba(0, 204, 150, 1)'},
        '軍事': {'bg': 'rgba(255, 0, 110, 0.7)', 'border': 'rgba(255, 0, 110, 1)'}
    }
    return category_colors

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

            # 使用任務函數啟動爬蟲
            from .tasks import run_scraper_task
            run_scraper_task(job.id)

            messages.success(request, '爬蟲任務已創建並開始執行')
            return redirect('job_list')
    else:
        form = ScrapeJobForm()

    return render(request, 'scraper/job_create.html', {'form': form})


@login_required
def job_detail(request, job_id):
    """爬蟲任務詳情"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    articles = Article.objects.filter(job=job)

    # 獲取該任務下所有存在的類別
    available_categories = KeywordAnalysis.objects.filter(job=job).values_list('category', flat=True).distinct()

    # 處理關鍵詞篩選
    form = KeywordFilterForm(request.GET)
    filter_args = {'job': job}

    # 設置初始表單數據，特別是多選類別
    if not request.GET:
        form = KeywordFilterForm(initial={'selected_categories': list(available_categories)})

    if form.is_valid():
        if form.cleaned_data.get('pos'):
            filter_args['pos'] = form.cleaned_data['pos']
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

        # 處理類別選擇 - 無論是否為跨類別模式都使用多選
        cross_category = form.cleaned_data.get('cross_category', False)
        selected_categories = form.cleaned_data.get('selected_categories', [])

        # 確保有選中的類別
        if not selected_categories:
            selected_categories = list(available_categories)

        # 添加類別條件 - 不論是否為跨類別模式，都使用 category__in
        filter_args['category__in'] = selected_categories

        # 如果啟用跨類別統計
        if cross_category:
            from django.db.models import Sum, F, Count, Q
            from collections import defaultdict

            # 限制關鍵詞數量
            limit = form.cleaned_data.get('limit', 20)

            # 先獲取分組統計的總頻率
            aggregated_keywords = (KeywordAnalysis.objects
                                   .filter(**filter_args)
                                   .values('word', 'pos')
                                   .annotate(total_frequency=Sum('frequency'))
                                   .order_by('-total_frequency')[:limit])

            # 獲取包含在結果中的詞列表
            words_in_result = [kw['word'] for kw in aggregated_keywords]

            # 對於每個聚合的關鍵詞，獲取其在各個類別中的詳細分布
            category_details = {}
            if words_in_result:
                detail_data = (KeywordAnalysis.objects
                               .filter(**filter_args, word__in=words_in_result)
                               .values('word', 'category', 'frequency')
                               .order_by('-frequency'))

                # 將詳細信息整理成詞典形式
                for item in detail_data:
                    word = item['word']
                    if word not in category_details:
                        category_details[word] = {}
                    category_details[word][item['category']] = item['frequency']

            # 創建可用於模板的自定義關鍵詞列表，包含類別分布信息
            from collections import namedtuple

            # 擴展 KeywordResult 以包含更多類別信息
            KeywordResult = namedtuple('KeywordResult', [
                'word', 'pos', 'frequency', 'category', 'category_details',
                'category_list', 'top_category'
            ])

            keyword_list = []
            for kw in aggregated_keywords:
                details = category_details.get(kw['word'], {})
                # 格式化類別詳情為可讀字符串
                details_str = ", ".join([f"{cat}: {freq}" for cat, freq in details.items()])

                # 獲取出現頻率最高的類別
                top_category = ""
                max_freq = 0
                for cat, freq in details.items():
                    if freq > max_freq:
                        max_freq = freq
                        top_category = cat

                # 所有出現的類別列表（按頻率排序）
                category_list = sorted(details.items(), key=lambda x: x[1], reverse=True)
                category_list = [cat for cat, _ in category_list]

                keyword_list.append(KeywordResult(
                    word=kw['word'],
                    pos=kw['pos'],
                    frequency=kw['total_frequency'],
                    category="跨類別統計",
                    category_details=details_str,
                    category_list=category_list,
                    top_category=top_category
                ))

            keywords = keyword_list
        else:
            # 不啟用跨類別統計但仍使用多類別查詢
            # 限制關鍵詞數量
            limit = form.cleaned_data.get('limit', 20)

            # 這裡不合併不同類別的相同關鍵詞，而是分別顯示
            keywords = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
    else:
        # 如果表單無效，使用默認查詢 - 所有類別
        filter_args['category__in'] = available_categories
        limit = 20
        keywords = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]

    context = {
        'job': job,
        'articles': articles,
        'articles_len': len(articles),
        'keywords': keywords,
        'form': form,
        'available_categories': available_categories,
        'is_cross_category': form.is_valid() and form.cleaned_data.get('cross_category', False),
        'category_colors': get_category_colors()  # 生成類別顏色映射
    }

    return render(request, 'scraper/job_detail.html', context)


@login_required
def generate_chart(request, job_id):
    """生成關鍵詞頻率圖表"""
    # 初始化圖表前關閉先前圖表
    plt.close('all')

    # 獲取字體屬性
    font_prop = set_matplotlib_chinese_font()

    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 處理篩選條件
    form = KeywordFilterForm(request.GET)
    filter_args = {'job': job}

    # 添加跨類別統計參數
    cross_category = False
    selected_categories = []

    if form.is_valid():
        if form.cleaned_data.get('category'):
            filter_args['category'] = form.cleaned_data['category']
        if form.cleaned_data.get('pos'):
            filter_args['pos'] = form.cleaned_data['pos']
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

        # 獲取跨類別統計選項
        cross_category = form.cleaned_data.get('cross_category', False)
        selected_categories = form.cleaned_data.get('selected_categories', [])

    # 獲取並限制關鍵詞數量
    limit = form.cleaned_data.get('limit', 20) if form.is_valid() else 20

    # 準備圖表數據
    if cross_category:
        from django.db.models import Sum

        # 準備基本的查詢條件
        base_filters = {'job': job}
        if form.is_valid():
            if form.cleaned_data.get('pos'):
                base_filters['pos'] = form.cleaned_data['pos']
            if form.cleaned_data.get('min_frequency'):
                base_filters['frequency__gte'] = form.cleaned_data['min_frequency']

        # 如果選擇了特定類別，則只統計這些類別
        if selected_categories:
            base_filters['category__in'] = selected_categories
            categories_label = "、".join(selected_categories)
        else:
            categories_label = "所有類別"

        # 分組統計
        keywords = (KeywordAnalysis.objects
                    .filter(**base_filters)
                    .values('word', 'pos')
                    .annotate(frequency=Sum('frequency'))
                    .order_by('-frequency')[:limit])

        words = [k['word'] for k in keywords]
        frequencies = [k['frequency'] for k in keywords]
        chart_title = f'跨類別關鍵詞頻率分布 ({categories_label})'
    else:
        keywords = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
        words = [k.word for k in keywords]
        frequencies = [k.frequency for k in keywords]

        # 設置圖表標題
        if 'category' in filter_args:
            chart_title = f"{filter_args['category']}類別關鍵詞頻率分布"
        else:
            chart_title = '所有類別關鍵詞頻率分布'

    # 使用 matplotlib 生成圖表
    fig, ax = plt.subplots(figsize=(10, 6))

    # 先設置刻度位置，再設置標籤
    y_pos = range(len(words))
    ax.barh(y_pos, frequencies)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(words, fontproperties=font_prop)

    # 設置標籤
    ax.set_xlabel('頻率', fontproperties=font_prop)
    ax.set_ylabel('關鍵詞', fontproperties=font_prop)
    ax.set_title(chart_title, fontproperties=font_prop)

    plt.tight_layout()

    # 保存圖表到靜態文件
    chart_path = f'static/charts/job_{job_id}_keywords.png'
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    plt.savefig(chart_path, dpi=100, bbox_inches='tight')
    plt.close()  # 確保關閉圖表

    # 準備Chart.js數據
    chart_data = {
        'labels': words,
        'datasets': [{
            'label': '頻率',
            'data': frequencies,
            'backgroundColor': 'rgba(54, 162, 235, 0.6)',
            'borderColor': 'rgba(54, 162, 235, 1)',
            'borderWidth': 1
        }]
    }

    return JsonResponse({
        'chart_data': chart_data,
        'chart_image': '/' + chart_path
    })


@login_required
def article_list(request, job_id):
    """文章列表視圖"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)
    articles = Article.objects.filter(job=job)
    return render(request, 'scraper/article_list.html', {'job': job, 'articles': articles})


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