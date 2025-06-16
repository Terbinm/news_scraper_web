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