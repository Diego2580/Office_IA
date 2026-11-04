import os
import json
import urllib.request
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

# Forzar la recarga del archivo .env ignorando la caché de la terminal
load_dotenv(override=True)

GEMINI_FALLBACKS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"]
OPENROUTER_FREE_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "xingchen-agi/xing4.0-29b-a4b:free",
    "google/gemini-2.0-flash-exp:free"
]

def obtener_modelos_gratuitos():
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            modelos = [m["id"] for m in data.get("data", []) if m["id"].endswith(":free")]
            return modelos if modelos else OPENROUTER_FREE_MODELS
    except Exception:
        return OPENROUTER_FREE_MODELS

def obtener_arquitecto():
    print("[1/2] Buscando Arquitecto disponible...")
    for modelo in GEMINI_FALLBACKS:
        try:
            llm = ChatGoogleGenerativeAI(
                model=modelo, google_api_key=os.getenv("GEMINI_API_KEY"), temperature=0.2
            )
            llm.invoke("Responde 'ok'.")
            print(f"  [EXITO] Arquitecto conectado en Google: {modelo}")
            return llm
        except Exception:
            print(f"  [FALLO] Google {modelo} bloqueado por cuota.")
            
    print("  [ALERTA] Cuota de Google agotada. Redirigiendo Arquitecto a OpenRouter...")
    modelos = obtener_modelos_gratuitos()
    for modelo in modelos:
        try:
            llm = ChatOpenAI(
                model=modelo,
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                temperature=0.2
            )
            llm.invoke("Responde 'ok'.")
            print(f"  [EXITO] Arquitecto de rescate en OpenRouter: {modelo}")
            return llm
        except Exception:
            continue
    raise Exception("Error crítico: Sin acceso a modelos en Google ni OpenRouter.")

def obtener_desarrollador():
    print("[2/2] Buscando Desarrollador disponible (OpenRouter Free)...")
    modelos = obtener_modelos_gratuitos()
    for modelo in modelos:
        try:
            print(f"  -> Probando {modelo}...")
            llm = ChatOpenAI(
                model=modelo,
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url="https://openrouter.ai/api/v1",
                temperature=0.4
            )
            llm.invoke("Responde 'ok'.")
            print(f"  [EXITO] Desarrollador conectado usando: {modelo}")
            return llm
        except Exception:
            print(f"  [FALLO] {modelo} rechazado.")
    raise Exception("Error crítico: Ningún modelo gratuito conectó.")
