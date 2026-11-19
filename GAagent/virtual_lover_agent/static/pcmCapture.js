class PcmCapture extends AudioWorkletProcessor {
  buffer = new Float32Array(2048)
  length = 0

  constructor() {
    super()
    this.port.onmessage = () => {
      this.flush()
      this.port.postMessage(null)
    }
  }

  flush() {
    if (!this.length) return
    const samples = this.buffer.slice(0, this.length)
    this.port.postMessage(samples, [samples.buffer])
    this.length = 0
  }

  process(inputs) {
    const samples = inputs[0]?.[0]
    if (!samples) return true
    for (const sample of samples) {
      this.buffer[this.length++] = sample
      if (this.length === this.buffer.length) this.flush()
    }
    return true
  }
}

registerProcessor('ga-pcm', PcmCapture)
