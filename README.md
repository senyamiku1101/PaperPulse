# PaperPulse

基于 DOI 引用图谱的学术文献自动追踪与分析系统。通过用户提供感兴趣论文的 DOI，自动构建引用关系网络，并利用 AI 生成中文综述与分析。

## 功能特性

- **DOI 引用图谱** — 输入种子论文 DOI，自动搜索其参考文献和引用文献，构建引用关系网络
- **关系图谱可视化** — D3.js 力导向图展示论文间引用关系，支持拖拽、缩放、筛选
- **AI 智能分析** — DeepSeek V4-Flash 生成中文综述、研究方法、创新点、结论、相关度评分
- **趋势热力图** — 1960 年至今的研究趋势可视化（5 年间隔），按用户自定义关键词分类并生成 AI 研究综述
- **课题组自动发现** — 基于机构归一化 + 共著网络聚类自动识别研究团队
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

# 4. 添加种子 DOI
# 编辑 data/seed_dois.json，添加你感兴趣的论文 DOI

# 5. 运行数据更新
python -m scripts.main --all

# 6. 启动本地服务器查看
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

### 单独运行各步骤

```bash
python -m scripts.main --fetch-only     # 仅抓取引用图谱
python -m scripts.main --analyze-only   # 仅 AI 分析
python -m scripts.main --trends-only    # 仅生成趋势数据
python -m scripts.main --groups-only    # 仅自动发现课题组
python -m scripts.main --summary-only   # 仅生成汇总统计
python -m scripts.main --clear --yes    # 清空 data/ 目录
```

## 数据处理流程

```
种子 DOI (data/seed_dois.json)
    ↓
引用图谱构建 (4并发)
    ├─ 通过 DOI 获取种子论文
    ├─ 获取种子论文的参考文献（被种子引用的论文）
    └─ 获取引用种子论文的文献
    ↓
AI 分析 (5并发)
    ├─ 2020年及以后 → 逐篇 DeepSeek 分析
    └─ 2019年及更早 → 跳过逐篇分析
    ↓
趋势数据生成
    ├─ 按自定义关键词分类论文
    └─ 每个主题单独生成 AI 研究综述
    ↓
课题组自动发现
    ├─ 机构名称归一化
    ├─ 共著网络构建 → 连通分量 = 课题组
    └─ 自动命名: 机构名 – 核心作者姓氏
    ↓
汇总统计 + JSON 输出
```

## 种子 DOI 管理

在 `data/seed_dois.json` 中管理你感兴趣的论文：

```json
[
  {
    "doi": "10.2514/1.J064898",
    "label": "Improved Generalized Eigenvalue Method for Compressor Stall Prediction"
  },
  {
    "doi": "10.1016/j.jsv.2022.117321",
    "label": "CFD/CAA coupling for fan tone noise propagation"
  }
]
```

添加新 DOI 后，运行 `python -m scripts.main --all` 或推送到 GitHub 触发自动更新。新文献会通过 `referenced_works` 自动与已有文献建立引用关联，关系图谱会显示完整的引用网络。

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

GitHub Actions 每周一 UTC 02:00 自动运行，也可在 Actions 页面手动触发。更新流程：验证种子 DOI → 运行管线 → 提交推送 `data/` 目录。

## 项目结构

```
PaperPulse/
├── index.html                    # 前端（HTML/CSS/JS + D3.js 图谱）
├── data/                         # JSON 数据文件
│   ├── seed_dois.json            # 种子 DOI 列表（用户维护）
│   ├── papers.json               # 论文数据库
│   ├── trends.json               # 趋势热力图数据
│   ├── groups.json               # 自动发现的课题组数据
│   └── summary.json              # 汇总统计
├── scripts/                      # Python 脚本
│   ├── config.py                 # 配置（API密钥、引用遍历参数、主题关键词）
│   ├── openalex_client.py        # OpenAlex API 封装（DOI解析、引用遍历、批量获取）
│   ├── deepseek_client.py        # DeepSeek AI 封装（逐篇分析 + 主题摘要）
│   ├── fetch_papers.py           # 引用图谱构建（4 并发）
│   ├── analyze_papers.py         # AI 分析（5 并发）
│   ├── generate_trends.py        # 趋势数据生成（关键词分类 + AI 摘要）
│   ├── discover_groups.py        # 课题组自动发现
│   ├── generate_summary.py       # 汇总统计生成
│   └── main.py                   # 主入口（编排流水线）
├── tests/test_all.py             # 测试套件
├── .github/workflows/update.yml  # GitHub Actions 工作流
├── requirements.txt              # Python 依赖
└── README.md
```

## 自定义配置

编辑 `scripts/config.py`：

```python
# 引用遍历参数
CITATION_CONFIG = {
    "max_citers_per_seed": 500,      # 每篇种子最多获取多少引用文献
    "max_references_per_seed": 200,  # 每篇种子最多获取多少参考文献
    "batch_size": 50,                # 批量获取每批大小
}

# 主题关键词（用于热力图分类和 AI 综述）
SUBTOPIC_KEYWORDS = {
    "气动声学": ["aeroacoustics", "acoustic", "noise"],
    "风扇/压气机": ["fan", "compressor", "turbomachinery"],
    "进气道": ["intake", "inlet", "nacelle", "drooped", "scarfed"],
    ...
}
```

## 许可证

MIT License
