"""论文筛选模块（已弃用 - 引用图谱遍历天然产出相关论文，无需筛选）"""

import logging

logger = logging.getLogger(__name__)


def run_filter_pipeline() -> int:
    """空操作，保持接口兼容"""
    logger.info("论文筛选已跳过（引用图谱模式无需筛选）")
    return 0
