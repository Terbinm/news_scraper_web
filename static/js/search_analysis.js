/**
 * 搜尋與分析頁面功能
 * 提供進階搜尋、數據視覺化和結果顯示功能
 */

// 在文檔就緒時執行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有組件
    initSearchForm();
    initResultsDisplay();

    // 如果有時間序列數據，初始化時間軸圖表
    if (timeSeriesData) {
        initTimeSeriesChart(timeSeriesData);
    }

    // 如果有共現數據，初始化關係圖
    if (cooccurrenceData) {
        initCooccurrenceNetwork(cooccurrenceData);
    }

    // 初始化關鍵詞和實體分布圖表
    if (keywordsDistribution) {
        initKeywordsChart(keywordsDistribution);
    }

    if (entitiesDistribution) {
        initEntitiesChart(entitiesDistribution);
    }
});

/**
 * 初始化搜尋表單
 */
function initSearchForm() {
    // 獲取表單元素
    const searchForm = document.getElementById('searchForm');
    const searchTypeRadios = document.querySelectorAll('input[name="search_type"]');
    const entityTypesSection = document.getElementById('entityTypesSection');
    const searchTermsInput = document.getElementById('id_search_terms');
    const minKeywordsInput = document.getElementById('id_min_keywords_count');
    const minEntitiesInput = document.getElementById('id_min_entities_count');

    // 根據搜尋類型顯示/隱藏實體類型選擇區
    function updateEntityTypesVisibility() {
        const selectedType = document.querySelector('input[name="search_type"]:checked').value;
        if (selectedType === 'entity' || selectedType === 'both') {
            entityTypesSection.classList.remove('d-none');
        } else {
            entityTypesSection.classList.add('d-none');
        }
    }

    // 初始設置
    updateEntityTypesVisibility();

    // 監聽搜尋類型變化
    searchTypeRadios.forEach(radio => {
        radio.addEventListener('change', updateEntityTypesVisibility);
    });

    // 處理表單提交
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            // 檢查是否有搜尋詞
            if (!searchTermsInput.value.trim() &&
                !minKeywordsInput.value &&
                !minEntitiesInput.value) {
                e.preventDefault();

                // 顯示提示訊息
                Swal.fire({
                    title: '提示',
                    text: '請輸入搜尋詞或設置最小關鍵詞/實體數量條件',
                    icon: 'warning',
                    confirmButtonText: '確定'
                });
                return false;
            }
        });
    }

    // 日期範圍檢查
    const dateFrom = document.getElementById('id_date_from');
    const dateTo = document.getElementById('id_date_to');

    if (dateFrom && dateTo) {
        dateFrom.addEventListener('change', function() {
            if (dateTo.value && new Date(dateFrom.value) > new Date(dateTo.value)) {
                Swal.fire({
                    title: '日期範圍錯誤',
                    text: '開始日期不能晚於結束日期',
                    icon: 'error',
                    confirmButtonText: '確定'
                });
                dateFrom.value = '';
            }
        });

        dateTo.addEventListener('change', function() {
            if (dateFrom.value && new Date(dateFrom.value) > new Date(dateTo.value)) {
                Swal.fire({
                    title: '日期範圍錯誤',
                    text: '結束日期不能早於開始日期',
                    icon: 'error',
                    confirmButtonText: '確定'
                });
                dateTo.value = '';
            }
        });
    }

    // 類別選擇處理
    initCategorySelection();
}

/**
 * 初始化類別選擇功能
 */
function initCategorySelection() {
    const selectAllBtn = document.getElementById('selectAllCategories');
    const deselectAllBtn = document.getElementById('deselectAllCategories');
    const categoryCheckboxes = document.querySelectorAll('.category-checkbox');

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            categoryCheckboxes.forEach(checkbox => {
                checkbox.checked = true;
            });
        });
    }

    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            categoryCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
        });
    }
}

/**
 * 初始化結果顯示
 */
function initResultsDisplay() {
    // 初始化文章表格
    initializeDataTable('articlesTable');

    // 初始化文章預覽功能
    initArticlePreview();

    // 初始化分頁
    initPagination();
}

/**
 * 初始化文章預覽功能
 */
function initArticlePreview() {
    const previewButtons = document.querySelectorAll('.article-preview-btn');

    previewButtons.forEach(button => {
        button.addEventListener('click', function() {
            const articleId = this.dataset.id;
            const title = this.dataset.title;
            const content = this.dataset.content;
            const date = this.dataset.date;
            const category = this.dataset.category;
            const author = this.dataset.author;
            const link = this.dataset.link;

            // 設置模態框內容
            document.getElementById('previewTitle').textContent = title;
            document.getElementById('previewCategory').textContent = category;
            document.getElementById('previewDate').textContent = date;
            document.getElementById('previewAuthor').textContent = author;
            document.getElementById('previewContent').innerHTML = content.replace(/\n/g, '<br>');
            document.getElementById('previewLink').href = link;
            document.getElementById('previewDetailLink').href = `/articles/${articleId}/`;

            // 顯示模態框
            const modal = new bootstrap.Modal(document.getElementById('articlePreviewModal'));
            modal.show();
        });
    });
}

/**
 * 初始化分頁功能
 */
function initPagination() {
    // 這裡可以根據需要自訂分頁邏輯
    // 或者使用後端分頁
}

/**
 * 初始化時間軸圖表
 * @param {Array} data - 時間軸數據
 */
function initTimeSeriesChart(data) {
    const ctx = document.getElementById('timeSeriesChart').getContext('2d');

    // 確保資料是按日期排序的
    data.sort((a, b) => new Date(a.date) - new Date(b.date));

    // 準備圖表資料
    const labels = data.map(item => formatDate(item.date));
    const counts = data.map(item => item.count);

    // 創建圖表
    const timeSeriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: '文章數量',
                data: counts,
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                tension: 0.4,
                pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(54, 162, 235, 1)'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: '文章數量時間分布',
                    color: '#fff'
                },
                legend: {
                    labels: {
                        color: '#fff'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,  // 只顯示整數
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });

    // 添加時間尺度切換
    const timeGroupingSelect = document.getElementById('id_time_grouping');
    if (timeGroupingSelect) {
        timeGroupingSelect.addEventListener('change', function() {
            // 提交表單重新載入數據
            document.getElementById('searchForm').submit();
        });
    }
}

/**
 * 格式化日期為更易讀的格式
 * @param {string} dateString - ISO格式日期字串
 * @returns {string} 格式化後的日期
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * 初始化共現網絡關係圖
 * @param {Object} data - 共現網絡數據
 */
function initCooccurrenceNetwork(data) {
    // 使用D3.js建立關係圖
    const container = document.getElementById('cooccurrenceNetwork');

    // 設置圖形尺寸
    const width = container.clientWidth;
    const height = 500;

    // 清除舊內容
    container.innerHTML = '';

    // 創建SVG元素
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    // 定義節點顏色
    const color = d3.scaleOrdinal()
        .domain([1, 2])  // 1=關鍵詞組, 2=實體組
        .range(['#6bd89e', '#f98e71']);

    // 創建力導向模擬
    const simulation = d3.forceSimulation()
        .force('link', d3.forceLink().id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => Math.sqrt(d.value) * 2 + 10));

    // 添加連接線
    const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(data.links)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => Math.sqrt(d.value));

    // 添加節點
    const node = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(data.nodes)
        .enter().append('g');

    // 添加節點圓形
    node.append('circle')
        .attr('r', d => Math.sqrt(d.value) * 1.5 + 5)
        .attr('fill', d => color(d.group))
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // 添加節點標籤
    node.append('text')
        .text(d => d.name)
        .attr('x', 0)
        .attr('y', d => -Math.sqrt(d.value) * 1.5 - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', '#fff')
        .style('font-size', '10px')
        .style('pointer-events', 'none');

    // 添加標題
    node.append('title')
        .text(d => d.name);

    // 更新力導向模擬
    simulation
        .nodes(data.nodes)
        .on('tick', ticked);

    simulation.force('link')
        .links(data.links);

    // 模擬更新函數
    function ticked() {
        link
            .attr('x1', d => Math.max(10, Math.min(width - 10, d.source.x)))
            .attr('y1', d => Math.max(10, Math.min(height - 10, d.source.y)))
            .attr('x2', d => Math.max(10, Math.min(width - 10, d.target.x)))
            .attr('y2', d => Math.max(10, Math.min(height - 10, d.target.y)));

        node
            .attr('transform', d => `translate(${Math.max(10, Math.min(width - 10, d.x))}, ${Math.max(10, Math.min(height - 10, d.y))})`);
    }

    // 拖拽開始
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    // 拖拽中
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    // 拖拽結束
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    // 添加圖例
    const legend = svg.append('g')
        .attr('class', 'legend')
        .attr('transform', 'translate(20, 20)');

    const legendItems = [
        { name: '關鍵詞', group: 1 },
        { name: '命名實體', group: 2 }
    ];

    legendItems.forEach((item, i) => {
        const legendItem = legend.append('g')
            .attr('transform', `translate(0, ${i * 25})`);

        legendItem.append('circle')
            .attr('r', 6)
            .attr('fill', color(item.group));

        legendItem.append('text')
            .attr('x', 15)
            .attr('y', 4)
            .text(item.name)
            .attr('fill', '#fff');
    });
}

/**
 * 初始化關鍵詞分布圖表
 * @param {Array} data - 關鍵詞分布數據
 */
function initKeywordsChart(data) {
    const ctx = document.getElementById('keywordsChart').getContext('2d');

    // 準備圖表資料
    const labels = data.map(item => item.word);
    const values = data.map(item => item.total);

    // 創建圖表
    const keywordsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出現次數',
                data: values,
                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',  // 水平條形圖
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: '關鍵詞分布',
                    color: '#fff'
                },
                legend: {
                    labels: {
                        color: '#fff'
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

/**
 * 初始化實體分布圖表
 * @param {Array} data - 實體分布數據
 */
function initEntitiesChart(data) {
    const ctx = document.getElementById('entitiesChart').getContext('2d');

    // 準備實體類型的顏色映射
    const entityTypeColors = {
        'PERSON': 'rgba(255, 99, 132, 0.7)',
        'LOC': 'rgba(54, 162, 235, 0.7)',
        'ORG': 'rgba(255, 206, 86, 0.7)',
        'TIME': 'rgba(75, 192, 192, 0.7)',
        'MISC': 'rgba(153, 102, 255, 0.7)'
    };

    // 準備圖表資料
    const labels = data.map(item => item.entity);
    const values = data.map(item => item.total);
    const backgroundColors = data.map(item => entityTypeColors[item.entity_type] || 'rgba(153, 102, 255, 0.7)');

    // 創建圖表
    const entitiesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '出現次數',
                data: values,
                backgroundColor: backgroundColors,
                borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',  // 水平條形圖
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: '命名實體分布',
                    color: '#fff'
                },
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const entityType = data[context.dataIndex].entity_type;
                            return [`${context.dataset.label}: ${context.raw}`, `類型: ${entityType}`];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0,
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

/**
 * 初始化數據表格
 * @param {string} tableId - 表格元素ID
 */
function initializeDataTable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    // 檢查表格是否已經初始化
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
            "search": "搜尋:",
            "paginate": {
                "first": "第一頁",
                "previous": "上一頁",
                "next": "下一頁",
                "last": "最後一頁"
            }
        },
        pageLength: 10,
        responsive: true,
        columnDefs: [
            {
                orderable: false,
                targets: -1  // 最後一欄（操作按鈕）不可排序
            }
        ]
    });
}