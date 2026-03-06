import { ref, onUnmounted } from 'vue'

export function useAvatarWS() {
    const wsStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected')
    const aiSubtitle = ref('')

    // 对外暴露的回调接口，外部可通过给这些变量赋值来接收事件
    // 例如：onBlendShapeUpdate.value = (shapeName, value) => { ... }
    const onBlendShapeUpdate = ref<((shapeName: string, value: number) => void) | null>(null)

    let ws: WebSocket | null = null
    let reconnectTimer: number | null = null
    let reconnectAttempts = 0
    const MAX_RECONNECT = 5

    const connect = () => {
        if (ws && ws.readyState === WebSocket.OPEN) return
        if (reconnectAttempts > MAX_RECONNECT) {
            wsStatus.value = 'error'
            return
        }

        wsStatus.value = 'connecting'

        // 这里替换为您实际的后端 V1.0 WS 地址
        const wsUrl = `ws://localhost:8080/api/v1/avatar/stream`
        ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            wsStatus.value = 'connected'
            reconnectAttempts = 0 // 重置重连次数
            console.log('[Avatar WS] Connected.')
        }

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)

                // 【指令解析示例】
                // 如果后端下发了字幕
                if (data.type === 'subtitle' && data.text) {
                    aiSubtitle.value = data.text
                }

                // 如果后端下发了口型/面部表情参数
                // e.g. { type: 'blendshape', shape: 'aa', value: 0.8 }
                if (data.type === 'blendshape' && data.shape && data.value !== undefined) {
                    if (onBlendShapeUpdate.value) {
                        onBlendShapeUpdate.value(data.shape, data.value)
                    }
                }

            } catch (err) {
                console.warn('[Avatar WS] Failed to parse message:', event.data)
            }
        }

        ws.onclose = () => {
            wsStatus.value = 'disconnected'
            console.log('[Avatar WS] Disconnected. Attempting to reconnect...')
            scheduleReconnect()
        }

        ws.onerror = (err) => {
            wsStatus.value = 'error'
            console.error('[Avatar WS] Error:', err)
            // 报错后通常会随之触发 onclose，所以交由 onclose 处理重连即可
        }
    }

    const disconnect = () => {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer)
            reconnectTimer = null
        }
        if (ws) {
            // 禁用自动重连
            ws.onclose = null
            ws.close()
            ws = null
        }
        wsStatus.value = 'disconnected'
    }

    const scheduleReconnect = () => {
        if (reconnectTimer) clearTimeout(reconnectTimer)
        reconnectTimer = window.setTimeout(() => {
            reconnectAttempts++
            connect()
        }, 3000) // 3秒后尝试重连
    }

    // 组件销毁时断开连接，防止内存和连接数泄漏
    onUnmounted(() => {
        disconnect()
    })

    return {
        wsStatus,
        aiSubtitle,
        onBlendShapeUpdate,
        connect,
        disconnect
    }
}
