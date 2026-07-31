import type { Editor } from '@tiptap/vue-3';

let editorRef: Editor | null = null;

export function setEditorRef(editor: Editor | null) {
  editorRef = editor;
}

export function getEditorRef(): Editor | null {
  return editorRef;
}

export function insertGeneratedContent(content: string) {
  if (!editorRef || !content) return;
  try {
    // Use TipTap's built-in markdown extension (same pattern as useFileGenerate)
    const parsed = (editorRef as any).markdown?.parse(content);
    if (parsed) {
      const { doc } = editorRef.state;
      const endPos = doc.content.size;
      editorRef.commands.focus();
      editorRef.commands.setTextSelection(endPos);
      editorRef.commands.insertContent(parsed);
      editorRef.commands.scrollIntoView();
    } else {
      // Fallback: insert at end as plain text
      const { doc } = editorRef.state;
      editorRef.commands.insertContentAt(doc.content.size, content);
    }
  } catch (e) {
    console.error('[useNodeChat] insertContent fallback failed:', e);
    // If all else fails, insert as plain text
    try {
      editorRef.commands.insertContent(content);
    } catch (e) {
      console.error('[useNodeChat] insertContent plain text fallback failed:', e);
    }
  }
}
