import threading
import logging
from .services import run_scraper

logger = logging.getLogger(__name__)


def run_scraper_task(job_id):
    """
    使用執行緒執行爬蟲任務

    Args:
        job_id: ScrapeJob的ID
    """
    thread = threading.Thread(target=_scraper_thread, args=(job_id,))
    thread.daemon = True  # 設置為守護線程，主程序結束時會自動退出
    thread.start()
    return thread

def _scraper_thread(job_id):
    """
    爬蟲執行緒函數
    """
    logger.info(f"開始執行爬蟲任務 {job_id}")
    try:
        # 使用非交互式matplotlib後端
        import matplotlib
        matplotlib.use('Agg')

        run_scraper(job_id)
        logger.info(f"爬蟲任務 {job_id} 完成")
    except Exception as e:
        logger.error(f"爬蟲任務 {job_id} 失敗: {e}", exc_info=True)
