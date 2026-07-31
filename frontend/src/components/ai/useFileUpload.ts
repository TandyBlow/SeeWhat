import { ref, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { uploadFileWithProgress, fetchUploadedContent } from './fileUploadApi'

export interface UploadedFile {
  file_id: string
  filename: string
  size: number
  extension: string
  text_length: number
  text_preview: string
  formatted_text?: string
  ocr_applied?: boolean
  ocr_reason?: string | null
  ocr_status?: string
  total_pages?: number
}

type UploadEmit = {
  (event: 'uploaded', file: UploadedFile): void
  (event: 'removed'): void
}

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
const VALID_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx', '.ipynb', '.py']

export function useFileUpload(fileInput: Ref<HTMLInputElement | null>, emit: UploadEmit) {
  const { t } = useI18n()

  const isDragOver = ref(false)
  const isUploading = ref(false)
  const isProcessing = ref(false)
  const uploadProgress = ref(0)
  const uploadedFile = ref<UploadedFile | null>(null)
  const errorMessage = ref('')
  const processingFileId = ref('')
  const pipelineMarkdown = ref('')
  const pendingFileMeta = ref<{ filename: string; size: number; extension: string } | null>(null)

  function shouldPreserveSource(extension: string): boolean {
    return ['.md', '.markdown'].includes(extension.toLowerCase())
  }

  function triggerFileInput() {
    if (!isUploading.value && !isProcessing.value && !uploadedFile.value) {
      fileInput.value?.click()
    }
  }

  function handleFileSelect(event: Event) {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    if (file) {
      uploadFile(file)
    }
  }

  function handleDrop(event: DragEvent) {
    isDragOver.value = false
    const file = event.dataTransfer?.files[0]
    if (file) {
      uploadFile(file)
    }
  }

  async function uploadFile(file: File) {
    errorMessage.value = ''

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      errorMessage.value = t('upload.sizeExceeded')
      return
    }

    // Validate file extension
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!VALID_EXTENSIONS.includes(fileExt)) {
      errorMessage.value = t('upload.unsupportedType', { ext: fileExt })
      return
    }

    isUploading.value = true
    uploadProgress.value = 0

    // Save file metadata for pipeline completion
    pendingFileMeta.value = {
      filename: file.name,
      size: file.size,
      extension: fileExt,
    }

    // Phase 1: upload with real progress via XHR
    let initialResponse: any
    try {
      initialResponse = await uploadFileWithProgress(file, t, (percent) => {
        uploadProgress.value = percent
      })
    } catch (err) {
      isUploading.value = false
      errorMessage.value = err instanceof Error ? err.message : t('upload.uploadFailed')
      return
    }

    isUploading.value = false
    uploadProgress.value = 0

    if (shouldPreserveSource(fileExt)) {
      try {
        const markdown = await fetchUploadedContent(initialResponse.file_id, t)
        onPipelineComplete(markdown)
      } catch (err) {
        errorMessage.value = err instanceof Error ? err.message : t('upload.parseFailed')
      }
      return
    }

    // Phase 2: start streaming markdown pipeline
    isProcessing.value = true
    processingFileId.value = initialResponse.file_id
    pipelineMarkdown.value = ''

    // Pipeline result is handled by onPipelineComplete/onPipelineError/onPipelineCancel
  }

  function onPipelineComplete(markdown: string) {
    pipelineMarkdown.value = markdown
    isProcessing.value = false

    const meta = pendingFileMeta.value
    const result: UploadedFile = {
      file_id: processingFileId.value,
      filename: meta?.filename || '',
      size: meta?.size || 0,
      extension: meta?.extension || '',
      text_length: markdown.length,
      text_preview: markdown.slice(0, 200) + (markdown.length > 200 ? '...' : ''),
      formatted_text: markdown,
    }
    pendingFileMeta.value = null
    uploadedFile.value = result
    emit('uploaded', result)
  }

  function onPipelineError(message: string) {
    isProcessing.value = false
    errorMessage.value = message
  }

  function onPipelineCancel() {
    isProcessing.value = false
    // Reset to pre-upload state
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }

  function removeFile() {
    uploadedFile.value = null
    pendingFileMeta.value = null
    pipelineMarkdown.value = ''
    errorMessage.value = ''
    if (fileInput.value) {
      fileInput.value.value = ''
    }
    emit('removed')
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return {
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
  }
}
