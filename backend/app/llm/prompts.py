INITIAL_PLAN_PROMPT = """你是项目拆解专家。根据课题生成里程碑和周任务。
课题：{topic}
团队人数：{team_size}
截止日期：{deadline}

输出严格 JSON（不要 markdown 代码块）：
{{
  "milestones": [
    {{"name": "...", "expected_artifact_type": "sql|md|code|json|other", "tasks": [
      {{"title": "...", "description": "...", "priority": "core|optional",
        "difficulty": "high|mid|low", "est_effort_days": 1.5, "week": 1}}
    ]}}
  ]
}}
要求：4-6 个里程碑，按 SDLC 顺序；每里程碑 2-4 任务；core/optional 比例约 6:4。
"""

REPLAN_PROMPT = """项目出现进度缺口，需要砍/降级任务。
剩余天数：{remaining_days}
团队人数：{team_size}
缺口（人天）：{gap_days}
当前未完成任务：
{tasks_json}

输出严格 JSON：
{{
  "cut_tasks": [任务id],
  "downgrade_tasks": [{{"id": 任务id, "from": "原难度", "to": "降级后难度", "new_effort": 0.5}}],
  "rationale": "简短说明"
}}
铁律：只能砍 priority=optional 的任务；core 任务只能降级不能砍；降级后 est_effort 必须减少。
"""

VALIDATE_FALLBACK_PROMPT = """校验以下文件是否符合里程碑要求。
里程碑名：{milestone_name}
文件类型：{file_type}
文件内容（截断）：
---
{content}
---
输出严格 JSON：{{"pass": true/false, "reasons": ["原因1"]}}
"""

FALLBACK_INITIAL_PLAN = {
    "milestones": [
        {"name": "需求分析", "expected_artifact_type": "md", "tasks": [
            {"title": "需求文档", "description": "撰写需求规格说明", "priority": "core",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 1}]},
        {"name": "数据库设计", "expected_artifact_type": "sql", "tasks": [
            {"title": "ER 图与表结构", "description": "设计核心表", "priority": "core",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 2}]},
        {"name": "核心实现", "expected_artifact_type": "code", "tasks": [
            {"title": "后端 API", "description": "实现核心接口", "priority": "core",
             "difficulty": "high", "est_effort_days": 2.0, "week": 3},
            {"title": "前端页面", "description": "实现主要界面", "priority": "optional",
             "difficulty": "mid", "est_effort_days": 1.5, "week": 3}]},
        {"name": "测试与部署", "expected_artifact_type": "md", "tasks": [
            {"title": "测试报告", "description": "功能测试与缺陷修复", "priority": "optional",
             "difficulty": "mid", "est_effort_days": 1.0, "week": 4}]}]
}

FALLBACK_REPLAN_PROPOSAL = {
    "cut_tasks": [], "downgrade_tasks": [],
    "rationale": "AI 提案失败，建议手动降级可选任务"
}
