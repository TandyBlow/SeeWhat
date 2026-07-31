import type { MarkdownEditorChatDoc } from './MarkdownEditorChatDoc'
import type { MarkdownEditorContext } from './MarkdownEditorContext'

export function useMarkdownEditorConcept(ctx: MarkdownEditorContext, doc: MarkdownEditorChatDoc) {
  async function onRegenerate() {
    if (ctx.isBusy.value || !ctx.activeNode.value) return
    const treeCtx = buildTreeContext()
    const result = await ctx.regenerateWithTreeContext(treeCtx)
    if (result) {
      doc.rebuildTranscriptFromMessages()
    }
  }

  async function onMarkConcept() {
    if (ctx.isBusy.value) return
    const name = window.prompt(ctx.t('editor.conceptNamePrompt'))
    if (!name || !name.trim()) return
    const result = await ctx.markConcept(name.trim())
    if (result) {
      doc.rebuildTranscriptFromMessages()
      await ctx.store.loadNode(ctx.activeNode.value?.id || '')
      // Record transition for context chain
      ctx.recordNavigationTransition(
        ctx.activeNode.value?.id || null,
        result.node_id,
        `在学习「${ctx.activeNode.value?.name || '未知'}」时标记了概念「${name.trim()}」`,
      )
    }
  }

  async function onConceptClick(conceptName: string) {
    if (ctx.isBusy.value || ctx.markedConceptNames.value.has(conceptName)) return
    // Check if concept already exists as a child node in the tree
    const existingChildNames = new Set((ctx.childNodes.value || []).map(n => n.name))
    if (existingChildNames.has(conceptName)) {
      ctx.markedConceptNames.value = new Set([...ctx.markedConceptNames.value, conceptName])
      return
    }
    const result = await ctx.markConcept(conceptName)
    if (result) {
      await ctx.store.loadNode(ctx.activeNode.value?.id || '')
      ctx.recordNavigationTransition(
        ctx.activeNode.value?.id || null,
        result.node_id,
        `在学习「${ctx.activeNode.value?.name || '未知'}」时标记了概念「${conceptName}」`,
      )
    }
  }

  function buildTreeContext(): string {
    if (!ctx.activeNode.value) return ''
    const parts: string[] = []
    const path = ctx.pathNodes.value || []
    if (path.length > 0) {
      parts.push('知识路径: ' + path.map(n => n.name).join(' → '))
    }
    parts.push('当前知识点: ' + ctx.activeNode.value.name)
    const children = ctx.childNodes.value || []
    if (children.length > 0) {
      parts.push('子知识点: ' + children.map(n => n.name).join(', '))
    }
    return parts.join('\n')
  }

  return { onRegenerate, onMarkConcept, onConceptClick }
}
