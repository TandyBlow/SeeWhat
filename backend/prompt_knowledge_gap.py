"""
Knowledge-gap handler prompt template and builder.
Split from handler_prompts.
"""

# ── Knowledge Gap Handler ─────────────────────────────────────────────

KNOWLEDGE_GAP_SUGGEST_SYSTEM = """用户的知识树在这个领域几乎为空。

用温暖、关心的语气建议用户先去创建前置知识点（给1-2个具体建议）。
如果用户表示想继续，就从最基础的定义开始教。
这不是拒绝用户，而是帮他建立正确的学习路径。

返回JSON：{"message": "...", "action": "hint", "sub_topic": ""}"""


def build_knowledge_gap_prompt(
    node_name: str,
    gap_result: dict,
    knowledge_profile: str = "",
) -> list[dict]:
    """Assemble prompt for suggesting the user go create prerequisite KPs."""
    domain = gap_result.get("domain_tag", "相关")
    related_count = gap_result.get("related_domain_nodes", 0)
    user_lines = [
        f"当前主题：{node_name}",
        f"用户在此领域（{domain}）只有 {related_count} 个知识点，基础薄弱。",
        "\n建议用户先出去创建前置知识点（给1-2个具体建议）。",
    ]
    if knowledge_profile:
        user_lines.append(f"\n{knowledge_profile}")
    return [
        {"role": "system", "content": KNOWLEDGE_GAP_SUGGEST_SYSTEM},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
