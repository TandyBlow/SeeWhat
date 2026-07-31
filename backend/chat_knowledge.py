"""
Knowledge-document consolidation: merges accumulated knowledge_note fragments
into a deduplicated Markdown document via LLM, plus the node-content-tail reader.
"""
import json
import logging

from database import get_db_ctx

from chat_llm import call_deepseek

logger = logging.getLogger(__name__)


# ── Knowledge Consolidation ──────────────────────────────────────────

CONSOLIDATE_KNOWLEDGE_SYSTEM = """你是一个知识整理专家。你的任务是将对话中生成的知识笔记片段合并成一份干净、无重复、结构清晰的知识文档。

# 输入

你会收到：
1. 对话中累积的知识笔记（可能包含重复、渐进修正、碎片化表述）
2. 参考资料原文（如果有）
3. 对话主题名称

# 你的任务

将这些碎片化的知识笔记整合成一份完整的知识文档。

# 整理规则

1. **去重合并**：同一个概念可能被记录了多次（初次记录、补充修正、换表述重述），只保留最准确、最完整的版本。如果两段说的是一件事，合并它们，不要各留一份。**即使两条笔记的措辞不同，只要描述的是同一个知识点，就是重复——必须合并。当不确定是否重复时，宁可合并也不要保留两份。**
2. **渐进修正优先**：如果同一概念有多条记录，保留对话后期修正后的版本。后续修正的版本比初始版本更准确。
3. **删除元对话**：删除"AI问"、"用户答"、"我们讨论了"、"AI通过用户笔记中的关键词推断"、"推测"、"似乎"等对话过程描述，只保留知识内容本身。任何描述 AI 推理过程（如"AI根据XX推断出YY"）或对话动态的句子必须完全删除。**尤其删除所有"修正链路"——不要写"先以为是X，后来纠正为Y""最初理解为A，经过讨论后修正为B"等句子。只保留最终正确的版本，删除修正过程的任何描述。如果整条笔记只是对前一条的修正，合并后只保留修正后的版本。**
4. **结构化组织**：用 ## 标题按知识点分组。一组相关概念放在一起。按照从基础到进阶的逻辑顺序排列。
5. **保留学习者口吻**：用学习者自己的表述（从对话中提取），不改写成教科书语气。
6. **公式完整准确**：保留对话中确认过的公式，用 $...$ 或 $$...$$ 格式。禁止脑补未确认的公式。
7. **保留关键例子**：对话中如果出现了有助于理解的具体例子，保留它。
8. **紧凑无废话**：删除过渡句、重复定义，同一概念只说一次。整体篇幅控制在合理范围内。
9. **连贯成文**：合并后的文档应该是一篇逻辑流畅的完整文章，而不是笔记片段的堆砌。调整片段之间的顺序和过渡，让上下文自然衔接。合并内容相近的段落，删除衔接生硬的片段边界。最终读者应该感觉这是一气呵成写的，而非多段拼凑的。

# 输出格式

返回JSON：{"content": "整理后的Markdown知识文档"}
content字段中是整理后的完整知识文档，用 ## 标题分组，按逻辑顺序排列。不要加"整理后""以下是整理结果"等引导语。"""


def consolidate_knowledge_content(
    messages: list,
    node_name: str = "",
    reference_text: str = "",
    existing_content: str = "",
) -> str:
    """Merge accumulated knowledge notes into a clean, deduplicated document via LLM."""
    # Build the knowledge fragments from messages
    fragments: list[str] = []
    for m in messages:
        meta = m.get("metadata", {})
        note = ""
        if isinstance(meta, dict):
            note = meta.get("knowledge_note", "")
        if note and note.strip():
            fragments.append(note.strip())

    if not fragments:
        # No knowledge notes to consolidate
        return ""

    # Build conversation-derived knowledge for the LLM
    knowledge_text = "\n\n---\n\n".join(
        f"[片段{i + 1}] {f}" for i, f in enumerate(fragments)
    )

    context_parts = [f"当前主题：{node_name}"]
    if reference_text.strip():
        # Truncate reference to reasonable length for consolidation
        ref = reference_text.strip()
        if len(ref) > 6000:
            ref = ref[:6000] + "\n...(参考资料过长，已截断)"
        context_parts.append(f"\n【参考资料】\n{ref}")
    if existing_content.strip():
        existing = existing_content.strip()
        if len(existing) > 3000:
            existing = existing[-3000:]
        context_parts.append(f"\n【节点现有内容（尾部）】\n{existing}")

    user_prompt = f"""{chr(10).join(context_parts)}

【需要整理的碎片化知识笔记】（共{len(fragments)}条）

{knowledge_text}

请将这些碎片整理成一份干净、无重复的知识文档。"""

    try:
        response = call_deepseek([
            {"role": "system", "content": CONSOLIDATE_KNOWLEDGE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ])
        # The response should be JSON with a "content" field since we use json_object mode
        result = json.loads(response)
        return result.get("content", "")
    except (json.JSONDecodeError, KeyError):
        # If JSON parsing fails, try to use the raw response as markdown
        if response and len(response) > 20:
            return response
        return ""


# ── Helpers ──────────────────────────────────────────────────────────

def _get_node_content_tail(node_id: str, owner_id: str, tail_chars: int = 800) -> str:
    """Read the tail portion of a node's content for dedup and style matching."""
    with get_db_ctx() as conn:
        row = conn.execute(
            "SELECT content FROM nodes WHERE id = ? AND owner_id = ? AND is_deleted = 0",
            (node_id, owner_id),
        ).fetchone()
    if not row or not row["content"]:
        return ""
    content = row["content"]
    if len(content) <= tail_chars:
        return content
    return "...(上文省略)\n" + content[-tail_chars:]
