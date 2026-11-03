import os
import json
import urllib.request
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

load_dotenv()

# Arquitecto confirmado
GEMINI_FALLBACKS = [
    "gemini-3.5-flash"
]

def obtener_arquitecto():
    print("[1/2] Buscando Arquitecto disponible (Google API)...")
    for modelo in GEMINI_FALLBACKS:
        try:
            llm = ChatGoogleGenerativeAI(
                model=modelo,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.2
            )
            llm.invoke("Responde 'ok' en minusculas.")
            print(f"  [EXITO] Arquitecto conectado usando: {modelo}")
            return llm
        except Exception as e:
            print(f"  [FALLO] {modelo} falló.")
    raise Exception("Error crítico de Google.")

def obtener_modelos_gratuitos():
    print("\n  -> Escaneando base de datos de OpenRouter en tiempo real...")
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # Filtramos todos los modelos que su ID termine en ":free"
            modelos = [m["id"] for m in data.get("data", []) if m["id"].endswith(":free")]
            print(f"  -> Se detectaron {len(modelos)} modelos gratuitos activos en este momento.")
            return modelos
    except Exception as e:
        print(f"  -> Error al escanear la API: {e}")
        return []

def obtener_desarrollador():
    print("[2/2] Buscando Desarrollador disponible (OpenRouter Free)...")
    modelos_disponibles = obtener_modelos_gratuitos()
    
    for modelo in modelos_disponibles:
        try:
            print(f"  -> Probando {modelo}...")
            llm = ChatOpenAI(
                model=modelo,
                openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                openai_api_base="https://openrouter.ai/api/v1",
                temperature=0.4,
                max_tokens=10
            )
            llm.invoke("Responde 'ok' en minusculas.")
            print(f"  [EXITO] Desarrollador conectado usando: {modelo}")
            return llm
        except Exception as e:
            print(f"  [FALLO] {modelo} rechazado. Saltando al siguiente...")
            
    raise Exception("Error crítico: Ningún modelo gratuito conectó con éxito.")

if __name__ == '__main__':
    print("--- Iniciando Orquestador con Auto-Descubrimiento de Modelos ---")
    arquitecto = obtener_arquitecto()
    desarrollador = obtener_desarrollador()
    print("\n¡Oficina IA conectada y lista para trabajar!")
