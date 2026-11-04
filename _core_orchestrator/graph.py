import sys, os, operator, json, time, re
from typing import TypedDict, Annotated, Sequence
from websockets.sync.client import connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from main import obtener_arquitecto, obtener_desarrollador
from tools import leer_archivo, escribir_archivo, listar_directorio, abrir_archivo, explorar_web

class EstadoOficina(TypedDict): messages: Annotated[Sequence[BaseMessage], operator.add]

arq_llm = obtener_arquitecto()
dev_llm = obtener_desarrollador()
herramientas = [leer_archivo, escribir_archivo, listar_directorio, abrir_archivo, explorar_web]
sec_con_herramientas = dev_llm.bind_tools(herramientas)

def notificar(agente, accion, estado):
    try:
        with connect("ws://127.0.0.1:8000/ws/oficina") as ws: ws.send(json.dumps({"agente": agente, "accion": accion, "estado": estado}))
        time.sleep(0.5)
    except: pass

def procesar_agente(rol, state, llm, prompt):
    print(f"\n[{rol}]: Operando...")
    notificar(rol, "Analizando", "Vibecoding...")
    mensajes = [SystemMessage(content=f"{prompt} Ruta base: {os.getcwd()}")] + state['messages']
    for intento in range(3):
        try:
            res = llm.invoke(mensajes)
            notificar(rol, "Terminado", "Listo")
            time.sleep(1)
            return {"messages": [res]}
        except Exception:
            notificar(rol, "Reintentando", "Esquivando red")
            time.sleep(3)
    return {"messages": [AIMessage(content="Error API.")]}

def nodo_arq(state):
    notificar("ARQ", "Enrutador", "Evaluando")
    prompt = """Eres Arquitecto Jefe operando bajo VIBECODING. Cero SDD, cero burocracia. Iteramos rápido.
    - Si dan URL o piden analizar estructura/ingeniería inversa: [RUTA: DEV]
    - Si suben IMAGEN o piden UI/diseño: [RUTA: UI]
    - Si solo piden abrir, guardar o leer algo puntual: [RUTA: SEC]"""
    return procesar_agente("ARQ", state, arq_llm, prompt)

def enrutador(state):
    msg = state['messages'][-1].content.upper()
    if "[RUTA: UI]" in msg: return "UI"
    if "[RUTA: DEV]" in msg: return "DEV"
    return "SEC"

def nodo_ui(state): return procesar_agente("UI", state, dev_llm, "Diseñador UI/UX experto en Vibecoding. Si te pasan imagen, clónala pixel-perfect en código moderno.")
def nodo_dev(state): return procesar_agente("DEV", state, dev_llm, "Eres Claude, el Desarrollador FullStack. Escribe código completo y funcional en bloques ```lenguaje ... ```. Usa herramientas web si hay URLs.")
def nodo_qa(state): return procesar_agente("QA", state, dev_llm, "QA rapido. Aprueba con 'OK' o arregla el codigo si hay error obvio.")

def auditar_secretos(codigo: str) -> tuple[str, bool]:
    """Filtro DevSecOps continuo: Neutraliza API Keys expuestas."""
    encontrado = False
    # Patrón OpenAI / OpenRouter / Anthropic (sk-...)
    if re.search(r'sk-[a-zA-Z0-9_-]{20,}', codigo):
        codigo = re.sub(r'sk-[a-zA-Z0-9_-]{20,}', 'os.getenv("API_KEY_PROTEGIDA")', codigo)
        encontrado = True
    # Patrón Google Gemini (AIza...)
    if re.search(r'AIza[a-zA-Z0-9_-]{35}', codigo):
        codigo = re.sub(r'AIza[a-zA-Z0-9_-]{35}', 'os.getenv("GEMINI_KEY_PROTEGIDA")', codigo)
        encontrado = True
    return codigo, encontrado

def nodo_sec(state):
    notificar("SEC", "Sistema", "Ejecutando IO")
    prompt_usuario = state['messages'][0].content.lower() if isinstance(state['messages'][0].content, str) else str(state['messages'][0].content).lower()
    
    res = AIMessage(content="Fallback", tool_calls=[])
    for _ in range(2):
        try:
            res = sec_con_herramientas.invoke([SystemMessage(content="Ejecuta herramientas OBLIGATORIO.")] + state['messages'])
            break
        except: time.sleep(2)
    
    if not hasattr(res, 'tool_calls') or not res.tool_calls:
        llamadas = []
        texto_hist = " ".join([m.content if isinstance(m.content, str) else "" for m in state['messages']])
        rutas = re.findall(r'[a-zA-Z]:\\[^\s"\'<>]+', texto_hist)
        ruta_final = rutas[0] if rutas else os.path.join(os.getcwd(), "resultado.html")
        
        if "abre" in prompt_usuario: llamadas.append({"name": "abrir_archivo", "args": {"ruta": ruta_final}, "id": "hk_o"})
        else:
            codigo_final = ""
            for msg in reversed(state['messages']):
                bloque = re.search(r'```[a-z]*\n(.*?)```', msg.content if isinstance(msg.content, str) else "", re.DOTALL | re.IGNORECASE)
                if bloque:
                    codigo_final = bloque.group(1).strip()
                    break
            if codigo_final:
                # [DEVSECOPS]: Escaneo e intercepción
                codigo_seguro, interceptado = auditar_secretos(codigo_final)
                if interceptado:
                    notificar("SEC", "Alerta", "Secreto neutralizado")
                    print("  [SEC-ALERT] Se detectó y bloqueó una API Key en el código generado por Claude.")
                    
                llamadas.append({"name": "escribir_archivo", "args": {"ruta": ruta_final, "contenido": codigo_seguro}, "id": "hk_w"})
                if "abre" in prompt_usuario: llamadas.append({"name": "abrir_archivo", "args": {"ruta": ruta_final}, "id": "hk_o2"})
        res = AIMessage(content="Vibecoding Action", tool_calls=llamadas)
    
    return {"messages": [res]}

app = StateGraph(EstadoOficina)
app.add_node("ARQ", nodo_arq); app.add_node("UI", nodo_ui); app.add_node("DEV", nodo_dev); app.add_node("QA", nodo_qa); app.add_node("SEC", nodo_sec); app.add_node("herramientas", ToolNode(herramientas))
app.add_edge(START, "ARQ"); app.add_conditional_edges("ARQ", enrutador, {"UI": "UI", "DEV": "DEV", "SEC": "SEC"})
app.add_edge("UI", "DEV"); app.add_edge("DEV", "QA"); app.add_edge("QA", "SEC")
app.add_conditional_edges("SEC", tools_condition, {"tools": "herramientas", END: END}); app.add_edge("herramientas", END)
motor = app.compile(checkpointer=MemorySaver())

if __name__ == '__main__':
    while True:
        try:
            with connect("ws://127.0.0.1:8000/ws/oficina") as ws:
                print(" -> Agencia Vibecoding Lista con DevSecOps Activo...")
                while True:
                    data = json.loads(ws.recv())
                    if data.get("origen") == "usuario":
                        content = []
                        if data.get("texto"): content.append({"type": "text", "text": data["texto"]})
                        if data.get("imagen"): content.append({"type": "image_url", "image_url": {"url": data["imagen"]}})
                        if not content: continue
                        
                        config = {"configurable": {"thread_id": "vibecoding_session_1"}}
                        for salida in motor.stream({"messages": [HumanMessage(content=content)]}, config=config):
                            pass
                        notificar("ARQ", "Completado", "Siguiente orden")
        except: time.sleep(3)
