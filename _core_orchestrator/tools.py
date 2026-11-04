import os
import urllib.request
from langchain_core.tools import tool

@tool
def leer_archivo(ruta: str) -> str:
    """Lee el contenido de un archivo local para tener contexto."""
    try:
        with open(ruta, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return f"Error: {e}"

@tool
def escribir_archivo(ruta: str, contenido: str) -> str:
    """Escribe o sobrescribe un archivo en disco."""
    try:
        if os.path.dirname(ruta): os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f: f.write(contenido)
        return f"Éxito guardando {ruta}"
    except Exception as e: return f"Error: {e}"

@tool
def listar_directorio(ruta: str) -> str:
    """Muestra los archivos de una carpeta para entender la estructura de una App."""
    try: return "\n".join(os.listdir(ruta))
    except Exception as e: return f"Error: {e}"

@tool
def abrir_archivo(ruta: str) -> str:
    """Abre el archivo web o proyecto en pantalla."""
    try:
        os.startfile(ruta)
        return f"Abierto: {ruta}"
    except Exception as e: return f"Error: {e}"

@tool
def explorar_web(url: str) -> str:
    """Extrae el código HTML o texto de una URL para hacer ingeniería inversa."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return response.read().decode('utf-8')[:15000] # Límite seguro de tokens
    except Exception as e: return f"Error web: {e}"
