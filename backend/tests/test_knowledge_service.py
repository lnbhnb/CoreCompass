from app.services import knowledge_service


def test_match_returns_hybrid_always():
    """SDLC 始终返回 hybrid（校园推荐）"""
    r = knowledge_service.match_references("任意课题")
    assert r["sdlc"] == "hybrid"


def test_match_flask_by_keyword():
    """课题含 web/api 关键词匹配 Flask"""
    r = knowledge_service.match_references("做一个 web api 后端项目")
    assert "flask" in r["projects"]


def test_match_taro_by_keyword():
    """课题含小程序关键词匹配 Taro"""
    r = knowledge_service.match_references("微信小程序跨端开发")
    assert "taro" in r["projects"]


def test_match_contest_by_keyword():
    """课题含挑战杯关键词匹配"""
    r = knowledge_service.match_references("准备挑战杯比赛")
    assert "challenge-cup" in r["contests"]


def test_match_returns_at_most_2_projects():
    """项目匹配最多 2 个（避免 prompt 过长）"""
    r = knowledge_service.match_references("web api 全栈 小程序")
    assert len(r["projects"]) <= 2


def test_load_excerpt_returns_string():
    """摘录返回字符串且非空"""
    excerpt = knowledge_service.load_excerpt("sdlc", "hybrid")
    assert isinstance(excerpt, str) and len(excerpt) > 50


def test_build_prompt_context_includes_all_matched():
    """构造的上下文包含所有匹配素材"""
    refs = {"sdlc": "hybrid", "projects": ["flask"], "contests": []}
    ctx = knowledge_service.build_prompt_context(refs)
    assert "混合模型" in ctx
    assert "Flask" in ctx


def test_build_prompt_context_length_bounded():
    """上下文总长 ≤ 4000 字符"""
    refs = {"sdlc": "hybrid", "projects": ["flask", "fastapi"], "contests": ["challenge-cup"]}
    ctx = knowledge_service.build_prompt_context(refs)
    assert len(ctx) <= 4000
