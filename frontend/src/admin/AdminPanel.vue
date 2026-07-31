<template>
  <div class="admin-layout">
    <header class="admin-header">
      <h1>{{ $t('admin.title') }}</h1>
      <button class="btn-logout" @click="$emit('logout')">{{ $t('admin.logout') }}</button>
    </header>

    <div class="admin-body">
      <!-- Left sidebar: node list -->
      <aside class="admin-sidebar">
        <div class="sidebar-header">
          <span>{{ $t('admin.officialNodes') }}</span>
          <button class="btn-new" @click="createNew">{{ $t('admin.new') }}</button>
        </div>
        <div v-if="loadingList" class="sidebar-status">{{ $t('admin.loading') }}</div>
        <div v-else-if="nodes.length === 0" class="sidebar-status">{{ $t('admin.noNodes') }}</div>
        <ul v-else class="node-list">
          <li
            v-for="node in nodes"
            :key="node.id"
            class="node-item"
            :class="{ active: selectedId === node.id }"
            @click="selectNode(node)"
          >
            <span class="node-status" :class="{ published: node.is_published }">
              {{ node.is_published ? '✓' : '○' }}
            </span>
            <span class="node-title" :class="{ draft: !node.is_published }">{{ node.title }}</span>
          </li>
        </ul>
      </aside>

      <!-- Main editor area -->
      <main class="admin-main">
        <div v-if="!selectedId && !isCreating" class="empty-editor">
          {{ $t('admin.selectNode') }}
        </div>
        <template v-else>
          <div class="editor-toolbar">
            <input
              v-model="editTitle"
              class="title-input"
              :placeholder="$t('admin.nodeTitle')"
              @input="markDirty"
            />
            <input
              v-model="editTitleEn"
              class="title-input title-input-en"
              :placeholder="$t('admin.nodeTitleEn')"
              @input="markDirty"
            />
            <label class="preview-toggle">
              <input type="checkbox" v-model="showPreview" /> {{ $t('admin.preview') }}
            </label>
          </div>

          <div class="editor-body">
            <div v-if="!showPreview" class="editor-body-layout">
              <textarea
                v-model="editContent"
                class="content-textarea"
                :placeholder="$t('admin.markdownPlaceholder')"
                @input="markDirty"
              ></textarea>
              <textarea
                v-model="editContentEn"
                class="content-textarea content-textarea-en"
                :placeholder="$t('admin.markdownPlaceholderEn')"
                @input="markDirty"
              ></textarea>
            </div>
            <div v-else class="content-preview" v-html="renderedPreview"></div>
          </div>

          <div v-if="saveError" class="editor-error">{{ saveError }}</div>

          <div class="editor-actions">
            <button class="btn-save" :disabled="saving || !dirty" @click="save">
              {{ saving ? $t('admin.saving') : $t('admin.save') }}
            </button>
            <button
              class="btn-publish"
              :class="{ unpublish: editPublished }"
              :disabled="saving"
              @click="togglePublish"
            >
              {{ editPublished ? $t('admin.unpublish') : $t('admin.publish') }}
            </button>
            <button class="btn-delete" :disabled="saving" @click="confirmDelete">
              {{ $t('admin.delete') }}
            </button>
          </div>
        </template>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAdminPanelState } from './AdminPanelState'
import { useAdminApi } from './AdminPanelApi'

defineEmits<{ logout: [] }>()

const admin = useAdminPanelState()
const { save, togglePublish, confirmDelete } = useAdminApi(admin)

const {
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
} = admin
</script>

<style scoped src="./AdminPanel.1.css"></style>
<style scoped src="./AdminPanel.2.css"></style>
