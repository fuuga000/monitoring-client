import CustomWebSocket from './websocket'
import { MonitoringType, Camera } from './types'

export default class MonitoringClient {
  type: MonitoringType
  pc?: RTCPeerConnection
  socket: CustomWebSocket
  stream?: MediaStream
  cameras: Camera[] = []
  constraints: object = { audio: false, video: true }

  constructor(websocket_url: string, type: MonitoringType, constraints: object = {}) {
    this.type = type
    Object.assign(this.constraints, constraints)

    this.socket = new CustomWebSocket(websocket_url)
    // typeに応じてメッセージ受け取り処理を振り分ける
    switch (this.type) {
      case 'camera':
        this.socket.onmessage = this.onCameraMessage.bind(this)
        break
      case 'monitor':
        this.socket.onmessage = this.onMonitorMessage.bind(this)
    }
  }

  async cameraStart() {
    this.pc = new RTCPeerConnection()
    this.pc.onconnectionstatechange = () => {
      const status = this.pc?.connectionState
      const failStatuses = ['disconnected', 'closed', 'failed']
      if (failStatuses.some((s) => s === status)) {
        this.closeConnection()
        this.cameraStart()
      }
    }
    const stream = await navigator.mediaDevices.getUserMedia(this.constraints)
    const tracks = stream.getTracks()
    tracks.forEach((track) => this.pc?.addTrack(track, stream))
    this.stream = stream
    this.onSetStream(stream)

    const offer = await this.pc.createOffer()
    await this.pc.setLocalDescription(offer)
    await this.waitStatusComplete(this.pc)
    this.socket.sendJson({
      action: 'offer',
      body: { id: this.socket.id, description: offer },
    })
  }

  async cameraStop() {
    if (!this.pc) return

    if (this.pc.getTransceivers) {
      this.pc.getTransceivers().forEach((transceiver) => transceiver.stop())
    }
    this.pc.getSenders().forEach((sender) => {
      if (sender && sender.track) sender.track.stop()
    })
    await new Promise((resolve) => setTimeout(resolve, 500))
    this.closeConnection()
  }

  async onCameraMessage(event: any) {
    const res = JSON.parse(String(event.data))
    switch (res.action) {
      case 'setting-self-id': {
        this.socket.setId(String(res.body.id))
        this.sendType()
        break
      }
      case 'answer': {
        if (!this.pc) return
        const description = new RTCSessionDescription(res.body.description)
        await this.pc.setRemoteDescription(description)
      }
    }
  }

  async onMonitorMessage(event: any) {
    const res = JSON.parse(String(event.data))
    switch (res.action) {
      case 'setting-self-id': {
        this.socket.setId(String(res.body.id))
        this.sendType()
        this.socket.sendJson({
          action: 'request-connecting-cameras',
          body: { id: this.socket.id },
        })
        break
      }
      case 'connecting-cameras': {
        this.cameras = res.body.cameras
        this.onUpdateCameras(this.cameras)
      }
    }
  }

  async connectCamera(camera: Camera) {
    this.closeConnection()
    if (!camera) return

    this.pc = new RTCPeerConnection()
    this.pc.ontrack = (e) => {
      this.stream = e.streams[0]
      this.onSetStream(e.streams[0])
    }
    const description = new RTCSessionDescription(camera.offer)
    await this.pc.setRemoteDescription(description)
    const answer = await this.pc.createAnswer()
    await this.pc.setRemoteDescription(description)
    await this.pc.setLocalDescription(answer)
    await this.waitStatusComplete(this.pc)
    this.socket.sendJson({
      action: 'answer',
      body: {
        id: this.socket.id,
        target: camera.id,
        description: this.pc.localDescription,
      },
    })
  }

  closeConnection() {
    if (!this.pc) return
    this.pc.close()
    this.pc = undefined
  }

  waitStatusComplete(pc: RTCPeerConnection): Promise<void> {
    return new Promise((resolve) => {
      if (pc.iceGatheringState === 'complete') {
        resolve()
      } else {
        const checkState = () => {
          if (pc.iceGatheringState === 'complete') {
            pc.removeEventListener('icegatheringstatechange', checkState)
            resolve()
          }
        }
        pc.addEventListener('icegatheringstatechange', checkState)
      }
    })
  }

  sendType() {
    this.socket.sendJson({
      action: 'set-type',
      body: {
        id: this.socket.id,
        type: this.type,
      },
    })
  }

  onUpdateCameras(cameras: Camera[]) {
    return cameras
  }

  onSetStream(stream: MediaStream) {
    return stream
  }
}
