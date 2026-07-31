import { Extension } from '@tiptap/core'
import { Plugin, PluginKey, TextSelection } from 'prosemirror-state'
import type { EditorState } from 'prosemirror-state'
import type { MarkdownEditorContext } from './MarkdownEditorContext'

export function createMarkdownEditorExtensions(ctx: MarkdownEditorContext) {
  /**
   * Custom extension that handles 'table' tokens from marked's lexer (when gfm: true).
   * @tiptap/markdown doesn't have a built-in handler for table tokens — its
   * parseFallbackToken drops them. This handler converts marked table tokens
   * directly to TipTap table/tableRow/tableHeader/tableCell JSON without going
   * through generateJSON (which would fail when paragraph is disabled in StarterKit).
   */
  const TableMarkdownParser = Extension.create({
    name: 'tableMarkdownParser',
    // These extension fields are read by @tiptap/markdown's MarkdownManager.registerExtension
    markdownTokenName: 'table',
    parseMarkdown: (token: any, helpers: any) => {
      const headerRow: any[] = token.header || []
      const bodyRows: any[][] = token.rows || []

      const allRows: any[] = []

      // Header row
      if (headerRow.length > 0) {
        const headerCells = headerRow.map((cell: any) => ({
          type: 'tableHeader',
          attrs: { colspan: 1, rowspan: 1, colwidth: null, align: cell.align ?? null },
          content: [{
            type: 'paragraph',
            content: helpers.parseInline(cell.tokens || []),
          }],
        }))
        allRows.push({ type: 'tableRow', content: headerCells })
      }

      // Body rows (skip the separator row which is row index 0 after header;
      // marked already filtered out the separator, so bodyRows are the actual data rows)
      for (const row of bodyRows) {
        const cells = row.map((cell: any) => ({
          type: 'tableCell',
          attrs: { colspan: 1, rowspan: 1, colwidth: null, align: cell.align ?? null },
          content: [{
            type: 'paragraph',
            content: helpers.parseInline(cell.tokens || []),
          }],
        }))
        allRows.push({ type: 'tableRow', content: cells })
      }

      return { type: 'table', content: allRows }
    },
  })

  const LockedParagraphAttr = Extension.create({
    name: 'lockedParagraphAttr',
    addGlobalAttributes() {
      return [
        {
          types: ['paragraph'],
          attributes: {
            locked: {
              default: null,
              parseHTML: element => element.getAttribute('data-locked'),
              renderHTML: attributes => {
                if (attributes.locked != null) {
                  return { 'data-locked': attributes.locked }
                }
                return {}
              },
            },
          },
        },
      ]
    },
  })

  // ── Locked node plugin ─────────────────────────────────────────────

  function isPositionInLockedNode(state: EditorState, pos: number): boolean {
    const $pos = state.doc.resolve(pos)
    return $pos.parent.attrs?.locked ?? false
  }

  const lockedNodePluginKey = new PluginKey('lockedNodes')
  const lockedNodePlugin = new Plugin({
    key: lockedNodePluginKey,
    props: {
      handleClick(view, pos) {
        if (ctx.chatMode.value !== 'text_input') return false
        // Redirect clicks inside locked nodes to the editable area
        if (isPositionInLockedNode(view.state, pos)) {
          const docSize = view.state.doc.content.size
          const tr = view.state.tr
          tr.setSelection(TextSelection.create(view.state.doc, docSize))
          view.dispatch(tr)
          view.focus()
          return true
        }
        return false
      },
      handleTextInput(view, from, _to, text) {
        if (ctx.chatMode.value !== 'text_input') return false
        // Block typing inside locked nodes - redirect to end of editable area
        if (isPositionInLockedNode(view.state, from)) {
          const docSize = view.state.doc.content.size
          const tr = view.state.tr
          tr.setSelection(TextSelection.create(view.state.doc, docSize))
          tr.insertText(text)
          view.dispatch(tr)
          return true
        }
        return false
      },
    },
    filterTransaction(tr, state) {
      if (!tr.docChanged) return true
      if (ctx.isApplyingExternalContent.value) return true

      const lockedRanges: {from: number, to: number}[] = []
      state.doc.descendants((node, pos) => {
        if (node.attrs?.locked) {
          lockedRanges.push({from: pos, to: pos + node.nodeSize})
        }
      })

      if (lockedRanges.length === 0) return true

      for (const step of tr.steps) {
        const map = step.getMap()
        let blocked = false
        map.forEach((oldStart: number, oldEnd: number, newStart: number, newEnd: number) => {
          if (blocked) return
          for (const range of lockedRanges) {
            if (oldStart < range.to && oldEnd > range.from) { blocked = true; return }
            if (newStart < range.to && newEnd > range.from) { blocked = true; return }
          }
        })
        if (blocked) return false
      }

      return true
    },
  })

  const LockedNodes = Extension.create({
    name: 'lockedNodes',
    addProseMirrorPlugins() {
      return [lockedNodePlugin]
    },
  })

  return { TableMarkdownParser, LockedParagraphAttr, LockedNodes }
}
