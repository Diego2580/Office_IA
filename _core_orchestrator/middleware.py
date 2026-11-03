import sqlite3
import time
import os
from datetime import datetime

class TokenMiddleware:
    def __init__(self, db_path="logs_tokens/presupuesto.db"):
        self.db_path = db_path
        # Asegura que la carpeta exista
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._inicializar_bd()

    def _inicializar_bd(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS uso_tokens 
                          (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, modelo TEXT, tokens INTEGER)''')
        conn.commit()
        conn.close()

    def registrar_consumo(self, modelo: str, tokens: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        fecha = datetime.now().isoformat()
        cursor.execute("INSERT INTO uso_tokens (fecha, modelo, tokens) VALUES (?, ?, ?)", 
                       (fecha, modelo, tokens))
        conn.commit()
        conn.close()
        print(f"  [Middleware] Gasto registrado: {tokens} tokens en {modelo}")

    def manejar_error_api(self, error_str: str):
        if '429' in error_str or 'Too Many Requests' in error_str:
            print("  [ALERTA] Límite de cuota alcanzado (Error 429).")
            print("  [SISTEMA] Activando Failover: Pausando 60 segundos para enfriar la API...")
            time.sleep(60)
            print("  [SISTEMA] Reanudando operaciones.")
            return True
        return False
