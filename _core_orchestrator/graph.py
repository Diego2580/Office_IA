import sys, os, operator, json, time, re
from typing import TypedDict, Annotated, Sequence
from websockets.sync.client import connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from main import obtener_arquitecto, obtener_desarrollador
from tools import leer_archivo, escribir_archivo, listar_directorio, abrir_archivo

class EstadoOficina(TypedDict): messages: Annotated[Sequence[BaseMessage], operator.add]

arq_llm = obtener_arquitecto()
dev_llm = obtener_desarrollador()
herramientas = [leer_archivo, escribir_archivo, listar_directorio, abrir_archivo]
sec_con_herramientas = dev_llm.bind_tools(herramientas)

def notificar(agente, accion, estado):
    try:
        with connect("ws://127.0.0.1:8000/ws/oficina") as ws:
            ws.send(json.dumps({"agente": agente, "accion": accion, "estado": estado}))
        time.sleep(0.5)
    except: pass

def procesar_agente(rol, state, llm, prompt):
    print(f"\n[{rol}]: Operando...")
    notificar(rol, "Analizando", "Procesando")
    ruta = os.getcwd().replace('\\', '/')
    mensajes = [SystemMessage(content=f"{prompt} Ruta base: {ruta}")] + state['messages']
    
    for intento in range(4):
        try:
            res = llm.invoke(mensajes)
            notificar(rol, "Terminado", "Avanzando")
            time.sleep(1.5)
            return {"messages": [res]}
        except Exception:
            notificar(rol, "Reintentando", "Esquivando bloqueo de red")
            time.sleep(4)
    return {"messages": [AIMessage(content="Omitido por error de API.")]}

def nodo_arq(state):
    print("\n[ARQ]: Evaluando y Enrutando...")
    notificar("ARQ", "Enrutador", "Decidiendo flujo")
    prompt = """Eres el Arquitecto Supervisor. Analiza la peticion.
    Si requiere diseño/UI o crear paginas, empieza con [RUTA: UI].
    Si requiere solo backend, empieza con [RUTA: DEV].
    Si es solo guardar texto, empieza con [RUTA: SEC]."""
    return procesar_agente("ARQ", state, arq_llm, prompt)

def enrutador(state):
    ultimo_mensaje = state['messages'][-1].content.upper()
    if "[RUTA: UI]" in ultimo_mensaje: return "UI"
    if "[RUTA: DEV]" in ultimo_mensaje: return "DEV"
    if "[RUTA: SEC]" in ultimo_mensaje: return "SEC"
    return "UI"

def nodo_ui(state): return procesar_agente("UI", state, dev_llm, "Eres Diseñador UI/UX. Define el diseño web en texto.")
def nodo_dev(state): return procesar_agente("DEV", state, dev_llm, "Eres Desarrollador. Escribe todo el codigo fuente dentro de bloques ```html ... ```")
def nodo_qa(state): return procesar_agente("QA", state, dev_llm, "Eres QA. Aprueba el codigo brevemente.")

def nodo_sec(state):
    print("\n[SEC]: Verificando y guardando...")
    notificar("SEC", "Auditoria", "Extrayendo codigo puro")
    
    res = AIMessage(content="Fallback", tool_calls=[])
    for intento in range(3):
        try:
            res = sec_con_herramientas.invoke([SystemMessage(content="Usa escribir_archivo y abrir_archivo.")] + state['messages'])
            break
        except Exception:
            time.sleep(3)
    
    if not hasattr(res, 'tool_calls') or not res.tool_calls:
        prompt_usuario = state['messages'][0].content
        rutas = re.findall(r'[a-zA-Z]:\\[^\s"\'<>]+', prompt_usuario)
        ruta_final = rutas[0] if rutas else os.path.join(os.getcwd(), "resultado.html")
        if not '.' in ruta_final.split('\\')[-1]:
            ruta_final = os.path.join(ruta_final, "index.html")
            
        codigo_final = ""
        for msg in reversed(state['messages']):
            bloque = re.search(r'```(?:html|css|js|javascript|python)?\s*(.*?)```', msg.content, re.DOTALL | re.IGNORECASE)
            if bloque:
                codigo_final = bloque.group(1).strip()
                break
        if not codigo_final: codigo_final = state['messages'][-1].content
        
        llamadas_herramientas = [{"name": "escribir_archivo", "args": {"ruta": ruta_final, "contenido": codigo_final}, "id": "hack_w"}]
        
        # Evaluar si el usuario pidio abrir el archivo
        if "abrelo" in prompt_usuario.lower() or "abrir" in prompt_usuario.lower():
            llamadas_herramientas.append({"name": "abrir_archivo", "args": {"ruta": ruta_final}, "id": "hack_o"})
            
        res = AIMessage(content="Acciones completadas.", tool_calls=llamadas_herramientas)
        notificar("SEC", "Herramientas", "Guardando y abriendo")
    else:
        notificar("SEC", "Herramienta", res.tool_calls[0]['name'])
        
    return {"messages": [res]}

flujo = StateGraph(EstadoOficina)
flujo.add_node("ARQ", nodo_arq)
flujo.add_node("UI", nodo_ui)
flujo.add_node("DEV", nodo_dev)
flujo.add_node("QA", nodo_qa)
flujo.add_node("SEC", nodo_sec)
flujo.add_node("herramientas", ToolNode(herramientas))

flujo.add_edge(START, "ARQ")
flujo.add_conditional_edges("ARQ", enrutador, {"UI": "UI", "DEV": "DEV", "SEC": "SEC"})
flujo.add_edge("UI", "DEV")
flujo.add_edge("DEV", "QA")
flujo.add_edge("QA", "SEC")
flujo.add_conditional_edges("SEC", tools_condition, {"tools": "herramientas", END: END})
flujo.add_edge("herramientas", END)

app = flujo.compile()

if __name__ == '__main__':
    while True:
        try:
            with connect("ws://127.0.0.1:8000/ws/oficina") as ws:
                print(" -> Escuchando en localhost:8030...")
                notificar("ARQ", "Sistema en linea", "Esperando tu orden")
                while True:
                    data = json.loads(ws.recv())
                    if data.get("origen") == "usuario":
                        for salida in app.stream({"messages": [HumanMessage(content=data["texto"])]}):
                            if "herramientas" in salida: 
                                print(f"  [SO]: Acciones ejecutadas en disco.")
                        notificar("ARQ", "Tarea finalizada", "Listo")
        except Exception as e:
            time.sleep(3)
