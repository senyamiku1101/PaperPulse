"""PaperPulse 共享配置模块"""

import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 项目路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# OpenAlex API
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "")
OPENALEX_BASE_URL = "https://api.openalex.org"
OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL", "")  # polite pool

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# 请求间隔
REQUEST_DELAY = 0.5  # OpenAlex polite pool 最小请求间隔（秒）
ANALYSIS_DELAY = 1.0  # DeepSeek 请求间隔（秒）

# 种子 DOI 文件路径
SEED_DOIS_FILE = DATA_DIR / "seed_dois.json"

# 引用图谱遍历配置
CITATION_CONFIG = {
    "max_citers_per_seed": 500,      # 每篇种子论文最多获取多少引用文献
    "max_references_per_seed": 200,  # 每篇种子论文最多获取多少参考文献
    "batch_size": 50,                # 批量获取论文的每批大小
}

# 子主题关键词分类（用于趋势热力图）
SUBTOPIC_KEYWORDS = {
    "气动声学": ["aeroacoustics", "acoustic", "noise"],
    "风扇/压气机": ["fan", "compressor", "turbomachinery", "rotor", "stator"],
    "进气道": ["intake", "inlet", "nacelle", "drooped", "scarfed"],
    "数值模拟": ["CFD", "CAA", "numerical", "simulation", "computational"],
    "实验测量": ["experiment", "measurement", "wind tunnel", "test"],
    "失速/稳定性": ["stall", "surge", "stability", "distortion"],
}


# 追踪的课题组
RESEARCH_GROUPS = [
    {
        "id": "group_cambridge",
        "name": "Cambridge Whittle Lab",
        "institution": "University of Cambridge",
        "institution_query": "University of Cambridge",
        "description": "航空发动机风扇噪声与气动声学",
        "author_ids": [],
    },
    {
        "id": "group_buaa",
        "name": "Beihang University",
        "institution": "Beihang University",
        "institution_query": "Beihang University",
        "description": "风扇气动声学与噪声控制",
        "author_ids": ["A5081338883"],
    },
    {
        "id": "group_ISVR_Southampton",
        "name": "ISVR, University of Southampton",
        "institution": "University of Southampton",
        "institution_query": "University of Southampton",
        "description": "航空发动机风扇噪声研究",
	# R. Jeremy Astley, Rie Sugimoto, Zbigniew Rarata, 
        "author_ids": ["A5111878691", "A5063240001", "A5045514304"],
    },
    {
        "id": "group_Rolls-Royce",
        "name": "Rolls-Royce",
        "institution": "Rolls-Royce",
        "institution_query": "Rolls-Royce",
        "description": "罗罗公司",
	# Peter Schwaller, Peter Schwaller, Iansteel Achunche, Prateek Mustafi
        "author_ids": ["a5012391981", "a5017217072", "a5088081377", "a5013690632"],
    },
    {
        "id": "group_LMFA",
        "name": "Fluid Mechanics and Acoustics Laboratory - LMFA UMR5509",
        "institution": "LMFA",
        "institution_query": "LMFA",
        "description": "里昂大学",
	# Christophe Bailly
        "author_ids": ["a5000644260"],
    },

]


def get_year_ranges(start: int = 1960, interval: int = 5) -> list[dict]:
    """生成 5 年间隔的年份区间列表"""
    current_year = datetime.now().year
    ranges = []
    for year in range(start, current_year + 1, interval):
        end = min(year + interval - 1, current_year)
        ranges.append({
            "period": f"{year}-{end}",
            "start_year": year,
            "end_year": end,
        })
    return ranges


YEAR_RANGES = get_year_ranges()