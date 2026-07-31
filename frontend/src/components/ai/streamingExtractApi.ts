export interface StreamOptions {
  url: string
  headers: Record<string, string>
  signal?: AbortSignal
  onEvent: (event: string, data: Record<string, any>) => void
  onError: (message: string) => void
}

export function openStream(options: StreamOptions) {
  const { url, headers, signal, onEvent, onError } = options

  fetch(url, {
    headers,
    signal,
  })
    .then((response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}`)
        return
      }
      const reader = response.body?.getReader()
      if (!reader) {
        onError('Response body is not readable')
        return
      }
      const decoder = new TextDecoder()
      let buffer = ''

      function processChunk() {
        reader!.read().then(({ done, value }) => {
          if (done) return

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          let currentEvent = 'message'
          let dataBuffer = ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              dataBuffer = line.slice(6)
              try {
                const data = JSON.parse(dataBuffer)
                onEvent(currentEvent, data)
              } catch {
                // Skip unparseable lines
              }
              currentEvent = 'message'
            }
          }
          processChunk()
        }).catch(() => {
          // Reader cancelled or errored
        })
      }
      processChunk()
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err.message)
    })
}

export async function fetchFormattedFile(fileId: string): Promise<string | null> {
  const token = localStorage.getItem('acacia_backend_token')
  const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860'

  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const resp = await fetch(`${backendUrl}/file-content/${fileId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (resp.ok) {
        const data = await resp.json()
        if (typeof data.full_text === 'string') {
          return data.full_text
        }
      }
    } catch {
      // If fetch fails, fall back to the SSE payload or accumulated fragments.
    }

    if (attempt < 2) {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }

  return null
}
