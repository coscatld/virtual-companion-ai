<template>
  <div ref="canvasContainer" class="w-full h-full cursor-grab active:cursor-grabbing relative bg-transparent overflow-hidden">
    <!-- 如果在加载中显示 Loading 提示 -->
    <div v-if="isLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-gray-900 bg-opacity-80 z-10">
      <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500 mb-4"></div>
      <p class="text-white text-lg tracking-widest font-semibold">正在唤醒相伴的数字灵魂 ({{ loadingProgress }}%)...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { VRMLoaderPlugin, VRMUtils, VRM } from '@pixiv/three-vrm'

// Props 可以以后扩展用来区分加载不同的模型
const props = defineProps({
  modelUrl: {
    type: String,
    default: '/models/avatar.vrm' // 默认测试模型路径
  }
})

// DOM 与状态
const canvasContainer = ref<HTMLElement | null>(null)
const isLoading = ref(true)
const loadingProgress = ref(0)
let currentVrm: VRM | null = null

// Three.js 核心对象
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let clock: THREE.Clock
let animationFrameId: number

/**
 * 初始化场景，灯光和摄像机
 */
const initScene = () => {
  if (!canvasContainer.value) return

  const container = canvasContainer.value
  const width = container.clientWidth
  const height = container.clientHeight

  // 1. 初始化 Scene
  scene = new THREE.Scene()
  
  // 此时设置背景为透明或浅色调，为了和外部全屏 Layout 融合
  scene.background = new THREE.Color(0xF5F7FA) // 或者 null 支持透明度
  // scene.fog = new THREE.Fog(0xFFFFFF, 1, 10)

  // 2. 初始化 Camera (近景/半身像视角)
  camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 20.0)
  camera.position.set(0.0, 1.4, 3.5) // X, Y, Z (视角放在模型脸部正前方 3.5m 处)

  // 3. 初始化 Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.outputColorSpace = THREE.SRGBColorSpace // @pixiv/three-vrm 对 sRGB 有要求
  container.appendChild(renderer.domElement)

  // 4. 初始化 控制器 (OrbitControls 方便用鼠标旋转/缩放数字人)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.screenSpacePanning = true
  controls.target.set(0.0, 1.4, 0.0) // 聚焦在模型的脸部(1.4m高度)
  controls.update()
  // 防止老年人乱动把人转没，可以限制拖拽角度
  controls.minDistance = 1.0
  controls.maxDistance = 5.0
  controls.maxPolarAngle = Math.PI / 1.5 // 限制俯仰角，别看到裙底或脚底

  // 5. 初始化 灯光
  const light = new THREE.DirectionalLight(0xffffff, Math.PI)
  light.position.set(1.0, 1.0, 1.0).normalize()
  scene.add(light)
  
  const ambientLight = new THREE.AmbientLight(0xffffff, Math.PI / 2) // 增加环境光防止背光死黑
  scene.add(ambientLight)

  // 6. 初始化时钟，用于平滑混合动画 (Spring) 等参数
  clock = new THREE.Clock()
}

/**
 * 加载 VRM 格式的数字人
 */
const loadVrm = () => {
  const loader = new GLTFLoader()
  // 注册 VRM 解析插件
  loader.register((parser) => {
    return new VRMLoaderPlugin(parser)
  })

  loader.load(
    props.modelUrl,
    (gltf) => {
      const vrm = gltf.userData.vrm as VRM
      
      // 取消之前的模型（如果存在切换逻辑）
      if (currentVrm) {
        scene.remove(currentVrm.scene)
        VRMUtils.removeUnloadables(currentVrm.scene)
      }

      // 为了确保 VRM 在不同方向不受影响，调用这个工具函数修正
      VRMUtils.removeUnloadables(gltf.scene)
      
      vrm.scene.rotation.y = Math.PI // 旋转 180 度让他正对镜头
      
      // 将模型加入场景
      scene.add(vrm.scene)
      currentVrm = vrm

      isLoading.value = false
      console.log('VRM Model Loaded Successfully!')
      
      // 开启渲染循环
      render()
    },
    (progress) => {
      loadingProgress.value = Math.round((progress.loaded / progress.total) * 100)
    },
    (error) => {
      console.error('Failed to load VRM model:', error)
      isLoading.value = false
      // Fallback 策略可以放在外层
    }
  )
}

/**
 * [对外暴露] 测试更新嘴巴开合度 (例如 0.0 到 1.0)
 * 您可以在使用此组件的地方，通过 ref 调用 updateMouth() 传入音频音量大小！
 */
const updateMouth = (openness: number) => {
  if (currentVrm && currentVrm.expressionManager) {
    // aa, ih, ou, ee, oh 是 VRM 标准定义的嘴型。
    // 我们最简单地驱动 'aa' (嘴巴张大) 即可
    currentVrm.expressionManager.setValue('aa', openness)
  }
}

/**
 * 窗体改变响应
 */
const onWindowResize = () => {
  if (!containerClientRef.value || !camera || !renderer) return
  camera.aspect = containerClientRef.value.clientWidth / containerClientRef.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(containerClientRef.value.clientWidth, containerClientRef.value.clientHeight)
}
const containerClientRef = computed(() => canvasContainer.value)


/**
 * 游戏循环 (渲染每一帧)
 */
const render = () => {
  animationFrameId = requestAnimationFrame(render)

  const deltaTime = clock.getDelta()

  if (currentVrm) {
    // 每次渲染必须更新 VRM (包含弹簧骨骼动态、表情混合步进等)
    currentVrm.update(deltaTime)
  }

  // 渲染这一帧
  renderer.render(scene, camera)
}


// 生命周期管理
onMounted(() => {
  initScene()
  loadVrm()
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
  // === 非常重要的内存清理逻辑 ===
  window.removeEventListener('resize', onWindowResize)
  cancelAnimationFrame(animationFrameId)
  
  if (currentVrm) {
    scene.remove(currentVrm.scene)
    VRMUtils.removeUnloadables(currentVrm.scene)
  }
  
  if (renderer && renderer.domElement) {
    // 从 DOM 移除 Canvas
    renderer.domElement.remove()
    renderer.dispose() // 释放 WebGL Context
  }
})

// 暴露 API 给父组件控制
defineExpose({
  updateMouth
})
</script>
