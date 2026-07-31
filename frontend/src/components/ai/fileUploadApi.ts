import type { Composer } from 'vue-i18n'

export interface UploadResult {
  file_id: string
  [key: string]: any
}

export function uploadFileWithProgress(
  file: File,
  t: Composer['t'],
  onProgress: (percent: number) => void
): Promise<UploadResult> {
  const token = localStorage.getItem('acacia_backend_token')
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860'

  return new Promise<UploadResult>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const formData = new FormData()
    formData.append('file', file)

    xhr.upload.onprogress = (e: ProgressEvent) => {
      if (e.lengthComputable && e.total > 0) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          reject(new Error(t('upload.uploadFailed')))
        }
      } else {
        let detail = t('upload.uploadFailed')
        try {
          const err = JSON.parse(xhr.responseText)
          detail = err.detail || t('upload.uploadFailed')
        } catch {
          console.error('[FileUploadArea] failed to parse error response')
        }
        if (xhr.status === 413) detail = t('upload.sizeLimitExceeded')
        reject(new Error(detail))
      }
    }

    xhr.onerror = () => reject(new Error(t('upload.uploadFailed')))

    xhr.open('POST', `${backendUrl}/upload-file`)
    xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.send(formData)
  })
}

export async function fetchUploadedContent(fileId: string, t: Composer['t']): Promise<string> {
  const token = localStorage.getItem('acacia_backend_token')
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860'

  for (let attempt = 0; attempt < 20; attempt += 1) {
    const resp = await fetch(`${backendUrl}/file-content/${fileId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (resp.ok) {
      const data = await resp.json()
      return typeof data.full_text === 'string' ? data.full_text : ''
    }
    if (attempt < 19) {
      await new Promise((resolve) => setTimeout(resolve, 300))
    }
  }

  throw new Error(t('upload.parseFailed'))
}
