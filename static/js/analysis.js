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