import os
from langchain_core.tools import tool

@tool
def leer_archivo(ruta: str) -> str:
    """Lee el contenido de un archivo local."""
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error leyendo: {e}"

@tool
def escribir_archivo(ruta: str, contenido: str) -> str:
    """Escribe contenido en disco y crea las carpetas necesarias si no existen."""
    try:
        directorio = os.path.dirname(ruta)
        if directorio:
            os.makedirs(directorio, exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return f"Éxito: Archivo guardado en {ruta}"
    except Exception as e:
        return f"Error escribiendo: {e}"

@tool
def listar_directorio(ruta: str) -> str:
    """Lista archivos de un directorio."""
    try:
        return "\n".join(os.listdir(ruta))
    except Exception as e:
        return f"Error listando: {e}"
