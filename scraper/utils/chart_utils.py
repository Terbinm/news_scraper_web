import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import matplotlib
from django.conf import settings
import numpy as np
import io
import base64
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# 設置matplotlib不使用GUI後端
matplotlib.use('Agg')


def generate_keyword_bar_chart(keywords, title='關鍵詞頻率分布', figsize=(10, 6)):
    """
    生成關鍵詞頻率條形圖

    Args:
        keywords: KeywordAnalysis查詢集或含word和frequency的字典列表
        title: 圖表標題
        figsize: 圖表尺寸

    Returns:
        str: 圖表文件路徑
    """
    # 準備數據
    if hasattr(keywords[0], 'word'):
        words = [k.word for k in keywords]
        frequencies = [k.frequency for k in keywords]
    else:
        words = [k['word'] for k in keywords]
        frequencies = [k['frequency'] for k in keywords]

    # 創建DataFrame
    df = pd.DataFrame({'word': words, 'frequency': frequencies})
    df = df.sort_values('frequency', ascending=True)  # 按頻率升序排列，以便在圖表中從上到下顯示

    # 設置風格
    sns.set_style("darkgrid")

    # 創建圖表
    plt.figure(figsize=figsize)
    ax = sns.barplot(x='frequency', y='word', data=df, palette='viridis')

    # 設置標題和標籤
    plt.title(title, fontsize=16)
    plt.xlabel('頻率', fontsize=12)
    plt.ylabel('關鍵詞', fontsize=12)

    # 在條形末端添加數值標籤
    for i, v in enumerate(frequencies):
        ax.text(v + 0.5, i, str(v), va='center')

    # 調整布局
    plt.tight_layout()

    # 確保目錄存在
    charts_dir = os.path.join(settings.MEDIA_ROOT, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    # 生成唯一文件名
    filename = f'keywords_bar_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.png'
    filepath = os.path.join(charts_dir, filename)

    # 保存圖表
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()

    # 返回相對於MEDIA_URL的路徑
    return os.path.join('charts', filename)


def generate_pos_pie_chart(keywords, title='詞性分布'):
    """
    生成詞性分布餅圖

    Args:
        keywords: KeywordAnalysis查詢集
        title: 圖表標題

    Returns:
        str: 圖表文件路徑
    """
    # 按詞性分組統計
    pos_counts = {}
    for keyword in keywords:
        pos = keyword.pos if hasattr(keyword, 'pos') else keyword['pos']
        pos_counts[pos] = pos_counts.get(pos, 0) + 1

    # 詞性標籤映射
    pos_labels = {
        'Na': '普通名詞 (Na)',
        'Nb': '專有名詞 (Nb)',
        'Nc': '地方名詞 (Nc)'
    }

    # 準備繪圖數據
    labels = [pos_labels.get(pos, pos) for pos in pos_counts.keys()]
    sizes = list(pos_counts.values())

    # 設置風格
    sns.set_style("whitegrid")

    # 創建圖表
    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct='%1.1f%%',
            shadow=False, startangle=90, colors=sns.color_palette("Set2"))
    plt.axis('equal')  # 確保餅圖是圓的
    plt.title(title, fontsize=16)

    # 確保目錄存在
    charts_dir = os.path.join(settings.MEDIA_ROOT, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    # 生成唯一文件名
    filename = f'pos_pie_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.png'
    filepath = os.path.join(charts_dir, filename)

    # 保存圖表
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()

    # 返回相對於MEDIA_URL的路徑
    return os.path.join('charts', filename)


def generate_category_distribution_chart(keywords, title='類別分布'):
    """
    生成關鍵詞類別分布圖

    Args:
        keywords: KeywordAnalysis查詢集
        title: 圖表標題

    Returns:
        str: 圖表文件路徑
    """
    # 按類別分組統計
    category_counts = {}
    for keyword in keywords:
        category = keyword.category if hasattr(keyword, 'category') else keyword['category']
        category_counts[category] = category_counts.get(category, 0) + 1

    # 準備繪圖數據
    categories = list(category_counts.keys())
    counts = list(category_counts.values())

    # 設置風格
    sns.set_style("whitegrid")

    # 創建圖表
    plt.figure(figsize=(10, 6))
    ax = sns.barplot(x=categories, y=counts, palette='viridis')

    # 設置標題和標籤
    plt.title(title, fontsize=16)
    plt.xlabel('類別', fontsize=12)
    plt.ylabel('關鍵詞數量', fontsize=12)
    plt.xticks(rotation=45)

    # 在條形上方添加數值標籤
    for i, v in enumerate(counts):
        ax.text(i, v + 0.5, str(v), ha='center')

    # 調整布局
    plt.tight_layout()

    # 確保目錄存在
    charts_dir = os.path.join(settings.MEDIA_ROOT, 'charts')
    os.makedirs(charts_dir, exist_ok=True)

    # 生成唯一文件名
    filename = f'category_dist_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.png'
    filepath = os.path.join(charts_dir, filename)

    # 保存圖表
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()

    # 返回相對於MEDIA_URL的路徑
    return os.path.join('charts', filename)


def get_chart_as_base64(chart_func, *args, **kwargs):
    """
    將圖表轉換為base64編碼

    Args:
        chart_func: 生成圖表的函數
        args, kwargs: 傳遞給chart_func的參數

    Returns:
        str: base64編碼的圖表數據
    """
    # 將matplotlib輸出重定向到內存緩衝區
    buf = io.BytesIO()

    # 創建圖表並保存到緩衝區
    fig = chart_func(*args, **kwargs)
    fig.savefig(buf, format='png', bbox_inches='tight')

    # 獲取base64編碼
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return f'data:image/png;base64,{img_str}'


def prepare_chart_js_data(keywords, chart_type='bar'):
    """
    準備Chart.js圖表數據

    Args:
        keywords: KeywordAnalysis查詢集
        chart_type: 圖表類型 (bar, pie, line)

    Returns:
        dict: Chart.js數據格式
    """
    if hasattr(keywords[0], 'word'):
        words = [k.word for k in keywords]
        frequencies = [k.frequency for k in keywords]
    else:
        words = [k['word'] for k in keywords]
        frequencies = [k['frequency'] for k in keywords]

    if chart_type == 'bar':
        return {
            'type': 'bar',
            'data': {
                'labels': words,
                'datasets': [{
                    'label': '頻率',
                    'data': frequencies,
                    'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 1
                }]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True
                    }
                }
            }
        }
    elif chart_type == 'pie':
        return {
            'type': 'pie',
            'data': {
                'labels': words,
                'datasets': [{
                    'data': frequencies,
                    'backgroundColor': [
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 206, 86, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(153, 102, 255, 0.6)',
                        'rgba(255, 159, 64, 0.6)'
                    ],
                    'borderColor': [
                        'rgba(255, 99, 132, 1)',
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)'
                    ],
                    'borderWidth': 1
                }]
            },
            'options': {
                'responsive': True
            }
        }
    elif chart_type == 'line':
        return {
            'type': 'line',
            'data': {
                'labels': words,
                'datasets': [{
                    'label': '頻率',
                    'data': frequencies,
                    'fill': False,
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'tension': 0.1
                }]
            },
            'options': {
                'responsive': True,
                'scales': {
                    'y': {
                        'beginAtZero': True
                    }
                }
            }
        }
    else:
        raise ValueError(f"不支持的圖表類型: {chart_type}")