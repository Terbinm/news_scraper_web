// 全站通用 JavaScript 函數

/**
 * 文檔就緒後執行
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有工具提示
    initializeTooltips();

    // 初始化所有下拉選單
    initializeSelect2();

    // 設定消息提示自動消失
    setupMessageAutoDismiss();

    // 轉換所有相對時間
    formatRelativeTimes();

    // 初始化摘要分析功能
    initializeSummaryAnalysis();
});

/**
 * 初始化Bootstrap工具提示
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * 初始化Select2下拉選單
 */
function initializeSelect2() {
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5',
            dropdownParent: $('body'),
            width: '100%'
        });
    }
}

/**
 * 設定提示消息自動消失
 */
function setupMessageAutoDismiss() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
}

/**
 * 格式化相對時間顯示
 */
function formatRelativeTimes() {
    if (typeof dayjs !== 'undefined') {
        const times = document.querySelectorAll('.relative-time');
        times.forEach(function(timeElement) {
            const timestamp = timeElement.getAttribute('data-timestamp');
            if (timestamp) {
                timeElement.textContent = dayjs(timestamp).fromNow();
            }
        });
    }
}

/**
 * 顯示加載指示器
 * @param {string} containerId - 容器元素ID
 * @param {string} [message="加載中..."] - 顯示的訊息
 */
function showLoader(containerId, message = "加載中...") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const loader = document.createElement('div');
    loader.className = 'text-center p-5 loader-container';
    loader.innerHTML = `
        <div class="spinner-border text-info" role="status">
            <span class="visually-hidden">加載中...</span>
        </div>
        <p class="mt-3 text-light">${message}</p>
    `;

    container.innerHTML = '';
    container.appendChild(loader);
}

/**
 * 隱藏加載指示器
 * @param {string} containerId - 容器元素ID
 */
function hideLoader(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const loader = container.querySelector('.loader-container');
    if (loader) {
        loader.remove();
    }
}

/**
 * 顯示確認對話框
 * @param {Object} options - 選項設定
 * @param {string} options.title - 對話框標題
 * @param {string} options.text - 對話框內容
 * @param {string} options.confirmButtonText - 確認按鈕文字
 * @param {Function} options.onConfirm - 確認回調函數
 * @returns {Promise} SweetAlert2 Promise
 */
function showConfirmDialog(options) {
    return Swal.fire({
        title: options.title || '確認操作',
        text: options.text || '您確定要執行此操作嗎？',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#17a2b8',
        cancelButtonColor: '#6c757d',
        confirmButtonText: options.confirmButtonText || '確認',
        cancelButtonText: '取消'
    }).then((result) => {
        if (result.isConfirmed && typeof options.onConfirm === 'function') {
            options.onConfirm();
        }
        return result;
    });
}

/**
 * 顯示通知
 * @param {string} title - 通知標題
 * @param {string} message - 通知內容
 * @param {string} [type="success"] - 通知類型: success, error, warning, info
 */
function showNotification(title, message, type = "success") {
    Swal.fire({
        title: title,
        text: message,
        icon: type,
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true
    });
}

/**
 * 格式化數字為千分位
 * @param {number} number - 要格式化的數字
 * @returns {string} 格式化後的字串
 */
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * 匯出表格為CSV
 * @param {string} tableId - 表格元素ID
 * @param {string} filename - 下載的文件名
 */
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;

    let csv = [];
    let rows = table.querySelectorAll('tr');

    for (let i = 0; i < rows.length; i++) {
        let row = [], cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            // 處理文字內容
            let text = cols[j].innerText;

            // 處理逗號和引號
            text = text.replace(/"/g, '""');
            row.push('"' + text + '"');
        }

        csv.push(row.join(','));
    }

    // 下載CSV文件
    const csvFile = new Blob([csv.join('\n')], {type: 'text/csv;charset=utf-8;'});

    if (navigator.msSaveBlob) { // IE 10+
        navigator.msSaveBlob(csvFile, filename);
    } else {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(csvFile);
        link.setAttribute('download', filename);
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

/**
 * AJAX請求封裝
 * @param {Object} options - 選項設定
 */
function ajaxRequest(options) {
    const defaults = {
        url: '',
        type: 'GET',
        data: {},
        dataType: 'json',
        beforeSend: function() {
            if (options.loaderId) {
                showLoader(options.loaderId, options.loaderMessage);
            }
        },
        success: function(response) {
            if (typeof options.success === 'function') {
                options.success(response);
            }
        },
        error: function(xhr, status, error) {
            console.error('AJAX Error:', error);

            if (typeof options.error === 'function') {
                options.error(xhr, status, error);
            } else {
                showNotification('錯誤', '請求發生錯誤: ' + error, 'error');
            }
        },
        complete: function() {
            if (options.loaderId) {
                hideLoader(options.loaderId);
            }
        }
    };

    const settings = Object.assign({}, defaults, options);

    $.ajax(settings);
}

// ================================
// 摘要分析相關功能
// ================================

/**
 * 初始化摘要分析功能
 */
function initializeSummaryAnalysis() {
    // 如果頁面包含摘要相關元素，則初始化相關功能
    if (document.querySelector('.summary-badge') || document.querySelector('.generate-summary-btn')) {
        bindSummaryEvents();
    }
}

/**
 * 綁定摘要分析相關事件
 */
function bindSummaryEvents() {
    // 綁定單篇文章摘要生成按鈕
    $(document).on('click', '.generate-summary-btn', function(e) {
        e.preventDefault();
        const articleId = $(this).data('article-id');
        generateSingleArticleSummary(articleId, $(this));
    });

    // 綁定批量摘要分析按鈕
    $(document).on('click', '.start-batch-summary-btn', function(e) {
        e.preventDefault();
        const jobId = $(this).data('job-id');
        startBatchSummaryAnalysis(jobId);
    });

    // 綁定重新生成摘要按鈕
    $(document).on('click', '.regenerate-summary-btn', function(e) {
        e.preventDefault();
        const articleId = $(this).data('article-id');
        regenerateArticleSummary(articleId, $(this));
    });

    // 綁定獲取摘要統計按鈕
    $(document).on('click', '.get-summary-stats-btn', function(e) {
        e.preventDefault();
        const jobId = $(this).data('job-id');
        getSummaryStatistics(jobId);
    });
}

/**
 * 生成單篇文章摘要
 * @param {number} articleId - 文章ID
 * @param {jQuery} buttonElement - 按鈕元素
 */
function generateSingleArticleSummary(articleId, buttonElement) {
    const originalText = buttonElement.html();

    // 顯示加載狀態
    buttonElement.html('<i class="bi bi-arrow-repeat spin"></i> 生成中...')
                 .prop('disabled', true);

    // 使用後端API生成摘要
    fetch(`/api/articles/${articleId}/generate-summary/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            if (data.already_analyzed) {
                showNotification('提示', '該文章已分析過，無需重複生成', 'info');

                // 更新顯示的摘要
                updateSummaryDisplay(articleId, data.result);
            } else {
                showNotification('成功', '摘要生成完成', 'success');

                // 更新顯示的摘要
                updateSummaryDisplay(articleId, data.result);

                // 更新按鈕為已分析狀態
                updateSummaryButton(buttonElement, true);
            }
        } else {
            showNotification('錯誤', data.message || '摘要生成失敗', 'error');
        }
    })
    .catch(error => {
        console.error('生成摘要時出錯:', error);
        showNotification('錯誤', '網路請求失敗', 'error');
    })
    .finally(() => {
        // 恢復按鈕狀態
        buttonElement.html(originalText).prop('disabled', false);
    });
}

/**
 * 啟動批量摘要分析
 * @param {number} jobId - 任務ID
 */
function startBatchSummaryAnalysis(jobId) {
    showConfirmDialog({
        title: '確認啟動批量摘要分析',
        text: '這將為該任務下的所有文章生成摘要，可能需要較長時間。',
        confirmButtonText: '啟動分析',
        onConfirm: function() {
            performBatchSummaryAnalysis(jobId);
        }
    });
}

/**
 * 執行批量摘要分析
 * @param {number} jobId - 任務ID
 */
function performBatchSummaryAnalysis(jobId) {
    // 顯示進度提示
    const progressContainer = document.createElement('div');
    progressContainer.id = 'summaryProgress';
    progressContainer.className = 'fixed-top bg-dark text-white p-3';
    progressContainer.style.zIndex = '9999';
    progressContainer.innerHTML = `
        <div class="container">
            <div class="d-flex align-items-center">
                <div class="spinner-border spinner-border-sm text-info me-3" role="status">
                    <span class="visually-hidden">分析中...</span>
                </div>
                <div class="flex-grow-1">
                    <strong>正在執行批量摘要分析...</strong>
                    <div class="progress mt-2" style="height: 10px;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated bg-info" 
                             role="progressbar" style="width: 0%" id="summaryProgressBar">
                        </div>
                    </div>
                </div>
                <button type="button" class="btn btn-sm btn-outline-light ms-3" onclick="hideSummaryProgress()">
                    <i class="bi bi-x"></i>
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(progressContainer);

    // 啟動批量分析
    fetch(`/api/jobs/${jobId}/summary-analysis/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            batch_size: 10,
            max_workers: 2
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('成功', data.message || '摘要分析任務已啟動', 'success');

            // 開始定期檢查進度
            checkSummaryProgress(jobId);
        } else {
            showNotification('錯誤', data.message || '啟動批量分析失敗', 'error');
            hideSummaryProgress();
        }
    })
    .catch(error => {
        console.error('啟動批量分析時出錯:', error);
        showNotification('錯誤', '網路請求失敗', 'error');
        hideSummaryProgress();
    });
}

/**
 * 檢查摘要分析進度
 * @param {number} jobId - 任務ID
 */
function checkSummaryProgress(jobId) {
    const progressCheck = setInterval(() => {
        fetch(`/api/jobs/${jobId}/summary-analysis/`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const progress = Math.round((data.analyzed_articles / data.total_articles) * 100);

                // 更新進度條
                const progressBar = document.getElementById('summaryProgressBar');
                if (progressBar) {
                    progressBar.style.width = progress + '%';
                    progressBar.textContent = `${data.analyzed_articles}/${data.total_articles} (${progress}%)`;
                }

                // 如果完成，停止檢查
                if (progress >= 100) {
                    clearInterval(progressCheck);
                    showNotification('完成', '所有文章摘要分析已完成', 'success');
                    hideSummaryProgress();

                    // 刷新頁面或更新顯示
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                }
            }
        })
        .catch(error => {
            console.error('檢查進度時出錯:', error);
        });
    }, 3000); // 每3秒檢查一次

    // 設置最大檢查時間（15分鐘）
    setTimeout(() => {
        clearInterval(progressCheck);
        hideSummaryProgress();
    }, 900000);
}

/**
 * 隱藏摘要分析進度
 */
function hideSummaryProgress() {
    const progressContainer = document.getElementById('summaryProgress');
    if (progressContainer) {
        progressContainer.remove();
    }
}

/**
 * 重新生成文章摘要
 * @param {number} articleId - 文章ID
 * @param {jQuery} buttonElement - 按鈕元素
 */
function regenerateArticleSummary(articleId, buttonElement) {
    showConfirmDialog({
        title: '確認重新生成摘要',
        text: '這將覆蓋現有的摘要內容。',
        confirmButtonText: '重新生成',
        onConfirm: function() {
            generateSingleArticleSummary(articleId, buttonElement);
        }
    });
}

/**
 * 獲取摘要統計信息
 * @param {number} jobId - 任務ID
 */
function getSummaryStatistics(jobId) {
    fetch(`/api/jobs/${jobId}/summary-analysis/`)
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 更新統計顯示
            updateSummaryStats(data);
        } else {
            console.error('獲取摘要統計失敗:', data.message);
        }
    })
    .catch(error => {
        console.error('獲取摘要統計時出錯:', error);
    });
}

/**
 * 更新摘要顯示
 * @param {number} articleId - 文章ID
 * @param {Object} summaryData - 摘要數據
 */
function updateSummaryDisplay(articleId, summaryData) {
    // 查找對應的摘要顯示區域
    const summaryElements = document.querySelectorAll(`[data-article-id="${articleId}"] .article-summary`);

    summaryElements.forEach(element => {
        if (summaryData && summaryData.summary_content) {
            element.textContent = summaryData.summary_content;
            element.classList.remove('text-muted');
            element.classList.add('text-info');

            // 更新摘要徽章
            const summaryBadge = element.closest('.article-item, .card')?.querySelector('.summary-badge');
            if (summaryBadge) {
                summaryBadge.textContent = '已分析';
                summaryBadge.className = 'badge bg-success summary-badge';
            }
        }
    });
}

/**
 * 更新摘要按鈕狀態
 * @param {jQuery} buttonElement - 按鈕元素
 * @param {boolean} isAnalyzed - 是否已分析
 */
function updateSummaryButton(buttonElement, isAnalyzed) {
    if (isAnalyzed) {
        buttonElement.removeClass('btn-outline-warning')
                    .addClass('btn-outline-success')
                    .html('<i class="bi bi-check-circle me-1"></i>已分析');
    } else {
        buttonElement.removeClass('btn-outline-success')
                    .addClass('btn-outline-warning')
                    .html('<i class="bi bi-cpu me-1"></i>生成摘要');
    }
}

/**
 * 更新摘要統計信息
 * @param {Object} statsData - 統計數據
 */
function updateSummaryStats(statsData) {
    // 更新總文章數
    const totalElement = document.querySelector('.summary-total-count');
    if (totalElement) {
        totalElement.textContent = statsData.total_articles || 0;
    }

    // 更新已分析數
    const analyzedElement = document.querySelector('.summary-analyzed-count');
    if (analyzedElement) {
        analyzedElement.textContent = statsData.analyzed_articles || 0;
    }

    // 更新進度
    const progressElement = document.querySelector('.summary-progress');
    if (progressElement) {
        const progress = statsData.total_articles > 0
            ? Math.round((statsData.analyzed_articles / statsData.total_articles) * 100)
            : 0;
        progressElement.textContent = progress + '%';
    }

    // 更新進度條
    const progressBar = document.querySelector('.summary-progress-bar');
    if (progressBar) {
        const progress = statsData.total_articles > 0
            ? Math.round((statsData.analyzed_articles / statsData.total_articles) * 100)
            : 0;
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
    }
}

/**
 * 獲取CSRF Token
 * @returns {string} CSRF Token
 */
function getCsrfToken() {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    if (token) {
        return token.value;
    }

    // 從Cookie中獲取CSRF Token
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }

    return '';
}

// 添加CSS動畫效果
const style = document.createElement('style');
style.textContent = `
    .spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .summary-badge {
        font-size: 0.7rem;
    }
    
    .article-summary {
        font-style: italic;
        line-height: 1.4;
        margin-top: 0.5rem;
    }
    
    .summary-loading {
        opacity: 0.7;
    }
`;
document.head.appendChild(style);