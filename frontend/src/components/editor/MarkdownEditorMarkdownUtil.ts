import type { Editor, JSONContent } from '@tiptap/core'

export function stripUnknownNodes(json: JSONContent, schema: Editor['schema']): JSONContent | null {
  if (!json || typeof json !== 'object') return null;
  if (!json.type) return json;

  if (!schema.nodes[json.type]) {
    if (Array.isArray(json.content) && json.content.length > 0) {
      const strippedChildren = json.content
        .map(c => stripUnknownNodes(c, schema))
        .filter((c): c is JSONContent => c !== null);

      if (strippedChildren.length === 0) return null;

      // Only wrap in paragraph if all children are inline nodes.
      // Block children inside a paragraph would fail schema validation.
      const allInline = strippedChildren.every(
        c => c && typeof c === 'object' && c.type && INLINE_NODE_TYPES.has(c.type),
      );
      if (allInline) {
        return { type: 'paragraph', content: strippedChildren };
      }
      // Unknown node with block children — drop it to avoid invalid structure
      return null;
    }
    if (typeof json.text === 'string' && json.text) {
      return { type: 'text', text: json.text };
    }
    return null;
  }

  const cleaned: JSONContent = { ...json };
  if (Array.isArray(cleaned.content)) {
    cleaned.content = cleaned.content
      .map(c => stripUnknownNodes(c, schema))
      .filter((c): c is JSONContent => c !== null);
  }
  return cleaned;
}
/** Inline node types that should be wrapped in a paragraph inside block containers. */
const INLINE_NODE_TYPES = new Set(['text', 'hardBreak', 'image', 'inlineMath', 'mention']);

/** Block nodes whose content model requires paragraphs, not raw inline nodes. */
const BLOCK_WRAPPER_TYPES = new Set(['listItem', 'blockquote', 'doc']);

/**
 * Wrap bare inline nodes (text, hardBreak, etc.) in paragraphs inside
 * block containers (listItem, blockquote) that require paragraph children.
 */
export function wrapBareInlineContent(json: JSONContent): JSONContent {
  if (!json || typeof json !== 'object') return json;

  const result: JSONContent = { ...json };

  if (Array.isArray(result.content)) {
    // Check if this is a block node whose children are all inline nodes
    if (BLOCK_WRAPPER_TYPES.has(result.type ?? '') && result.content.length > 0) {
      const needsParagraph = result.content.some(
        c => c && typeof c === 'object' && c.type && INLINE_NODE_TYPES.has(c.type),
      );
      if (needsParagraph) {
        // Group inline children into paragraph-wrapped segments,
        // keeping existing block children (like nested lists) as-is
        const groups: JSONContent[][] = [];
        let currentInline: JSONContent[] = [];

        for (const child of result.content) {
          if (child && typeof child === 'object' && child.type && INLINE_NODE_TYPES.has(child.type)) {
            currentInline.push(wrapBareInlineContent(child));
          } else {
            if (currentInline.length > 0) {
              groups.push(currentInline);
              currentInline = [];
            }
            groups.push([wrapBareInlineContent(child)]);
          }
        }
        if (currentInline.length > 0) {
          groups.push(currentInline);
        }

        result.content = groups.map(group => {
          // If the group starts with a block node, keep it as-is
          if (group.length === 1 && group[0]?.type && !INLINE_NODE_TYPES.has(group[0].type)) {
            return group[0];
          }
          return { type: 'paragraph', content: group };
        });
      } else {
        result.content = result.content.map(c => wrapBareInlineContent(c));
      }
    } else {
      result.content = result.content.map(c => wrapBareInlineContent(c));
    }
  }

  return result;
}

export function sanitizeMarkdownSource(content: string): string {
  return content
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/\son\w+\s*=\s*(['"]).*?\1/gi, '')
    .replace(/\s(href|src)\s*=\s*(['"])\s*javascript:[^'"]*\2/gi, ' $1="#"');
}

export function normalizePastedText(content: string): string {
  return content
    .replace(/\r\n?/g, '\n')
    .replace(/[​-‍﻿]/g, '')
    .replace(/ /g, ' ');
}

export function buildPlainTextDoc(content: string): JSONContent {
  const normalized = normalizePastedText(content);
  if (!normalized) {
    return {
      type: 'doc',
      content: [{ type: 'paragraph' }],
    };
  }

  const lines = normalized.split('\n');
  const paragraphContent: JSONContent[] = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] ?? '';
    if (line.length > 0) {
      paragraphContent.push({
        type: 'text',
        text: line,
      });
    }
    if (index < lines.length - 1) {
      paragraphContent.push({ type: 'hardBreak' });
    }
  }

  return {
    type: 'doc',
    content: [
      paragraphContent.length > 0
        ? {
            type: 'paragraph',
            content: paragraphContent,
          }
        : {
            type: 'paragraph',
          },
    ],
  };
}
