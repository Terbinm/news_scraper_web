/**
 * 初始化關鍵詞文字雲
 * @param {Object|String} keywordsData - 關鍵詞分布數據或JSON字符串
 */
function initWordCloud(keywordsData) {
    if (!keywordsData) {
        console.warn("沒有提供關鍵詞數據");
        return;
    }

    // 確保容器元素存在
    const container = document.getElementById('wordCloudContainer');
    if (!container) return;

    try {
        // 清除原有內容
        container.innerHTML = '';

        // 確保數據是JavaScript對象
        const data = typeof keywordsData === 'string' ? JSON.parse(keywordsData) : keywordsData;

        // 設置SVG尺寸
        const width = container.clientWidth;
        const height = 500;

        // 創建SVG元素
        const svg = d3.select(container)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height])
            .attr("style", "max-width: 100%; height: auto;");

        // 準備文字雲數據
        let cloudWords = data.map(item => ({
            text: item.word,
            size: calculateFontSize(item.total, data),
            count: item.total,
            pos: item.pos,
        }));

        // 限制詞彙數量
        cloudWords = cloudWords.slice(0, 50);

        // 詞性顏色映射
        const posColors = {
            'Na': "#17a2b8",  // 普通名詞
            'Nb': "#28a745",  // 專有名詞
            'Nc': "#ffc107",  // 地方名詞
            'default': "#6c757d"
        };

        // 創建文字雲佈局
        const layout = d3.layout.cloud()
            .size([width, height])
            .words(cloudWords)
            .padding(5)
            .rotate(() => 0) // 不旋轉文字
            .font("Impact")
            .fontSize(d => d.size)
            .spiral("archimedean") // 使用阿基米德螺旋線排列
            .on("end", draw);

        // 開始佈局計算
        layout.start();

        // 繪製文字雲
        function draw(words) {
            const group = svg.append("g")
                .attr("transform", `translate(${width / 2},${height / 2})`)
                .selectAll("text")
                .data(words)
                .enter().append("text")
                .style("font-family", "Impact, 'Noto Sans TC', sans-serif")
                .style("fill", d => posColors[d.pos] || posColors.default)
                .attr("text-anchor", "middle")
                .attr("transform", d => `translate(${d.x},${d.y})`)
                .attr("font-size", d => `${d.size}px`)
                .text(d => d.text)
                .style("cursor", "pointer")
                .style("opacity", 0.9)
                .on("mouseover", function(event, d) {
                    d3.select(this)
                        .style("opacity", 1)
                        .style("filter", "drop-shadow(0 0 2px rgba(255,255,255,0.8))")
                        .transition()
                        .duration(200)
                        .attr("font-size", `${d.size * 1.2}px`);

                    showTooltip(event, d);
                })
                .on("mouseout", function(event, d) {
                    d3.select(this)
                        .style("opacity", 0.9)
                        .style("filter", "none")
                        .transition()
                        .duration(200)
                        .attr("font-size", `${d.size}px`);

                    hideTooltip();
                })
                .on("click", function(event, d) {
                    // 點擊詞彙時將其添加到搜索框
                    addTermToSearchBox(d.text);
                });
        }

        // 添加提示框
        const tooltip = d3.select("body").append("div")
            .attr("class", "custom-tooltip")
            .style("position", "absolute")
            .style("visibility", "hidden")
            .style("background-color", "rgba(0, 0, 0, 0.8)")
            .style("color", "white")
            .style("padding", "8px")
            .style("border-radius", "4px")
            .style("font-size", "14px")
            .style("pointer-events", "none")
            .style("z-index", "1000");

        function showTooltip(event, d) {
            const posNames = {
                'Na': '普通名詞',
                'Nb': '專有名詞',
                'Nc': '地方名詞'
            };
            const posName = posNames[d.pos] || d.pos;

            tooltip
                .style("visibility", "visible")
                .html(`<strong>${d.text}</strong><br/>詞性: ${posName}<br/>出現頻率: ${d.count}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        }

        function hideTooltip() {
            tooltip.style("visibility", "hidden");
        }

        // 更新重新生成按鈕事件
        const refreshBtn = document.getElementById('wordCloudRefreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                initWordCloud(keywordsData);
            });
        }

        // 添加詞性圖例
        const legend = svg.append("g")
            .attr("class", "legend")
            .attr("transform", `translate(20, 20)`);

        const legendItems = [
            { label: "普通名詞 (Na)", color: posColors.Na },
            { label: "專有名詞 (Nb)", color: posColors.Nb },
            { label: "地方名詞 (Nc)", color: posColors.Nc }
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

    } catch (error) {
        console.error("初始化文字雲失敗:", error);
        container.innerHTML = `
            <div class="d-flex align-items-center justify-content-center h-100 text-white">
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle display-4 mb-3 text-danger"></i>
                    <p>加載文字雲時發生錯誤: ${error.message}</p>
                </div>
            </div>
        `;
    }
}

/**
 * 計算文字雲中字體大小
 * @param {number} count - 詞彙出現次數
 * @param {Array} data - 所有詞彙數據
 * @returns {number} 字體大小 (像素)
 */
function calculateFontSize(count, data) {
    // 找出最大和最小頻率值
    const maxCount = Math.max(...data.map(item => item.total));
    const minCount = Math.min(...data.map(item => item.total));

    // 設定字體大小的範圍
    const minSize = 12;
    const maxSize = 60;

    // 如果最大值和最小值相同，返回中間大小
    if (maxCount === minCount) {
        return (minSize + maxSize) / 2;
    }

    // 根據詞彙頻率線性映射到字體大小
    return minSize + ((count - minCount) / (maxCount - minCount)) * (maxSize - minSize);
}

/**
 * 將詞彙添加到搜索框
 * @param {string} term - 要添加的詞彙
 */
function addTermToSearchBox(term) {
    const searchInput = document.getElementById('id_search_terms');
    if (!searchInput) return;

    // 獲取當前搜索框的值
    let currentValue = searchInput.value.trim();

    // 檢查詞彙是否已經存在
    if (currentValue.split(',').map(t => t.trim()).includes(term)) {
        return; // 已存在，不添加
    }

    // 添加新詞彙
    if (currentValue) {
        searchInput.value = currentValue + ', ' + term;
    } else {
        searchInput.value = term;
    }

    // 用動畫效果提示用戶
    searchInput.classList.add('highlight-animation');
    setTimeout(() => {
        searchInput.classList.remove('highlight-animation');
    }, 1000);

    // 提示用戶已添加詞彙
    const toast = document.createElement('div');
    toast.className = 'toast position-fixed bottom-0 end-0 m-3';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.innerHTML = `
        <div class="toast-header bg-info text-white">
            <i class="bi bi-info-circle me-2"></i>
            <strong class="me-auto">詞彙已添加</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body bg-dark text-light">
            已將「${term}」添加至搜索框
        </div>
    `;
    document.body.appendChild(toast);

    // 顯示通知
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // 通知消失後移除DOM元素
    toast.addEventListener('hidden.bs.toast', function () {
        document.body.removeChild(toast);
    });
}

// 在文檔就緒時調用
document.addEventListener('DOMContentLoaded', function() {
    // 初始化文字雲（在其他圖表初始化之後）
    if (typeof keywordsDistribution !== 'undefined' && keywordsDistribution) {
        initWordCloud(keywordsDistribution);
    }
});

// 當窗口大小改變時重繪文字雲
window.addEventListener('resize', function() {
    // 如果有關鍵詞數據，重新初始化文字雲
    if (typeof keywordsDistribution !== 'undefined' && keywordsDistribution) {
        // 使用防抖函數避免頻繁重繪
        clearTimeout(window.resizeTimeout);
        window.resizeTimeout = setTimeout(function() {
            initWordCloud(keywordsDistribution);
        }, 250);
    }
});