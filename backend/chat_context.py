"""
Builds the AI prompt context for single-topic turns/regeneration (reference
material, enriched context, gap warning, tone, knowledge profile fallback,
transition context, chat memories, existing notes, recent history). Also owns
conversation-text helpers and get_node_chat_memories.
"""
import logging

from database import get_db_ctx

from chat_session import _read_uploaded_file
from chat_knowledge_profile import build_knowledge_profile

logger = logging.getLogger(__name__)


def _get_recent_conversation_text(session: dict, max_messages: int = 4) -> str:
    """Get the last N messages as analysis text for concept extraction."""
    messages = session.get("messages", [])
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    parts = []
    for msg in recent:
        role = "AI" if msg["role"] == "ai" else "用户"
        content = msg.get("content", "")
        if content.strip():
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _last_user_message(session: dict) -> str:
    """Get the most recent user message from the session."""
    messages = session.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def _collect_previous_knowledge_notes(session: dict) -> list[str]:
    """Collect all knowledge_note fragments from prior AI messages in this session."""
    notes = []
    for m in session.get("messages", []):
        meta = m.get("metadata", {})
        if isinstance(meta, dict):
            note = meta.get("knowledge_note", "")
            if note and note.strip():
                notes.append(note.strip())
    return notes


def _build_conversation_context(session: dict, owner_id: str = "", current_node_id: str = "", existing_content_tail: str = "", tone: dict = None, gap_warning: str = "") -> str:
    """Build conversation context string for the AI prompt.

    Includes: reference material, filtered knowledge matches (from enrichment pipeline),
    tone instruction, gap warning, conversation history, and existing note content tail.
    Uses enriched context (concept extraction + knowledge retrieval by content) when available,
    falling back to the full knowledge profile only when enrichment hasn't run.
    """
    lines = []
    node_name = ""
    kps = session.get("knowledge_points", [])
    if kps:
        node_name = kps[0].get("title", "")

    lines.append(f"当前主题：{node_name}")

    if node_name:
        lines.append(f"\n你正在帮助用户理解「{node_name}」。")

    # Include reference material so AI doesn't forget what it's teaching
    oid = owner_id or session.get("owner_id", "")
    file_id = session.get("file_id", "")
    reference_text = session.get("reference_text", "")
    full_reference = ""
    if file_id:
        full_reference = _read_uploaded_file(oid, file_id) or ""
    if not full_reference and reference_text.strip():
        full_reference = reference_text
    if full_reference.strip():
        lines.append(f"\n【参考资料】以下是你正在讲解的原始资料，请始终基于此内容进行对话：\n{full_reference}")

    # ── Enriched context (concept extraction + knowledge retrieval by content) ──
    enriched = session.get("_enriched_context", {}) or {}
    concept_ctx = enriched.get("concept_context", "")
    personalized = enriched.get("personalized_context", "")
    expansion = enriched.get("expansion_context", "")
    def_chain = enriched.get("definition_chain", "")

    if concept_ctx:
        lines.append(f"\n{concept_ctx}")
    if personalized:
        lines.append(f"\n{personalized}")
    if expansion:
        lines.append(f"\n{expansion}")
    if def_chain:
        lines.append(f"\n{def_chain}")

    # ── Gap warning (from code-level knowledge_gap_detector) ──
    if gap_warning:
        lines.append(f"\n{gap_warning}")

    # ── Tone instruction (from code-level tone_wrapper) ──
    if tone and tone.get("instruction"):
        lines.append(f"\n{tone['instruction']}")

    # Fallback: full knowledge profile only if enrichment didn't produce personalized context
    # This prevents the "same KP every turn" problem when enrichment is working
    if not personalized:
        nid = current_node_id or session.get("node_id", "")
        if oid and nid:
            profile = build_knowledge_profile(oid, nid)
            if profile:
                lines.append(f"\n{profile}")

    # Declare authority: when knowledge profile and reference material both exist,
    # the reference material is the ground truth.
    nid = current_node_id or session.get("node_id", "")
    if full_reference.strip() and oid and nid:
        lines.append("\n⚠️ 重要提示：当知识档案中的术语/标签与【参考资料】的实际内容不一致时，以【参考资料】为准。知识档案中的节点名称只是用户的命名标签，不能替代参考资料中的真实定义。如果知识档案中的术语在参考资料中找不到对应，直接问用户这个术语是什么，不要猜测。")

    # Inject transition context (context chain awareness)
    transition_ctx = session.get("transition_context", "")
    if transition_ctx:
        lines.append(f"\n【用户跳转背景】{transition_ctx}")

    # Inject new learnings since last visit (for return visits)
    previous_node_id = session.get("previous_node_id")
    if previous_node_id and oid and nid:
        try:
            from context_chain_service import get_new_learnings_since_last_visit
            new_learnings = get_new_learnings_since_last_visit(oid, nid)
            if new_learnings:
                lines.append("\n【自上次访问后的新学习内容】")
                for nl in new_learnings:
                    lines.append(f"  - 在「{nl.get('node_name', '未知')}」中学习了：{nl.get('learned_concepts', '')}")
        except Exception as e:
            logger.warning("Failed to fetch new learnings for node %s: %s", nid, e)
    if oid and nid:
        try:
            memories = get_node_chat_memories(oid, nid, limit=5)
            if memories:
                lines.append("\n【本知识点历史对话摘要】以下是之前关于此知识点的对话压缩记录，请参考其中的讨论内容和学习进度，避免重复已讨论过的话题：")
                for i, mem in enumerate(memories):
                    lines.append(f"  [历史对话{i+1}] {mem['compressed_summary']}")
        except Exception as e:
            logger.warning("Failed to fetch chat memories for node %s: %s", nid, e)
    if existing_content_tail.strip():
        lines.append(f"\n【已有笔记内容（尾部）】请检查以下内容，避免重复记录已存在的知识点，并匹配其记叙方式和排版格式：\n{existing_content_tail}")

    # Extract chapter titles from already-generated content for continuity awareness
    generated = session.get("generated_content", "")
    if generated.strip():
        import re as _re
        chapters = _re.findall(r'^##\s+(.+)$', generated, _re.MULTILINE)
        if chapters:
            lines.append(f"\n【已生成的章节】已写过的章节标题：{'、'.join(chapters)}。新生成的笔记章节应避免与这些章节标题重复，内容上也要自然衔接而非另起炉灶。")

    # Inject previous knowledge notes from this session for dedup
    prev_notes = _collect_previous_knowledge_notes(session)
    if prev_notes:
        lines.append("\n【已记录的知识笔记】以下笔记已在本对话中生成过，请勿在本次knowledge_note中重复这些内容（只记录本轮出现的新知识）：")
        for i, note in enumerate(prev_notes):
            lines.append(f"  [{i+1}] {note}")

    # Include recent conversation (last 20 messages to stay within context)
    messages = session.get("messages", [])
    recent = messages[-20:] if len(messages) > 20 else messages
    if recent:
        lines.append("\n对话历史：")
        for msg in recent:
            role_label = "AI" if msg["role"] == "ai" else "用户"
            lines.append(f"{role_label}: {msg['content']}")

    return "\n".join(lines)


def get_node_chat_memories(owner_id: str, node_id: str, limit: int = 5) -> list:
    """Fetch compressed chat memories for a node, most recent first."""
    with get_db_ctx() as conn:
        rows = conn.execute(
            """SELECT * FROM node_chat_memories
               WHERE owner_id = ? AND node_id = ?
               ORDER BY compressed_at DESC LIMIT ?""",
            (owner_id, node_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]
