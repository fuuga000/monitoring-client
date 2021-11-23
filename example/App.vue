<template>
  <div class="container">
    <div>
      <video
        id="cameraVideo"
        class="img-fluid"
        title="camera"
        autoplay
        playsinline
        muted
        controls
      ></video>
      camera
    </div>

    <div>
      <video
        id="monitorVideo"
        class="img-fluid"
        title="monitor"
        autoplay
        playsinline
        muted
        controls
      ></video>
      monitor
    </div>

    <select v-model="selectedCamera">
      <option :value="null">カメラを選択</option>
      <option v-for="camera in cameras" :value="camera" :key="camera.id">
        {{ camera.id }}
      </option>
    </select>

    <div>
      <button @click="cameraStart">camera start</button>
      <button @click="cameraStop">camera stop</button>
    </div>
  </div>
</template>

<script>
import MonitoringClient from '../dist/index'

const server_url = 'ws://localhost:8805/monitoring'

export default {
  data() {
    return {
      camera: null,
      cameraVideo: null,

      monitor: null,
      monitorVideo: null,

      selectedCamera: null,
    }
  },
  mounted() {
    this.cameraVideo = document.getElementById('cameraVideo')
    this.monitorVideo = document.getElementById('monitorVideo')

    this.monitor = new MonitoringClient(server_url, 'monitor')
    this.monitor.onSetStream = (s) => (this.monitorVideo.srcObject = s)
  },
  computed: {
    cameras() {
      return this.monitor ? this.monitor.cameras : []
    },
  },
  watch: {
    selectedCamera(camera) {
      this.monitor.connectCamera(camera)
    },
  },
  methods: {
    async cameraStart() {
      if (!this.camera) {
        this.camera = new MonitoringClient(server_url, 'camera')
      }

      this.camera.onSetStream = (s) => (this.cameraVideo.srcObject = s)
      await this.camera.cameraStart()
    },
    async cameraStop() {
      await this.camera.cameraStop()
    },
  },
}
</script>
