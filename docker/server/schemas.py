from pydantic import BaseModel


class MessageBody(BaseModel):
    id: str = ""
    state: str = ""
    type: str = ""
    target: str = ""
    description: dict = {}

class Message(BaseModel):
    action: str
    body: MessageBody = {}
