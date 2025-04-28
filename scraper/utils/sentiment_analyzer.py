from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import logging
import os
from opencc import OpenCC
import numpy as np

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """繁體中文情感分析器"""

    def __init__(self, model_name="uer/roberta-base-finetuned-dianping-chinese", cache_dir=None):
        """
        初始化情感分析器

        Args:
            model_name: 預訓練模型名稱，預設使用 uer/roberta-base-finetuned-dianping-chinese
            cache_dir: 模型快取目錄，預設為None
        """
        self.logger = logging.getLogger(__name__)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"使用設備: {self.device}")

        # 簡繁轉換工具
        self.t2s = OpenCC('t2s')  # 繁體轉簡體
        self.s2t = OpenCC('s2t')  # 簡體轉繁體

        try:
            # 載入預訓練模型和 tokenizer
            self.logger.info(f"正在載入模型 {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name, cache_dir=cache_dir)
            self.model.to(self.device)
            self.model.eval()  # 設定為評估模式
            self.logger.info("模型載入完成")
        except Exception as e:
            self.logger.error(f"模型載入失敗: {e}", exc_info=True)
            raise

    def analyze(self, text, max_length=512):
        """
        分析文本情感

        Args:
            text: 要分析的文本
            max_length: 文本最大長度，超過會被截斷

        Returns:
            dict: 包含情感分析結果的字典，格式為 {'positive': 0.xx, 'negative': 0.xx, 'sentiment': '正面/負面'}
        """
        try:
            # 繁體轉簡體，因為大多數預訓練模型是用簡體中文訓練的
            simplified_text = self.t2s.convert(text)

            # 準備輸入
            inputs = self.tokenizer(
                simplified_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=max_length
            )

            # 將輸入移到指定設備
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 關閉梯度計算以提高效率
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

                # 獲取預測結果
                probabilities = torch.nn.functional.softmax(logits, dim=1)
                probabilities = probabilities.cpu().numpy()[0]

            # 假設標籤0為負面，標籤1為正面
            # 由於不同模型的標籤順序可能不同，這裡需要根據實際模型調整
            negative_prob = float(probabilities[0])
            positive_prob = float(probabilities[1])

            # 確定情感傾向與中立判斷邏輯
            if 0.3 <= positive_prob <= 0.7 and 0.3 <= negative_prob <= 0.7:
                sentiment = "中立"
            else:
                sentiment = "正面" if positive_prob > negative_prob else "負面"

            return {
                "positive": positive_prob,
                "negative": negative_prob,
                "sentiment": sentiment
            }

        except Exception as e:
            self.logger.error(f"情感分析失敗: {e}", exc_info=True)
            # 返回一個默認的中性結果
            return {
                "positive": 0.5,
                "negative": 0.5,
                "sentiment": "中性"
            }

    def batch_analyze(self, texts, batch_size=16, max_length=512):
        """
        批次分析多個文本

        Args:
            texts: 文本列表
            batch_size: 批次大小
            max_length: 文本最大長度

        Returns:
            list: 包含每個文本分析結果的列表
        """
        results = []

        # 批次處理
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = [self.analyze(text, max_length) for text in batch_texts]
            results.extend(batch_results)

        return results


# 簡單的測試函數
def test_sentiment_analyzer():
    """測試情感分析器功能"""
    analyzer = SentimentAnalyzer()

    test_texts = [
        "這部電影真是太棒了，我非常喜歡！",
        "服務態度很差，完全不推薦這家餐廳",
        "這個產品品質一般，但價格便宜"
    ]

    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"文本: {text}")
        print(f"分析結果: {result}")
        print("-" * 50)


if __name__ == "__main__":
    # 設置日誌
    logging.basicConfig(level=logging.INFO)
    # 執行測試
    test_sentiment_analyzer()