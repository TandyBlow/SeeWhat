"""
Line-by-line reading mode prompt templates and builders.
Split from handler_prompts.
"""

# ── Line-by-Line Mode Handlers ────────────────────────────────────────

LINE_BY_LINE_EXPLAIN_SYSTEM = """你是一个知识导师，正在陪用户逐句阅读一份文档。

铁律：
- 只解释当前这一句。绝对不要提及后面还没讲到的内容。禁止"随后会介绍""后面会看到""接下来"等向前引用。禁止总结整段或整节。
- 解释控制在1-3句话。你不是在写综述，只讲当前这一句。
- 如果当前句涉及的前置知识用户尚未掌握，简要指出缺少什么即可，不要展开讲那个前置知识。

你的每次回复：
1. 用 > 引用当前句原文，换行后写解释。格式：> 原文\n\n解释内容
2. 解释这一句。利用【知识点结构】理解涉及的概念及其前置知识，自然地融入解释中
3. 如果【个性化知识关联】中有用户已掌握的相关内容，指出具体在哪个概念上有怎样的关联
4. 数学公式用 $...$ 或 $$...$$ 包裹

返回JSON：{"message": "> 原文\\n\\n解释内容", "reason": "简短标注"}"""


LINE_BY_LINE_ANSWER_SYSTEM = """你是一个知识导师。用户对当前正在阅读的段落提出了疑问或表示不理解。

回复策略（按优先级判断）：
1. 用户是否缺少前置知识？— 看【知识点结构】中列出的前置知识。如果用户明显没掌握这些前置概念，不要展开解释当前内容，而是明确指出他需要先学什么："要理解这个概念，你需要先了解XX和YY。你的知识树里好像还没有这些，要不要先去建一下？"——这不是拒绝，是帮他建立正确的学习路径。
2. 用户有前置知识但不理解你的解释？— 换个角度重新解释，用更具体的例子或更简单的语言。不需要问"要不要展开"，直接展开。
3. 用户只是确认（"嗯""懂了""继续"）？— 这不是由你处理的场景，你不会收到这类消息。

回复格式：
- 用 > 引用当前段落原文
- 数学公式用 $...$ 或 $$...$$ 包裹
- 回复控制在2-5句话

返回JSON：{"message": "完整回复", "reason": "简短标注"}"""


def build_line_by_line_explain_prompt(
    current_segment: str,
    progress: str,
    knowledge_profile: str = "",
    gap_warning: str = "",
    tone_instruction: str = "",
    recent_history: str = "",
    context_window: str = "",
    position_marker: str = "",
    concept_context: str = "",
    personalized_context: str = "",
    expansion_context: str = "",
) -> list[dict]:
    """Assemble prompt for explaining the next document segment."""
    user_lines = []
    # Context window — AI sees nearby segments, not the entire file
    if context_window:
        user_lines.append(f"【文档上下文】（当前位置附近的段落，供参考）\n{context_window}")
    if position_marker:
        user_lines.append(f"【{position_marker}】")
    if gap_warning:
        user_lines.append(gap_warning)
    if tone_instruction:
        user_lines.append(tone_instruction)
    if knowledge_profile:
        user_lines.append(knowledge_profile)
    if concept_context:
        user_lines.append(concept_context)
    if personalized_context:
        user_lines.append(personalized_context)
    if expansion_context:
        user_lines.append(expansion_context)
    user_lines.append(f"【{progress}】请解释下面这句话：\n\n{current_segment}")
    if recent_history:
        user_lines.append(f"\n最近对话：\n{recent_history}")
    return [
        {"role": "system", "content": LINE_BY_LINE_EXPLAIN_SYSTEM},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


def build_line_by_line_answer_prompt(
    current_segment: str,
    progress: str,
    user_question: str,
    knowledge_profile: str = "",
    gap_warning: str = "",
    tone_instruction: str = "",
    recent_history: str = "",
    context_window: str = "",
    position_marker: str = "",
    concept_context: str = "",
    personalized_context: str = "",
    expansion_context: str = "",
    definition_chain: str = "",
) -> list[dict]:
    """Assemble prompt for answering a user question in line-by-line mode."""
    user_lines = []
    # Context window — nearby segments for orientation
    if context_window:
        user_lines.append(f"【文档上下文】（当前位置附近的段落）\n{context_window}")
    if position_marker:
        user_lines.append(f"【{position_marker}】")
    if gap_warning:
        user_lines.append(gap_warning)
    if tone_instruction:
        user_lines.append(tone_instruction)
    if definition_chain:
        user_lines.append(definition_chain)
    if knowledge_profile:
        user_lines.append(knowledge_profile)
    if concept_context:
        user_lines.append(concept_context)
    if personalized_context:
        user_lines.append(personalized_context)
    if expansion_context:
        user_lines.append(expansion_context)
    user_lines.append(f"【{progress}】当前句子：\n\n{current_segment}")
    user_lines.append(f"\n用户问：{user_question}")
    user_lines.append(
        "\n判断用户是缺少前置知识还是需要换角度解释。"
        "缺少前置知识 → 建议去学习具体的原子知识点。"
        "需要换角度解释 → 直接展开，不要问'要不要展开'。"
    )
    if recent_history:
        user_lines.append(f"\n最近对话：\n{recent_history}")
    return [
        {"role": "system", "content": LINE_BY_LINE_ANSWER_SYSTEM},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
