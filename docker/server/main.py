from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WebSocketClient():
    def __init__(self, id: str, socket: WebSocket) -> None:
        self.id = id
        self.socket = socket
        self.type = "camera"
        self.offer = ""
        self.state = "init"

    def set_type(self, type: str):
        self.type = type

    def set_offer(self, offer: str):
        self.offer = offer

    def set_state(self, state: str):
        self.state = state

clients = {}

@app.websocket("/monitoring")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    key = ws.headers.get('sec-websocket-key')
    client = WebSocketClient(key, ws)
    clients[key] = client

    # IDを通知
    await ws.send_json(
      {
        "action": "setting-self-id",
        "body": { "id": key }
      }
    )

    try:
        while True:
            res = await ws.receive_json()
            action = res.get("action")
            body = res.get("body")
            if action == "set-type":
                type = body.get("type")
                clients[body.get("id")].set_type(type)
            elif action == "set-state":
                state = body.get("state")
                clients[body.get("id")].set_state(state)
            elif action == "offer":
                offer = body.get("description")
                clients[body.get("id")].set_offer(offer)
                await send_cameras()
            elif action == "answer":
                answer = body.get("description")
                client = clients[body.get("target")]
                if client:
                    await client.socket.send_json(
                        {
                            "action": "answer",
                            "body": { "description": answer }
                        }
                    )
                await send_cameras()
            elif action == "request-connecting-cameras":
                await send_cameras()

    except Exception:
        await ws.close()
        del clients[key]
        for client in clients.values():
            if client.type == "monitor":
                await send_cameras()


async def send_cameras() -> None:
    cameras = []
    for client in clients.values():
        if client.type == "camera":
            cameras.append(
                {
                    "id": client.id,
                    "offer": client.offer,
                }
            )
    for client in clients.values():
        if client.type == "monitor":
            await client.socket.send_json(
                {
                    "action": "connecting-cameras",
                    "body": { "cameras": cameras }
                }
            )

@app.on_event("shutdown")
async def on_shutdown():
    for client in clients.values():
      client.socket.close()
