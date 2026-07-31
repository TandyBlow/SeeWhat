<template>
  <div class="upload-area">
    <div
      class="upload-zone"
      :class="{ 'drag-over': isDragOver, 'uploading': isUploading }"
      @drop.prevent="handleDrop"
      @dragover.prevent="isDragOver = true"
      @dragleave.prevent="isDragOver = false"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".txt,.md,.pdf,.docx,.ipynb,.py"
        @change="handleFileSelect"
        style="display: none"
      />

      <template v-if="!isUploading && !isProcessing && !uploadedFile">
        <div class="upload-icon">📄</div>
        <div class="upload-text">
          <div class="upload-primary">{{ $t('upload.clickOrDrag') }}</div>
          <div class="upload-secondary">{{ $t('upload.supportedFormats') }}</div>
        </div>
      </template>

      <template v-else-if="isUploading">
        <div class="upload-icon">⏳</div>
        <div class="upload-text">
          <div class="upload-primary">{{ $t('upload.uploading') }}</div>
          <div class="upload-secondary">{{ uploadProgress }}%</div>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
      </template>

      <template v-else-if="isProcessing">
        <StreamingExtractPanel
          :file-id="processingFileId"
          @complete="onPipelineComplete"
          @error="onPipelineError"
          @cancel="onPipelineCancel"
        />
      </template>

      <template v-else-if="uploadedFile">
        <div class="upload-icon">✓</div>
        <div class="upload-text">
          <div class="upload-primary">{{ uploadedFile.filename }}</div>
          <div class="upload-secondary">
            {{ formatFileSize(uploadedFile.size) }} · {{ $t('upload.chars', { n: uploadedFile.text_length }) }}
            <span v-if="uploadedFile.ocr_status === 'pending'" class="ocr-badge ocr-badge-pending">OCR...</span>
            <span v-else-if="uploadedFile.ocr_applied" class="ocr-badge">OCR</span>
          </div>
          <div v-if="uploadedFile.text_length === 0 && uploadedFile.ocr_status === 'pending'" class="upload-warning">
            {{ $t('upload.ocrPending') }}
          </div>
          <div v-else-if="uploadedFile.text_length === 0" class="upload-warning">
            {{ $t('upload.emptyWarning') }}
          </div>
        </div>
        <button class="remove-btn" @click.stop="removeFile">✕</button>
      </template>
    </div>

    <div v-if="errorMessage" class="upload-error">{{ errorMessage }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import StreamingExtractPanel from './StreamingExtractPanel.vue'
import { useFileUpload, type UploadedFile } from './useFileUpload'

const emit = defineEmits<{
  uploaded: [file: UploadedFile];
  removed: [];
}>()

const fileInput = ref<HTMLInputElement | null>(null)

const {
  isDragOver,
  isUploading,
  isProcessing,
  uploadProgress,
  uploadedFile,
  errorMessage,
  processingFileId,
  handleDrop,
  handleFileSelect,
  triggerFileInput,
  onPipelineComplete,
  onPipelineError,
  onPipelineCancel,
  removeFile,
  formatFileSize,
} = useFileUpload(fileInput, emit)
</script>

<style scoped src="./FileUploadArea.1.css"></style>
