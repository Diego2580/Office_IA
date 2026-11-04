import os
import json
import urllib.request
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

load_dotenv()

GEMINI_FALLBACKS = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"]

def obtener_modelos_gratuitos():
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return [m["id"] for m in data.get("data", []) if m["id"].endswith(":free")]
    except Exception:
        return []

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
    for modelo in obtener_modelos_gratuitos():
        try:
            # ACTUALIZADO: api_key y base_url para evitar warnings en Pylance
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
            # ACTUALIZADO: api_key y base_url para evitar warnings en Pylance
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
