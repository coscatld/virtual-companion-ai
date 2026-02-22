import { ref, onUnmounted } from 'vue';

export function useAudioStream() {
  const isRecording = ref(false);
  const isPlaying = ref(false);
  const wsStatus = ref<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const wsErrorMsg = ref('');
  const aiText = ref('');
  const userText = ref('');
  const mouthOpenness = ref(0); // 0.0 to 1.0 用于驱动数字人嘴巴张合度

  let ws: WebSocket | null = null;
  let mediaRecorder: MediaRecorder | null = null;
  let audioContext: AudioContext | null = null;
  let analyser: AnalyserNode | null = null;
  let animationFrameId: number;

  const connectWebSocket = () => {
    if (ws && ws.readyState !== WebSocket.CLOSED) return;

    wsStatus.value = 'connecting';
    const token = localStorage.getItem('token') || '';
    const wsUrl = `ws://localhost:8080/audio?token=${token}`;
    
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer'; // 接收后端返回的纯二进制流

    ws.onopen = () => {
      wsStatus.value = 'connected';
      wsErrorMsg.value = '';
    };

    ws.onmessage = async (event) => {
      // 收到后端的音频二进制流或文本
      if (event.data instanceof ArrayBuffer) {
        await playAudioChunk(event.data);
      } else if (typeof event.data === 'string') {
        const res = JSON.parse(event.data);
        if (res.ai_text) {
          aiText.value += res.ai_text;
        }
      }
    };

    ws.onclose = () => {
      wsStatus.value = 'disconnected';
      if (isRecording.value) stopRecording();
      // 提示重连
      setTimeout(connectWebSocket, 3000); 
    };

    ws.onerror = (error) => {
      wsStatus.value = 'error';
      wsErrorMsg.value = '网络开小差了，正在为您重连...';
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
      source.connect(analyser); // 连接到分析器以便计算音量
      
      isPlaying.value = true;
      source.onended = () => {
        isPlaying.value = false;
        mouthOpenness.value = 0; // 说话结束，闭嘴
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
        sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    // 归一化音量到 0.0 ~ 1.0 (根据实际音量反馈微调分母)
    mouthOpenness.value = Math.min(1.0, average / 60);

    if (isPlaying.value) {
      animationFrameId = requestAnimationFrame(monitorAudioLevel);
    } else {
      cancelAnimationFrame(animationFrameId);
      mouthOpenness.value = 0;
    }
  };

  const startRecording = async () => {
    if (wsStatus.value !== 'connected') {
       alert("网络未连接，请稍等再试");
       return;
    }
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' }); // Chrome 默认
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
          // 向后端发送录音碎块
          ws.send(e.data);
        }
      };

      mediaRecorder.start(500); // 时间切片，每 500ms 触发一次 ondataavailable
      isRecording.value = true;
      aiText.value = ''; // 准备接收新一轮
      userText.value = '正在倾听您说话...';
    } catch (err) {
      console.error('麦克风权限被拒:', err);
      alert('请允许麦克风访问权限才可以说话哦。');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording.value) {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach(track => track.stop());
      
      // 发送 0 字节空包给后端，代表 VAD Endpoint，说话完毕
      if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(new Uint8Array(0));
      }
      isRecording.value = false;
      userText.value = '您的声音已发送，等待伴侣回复...';
    }
  };

  onUnmounted(() => {
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
