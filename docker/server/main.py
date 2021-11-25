from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.endpoints import WebSocketEndpoint
from typing import Any
from schemas import Message
from pydantic import ValidationError


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


@app.websocket_route("/monitoring")
class MonitoringtEndpoint(WebSocketEndpoint):
    encoding = 'json'
    clients = {}

    async def on_connect(self, ws: WebSocket) -> None:
        await ws.accept()
        key = ws.headers.get('sec-websocket-key')
        client = WebSocketClient(key, ws)
        self.clients[key] = client

        # IDを通知
        await ws.send_json(
            {
                "action": "setting-self-id",
                "body": { "id": key }
            }
        )

    async def on_receive(self, ws: WebSocket, data: Any) -> None:
        try:
            message = Message(**data)
        except ValidationError as e:
            await ws.send_json(
                {
                    "action": "validation-error",
                    "body": {
                        "message": "not match format",
                        "detail": str(e),
                    }
                }
            )
            return
        except Exception as e:
            print(e)
            await ws.close()
            return

        body = message.body
        if message.action == "set-type":
            self.clients[body.id].set_type(body.type)
        elif message.action == "set-state":
            self.clients[body.id].set_state(body.state)
        elif message.action == "offer":
            offer = body.description
            self.clients[body.id].set_offer(offer)
            await self.send_cameras()
        elif message.action == "answer":
            answer = body.description
            client = self.clients[body.target]
            if client:
                await client.socket.send_json(
                    {
                        "action": "answer",
                        "body": { "description": answer }
                    }
                )
        elif message.action == "request-connecting-cameras":
            await self.send_cameras()

    async def on_disconnect(self, ws: WebSocket, close_code: int) -> None:
        key = ws.headers.get('sec-websocket-key')
        del self.clients[key]

    async def send_cameras(self) -> None:
        cameras = []
        for client in self.clients.values():
            if client.type == "camera":
                cameras.append(
                    {
                        "id": client.id,
                        "offer": client.offer,
                    }
                )
        for client in self.clients.values():
            if client.type == "monitor":
                await client.socket.send_json(
                    {
                        "action": "connecting-cameras",
                        "body": { "cameras": cameras }
                    }
                )
