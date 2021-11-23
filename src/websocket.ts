export default class CustomWebSocket extends WebSocket {
  id?: string

  setId(id: string) {
    this.id = id
  }

  sendJson(text: object) {
    this.send(JSON.stringify(text))
  }
}
