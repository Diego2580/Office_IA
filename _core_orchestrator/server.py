import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List
import uvicorn

app = FastAPI(title="AI Office Bridge")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Cliente conectado. Total activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] Cliente desconectado. Total activos: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@app.websocket("/ws/oficina")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[Broadcast recibido]: {data}")
            # Reenviar a todos los clientes (navegador incluido)
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    print("--- Iniciando Servidor de Comunicaciones con Broadcast ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)
