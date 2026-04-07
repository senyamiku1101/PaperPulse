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
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# OpenAlex 过滤器：限制在 Aerospace Engineering (subfield id: 2202)
OPENALEX_TOPIC_FILTER = "primary_topic.subfield.id:2202,type:article"

# 搜索配置
MAX_PAPERS_PER_QUERY = int(os.getenv("MAX_PAPERS_PER_QUERY", "200"))
REQUEST_DELAY = 0.5  # OpenAlex polite pool 最小请求间隔（秒）
ANALYSIS_DELAY = 1.0  # DeepSeek 请求间隔（秒）

# 风扇噪声研究搜索词
SEARCH_QUERIES = [
    # 斜切口短舱进气道
    "drooped intake",
    "scarfed intake",
    "short intake",
    "nacelle",
]

# 子主题关键词分类（用于趋势分析）
SUBTOPIC_KEYWORDS = {
    "短舱进气道": ["drooped intake", "scarfed intake", "short intake", "nacelle"],
    "单音噪声": ["tonal", "tone", "blade passing frequency", "BPF", "rotor-stator interaction"],
    "宽频噪声": ["broadband", "turbulent", "boundary layer", "trailing edge", "leading edge"],
    "实验测量": ["measurement", "experimental", "test", "array", "microphone", "acoustic test", "wind tunnel", "experiment", "PIV", "hot-wire", "flow visualization"],
    "声衬设计": ["liner", "acoustic treatment", "sound absorption", "impedance", "duct lining"],
    "数值模拟": ["CFD", "computational", "simulation", "LES", "DNS", "RANS", "numerical"],
    "解析方法": ["analytical", "theoretical", "modeling", "prediction", "mathematical"],
    "流动控制": ["active control", "passive control", "serpentine", "chevron", "serration"],
}

# 追踪的课题组
RESEARCH_GROUPS = [
    {
        "id": "group_mit_gt",
        "name": "MIT Gas Turbine Lab",
        "institution": "Massachusetts Institute of Technology",
        "institution_query": "Massachusetts Institute of Technology",
        "description": "涡轮机械气动声学与风扇噪声研究",
        "author_ids": [],
    },
    {
        "id": "group_purdue",
        "name": "Purdue University Acoustics",
        "institution": "Purdue University",
        "institution_query": "Purdue University",
        "description": "航空声学与风扇噪声实验研究",
        "author_ids": [],
    },
    {
        "id": "group_cambridge",
        "name": "Cambridge Whittle Lab",
        "institution": "University of Cambridge",
        "institution_query": "University of Cambridge",
        "description": "航空发动机风扇噪声与气动声学",
        "author_ids": [],
    },
    {
        "id": "group_dlr",
        "name": "DLR German Aerospace Center",
        "institution": "Deutsches Zentrum für Luft- und Raumfahrt",
        "institution_query": "Deutsches Zentrum für Luft- und Raumfahrt",
        "description": "航空发动机噪声研究",
        "author_ids": [],
    },
    {
        "id": "group_onera",
        "name": "ONERA The French Aerospace Lab",
        "institution": "Office National d'Etudes et de Recherches Aérospatiales",
        "institution_query": "Office National d'Etudes et de Recherches Aérospatiales",
        "description": "风扇噪声预测与控制",
        "author_ids": [],
    },
    {
        "id": "group_buaa",
        "name": "Beihang University",
        "institution": "Beihang University",
        "institution_query": "Beihang University",
        "description": "风扇气动声学与噪声控制",
        "author_ids": [],
    },
    {
        "id": "group_sjtu",
        "name": "Shanghai Jiao Tong University",
        "institution": "Shanghai Jiao Tong University",
        "institution_query": "Shanghai Jiao Tong University",
        "description": "旋转机械噪声与振动",
        "author_ids": [],
    },
    {
        "id": "group_nasa_glenn",
        "name": "NASA Glenn Research Center",
        "institution": "NASA Glenn Research Center",
        "institution_query": "NASA Glenn Research Center",
        "description": "航空发动机风扇噪声研究",
        "author_ids": [],
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
