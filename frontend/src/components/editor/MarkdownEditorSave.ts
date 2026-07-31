import { migrateMathStrings } from '@tiptap/extension-mathematics'
import { AUTO_SAVE_DELAY_MS } from '../../constants/app'
import { parseMarkdownDoc } from './MarkdownEditorMarkdown'
import { buildPlainTextDoc, normalizePastedText, sanitizeMarkdownSource } from './MarkdownEditorMarkdownUtil'
import type { MarkdownEditorContext } from './MarkdownEditorContext'

let autoSaveTimer: number | null = null
let saveInFlight = false
let queuedContent: string | null = null

export function useMarkdownEditorSave(ctx: MarkdownEditorContext) {
  function clearAutoSaveTimer(): void {
    if (autoSaveTimer !== null) {
      window.clearTimeout(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  async function enqueueSave(nodeId: string, content: string): Promise<void> {
    if (!ctx.activeNode.value || ctx.activeNode.value.id !== nodeId) {
      return
    }
    if (content === ctx.lastSavedContent.value) {
      return
    }

    if (saveInFlight) {
      queuedContent = content
      return
    }

    saveInFlight = true
    try {
      const saved = await ctx.store.saveActiveNodeContent(nodeId, content)
      if (saved && ctx.activeNode.value?.id === nodeId) {
        ctx.lastSavedContent.value = content
      }
    } finally {
      saveInFlight = false
      if (queuedContent !== null) {
        const nextContent = queuedContent
        queuedContent = null
        if (ctx.activeNode.value?.id === nodeId && nextContent !== ctx.lastSavedContent.value) {
          await enqueueSave(nodeId, nextContent)
        }
      }
    }
  }

  function scheduleAutoSave(nodeId: string, content: string): void {
    clearAutoSaveTimer()
    autoSaveTimer = window.setTimeout(() => {
      void enqueueSave(nodeId, content)
    }, AUTO_SAVE_DELAY_MS)
  }

  function resetAutoSave(): void {
    clearAutoSaveTimer()
    saveInFlight = false
    queuedContent = null
  }

  function syncEditorContent(content: string): void {
    if (!ctx.editor.value) return

    const normalized = normalizePastedText(content)

    // Empty content: set an empty doc directly, skip the markdown parser
    if (!normalized) {
      ctx.isApplyingExternalContent.value = true
      ctx.editor.value.commands.setContent({ type: 'doc', content: [{ type: 'paragraph' }] }, {
        emitUpdate: false,
      })
      ctx.isApplyingExternalContent.value = false
      return
    }

    const source = sanitizeMarkdownSource(normalized)
    const parsedDoc = parseMarkdownDoc(ctx.editor.value, source)

    ctx.isApplyingExternalContent.value = true
    ctx.editor.value.commands.setContent(parsedDoc ?? buildPlainTextDoc(source), {
      emitUpdate: false,
    })
    migrateMathStrings(ctx.editor.value)
    ctx.isApplyingExternalContent.value = false
  }

  return { syncEditorContent, resetAutoSave, clearAutoSaveTimer, scheduleAutoSave, enqueueSave }
}

export type MarkdownEditorSave = ReturnType<typeof useMarkdownEditorSave>
