import os
from langchain_core.tools import tool

@tool
def leer_archivo(ruta: str) -> str:
    try:
        with open(ruta, 'r', encoding='utf-8') as f: return f.read()
    except Exception as e: return f"Error leyendo: {e}"

@tool
def escribir_archivo(ruta: str, contenido: str) -> str:
    try:
        if os.path.dirname(ruta): os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as f: f.write(contenido)
        return f"Éxito: Archivo guardado en {ruta}"
    except Exception as e: return f"Error escribiendo: {e}"

@tool
def listar_directorio(ruta: str) -> str:
    try: return "\n".join(os.listdir(ruta))
    except Exception as e: return f"Error listando: {e}"

@tool
def abrir_archivo(ruta: str) -> str:
    """Abre un archivo local en el navegador o programa predeterminado de Windows."""
    try:
        os.startfile(ruta)
        return f"Éxito: Archivo {ruta} abierto en pantalla."
    except Exception as e:
        return f"Error abriendo archivo: {e}"
