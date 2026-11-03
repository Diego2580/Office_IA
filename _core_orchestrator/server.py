from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

app = FastAPI(title="AI Office Workspace API")

# Evita bloqueos de seguridad cuando el mapa 2D (Angular/HTML) se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print("  [WebSocket] Cliente 2D conectado.")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print("  [WebSocket] Cliente 2D desconectado.")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@app.websocket("/ws/oficina")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Escucha comandos que envíes desde la interfaz del juego
            data = await websocket.receive_text()
            print(f"  [Interfaz 2D]: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
def root():
    return {"estado": "Motor de AI Office ejecutándose correctamente."}

if __name__ == '__main__':
    print("--- Iniciando Servidor de Comunicaciones ---")
    uvicorn.run(app, host="0.0.0.0", port=8000)
