from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse
import json
import os
import threading
import matplotlib.pyplot as plt
import pandas as pd
from .models import ScrapeJob, Article, KeywordAnalysis
from .forms import LoginForm, ScrapeJobForm, KeywordFilterForm
from .services import run_scraper


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

            # 開啟執行緒執行爬蟲任務
            thread = threading.Thread(target=run_scraper, args=(job.id,))
            thread.daemon = True
            thread.start()

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

    # 處理關鍵詞篩選
    form = KeywordFilterForm(request.GET)
    filter_args = {'job': job}

    if form.is_valid():
        if form.cleaned_data.get('category'):
            filter_args['category'] = form.cleaned_data['category']
        if form.cleaned_data.get('pos'):
            filter_args['pos'] = form.cleaned_data['pos']
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

    keywords = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')

    # 限制關鍵詞數量
    limit = form.cleaned_data.get('limit', 20) if form.is_valid() else 20
    keywords = keywords[:limit]

    context = {
        'job': job,
        'articles': articles,
        'keywords': keywords,
        'form': form,
    }

    return render(request, 'scraper/job_detail.html', context)


@login_required
def generate_chart(request, job_id):
    """生成關鍵詞頻率圖表"""
    job = get_object_or_404(ScrapeJob, id=job_id, user=request.user)

    # 處理篩選條件
    form = KeywordFilterForm(request.GET)
    filter_args = {'job': job}

    if form.is_valid():
        if form.cleaned_data.get('category'):
            filter_args['category'] = form.cleaned_data['category']
        if form.cleaned_data.get('pos'):
            filter_args['pos'] = form.cleaned_data['pos']
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

    # 獲取並限制關鍵詞數量
    limit = form.cleaned_data.get('limit', 20) if form.is_valid() else 20
    keywords = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]

    # 準備圖表數據
    words = [k.word for k in keywords]
    frequencies = [k.frequency for k in keywords]

    # 使用 matplotlib 生成圖表
    plt.figure(figsize=(10, 6))
    plt.barh(words, frequencies)
    plt.xlabel('頻率')
    plt.ylabel('關鍵詞')
    plt.title('關鍵詞頻率分布')
    plt.tight_layout()

    # 保存圖表到靜態文件
    chart_path = f'static/charts/job_{job_id}_keywords.png'
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    plt.savefig(chart_path)
    plt.close()

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