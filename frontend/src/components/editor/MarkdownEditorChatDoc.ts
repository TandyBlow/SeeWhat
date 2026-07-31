import { nextTick } from 'vue'
import type { JSONContent } from '@tiptap/core'
import { parseMarkdownContent } from './MarkdownEditorMarkdown'
import type { MarkdownEditorContext } from './MarkdownEditorContext'

const CHAT_PROMPT_TEXT = '想聊点啥？主动换行可以给我发送消息。我会基于我们的聊天记录来填充这个知识点的内容，当然，之后你也可以把我填充的内容剪切到其他知识点中，随你喜欢。'

export function useMarkdownEditorChatDoc(ctx: MarkdownEditorContext) {
  function getChatPromptText(): string {
    return ctx.t('editor.chatPrompt')
  }

  function startChatText() {
    ctx.chatMode.value = 'text_input'
    if (ctx.editor.value) {
      ctx.isApplyingExternalContent.value = true
      ctx.editor.value.commands.setContent({
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            attrs: { locked: 'true' },
            content: [{ type: 'text', text: getChatPromptText() }],
          },
          { type: 'paragraph' },
        ],
      }, { emitUpdate: false })
      const docSize = ctx.editor.value.state.doc.content.size
      ctx.editor.value.commands.setTextSelection(docSize)
      ctx.editor.value.commands.focus()
      ctx.isApplyingExternalContent.value = false
    }
  }

  function getLastInputParagraphText(): string {
    if (!ctx.editor.value) return ''
    let lastText = ''
    ctx.editor.value.state.doc.descendants((node) => {
      if (node.type.name === 'paragraph' && !node.attrs.locked) {
        lastText = node.textContent
      }
    })
    return lastText.trim()
  }

  function makeAllParagraphsNonEditable(node: JSONContent) {
    if (node.type === 'paragraph') {
      node.attrs = { ...(node.attrs || {}), locked: 'true' }
    }
    if (Array.isArray(node.content)) {
      for (const child of node.content) {
        makeAllParagraphsNonEditable(child)
      }
    }
  }

  function pushLockedParsedNodes(content: JSONContent[], parsed: JSONContent | null) {
    if (parsed && Array.isArray(parsed.content)) {
      for (const node of parsed.content) {
        makeAllParagraphsNonEditable(node)
        content.push(node)
      }
      return true
    }
    return false
  }

  function pushLockedSeparator(content: JSONContent[]) {
    const parsed = ctx.editor.value ? parseMarkdownContent(ctx.editor.value, '---') : null
    if (!pushLockedParsedNodes(content, parsed)) {
      content.push({
        type: 'paragraph',
        attrs: { locked: 'true' },
        content: [{ type: 'text', text: '---' }],
      })
    }
  }

  function buildInlineChatDoc(pendingUserMsg?: string): JSONContent {
    const content: JSONContent[] = []

    // Prompt paragraph
    content.push({
      type: 'paragraph',
      attrs: { locked: 'true' },
      content: [{ type: 'text', text: CHAT_PROMPT_TEXT }],
    })

    // Message history
    const msgs = ctx.messages.value
    for (let i = 0; i < msgs.length; i++) {
      const msg = msgs[i]
      if (!msg) continue
      const prefix = msg.role === 'ai' ? '**AI**: ' : '**你**: '
      const mdText = prefix + msg.content

      const parsed = ctx.editor.value ? parseMarkdownContent(ctx.editor.value, mdText) : null
      if (!pushLockedParsedNodes(content, parsed)) {
        content.push({
          type: 'paragraph',
          attrs: { locked: 'true' },
          content: [{ type: 'text', text: mdText }],
        })
      }

      // Separator between messages or before pending
      if (i < msgs.length - 1 || pendingUserMsg) {
        pushLockedSeparator(content)
      }
    }

    // Pending user message
    if (pendingUserMsg) {
      const parsed = ctx.editor.value ? parseMarkdownContent(ctx.editor.value, '**你**: ' + pendingUserMsg) : null
      if (!pushLockedParsedNodes(content, parsed)) {
        content.push({
          type: 'paragraph',
          attrs: { locked: 'true' },
          content: [{ type: 'text', text: '**你**: ' + pendingUserMsg }],
        })
      }
      pushLockedSeparator(content)

      // "让我思考一下" placeholder
      if (ctx.isBusy.value) {
        content.push({
          type: 'paragraph',
          attrs: { locked: 'true' },
          content: [{ type: 'text', text: ctx.t('editor.thinking') }],
        })
      }
    }

    // Empty input paragraph (always last, always editable)
    content.push({ type: 'paragraph' })

    return { type: 'doc', content }
  }

  function applyInlineChatDoc(doc: JSONContent) {
    if (!ctx.editor.value) return
    ctx.isApplyingExternalContent.value = true
    ctx.editor.value.commands.setContent(doc, { emitUpdate: false })
    const docSize = ctx.editor.value.state.doc.content.size
    ctx.editor.value.commands.setTextSelection(docSize)
    ctx.editor.value.commands.focus()
    ctx.isApplyingExternalContent.value = false

    nextTick(() => {
      const scrollEl = ctx.editorRef.value?.querySelector('.activity-scroll')
      if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight
    })
  }

  function rebuildTranscriptFromMessages() {
    if (!ctx.editor.value) return
    const msgs = ctx.messages.value
    if (msgs.length === 0) return
    const md = msgs
      .map(m => m.role === 'ai' ? `**AI**: ${m.content}` : `**你**: ${m.content}`)
      .join('\n\n---\n\n')
    ctx.isApplyingExternalContent.value = true
    const parsed = parseMarkdownContent(ctx.editor.value, md)
    if (parsed) {
      ctx.editor.value.commands.setContent(parsed, { emitUpdate: false })
    }
    ctx.isApplyingExternalContent.value = false
  }

  return { startChatText, getLastInputParagraphText, buildInlineChatDoc, applyInlineChatDoc, rebuildTranscriptFromMessages }
}

export type MarkdownEditorChatDoc = ReturnType<typeof useMarkdownEditorChatDoc>
