import { ref, onUnmounted } from 'vue'

export function useMediaDevices() {
    // 暴露出的媒体流，供外部 <video> 绑定和后续 WebRTC 传输使用
    const videoStream = ref<MediaStream | null>(null)
    const audioStream = ref<MediaStream | null>(null)

    // 状态指示
    const isVideoEnabled = ref(false)
    const isAudioEnabled = ref(false)
    const isRequesting = ref(false)
    const errorMsg = ref('')

    // 内部保存的合并后的完整 Stream，方便统一释放
    let currentStream: MediaStream | null = null

    /**
     * 请求媒体权限并开启设备
     * @param enableVideo 是否开启摄像头
     * @param enableAudio 是否开启麦克风
     */
    const startDevices = async (enableVideo = true, enableAudio = true) => {
        if (isRequesting.value) return
        isRequesting.value = true
        errorMsg.value = ''

        try {
            // 调用浏览器原生 API 请求音视频权限
            currentStream = await navigator.mediaDevices.getUserMedia({
                video: enableVideo ? { width: 1280, height: 720, facingMode: 'user' } : false,
                audio: enableAudio ? { echoCancellation: true, noiseSuppression: true } : false
            })

            // 提取视频轨道（如果有的话）
            const videoTracks = currentStream.getVideoTracks()
            if (videoTracks.length > 0) {
                const vStream = new MediaStream([videoTracks[0]])
                videoStream.value = vStream
                isVideoEnabled.value = true
            }

            // 提取音频轨道（如果有的话）
            const audioTracks = currentStream.getAudioTracks()
            if (audioTracks.length > 0) {
                const aStream = new MediaStream([audioTracks[0]])
                audioStream.value = aStream
                isAudioEnabled.value = true
            }

        } catch (err: any) {
            console.error('Failed to get media devices:', err)
            if (err.name === 'NotAllowedError') {
                errorMsg.value = '您拒绝了相机或麦克风的权限，请在浏览器设置中开启后重试。'
            } else if (err.name === 'NotFoundError') {
                errorMsg.value = '未检测到可用的相机或麦克风设备。'
            } else {
                errorMsg.value = '无法打开设备: ' + err.message
            }
            isVideoEnabled.value = false
            isAudioEnabled.value = false
        } finally {
            isRequesting.value = false
        }
    }

    /**
     * 关闭所有正在使用的媒体设备，避免内存泄漏和设备占用（防指纹/红灯常亮）
     */
    const stopDevices = () => {
        if (currentStream) {
            currentStream.getTracks().forEach(track => {
                track.stop()
            })
            currentStream = null
        }
        videoStream.value = null
        audioStream.value = null
        isVideoEnabled.value = false
        isAudioEnabled.value = false
    }

    /**
     * 仅切换音频采集状态
     */
    const toggleAudio = () => {
        if (!currentStream) return
        const audioTrack = currentStream.getAudioTracks()[0]
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled
            isAudioEnabled.value = audioTrack.enabled
        }
    }

    /**
     * 仅切换视频采集状态
     */
    const toggleVideo = () => {
        if (!currentStream) return
        const videoTrack = currentStream.getVideoTracks()[0]
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled
            isVideoEnabled.value = videoTrack.enabled
        }
    }

    // 组件销毁时自动施放硬件资源
    onUnmounted(() => {
        stopDevices()
    })

    return {
        videoStream,
        audioStream,
        isVideoEnabled,
        isAudioEnabled,
        isRequesting,
        errorMsg,
        startDevices,
        stopDevices,
        toggleAudio,
        toggleVideo
    }
}
