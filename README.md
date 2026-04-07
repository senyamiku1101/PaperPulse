# PaperPulse

面向特定研究方向的学术文献自动追踪与分析系统。默认配置针对**风扇噪声**方向，覆盖噪声测量、宽频噪声、单音噪声、声衬设计等子领域。

## 功能特性

- **自动论文抓取** — 从 OpenAlex 批量获取相关论文
- **AI 智能分析** — DeepSeek 生成中文综述、研究方法、创新点、结论、相关度评分
- **趋势热力图** — 1960 年至今的研究趋势可视化（5 年间隔）
- **课题组追踪** — 自动追踪全球主要研究团队
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
python -m scripts.main --analyze-only   # 仅 AI 分析
python -m scripts.main --trends-only    # 仅生成趋势数据
python -m scripts.main --groups-only    # 仅追踪课题组
python -m scripts.main --summary-only   # 仅生成汇总统计
```

## GitHub Pages 部署

### 1. 配置 Secrets

进入仓库 Settings → Secrets and variables → Actions，添加：

- `DEEPSEEK_API_KEY` — DeepSeek API 密钥（必需）
- `OPENALEX_API_KEY` — OpenAlex API 密钥（可选，提高请求限制）

### 2. 启用 GitHub Pages

Settings → Pages → Source: `main` branch, `/ (root)`

### 3. 自动更新

GitHub Actions 每周一 UTC 02:00 自动运行，也可在 Actions 页面手动触发。

## 项目结构

```
PaperPulse/
├── index.html                    # 前端（纯 HTML/CSS/JS）
├── data/                         # JSON 数据文件
│   ├── papers.json               # 论文数据库
│   ├── trends.json               # 趋势热力图数据
│   ├── groups.json               # 课题组数据
│   └── summary.json              # 汇总统计
├── scripts/                      # Python 脚本
│   ├── config.py                 # 共享配置
│   ├── openalex_client.py        # OpenAlex API 封装
│   ├── deepseek_client.py        # DeepSeek AI 封装
│   ├── fetch_papers.py           # 论文抓取
│   ├── analyze_papers.py         # AI 分析
│   ├── generate_trends.py        # 趋势数据生成
│   ├── track_groups.py           # 课题组追踪
│   ├── generate_summary.py       # 汇总统计生成
│   └── main.py                   # 主入口
├── .github/workflows/update.yml  # GitHub Actions 工作流
├── requirements.txt              # Python 依赖
├── .gitignore
└── README.md
```

## 自定义研究方向

编辑 `scripts/config.py` 中的 `SEARCH_QUERIES` 列表，替换为你的研究方向的搜索词：

```python
SEARCH_QUERIES = [
    "your research topic",
    "related keyword",
    # ...
]
```

同时更新 `RESEARCH_GROUPS` 为你想追踪的课题组。

## 许可证

MIT License
