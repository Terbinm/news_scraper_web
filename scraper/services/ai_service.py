import os
import json
import logging
import threading
import time
import requests
from django.conf import settings
from ..models import AIReport

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama API 客戶端"""

    def __init__(self, base_url=None, model=None):
        """初始化 Ollama 客戶端

        Args:
            base_url: Ollama服務基礎URL，默認使用設置中的配置
            model: 使用的模型，默認使用設置中的配置
        """
        self.base_url = base_url or settings.OLLAMA_SETTINGS['BASE_URL']
        self.model = model or settings.OLLAMA_SETTINGS['MODEL']
        self.timeout = settings.OLLAMA_SETTINGS.get('TIMEOUT', 120)

    def generate(self, prompt, **kwargs):
        """生成文本

        Args:
            prompt: 提示詞
            **kwargs: 其他參數如temperature, top_p等

        Returns:
            str: 生成的文本

        Raises:
            Exception: 如果API調用失敗
        """
        try:
            # 構建請求URL
            url = f"{self.base_url}/api/generate"

            # 構建請求參數
            params = {
                "model": self.model,
                "prompt": prompt,
                "stream": False  # 我們要求一次性返回完整結果
            }

            # 添加其他參數
            for key in ['temperature', 'top_p', 'top_k', 'max_tokens']:
                if key in kwargs:
                    params[key] = kwargs[key]
                elif key.upper() in settings.OLLAMA_SETTINGS:
                    params[key] = settings.OLLAMA_SETTINGS[key.upper()]

            # 發送請求
            response = requests.post(url, json=params, timeout=self.timeout)

            # 檢查響應狀態
            response.raise_for_status()

            # 解析響應
            result = response.json()

            # 提取生成的文本
            return result.get('response', '')

        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API調用失敗: {e}")
            raise Exception(f"AI服務連接失敗: {str(e)}")
        except Exception as e:
            logger.error(f"生成文本時發生錯誤: {e}")
            raise


def _prepare_report_prompt(search_params, search_results, language='zh-TW'):
    """準備報告生成的提示詞

    Args:
        search_params: 搜索參數
        search_results: 搜索結果
        language: 報告語言

    Returns:
        str: 格式化的提示詞
    """
    # 提取搜索詞
    search_terms = search_params.get('search_terms', [])
    if isinstance(search_terms, str):
        search_terms = [term.strip() for term in search_terms.split(',') if term.strip()]

    # 提取類別
    categories = search_params.get('categories', [])

    # 提取日期範圍
    date_from = search_params.get('date_from', '')
    date_to = search_params.get('date_to', '')
    date_range = f"{date_from} 至 {date_to}" if date_from and date_to else "全部時間"

    # 準備文章摘要
    article_summaries = []
    for i, article in enumerate(search_results[:10]):  # 限制使用前10篇文章
        article_summaries.append(
            f"文章{i + 1}:\n"
            f"標題: {article.get('title', '')}\n"
            f"類別: {article.get('category', '')}\n"
            f"日期: {article.get('date', '')}\n"
            f"內容摘要: {article.get('content', '')[:200]}...\n"
        )

    article_data = "\n".join(article_summaries)

    # 構建提示詞
    prompt = f"""你是一位專業的新聞分析師，請根據以下提供的新聞文章數據，用{language}撰寫一份詳盡的分析報告。

搜索關鍵詞: {', '.join(search_terms)}
類別: {', '.join(categories)}
時間範圍: {date_range}
相關文章數量: {len(search_results)}

以下是部分相關文章的摘要:
{article_data}

請撰寫一份全面的分析報告，包含以下部分：
1. 摘要：概述主要發現和趨勢
2. 關鍵詞分析：分析搜索關鍵詞在這些新聞中的上下文和重要性
3. 時間趨勢：分析這些報導在時間線上的分布和演變
4. 類別分布：分析不同新聞類別的報導數量和角度差異
5. 核心議題：識別這些新聞報導的核心議題和主題
6. 潛在影響：分析這些新聞事件可能產生的社會、政治或經濟影響
7. 建議與結論：根據分析提出的見解和建議

請確保報告客觀、全面，使用正式的分析語言，並基於提供的數據進行分析。如果數據不足以支持某些結論，請明確指出。報告長度應在1500-2000字之間。

報告：
"""

    return prompt


def generate_report_async(report_id, search_params, search_results):
    """非同步生成報告

    Args:
        report_id: AIReport模型的ID
        search_params: 搜索參數
        search_results: 搜索結果列表
    """
    thread = threading.Thread(
        target=_generate_report_task,
        args=(report_id, search_params, search_results)
    )
    thread.daemon = True
    thread.start()
    return thread


def _generate_report_task(report_id, search_params, search_results):
    """報告生成任務

    Args:
        report_id: AIReport模型的ID
        search_params: 搜索參數
        search_results: 搜索結果列表
    """
    try:
        # 獲取報告記錄
        report = AIReport.objects.get(id=report_id)

        # 防止重複生成
        if report.status != 'pending':
            logger.warning(f"報告 {report_id} 狀態為 {report.status}，跳過生成")
            return

        # 更新狀態為處理中
        report.status = 'running'
        report.save()

        # 準備提示詞
        prompt = _prepare_report_prompt(
            search_params,
            search_results,
            language=report.language
        )

        # 初始化Ollama客戶端
        client = OllamaClient()

        # 生成報告
        content = client.generate(
            prompt,
            temperature=settings.OLLAMA_SETTINGS.get('TEMPERATURE', 0.7),
            top_p=settings.OLLAMA_SETTINGS.get('TOP_P', 0.9),
            max_tokens=settings.OLLAMA_SETTINGS.get('MAX_TOKENS', 2000)
        )

        # 更新報告內容
        report.content = content
        report.status = 'completed'
        report.save()

        # 保存為文件
        report.save_to_file()

        logger.info(f"報告 {report_id} 生成完成")

    except Exception as e:
        logger.error(f"生成報告 {report_id} 時出錯: {e}", exc_info=True)
        try:
            # 更新報告狀態為失敗
            report = AIReport.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = str(e)
            report.save()
        except:
            pass