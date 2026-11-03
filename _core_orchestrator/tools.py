import os
from langchain_core.tools import tool

@tool
def leer_archivo(ruta_absoluta: str) -> str:
    "`"`"Lee el contenido de un archivo en el disco duro local del usuario."`"`"
    try:
        with open(ruta_absoluta, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error al leer: {str(e)}"

@tool
def escribir_archivo(ruta_absoluta: str, contenido: str) -> str:
    "`"`"Escribe o sobrescribe un archivo con código en el disco duro local."`"`"
    try:
        # Crea las carpetas intermedias si no existen
        os.makedirs(os.path.dirname(ruta_absoluta), exist_ok=True)
        with open(ruta_absoluta, 'w', encoding='utf-8') as f:
            f.write(contenido)
        return f"Éxito: Archivo guardado en {ruta_absoluta}"
    except Exception as e:
        return f"Error al escribir: {str(e)}"

@tool
def listar_directorio(ruta_absoluta: str) -> str:
    "`"`"Lista los archivos y carpetas dentro de un directorio dado."`"`"
    try:
        elementos = os.listdir(ruta_absoluta)
        return f"Contenido de {ruta_absoluta}:\n" + "\n".join(elementos)
    except Exception as e:
        return f"Error al listar el directorio: {str(e)}"
