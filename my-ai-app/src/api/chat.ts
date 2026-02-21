// Fetch API or EventSource based SSE implementation string
export const streamChat = (message: string, onMessage: (text: string) => void, onError: (err: any) => void, onEnd: () => void) => {
    const token = localStorage.getItem('token') || ''

    // We use fetch for POST request with streaming response
    const controller = new AbortController()

    fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'text/plain'
        },
        body: message,
        signal: controller.signal
    }).then(async (response) => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }
        if (!response.body) {
            throw new Error('ReadableStream not yet supported in this browser.')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')

        let buffer = ''
        while (true) {
            const { done, value } = await reader.read()
            if (done) {
                onEnd()
                break
            }

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
                if (line.startsWith('data:')) {
                    const data = line.slice(5).trim()
                    if (data === '[END]') {
                        onEnd()
                        return
                    } else if (data) {
                        onMessage(data)
                    }
                }
            }
        }
    }).catch(err => {
        onError(err)
    })

    return {
        abort: () => controller.abort()
    }
}
