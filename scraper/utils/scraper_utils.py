import json
import logging
import os
import random
import re
import time
import threading
import concurrent.futures
from queue import Queue
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse
from django.utils import timezone

import pandas as pd
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# 設定日誌
def setup_logger(output_dir):
    current_date = datetime.now().strftime('%Y%m%d_%H%M_%S')
    os.makedirs(output_dir, exist_ok=True)

    logger = logging.getLogger("scraper")
    logger.setLevel(logging.INFO)

    # 添加文件處理器
    file_handler = logging.FileHandler(
        os.path.join(output_dir, f"ct_scraper_{current_date}.log"))
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(file_handler)

    # 添加控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    logger.addHandler(console_handler)

    return logger


class CTSimpleScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.base_urls = {
            "財經": "https://www.chinatimes.com/money/?chdtv",
            "政治": "https://www.chinatimes.com/politic/?chdtv",
            "社會": "https://www.chinatimes.com/society/?chdtv",
            "科技": "https://www.chinatimes.com/technologynews/?chdtv",
            "國際": "https://www.chinatimes.com/world/?chdtv",
            "娛樂": "https://www.chinatimes.com/star/?chdtv",
            "生活": "https://www.chinatimes.com/life/?chdtv",
            "言論": "https://www.chinatimes.com/opinion/?chdtv",
            "軍事": "https://www.chinatimes.com/armament/?chdtv"
        }
        # 分頁URL模板 - 新增
        self.page_url_templates = {
            "財經": "https://www.chinatimes.com/money/total?page={page}&chdtv",
            "政治": "https://www.chinatimes.com/politic/total?page={page}&chdtv",
            "社會": "https://www.chinatimes.com/society/total?page={page}&chdtv",
            "科技": "https://www.chinatimes.com/technologynews/total?page={page}&chdtv",
            "國際": "https://www.chinatimes.com/world/total?page={page}&chdtv",
            "娛樂": "https://www.chinatimes.com/star/total?page={page}&chdtv",
            "生活": "https://www.chinatimes.com/life/total?page={page}&chdtv",
            "言論": "https://www.chinatimes.com/opinion/total?page={page}&chdtv",
            "軍事": "https://www.chinatimes.com/armament/total?page={page}&chdtv"
        }
        self.category_codes = {
            "財經": "money",
            "政治": "politic",
            "社會": "society",
            "科技": "technology",
            "國際": "world",
            "娛樂": "star",
            "生活": "life",
            "言論": "opinion",
            "軍事": "military"
        }
        self.article_links = {}  # 按類別存儲文章連結
        self.results = []
        self.ua = UserAgent()
        self.user_agent = self.ua.random
        self.cookies = {}
        self.output_dir = None  # 將在run方法中設置
        self.logger = None  # 將在run方法中設置
        self.processed_urls = set()  # 用於儲存已處理過的 URL，防止重複爬取
        self.processed_titles = set()  # 用於儲存已處理過的標題，防止不同URL但相同內容的重複爬取
        self.lock = threading.RLock()  # 線程鎖，用於多線程安全

    def setup_driver(self):
        """設置 undetected-chromedriver"""
        self.logger.info("初始化 undetected-chromedriver...")

        try:
            options = uc.ChromeOptions()

            # 無頭模式
            if self.headless:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")

            # 基本設置
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1366,768")
            options.add_argument(f"--user-agent={self.user_agent}")
            options.add_argument("--lang=zh-TW")

            # 優化記憶體使用
            options.add_argument("--js-flags=--max-old-space-size=512")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-translate")

            # 初始化 undetected_chromedriver
            self.driver = uc.Chrome(options=options)

            # 注入基本的反檢測腳本
            minimal_js = """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            """
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": minimal_js
            })

            self.logger.info("undetected-chromedriver 初始化完成")

        except Exception as e:
            self.logger.error(f"WebDriver 初始化失敗: {e}", exc_info=True)
            try:
                options = uc.ChromeOptions()
                options.add_argument("--no-sandbox")
                options.add_argument(f"--user-agent={self.user_agent}")
                self.driver = uc.Chrome(options=options)
                self.logger.info("備用 WebDriver 初始化成功")
            except Exception as e2:
                self.logger.error(f"備用 WebDriver 初始化也失敗: {e2}", exc_info=True)
                raise

    def simulate_human_behavior(self):
        """簡單的人類行為模擬"""
        try:
            # 隨機滾動
            scroll_amount = random.randint(300, 700)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
            time.sleep(random.uniform(0.3, 0.8))

            # 再滾動一次到不同位置
            scroll_amount = random.randint(800, 1200)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_amount});")
            time.sleep(random.uniform(0.3, 0.8))
        except Exception as e:
            self.logger.error(f"模擬人類行為時發生錯誤: {e}")

    def clean_url(self, url):
        """清理 URL，移除追蹤參數"""
        if not url:
            return None

        # 移除常見追蹤參數
        url = re.sub(r'utm_[^=&]+=[^&]+&?', '', url)
        url = re.sub(r'fbclid=[^&]+&?', '', url)
        url = re.sub(r'[?&]$', '', url)

        # 排除明顯的廣告 URL
        if any(x in url for x in ['tenmax.io', 'bid', 'click', 'ad']):
            return None

        # 確保是中時的 URL
        if 'chinatimes.com' not in url:
            return None

        return url

    def save_cookies(self):
        """儲存 cookies 到文件"""
        try:
            selenium_cookies = self.driver.get_cookies()

            # 儲存到文件
            cookie_path = os.path.join(self.output_dir, f"cookies_{datetime.now().strftime('%Y%m%d')}.json")
            with open(cookie_path, "w", encoding="utf-8") as f:
                json.dump(selenium_cookies, f)

            # 轉換並儲存到內部字典
            for cookie in selenium_cookies:
                self.cookies[cookie['name']] = cookie['value']

        except Exception as e:
            self.logger.error(f"儲存 cookies 時發生錯誤: {e}")

    def load_recent_cookies(self):
        """載入最近的 cookies 文件"""
        try:
            cookie_files = [f for f in os.listdir(self.output_dir) if
                            f.startswith('cookies_') and f.endswith('.json')]
            if not cookie_files:
                # 如果日期目錄沒有，嘗試查看當前目錄
                cookie_files = [f for f in os.listdir('') if f.startswith('cookies_') and f.endswith('.json')]
                if not cookie_files:
                    return False

            # 載入最近的 cookies
            latest_cookie = sorted(cookie_files)[-1]
            cookie_path = os.path.join(self.output_dir, latest_cookie) if os.path.exists(
                os.path.join(self.output_dir, latest_cookie)) else latest_cookie

            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            # 加入到 driver
            for cookie in cookies:
                try:
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    self.driver.add_cookie(cookie)
                    self.cookies[cookie['name']] = cookie['value']
                except Exception as e:
                    pass

            self.logger.info(f"已載入 {len(cookies)} 個 cookies")
            return True

        except Exception as e:
            self.logger.error(f"載入 cookies 時發生錯誤: {e}")
            return False

    def extract_category_from_url(self, url):
        """從 URL 提取新聞類別"""
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path.strip("/").split("/")

            # 從 URL 路徑中提取新聞類別
            for category_code in self.category_codes.values():
                if category_code in path:
                    return category_code

            # 若無法從路徑直接提取，檢查 URL 中的特定字段
            for category_name, category_code in self.category_codes.items():
                if category_code in url:
                    return category_code

            # 默認返回財經類別
            return "money"
        except Exception as e:
            self.logger.error(f"提取新聞類別時出錯: {e}")
            return "money"  # 默認為財經類別

    def extract_date_from_url(self, url):
        """從 URL 提取日期"""
        try:
            # 一般中時新聞 URL 格式: https://www.chinatimes.com/category/YYYYMMDD/id
            match = re.search(r'/(\d{8})/', url)
            if match:
                return match.group(1)
            return datetime.now().strftime('%Y%m%d')
        except Exception as e:
            self.logger.error(f"提取日期時出錯: {e}")
            return datetime.now().strftime('%Y%m%d')

    def generate_item_id(self, url, date_str, category, serial_no):
        """生成文章唯一 ID"""
        try:
            # 格式: 類別代碼_日期_序號
            url_short_name = category
            return f"{url_short_name}_{date_str}_{serial_no}"
        except Exception as e:
            self.logger.error(f"生成 item_id 時出錯: {e}")
            return f"unknown_{date_str}_{serial_no}"

    def scrape_categories(self, categories=None, limit_per_category=5):
        """爬取指定類別的主頁並獲取文章連結，支持翻頁功能"""
        if not categories:
            categories = list(self.base_urls.keys())  # 默認爬取所有類別

        # 用於臨時去重，但不把URL添加到self.processed_urls
        all_urls = set()

        for category in categories:
            if category not in self.base_urls:
                self.logger.warning(f"未知類別: {category}")
                continue

            # 清空此類別的連結列表，準備重新收集
            self.article_links[category] = []

            # 計算需要爬取的頁數
            needed_pages = (limit_per_category + self.articles_per_page - 1) // self.articles_per_page
            self.logger.info(f"類別 {category} 需要爬取 {needed_pages} 頁")

            # 爬取需要的頁數
            for page in range(1, needed_pages + 1):
                # 第一頁使用原始URL，後續頁使用分頁URL模板
                if page == 1:
                    url = self.base_urls[category]
                else:
                    url = self.page_url_templates[category].format(page=page)

                self.logger.info(f"開始爬取 {category} 類別第 {page} 頁: {url}")

                try:
                    self.driver.get(url)

                    # 等待頁面載入
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    # 最小化人類行為模擬
                    self.simulate_human_behavior()

                    # 檢查是否成功載入頁面
                    if "Cloudflare" in self.driver.title:
                        self.logger.warning(f"{category} 類別檢測到 Cloudflare 挑戰頁面")
                        time.sleep(10)
                        if "Cloudflare" in self.driver.title:
                            continue

                    # 使用 CSS 選擇器加速查詢
                    article_elements = self.driver.find_elements(By.CSS_SELECTOR, 'h3.title > a')
                    temp_links = [elem.get_attribute('href') for elem in article_elements]

                    # 清理連結並在內部去重（不影響processed_urls）
                    valid_links = []
                    for link in temp_links:
                        cleaned_link = self.clean_url(link)
                        # 只在當前收集階段去重，不添加到self.processed_urls
                        if cleaned_link and cleaned_link not in all_urls:
                            valid_links.append(cleaned_link)
                            all_urls.add(cleaned_link)  # 僅添加到臨時集合

                    # 添加到該類別的連結列表
                    self.article_links[category].extend(valid_links)

                    self.logger.info(f"{category} 類別第 {page} 頁找到 {len(valid_links)} 個有效且未重複的文章連結")

                    # 加入適當延遲，避免被封鎖
                    time.sleep(random.uniform(1, 3))

                    # 如果已經收集到足夠的連結，提前結束
                    if len(self.article_links[category]) >= limit_per_category:
                        break

                except Exception as e:
                    self.logger.error(f"爬取 {category} 類別第 {page} 頁時發生錯誤: {e}", exc_info=True)

            # 確保每個類別只保留所需數量的連結
            if len(self.article_links[category]) > limit_per_category:
                self.article_links[category] = self.article_links[category][:limit_per_category]

            self.logger.info(f"{category} 類別最終獲取 {len(self.article_links[category])} 個有效且未重複的文章連結")

        # 儲存 cookies (只需儲存一次)
        self.save_cookies()

        # 返回是否成功爬取到文章連結
        return any(len(links) > 0 for links in self.article_links.values())

    def extract_photo_links(self, category):
        """提取文章中的圖片連結"""
        try:
            # 嘗試提取所有圖片連結
            photo_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.article-body img')
            photo_links = [img.get_attribute('src') for img in photo_elements if img.get_attribute('src')]

            # 過濾掉 GIF 和廣告圖片
            filtered_links = [link for link in photo_links if
                              link and not ('gif' in link.lower() or 'ad' in link.lower())]

            return filtered_links
        except Exception as e:
            self.logger.error(f"提取圖片連結時出錯: {e}")
            return []

    def scrape_article_selenium(self, url, category, serial_no):
        """使用 Selenium 爬取單篇文章"""
        # 創建每個線程專屬的WebDriver實例
        local_driver = None

        try:
            # 使用線程鎖檢查URL和標題是否已經處理過
            with self.lock:
                if url in self.processed_urls:
                    self.logger.info(f"跳過已處理的文章URL: {url}")
                    return None

            # 初始化每個線程自己的WebDriver，避免共享問題
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument(f"--user-agent={UserAgent().random}")

            local_driver = uc.Chrome(options=options)

            self.logger.info(f"開始爬取文章: {url}")
            local_driver.get(url)

            # 等待文章標題載入
            WebDriverWait(local_driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.article-title'))
            )

            # 提取文章資訊 (使用 CSS 選擇器)
            title_elem = local_driver.find_element(By.CSS_SELECTOR, 'h1.article-title')
            title = title_elem.text.strip() if title_elem else "未找到標題"

            # 檢查標題是否已處理過（避免不同URL但內容相同的情況）
            with self.lock:
                if title in self.processed_titles:
                    self.logger.info(f"跳過已處理的文章標題: {title}")
                    if local_driver:
                        local_driver.quit()
                    return None

                # 標記URL和標題為已處理
                self.processed_urls.add(url)
                self.processed_titles.add(title)

            # 最小化人類行為模擬
            scroll_height = 300
            local_driver.execute_script(f"window.scrollTo(0, {scroll_height});")
            time.sleep(0.5)

            date_elem = local_driver.find_element(By.CSS_SELECTOR, 'div.meta-info time')
            date = date_elem.get_attribute('datetime') if date_elem else "未找到日期"

            # 提取作者資訊
            author_elems = local_driver.find_elements(By.CSS_SELECTOR, 'div.author a')
            author = [a.text.strip() for a in author_elems] if author_elems else ["未找到作者"]

            # 提取內文
            content_elems = local_driver.find_elements(By.CSS_SELECTOR, 'div.article-body p')
            content = "\n".join([p.text.strip() for p in content_elems]) if content_elems else "未找到內容"

            # 提取圖片連結 - 使用local_driver而不是self.driver
            photo_elements = local_driver.find_elements(By.CSS_SELECTOR, 'div.article-body img')
            photo_links = [img.get_attribute('src') for img in photo_elements if img.get_attribute('src')]
            filtered_links = [link for link in photo_links if
                              link and not ('gif' in link.lower() or 'ad' in link.lower())]

            # 提取日期用於 item_id
            date_str = self.extract_date_from_url(url)

            # 生成 item_id
            category_code = self.category_codes.get(category, self.extract_category_from_url(url))
            item_id = self.generate_item_id(url, date_str, category_code, serial_no)

            return {
                "item_id": item_id,
                "category": category,
                "date": date,
                "author": author,
                "title": title,
                "content": content,
                "link": url,
                "photo_links": filtered_links
            }
        except Exception as e:
            self.logger.error(f"爬取文章 {url} 失敗: {e}")
            return None
        finally:
            # 確保每個線程的WebDriver都能被關閉
            if local_driver:
                try:
                    local_driver.quit()
                except:
                    pass

    def scrape_articles(self, limit_per_category=5, use_threading=False, max_workers=4):
        """爬取每個類別的文章內容

        Args:
            limit_per_category (int): 每個類別最多爬取的文章數量
            use_threading (bool): 是否使用多線程處理
            max_workers (int): 最大線程數量

        Returns:
            bool: 是否成功爬取到文章
        """
        results = []

        if use_threading:
            self.logger.info(f"使用多線程進行文章爬取，最大線程數: {max_workers}")

            # 準備所有需要爬取的連結及對應資訊
            all_tasks = []
            for category, links in self.article_links.items():
                if not links:
                    continue

                category_links = links[:limit_per_category]
                for i, link in enumerate(category_links):
                    all_tasks.append((link, category, i + 1))

            # 使用線程池並行處理
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 建立任務字典，將每個任務映射到相應的 future 對象
                future_to_url = {
                    executor.submit(self.scrape_article_selenium, link, category, serial_no): (
                        link, category, serial_no)
                    for link, category, serial_no in all_tasks
                }

                # 收集結果
                for future in concurrent.futures.as_completed(future_to_url):
                    link, category, serial_no = future_to_url[future]
                    try:
                        article_data = future.result()
                        if article_data:
                            with self.lock:  # 使用鎖保護對results的訪問
                                results.append(article_data)
                            self.logger.info(f"成功爬取 {category} 類別的文章: {article_data['title']}")
                    except Exception as e:
                        self.logger.error(f"爬取文章 {link} 時發生異常: {e}")
        else:
            # 原有的單線程處理邏輯
            for category, links in self.article_links.items():
                if not links:
                    continue

                self.logger.info(f"開始爬取 {category} 類別的文章")
                category_links = links[:limit_per_category]

                for i, link in enumerate(category_links):
                    # 嘗試爬取文章
                    article_data = self.scrape_article_selenium(link, category, i + 1)
                    if article_data:
                        results.append(article_data)
                        self.logger.info(f"成功爬取 {category} 類別的文章: {article_data['title']}")

                    # 增加隨機等待時間，避免被封鎖
                    time.sleep(random.uniform(1, 3))

        self.results.extend(results)
        return len(results) > 0

    def save_results(self):
        """將結果保存到JSON文件"""
        if not self.results:
            self.logger.warning("沒有結果可保存")
            return False

        filename = os.path.join(self.output_dir, f"ct_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"結果已保存到: {filename}")
            return True
        except Exception as e:
            self.logger.error(f"保存結果時發生錯誤: {e}", exc_info=True)
            return False

    def run(self, categories=None, limit_per_category=5, max_retries=2, use_threading=False, max_workers=4,
            output_dir=None):
        """運行爬蟲流程

        Args:
            categories (list): 要爬取的新聞類別列表，預設爬取全部類別
            limit_per_category (int): 每個類別最多爬取的文章數量
            max_retries (int): 最大重試次數
            use_threading (bool): 是否使用多線程爬取文章
            max_workers (int): 多線程模式下的最大線程數
            output_dir (str): 輸出目錄，默認使用當前日期時間

        Returns:
            bool: 爬蟲是否成功完成
        """
        try:
            # 每次執行時重置已處理 URL 和標題集合
            self.processed_urls = set()
            self.processed_titles = set()

            # 設置輸出目錄
            if output_dir is None:
                current_date = datetime.now().strftime('%Y%m%d_%H%M_%S')
                output_dir = os.path.join(os.getcwd(), "output", current_date)

            os.makedirs(output_dir, exist_ok=True)
            self.output_dir = output_dir

            # 設置日誌
            self.logger = setup_logger(output_dir)
            self.logger.info(f"爬蟲輸出目錄: {output_dir}")

            # 設置 WebDriver
            self.setup_driver()

            # 嘗試載入已有的 cookies
            self.load_recent_cookies()

            # 爬取多個類別的主頁，使用指數退避策略
            success = False
            retry_count = 0
            wait_time = 5  # 初始等待 5 秒

            while not success and retry_count < max_retries:
                success = self.scrape_categories(categories)
                if not success:
                    retry_count += 1
                    self.logger.warning(f"主頁爬取失敗，嘗試重試 ({retry_count}/{max_retries})")
                    # 指數退避策略
                    wait_time = min(30, wait_time * 2)  # 最多等待 30 秒
                    time.sleep(wait_time)

            if not success:
                self.logger.error("主頁爬取失敗，已達最大重試次數，終止程序")
                return False

            # 使用 Selenium 爬取文章，可選擇是否使用多線程
            if not self.scrape_articles(limit_per_category, use_threading, max_workers):
                self.logger.error("文章爬取失敗，終止程序")
                return False

            # 保存結果
            self.save_results()

            # 處理關鍵詞分析
            self.logger.info("開始文本處理與分析")
            processor = CTTextProcessor(self.output_dir)
            processor.process_articles(self.results)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"爬蟲運行過程中發生錯誤: {e}", exc_info=True)
            else:
                print(f"爬蟲運行過程中發生錯誤: {e}")
            return False

        finally:
            # 關閉瀏覽器
            if self.driver:
                self.driver.quit()
                if self.logger:
                    self.logger.info("已關閉瀏覽器")


class CTTextProcessor:
    """中時新聞文本處理類

    用於對爬取的新聞進行斷詞分析與預處理，使用中研院 CKIP 斷詞工具
    """

    def __init__(self, output_dir):
        """初始化文本處理器，使用中研院斷詞套件"""
        self.logger = logging.getLogger("scraper.processor")
        self.stop_words = set()
        self.output_dir = output_dir  # 儲存輸出目錄
        # 指定要篩選的詞性 (Na:普通名詞, Nb:專有名詞, Nc:地方名詞)
        self.target_pos = {'Na', 'Nb', 'Nc'}
        # 最短關鍵字長度限制
        self.min_keyword_length = 2

        # 初始化中研院斷詞工具
        try:
            from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger, CkipNerChunker
            self.logger.info("使用中研院 CKIP Transformers 進行斷詞")
            # 使用 albert-tiny 模型以提高效能
            self.ws = CkipWordSegmenter(model="albert-tiny")
            self.pos = CkipPosTagger(model="albert-tiny")
            self.ner = CkipNerChunker(model="albert-tiny")
        except ImportError:
            self.logger.warning("未安裝中研院斷詞套件，使用簡易分詞模式")
            self.ws = None
            self.pos = None
            self.ner = None

        # 載入停用詞
        self.load_stop_words()

    def load_stop_words(self, file_path=None):
        """載入停用詞表

        Args:
            file_path (str, optional): 停用詞檔案路徑，預設為None使用內建設定
        """
        try:
            if file_path and os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        self.stop_words.add(line.strip())
                self.logger.info(f"已載入 {len(self.stop_words)} 個停用詞")
            else:
                # 使用基本停用詞
                basic_stop_words = [
                    '的', '了', '和', '是', '就', '都', '而', '及', '與', '著',
                    '或', '一個', '沒有', '因為', '但是', '所以', '如果', '，', '。',
                    '、', '；', '：', '！', '？', '"', '"', ''', ''', '（', '）',
                    '【', '】', '[', ']', '{', '}', '「', '」', '《', '》', '／',
                    '(', ')', '／', '／', '／', '／', '／', '…', '..', '...', '等',
                    '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                    '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                    '有', '會', '他', '她', '我', '你', '它'
                ]
                self.stop_words = set(basic_stop_words)
                self.logger.info(f"使用預設停用詞 {len(self.stop_words)} 個")
        except Exception as e:
            self.logger.error(f"載入停用詞失敗: {e}")

    def segment_text(self, text):
        """使用中研院斷詞工具進行斷詞

        Args:
            text (str): 要斷詞的文本

        Returns:
            list: 斷詞結果列表，僅包含目標詞性且長度符合要求的詞
        """
        if not text or len(text.strip()) == 0:
            return []

        try:
            # 檢查是否有可用的斷詞工具
            if self.ws is None or self.pos is None:
                # 使用簡易斷詞方法（僅作為備用）
                words = text.replace('\n', '').split(' ')
                return [(w, 'Na') for w in words if
                        w and len(w) >= self.min_keyword_length and w not in self.stop_words]

            # 使用中研院斷詞
            ws_results = self.ws([text])
            pos_results = self.pos(ws_results)

            # 合併結果
            words = ws_results[0]
            pos_tags = pos_results[0]

            # 過濾停用詞、指定詞性及長度
            filtered_words = []
            for w, p in zip(words, pos_tags):
                # 僅保留指定詞性(Na,Nb,Nc)、長度>=2且不在停用詞表的詞
                if (w.strip() and
                        w not in self.stop_words and
                        p in self.target_pos and
                        len(w) >= self.min_keyword_length):
                    filtered_words.append((w, p))  # 保留詞性標籤

            return filtered_words
        except Exception as e:
            self.logger.error(f"斷詞失敗: {e}")
            return []

    def identify_named_entities(self, text):
        """識別文本中的命名實體

        Args:
            text (str): 文本內容

        Returns:
            list: 命名實體列表
        """
        try:
            if self.ner is None:
                self.logger.warning("未初始化CKIP NER模型，無法識別命名實體")
                return []

            # 確保輸入文字不為空
            if not text or len(text.strip()) == 0:
                return []

            # 使用CKIP進行命名實體識別
            ner_results = self.ner([text])
            self.logger.info(f"識別出 {len(ner_results[0])} 個命名實體")
            return ner_results[0]
        except Exception as e:
            self.logger.error(f"命名實體識別失敗: {e}", exc_info=True)
            return []

    def process_named_entities(self, articles):
        """處理命名實體並輸出分析結果

        Args:
            articles (list): 文章列表

        Returns:
            dict: 按類別組織的命名實體統計
        """
        # 按類別分組
        category_articles = defaultdict(list)
        for article in articles:
            category = article.get("category", "未知")
            category_articles[category].append(article)

        # 存儲每個類別的命名實體與詞頻結果
        category_entities = {}

        # 對每個類別進行分析
        for category, category_data in category_articles.items():
            self.logger.info(f"分析 {category} 類別的 {len(category_data)} 篇文章命名實體")

            # 合併該類別所有文章內容
            category_text = ""
            for article in category_data:
                category_text += article.get("content", "") + "\n"

            # 使用CKIP NER分析
            named_entities = self.identify_named_entities(category_text)

            # 統計實體頻率
            entity_freq = defaultdict(int)
            entity_type_map = {}  # 記錄每個實體的類型

            for entity in named_entities:
                entity_key = f"{entity.word}_{entity.ner}"  # 使用實體+類型作為唯一鍵
                entity_freq[entity_key] += 1
                entity_type_map[entity_key] = {"entity": entity.word, "type": entity.ner}

            # 轉換為排序列表
            entities_with_freq = []
            for entity_key, freq in sorted(entity_freq.items(), key=lambda x: x[1], reverse=True):
                entity_info = entity_type_map[entity_key]
                entities_with_freq.append({
                    "entity": entity_info["entity"],
                    "entity_type": entity_info["type"],
                    "frequency": freq,
                    "category": category
                })

            category_entities[category] = entities_with_freq

        return category_entities

    def extract_keywords(self, words_with_pos, topK=20):
        """根據詞性和詞頻提取關鍵詞

        Args:
            words_with_pos (list): 帶詞性標籤的詞列表
            topK (int): 提取前K個關鍵詞

        Returns:
            list: 關鍵詞列表
        """
        # 計算詞頻
        word_freq = {}
        for word, pos in words_with_pos:
            # 只有指定詞性的詞才會在words_with_pos中，所以不需要額外檢查
            word_freq[word] = word_freq.get(word, 0) + 1

        # 排序
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # 返回前 topK 個關鍵詞
        return sorted_words[:topK]

    def analyze_by_category(self, articles):
        """按類別分析文章關鍵字和詞頻

        Args:
            articles (list): 文章列表

        Returns:
            dict: 按類別組織的關鍵詞統計
        """
        # 按類別分組
        category_articles = defaultdict(list)
        for article in articles:
            category = article.get("category", "未知")
            category_articles[category].append(article)

        # 存儲每個類別的關鍵詞與詞頻結果
        category_keywords = {}

        # 對每個類別進行分析
        for category, category_data in category_articles.items():
            self.logger.info(f"分析 {category} 類別的 {len(category_data)} 篇文章")

            # 合併該類別所有文章內容
            category_text = ""
            for article in category_data:
                category_text += article.get("content", "") + "\n"

            # 使用CKIP斷詞與詞性標註 (已篩選符合條件的詞)
            segmented_words_with_pos = self.segment_text(category_text)

            # 統計詞性與頻率
            word_pos_freq = defaultdict(int)
            word_pos_map = {}  # 記錄每個詞的詞性

            for word, pos in segmented_words_with_pos:
                word_pos_key = f"{word}_{pos}"  # 使用詞+詞性作為唯一鍵
                word_pos_freq[word_pos_key] += 1
                word_pos_map[word_pos_key] = {"word": word, "pos": pos}

            # 轉換為排序列表
            keywords_with_pos_freq = []
            for word_pos_key, freq in sorted(word_pos_freq.items(), key=lambda x: x[1], reverse=True):
                word_info = word_pos_map[word_pos_key]
                keywords_with_pos_freq.append({
                    "word": word_info["word"],
                    "pos": word_info["pos"],
                    "frequency": freq
                })

            category_keywords[category] = keywords_with_pos_freq

        return category_keywords

    def analyze_articles(self, articles):
        """分析文章集合

        Args:
            articles (list): 文章字典列表

        Returns:
            dict: 分析結果
        """
        if not articles:
            return {"error": "沒有文章可分析"}

        # 合併所有文章內容作為語料庫
        corpus = ""
        for article in articles:
            if "content" in article and article["content"]:
                corpus += article["content"] + "\n"

        # 斷詞結果（包含詞性標籤，只有符合條件的詞）
        segmented_corpus_with_pos = self.segment_text(corpus)

        # 提取只有詞的列表（用於計算總詞數）
        segmented_corpus = [word for word, _ in segmented_corpus_with_pos]

        # 詞頻統計（只根據詞）
        word_freq = {}
        for word in segmented_corpus:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 排序詞頻
        sorted_word_freq = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

        # 根據詞性和詞頻提取關鍵詞
        keywords = self.extract_keywords(segmented_corpus_with_pos)

        # 命名實體識別
        named_entities = self.identify_named_entities(corpus)

        # 按類別分析關鍵詞統計
        category_keywords_stats = self.analyze_by_category(articles)

        # 按類別分析命名實體統計
        category_entities_stats = self.process_named_entities(articles)

        # 獲取每篇文章的關鍵詞和命名實體
        articles_analysis = []
        for article in articles:
            if "content" in article and article["content"]:
                title = article.get("title", "未知標題")
                article_words_with_pos = self.segment_text(article["content"])
                article_keywords = self.extract_keywords(article_words_with_pos, topK=10)
                article_entities = self.identify_named_entities(article["content"])

                articles_analysis.append({
                    "title": title,
                    "keywords": article_keywords,
                    "named_entities": [{'entity': entity.word, 'entity_type': entity.ner} for entity in
                                       article_entities]
                })

        result = {
            "total_articles": len(articles),
            "total_words": len(segmented_corpus),
            "unique_words": len(word_freq),
            "top_words": sorted_word_freq[:50],  # 前50個高頻詞
            "keywords": keywords,
            "named_entities": [{'entity': entity.word, 'entity_type': entity.ner} for entity in named_entities],
            "articles_analysis": articles_analysis,
            "category_keywords_stats": category_keywords_stats,  # 按類別的關鍵詞統計
            "category_entities_stats": category_entities_stats  # 按類別的命名實體統計
        }

        return result

    def save_analysis_result(self, result, output_file=None):
        """保存分析結果到檔案，只輸出所需的分析結果

        Args:
            result (dict): 分析結果
            output_file (str, optional): 輸出檔案路徑，如果不指定，將使用預設路徑
        """
        try:
            # 保存類別關鍵詞統計結果到JSON，並轉換為扁平化結構
            if "category_keywords_stats" in result:
                category_keywords_file = os.path.join(self.output_dir, "category_keywords_stats.json")

                # 將巢狀結構轉換為扁平化列表
                flat_keywords = []
                for category, keywords in result["category_keywords_stats"].items():
                    for keyword in keywords:
                        # 將類別資訊加入每個關鍵詞項目
                        keyword_with_category = keyword.copy()
                        keyword_with_category["category"] = category
                        flat_keywords.append(keyword_with_category)

                # 寫入扁平化結構到檔案
                with open(category_keywords_file, 'w', encoding='utf-8') as f:
                    json.dump(flat_keywords, f, ensure_ascii=False, indent=2)
                self.logger.info(f"類別關鍵詞統計已保存到: {category_keywords_file}")

            # 保存類別命名實體統計結果到JSON，並轉換為扁平化結構
            if "category_entities_stats" in result:
                category_entities_file = os.path.join(self.output_dir, "category_entities_stats.json")

                # 將巢狀結構轉換為扁平化列表
                flat_entities = []
                for category, entities in result["category_entities_stats"].items():
                    for entity in entities:
                        # 確保每個實體項目都已包含類別資訊
                        flat_entities.append(entity)

                # 寫入扁平化結構到檔案
                with open(category_entities_file, 'w', encoding='utf-8') as f:
                    json.dump(flat_entities, f, ensure_ascii=False, indent=2)
                self.logger.info(f"類別命名實體統計已保存到: {category_entities_file}")

            return True
        except Exception as e:
            self.logger.error(f"保存分析結果時發生錯誤: {e}")
            return False

    def process_articles(self, articles, output_dir=None):
        """處理文章集合並輸出結果，只輸出必要的分析結果

        Args:
            articles (list): 文章字典列表
            output_dir (str, optional): 輸出目錄，不指定則使用初始化時設定的目錄

        Returns:
            bool: 是否成功處理
        """
        try:
            # 使用指定的輸出目錄
            if output_dir is not None:
                self.output_dir = output_dir

            # 確保輸出目錄存在
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            self.logger.info(f"將保存結果到目錄: {self.output_dir}")
            self.logger.info(
                f"只保存包含目標詞性({', '.join(self.target_pos)})且長度>={self.min_keyword_length}的關鍵詞統計")

            # 分析文章
            analysis_result = self.analyze_articles(articles)

            # 保存分析結果（只保存主要的關鍵詞統計）
            self.save_analysis_result(analysis_result)

            self.logger.info(f"所有處理結果已保存到目錄: {self.output_dir}")
            return True
        except Exception as e:
            self.logger.error(f"處理文章時發生錯誤: {e}")
            return False


# 當直接執行此模組時的測試代碼
if __name__ == "__main__":
    print("這是中時新聞爬蟲模組，應當被導入使用而非直接執行")