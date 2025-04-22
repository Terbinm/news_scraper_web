import re
import json
import logging
import datetime
from collections import defaultdict, Counter
from django.db.models import Q, Count, Case, When, Value, IntegerField, Sum
from django.utils import timezone
from django.core.cache import cache
import hashlib

from ..models import ScrapeJob, Article, KeywordAnalysis, NamedEntityAnalysis

logger = logging.getLogger(__name__)


class SearchAnalysisService:
    """提供文章的搜尋與分析功能"""

    def __init__(self, job):
        """
        初始化搜尋分析服務

        Args:
            job: ScrapeJob 實例
        """
        self.job = job
        self.cache_timeout = 60 * 60  # 缓存超时时间（1小时）

    def search(self, search_criteria):
        """
        根據搜尋條件查找文章

        Args:
            search_criteria: 包含所有搜尋條件的字典

        Returns:
            QuerySet: 符合條件的文章查詢集
        """
        try:
            # 使用新的方法構建查詢
            query = self.build_search_query(search_criteria)

            # 使用緩存鍵 - 使用更安全的方式處理不可哈希類型如列表
            # 使用 MD5 哈希縮短緩存鍵長度
            criteria_str = str(self.job.id)
            for key, value in sorted(search_criteria.items()):
                if isinstance(value, list):
                    # 將列表轉換為排序後的字符串
                    value_str = ','.join(sorted([str(v) for v in value]))
                    criteria_str += f"_{key}:{value_str}"
                else:
                    criteria_str += f"_{key}:{str(value)}"

            # 使用 MD5 哈希縮短緩存鍵
            hash_object = hashlib.md5(criteria_str.encode())
            cache_key = f"search_{self.job.id}_{hash_object.hexdigest()}"

            # 嘗試從緩存獲取結果
            cached_results = cache.get(cache_key)
            if cached_results is not None:
                logger.info(f"使用緩存的搜索結果 {cache_key}")
                return cached_results

            # 使結果唯一並按日期排序
            query = query.distinct().order_by('-date')

            # 緩存結果
            cache.set(cache_key, query, self.cache_timeout)

            return query

        except Exception as e:
            logger.error(f"搜尋文章時發生錯誤: {e}", exc_info=True)
            return Article.objects.none()  # 返回空查詢集

    def build_search_query(self, search_criteria):
        """
        構建搜索查詢，但不執行

        Args:
            search_criteria: 包含所有搜尋條件的字典

        Returns:
            QuerySet: 構建的查詢但不執行
        """
        # 初始查詢 - 該任務的所有文章
        query = Article.objects.filter(job=self.job)

        # 應用類別篩選
        if 'categories' in search_criteria and search_criteria['categories']:
            query = query.filter(category__in=search_criteria['categories'])

        # 應用日期篩選
        if search_criteria.get('date_from'):
            date_from = search_criteria['date_from']
            if isinstance(date_from, str):
                date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(date__gte=datetime.datetime.combine(date_from, datetime.time.min))

        if search_criteria.get('date_to'):
            date_to = search_criteria['date_to']
            if isinstance(date_to, str):
                date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(date__lte=datetime.datetime.combine(date_to, datetime.time.max))

        # 準備搜尋詞相關條件
        search_terms = search_criteria.get('search_terms', [])
        search_mode = search_criteria.get('search_mode', 'and')
        search_type = search_criteria.get('search_type', 'both')

        # 對非列表類型的搜尋詞進行處理
        if isinstance(search_terms, str):
            search_terms = [term.strip() for term in search_terms.split(',') if term.strip()]

        # 如果有搜尋詞，則進行內容搜尋
        if search_terms:
            # 根據搜尋類型確定查詢條件
            content_filter = None

            for term in search_terms:
                current_filter = self._build_term_filter(
                    term,
                    search_type,
                    search_criteria.get('include_title', True),
                    search_criteria.get('include_content', True),
                    search_criteria.get('entity_types', []),
                    search_criteria.get('pos_types', [])
                )

                if search_mode == 'and':
                    query = query.filter(current_filter)
                else:  # 'or' mode
                    if content_filter is None:
                        content_filter = current_filter
                    else:
                        content_filter |= current_filter

            # 對於OR模式，最後應用過濾器
            if search_mode == 'or' and content_filter is not None:
                query = query.filter(content_filter)

        # 根據關鍵詞數量篩選
        min_keywords_count = search_criteria.get('min_keywords_count')
        if min_keywords_count and int(min_keywords_count) > 0:
            # 獲取符合條件的文章ID
            keyword_articles = self._filter_by_keyword_count(query, int(min_keywords_count), search_terms,
                                                             search_criteria.get('pos_types', []))
            if keyword_articles:
                query = query.filter(id__in=keyword_articles)
            else:
                # 如果沒有符合的文章，返回空集
                return Article.objects.none()

        # 根據實體數量篩選
        min_entities_count = search_criteria.get('min_entities_count')
        if min_entities_count and int(min_entities_count) > 0:
            # 獲取符合條件的文章ID
            entity_articles = self._filter_by_entity_count(
                query,
                int(min_entities_count),
                search_terms,
                search_criteria.get('entity_types', [])
            )
            if entity_articles:
                query = query.filter(id__in=entity_articles)
            else:
                # 如果沒有符合的文章，返回空集
                return Article.objects.none()

        return query

    def _build_term_filter(self, term, search_type, include_title, include_content, entity_types, pos_types):
        """
        構建單個搜尋詞的過濾條件

        Args:
            term: 搜尋詞
            search_type: 搜尋類型 ('keyword', 'entity', 'both')
            include_title: 是否包含標題
            include_content: 是否包含內容
            entity_types: 實體類型列表
            pos_types: 詞性列表

        Returns:
            Q: Django 查詢條件
        """
        filters = Q()

        # 搜索关键词或两者
        if search_type in ['keyword', 'both']:
            # 如果有指定詞性，先檢查該詞是否符合要求的詞性
            if pos_types:
                keyword_query = KeywordAnalysis.objects.filter(
                    job=self.job,
                    word__icontains=term,
                    pos__in=pos_types
                )
                # 如果存在符合條件的關鍵詞，則在文章中搜尋
                if keyword_query.exists():
                    if include_title:
                        filters |= Q(title__icontains=term)
                    if include_content:
                        filters |= Q(content__icontains=term)
            else:
                # 如果未指定詞性，則直接搜尋
                if include_title:
                    filters |= Q(title__icontains=term)
                if include_content:
                    filters |= Q(content__icontains=term)

        # 搜索命名实体或两者
        if search_type in ['entity', 'both']:
            # 获取包含指定实体的文章ID
            entity_articles = self._get_articles_with_entity(term, entity_types)
            if entity_articles:
                filters |= Q(id__in=entity_articles)

        return filters

    def _get_articles_with_entity(self, entity_term, entity_types):
        """
        獲取包含指定實體的文章ID

        Args:
            entity_term: 實體搜尋詞
            entity_types: 要搜尋的實體類型列表

        Returns:
            list: 文章ID列表
        """
        try:
            # 查詢符合條件的命名實體
            query = NamedEntityAnalysis.objects.filter(
                job=self.job,
                entity__icontains=entity_term
            )

            if entity_types:
                query = query.filter(entity_type__in=entity_types)

            # 獲取包含這些實體的所有類別
            categories = query.values_list('category', flat=True).distinct()

            # 查找包含這些類別且屬於該任務的文章
            # 這裡我們使用聯合查詢查找匹配的文章
            article_ids = []
            for article in Article.objects.filter(job=self.job, category__in=categories):
                # 檢查文章內容是否包含該實體詞
                if entity_term.lower() in article.title.lower() or entity_term.lower() in article.content.lower():
                    article_ids.append(article.id)

            return article_ids
        except Exception as e:
            logger.error(f"獲取包含實體的文章時發生錯誤: {e}", exc_info=True)
            return []

    def _filter_by_keyword_count(self, article_query, min_count, search_terms, pos_types=None):
        """
        根據關鍵詞出現次數篩選文章

        Args:
            article_query: 文章查詢集
            min_count: 最小關鍵詞出現次數
            search_terms: 搜尋詞列表
            pos_types: 詞性列表（可選）

        Returns:
            list: 符合條件的文章ID列表
        """
        # 如果沒有搜尋詞且有指定最小關鍵詞數量，則計算所有關鍵詞
        if not search_terms and min_count > 0:
            # 使用分組和計數來提高效率
            from django.db.models import Count

            # 獲取每篇文章對應的關鍵詞數量
            keyword_counts = KeywordAnalysis.objects.filter(
                job=self.job
            )

            if pos_types:
                keyword_counts = keyword_counts.filter(pos__in=pos_types)

            # 按類別和詞性分組，計算每個類別的關鍵詞數量
            keyword_counts = keyword_counts.values('category').annotate(
                count=Count('word', distinct=True)
            )

            # 獲取所有包含足夠關鍵詞的類別
            qualifying_categories = [
                item['category'] for item in keyword_counts
                if item['count'] >= min_count
            ]

            # 篩選出屬於這些類別的文章
            article_ids = list(article_query.filter(
                category__in=qualifying_categories
            ).values_list('id', flat=True))

            return article_ids

        # 如果有搜尋詞，檢查每篇文章中這些詞的出現次數
        article_ids = []

        for article in article_query:
            keyword_count = 0
            for term in search_terms:
                if term.lower() in article.title.lower() or term.lower() in article.content.lower():
                    keyword_count += 1

            if keyword_count >= min_count:
                article_ids.append(article.id)

        return article_ids

    def _filter_by_entity_count(self, article_query, min_count, search_terms, entity_types=None):
        """
        根據實體出現次數篩選文章

        Args:
            article_query: 文章查詢集
            min_count: 最小實體出現次數
            search_terms: 搜尋詞列表
            entity_types: 實體類型列表（可選）

        Returns:
            list: 符合條件的文章ID列表
        """
        try:
            # 如果沒有搜尋詞且有指定最小實體數量，則計算所有實體
            if not search_terms and min_count > 0:
                # 使用分組和計數來提高效率
                from django.db.models import Count

                # 獲取每篇文章對應的實體數量
                entity_counts = NamedEntityAnalysis.objects.filter(
                    job=self.job
                )

                if entity_types:
                    entity_counts = entity_counts.filter(entity_type__in=entity_types)

                # 按類別分組，計算每個類別的實體數量
                entity_counts = entity_counts.values('category').annotate(
                    count=Count('entity', distinct=True)
                )

                # 獲取所有包含足夠實體的類別
                qualifying_categories = [
                    item['category'] for item in entity_counts
                    if item['count'] >= min_count
                ]

                # 篩選出屬於這些類別的文章
                article_ids = list(article_query.filter(
                    category__in=qualifying_categories
                ).values_list('id', flat=True))

                return article_ids

            # 獲取所有相關的命名實體
            query = NamedEntityAnalysis.objects.filter(job=self.job)

            if entity_types:
                query = query.filter(entity_type__in=entity_types)

            # 使用 OR 邏輯匹配任一搜尋詞
            entity_filter = Q()
            for term in search_terms:
                entity_filter |= Q(entity__icontains=term)

            query = query.filter(entity_filter)

            # 獲取包含這些實體的所有類別
            entity_categories = query.values_list('category', flat=True).distinct()

            # 創建一個字典來計數每篇文章中的實體數量
            article_entity_counts = defaultdict(int)

            # 對於每篇文章，檢查它是否包含搜尋詞
            for article in article_query.filter(category__in=entity_categories):
                entity_count = 0
                for term in search_terms:
                    # 檢查文章內容或標題是否包含該搜尋詞
                    if (term.lower() in article.title.lower() or
                            term.lower() in article.content.lower()):
                        entity_count += 1

                # 只有當實體數量達到最小要求時才加入結果
                if entity_count >= min_count:
                    article_entity_counts[article.id] = entity_count

            # 返回符合條件的文章ID列表
            return list(article_entity_counts.keys())

        except Exception as e:
            logger.error(f"根據實體數量篩選文章時發生錯誤: {e}", exc_info=True)
            return []

    def get_entity_distribution(self, articles, limit=20):
        """
        獲取實體分布數據

        Args:
            articles: 文章查詢集
            limit: 最大實體數量

        Returns:
            list: 實體分布數據列表
        """
        try:

            # 獲取所有文章的類別
            article_categories = list(articles.values_list('category', flat=True))

            if not article_categories:
                return []

            # 獲取這些類別中的命名實體
            entities = NamedEntityAnalysis.objects.filter(
                job=self.job,
                category__in=article_categories
            ).values('entity', 'entity_type').annotate(
                total=Sum('frequency')
            ).order_by('-total')[:limit]

            # 確保返回的是列表
            result = []
            for entity in entities:
                result.append({
                    'entity': entity['entity'],
                    'entity_type': entity['entity_type'],
                    'total': entity['total']
                })

            return result

        except Exception as e:
            logger.error(f"獲取實體分布時出錯: {e}", exc_info=True)
            return []

    def generate_cooccurrence_data(self, articles, limit=30):
        """
        生成關鍵詞/實體共現數據

        Args:
            articles: 文章查詢集
            limit: 最大節點數量

        Returns:
            dict: 共現關係數據
        """
        try:
            # 確保有文章可分析
            if not articles.exists():
                return {"nodes": [], "links": []}

            from collections import defaultdict, Counter

            # 獲取所有文章的類別
            article_categories = list(articles.values_list('category', flat=True))

            # 收集所有文章的前15個關鍵詞和前10個命名實體
            all_keywords = []
            all_entities = []

            # 獲取這些類別中的關鍵詞
            keywords = KeywordAnalysis.objects.filter(
                job=self.job,
                category__in=article_categories
            ).values('word', 'pos', 'category').order_by('-frequency')[:100]  # 取前100個關鍵詞

            # 獲取這些類別中的命名實體
            entities = NamedEntityAnalysis.objects.filter(
                job=self.job,
                category__in=article_categories
            ).values('entity', 'entity_type', 'category').order_by('-frequency')[:50]  # 取前50個實體

            # 將關鍵詞和實體分組到類別
            category_keywords = defaultdict(list)
            category_entities = defaultdict(list)

            for kw in keywords:
                category_keywords[kw['category']].append(kw['word'])
                all_keywords.append(kw['word'])

            for ent in entities:
                category_entities[ent['category']].append(ent['entity'])
                all_entities.append(ent['entity'])

            # 如果沒有足夠數據，返回空結果
            if not all_keywords and not all_entities:
                return {"nodes": [], "links": []}

            # 計算最常見的關鍵詞和實體
            common_keywords = [item for item, count in Counter(all_keywords).most_common(limit // 2)]
            common_entities = [item for item, count in Counter(all_entities).most_common(limit // 2)]

            # 構建共現矩陣
            nodes = []
            links = []

            # 添加關鍵詞節點
            for i, keyword in enumerate(common_keywords):
                nodes.append({
                    'id': f'kw_{i}',
                    'name': keyword,
                    'group': 1,  # 關鍵詞組
                    'value': all_keywords.count(keyword)  # 頻率作為節點大小
                })

            # 添加實體節點
            for i, entity in enumerate(common_entities):
                nodes.append({
                    'id': f'ent_{i}',
                    'name': entity,
                    'group': 2,  # 實體組
                    'value': all_entities.count(entity)  # 頻率作為節點大小
                })

            # 構建連接
            # 統計兩兩共現次數
            cooccurrence = defaultdict(int)

            # 根據類別判斷共現關係
            for category in article_categories:
                keywords_in_category = [kw for kw in category_keywords.get(category, [])]
                entities_in_category = [ent for ent in category_entities.get(category, [])]

                # 過濾出常見關鍵詞和實體
                keywords_in_category = [kw for kw in keywords_in_category if kw in common_keywords]
                entities_in_category = [ent for ent in entities_in_category if ent in common_entities]

                # 關鍵詞與關鍵詞共現
                for i in range(len(keywords_in_category)):
                    for j in range(i + 1, len(keywords_in_category)):
                        pair = tuple(sorted([keywords_in_category[i], keywords_in_category[j]]))
                        cooccurrence[pair] += 1

                # 實體與實體共現
                for i in range(len(entities_in_category)):
                    for j in range(i + 1, len(entities_in_category)):
                        pair = tuple(sorted([entities_in_category[i], entities_in_category[j]]))
                        cooccurrence[pair] += 1

                # 關鍵詞與實體共現
                for kw in keywords_in_category:
                    for ent in entities_in_category:
                        pair = tuple(sorted([kw, ent]))
                        cooccurrence[pair] += 1

            # 建立連接
            for (source, target), weight in cooccurrence.items():
                # 只保留權重大於1的連接
                if weight > 1:
                    source_id = None
                    target_id = None

                    # 查找source對應的節點ID
                    for node in nodes:
                        if node['name'] == source:
                            source_id = node['id']
                            break

                    # 查找target對應的節點ID
                    for node in nodes:
                        if node['name'] == target:
                            target_id = node['id']
                            break

                    if source_id and target_id:
                        links.append({
                            'source': source_id,
                            'target': target_id,
                            'value': weight  # 共現次數作為連接權重
                        })

            return {
                'nodes': nodes,
                'links': links
            }

        except Exception as e:
            logger.error(f"生成共現關係數據時出錯: {e}", exc_info=True)
            return {'nodes': [], 'links': []}

    def get_top_article_image(self, articles):
        """
        獲取包含最多搜尋關鍵詞的文章的圖片

        Args:
            articles: 文章查詢集

        Returns:
            str: 圖片URL或預設圖片
        """
        try:
            # 確保有文章可分析
            if not articles.exists():
                return "/static/images/404.svg"

            # 按日期倒序獲取前5篇文章
            top_articles = articles.order_by('-date')[:5]

            for article in top_articles:
                # 嘗試解析photo_links
                if article.photo_links:
                    try:
                        photo_links = json.loads(article.photo_links)
                        if photo_links and isinstance(photo_links, list) and len(photo_links) > 0:
                            # 過濾無效URL
                            valid_links = [link for link in photo_links if
                                           isinstance(link, str) and
                                           (link.startswith('http') or link.startswith('/'))]

                            # 返回第一個有效圖片鏈接
                            if valid_links:
                                return valid_links[0]
                    except (json.JSONDecodeError, TypeError):
                        # 如果不是有效的JSON，嘗試其他文章
                        continue

            # 如果沒有找到有效圖片，返回預設圖片
            return "/static/images/404.svg"

        except Exception as e:
            logger.error(f"獲取頂部文章圖片時出錯: {e}", exc_info=True)
            return "/static/images/404.svg"  # 返回預設圖片

    def get_keywords_distribution(self, articles, limit=20):
        """
        獲取關鍵詞分布數據

        Args:
            articles: 文章查詢集
            limit: 最大關鍵詞數量

        Returns:
            list: 關鍵詞分布數據列表
        """
        try:
            from django.db.models import Count

            # 獲取所有文章的類別
            article_categories = list(articles.values_list('category', flat=True))

            if not article_categories:
                return []

            # 獲取這些類別中的關鍵詞
            keywords = KeywordAnalysis.objects.filter(
                job=self.job,
                category__in=article_categories
            ).values('word', 'pos').annotate(
                total=Sum('frequency')
            ).order_by('-total')[:limit]

            # 確保返回的是列表，並添加來源分類
            result = []
            for keyword in keywords:
                result.append({
                    'word': keyword['word'],
                    'pos': keyword['pos'],
                    'total': keyword['total']
                })

            return result

        except Exception as e:
            logger.error(f"獲取關鍵詞分布時出錯: {e}", exc_info=True)
            return []

    def generate_time_series(self, articles, grouping='day'):
        """
        生成時間序列數據，顯示隨時間變化的文章數量

        Args:
            articles: 文章查詢集
            grouping: 時間分組方式 ('day', 'week', 'month')

        Returns:
            list: 時間序列數據列表
        """
        try:
            from collections import defaultdict
            import datetime

            time_series = defaultdict(int)

            # 對於每篇文章，根據選擇的分組方式分組
            for article in articles:
                date = article.date.date()

                if grouping == 'week':
                    # 獲取該日期所在的週的星期一
                    date = date - datetime.timedelta(days=date.weekday())
                elif grouping == 'month':
                    # 獲取該月的第一天
                    date = date.replace(day=1)

                # 轉換為ISO格式字符串，確保Javascript可以正確解析
                date_str = date.isoformat()

                # 增加該日期/週/月的文章計數
                time_series[date_str] += 1

            # 將defaultdict轉換為列表
            time_series_data = [
                {'date': k, 'count': v} for k, v in sorted(time_series.items())
            ]

            return time_series_data

        except Exception as e:
            self.logger.error(f"生成時間序列數據時出錯: {e}", exc_info=True)
            return []

    def get_date_range(self):
        """
        獲取該任務下文章的日期範圍

        Returns:
            tuple: (最早日期, 最晚日期)
        """
        from django.db.models import Min, Max

        try:
            date_range = Article.objects.filter(job=self.job).aggregate(
                min_date=Min('date'),
                max_date=Max('date')
            )

            return (
                date_range['min_date'].date() if date_range['min_date'] else None,
                date_range['max_date'].date() if date_range['max_date'] else None
            )
        except Exception as e:
            logger.error(f"獲取日期範圍時發生錯誤: {e}", exc_info=True)
            return (None, None)