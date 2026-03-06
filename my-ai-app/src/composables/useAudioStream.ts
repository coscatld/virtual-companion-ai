import { ref, onUnmounted } from 'vue';

export function useAudioStream() {
  const isRecording = ref(false);
  const isPlaying = ref(false);
  const wsStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const wsErrorMsg = ref('');
  const aiText = ref('');
  const userText = ref('');
  const mouthOpenness = ref(0);

  let ws: WebSocket | null = null;
  let mediaRecorder: MediaRecorder | null = null;
  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let animationFrameId: number;
  let reconnectTimer: number | null = null;

  const connectWebSocket = () => {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    wsStatus.value = 'connecting';
    const token = localStorage.getItem('token') || '';
    const wsUrl = `ws://${window.location.host}/audio?token=${token}`;

    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      wsStatus.value = 'connected';
      wsErrorMsg.value = '';
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        await playAudioChunk(event.data);
      } else if (typeof event.data === 'string') {
        try {
          const res = JSON.parse(event.data);
          if (res.ai_text) {
            aiText.value += res.ai_text;
          }
        } catch (e) {
          console.error("Failed to parse websocket string msg", e);
        }
      }
    };

    ws.onclose = () => {
      wsStatus.value = 'disconnected';
      if (isRecording.value) stopRecording();

      wsErrorMsg.value = '与伴侣的连接断开了，正在尝试重连...';
      reconnectTimer = window.setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (error) => {
      wsStatus.value = 'error';
      wsErrorMsg.value = '网络似乎有点问题...';
      console.error('WebSocket Error:', error);
    };
  };

  const initAudioContext = () => {
    if (!audioContext) {
      audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      analyser.connect(audioContext.destination);
    }
  };

  const playAudioChunk = async (arrayBuffer: ArrayBuffer) => {
    initAudioContext();
    if (!audioContext || !analyser) return;

    try {
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyser);

      isPlaying.value = true;
      source.onended = () => {
        isPlaying.value = false;
        mouthOpenness.value = 0;
      };

      source.start();
      monitorAudioLevel();
    } catch (e) {
      console.error('Error decoding audio context', e);
    }
  };

  const monitorAudioLevel = () => {
    if (!analyser || !isPlaying.value) return;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i]!;
    }
    const average = sum / dataArray.length;

    // Normalize and add easing to prevent mouth jitter
    const targetOpenness = Math.min(1.0, average / 60);
    mouthOpenness.value = mouthOpenness.value + (targetOpenness - mouthOpenness.value) * 0.3;

    if (isPlaying.value) {
      animationFrameId = requestAnimationFrame(monitorAudioLevel);
    } else {
      cancelAnimationFrame(animationFrameId);
      mouthOpenness.value = 0;
    }
  };

  const startRecording = async () => {
    if (wsStatus.value !== 'connected') {
      alert("等一等，正在连接您的数字伴侣哦。");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };

      mediaRecorder.start(500);
      isRecording.value = true;
      aiText.value = '';
      userText.value = '正在倾听您说话...';
    } catch (err) {
      console.error('麦克风权限被拒:', err);
      alert('如果要和伴侣说话，请在浏览器地址栏左侧允许麦克风权限哦。');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording.value) {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(track => track.stop());

      if (ws && ws.readyState === WebSocket.OPEN) {
        // Push 0 byte ArrayBuffer to end VAD
        ws.send(new Uint8Array(0));
      }
      isRecording.value = false;
      userText.value = '您的声音已发送，请听我说...';
    }
  };

  onUnmounted(() => {
    if (reconnectTimer) clearTimeout(reconnectTimer);
    stopRecording();
    if (ws) ws.close();
    if (audioContext) audioContext.close();
    cancelAnimationFrame(animationFrameId);
  });

  return {
    isRecording,
    isPlaying,
    wsStatus,
    wsErrorMsg,
    aiText,
    userText,
    mouthOpenness,
    connectWebSocket,
    startRecording,
    stopRecording
  };
}
