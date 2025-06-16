/**
 * 分析頁面通用JavaScript函數
 */

/**
 * 初始化資料表格
 * @param {string} tableId - 表格元素ID
 * @param {number} pageLength - 每頁顯示的記錄數
 */
function initializeDataTable(tableId, pageLength = 15) {
    // 檢查表格是否存在
    if (!document.getElementById(tableId)) return;

    // 檢查表格是否已經初始化為DataTable
    if ($.fn.DataTable.isDataTable('#' + tableId)) {
        $('#' + tableId).DataTable().destroy();
    }

    // 初始化DataTable
    $('#' + tableId).DataTable({
        language: {
            "processing": "處理中...",
            "loadingRecords": "載入中...",
            "lengthMenu": "顯示 _MENU_ 項結果",
            "zeroRecords": "沒有符合的結果",
            "info": "顯示第 _START_ 至 _END_ 項結果，共 _TOTAL_ 項",
            "infoEmpty": "顯示第 0 至 0 項結果，共 0 項",
            "infoFiltered": "(從 _MAX_ 項結果中過濾)",
            "infoPostFix": "",
            "search": "搜尋:",
            "paginate": {
                "first": "第一頁",
                "previous": "上一頁",
                "next": "下一頁",
                "last": "最後一頁"
            },
            "aria": {
                "sortAscending": ": 升冪排列",
                "sortDescending": ": 降冪排列"
            }
        },
        pageLength: pageLength,
        responsive: true
    });
}

/**
 * 顯示詳情模態框
 * @param {Object} options - 設定選項
 * @param {string} options.modalId - 模態框元素ID
 * @param {string} options.title - 標題文字
 * @param {string} options.details - 詳情數據字符串
 * @param {string} options.chartId - 圖表畫布元素ID
 */
function showDetailModal(options) {
    // 解析詳情數據
    const detailPairs = options.details.split(', ');
    const categories = [];
    const frequencies = [];
    let totalFreq = 0;

    // 解析每組類別:頻率
    detailPairs.forEach(pair => {
        const [category, frequency] = pair.split(': ');
        const freqNum = parseInt(frequency);
        categories.push(category);
        frequencies.push(freqNum);
        totalFreq += freqNum;
    });

    // 創建表格HTML
    let tableHtml = '<table class="table table-dark table-striped">';
    tableHtml += '<thead><tr><th>類別</th><th>頻率</th><th>佔比</th></tr></thead><tbody>';

    // 生成表格行
    detailPairs.forEach(pair => {
        const [category, frequency] = pair.split(': ');
        const freqNum = parseInt(frequency);
        const percentage = ((freqNum / totalFreq) * 100).toFixed(1);

        tableHtml += `<tr>
            <td>${category}</td>
            <td>${frequency}</td>
            <td>${percentage}%</td>
        </tr>`;
    });

    tableHtml += '</tbody></table>';

    // 設置模態框內容
    $(options.titleElement).text(options.titleText);
    $(options.contentElement).html(tableHtml);

    // 創建圓餅圖
    const ctx = document.getElementById(options.chartId).getContext('2d');

    // 如果已有圖表，先銷毀
    if (window[options.chartInstanceVar]) {
        window[options.chartInstanceVar].destroy();
    }

    // 創建新圖表
    window[options.chartInstanceVar] = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: categories,
            datasets: [{
                data: frequencies,
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(199, 199, 199, 0.7)',
                    'rgba(83, 102, 255, 0.7)',
                    'rgba(40, 159, 64, 0.7)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)',
                    'rgba(83, 102, 255, 1)',
                    'rgba(40, 159, 64, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)',
                        padding: 10,
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            const percentage = ((value / totalFreq) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });

    // 顯示模態框
    const modal = new bootstrap.Modal(document.getElementById(options.modalId));
    modal.show();
}

/**
 * 匯出表格為CSV
 * @param {string} tableId - 表格元素ID
 * @param {string} filename - 下載的文件名
 */
function exportTableToCSV(tableId, filename) {
    const csv = [];
    const rows = document.querySelectorAll(`#${tableId} tr`);

    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');

        for (let j = 0; j < cols.length; j++) {
            // 跳過操作按鈕欄位
            if (cols[j].querySelector('.btn-outline-info')) {
                continue;
            }

            // 處理特殊標籤內容
            let cellText = cols[j].innerText;
            if (cols[j].querySelector('.badge')) {
                cellText = cols[j].querySelector('.badge').innerText;
            }

            // 處理CSV中的逗號和引號
            row.push('"' + cellText.replace(/"/g, '""') + '"');
        }

        csv.push(row.join(','));
    }

    // 下載CSV文件
    const csvFile = new Blob([csv.join('\n')], {type: 'text/csv;charset=utf-8;'});
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(csvFile);
    downloadLink.setAttribute('download', filename);
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

/**
 * 初始化圖表切換按鈕
 * @param {object} chart - Chart.js圖表實例
 */
function initChartToggle(chart) {
    $('#barChartBtn').click(function() {
        $(this).addClass('active');
        $('#pieChartBtn').removeClass('active');
        chart.config.type = 'bar';
        chart.config.options.indexAxis = 'y';
        chart.update();
    });

    $('#pieChartBtn').click(function() {
        $(this).addClass('active');
        $('#barChartBtn').removeClass('active');
        chart.config.type = 'pie';
        chart.update();
    });
}

/**
 * 將range滑桿值顯示到指定元素
 * @param {string} rangerId - range滑桿元素ID
 * @param {string} displayId - 顯示值的元素ID
 */
function bindRangeValue(rangerId, displayId) {
    $(`#${rangerId}`).on('input', function() {
        $(`#${displayId}`).text($(this).val());
    });
}

/**
 * 全選/取消全選類別
 * @param {string} selectAllId - 全選複選框元素ID
 * @param {string} targetName - 目標複選框的name屬性
 */
function initSelectAll(selectAllId, targetName) {
    $(`#${selectAllId}`).click(function() {
        const isChecked = $(this).prop('checked');
        $(`input[name="${targetName}"]`).prop('checked', isChecked);
    });
}

/**
 * 標籤篩選控制器 - 修正版本
 * 處理各種類型標籤（類別、詞性、實體類型）的選擇與UI狀態
 * @param {Object} options - 設定選項
 */
function initTagFilters(options) {
    // 處理默認選項
    const settings = Object.assign({
        // 標籤選擇器
        tagSelector: '.filter-tag',
        // 用於檢查跨類別可用性的類別標籤
        categoryTagSelector: '.category-checkbox',
        // 全選按鈕的ID
        selectAllBtnId: '',
        // 取消全選按鈕的ID
        deselectAllBtnId: '',
        // 跨類別切換ID (如果有的話)
        crossCategoryId: '',
        // 跨類別切換容器
        crossCategoryContainerId: '',
        // 處理數據變化的回調
        onSelectionChange: null
    }, options);

    // 獲取所有標籤元素
    const allTags = document.querySelectorAll(settings.tagSelector);

    if (allTags.length === 0) {
        console.warn(`標籤選擇器 "${settings.tagSelector}" 未找到任何元素`);
        return; // 如果沒有找到元素，提前結束函數
    }

    // 處理所有標籤的點擊事件
    allTags.forEach(tag => {
        // 移除現有的事件監聽器，防止重複綁定
        const newTag = tag.cloneNode(true);
        tag.parentNode.replaceChild(newTag, tag);

        // 添加新的點擊事件處理器
        newTag.addEventListener('click', function(e) {
            // 防止標籤內部元素（如checkbox）的事件傳播
            e.preventDefault();

            // 找到與標籤關聯的複選框
            const checkbox = this.querySelector('input[type="checkbox"]');
            if (!checkbox) {
                console.warn('標籤內未找到複選框');
                return;
            }

            // 切換複選框狀態
            checkbox.checked = !checkbox.checked;

            // 切換視覺效果
            this.classList.toggle('active', checkbox.checked);

            // 如果是類別複選框，檢查跨類別可用性
            if (settings.crossCategoryId && checkbox.matches(settings.categoryTagSelector)) {
                checkCrossCategoryAvailability();
            }

            // 如果有回調函數，則調用
            if (typeof settings.onSelectionChange === 'function') {
                settings.onSelectionChange();
            }
        });

        // 設置初始狀態
        const checkbox = newTag.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) {
            newTag.classList.add('active');
        } else if (checkbox) {
            newTag.classList.remove('active');
        }
    });

    // 全選按鈕
    if (settings.selectAllBtnId) {
        const selectAllBtn = document.getElementById(settings.selectAllBtnId);
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', function() {
                // 找到所有相關的複選框並設置為選中
                const checkboxSelector = settings.categoryTagSelector ||
                    `${settings.tagSelector} input[type="checkbox"]`;

                const checkboxes = document.querySelectorAll(checkboxSelector);

                checkboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    const parentTag = checkbox.closest(settings.tagSelector);
                    if (parentTag) {
                        parentTag.classList.add('active');
                    }
                });

                // 檢查跨類別可用性
                if (settings.crossCategoryId) {
                    checkCrossCategoryAvailability();
                }

                // 如果有回調函數，則調用
                if (typeof settings.onSelectionChange === 'function') {
                    settings.onSelectionChange();
                }
            });
        } else {
            console.warn(`全選按鈕ID "${settings.selectAllBtnId}" 未找到對應元素`);
        }
    }

    // 取消全選按鈕
    if (settings.deselectAllBtnId) {
        const deselectAllBtn = document.getElementById(settings.deselectAllBtnId);
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', function() {
                // 找到所有相關的複選框並設置為未選中
                const checkboxSelector = settings.categoryTagSelector ||
                    `${settings.tagSelector} input[type="checkbox"]`;

                const checkboxes = document.querySelectorAll(checkboxSelector);

                checkboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    const parentTag = checkbox.closest(settings.tagSelector);
                    if (parentTag) {
                        parentTag.classList.remove('active');
                    }
                });

                // 檢查跨類別可用性
                if (settings.crossCategoryId) {
                    checkCrossCategoryAvailability();
                }

                // 如果有回調函數，則調用
                if (typeof settings.onSelectionChange === 'function') {
                    settings.onSelectionChange();
                }
            });
        } else {
            console.warn(`取消全選按鈕ID "${settings.deselectAllBtnId}" 未找到對應元素`);
        }
    }

    // 檢查跨類別分析可用性
    function checkCrossCategoryAvailability() {
        if (!settings.crossCategoryId) return;

        const crossCategoryCheckbox = document.getElementById(settings.crossCategoryId);
        if (!crossCategoryCheckbox) {
            console.warn(`跨類別切換ID "${settings.crossCategoryId}" 未找到對應元素`);
            return;
        }

        const categoryCheckboxes = document.querySelectorAll(settings.categoryTagSelector);
        const selectedCount = Array.from(categoryCheckboxes).filter(cb => cb.checked).length;

        // 如果選擇的類別數量為1或0，禁用跨類別分析
        if (selectedCount <= 1) {
            crossCategoryCheckbox.checked = false;
            crossCategoryCheckbox.disabled = true;

            // 如果指定了容器，則添加禁用樣式
            if (settings.crossCategoryContainerId) {
                const container = document.getElementById(settings.crossCategoryContainerId);
                if (container) {
                    container.classList.add('text-muted');
                }
            }
        } else {
            crossCategoryCheckbox.disabled = false;

            // 如果指定了容器，則移除禁用樣式
            if (settings.crossCategoryContainerId) {
                const container = document.getElementById(settings.crossCategoryContainerId);
                if (container) {
                    container.classList.remove('text-muted');
                }
            }
        }
    }

    // 初始化時檢查跨類別可用性
    if (settings.crossCategoryId) {
        checkCrossCategoryAvailability();
    }

    // 返回工具物件
    return {
        checkCrossCategoryAvailability: checkCrossCategoryAvailability
    };
}

/**
 * 初始化類別標籤選擇
 * @param {string} filterFormId - 篩選表單ID
 */
function initCategoryFilters(filterFormId) {
    // 標籤選擇效果
    $('.filter-tag').click(function() {
        const checkbox = $(this).find('input[type="checkbox"]');
        checkbox.prop('checked', !checkbox.prop('checked'));
        $(this).toggleClass('active');
        checkCrossCategoryAvailability();
    });

    // 初始化設置已選擇的類別標籤
    $('.filter-tag input:checked').each(function() {
        $(this).parent().addClass('active');
    });

    // 全選按鈕
    $('#selectAllCategories').click(function() {
        $('.category-checkbox').prop('checked', true);
        $('.filter-tag').addClass('active');
        checkCrossCategoryAvailability();
    });

    // 取消全選按鈕
    $('#deselectAllCategories').click(function() {
        $('.category-checkbox').prop('checked', false);
        $('.filter-tag').removeClass('active');
        checkCrossCategoryAvailability();
    });

    // 檢查跨類別分析可用性
    function checkCrossCategoryAvailability() {
        const selectedCount = $('.category-checkbox:checked').length;

        // 如果選擇的類別數量為1或0，禁用跨類別分析
        if (selectedCount <= 1) {
            $('#id_cross_category').prop('checked', false).prop('disabled', true);
            $('#crossCategorySwitch').addClass('text-muted');
        } else {
            $('#id_cross_category').prop('disabled', false);
            $('#crossCategorySwitch').removeClass('text-muted');
        }
    }

    // 初始化時檢查跨類別分析可用性
    checkCrossCategoryAvailability();
}

/**
 * 高亮搜尋關鍵字
 * @param {string} keyword - 搜尋關鍵字
 */
function highlightKeyword(keyword) {
    if (!keyword) return;

    const regex = new RegExp(keyword, 'gi');

    // 高亮文章標題
    $('.article-title').each(function() {
        const title = $(this).text();
        if (regex.test(title)) {
            $(this).html(title.replace(regex, match => `<mark class="highlight">${match}</mark>`));
        }
    });

    // 高亮作者名稱
    $('.article-meta').each(function() {
        const text = $(this).html();
        if (regex.test(text)) {
            $(this).html(text.replace(regex, match => `<mark class="highlight">${match}</mark>`));
        }
    });
}

/**
 * 文章搜尋和篩選功能
 */
function initArticleFilter() {
    // 客戶端篩選文章功能
    function filterArticles() {
        const selectedCategories = [];

        // 獲取所有選中的類別
        $('.category-checkbox:checked').each(function() {
            selectedCategories.push($(this).val());
        });

        // 如果沒有選擇任何類別，顯示所有文章
        if (selectedCategories.length === 0) {
            $('.article-item').show();
            updateArticleCount();
            $('#noResultsAlert').hide();
            return;
        }

        // 根據選擇的類別顯示/隱藏文章
        let visibleCount = 0;
        $('.article-item').each(function() {
            const category = $(this).data('category');
            if (selectedCategories.includes(category)) {
                $(this).show();
                visibleCount++;
            } else {
                $(this).hide();
            }
        });

        // 更新文章計數
        updateArticleCount(visibleCount);

        // 顯示/隱藏無結果提示
        if (visibleCount === 0) {
            $('#noResultsAlert').show();
            $('#pagination').hide();
        } else {
            $('#noResultsAlert').hide();
            $('#pagination').show();
        }
    }

    // 更新文章計數
    function updateArticleCount(count) {
        const totalVisible = count !== undefined ? count : $('.article-item:visible').length;
        $('#article-count').text(totalVisible);
    }

    // 監聽類別複選框變化
    $('.category-checkbox').change(function() {
        filterArticles();
    });

    // 初始篩選（如果有篩選參數）
    filterArticles();
}

// ================================
// 摘要分析專用功能（分析頁面）
// ================================

/**
 * 增強版文章預覽模態框 - 包含摘要功能
 * @param {Object} articleData - 文章數據
 */
function showArticlePreviewWithSummary(articleData) {
    const modalId = 'articlePreviewModal';

    // 確保模態框存在，如果不存在則創建
    if (!document.getElementById(modalId)) {
        createArticlePreviewModal();
    }

    // 填充基本文章信息
    document.getElementById('previewArticleTitle').textContent = articleData.title;
    document.getElementById('previewArticleCategory').textContent = articleData.category;
    document.getElementById('previewArticleDate').textContent = articleData.date;
    document.getElementById('previewArticleAuthor').textContent = articleData.author;
    document.getElementById('previewArticleContent').innerHTML = articleData.content.replace(/\n/g, '<br>');
    document.getElementById('previewArticleLink').href = articleData.link;

    // 處理摘要顯示
    const summaryContainer = document.getElementById('previewArticleSummary');
    const summaryLoadingContainer = document.getElementById('previewSummaryLoading');
    const generateSummaryBtn = document.getElementById('previewGenerateSummaryBtn');

    // 重置摘要區域
    summaryContainer.style.display = 'none';
    summaryLoadingContainer.style.display = 'none';
    generateSummaryBtn.style.display = 'inline-block';

    // 檢查是否已有摘要
    checkExistingSummary(articleData.id);

    // 綁定生成摘要按鈕事件
    generateSummaryBtn.onclick = function() {
        generateSummaryInModal(articleData.id);
    };

    // 顯示模態框
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
}

/**
 * 創建文章預覽模態框
 */
function createArticlePreviewModal() {
    const modalHtml = `
        <div class="modal fade" id="articlePreviewModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content bg-dark text-white">
                    <div class="modal-header">
                        <h5 class="modal-title" id="previewArticleTitle"></h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <!-- 文章基本信息 -->
                        <div class="mb-3">
                            <span class="badge bg-info me-2" id="previewArticleCategory"></span>
                            <small class="text-white" id="previewArticleDate"></small>
                            <small class="text-white ms-2" id="previewArticleAuthor"></small>
                        </div>
                        
                        <!-- 摘要區域 -->
                        <div class="mb-4 p-3 bg-secondary bg-opacity-25 rounded">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="text-info mb-0">
                                    <i class="bi bi-cpu me-2"></i>AI 生成摘要
                                </h6>
                                <button type="button" class="btn btn-sm btn-outline-warning" id="previewGenerateSummaryBtn">
                                    <i class="bi bi-cpu me-1"></i>生成摘要
                                </button>
                            </div>
                            
                            <!-- 摘要內容 -->
                            <div id="previewArticleSummary" style="display: none;">
                                <p class="text-info mb-0" id="previewSummaryContent"></p>
                                <small class="text-muted" id="previewSummaryTime"></small>
                            </div>
                            
                            <!-- 加載狀態 -->
                            <div id="previewSummaryLoading" class="text-center" style="display: none;">
                                <div class="spinner-border spinner-border-sm text-info me-2"></div>
                                <span>正在生成摘要...</span>
                            </div>
                        </div>
                        
                        <!-- 文章內容 -->
                        <div class="article-content" id="previewArticleContent"></div>
                    </div>
                    <div class="modal-footer">
                        <a href="#" class="btn btn-outline-info" id="previewArticleLink" target="_blank">
                            <i class="bi bi-box-arrow-up-right me-1"></i>原始文章
                        </a>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">關閉</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

/**
 * 檢查文章是否已有摘要
 * @param {number} articleId - 文章ID
 */
function checkExistingSummary(articleId) {
    fetch(`/api/articles/${articleId}/summary/`)
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success' && data.has_summary) {
            displaySummaryInModal(data.summary);
        }
    })
    .catch(error => {
        console.log('檢查摘要時出錯:', error);
    });
}

/**
 * 在模態框中生成摘要
 * @param {number} articleId - 文章ID
 */
function generateSummaryInModal(articleId) {
    const summaryContainer = document.getElementById('previewArticleSummary');
    const summaryLoadingContainer = document.getElementById('previewSummaryLoading');
    const generateSummaryBtn = document.getElementById('previewGenerateSummaryBtn');

    // 顯示加載狀態
    summaryContainer.style.display = 'none';
    summaryLoadingContainer.style.display = 'block';
    generateSummaryBtn.style.display = 'none';

    // 調用API生成摘要
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
            displaySummaryInModal(data.result);
            showNotification('成功', '摘要生成完成', 'success');
        } else {
            throw new Error(data.message || '摘要生成失敗');
        }
    })
    .catch(error => {
        console.error('生成摘要時出錯:', error);
        showNotification('錯誤', error.message || '摘要生成失敗', 'error');

        // 恢復按鈕
        summaryLoadingContainer.style.display = 'none';
        generateSummaryBtn.style.display = 'inline-block';
    });
}

/**
 * 在模態框中顯示摘要
 * @param {Object} summaryData - 摘要數據
 */
function displaySummaryInModal(summaryData) {
    const summaryContainer = document.getElementById('previewArticleSummary');
    const summaryLoadingContainer = document.getElementById('previewSummaryLoading');
    const generateSummaryBtn = document.getElementById('previewGenerateSummaryBtn');

    // 填充摘要內容
    document.getElementById('previewSummaryContent').textContent = summaryData.summary_content || summaryData.content;

    // 格式化時間
    if (summaryData.generated_at) {
        const time = new Date(summaryData.generated_at).toLocaleString('zh-TW');
        document.getElementById('previewSummaryTime').textContent = `生成時間: ${time}`;
    }

    // 顯示摘要，隱藏加載狀態
    summaryLoadingContainer.style.display = 'none';
    summaryContainer.style.display = 'block';

    // 更改按鈕為重新生成
    generateSummaryBtn.innerHTML = '<i class="bi bi-arrow-clockwise me-1"></i>重新生成';
    generateSummaryBtn.style.display = 'inline-block';
}

/**
 * 更新文章卡片的摘要顯示
 * @param {number} articleId - 文章ID
 * @param {Object} summaryData - 摘要數據
 */
function updateArticleCardSummary(articleId, summaryData) {
    // 查找對應的文章卡片
    const articleCard = document.querySelector(`[data-article-id="${articleId}"]`);
    if (!articleCard) return;

    // 查找摘要顯示區域
    const summaryElement = articleCard.querySelector('.article-summary');
    const summaryBadge = articleCard.querySelector('.summary-badge');
    const generateButton = articleCard.querySelector('.generate-summary-btn');

    if (summaryElement) {
        summaryElement.textContent = summaryData.summary_content || summaryData.content;
        summaryElement.classList.remove('text-muted');
        summaryElement.classList.add('text-info');
    }

    if (summaryBadge) {
        summaryBadge.textContent = '已分析';
        summaryBadge.className = 'badge bg-success summary-badge';
    }

    if (generateButton) {
        generateButton.innerHTML = '<i class="bi bi-check-circle me-1"></i>已分析';
        generateButton.classList.remove('btn-outline-warning');
        generateButton.classList.add('btn-outline-success');
    }
}

/**
 * 批量更新摘要按鈕狀態
 * @param {number} jobId - 任務ID
 */
function refreshSummaryButtonsStatus(jobId) {
    // 獲取當前頁面所有文章的摘要狀態
    const articleCards = document.querySelectorAll('[data-article-id]');

    articleCards.forEach(card => {
        const articleId = card.getAttribute('data-article-id');
        if (articleId) {
            checkAndUpdateSummaryStatus(articleId);
        }
    });
}

/**
 * 檢查並更新單個文章的摘要狀態
 * @param {number} articleId - 文章ID
 */
function checkAndUpdateSummaryStatus(articleId) {
    fetch(`/api/articles/${articleId}/summary/`)
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success' && data.has_summary) {
            updateArticleCardSummary(articleId, data.summary);
        }
    })
    .catch(error => {
        console.log('檢查摘要狀態時出錯:', error);
    });
}

/**
 * 獲取CSRF Token - 用於摘要分析
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