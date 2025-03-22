import logging
import threading
from ..models import ScrapeJob

logger = logging.getLogger(__name__)


def execute_scraper_task(job_id):
    """
    使用執行緒執行爬蟲任務的服務函數

    Args:
        job_id: ScrapeJob 的 ID

    Returns:
        thread: 啟動的線程實例
    """
    thread = threading.Thread(target=_scraper_thread, args=(job_id,))
    thread.daemon = True  # 設置為守護線程，主程序結束時會自動退出
    thread.start()
    logger.info(f"啟動爬蟲任務 {job_id} 的執行線程")
    return thread


def _scraper_thread(job_id):
    """
    爬蟲執行緒函數

    Args:
        job_id: ScrapeJob 的 ID
    """
    logger.info(f"開始執行爬蟲任務 {job_id}")
    try:
        # 使用非交互式matplotlib後端
        import matplotlib
        matplotlib.use('Agg')

        # 導入 run_scraper 函數
        from ..services.scraper_service import run_scraper
        run_scraper(job_id)

        logger.info(f"爬蟲任務 {job_id} 完成")
    except Exception as e:
        logger.error(f"爬蟲任務 {job_id} 失敗: {e}", exc_info=True)

        try:
            # 更新任務狀態為失敗
            job = ScrapeJob.objects.get(id=job_id)
            job.status = 'failed'
            job.save()
        except:
            pass