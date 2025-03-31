/**
 * 進階搜尋與分析頁面功能
 * 提供進階搜尋、數據視覺化和結果顯示功能
 */

// 日期範圍資料
let minDate, maxDate;
let dateSlider;

// 在文檔就緒時執行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有組件
    initSearchForm();
    setupDateRangeSlider();
    setupSearchTypeToggle();
    setupEntityTypeFilters();
    initResultsDisplay();
    setupCalculateMatches();

    // 如果有時間序列數據，初始化時間軸圖表
    if (typeof timeSeriesData !== 'undefined' && timeSeriesData) {
        initTimeSeriesChart(timeSeriesData);
    }

    // 如果有共現數據，初始化關係圖
    if (typeof cooccurrenceData !== 'undefined' && cooccurrenceData) {
        initCooccurrenceNetwork(cooccurrenceData);
    }

    // 初始化關鍵詞和實體分布圖表
    if (typeof keywordsDistribution !== 'undefined' && keywordsDistribution) {
        initKeywordsChart(keywordsDistribution);
    }

    if (typeof entitiesDistribution !== 'undefined' && entitiesDistribution) {
        initEntitiesChart(entitiesDistribution);
    }
});

/**
 * 初始化搜尋表單
 */
function initSearchForm() {
    // 獲取表單元素
    const searchForm = document.getElementById('searchForm');
    const searchTermsInput = document.getElementById('id_search_terms');
    const analyzeTermsBtn = document.getElementById('analyzeTermsBtn');
    const minKeywordsInput = document.getElementById('id_min_keywords_count');
    const minEntitiesInput = document.getElementById('id_min_entities_count');
    const keywordsSlider = document.getElementById('keywords_count_slider');
    const entitiesSlider = document.getElementById('entities_count_slider');
    const resetFormBtn = document.getElementById('resetFormBtn');

    // 同步滑塊與數字輸入
    if (keywordsSlider && minKeywordsInput) {
        keywordsSlider.addEventListener('input', function() {
            minKeywordsInput.value = this.value;
        });

        minKeywordsInput.addEventListener('input', function() {
            keywordsSlider.value = this.value;
        });
    }

    if (entitiesSlider && minEntitiesInput) {
        entitiesSlider.addEventListener('input', function() {
            minEntitiesInput.value = this.value;
        });

        minEntitiesInput.addEventListener('input', function() {
            entitiesSlider.value = this.value;
        });
    }

    // 搜尋選項點擊事件
    document.querySelectorAll('.search-option').forEach(option => {
        option.addEventListener('click', function() {
            const radio = this.querySelector('input[type="radio"]');
            if (radio) {
                radio.checked = true;
                document.querySelectorAll('.search-option').forEach(opt => {
                    opt.classList.toggle('active', opt === this);
                });
            }
        });

        // 初始化狀態
        const radio = option.querySelector('input[type="radio"]');
        if (radio && radio.checked) {
            option.classList.add('active');
        }
    });

    // 標籤選擇功能
    initTagSelection('.category-tag', '.category-checkbox');
    initTagSelection('.filter-tag', 'input[type="checkbox"]');

    // 全選/取消全選類別
    setupSelectAllButtons('selectAllCategories', 'deselectAllCategories', '.category-checkbox', '.category-tag');
    setupSelectAllButtons('selectAllEntityTypes', 'deselectAllEntityTypes', 'input[name="entity_types"]', '.entity-type-PERSON, .entity-type-LOC, .entity-type-ORG, .entity-type-TIME, .entity-type-MISC');
    setupSelectAllButtons('selectAllPos', 'deselectAllPos', 'input[name="pos_types"]', '.pos-na-badge, .pos-nb-badge, .pos-nc-badge');

    // 分析關鍵詞按鈕
    if (analyzeTermsBtn) {
        analyzeTermsBtn.addEventListener('click', function() {
            analyzeSearchTerms(searchTermsInput.value);
        });
    }

    // 重設表單按鈕
    if (resetFormBtn) {
        resetFormBtn.addEventListener('click', function(e) {
            e.preventDefault();
            resetSearchForm();
        });
    }

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

            // 根據複選框更新隱藏的搜尋類型
            updateHiddenSearchType();

            // 檢查實體搜尋類型
            if (document.getElementById('search_entity').checked) {
                // 如果沒有選擇任何實體類型，則選中所有
                const entityCheckboxes = document.querySelectorAll('input[name="entity_types"]');
                const anyChecked = Array.from(entityCheckboxes).some(cb => cb.checked);

                if (!anyChecked) {
                    entityCheckboxes.forEach(cb => {
                        cb.checked = true;
                    });
                }
            }
        });
    }
}

/**
 * 設置搜尋類型切換功能
 */
function setupSearchTypeToggle() {
    const searchKeywordCheckbox = document.getElementById('search_keyword');
    const searchEntityCheckbox = document.getElementById('search_entity');
    const posTypesSection = document.getElementById('posTypesSection');
    const entityTypesSection = document.getElementById('entityTypesSection');

    function updateSections() {
        // 如果勾選了關鍵字，顯示詞性選擇區
        if (searchKeywordCheckbox && searchKeywordCheckbox.checked) {
            if (posTypesSection) posTypesSection.classList.remove('d-none');
        } else {
            if (posTypesSection) posTypesSection.classList.add('d-none');
        }

        // 如果勾選了命名實體，顯示實體類型選擇區
        if (searchEntityCheckbox && searchEntityCheckbox.checked) {
            if (entityTypesSection) entityTypesSection.classList.remove('d-none');
        } else {
            if (entityTypesSection) entityTypesSection.classList.add('d-none');
        }
    }

    // 初始化
    updateSections();

    // 監聽變更
    if (searchKeywordCheckbox) {
        searchKeywordCheckbox.addEventListener('change', updateSections);
    }

    if (searchEntityCheckbox) {
        searchEntityCheckbox.addEventListener('change', updateSections);
    }
}

/**
 * 根據複選框更新隱藏的搜尋類型欄位 (search_type)
 */
function updateHiddenSearchType() {
    const searchKeywordCheckbox = document.getElementById('search_keyword');
    const searchEntityCheckbox = document.getElementById('search_entity');
    const hiddenSearchType = document.getElementById('hidden_search_type');

    if (!hiddenSearchType) return;

    if (searchKeywordCheckbox.checked && searchEntityCheckbox.checked) {
        hiddenSearchType.value = 'both';
    } else if (searchKeywordCheckbox.checked) {
        hiddenSearchType.value = 'keyword';
    } else if (searchEntityCheckbox.checked) {
        hiddenSearchType.value = 'entity';
    } else {
        // 預設至少選一個
        hiddenSearchType.value = 'both';
        searchKeywordCheckbox.checked = true;
        searchEntityCheckbox.checked = true;
    }
}

/**
 * 設置日期範圍滑動器
 */
function setupDateRangeSlider() {
    const dateSliderElement = document.getElementById('dateRangeSlider');
    const startDateValue = document.getElementById('startDateValue');
    const endDateValue = document.getElementById('endDateValue');
    const dateFromInput = document.getElementById('date_from');
    const dateToInput = document.getElementById('date_to');

    if (!dateSliderElement) return;

    // 從資料庫獲取文章最早和最晚日期，或使用預設值
    // 在實際應用中，這些應該從後端傳遞
    const today = new Date();
    minDate = new Date(today);
    minDate.setMonth(today.getMonth() - 3); // 預設3個月前
    maxDate = new Date(today);

    // 從隱藏輸入框獲取已選日期，若有的話
    let startDate = dateFromInput && dateFromInput.value ? new Date(dateFromInput.value) : minDate;
    let endDate = dateToInput && dateToInput.value ? new Date(dateToInput.value) : maxDate;

    // 確保日期在有效範圍內
    if (startDate < minDate) startDate = minDate;
    if (endDate > maxDate) endDate = maxDate;
    if (startDate > endDate) startDate = endDate;

    // 設置滑動器
    if (typeof noUiSlider !== 'undefined') {
        // 如果已經初始化過，先銷毀
        if (dateSliderElement.noUiSlider) {
            dateSliderElement.noUiSlider.destroy();
        }

        // 創建新的滑動器
        noUiSlider.create(dateSliderElement, {
            start: [startDate.getTime(), endDate.getTime()],
            connect: true,
            step: 24 * 60 * 60 * 1000, // 一天的毫秒數
            range: {
                'min': minDate.getTime(),
                'max': maxDate.getTime()
            },
            format: {
                to: function(value) {
                    return new Date(value);
                },
                from: function(value) {
                    return new Date(value).getTime();
                }
            }
        });

        // 更新顯示和隱藏輸入框
        dateSliderElement.noUiSlider.on('update', function(values, handle) {
            const date = values[handle];
            const formattedDate = formatDate(date);

            if (handle === 0) {
                startDateValue.textContent = formattedDate;
                if (dateFromInput) dateFromInput.value = formatDateForInput(date);
            } else {
                endDateValue.textContent = formattedDate;
                if (dateToInput) dateToInput.value = formatDateForInput(date);
            }
        });

        // 顯示使用提示
        setTimeout(function() {
            const infoModal = new bootstrap.Modal(document.getElementById('dateRangeInfoModal'));
            infoModal.show();
        }, 1000);
    } else {
        // noUiSlider 未加載，顯示普通的日期輸入框
        const dateRangeContainer = dateSliderElement.parentElement;
        if (dateRangeContainer) {
            dateRangeContainer.innerHTML = `
                <div class="row">
                    <div class="col-md-6 mb-2">
                        <label for="date_from" class="form-label">開始日期</label>
                        <input type="date" id="date_from" name="date_from" class="form-control" 
                               value="${dateFromInput ? dateFromInput.value : ''}">
                    </div>
                    <div class="col-md-6 mb-2">
                        <label for="date_to" class="form-label">結束日期</label>
                        <input type="date" id="date_to" name="date_to" class="form-control"
                               value="${dateToInput ? dateToInput.value : ''}">
                    </div>
                </div>
            `;
        }
    }
}

/**
 * 設置計算符合數量功能
 */
function setupCalculateMatches() {
    const calculateBtn = document.getElementById('calculateMatchesBtn');
    if (!calculateBtn) return;

    calculateBtn.addEventListener('click', function() {
        // 顯示計算中模態框
        const calculatingModal = new bootstrap.Modal(document.getElementById('calculatingModal'));
        calculatingModal.show();

        // 收集當前表單數據
        const formData = new FormData(document.getElementById('searchForm'));

        // 添加計算標記（後端可識別為僅計算數量而非真正搜尋）
        formData.append('calculate_only', 'true');

        // 獲取CSRF令牌
        const csrftoken = getCsrfToken();

        // 發送AJAX請求
        fetch(window.location.pathname, {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': csrftoken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // 隱藏計算中模態框
            calculatingModal.hide();

            // 顯示結果
            const matchingCount = document.getElementById('matchingCount');
            const matchCount = document.getElementById('matchCount');

            if (matchingCount && matchCount) {
                matchCount.textContent = data.count;
                matchingCount.style.display = 'block';
            }

            // 額外提示
            if (data.count > 500) {
                Swal.fire({
                    title: '提示',
                    text: `找到 ${data.count} 篇符合的文章，建議添加更多篩選條件以獲得更精確的分析結果。`,
                    icon: 'info',
                    confirmButtonText: '確定'
                });
            } else if (data.count === 0) {
                Swal.fire({
                    title: '未找到符合條件的文章',
                    text: '請嘗試放寬搜尋條件',
                    icon: 'warning',
                    confirmButtonText: '確定'
                });
            }
        })
        .catch(error => {
            console.error('Error calculating matches:', error);
            calculatingModal.hide();

            Swal.fire({
                title: '計算失敗',
                text: '無法完成符合數量計算，請稍後再試',
                icon: 'error',
                confirmButtonText: '確定'
            });
        });
    });
}

/**
 * 獲取 CSRF Token
 */
function getCsrfToken() {
    // 獲取cookie中的csrftoken
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];

    // 如果cookie中找到，則返回
    if (cookieValue) {
        return cookieValue;
    }

    // 否則從表單中獲取
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    return tokenElement ? tokenElement.value : '';
}


/**
 * 分析搜尋詞
 * @param {string} searchTerms - 用戶輸入的搜尋詞
 */
function analyzeSearchTerms(searchTerms) {
    if (!searchTerms.trim()) {
        Swal.fire({
            title: '提示',
            text: '請先輸入要分析的搜尋詞',
            icon: 'info',
            confirmButtonText: '確定'
        });
        return;
    }

    // 顯示分析模態框
    const termsModal = new bootstrap.Modal(document.getElementById('termsAnalysisModal'));
    termsModal.show();

    // 顯示加載狀態
    document.querySelector('.terms-analysis-loading').style.display = 'block';
    document.querySelector('.terms-analysis-results').style.display = 'none';

    // 獲取CSRF令牌
    const csrftoken = getCsrfToken();

    // 發送AJAX請求
    fetch('/api/analyze_search_terms/', {
        method: 'POST',
        body: JSON.stringify({ terms: searchTerms }),
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // 隱藏加載狀態
        document.querySelector('.terms-analysis-loading').style.display = 'none';
        document.querySelector('.terms-analysis-results').style.display = 'block';

        // 顯示斷詞結果
        const segmentedTermsEl = document.getElementById('segmentedTerms');
        if (segmentedTermsEl) {
            let segmentedHtml = '';
            if (data.segmented_terms && data.segmented_terms.length > 0) {
                data.segmented_terms.forEach(term => {
                    segmentedHtml += `<span class="badge bg-dark text-light border border-secondary me-2 mb-2">${term}</span>`;
                });
            } else {
                segmentedHtml = '<p class="text-white">沒有找到可分析的詞彙</p>';
            }
            segmentedTermsEl.innerHTML = segmentedHtml;
        }

        // 顯示關鍵詞結果
        const keywordsEl = document.getElementById('identifiedKeywords');
        if (keywordsEl) {
            let keywordsHtml = '';
            if (data.keywords && data.keywords.length > 0) {
                data.keywords.forEach(keyword => {
                    let posClass = 'bg-secondary';
                    if (keyword.pos === 'Na') posClass = 'pos-na-badge';
                    else if (keyword.pos === 'Nb') posClass = 'pos-nb-badge';
                    else if (keyword.pos === 'Nc') posClass = 'pos-nc-badge';

                    keywordsHtml += `<span class="badge ${posClass} me-2 mb-2">${keyword.word} (${keyword.pos})</span>`;
                });
            } else {
                keywordsHtml = '<p class="text-white">沒有識別出關鍵詞</p>';
            }
            keywordsEl.innerHTML = keywordsHtml;
        }

        // 顯示命名實體結果
        const entitiesEl = document.getElementById('identifiedEntities');
        if (entitiesEl) {
            let entitiesHtml = '';
            if (data.entities && data.entities.length > 0) {
                data.entities.forEach(entity => {
                    entitiesHtml += `<span class="badge entity-type-${entity.entity_type} me-2 mb-2">${entity.entity} (${entity.entity_type})</span>`;
                });
            } else {
                entitiesHtml = '<p class="text-white">沒有識別出命名實體</p>';
            }
            entitiesEl.innerHTML = entitiesHtml;
        }

        // 設置套用結果按鈕
        const useResultsBtn = document.getElementById('useAnalysisResultsBtn');
        if (useResultsBtn) {
            useResultsBtn.onclick = function() {
                // 將結果轉換為搜尋詞（可根據需求調整）
                let newSearchTerms = '';

                // 添加識別出的關鍵詞
                if (data.keywords && data.keywords.length > 0) {
                    newSearchTerms = data.keywords.map(k => k.word).join(',');
                }

                // 添加識別出的命名實體（如果有）
                if (data.entities && data.entities.length > 0) {
                    const entityTerms = data.entities.map(e => e.entity).join(',');
                    newSearchTerms = newSearchTerms ? newSearchTerms + ',' + entityTerms : entityTerms;
                }

                // 將結果填入搜尋框
                const searchTermsInput = document.getElementById('id_search_terms');
                if (searchTermsInput) {
                    searchTermsInput.value = newSearchTerms;
                }

                // 關閉模態框
                termsModal.hide();
            };
        }
    })
    .catch(error => {
        console.error('Error analyzing search terms:', error);

        // 顯示錯誤信息
        document.querySelector('.terms-analysis-loading').style.display = 'none';
        document.querySelector('.terms-analysis-results').style.display = 'block';
        document.getElementById('segmentedTerms').innerHTML = '<p class="text-danger">分析搜尋詞時發生錯誤</p>';
        document.getElementById('identifiedKeywords').innerHTML = '<p class="text-danger">請稍後再試</p>';
        document.getElementById('identifiedEntities').innerHTML = '<p class="text-danger">或聯繫系統管理員</p>';
    });
}
/**
 * 重設搜尋表單
 */
function resetSearchForm() {
    const form = document.getElementById('searchForm');
    if (!form) return;

    // 重設輸入框
    form.reset();

    // 重設標籤選擇狀態
    document.querySelectorAll('.filter-tag, .category-tag').forEach(tag => {
        tag.classList.remove('active');
    });

    // 重設搜尋選項狀態
    document.querySelectorAll('.search-option').forEach(option => {
        const radio = option.querySelector('input[type="radio"]');
        option.classList.toggle('active', radio && radio.checked);
    });

    // 重設日期範圍
    setupDateRangeSlider();

    // 重設搜尋類型區域顯示
    setupSearchTypeToggle();

    // 重設匹配計數顯示
    const matchingCount = document.getElementById('matchingCount');
    if (matchingCount) matchingCount.style.display = 'none';
}

/**
 * 初始化標籤選擇功能
 * @param {string} tagSelector - 標籤選擇器
 * @param {string} checkboxSelector - 複選框選擇器
 */
function initTagSelection(tagSelector, checkboxSelector) {
    // 標籤點擊事件
    document.querySelectorAll(tagSelector).forEach(tag => {
        const checkbox = tag.querySelector(checkboxSelector);
        if (checkbox && checkbox.checked) {
            tag.classList.add('active');
        }

        tag.addEventListener('click', function(e) {
            e.preventDefault();
            const checkbox = this.querySelector(checkboxSelector);
            if (checkbox) {
                checkbox.checked = !checkbox.checked;
                this.classList.toggle('active', checkbox.checked);
            }
        });
    });
}

/**
 * 設置全選/取消全選按鈕
 * @param {string} selectAllId - 全選按鈕ID
 * @param {string} deselectAllId - 取消全選按鈕ID
 * @param {string} checkboxSelector - 複選框選擇器
 * @param {string} tagSelector - 標籤選擇器
 */
function setupSelectAllButtons(selectAllId, deselectAllId, checkboxSelector, tagSelector) {
    const selectAllBtn = document.getElementById(selectAllId);
    const deselectAllBtn = document.getElementById(deselectAllId);

    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            document.querySelectorAll(checkboxSelector).forEach(checkbox => {
                checkbox.checked = true;
            });

            document.querySelectorAll(tagSelector).forEach(tag => {
                tag.classList.add('active');
            });
        });
    }

    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            document.querySelectorAll(checkboxSelector).forEach(checkbox => {
                checkbox.checked = false;
            });

            document.querySelectorAll(tagSelector).forEach(tag => {
                tag.classList.remove('active');
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
 * 格式化日期為易讀格式
 * @param {Date} date - 日期物件
 * @returns {string} 格式化後的日期
 */
function formatDate(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }

    return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * 格式化日期為輸入欄位格式 (YYYY-MM-DD)
 * @param {Date} date - 日期物件
 * @returns {string} YYYY-MM-DD 格式的日期
 */
function formatDateForInput(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
}

/**
 * 初始化時間軸圖表
 * @param {Array} data - 時間軸數據
 */
function initTimeSeriesChart(data) {
    const ctx = document.getElementById('timeSeriesChart').getContext('2d');
    if (!ctx) return;

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
 * 初始化共現網絡關係圖
 * @param {Object} data - 共現網絡數據
 */
function initCooccurrenceNetwork(data) {
    // 使用D3.js建立關係圖
    const container = document.getElementById('cooccurrenceNetwork');
    if (!container || !data || typeof d3 === 'undefined') return;

    // 清除舊內容
    container.innerHTML = '';

    // 設置圖形尺寸
    const width = container.clientWidth;
    const height = container.clientHeight || 500;

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
        .attr('class', 'node-label')
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
    const ctx = document.getElementById('keywordsChart');
    if (!ctx) return;

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
    const ctx = document.getElementById('entitiesChart');
    if (!ctx) return;

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
    if (!table || typeof $.fn.DataTable === 'undefined') return;

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

/**
 * 匯出搜尋結果為CSV
 */
function exportSearchResults() {
    const exportBtn = document.getElementById('exportResultsBtn');
    if (!exportBtn) return;

    exportBtn.addEventListener('click', function() {
        // 準備CSV內容
        const headers = ['標題', '類別', '日期', '作者', '連結'];
        let csvContent = headers.join(',') + '\n';

        // 獲取表格內容
        const table = document.getElementById('articlesTable');
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');

        rows.forEach(row => {
            const title = row.querySelector('td:nth-child(2)').textContent;
            const category = row.querySelector('td:nth-child(3) .badge').textContent.trim();
            const date = row.querySelector('td:nth-child(4)').textContent;
            const author = row.querySelector('td:nth-child(5)').textContent;

            // 嘗試獲取連結，若無則使用空值
            let link = '';
            const previewBtn = row.querySelector('.article-preview-btn');
            if (previewBtn) {
                link = previewBtn.dataset.link || '';
            }

            // 處理CSV中的引號和逗號
            const formattedRow = [title, category, date, author, link].map(cell => {
                // 如果數據包含逗號、引號或換行符，使用引號包裹並將內部引號轉換為雙引號
                cell = String(cell).trim();
                if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
                    return `"${cell.replace(/"/g, '""')}"`;
                }
                return cell;
            });

            csvContent += formattedRow.join(',') + '\n';
        });

        // 創建Blob並下載
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `搜尋結果_${new Date().toISOString().slice(0, 10)}.csv`);
        link.style.display = 'none';

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
}

// 實體類型篩選按鈕處理
function setupEntityTypeFilters() {
    // 全選按鈕
    $('#selectAllEntityTypes').click(function() {
        $('input[name="entity_types"]').prop('checked', true);
        $('.filter-tag:has(input[name="entity_types"])').addClass('active');
    });

    // 取消全選按鈕
    $('#deselectAllEntityTypes').click(function() {
        $('input[name="entity_types"]').prop('checked', false);
        $('.filter-tag:has(input[name="entity_types"])').removeClass('active');
    });

    // 實體類型標籤點擊事件
    $('.filter-tag:has(input[name="entity_types"])').click(function(e) {
        e.preventDefault();
        const checkbox = $(this).find('input[name="entity_types"]');
        checkbox.prop('checked', !checkbox.prop('checked'));
        $(this).toggleClass('active', checkbox.prop('checked'));
    });

    // 初始化已選擇的實體類型標籤
    $('input[name="entity_types"]:checked').each(function() {
        $(this).closest('.filter-tag').addClass('active');
    });
}


// 當視窗調整大小時重繪圖表
window.addEventListener('resize', function() {
    // 重新初始化共現網絡圖
    if (typeof cooccurrenceData !== 'undefined' && cooccurrenceData) {
        initCooccurrenceNetwork(cooccurrenceData);
    }
});

// 自動初始化匯出功能
document.addEventListener('DOMContentLoaded', function() {
    exportSearchResults();
});