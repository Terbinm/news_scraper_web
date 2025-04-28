/**
 * 修復進階搜尋與分析頁面實體類型選擇功能
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

    // 初始化圖表
    if (typeof timeSeriesData !== 'undefined' && timeSeriesData) {
        initTimeSeriesChart(timeSeriesData);
    }

    if (typeof cooccurrenceData !== 'undefined' && cooccurrenceData) {
        initCooccurrenceNetwork(cooccurrenceData);
    }

    if (typeof keywordsDistribution !== 'undefined' && keywordsDistribution) {
        initKeywordsChart(keywordsDistribution);
    }

    if (typeof entitiesDistribution !== 'undefined' && entitiesDistribution) {
        initEntitiesChart(entitiesDistribution);
    }

    // 初始化情緒分析圖表
    if (typeof sentimentDistribution !== 'undefined' && sentimentDistribution) {
        initSentimentDistributionChart(sentimentDistribution);
    }

    if (typeof timeSeriesData !== 'undefined' && timeSeriesData &&
        typeof sentimentTimeData !== 'undefined' && sentimentTimeData) {
        initSentimentTimeSeriesChart(timeSeriesData, sentimentTimeData);
    }

    // 初始化匯出功能
    exportSearchResults();
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
    setupSelectAllButtons('selectAllEntityTypes', 'deselectAllEntityTypes', 'input[name="entity_types"]', '.filter-tag:has(input[name="entity_types"])');
    setupSelectAllButtons('selectAllPos', 'deselectAllPos', 'input[name="pos_types"]', '.filter-tag:has(input[name="pos_types"])');

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
                // 檢查是否有選擇至少一個實體類型
                const entityCheckboxes = document.querySelectorAll('input[name="entity_types"]');
                const anyChecked = Array.from(entityCheckboxes).some(cb => cb.checked);

                if (!anyChecked) {
                    // 如果沒有選擇任何實體類型，選中所有
                    entityCheckboxes.forEach(cb => {
                        cb.checked = true;
                    });
                    // 更新視覺效果
                    document.querySelectorAll('.filter-tag:has(input[name="entity_types"])').forEach(tag => {
                        tag.classList.add('active');
                    });
                }
            }

            // 檢查詞性選擇
            if (document.getElementById('search_keyword').checked) {
                // 檢查是否有選擇至少一個詞性
                const posCheckboxes = document.querySelectorAll('input[name="pos_types"]');
                const anyPosChecked = Array.from(posCheckboxes).some(cb => cb.checked);

                if (!anyPosChecked) {
                    // 如果沒有選擇任何詞性，選中所有
                    posCheckboxes.forEach(cb => {
                        cb.checked = true;
                    });
                    // 更新視覺效果
                    document.querySelectorAll('.filter-tag:has(input[name="pos_types"])').forEach(tag => {
                        tag.classList.add('active');
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
 * 設置實體類型篩選器
 */
function setupEntityTypeFilters() {
    // 實體標籤點擊事件
    const entityTags = document.querySelectorAll('.filter-tag:has(input[name="entity_types"])');
    if (entityTags.length === 0) {
        // 如果查詢器不支持:has選擇器（較舊的瀏覽器），使用替代方法
        document.querySelectorAll('.filter-tag').forEach(tag => {
            const checkbox = tag.querySelector('input[name="entity_types"]');
            if (checkbox) {
                // 設置初始狀態
                if (checkbox.checked) {
                    tag.classList.add('active');
                }

                // 添加點擊事件
                tag.addEventListener('click', function(e) {
                    e.preventDefault();
                    checkbox.checked = !checkbox.checked;
                    tag.classList.toggle('active', checkbox.checked);
                });
            }
        });
    }

    // 全選按鈕
    const selectAllEntityTypesBtn = document.getElementById('selectAllEntityTypes');
    if (selectAllEntityTypesBtn) {
        selectAllEntityTypesBtn.addEventListener('click', function() {
            const entityCheckboxes = document.querySelectorAll('input[name="entity_types"]');
            entityCheckboxes.forEach(checkbox => {
                checkbox.checked = true;
                const parentTag = checkbox.closest('.filter-tag');
                if (parentTag) {
                    parentTag.classList.add('active');
                }
            });
        });
    }

    // 取消全選按鈕
    const deselectAllEntityTypesBtn = document.getElementById('deselectAllEntityTypes');
    if (deselectAllEntityTypesBtn) {
        deselectAllEntityTypesBtn.addEventListener('click', function() {
            const entityCheckboxes = document.querySelectorAll('input[name="entity_types"]');
            entityCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
                const parentTag = checkbox.closest('.filter-tag');
                if (parentTag) {
                    parentTag.classList.remove('active');
                }
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
 * @param {Object|String} timeSeriesData - 時間軸數據或JSON字符串
 */
function initTimeSeriesChart(timeSeriesData) {
    if (!timeSeriesData) {
        console.warn("沒有提供時間軸數據");
        return;
    }

    const ctx = document.getElementById('timeSeriesChart');
    if (!ctx) return;

    try {
        // 直接使用數據，不再嘗試解析
        const data = timeSeriesData;

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
    } catch (error) {
        console.error("初始化時間軸圖表失敗:", error);
    }
}



/**
 * 初始化共現網絡關係圖
 * @param {Object|String} cooccurrenceData - 共現網絡數據或JSON字符串
 */
function initCooccurrenceNetwork(cooccurrenceData) {
    if (!cooccurrenceData) {
        console.warn("沒有提供共現網絡數據");
        return;
    }

    // 使用D3.js建立關係圖
    const container = document.getElementById('cooccurrenceNetwork');
    if (!container || typeof d3 === 'undefined') return;

    try {
        // 清除舊內容
        container.innerHTML = '';

        // 確保數據是JavaScript對象
        const data = typeof cooccurrenceData === 'string' ? JSON.parse(cooccurrenceData) : cooccurrenceData;

        if (!data || !data.nodes || !data.links || data.nodes.length === 0) {
            container.innerHTML = `
                <div class="d-flex align-items-center justify-content-center h-100 text-white">
                    <div class="text-center">
                        <i class="bi bi-exclamation-triangle display-4 mb-3 text-warning"></i>
                        <p>沒有足夠的數據生成關聯圖</p>
                    </div>
                </div>
            `;
            return;
        }

        // 設定圖表尺寸
        const width = container.clientWidth;
        const height = 500;

        // 建立力導向圖
        const svg = d3.select(container)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height])
            .attr("style", "max-width: 100%; height: auto;");

        // 增加縮放功能
        const g = svg.append("g");
        svg.call(d3.zoom()
            .extent([[0, 0], [width, height]])
            .scaleExtent([0.25, 8])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            }));

        // 建立圖例
        const legend = svg.append("g")
            .attr("class", "legend")
            .attr("transform", `translate(20, 20)`);

        // 圖例項目
        const legendItems = [
            { label: "關鍵詞", color: "#69b3a2", group: 1 },
            { label: "命名實體", color: "#ff7f50", group: 2 }
        ];

        legendItems.forEach((item, index) => {
            const legendRow = legend.append("g")
                .attr("transform", `translate(0, ${index * 20})`);

            legendRow.append("rect")
                .attr("width", 15)
                .attr("height", 15)
                .attr("fill", item.color);

            legendRow.append("text")
                .attr("x", 20)
                .attr("y", 12)
                .text(item.label)
                .style("font-size", "12px")
                .style("fill", "white");
        });

        // 創建節點顏色映射
        const color = d3.scaleOrdinal()
            .domain([1, 2])
            .range(["#4a86e8", "#ff9900"]);

        // 為實體類型創建更細緻的顏色
        const entityColors = {
            "PERSON": "#ff7f50",
            "LOC": "#6a0dad",
            "ORG": "#2e8b57",
            "TIME": "#6495ed",
            "MISC": "#ff6699"
        };

        // 設定力模擬
        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(d => 150 / (Math.sqrt(d.value)/10 + 1)).strength(0.3))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("x", d3.forceX().strength(0.05))
            .force("y", d3.forceY().strength(0.05))
            .force("collision", d3.forceCollide().radius(d => Math.sqrt(d.value) * 4 + 8).strength(0.7));

        // 創建連結
        const link = g.append("g")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(data.links)
            .join("line")
            .attr("stroke-width", d => Math.sqrt(d.value) / 10)
            .attr("opacity", d => Math.min(0.7, d.value / 300));

        // 添加連結的懸停效果
        link.append("title")
            .text(d => `連結強度: ${d.value}`);

        // 創建節點
        const node = g.append("g")
            .selectAll(".node")
            .data(data.nodes)
            .join("g")
            .attr("class", "node")
            .call(drag(simulation));

        // 節點圓形
        node.append("circle")
            .attr("r", d => Math.sqrt(d.value) * 3 + 5)
            .attr("fill", d => color(d.group))
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5);

        // 節點文字標籤
        node.append("text")
            .attr("dy", ".35em")
            .attr("x", d => Math.sqrt(d.value) * 3 + 8)
            .text(d => d.name)
            .style("font-size", d => Math.min(12 + d.value / 2, 16) + "px")
            .style("fill", "white")
            .style("text-shadow", "0 1px 3px rgba(0,0,0,0.8)");

        // 添加標題提示
        node.append("title")
            .text(d => {
                let typeText = d.group === 1 ? "關鍵詞" : "命名實體";
                return `${d.name} (${typeText})\n出現次數: ${d.value}`;
            });

        // 節點拖拽功能
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }

            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }

            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }

            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }

        // 模擬更新
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });

        // 添加控制面板
        const controlPanel = document.createElement("div");
        controlPanel.className = "control-panel mb-3";
        controlPanel.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text bg-dark border-secondary">
                            <i class="bi bi-search text-light"></i>
                        </span>
                        <input type="text" class="form-control bg-dark text-light border-secondary" 
                               id="networkSearchInput" placeholder="搜尋節點...">
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="input-group">
                        <span class="input-group-text bg-dark border-secondary">
                            <i class="bi bi-sliders text-light"></i>
                        </span>
                        <select class="form-select bg-dark text-light border-secondary" id="networkFilterSelect">
                            <option value="all">顯示全部</option>
                            <option value="1">僅顯示關鍵詞</option>
                            <option value="2">僅顯示實體</option>
                            <option value="top10">僅顯示前10大節點</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
        container.parentNode.insertBefore(controlPanel, container);

        // 搜尋功能
        const searchInput = document.getElementById("networkSearchInput");
        const filterSelect = document.getElementById("networkFilterSelect");

        function updateNetworkDisplay() {
            const searchTerm = searchInput.value.toLowerCase();
            const filterValue = filterSelect.value;

            // 重設所有節點和連結
            node.style("opacity", 1);
            node.selectAll("circle")
                .attr("fill", d => color(d.group))
                .attr("r", d => Math.sqrt(d.value) * 3 + 5);

            node.selectAll("text")
                .style("font-weight", "normal")
                .style("font-size", d => Math.min(12 + d.value / 2, 16) + "px")
                .style("fill", "white");

            link.style("opacity", d => Math.min(0.7, d.value / 300));

            // 應用過濾器
            let visibleNodes = data.nodes;

            if (filterValue === "1") {
                // 僅關鍵詞
                node.filter(d => d.group !== 1).style("opacity", 0.1);
                link.style("opacity", 0.1);
            } else if (filterValue === "2") {
                // 僅實體
                node.filter(d => d.group !== 2).style("opacity", 0.1);
                link.style("opacity", 0.1);
            } else if (filterValue === "top10") {
                // 前10大節點
                const sortedNodes = [...data.nodes].sort((a, b) => b.value - a.value);
                const top10Ids = sortedNodes.slice(0, 10).map(n => n.id);
                node.filter(d => !top10Ids.includes(d.id)).style("opacity", 0.1);
                link.filter(d => !top10Ids.includes(d.source.id) || !top10Ids.includes(d.target.id))
                    .style("opacity", 0.1);
            }

            // 應用搜尋
            if (searchTerm) {
                // 找到匹配的節點
                const matchingNodes = node.filter(d => d.name.toLowerCase().includes(searchTerm));

                // 淡化所有不匹配的節點和連結
                node.filter(d => !d.name.toLowerCase().includes(searchTerm))
                    .style("opacity", 0.1);

                // 強調匹配的節點
                matchingNodes.selectAll("circle")
                    .attr("fill", "#f8f9fa")
                    .attr("r", d => (Math.sqrt(d.value) * 3 + 5) * 1.3);

                matchingNodes.selectAll("text")
                    .style("font-weight", "bold")
                    .style("font-size", d => (Math.min(12 + d.value / 2, 16) * 1.2) + "px")
                    .style("fill", "#f8f9fa");

                // 強調與匹配節點相關的連結
                const matchingIds = matchingNodes.data().map(d => d.id);
                link.filter(d => matchingIds.includes(d.source.id) || matchingIds.includes(d.target.id))
                    .style("opacity", 0.8)
                    .attr("stroke", "#f8f9fa");
            }
        }

        searchInput.addEventListener("input", updateNetworkDisplay);
        filterSelect.addEventListener("change", updateNetworkDisplay);

    } catch (error) {
        console.error("初始化共現網絡圖失敗:", error);
        container.innerHTML = `
            <div class="d-flex align-items-center justify-content-center h-100 text-white">
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle display-4 mb-3 text-danger"></i>
                    <p>加載關聯圖時發生錯誤: ${error.message}</p>
                </div>
            </div>
        `;
    }
}


/**
 * 初始化關鍵詞分布圖表
 * @param {Object|String} keywordsDistribution - 關鍵詞分布數據或JSON字符串
 */
function initKeywordsChart(keywordsDistribution) {
    if (!keywordsDistribution) {
        console.warn("沒有提供關鍵詞分布數據");
        return;
    }

    const ctx = document.getElementById('keywordsChart');
    if (!ctx) return;

    try {
        // 確保數據是JavaScript對象
        const data = typeof keywordsDistribution === 'string' ? JSON.parse(keywordsDistribution) : keywordsDistribution;

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
    } catch (error) {
        console.error("初始化關鍵詞分布圖表失敗:", error);
    }
}


/**
 * 初始化實體分布圖表
 * @param {Object|String} entitiesDistribution - 實體分布數據或JSON字符串
 */
function initEntitiesChart(entitiesDistribution) {
    if (!entitiesDistribution) {
        console.warn("沒有提供實體分布數據");
        return;
    }

    const ctx = document.getElementById('entitiesChart');
    if (!ctx) return;

    try {
        // 確保數據是JavaScript對象
        const data = typeof entitiesDistribution === 'string' ? JSON.parse(entitiesDistribution) : entitiesDistribution;

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
    } catch (error) {
        console.error("初始化實體分布圖表失敗:", error);
    }
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
 * 初始化情緒分布餅圖
 * @param {Object|String} sentimentData - 情緒分析數據或JSON字符串
 */
function initSentimentDistributionChart(sentimentData) {
    if (!sentimentData) {
        console.warn("沒有提供情緒分析數據");
        return;
    }

    const ctx = document.getElementById('sentimentDistributionChart');
    if (!ctx) return;

    try {
        // 確保數據是JavaScript對象
        const data = typeof sentimentData === 'string' ? JSON.parse(sentimentData) : sentimentData;

        // 準備圖表資料
        const labels = ['正面', '負面', '中立'];
        const counts = [
            data.positive_count || 0,
            data.negative_count || 0,
            data.neutral_count || 0
        ];
        const total = counts.reduce((a, b) => a + b, 0);

        // 圖表顏色
        const colors = {
            backgroundColor: [
                'rgba(40, 167, 69, 0.7)',  // 正面 - 綠色
                'rgba(220, 53, 69, 0.7)',  // 負面 - 紅色
                'rgba(108, 117, 125, 0.7)'  // 中立 - 灰色
            ],
            borderColor: [
                'rgba(40, 167, 69, 1)',
                'rgba(220, 53, 69, 1)',
                'rgba(108, 117, 125, 1)'
            ]
        };

        // 創建圖表
        const sentimentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colors.backgroundColor,
                    borderColor: colors.borderColor,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: '情緒分析分布',
                        color: '#fff'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.7)'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error("初始化情緒分布餅圖失敗:", error);
    }
}

/**
 * 初始化情緒隨時間變化趨勢圖
 * @param {Object|String} timeSeriesData - 時間序列數據或JSON字符串
 * @param {Object|String} sentimentTimeData - 情緒時間序列數據或JSON字符串
 */
function initSentimentTimeSeriesChart(timeSeriesData, sentimentTimeData) {
    if (!timeSeriesData || !sentimentTimeData) {
        console.warn("沒有提供情緒時間序列數據");
        return;
    }

    const ctx = document.getElementById('sentimentTimeSeriesChart');
    if (!ctx) return;

    try {
        // 確保數據是JavaScript對象
        const timeData = typeof timeSeriesData === 'string' ? JSON.parse(timeSeriesData) : timeSeriesData;
        const sentimentData = typeof sentimentTimeData === 'string' ? JSON.parse(sentimentTimeData) : sentimentTimeData;

        // 將數據按日期排序
        timeData.sort((a, b) => new Date(a.date) - new Date(b.date));

        // 準備圖表資料
        const labels = timeData.map(item => formatDate(item.date));

        // 準備情緒數據
        // 這裡假設sentimentData包含了日期對應的正面、負面和中立情緒數量
        const positiveData = [];
        const negativeData = [];
        const neutralData = [];

        // 對於每個日期，找到對應的情緒數據
        for (const dateItem of timeData) {
            const date = dateItem.date;
            const sentiment = sentimentData[date] || { positive: 0, negative: 0, neutral: 0 };
            positiveData.push(sentiment.positive || 0);
            negativeData.push(sentiment.negative || 0);
            neutralData.push(sentiment.neutral || 0);
        }

        // 創建圖表
        const sentimentTimeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: '正面',
                        data: positiveData,
                        fill: false,
                        borderColor: 'rgba(40, 167, 69, 1)',  // 綠色
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(40, 167, 69, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(40, 167, 69, 1)'
                    },
                    {
                        label: '負面',
                        data: negativeData,
                        fill: false,
                        borderColor: 'rgba(220, 53, 69, 1)',  // 紅色
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(220, 53, 69, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(220, 53, 69, 1)'
                    },
                    {
                        label: '中立',
                        data: neutralData,
                        fill: false,
                        borderColor: 'rgba(108, 117, 125, 1)',  // 灰色
                        backgroundColor: 'rgba(108, 117, 125, 0.1)',
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(108, 117, 125, 1)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgba(108, 117, 125, 1)'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    title: {
                        display: true,
                        text: '情緒隨時間變化趨勢',
                        color: '#fff'
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: 'rgba(255, 255, 255, 0.7)'
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
    } catch (error) {
        console.error("初始化情緒隨時間變化趨勢圖失敗:", error);
    }
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

// 當視窗調整大小時重繪圖表
window.addEventListener('resize', function() {
    // 重新初始化共現網絡圖
    if (typeof cooccurrenceData !== 'undefined' && cooccurrenceData) {
        initCooccurrenceNetwork(cooccurrenceData);
    }
});
