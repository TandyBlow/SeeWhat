import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export interface OfficialNode {
  id: string
  title: string
  content: string
  sort_order: number
  is_published: boolean
  created_at: string
  updated_at: string
}

export function useAdminPanelState() {
  const nodes = ref<OfficialNode[]>([])
  const selectedId = ref<string | null>(null)
  const editTitle = ref('')
  const editContent = ref('')
  const editTitleEn = ref('')
  const editContentEn = ref('')
  const editPublished = ref(false)
  const showPreview = ref(false)
  const dirty = ref(false)
  const saving = ref(false)
  const saveError = ref('')
  const loadingList = ref(true)
  const isCreating = ref(false)

  const renderedPreview = computed(() => {
    return DOMPurify.sanitize(marked.parse(editContent.value, { async: false }) as string)
  })

  function selectNode(node: OfficialNode) {
    selectedId.value = node.id
    editTitle.value = node.title
    editContent.value = node.content
    editTitleEn.value = (node as any).title_en || ''
    editContentEn.value = (node as any).content_en || ''
    editPublished.value = !!node.is_published
    dirty.value = false
    saveError.value = ''
    isCreating.value = false
  }

  function createNew() {
    selectedId.value = null
    editTitle.value = ''
    editContent.value = ''
    editTitleEn.value = ''
    editContentEn.value = ''
    editPublished.value = false
    dirty.value = false
    saveError.value = ''
    isCreating.value = true
  }

  function markDirty() {
    dirty.value = true
  }

  return {
    nodes,
    selectedId,
    editTitle,
    editContent,
    editTitleEn,
    editContentEn,
    editPublished,
    showPreview,
    dirty,
    saving,
    saveError,
    loadingList,
    isCreating,
    renderedPreview,
    selectNode,
    createNew,
    markDirty,
  }
}
