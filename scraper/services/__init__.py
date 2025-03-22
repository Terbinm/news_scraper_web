# 初始化服務模組
# 使這個目錄被視為一個Python套件

from .analysis_service import (
    get_category_colors,
    get_keywords_analysis,
    get_entities_analysis,
    get_entity_type_distribution,
    get_pos_distribution
)

from .task_service import (
    execute_scraper_task
)

from .scraper_service import (
    run_scraper,
    process_scraper_results
)

__all__ = [
    'get_category_colors',
    'get_keywords_analysis',
    'get_entities_analysis',
    'get_entity_type_distribution',
    'get_pos_distribution',
    'execute_scraper_task',
    'run_scraper',
    'process_scraper_results'
]