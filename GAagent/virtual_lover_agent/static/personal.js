const byId = (id) => document.getElementById(id)
const access = byId('access')
const room = byId('room')
const tokenInput = byId('token')
const state = byId('state')
const timeline = byId('messages')
const empty = byId('empty')
const draft = byId('draft')
const recordButton = byId('record')
const sendButton = byId('send')
const cancelButton = byId('cancel')
const settings = byId('settings')
const chatStatus = byId('chat-status')
const output = byId('reply-audio')

const storageKey = 'ga-personal-token'
let token = ''
let profile
let request
let recording
let phase = 'idle'
let audioUrl

const textByPhase = {
  idle: '等待消息',
  replying: '正在回复',
  permission: '等待麦克风授权',
  recording: '正在录音',
  voice: '正在处理语音',
}

function setPhase(next) {
  phase = next
  state.textContent = textByPhase[next]
  room.dataset.active = String(next !== 'idle')
  sendButton.disabled = next !== 'idle'
  cancelButton.hidden = next === 'idle'
  recordButton.disabled = !['idle', 'recording'].includes(next)
  recordButton.textContent = next === 'recording' ? '发送语音' : '录音'
}

function turn(role, content) {
  empty.hidden = true
  const article = document.createElement('article')
  const label = document.createElement('span')
  const text = document.createElement('p')
  article.className = 'turn'
  article.dataset.role = role
  label.textContent = role === 'user' ? '你' : profile.name
  text.textContent = content
  article.append(label, text)
  timeline.append(article)
  timeline.scrollTop = timeline.scrollHeight
  return text
}

function updateProfile(value) {
  profile = value
  byId('companion-name').textContent = profile.name
  for (const label of timeline.querySelectorAll('article[data-role="assistant"] > span')) {
    label.textContent = profile.name
  }
}

async function api(path, { credential = token, headers, ...options } = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { Authorization: `Bearer ${credential}`, ...headers },
  })
  if (response.ok) return response

  const { detail } = await response.json().catch(() => ({}))
  const descriptions = {
    invalid_token: '访问令牌无效。',
    authentication_required: '请先输入访问令牌。',
    audio_too_large: '录音超过大小限制。',
    invalid_audio: '这段录音无法读取，请重新录音。',
    speech_not_recognized: '未能识别这段录音，请重新录音。',
    voice_disabled: '终端尚未配置语音服务。',
    model_unavailable: '当前模型服务不可用。',
  }
  const error = new Error(descriptions[detail] || `终端暂时无法处理请求（${response.status}）。`)
  error.status = response.status
  throw error
}

async function unlock(credential) {
  const button = byId('login').querySelector('button')
  const status = byId('login-status')
  button.disabled = true
  status.textContent = ''
  try {
    const savedProfile = await (await api('/v1/profile', { credential })).json()
    token = credential
    sessionStorage.setItem(storageKey, token)
    updateProfile(savedProfile)
    try {
      const history = await (await api('/v1/chat/history')).json()
      for (const message of history.messages) turn(message.role, message.content)
    } catch {
      chatStatus.textContent = '暂时无法加载近期对话。'
    }
    access.hidden = true
    room.hidden = false
    byId('navigation').hidden = false
    timeline.scrollTop = timeline.scrollHeight
    tokenInput.value = ''
    draft.focus()
  } catch (error) {
    sessionStorage.removeItem(storageKey)
    status.textContent = error.message
  } finally {
    button.disabled = false
  }
}

function clearAudio() {
  if (audioUrl) URL.revokeObjectURL(audioUrl)
  audioUrl = undefined
  output.pause()
  output.removeAttribute('src')
  output.hidden = true
}

function lock() {
  cancel()
  settings.close()
  clearAudio()
  for (const article of timeline.querySelectorAll('article')) article.remove()
  empty.hidden = false
  chatStatus.textContent = ''
  draft.value = ''
  token = ''
  sessionStorage.removeItem(storageKey)
  byId('navigation').hidden = true
  room.hidden = true
  access.hidden = false
  tokenInput.focus()
}

function showError(error) {
  if (error.status === 401) {
    lock()
    byId('login-status').textContent = '访问令牌失效，请重新连接。'
  } else {
    chatStatus.textContent = error.message
  }
}

function release(media) {
  clearTimeout(media.timer)
  media.node?.disconnect()
  media.stream?.getTracks().forEach((track) => track.stop())
  if (media.context) void media.context.close().catch(() => {})
}

function cancel() {
  request?.abort()
  request = undefined
  if (recording) release(recording)
  recording = undefined
  setPhase('idle')
}

function begin(next) {
  chatStatus.textContent = ''
  setPhase(next)
  request = new AbortController()
  return request
}

async function streamReply(response, text) {
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) throw new Error('回复中断，请重新发送。')
      pending += value
      let separator = pending.indexOf('\n\n')
      while (separator !== -1) {
        const block = pending.slice(0, separator)
        pending = pending.slice(separator + 2)
        if (block.startsWith('data:')) {
          const frame = JSON.parse(block.slice(5))
          if (frame.type === 'done') return
          if (frame.type === 'error') throw new Error('模型暂时无法完成回复。')
          if (frame.type === 'delta') {
            if (text.textContent === '…') text.textContent = ''
            text.append(frame.delta)
            timeline.scrollTop = timeline.scrollHeight
          }
        }
        separator = pending.indexOf('\n\n')
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

async function sendText() {
  const message = draft.value.trim()
  if (!message || phase !== 'idle') return
  draft.value = ''
  turn('user', message)
  const reply = turn('assistant', '…')
  const current = begin('replying')
  try {
    const response = await api('/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ message }),
      signal: current.signal,
    })
    await streamReply(response, reply)
  } catch (error) {
    if (reply.textContent === '…') reply.parentElement?.remove()
    if (!current.signal.aborted) showError(error)
  } finally {
    if (request === current) cancel()
  }
}

function encodeWav(chunks, sampleRate) {
  const size = chunks.reduce((total, chunk) => total + chunk.length, 0) * 2
  const buffer = new ArrayBuffer(size + 44)
  const view = new DataView(buffer)
  const tag = (offset, value) => {
    for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i))
  }
  tag(0, 'RIFF')
  view.setUint32(4, 36 + size, true)
  tag(8, 'WAVEfmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  tag(36, 'data')
  view.setUint32(40, size, true)
  let offset = 44
  for (const chunk of chunks) {
    for (const sample of chunk) {
      view.setInt16(offset, Math.round(Math.min(1, Math.max(-1, sample)) * 32767), true)
      offset += 2
    }
  }
  return buffer
}

async function sendVoice(buffer) {
  const current = begin('voice')
  const timeout = setTimeout(() => {
    if (request !== current) return
    chatStatus.textContent = '等待语音回复超时，请重试。'
    cancel()
  }, 90_000)
  try {
    if (buffer.byteLength <= 44) throw new Error('没有录到声音，请重新录音。')
    const response = await api('/v1/voice', {
      method: 'POST',
      headers: { 'Content-Type': 'audio/wav' },
      body: buffer,
      signal: current.signal,
    })
    const reply = await response.json()
    if (current.signal.aborted) return
    const bytes = Uint8Array.from(atob(reply.audio_base64), (character) => character.charCodeAt(0))
    turn('user', reply.user_text)
    turn('assistant', reply.text)
    clearAudio()
    audioUrl = URL.createObjectURL(new Blob([bytes], { type: reply.audio_content_type }))
    output.src = audioUrl
    output.hidden = false
    void output.play().catch(() => {})
  } catch (error) {
    if (!current.signal.aborted) showError(error)
  } finally {
    clearTimeout(timeout)
    if (request === current) cancel()
  }
}

function stopRecording() {
  if (phase !== 'recording' || !recording?.node) return
  setPhase('voice')
  recording.node.port.postMessage('flush')
}

async function startRecording() {
  if (phase !== 'idle') return
  chatStatus.textContent = ''
  if (!navigator.mediaDevices?.getUserMedia || !window.AudioContext) {
    chatStatus.textContent = '请通过本机地址或 HTTPS 打开终端，才能使用麦克风。'
    return
  }
  setPhase('permission')
  const media = { chunks: [] }
  recording = media
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1 } })
    media.stream = stream
    if (recording !== media) return release(media)

    try {
      media.context = new AudioContext({ sampleRate: 16000 })
    } catch {
      media.context = new AudioContext()
    }
    await media.context.audioWorklet.addModule('/static/pcmCapture.js')
    await media.context.resume()
    if (recording !== media) return

    const node = new AudioWorkletNode(media.context, 'ga-pcm', { channelCount: 1 })
    media.node = node
    node.port.onmessage = ({ data }) => {
      if (recording !== media) return
      if (data) {
        media.chunks.push(data)
      } else {
        const buffer = encodeWav(media.chunks, media.context.sampleRate)
        release(media)
        recording = undefined
        void sendVoice(buffer)
      }
    }
    media.context.createMediaStreamSource(stream).connect(node).connect(media.context.destination)
    setPhase('recording')
    media.timer = setTimeout(stopRecording, 20_000)
  } catch {
    if (recording === media) {
      chatStatus.textContent = '无法开始录音，请检查麦克风权限和设备。'
      cancel()
    }
  }
}

byId('login').addEventListener('submit', (event) => {
  event.preventDefault()
  if (tokenInput.value.trim()) void unlock(tokenInput.value.trim())
})
byId('send-text').addEventListener('submit', (event) => {
  event.preventDefault()
  void sendText()
})
draft.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    void sendText()
  }
})
recordButton.addEventListener('click', () => {
  if (phase === 'recording') stopRecording()
  else void startRecording()
})
cancelButton.addEventListener('click', cancel)
byId('logout').addEventListener('click', lock)
byId('edit-profile').addEventListener('click', () => {
  byId('profile-name').value = profile.name
  byId('profile-prompt').value = profile.system_prompt
  byId('profile-voice').value = profile.voice_id
  byId('profile-status').textContent = ''
  settings.showModal()
})
byId('close-settings').addEventListener('click', () => settings.close())
byId('profile').addEventListener('submit', async (event) => {
  event.preventDefault()
  const button = event.submitter
  const status = byId('profile-status')
  const credential = token
  button.disabled = true
  status.textContent = ''
  try {
    const response = await api('/v1/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: byId('profile-name').value.trim(),
        system_prompt: byId('profile-prompt').value.trim(),
        voice_id: byId('profile-voice').value.trim(),
      }),
    })
    const savedProfile = await response.json()
    if (token === credential) {
      updateProfile(savedProfile)
      settings.close()
    }
  } catch (error) {
    status.textContent = error.message
  } finally {
    button.disabled = false
  }
})
window.addEventListener('pagehide', cancel)
const remembered = sessionStorage.getItem(storageKey)
if (remembered) void unlock(remembered)
