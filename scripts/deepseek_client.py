"""DeepSeek AI API 封装模块"""

import json
import logging
import time
from typing import Optional

from openai import OpenAI

from scripts.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

logger = logging.getLogger(__name__)

# 论文分析系统提示
ANALYSIS_SYSTEM_PROMPT = """你是一位风扇噪声领域的学术专家。请分析以下论文的标题和摘要，返回JSON格式的分析结果。

JSON结构要求：
{
  "summary": "中文综述（150-300字），概括论文核心内容",
  "methods": "研究方法（中文，100-200字），说明使用的关键研究方法",
  "innovations": "创新点（中文，列出主要创新贡献）",
  "conclusions": "结论（中文，总结主要结论）",
  "relevance_score": 8,
  "keywords": ["keyword1", "keyword2", "keyword3"]
}

relevance_score评分标准（1-10）：
10: 直接研究风扇噪声
8-9: 与风扇噪声高度相关（如气动声学、叶轮机械噪声）
5-7: 有一定相关性（如通用声学方法）
1-4: 弱相关

请严格返回JSON格式，不要添加其他内容。"""

# 问答系统提示
QA_SYSTEM_PROMPT = """你是风扇噪声研究领域的专家助手。根据提供的论文资料回答用户的问题。
要求：
1. 回答使用中文
2. 引用具体论文时注明作者和年份
3. 如果资料不足以回答，请如实说明
4. 尽量综合多篇论文的观点"""


class DeepSeekClient:
    """DeepSeek API 客户端，使用 OpenAI 兼容接口"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.base_url = base_url or DEEPSEEK_BASE_URL

        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置，请在 .env 文件或环境变量中配置")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _call(
        self,
        messages: list[dict],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        json_mode: bool = False,
    ) -> str:
        """底层 API 调用，带重试"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"DeepSeek API 调用失败，{wait}秒后重试: {e}")
                    time.sleep(wait)
                else:
                    raise

    def analyze_paper(self, title: str, abstract: str) -> dict:
        """分析单篇论文，返回结构化分析结果"""
        if not abstract.strip():
            return {
                "summary": "无摘要",
                "methods": "无摘要",
                "innovations": "无摘要",
                "conclusions": "无摘要",
                "relevance_score": 0,
                "keywords": [],
                "analyzed_at": "",
            }

        user_message = f"论文标题：{title}\n\n论文摘要：{abstract}"

        try:
            result_text = self._call(
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1500,
                temperature=0.2,
                json_mode=True,
            )
            analysis = json.loads(result_text)

            # 确保包含所有必要字段
            defaults = {
                "summary": "",
                "methods": "",
                "innovations": "",
                "conclusions": "",
                "relevance_score": 5,
                "keywords": [],
            }
            for key, default in defaults.items():
                if key not in analysis:
                    analysis[key] = default

            # 类型校验
            analysis["relevance_score"] = max(1, min(10, int(analysis.get("relevance_score", 5))))
            if not isinstance(analysis.get("keywords"), list):
                analysis["keywords"] = []

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"DeepSeek 返回非法 JSON: {e}")
            return {
                "summary": "",
                "methods": "",
                "innovations": "",
                "conclusions": "",
                "relevance_score": 5,
                "keywords": [],
                "error": True,
                "raw": result_text if 'result_text' in dir() else "",
            }
        except Exception as e:
            logger.error(f"论文分析失败 '{title[:50]}': {e}")
            raise

    def answer_question(self, question: str, paper_contexts: list[dict]) -> str:
        """基于论文上下文回答问题"""
        # 构建论文上下文
        context_parts = []
        for i, p in enumerate(paper_contexts, 1):
            analysis = p.get("analysis", {})
            if analysis and not analysis.get("error"):
                context_parts.append(
                    f"[{i}] 论文：{p.get('title', '')} ({p.get('year', '')})\n"
                    f"    综述：{analysis.get('summary', '')}\n"
                    f"    关键词：{', '.join(analysis.get('keywords', []))}"
                )
            else:
                context_parts.append(
                    f"[{i}] 论文：{p.get('title', '')} ({p.get('year', '')})\n"
                    f"    摘要：{p.get('abstract', '')[:300]}"
                )

        context = "\n\n".join(context_parts)

        user_message = f"参考资料：\n{context}\n\n用户问题：{question}"

        return self._call(
            messages=[
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=2000,
            temperature=0.5,
        )