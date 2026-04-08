# PaperPulse项目说明

---

## 1. 系统概述

PaperPulse 是一个面向特定研究方向的学术文献自动追踪与分析系统。默认配置针对**风扇噪声**方向，覆盖噪声测量、宽频噪声、单音噪声、声衬设计等子领域。

**核心能力：**
- 自动从 OpenAlex 抓取论文
- DeepSeek AI 生成中文综述、研究方法、创新点、结论、相关度评分
- 1960 年至今的研究趋势热力图（5 年间隔）
- 课题组追踪
- 基于论文库的 AI 对话问答
- GitHub Actions 自动更新 + GitHub Pages 静态部署

---

## 2. 项目结构

```
PaperPulse/
├── index.html                          # 前端（纯 HTML/CSS/JS，~4200 行）
├── data/                               # 数据文件，以json格式保存
├── scripts/                            # 代码文件
├── .github/workflows/                  # github工件流
├── CLAUDE.md                           # Claude Code 项目说明
└── README.md                           # 项目介绍
```

---

## 3. 工作环境

### 3.1 Python 环境

python版本:3.12+

requirements.txt

### 3.2 环境变量

在项目根目录创建 `.env`（已加入 .gitignore）：

```
DEEPSEEK_API_KEY=sk-你的密钥
GITHUB_TOKEN=ghp_你的token（可选，用于抓取 GitHub 仓库）
```

### 3.3 GitHub 配置（线上部署）

1. **Secrets**：Settings → Secrets → Actions → 添加 `DEEPSEEK_API_KEY`
2. **Pages**：Settings → Pages → Source: `main` branch, `/ (root)`
3. **Actions**：自动每周一 UTC 02:00 运行，也可手动触发

---
