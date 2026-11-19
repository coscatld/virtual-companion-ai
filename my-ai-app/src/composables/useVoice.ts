import { onUnmounted, ref } from 'vue'
import captureWorklet from './pcmCapture.js?url'
import { websocketUrl } from '../api/endpoints'

const MAX_RECORDING_MS = 20_000
const FRAME_BYTES = 128 * 1024

type Capture = {
  stream?: MediaStream
  context?: AudioContext
  node?: AudioWorkletNode
  chunks: Float32Array[]
  timer?: ReturnType<typeof setTimeout>
}

type VoiceEvent =
  | { type: 'transcript'; userText?: string; text: string }
  | { type: 'audio'; contentType: string }
  | { type: 'done' }
  | { type: 'error'; text: string }

function voiceError(code: string): string {
  switch (code) {
    case 'voice_disabled': return '语音服务尚未配置。'
    case 'audio_too_large': return '录音超过大小限制，请缩短后重试。'
    case 'invalid_audio':
    case 'speech_not_recognized': return '这段录音未能识别，请再说一次。'
    default: return '语音服务暂时不可用，请稍后重试。'
  }
}

function pcmWav(chunks: Float32Array[], sampleRate: number): ArrayBuffer {
  const size = chunks.reduce((total, chunk) => total + chunk.length, 0) * 2
  const wav = new ArrayBuffer(44 + size)
  const view = new DataView(wav)
  const write = (offset: number, tag: string) => {
    for (let i = 0; i < tag.length; i++) view.setUint8(offset + i, tag.charCodeAt(i))
  }
  write(0, 'RIFF')
  view.setUint32(4, 36 + size, true)
  write(8, 'WAVEfmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  write(36, 'data')
  view.setUint32(40, size, true)
  let offset = 44
  for (const chunk of chunks) {
    for (const sample of chunk) {
      view.setInt16(offset, Math.round(Math.max(-1, Math.min(1, sample)) * 32767), true)
      offset += 2
    }
  }
  return wav
}

export function useVoice(token: () => string | null, onTranscript: (userText: string, text: string) => void) {
  const phase = ref<'idle' | 'requesting' | 'recording' | 'waiting'>('idle')
  const error = ref('')
  const audioUrl = ref('')
  let capture: Capture | undefined
  let socket: WebSocket | undefined
  let timeout: ReturnType<typeof setTimeout> | undefined

  function release(recording: Capture) {
    clearTimeout(recording.timer)
    recording.node?.disconnect()
    recording.stream?.getTracks().forEach((track) => track.stop())
    if (recording.context) void recording.context.close().catch(() => undefined)
  }

  function cancel() {
    if (capture) release(capture)
    capture = undefined
    clearTimeout(timeout)
    const connection = socket
    socket = undefined
    connection?.close()
    phase.value = 'idle'
  }

  function fail(message: string) {
    error.value = message
    cancel()
  }

  async function start() {
    if (phase.value !== 'idle') return
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
      error.value = '请在支持麦克风的浏览器中通过 HTTPS 或本机地址打开。'
      return
    }
    error.value = ''
    phase.value = 'requesting'
    const recording: Capture = { chunks: [] }
    capture = recording
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } })
      if (capture !== recording) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      recording.stream = stream
      let context: AudioContext
      try {
        context = new AudioContext({ sampleRate: 16000 })
      } catch {
        context = new AudioContext()
      }
      recording.context = context
      await context.audioWorklet.addModule(captureWorklet)
      await context.resume()
      if (capture !== recording) return
      const node = new AudioWorkletNode(context, 'ga-pcm', { channelCount: 1 })
      recording.node = node
      node.port.onmessage = ({ data }: MessageEvent<Float32Array | null>) => {
        if (capture !== recording) return
        if (data) recording.chunks.push(data)
        else {
          const wav = pcmWav(recording.chunks, context.sampleRate)
          release(recording)
          capture = undefined
          send(wav)
        }
      }
      context.createMediaStreamSource(stream).connect(node).connect(context.destination)
      phase.value = 'recording'
      recording.timer = setTimeout(stop, MAX_RECORDING_MS)
    } catch {
      if (capture === recording) fail('无法开始录音，请检查麦克风权限和设备。')
    }
  }

  function stop() {
    if (phase.value !== 'recording' || !capture?.node) return
    phase.value = 'waiting'
    capture.node.port.postMessage('flush')
  }

  function showReply(userText: string, text: string, audio?: Blob) {
    onTranscript(userText, text)
    if (audio) {
      if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
      audioUrl.value = URL.createObjectURL(audio)
    }
    cancel()
  }

  function send(wav: ArrayBuffer) {
    const credential = token()
    if (!credential) return fail('请登录后使用语音。')
    if (wav.byteLength <= 44) return fail('没有录到声音，请重试。')

    const connection = new WebSocket(websocketUrl('/audio'), ['ga.jwt', `jwt.${credential}`])
    socket = connection
    connection.binaryType = 'arraybuffer'
    timeout = setTimeout(() => fail('等待语音回复超时，请重试。'), 90_000)
    let contentType = 'audio/mpeg'
    let transcript: { userText?: string; text: string } | undefined
    let audio: Blob | undefined

    connection.onopen = () => {
      if (socket !== connection) return
      for (let offset = 0; offset < wav.byteLength; offset += FRAME_BYTES) {
        connection.send(wav.slice(offset, offset + FRAME_BYTES))
      }
      connection.send(new ArrayBuffer(0))
    }
    connection.onmessage = ({ data }: MessageEvent<string | ArrayBuffer>) => {
      if (socket !== connection) return
      if (typeof data !== 'string') {
        audio = new Blob([data], { type: contentType })
        return
      }
      try {
        const event = JSON.parse(data) as VoiceEvent
        if (event.type === 'transcript') transcript = event
        if (event.type === 'audio') contentType = event.contentType
        if (event.type === 'error') fail(/^[a-z_]+$/.test(event.text) ? voiceError(event.text) : event.text || voiceError(''))
        if (event.type === 'done') {
          showReply(transcript?.userText ?? '', transcript?.text ?? '', audio)
        }
      } catch {
        fail('语音服务返回了无法识别的数据。')
      }
    }
    connection.onerror = connection.onclose = () => {
      if (socket === connection) fail('语音连接中断，请重试。')
    }
  }

  onUnmounted(() => {
    cancel()
    if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
  })
  return { phase, error, audioUrl, start, stop, cancel }
}
