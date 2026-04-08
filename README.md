# PaperPulse

面向特定研究方向的学术文献自动追踪与分析系统。默认配置针对**风扇噪声**方向，覆盖进气道设计、风扇噪声、压气机气动声学、进气畸变等子领域。

示例 https://senyamiku1101.github.io/PaperPulse/

## 功能特性

- **自动论文抓取** — 从 OpenAlex 批量获取相关论文（8 并发，cursor 分页，每关键词最多 1000 篇）
- **智能论文筛选** — 三级漏斗策略：著名期刊直接保留 → 指定课题组直接保留 → 其余按引用量+时间分层筛选
- **AI 智能分析** — DeepSeek 生成中文综述、研究方法、创新点、结论、相关度评分（2020 年及以后逐篇分析，相关性 < 2 自动移除）
- **趋势热力图** — 1960 年至今的研究趋势可视化（5 年间隔），按主题分类生成 AI 研究综述
- **课题组自动发现** — 基于机构归一化 + 共著网络聚类自动识别研究团队，无需手动配置
- **智能问答** — 基于论文库的 AI 对话问答
- **自动更新** — GitHub Actions 每周自动更新 + GitHub Pages 静态部署

## 快速开始

### 环境要求

- Python 3.12+
- DeepSeek API Key（[获取地址](https://platform.deepseek.com/)）

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/PaperPulse.git
cd PaperPulse

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DEEPSEEK_API_KEY

# 4. 运行数据更新
python -m scripts.main --all

# 5. 启动本地服务器查看
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

### 单独运行各步骤

```bash
python -m scripts.main --fetch-only     # 仅抓取论文
python -m scripts.main --analyze-only   # 仅 AI 分析（含筛选）
python -m scripts.main --trends-only    # 仅生成趋势数据
python -m scripts.main --groups-only    # 仅自动发现课题组
python -m scripts.main --summary-only   # 仅生成汇总统计
python -m scripts.main --no-filter      # 跳过筛选步骤
python -m scripts.main --clear --yes    # 清空 data/ 目录
```

## 数据处理流程

```
OpenAlex 抓取 (8并发)
    ↓
论文筛选 (三级漏斗)
    ├─ ISSN 匹配著名期刊 → 全部保留
    ├─ 课题组作者匹配 → 全部保留
    └─ 引用量+时间分层筛选
    ↓
AI 分析 (5并发)
    ├─ 2020年及以后 → 逐篇 DeepSeek 分析，相关性 < 2 移除
    └─ 2019年及更早 → 跳过逐篇分析
    ↓
趋势数据生成
    ├─ 按主题分组论文
    └─ 每个主题单独生成 AI 研究综述（引用作者年份）
    ↓
课题组自动发现
    ├─ 机构名称归一化 (difflib 相似度匹配)
    ├─ 共著网络构建 → 连通分量 = 课题组
    └─ 自动命名: 机构名 – 核心作者姓氏
    ↓
汇总统计 + JSON 输出
```

## GitHub Pages 部署

### 1. 配置 Secrets

进入仓库 Settings → Secrets and variables → Actions，添加：

- `DEEPSEEK_API_KEY` — DeepSeek API 密钥（必需）
- `OPENALEX_API_KEY` — OpenAlex API 密钥（可选，提高请求限制）

### 2. 配置 Workflow 权限

Settings → Actions → General → Workflow permissions → 选择 **Read and write permissions**

### 3. 启用 GitHub Pages

Settings → Pages → Source: `main` branch, `/ (root)`

### 4. 自动更新

GitHub Actions 每周一 UTC 02:00 自动运行，也可在 Actions 页面手动触发。

## 项目结构

```
PaperPulse/
├── index.html                    # 前端（纯 HTML/CSS/JS）
├── data/                         # JSON 数据文件
│   ├── papers.json               # 论文数据库
│   ├── trends.json               # 趋势热力图数据（含主题关键词和 AI 综述）
│   ├── groups.json               # 自动发现的课题组数据
│   └── summary.json              # 汇总统计
├── scripts/                      # Python 脚本
│   ├── config.py                 # 共享配置（搜索词、主题关键词、期刊 ISSN 等）
│   ├── openalex_client.py        # OpenAlex API 封装（cursor 分页）
│   ├── deepseek_client.py        # DeepSeek AI 封装（逐篇分析 + 主题摘要）
│   ├── fetch_papers.py           # 论文抓取（8 并发）
│   ├── filtering.py              # 论文筛选（ISSN + 课题组 + 引用量漏斗）
│   ├── analyze_papers.py         # AI 分析（5 并发，2020+ 逐篇，相关性阈值）
│   ├── generate_trends.py        # 趋势数据生成（按主题分组 AI 摘要）
│   ├── discover_groups.py        # 课题组自动发现（机构归一化 + 共著聚类）
│   ├── generate_summary.py       # 汇总统计生成
│   └── main.py                   # 主入口（编排流水线）
├── tests/test_all.py             # 测试套件
├── .github/workflows/update.yml  # GitHub Actions 工作流
├── requirements.txt              # Python 依赖
├── .gitignore
└── README.md
```

## 自定义研究方向

编辑 `scripts/config.py`：

```python
# 搜索词
SEARCH_QUERIES = ["fan aeroacoustics", "compressor noise", ...]

# 主题关键词（用于热力图分类和 AI 综述）
SUBTOPIC_KEYWORDS = {
    "风扇噪声": ["fan noise", "tonal noise", "broadband noise"],
    "进气畸变": ["distortion", "inlet distortion", ...],
    ...
}

# 著名期刊 ISSN（这些期刊的论文自动保留）
PRESTIGIOUS_JOURNAL_ISSNS = {
    "0001-1452",  # AIAA Journal
    "0022-460X",  # Journal of Sound and Vibration
    ...
}

# 引用量筛选阈值
CITATION_THRESHOLDS = {
    "recent_min_citations": 1,   # 2年内
    "mid_min_citations": 3,      # 2-5年
    "old_min_citations": 5,      # 5年以上
}
```

## 更新日志

### 2026-04-08 (v0.61)
修复大量bug，现已基本稳定

### 2026-04-06 (v0.53)
初始版本，存在大量Bug

## 许可证

MIT License
