import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge_base"
MAX_PROJECTS = 2
MAX_EXCERPT_CHARS = 1200  # 单个素材摘录上限
MAX_CONTEXT_CHARS = 4000  # 上下文总长上限

_index_cache = None


def _load_index() -> dict:
    global _index_cache
    if _index_cache is None:
        with open(KB_DIR / "index.json", encoding="utf-8") as f:
            _index_cache = json.load(f)
    return _index_cache


def match_references(topic: str) -> dict:
    """按课题关键词匹配三类素材。

    匹配策略（避免空召回）：
    1. 课题含显式关键词 → 精确召回
    2. 课题包含项目类型子串（如"小程序"、"api"、"web"）→ 模糊召回
    3. 都未命中 → 回退到通用 web 项目（flask），保证 LLM 始终有参考
    """
    topic_lower = topic.lower()
    index = _load_index()

    def _match(category: str) -> list:
        matched = []
        for name, meta in index.get(category, {}).items():
            if any(k.lower() in topic_lower for k in meta["keywords"]):
                matched.append(name)
        return matched

    projects = _match("projects")[:MAX_PROJECTS]
    # 兜底：若未匹配到任何项目，按课题特征回退
    if not projects:
        if any(k in topic_lower for k in ["小程序", "跨端", "微信", "taro"]):
            projects = ["taro"]
        elif any(k in topic_lower for k in ["异步", "restful", "openapi", "fastapi"]):
            projects = ["fastapi"]
        elif any(k in topic_lower for k in ["cms", "内容管理", "admin", "django"]):
            projects = ["django"]
        else:
            projects = ["flask"]  # 通用 web 后端兜底

    return {
        "sdlc": "hybrid",  # 校园团队始终推荐混合模型
        "projects": projects,
        "contests": _match("contests"),
    }


def load_excerpt(category: str, name: str) -> str:
    """读取素材文件并截取关键段落"""
    index = _load_index()
    meta = index.get(category, {}).get(name)
    if not meta:
        return ""
    file_path = KB_DIR / meta["file"]
    if not file_path.exists():
        return ""
    content = file_path.read_text(encoding="utf-8")
    # 去掉 YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            content = content[end + 3:].strip()
    # 截取前 N 字符
    return content[:MAX_EXCERPT_CHARS]


def build_prompt_context(refs: dict) -> str:
    """构造注入 prompt 的上下文文本"""
    parts = []

    sdlc_excerpt = load_excerpt("sdlc", refs["sdlc"])
    if sdlc_excerpt:
        parts.append(f"【SDLC 模型参考：{refs['sdlc']}】\n{sdlc_excerpt}")

    for proj in refs.get("projects", []):
        proj_excerpt = load_excerpt("projects", proj)
        if proj_excerpt:
            parts.append(f"【相似项目参考：{proj}】\n{proj_excerpt}")

    for contest in refs.get("contests", []):
        contest_excerpt = load_excerpt("contests", contest)
        if contest_excerpt:
            parts.append(f"【比赛日程参考：{contest}】\n{contest_excerpt}")

    ctx = "\n\n".join(parts)
    return ctx[:MAX_CONTEXT_CHARS]
