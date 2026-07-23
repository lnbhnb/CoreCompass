import json
import re
import time
import logging
from typing import Optional
from openai import OpenAI
from json_repair import repair_json
from app import config
from app.llm.prompts import (INITIAL_PLAN_PROMPT, INITIAL_PLAN_PROMPT_WITH_KB,
                             REPLAN_PROMPT, VALIDATE_FALLBACK_PROMPT,
                             FALLBACK_INITIAL_PLAN, FALLBACK_REPLAN_PROPOSAL)

logger = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


class LLMUnavailableError(Exception):
    pass


def get_client() -> OpenAI:
    """兼容 DeepSeek / 豆包 / 任何 OpenAI 协议模型"""
    global _client
    if _client is None:
        if not config.DEEPSEEK_API_KEY:
            raise LLMUnavailableError("未配置 DEEPSEEK_API_KEY")
        _client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
    return _client


def parse_json_robust(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(repair_json(text))
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if m:
        try:
            return json.loads(repair_json(m.group(1)))
        except Exception:
            pass
    raise json.JSONDecodeError("无法解析为 JSON", text, 0)


def call_llm(prompt: str, max_retries: int = 1) -> dict:
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = get_client().chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3)
            return parse_json_robust(resp.choices[0].message.content)
        except Exception as e:
            logger.warning(f"LLM 调用失败 attempt={attempt}: {e}")
            last_err = e
            if attempt < max_retries:
                time.sleep(2)
    raise LLMUnavailableError(str(last_err))


def generate_initial_plan(topic, team_size, deadline):
    try:
        return call_llm(INITIAL_PLAN_PROMPT.format(
            topic=topic, team_size=team_size, deadline=deadline))
    except LLMUnavailableError:
        logger.error("初始计划 LLM 失败，用 fallback 模板")
        return FALLBACK_INITIAL_PLAN


def generate_initial_plan_with_kb(topic, team_size, deadline, kb_context):
    """带知识库素材的初始计划生成"""
    try:
        return call_llm(INITIAL_PLAN_PROMPT_WITH_KB.format(
            topic=topic, team_size=team_size,
            deadline=deadline, kb_context=kb_context))
    except LLMUnavailableError:
        logger.error("带知识库的初始计划 LLM 失败，用 fallback")
        return FALLBACK_INITIAL_PLAN


def generate_replan_proposal(remaining_days, team_size, gap_days, tasks_json):
    try:
        return call_llm(REPLAN_PROMPT.format(
            remaining_days=remaining_days, team_size=team_size,
            gap_days=gap_days, tasks_json=tasks_json))
    except LLMUnavailableError:
        logger.error("重规划 LLM 失败，用 fallback")
        return FALLBACK_REPLAN_PROPOSAL


def validate_with_llm(milestone_name, file_type, content):
    try:
        return call_llm(VALIDATE_FALLBACK_PROMPT.format(
            milestone_name=milestone_name, file_type=file_type, content=content[:8000]))
    except LLMUnavailableError:
        return {"pass": False, "reasons": ["AI 校验失败，请人工确认"]}
