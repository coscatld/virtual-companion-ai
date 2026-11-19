import { onMounted, onUnmounted } from 'vue'
import { websocketUrl } from '../api/endpoints'
import { getLatestBriefing, type Briefing } from '../api/briefingApi'

export function useBriefingFeed(token: () => string | null, onBriefing: (text: string) => void) {
  let active = false
  let socket: WebSocket | undefined
  let retry: ReturnType<typeof setTimeout> | undefined
  let latest = 0

  function receive(briefing: Briefing) {
    const generated = Date.parse(briefing.generatedAt)
    if (active && generated > latest) {
      latest = generated
      onBriefing(briefing.text)
    }
  }

  function connect() {
    const credential = token()
    if (!active || !credential) return
    void getLatestBriefing().then((briefing) => {
      if (briefing) receive(briefing)
    }).catch(() => undefined)
    socket = new WebSocket(websocketUrl('/ws/briefing'), ['ga.jwt', `jwt.${credential}`])
    socket.onmessage = ({ data }) => {
      try {
        const event = JSON.parse(data)
        if (event.type === 'briefing' && typeof event.text === 'string') receive(event)
      } catch {
        // Ignore unrecognized messages from the notification stream.
      }
    }
    socket.onclose = () => {
      if (active) retry = setTimeout(connect, 15_000)
    }
  }

  onMounted(() => { active = true; connect() })
  onUnmounted(() => {
    active = false
    clearTimeout(retry)
    socket?.close()
  })
}
