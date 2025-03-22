import logging
from collections import namedtuple
from django.db.models import Sum, F, Count, Q

from ..models import KeywordAnalysis, NamedEntityAnalysis

logger = logging.getLogger(__name__)


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


def get_keywords_analysis(job, form, available_categories):
    """
    獲取關鍵詞分析結果，支持多選詞性

    Args:
        job: ScrapeJob 實例
        form: KeywordFilterForm 實例
        available_categories: 可用的類別列表

    Returns:
        dict: 包含分析結果的字典
    """
    # 初始化結果字典
    result = {
        'keywords': [],
        'is_cross_category': False
    }

    # 設置基本過濾條件
    filter_args = {'job': job}

    if form.is_valid():
        # 添加詞性過濾條件 - 改為支持多選
        selected_pos = form.data.getlist('pos')
        if selected_pos:
            filter_args['pos__in'] = selected_pos  # 使用 __in 查詢

        # 添加頻率過濾條件
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

        # 處理類別選擇
        cross_category = form.cleaned_data.get('cross_category', False)
        selected_categories = form.cleaned_data.get('selected_categories', [])

        # 確保有選中的類別
        if not selected_categories:
            selected_categories = list(available_categories)

        # 添加類別過濾條件
        filter_args['category__in'] = selected_categories

        # 設置結果數量限制
        limit = form.cleaned_data.get('limit', 20)

        # 設置跨類別標記
        result['is_cross_category'] = cross_category

        try:
            # 根據是否跨類別進行不同的處理
            if cross_category:
                # 跨類別分析 - 合併相同關鍵詞在不同類別的頻率
                keywords = (KeywordAnalysis.objects
                            .filter(**filter_args)
                            .values('word', 'pos')
                            .annotate(total_frequency=Sum('frequency'))
                            .order_by('-total_frequency')[:limit])

                # 獲取包含在結果中的詞列表
                words_in_result = [kw['word'] for kw in keywords]

                # 獲取每個關鍵詞在各類別中的分布
                detail_data = []
                if words_in_result:
                    detail_data = (KeywordAnalysis.objects
                                   .filter(**filter_args, word__in=words_in_result)
                                   .values('word', 'category', 'frequency')
                                   .order_by('-frequency'))

                # 構建類別詳情字典
                category_details = {}
                for item in detail_data:
                    word = item['word']
                    if word not in category_details:
                        category_details[word] = {}
                    category_details[word][item['category']] = item['frequency']

                # 創建命名元組用於模板渲染
                KeywordResult = namedtuple('KeywordResult', [
                    'word', 'pos', 'frequency', 'category', 'category_details',
                    'category_list', 'top_category'
                ])

                # 構建最終結果列表
                keyword_list = []
                for kw in keywords:
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

                result['keywords'] = keyword_list
            else:
                # 單類別分析 - 直接獲取結果
                result['keywords'] = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
        except Exception as e:
            logger.error(f"關鍵詞分析發生錯誤: {e}", exc_info=True)
    else:
        # 表單無效時，使用默認查詢
        filter_args['category__in'] = available_categories
        limit = 20
        try:
            result['keywords'] = KeywordAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
        except Exception as e:
            logger.error(f"獲取關鍵詞時發生錯誤: {e}", exc_info=True)

    return result


def get_entities_analysis(job, form, available_categories):
    """
    獲取命名實體分析結果，支持多選實體類型

    Args:
        job: ScrapeJob 實例
        form: KeywordFilterForm 實例
        available_categories: 可用的類別列表

    Returns:
        dict: 包含分析結果的字典
    """
    # 初始化結果字典
    result = {
        'entities': [],
        'is_cross_category': False
    }

    # 設置基本過濾條件
    filter_args = {'job': job}

    if form.is_valid():
        # 添加實體類型過濾條件 - 改為支持多選
        selected_entity_types = form.data.getlist('entity_type')
        if selected_entity_types:
            filter_args['entity_type__in'] = selected_entity_types  # 使用 __in 查詢

        # 添加頻率過濾條件
        if form.cleaned_data.get('min_frequency'):
            filter_args['frequency__gte'] = form.cleaned_data['min_frequency']

        # 處理類別選擇
        cross_category = form.cleaned_data.get('cross_category', False)
        selected_categories = form.cleaned_data.get('selected_categories', [])

        # 確保有選中的類別
        if not selected_categories:
            selected_categories = list(available_categories)

        # 添加類別過濾條件
        filter_args['category__in'] = selected_categories

        # 設置結果數量限制
        limit = form.cleaned_data.get('limit', 20)

        # 設置跨類別標記
        result['is_cross_category'] = cross_category

        try:
            # 根據是否跨類別進行不同的處理
            if cross_category:
                # 跨類別分析 - 合併相同實體在不同類別的頻率
                entities = (NamedEntityAnalysis.objects
                            .filter(**filter_args)
                            .values('entity', 'entity_type')
                            .annotate(total_frequency=Sum('frequency'))
                            .order_by('-total_frequency')[:limit])

                # 獲取包含在結果中的實體列表
                entities_in_result = [(e['entity'], e['entity_type']) for e in entities]

                # 構建類別詳情字典
                category_details = {}

                # 獲取每個實體在各類別中的分布
                for entity, entity_type in entities_in_result:
                    key = (entity, entity_type)

                    # 創建這個實體的查詢條件
                    entity_filter = {
                        'job': job,
                        'entity': entity,
                        'entity_type': entity_type,
                        'category__in': selected_categories
                    }

                    detail_data = (NamedEntityAnalysis.objects
                                   .filter(**entity_filter)
                                   .values('category', 'frequency')
                                   .order_by('-frequency'))

                    # 將詳細信息整理成詞典形式
                    if key not in category_details:
                        category_details[key] = {}

                    for item in detail_data:
                        category_details[key][item['category']] = item['frequency']

                # 創建命名元組用於模板渲染
                EntityResult = namedtuple('EntityResult', [
                    'entity', 'entity_type', 'frequency', 'category', 'category_details',
                    'category_list', 'top_category'
                ])

                # 構建最終結果列表
                entity_list = []
                for e in entities:
                    key = (e['entity'], e['entity_type'])
                    details = category_details.get(key, {})

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

                    entity_list.append(EntityResult(
                        entity=e['entity'],
                        entity_type=e['entity_type'],
                        frequency=e['total_frequency'],
                        category="跨類別統計",
                        category_details=details_str,
                        category_list=category_list,
                        top_category=top_category
                    ))

                result['entities'] = entity_list
            else:
                # 單類別分析 - 直接獲取結果
                result['entities'] = NamedEntityAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
        except Exception as e:
            logger.error(f"命名實體分析發生錯誤: {e}", exc_info=True)
    else:
        # 表單無效時，使用默認查詢
        filter_args['category__in'] = available_categories
        limit = 20
        try:
            result['entities'] = NamedEntityAnalysis.objects.filter(**filter_args).order_by('-frequency')[:limit]
        except Exception as e:
            logger.error(f"獲取命名實體時發生錯誤: {e}", exc_info=True)

    return result


def get_entity_type_distribution(job, categories=None):
    """
    獲取命名實體類型的分布統計

    Args:
        job: ScrapeJob 實例
        categories: 可選，類別列表

    Returns:
        dict: 各實體類型的計數
    """
    filter_args = {'job': job}

    if categories:
        filter_args['category__in'] = categories

    try:
        # 按實體類型分組並計數
        distribution = (NamedEntityAnalysis.objects
                        .filter(**filter_args)
                        .values('entity_type')
                        .annotate(count=Count('id'))
                        .order_by('entity_type'))

        # 轉換為字典格式
        entity_type_counts = {
            'PERSON': 0,
            'LOC': 0,
            'ORG': 0,
            'TIME': 0,
            'MISC': 0
        }

        for item in distribution:
            entity_type = item['entity_type']
            if entity_type in entity_type_counts:
                entity_type_counts[entity_type] = item['count']

        return entity_type_counts
    except Exception as e:
        logger.error(f"獲取實體類型分布時發生錯誤: {e}", exc_info=True)
        return {
            'PERSON': 0,
            'LOC': 0,
            'ORG': 0,
            'TIME': 0,
            'MISC': 0
        }


def get_pos_distribution(job, categories=None):
    """
    獲取詞性的分布統計

    Args:
        job: ScrapeJob 實例
        categories: 可選，類別列表

    Returns:
        dict: 各詞性的計數
    """
    filter_args = {'job': job}

    if categories:
        filter_args['category__in'] = categories

    try:
        # 按詞性分組並計數
        distribution = (KeywordAnalysis.objects
                        .filter(**filter_args)
                        .values('pos')
                        .annotate(count=Count('id'))
                        .order_by('pos'))

        # 轉換為字典格式
        pos_counts = {
            'Na': 0,
            'Nb': 0,
            'Nc': 0
        }

        for item in distribution:
            pos = item['pos']
            if pos in pos_counts:
                pos_counts[pos] = item['count']

        return pos_counts
    except Exception as e:
        logger.error(f"獲取詞性分布時發生錯誤: {e}", exc_info=True)
        return {
            'Na': 0,
            'Nb': 0,
            'Nc': 0
        }