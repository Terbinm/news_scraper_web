import os
import json
import logging
import importlib
import sys
from datetime import datetime
from django.conf import settings
from django.utils import timezone

from .models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis


def run_scraper(job_id):
    """
    運行爬蟲的主函數

    Args:
        job_id: ScrapeJob 模型的 ID
    """

    try:
        # 獲取任務記錄
        job = ScrapeJob.objects.get(id=job_id)
        job.status = 'running'
        job.save()

        # 設置輸出目錄
        current_date = datetime.now().strftime('%Y%m%d_%H%M_%S')
        output_dir = os.path.join(settings.MEDIA_ROOT, 'scraper_output', f'job_{job_id}_{current_date}')
        os.makedirs(output_dir, exist_ok=True)

        # 導入爬蟲模組
        # 假設爬蟲代碼已複製到專案中，需要調整路徑
        scraper_module_path = os.path.join(settings.BASE_DIR, 'scraper', 'utils', 'scraper_utils.py')
        spec = importlib.util.spec_from_file_location("scraper_utils", scraper_module_path)
        scraper_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scraper_module)

        # 獲取爬蟲參數
        categories = job.categories.split(',') if job.categories else None
        limit_per_category = job.limit_per_category
        use_threading = job.use_threading
        max_workers = job.max_workers

        # 初始化爬蟲
        scraper = scraper_module.CTSimpleScraper(headless=True)

        # 執行爬蟲
        success = scraper.run(
            categories=categories,
            limit_per_category=limit_per_category,
            use_threading=use_threading,
            max_workers=max_workers,
            output_dir=output_dir
        )

        # 處理爬蟲結果
        if success:
            # 找到結果 JSON 文件
            json_files = [f for f in os.listdir(output_dir) if f.endswith('.json') and f.startswith('ct_articles_')]
            if json_files:
                result_file = os.path.join(output_dir, sorted(json_files)[-1])  # 取最新的文件
                job.result_file_path = result_file
                job.status = 'completed'

                # 解析JSON並存入資料庫
                process_scraper_results(job, result_file)
            else:
                job.status = 'failed'
                logging.error(f"爬蟲任務 {job_id} 未生成結果文件")
        else:
            job.status = 'failed'
            logging.error(f"爬蟲任務 {job_id} 執行失敗")

        job.save()

    except Exception as e:
        logging.error(f"運行爬蟲時發生錯誤: {e}", exc_info=True)
        try:
            job = ScrapeJob.objects.get(id=job_id)
            job.status = 'failed'
            job.save()
        except:
            pass


def process_scraper_results(job, result_file_path):
    """
    處理爬蟲結果，將文章和關鍵詞寫入資料庫

    Args:
        job: ScrapeJob 實例
        result_file_path: 結果JSON文件路徑
    """
    try:
        # 讀取 JSON 文件
        with open(result_file_path, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)

        # 保存文章
        for article_data in articles_data:
            # 創建 Article 記錄
            date_str = article_data.get('date', datetime.now().isoformat())
            date_obj = datetime.fromisoformat(date_str)
            aware_date = timezone.make_aware(date_obj)

            article = Article(
                job=job,
                item_id=article_data.get('item_id', ''),
                category=article_data.get('category', ''),
                title=article_data.get('title', ''),
                content=article_data.get('content', ''),
                date=aware_date,
                author=','.join(article_data.get('author', [])),
                link=article_data.get('link', ''),
                photo_links=json.dumps(article_data.get('photo_links', []))
            )
            article.save()

        # 處理 category_keywords_stats.json 文件
        keywords_file = os.path.join(os.path.dirname(result_file_path), 'category_keywords_stats.json')
        if os.path.exists(keywords_file):
            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords_data = json.load(f)

            # 批量創建關鍵詞分析記錄
            keyword_objects = []
            for keyword_data in keywords_data:
                keyword_objects.append(KeywordAnalysis(
                    job=job,
                    word=keyword_data.get('word', ''),
                    pos=keyword_data.get('pos', ''),
                    frequency=keyword_data.get('frequency', 0),
                    category=keyword_data.get('category', '')
                ))

            # 批量保存 (分批次以避免過大的查詢)
            batch_size = 100
            for i in range(0, len(keyword_objects), batch_size):
                KeywordAnalysis.objects.bulk_create(keyword_objects[i:i + batch_size])

        # 處理 category_entities_stats.json 文件
        entities_file = os.path.join(os.path.dirname(result_file_path), 'category_entities_stats.json')
        if os.path.exists(entities_file):
            with open(entities_file, 'r', encoding='utf-8') as f:
                entities_data = json.load(f)

            # 批量創建命名實體分析記錄
            entity_objects = []
            for entity_data in entities_data:
                entity_objects.append(NamedEntityAnalysis(
                    job=job,
                    entity=entity_data.get('entity', ''),
                    entity_type=entity_data.get('entity_type', ''),
                    frequency=entity_data.get('frequency', 0),
                    category=entity_data.get('category', '')
                ))

            # 批量保存 (分批次以避免過大的查詢)
            batch_size = 100
            for i in range(0, len(entity_objects), batch_size):
                NamedEntityAnalysis.objects.bulk_create(entity_objects[i:i + batch_size])

    except Exception as e:
        logging.error(f"處理爬蟲結果時發生錯誤: {e}", exc_info=True)
        raise

def generate_entity_chart_data(job_id, filters=None):
    """
    生成命名實體圖表數據

    Args:
        job_id: ScrapeJob ID
        filters: 篩選條件字典

    Returns:
        dict: 圖表數據
    """
    # 準備篩選條件
    if filters is None:
        filters = {}

    query_filters = {'job_id': job_id}

    if 'category' in filters and filters['category']:
        query_filters['category'] = filters['category']

    if 'entity_type' in filters and filters['entity_type']:
        query_filters['entity_type'] = filters['entity_type']

    if 'min_frequency' in filters and filters['min_frequency']:
        query_filters['frequency__gte'] = filters['min_frequency']

    # 獲取並限制命名實體數量
    limit = filters.get('limit', 20)
    cross_category = filters.get('cross_category', False)

    # 獲取符合篩選條件的命名實體
    entities = NamedEntityAnalysis.objects.filter(**query_filters)

    # 如果啟用跨類別統計，則合併相同實體在不同類別的頻率
    if cross_category:
        from django.db.models import Sum

        # 將category從篩選條件中移除（如果有的話）
        if 'category' in query_filters:
            del query_filters['category']

        # 如果有選擇特定類別，則限制查詢範圍
        selected_categories = filters.get('selected_categories', [])
        if selected_categories:
            query_filters['category__in'] = selected_categories

        # 重新查詢命名實體，按照實體和類型分組，並計算頻率總和
        entities = (NamedEntityAnalysis.objects
                   .filter(**query_filters)
                   .values('entity', 'entity_type')
                   .annotate(frequency=Sum('frequency'))
                   .order_by('-frequency')[:limit])

        # 準備圖表數據
        labels = [f"{e['entity']} ({e['entity_type']})" for e in entities]
        data = [e['frequency'] for e in entities]

        # 設置類別為"跨類別統計"
        if selected_categories:
            category_label = "、".join(selected_categories) + " 跨類別統計"
        else:
            category_label = "所有類別跨類別統計"
    else:
        # 不進行跨類別統計時，直接按頻率排序取前N個
        entities = entities.order_by('-frequency')[:limit]

        # 準備圖表數據
        labels = [f"{e.entity} ({e.entity_type})" for e in entities]
        data = [e.frequency for e in entities]

        # 設置類別標籤
        if 'category' in filters and filters['category']:
            category_label = filters['category']
        else:
            category_label = "所有類別"

    # 返回 Chart.js 格式數據
    return {
        'labels': labels,
        'datasets': [{
            'label': f'{category_label}命名實體頻率',
            'data': data,
            'backgroundColor': 'rgba(153, 102, 255, 0.6)',
            'borderColor': 'rgba(153, 102, 255, 1)',
            'borderWidth': 1
        }]
    }



def get_categories_list():
    """獲取所有類別列表"""
    return [
        '財經', '政治', '社會', '科技', '國際', '娛樂', '生活', '言論', '軍事'
    ]


def get_pos_list():
    """獲取所有詞性列表"""
    return [
        {'code': 'Na', 'name': '普通名詞'},
        {'code': 'Nb', 'name': '專有名詞'},
        {'code': 'Nc', 'name': '地方名詞'}
    ]


def generate_keyword_chart_data(job_id, filters=None):
    """
    生成關鍵詞圖表數據

    Args:
        job_id: ScrapeJob ID
        filters: 篩選條件字典

    Returns:
        dict: 圖表數據
    """
    # 準備篩選條件
    if filters is None:
        filters = {}

    query_filters = {'job_id': job_id}

    if 'category' in filters and filters['category']:
        query_filters['category'] = filters['category']

    if 'pos' in filters and filters['pos']:
        query_filters['pos'] = filters['pos']

    if 'min_frequency' in filters and filters['min_frequency']:
        query_filters['frequency__gte'] = filters['min_frequency']

    # 獲取關鍵詞資料
    limit = filters.get('limit', 20)
    cross_category = filters.get('cross_category', False)

    # 獲取符合篩選條件的關鍵詞
    keywords = KeywordAnalysis.objects.filter(**query_filters)

    # 如果啟用跨類別統計，則合併相同關鍵詞在不同類別的頻率
    if cross_category:
        from django.db.models import Sum

        # 將category從篩選條件中移除（如果有的話）
        if 'category' in query_filters:
            del query_filters['category']

        # 重新查詢關鍵詞，按照詞和詞性分組，並計算頻率總和
        keywords = (KeywordAnalysis.objects
                    .filter(**query_filters)
                    .values('word', 'pos')
                    .annotate(frequency=Sum('frequency'))
                    .order_by('-frequency')[:limit])

        # 準備圖表數據
        labels = [k['word'] for k in keywords]
        data = [k['frequency'] for k in keywords]

        # 設置類別為"跨類別統計"
        category_label = "跨類別統計"
    else:
        # 不進行跨類別統計時，直接按頻率排序取前N個
        keywords = keywords.order_by('-frequency')[:limit]

        # 準備圖表數據
        labels = [k.word for k in keywords]
        data = [k.frequency for k in keywords]

        # 設置類別標籤
        if 'category' in filters and filters['category']:
            category_label = filters['category']
        else:
            category_label = "所有類別"

    # 返回 Chart.js 格式數據
    return {
        'labels': labels,
        'datasets': [{
            'label': f'{category_label}關鍵詞頻率',
            'data': data,
            'backgroundColor': 'rgba(54, 162, 235, 0.6)',
            'borderColor': 'rgba(54, 162, 235, 1)',
            'borderWidth': 1
        }]
    }