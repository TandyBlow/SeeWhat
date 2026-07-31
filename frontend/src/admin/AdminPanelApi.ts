import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiFetch } from '../utils/api'
import { useAdminPanelState, type OfficialNode } from './AdminPanelState'

export function useAdminApi(state: ReturnType<typeof useAdminPanelState>) {
  const { t } = useI18n()

  const {
    nodes,
    selectedId,
    editTitle,
    editContent,
    editTitleEn,
    editContentEn,
    editPublished,
    dirty,
    saving,
    saveError,
    loadingList,
    isCreating,
  } = state

  async function fetchList() {
    loadingList.value = true
    try {
      nodes.value = await apiFetch<OfficialNode[]>('/admin/official-nodes')
    } catch (e) {
      console.error('[AdminPanel] fetchList failed:', e)
      nodes.value = []
    } finally {
      loadingList.value = false
    }
  }

  async function save() {
    if (!editTitle.value.trim()) {
      saveError.value = t('admin.titleRequired')
      return
    }
    saving.value = true
    saveError.value = ''
    try {
      const body = JSON.stringify({
        title: editTitle.value.trim(),
        content: editContent.value,
        title_en: editTitleEn.value,
        content_en: editContentEn.value,
        is_published: editPublished.value,
      })

      if (selectedId.value) {
        // Update existing
        const result = await apiFetch<OfficialNode>(`/admin/official-nodes/${selectedId.value}`, {
          method: 'PATCH',
          body,
        })
        // Populate English fields with auto-translated result
        if ((result as any).title_en) editTitleEn.value = (result as any).title_en
        if ((result as any).content_en) editContentEn.value = (result as any).content_en
      } else {
        // Create new
        const node = await apiFetch<OfficialNode>('/admin/official-nodes', {
          method: 'POST',
          body,
        })
        selectedId.value = node.id
        if ((node as any).title_en) editTitleEn.value = (node as any).title_en
        if ((node as any).content_en) editContentEn.value = (node as any).content_en
      }
      dirty.value = false
      isCreating.value = false
      await fetchList()
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : t('admin.saveFailed')
    } finally {
      saving.value = false
    }
  }

  async function togglePublish() {
    const next = !editPublished.value
    saving.value = true
    saveError.value = ''
    try {
      if (selectedId.value) {
        await apiFetch(`/admin/official-nodes/${selectedId.value}`, {
          method: 'PATCH',
          body: JSON.stringify({ is_published: next }),
        })
      }
      editPublished.value = next
      dirty.value = true
      await fetchList()
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : t('admin.operationFailed')
    } finally {
      saving.value = false
    }
  }

  async function confirmDelete() {
    if (!selectedId.value) return
    if (!window.confirm(t('admin.confirmDelete'))) return
    saving.value = true
    saveError.value = ''
    try {
      await apiFetch(`/admin/official-nodes/${selectedId.value}`, { method: 'DELETE' })
      selectedId.value = null
      editTitle.value = ''
      editContent.value = ''
      dirty.value = false
      await fetchList()
    } catch (e) {
      saveError.value = e instanceof Error ? e.message : t('admin.deleteFailed')
    } finally {
      saving.value = false
    }
  }

  onMounted(fetchList)

  return { fetchList, save, togglePublish, confirmDelete }
}
