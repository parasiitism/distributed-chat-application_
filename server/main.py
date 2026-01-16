import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis
import threading

app = FastAPI()

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
pubsub = redis_client.pubsub()
pubsub.subscribe("chat")

class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("Client connected")

    try:
        while True:
            data = await websocket.receive_text()
            print("Publishing:", data)
            redis_client.publish("chat", data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected")

#Background Redis listener
def redis_listener():
    for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            asyncio.run(manager.broadcast(data))

threading.Thread(target=redis_listener, daemon=True).start()
