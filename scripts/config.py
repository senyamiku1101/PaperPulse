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
MAX_PAPERS_PER_QUERY = int(os.getenv("MAX_PAPERS_PER_QUERY", "2000"))
REQUEST_DELAY = 0.5  # OpenAlex polite pool 最小请求间隔（秒）
ANALYSIS_DELAY = 1.0  # DeepSeek 请求间隔（秒）

# 风扇噪声研究搜索词
SEARCH_QUERIES = [
    # ── 斜切口短舱进气道 ──
    "drooped intake",
    "scarfed intake",
    "short intake",
    "turbofan intake",

    # ── 风扇噪声 ──
    "fan noise",
    "compressor noise",
    "tonal noise",
    "broadband noise",

    # ── 压气机气动声学 ──
    "compressor aeroacoustics",
    "fan aeroacoustics",

    # ── 稳定性建模 ──
    "actuator disk",
    "body force model",
    "Moore Greitzer",
    "streamline curvature",

    # ── 进气畸变 ──
    "distortion",
    "inlet distortion",
    "circumferential distortion",
    "radial distortion",
    "steady flow distortion",
    "static pressure distortion",
]

# 子主题关键词分类（用于趋势分析）
SUBTOPIC_KEYWORDS = {
    "斜切口短舱进气道": ["drooped intake", "scarfed intake", "short intake", "turbofan intake"],
    "风扇噪声": ["fan noise", "tonal noise", "compressor noise", "broadband noise"],
    "压气机气动声学": ["compressor aeroacoustics", "fan aeroacoustics"],
    "稳定性建模": ["analytical", "theoretical", "modeling", "prediction", "mathematical", "actuator disk", "body force model", "streamline curvature"],
    "进气畸变": ["distortion", "inlet distortion", "circumferential distortion", "radial distortion", "steady flow distortion", "static pressure distortion", "total pressure distortion"],
	"实验研究": ["wind tunnel", "experiment", "PIV", "hot-wire", "flow visualization", "measurement", "experimental", "test", "array", "microphone", "acoustic test"],
	"数值方法": ["CFD", "computational", "simulation", "LES", "DNS", "RANS", "numerical", ],
}

# ==================== 论文筛选配置 ====================

# 著名期刊（以 ISSN 匹配，论文全部保留）
PRESTIGIOUS_JOURNAL_ISSNS = {
    # 航空航天顶级期刊
    "0001-1452",   # AIAA Journal
    "0021-8669",   # Journal of Aircraft
    "0748-4658",   # Journal of Propulsion and Power
    "1270-9638",   # Aerospace Science and Technology
    "0376-0421",   # Progress in Aerospace Sciences
    "0001-9240",   # Aeronautical Journal
    "1000-9361",   # Chinese Journal of Aeronautics
    "0742-4795",   # J. Eng. Gas Turbines and Power
    "0889-504X",   # Journal of Turbomachinery
    "0022-0825",   # J. Eng. for Power (→JEGTP前身)
    "0021-9223",   # J. Basic Engineering
    # 声学顶级期刊
    "0022-460X",   # Journal of Sound and Vibration
    "0001-4966",   # Journal of the Acoustical Society of America
    "0003-682X",   # Applied Acoustics
    "1610-1928",   # Acta Acustica
    "0736-2501",   # Noise Control Engineering Journal
    # 流体力学
    "0022-1120",   # Journal of Fluid Mechanics
    "1070-6631",   # Physics of Fluids
    "0899-8213",   # Theoretical and Computational Fluid Dynamics
    "0723-4864",   # Experiments in Fluids
    # 综合性期刊
    "0028-0836",   # Nature
    "0036-8075",   # Science
    "1364-5021",   # Proceedings of the Royal Society A
    "2045-2322",   # Scientific Reports
    "1932-6203",   # PLOS ONE
}

# 引用量筛选阈值（按论文年龄分层）
CITATION_THRESHOLDS = {
    "recent_days": 730,       # 2年内视为"近期"
    "recent_min_citations": 1,     # 近期论文最低引用
    "mid_days": 1825,         # 5年内视为"中期"
    "mid_min_citations": 3,        # 中期论文最低引用
    "old_min_citations": 5,        # 5年以上论文最低引用
    "old_min_cites_per_year": 1,   # 5年以上年均最低引用
}

# 当领域论文总数低于此值时，跳过引用量筛选（保留全部）
LOW_VOLUME_THRESHOLD = 300


# 追踪的课题组
RESEARCH_GROUPS = [
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
