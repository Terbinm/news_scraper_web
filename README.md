# 新聞爬蟲與全文檢索關聯分析系統

## 專案概述

本專案是一個基於Django的新聞爬蟲與分析系統，主要功能包括從中時電子報(China Times)抓取新聞文章，進行中文自然語言處理分析，並提供全文檢索、關鍵詞分析、命名實體識別、情感分析以及領導人物提及分析等功能。系統使用了現代化的前後端技術，實現了新聞資料的自動抓取、存儲、分析與可視化。

本項目代碼託管於 GitHub：[https://github.com/Terbinm/news_scraper_web](https://github.com/Terbinm/news_scraper_web)


## 系統展示

太好了！以下是完整版本的 **系統展示文件（含圖片語法與說明文字）**，涵蓋了你**原本列出的6個頁面**，再加上我剛剛幫你補齊的 **登入頁、任務列表、文章詳情、AI報告、情感分析與領導人物比較** 等所有視圖。

---

## 系統展示

---


### 登入頁面
![登入頁面](images/login.png)

登入頁面是系統的入口，使用者需輸入帳號與密碼以登入系統。若驗證失敗，系統會提示錯誤訊息。登入成功後自動導向爬蟲任務總覽頁面。

### 爬蟲任務創建頁面
![爬蟲任務創建頁面](images/task_create.png)

此頁面允許用戶選擇要爬取的新聞類別、設定每類文章數量上限，以及是否啟用多線程加速爬取。提交後將自動啟動爬蟲任務並顯示進度。

### 任務概覽頁面
![任務概覽頁面](images/task_overview.png)

展示特定爬蟲任務的基本統計資訊，包括文章總數、各類別文章分布、關鍵詞與命名實體數量。可從此頁面導向各分析模組。

### 文章列表頁面
![文章列表頁面](images/job_articles.png)

列出指定任務下的所有文章，支援依標題、日期排序、分類與關鍵字查詢。若文章已完成摘要，將一併顯示摘要資訊與分析狀態。

### 文章詳情頁面
![文章詳情頁面](images/article_detail.png)

提供文章標題、內文、作者與發布日期等詳細內容，並可觸發單篇情感分析與摘要產生。若已有分析結果，也會同步展示。

### 關鍵詞分析頁面

![關鍵詞分析頁面](images/keywords_analysis.png)

顯示文章中出現的關鍵詞，支援依分類與詞性過濾，並提供圖表與表格檢視模式。可用來觀察不同類別之間的關鍵詞差異。

### 命名實體分析頁面
![命名實體分析頁面](images/entities_analysis.png)

展示文章中抽取的人物、地點、組織等命名實體，並支援類型與頻率篩選。可辨識各類文章中提及的核心實體。

### 進階搜尋頁面
![進階搜尋頁面](images/advanced_search.png)

本系統的核心功能之一，支援複合條件查詢、時間範圍、分類、實體與關鍵詞篩選等多元條件設定。並提供時間趨勢圖、共現關係圖等多樣視覺化分析。

### 情感分析頁面
![情感分析頁面](images/sentiment_analysis.png)

展示文章的整體情感分布（正面、中立、負面），並可查看各分類的情緒概況與變化趨勢。亦可檢視情感分數最高與最低的代表文章。

### 領導人物分析頁面
![領導人物分析頁面](images/leader_analysis.png)

針對特定人物（如政治領袖）進行新聞分析，顯示其在新聞中被提及的頻率、主題類型、情感分布與時間趨勢，協助掌握輿論動向。

### 領導人物比較分析頁面
![領導人物比較分析頁面](images/leader_compare.png)

支援多位人物交叉分析，顯示其文章數、出現次數、情緒分布與類別差異。並以多條時間趨勢圖比較各人物的關注度與情感變化。

### AI 報告總覽頁面
![AI報告總覽頁面](images/ai_report_list.png)

列出所有由 AI 自動生成的報告，包含分析標題、時間、狀態與操作選項（如重新生成、刪除與下載）。方便快速管理分析內容。

### AI 報告詳情頁面
![AI報告詳情頁面](images/ai_report_detail.png)

提供完整 AI 分析報告的閱讀介面，採用 Markdown 轉換成 HTML 呈現，便於閱讀與理解。支援下載 Markdown 檔案以供離線參考。

### 摘要分析頁面
![摘要分析頁面](images/summary_analysis.png)

展示爬蟲任務中所有文章的摘要分析狀況，包括未完成/失敗數、完成摘要內容、生成時間與摘要長度等資訊，支援手動重新生成。



### 主要特點

- **多類別新聞爬取**：支援財經、政治、社會等9個類別的新聞抓取
- **自然語言處理**：使用CKIP中文斷詞系統進行文本分析
- **全文檢索引擎**：支援複雜查詢條件與多維度分析
- **情感分析**：使用預訓練模型分析文章情感傾向
- **數據可視化**：使用Chart.js等工具直觀展示分析結果
- **領導人物分析**：針對特定領導人物進行關注度與情感傾向分析
- **多用戶支援**：基於Django認證系統，支援多用戶獨立資料管理

## 系統架構

### 技術棧

- **後端框架**：Django 4.2
- **前端技術**：Bootstrap 5、Chart.js、D3.js
- **資料庫**：SQLite（開發環境）/ PostgreSQL（生產環境）
- **爬蟲技術**：Selenium、undetected-chromedriver
- **NLP工具**：CKIP Transformers、HuggingFace Transformers
- **情感分析**：基於RoBERTa的預訓練模型

### 系統模組

```mermaid
flowchart TD
    %% User Interface Layer
    subgraph "User Interface" 
        Browser["User Browser"]:::external
    end

    %% Web Application Layer
    subgraph "Web Layer" 
        DjangoServer["Django Server (ASGI/WSGI)"]:::web
        URLRouter["URL Router"]:::web
        Views["Views (scraper/views.py)"]:::web
        Templates["Templates"]:::web
        StaticAssets["Static Assets (CSS/JS)"]:::web
        Browser -->|"HTTP Request"| DjangoServer
        DjangoServer -->|"routes to"| URLRouter
        URLRouter -->|"calls"| Views
        Views -->|"renders"| Templates
        Views -->|"serves"| StaticAssets
    end

    %% Service Layer
    subgraph "Services Layer" 
        ScraperService["ScraperService"]:::service
        AnalysisService["AnalysisService"]:::service
        SentimentService["SentimentService"]:::service
        SearchService["SearchService"]:::service
        TaskService["TaskService"]:::service
    end

    %% Background Task Layer
    subgraph "Background Layer" 
        CeleryWorker["Celery Worker"]:::background
        RedisBroker["Redis (Broker & Cache)"]:::data
        Views -->|"trigger task"| TaskService
        TaskService -->|"enqueue"| CeleryWorker
        CeleryWorker -->|"uses"| ScraperService
        CeleryWorker -->|"uses"| AnalysisService
        CeleryWorker -->|"uses"| SentimentService
        CeleryWorker -->|"uses"| SearchService
        CeleryWorker -->|"publishes"| RedisBroker
    end

    %% Data Layer
    subgraph "Data Layer" 
        Database["Database (SQLite/PostgreSQL)"]:::data
        Media["Media Storage"]:::data
        Cache["Redis Cache"]:::data
        ScraperService -->|"writes Article, ScrapeJob"| Database
        AnalysisService -->|"writes Analysis tables"| Database
        SentimentService -->|"writes Sentiment tables"| Database
        SearchService -->|"queries"| Database
        SearchService -->|"reads/writes"| Cache
    end

    %% External Dependencies
    subgraph "External Services" 
        ChinaTimes["China Times Website"]:::external
        CKIP["CKIP Transformers"]:::external
        HFModels["HuggingFace Models"]:::external
        ScraperService -->|"crawls"| ChinaTimes
        AnalysisService -->|"calls"| CKIP
        SentimentService -->|"loads"| HFModels
    end

    %% Search flow back to UI
    SearchService -->|"returns data"| Views
    Views -->|"JSON/HTML"| Browser

    %% Click Events
    click DjangoServer "https://github.com/terbinm/news_scraper_web/blob/master/news_scraper_web/asgi.py"
    click DjangoServer "https://github.com/terbinm/news_scraper_web/blob/master/news_scraper_web/wsgi.py"
    click URLRouter "https://github.com/terbinm/news_scraper_web/blob/master/news_scraper_web/urls.py"
    click Views "https://github.com/terbinm/news_scraper_web/blob/master/scraper/views.py"
    click Templates "https://github.com/terbinm/news_scraper_web/blob/master/templates/base.html"
    click Templates "https://github.com/terbinm/news_scraper_web/blob/master/templates/scraper/*.html"
    click StaticAssets "https://github.com/terbinm/news_scraper_web/blob/master/static/css/main.css"
    click StaticAssets "https://github.com/terbinm/news_scraper_web/blob/master/static/js/main.js"
    click ScraperService "https://github.com/terbinm/news_scraper_web/blob/master/scraper/services/scraper_service.py"
    click AnalysisService "https://github.com/terbinm/news_scraper_web/blob/master/scraper/services/analysis_service.py"
    click SentimentService "https://github.com/terbinm/news_scraper_web/blob/master/scraper/services/sentiment_service.py"
    click SearchService "https://github.com/terbinm/news_scraper_web/blob/master/scraper/services/search_service.py"
    click TaskService "https://github.com/terbinm/news_scraper_web/blob/master/scraper/services/task_service.py"
    click RedisBroker "https://github.com/terbinm/news_scraper_web/blob/master/requirements.txt"
    click Database "https://github.com/terbinm/news_scraper_web/blob/master/database-erd.mermaid"
    click Views "https://github.com/terbinm/news_scraper_web/blob/master/scraper/urls.py"
    click Views "https://github.com/terbinm/news_scraper_web/blob/master/scraper/forms.py"
    click Views "https://github.com/terbinm/news_scraper_web/blob/master/scraper/api.py"
    click Views "https://github.com/terbinm/news_scraper_web/blob/master/scraper/admin.py"
    click CeleryWorker "https://github.com/terbinm/news_scraper_web/blob/master/scraper/tasks.py"

    %% Styles
    classDef web fill:#b3d7ff,stroke:#036,stroke-width:1px
    classDef service fill:#c2f0c2,stroke:#070,stroke-width:1px
    classDef background fill:#ffd9b3,stroke:#f60,stroke-width:1px
    classDef data fill:#e0e0e0,stroke:#666,stroke-width:1px
    classDef external fill:#e6ccff,stroke:#704,stroke-width:1px
 ```

### 項目目錄結構

```
news_scraper_web/
├── .gitignore                       # Git 忽略設定檔，排除不需追蹤的檔案（如 __pycache__/、db.sqlite3 等）
├── db.sqlite3                       # SQLite 資料庫檔案，儲存系統資料
├── manage.py                        # Django 專案的管理工具，可用來執行 migrate、runserver 等指令
├── README.md                        # 專案說明文件，提供使用說明與架構簡介
├── requirements.txt                # Python 套件需求清單，用於建立環境
├── images/                          # 系統展示截圖資料夾（自定義），用於說明文件或README中插圖
├── media/                           # 使用者上傳資料與AI生成報告存放位置
│   ├── ai_reports/                  # 存放由 AI 產生的 Markdown 報告檔
│   │   ├── report_XX.md            # 單份 AI 分析報告（Markdown 格式）
│   ├── models/                      # 可用於存放上傳模型檔、圖像等資料（目前尚未細列）
├── news_scraper_web/               # Django 專案設定目錄（與專案同名）
│   ├── asgi.py                      # ASGI 進入點，用於非同步部署
│   ├── settings.py                  # 專案設定檔，包括資料庫、靜態檔、應用註冊等
│   ├── urls.py                      # 專案 URL 路由總入口
│   ├── wsgi.py                      # WSGI 進入點，用於部署至傳統伺服器
│   ├── __init__.py                  # 專案模組初始化
├── scraper/                         # 系統核心 app，負責新聞爬蟲、分析、UI、API 等
│   ├── admin.py                     # Django 後台管理設定
│   ├── api.py                       # 若有提供 REST API，可放在此處（依需求而定）
│   ├── apps.py                      # Django App 註冊設定
│   ├── forms.py                     # 表單邏輯定義（如登入、任務表單、篩選器）
│   ├── models.py                    # 資料模型定義（如文章、任務、分析結果）
│   ├── tasks.py                     # 任務排程/背景任務（如Celery）邏輯（若使用）
│   ├── tests.py                     # 自動化測試程式
│   ├── urls.py                      # scraper 應用自身的 URL 路由設定
│   ├── views.py                     # 系統所有視圖（網頁邏輯處理）定義
│   ├── __init__.py                  # 模組初始化
│   ├── migrations/                  # 資料表遷移檔案（由 makemigrations 產生）
│   ├── services/                    # 分離商業邏輯層，各分析服務模組
│   │   ├── ai_service.py            # AI 報告生成相關邏輯
│   │   ├── analysis_service.py      # 關鍵詞/實體分析邏輯
│   │   ├── scraper_service.py       # 爬蟲任務核心邏輯
│   │   ├── search_service.py        # 進階搜尋與查詢邏輯
│   │   ├── sentiment_service.py     # 情感分析服務邏輯
│   │   ├── summary_service.py       # 摘要產生與分析邏輯
│   │   ├── task_service.py          # 任務初始化與執行邏輯
│   │   ├── __init__.py              # services 模組初始化
│   ├── templatetags/                # 自訂 template filter 與標籤
│   │   ├── custom_filters.py        # 定義自訂過濾器（如數字格式化、顏色轉換等）
│   │   ├── __init__.py              # 模組初始化
│   ├── utils/                       # 工具函式集
│   │   ├── chart_utils.py           # 圖表用資料處理輔助函數
│   │   ├── scraper_utils.py         # 爬蟲相關的處理函式（如斷詞、斷句等）
│   │   ├── sentiment_analyzer.py    # 情感分析模型或推論方法
│   │   ├── __init__.py              # 模組初始化
├── static/                          # 靜態檔案資源（CSS、JS、圖檔）
│   ├── css/
│   │   ├── ai_report.css            # AI 報告頁面樣式
│   │   ├── analysis.css             # 一般分析模組頁面樣式
│   │   ├── bootstrap.min.css        # Bootstrap 樣式表（前端框架）
│   │   ├── main.css                 # 通用樣式
│   │   ├── search_analysis.css      # 搜尋分析頁面專用樣式
│   ├── images/
│   │   ├── 404.svg                  # 404 頁面的插圖
│   │   ├── login.png                # 登入頁的背景或 UI 示意圖
│   │   ├── leader/                  # 領導人物相關圖片
│   │   │   ├── biden.png            # 拜登圖片
│   │   │   ├── lai.png              # 賴清德圖片
│   │   │   ├── trump.png            # 川普圖片
│   │   │   ├── tsai.png             # 蔡英文圖片
│   │   │   ├── xi.png               # 習近平圖片
│   ├── js/
│   │   ├── analysis.js              # 分析頁的互動邏輯
│   │   ├── bootstrap.min.js         # Bootstrap 前端元件邏輯
│   │   ├── chart.js                 # Chart.js 圖表套件
│   │   ├── datatables.min.js        # 表格操作功能（排序、分頁）
│   │   ├── main.js                  # 通用 JS 邏輯
│   │   ├── search_analysis.js       # 進階搜尋互動邏輯
│   │   ├── word_cloud_analysis.js   # 關鍵詞雲圖產生邏輯
├── templates/                       # HTML 模板資料夾
│   ├── 403.html                     # 無權限錯誤頁
│   ├── 404.html                     # 頁面不存在錯誤頁
│   ├── 500.html                     # 系統錯誤頁
│   ├── base.html                    # 通用模板框架，其他頁面繼承自此
│   ├── scraper/                     # scraper app 專用的頁面模板
│   │   ├── ai_report_detail.html    # AI 報告詳情頁
│   │   ├── ai_report_list.html      # AI 報告總覽頁
│   │   ├── article_detail.html      # 文章詳情頁
│   │   ├── job_articles.html        # 文章列表頁
│   │   ├── job_create.html          # 建立爬蟲任務頁
│   │   ├── job_detail.html          # 任務總覽頁
│   │   ├── job_entities.html        # 命名實體分析頁
│   │   ├── job_keywords.html        # 關鍵詞分析頁
│   │   ├── job_list.html            # 任務列表頁
│   │   ├── job_search_analysis.html # 進階搜尋分析頁
│   │   ├── job_sentiment_analysis.html # 情感分析頁
│   │   ├── job_summary_analysis.html   # 摘要分析頁
│   │   ├── key_a_person.html       # 領導人物分析頁（單人）
│   │   ├── key_compare_persons.html # 領導人物比較頁
│   │   ├── key_person_selection.html # 領導人物選擇頁
│   │   ├── login.html              # 登入頁模板
```

---

## 資料庫設計

系統使用關聯式資料庫（Django ORM），共包含以下主要資料表：

### 資料表結構

#### 1. ScrapeJob（爬蟲任務）

| 欄位名稱                 | 資料類型          | 說明                                     |
| -------------------- | ------------- | -------------------------------------- |
| id                   | AutoField     | 主鍵                                     |
| user                 | ForeignKey    | 關聯使用者（User）                            |
| created\_at          | DateTimeField | 任務建立時間                                 |
| updated\_at          | DateTimeField | 任務更新時間                                 |
| status               | CharField     | 任務狀態（pending、running、completed、failed） |
| categories           | CharField     | 爬取新聞分類（逗號分隔）                           |
| limit\_per\_category | IntegerField  | 每分類最大文章數量                              |
| use\_threading       | BooleanField  | 是否啟用多線程                                |
| max\_workers         | IntegerField  | 最大線程數                                  |
| result\_file\_path   | CharField     | 任務結果檔案儲存路徑                             |
| sentiment\_analyzed  | BooleanField  | 是否已進行情感分析                              |

---

#### 2. Article（文章）

| 欄位名稱         | 資料類型          | 說明            |
| ------------ | ------------- | ------------- |
| id           | AutoField     | 主鍵            |
| job          | ForeignKey    | 所屬爬蟲任務        |
| item\_id     | CharField     | 原始文章唯一識別碼     |
| category     | CharField     | 文章分類          |
| title        | CharField     | 文章標題          |
| content      | TextField     | 文章內容          |
| date         | DateTimeField | 發布時間          |
| author       | CharField     | 作者            |
| link         | URLField      | 原始連結          |
| photo\_links | TextField     | 圖片連結（JSON 字串） |

---

#### 3. KeywordAnalysis（關鍵詞分析）

| 欄位名稱        | 資料類型          | 說明   |
| ----------- | ------------- | ---- |
| id          | AutoField     | 主鍵   |
| job         | ForeignKey    | 所屬任務 |
| word        | CharField     | 關鍵詞  |
| pos         | CharField     | 詞性   |
| frequency   | IntegerField  | 出現次數 |
| category    | CharField     | 所屬分類 |
| created\_at | DateTimeField | 建立時間 |

---

#### 4. NamedEntityAnalysis（命名實體分析）

| 欄位名稱         | 資料類型          | 說明                 |
| ------------ | ------------- | ------------------ |
| id           | AutoField     | 主鍵                 |
| job          | ForeignKey    | 所屬任務               |
| entity       | CharField     | 實體文字（人名、地名等）       |
| entity\_type | CharField     | 實體類型（如 PERSON、ORG） |
| frequency    | IntegerField  | 出現頻率               |
| category     | CharField     | 所屬分類               |
| created\_at  | DateTimeField | 建立時間               |

---

#### 5. SentimentAnalysis（情感分析）

| 欄位名稱                   | 資料類型          | 說明     |
| ---------------------- | ------------- | ------ |
| id                     | AutoField     | 主鍵     |
| article                | OneToOneField | 關聯文章   |
| job                    | ForeignKey    | 所屬任務   |
| positive\_score        | FloatField    | 內容正面分數 |
| negative\_score        | FloatField    | 內容負面分數 |
| sentiment              | CharField     | 內容情感傾向 |
| title\_sentiment       | CharField     | 標題情感傾向 |
| title\_positive\_score | FloatField    | 標題正面分數 |
| title\_negative\_score | FloatField    | 標題負面分數 |
| created\_at            | DateTimeField | 建立時間   |
| updated\_at            | DateTimeField | 更新時間   |

---

#### 6. CategorySentimentSummary（類別情感摘要）

| 欄位名稱                     | 資料類型          | 說明     |
| ------------------------ | ------------- | ------ |
| id                       | AutoField     | 主鍵     |
| job                      | ForeignKey    | 所屬任務   |
| category                 | CharField     | 分類名稱   |
| positive\_count          | IntegerField  | 正面文章數  |
| negative\_count          | IntegerField  | 負面文章數  |
| neutral\_count           | IntegerField  | 中立文章數  |
| average\_positive\_score | FloatField    | 平均正面分數 |
| created\_at              | DateTimeField | 建立時間   |
| updated\_at              | DateTimeField | 更新時間   |

---

#### 7. AIReport（AI 生成報告）

| 欄位名稱           | 資料類型          | 說明                             |
| -------------- | ------------- | ------------------------------ |
| id             | AutoField     | 主鍵                             |
| job            | ForeignKey    | 所屬任務                           |
| search\_query  | TextField     | 搜尋查詢內容（文字版）                    |
| content        | TextField     | 生成的報告內容                        |
| generated\_at  | DateTimeField | 生成時間                           |
| updated\_at    | DateTimeField | 更新時間                           |
| language       | CharField     | 語言設定（預設 zh-TW）                 |
| article\_count | IntegerField  | 分析的文章數量                        |
| status         | CharField     | 處理狀態（pending、completed、failed） |
| error\_message | TextField     | 錯誤訊息（如有）                       |
| search\_params | JSONField     | 搜尋參數（JSON 格式）                  |

---

#### 8. ArticleSummary（文章摘要）

| 欄位名稱             | 資料類型          | 說明                                   |
| ---------------- | ------------- | ------------------------------------ |
| id               | AutoField     | 主鍵                                   |
| article          | OneToOneField | 所屬文章                                 |
| job              | ForeignKey    | 所屬任務                                 |
| summary\_text    | TextField     | 生成的摘要文字                              |
| generated\_at    | DateTimeField | 生成時間                                 |
| updated\_at      | DateTimeField | 更新時間                                 |
| status           | CharField     | 狀態（pending、running、completed、failed） |
| error\_message   | TextField     | 錯誤訊息                                 |
| model\_used      | CharField     | 使用的 LLM 模型名稱                         |
| generation\_time | FloatField    | 生成耗時（秒）                              |

---

## 參考資料

1. Django 官方文檔: https://docs.djangoproject.com/
2. CKIP Transformers: https://github.com/ckiplab/ckip-transformers
3. Chart.js 文檔: https://www.chartjs.org/docs/latest/
4. Selenium 文檔: https://selenium-python.readthedocs.io/
5. Transformers 文檔: https://huggingface.co/docs/transformers/