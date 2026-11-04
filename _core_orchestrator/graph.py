import sys, os, operator, json, time
from typing import TypedDict, Annotated, Sequence
from websockets.sync.client import connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from main import obtener_arquitecto, obtener_desarrollador
from tools import leer_archivo, escribir_archivo, listar_directorio

class EstadoOficina(TypedDict): messages: Annotated[Sequence[BaseMessage], operator.add]

arq_llm = obtener_arquitecto()
dev_llm = obtener_desarrollador()
herramientas = [leer_archivo, escribir_archivo, listar_directorio]
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
    res = llm.invoke([SystemMessage(content=f"{prompt} Ruta base: {ruta}")] + state['messages'])
    notificar(rol, "Terminado", "Avanzando")
    return {"messages": [res]}

def nodo_arq(state):
    print("\n[ARQ]: Evaluando y Enrutando...")
    notificar("ARQ", "Enrutador", "Decidiendo flujo")
    prompt = """Eres el Arquitecto Supervisor. Analiza la petición del usuario.
    Si requiere diseño/colores/frontend, empieza tu respuesta EXACTAMENTE con [RUTA: UI].
    Si requiere solo código lógico/backend, empieza con [RUTA: DEV].
    Si es solo guardar un texto o archivo simple, empieza con [RUTA: SEC].
    Luego explica brevemente tu plan."""
    res = arq_llm.invoke([SystemMessage(content=prompt)] + state['messages'])
    return {"messages": [res]}

def enrutador(state):
    ultimo_mensaje = state['messages'][-1].content.upper()
    if "[RUTA: UI]" in ultimo_mensaje: return "UI"
    if "[RUTA: DEV]" in ultimo_mensaje: return "DEV"
    if "[RUTA: SEC]" in ultimo_mensaje: return "SEC"
    return "DEV"

def nodo_ui(state): return procesar_agente("UI", state, dev_llm, "Eres Diseñador UI/UX.")
def nodo_dev(state): return procesar_agente("DEV", state, dev_llm, "Eres Desarrollador. Escribe código.")
def nodo_qa(state): return procesar_agente("QA", state, dev_llm, "Eres QA. Busca bugs, no uses herramientas.")

def nodo_sec(state):
    print("\n[SEC]: Verificando y guardando...")
    notificar("SEC", "Auditoria", "Guardando a disco")
    instruccion = SystemMessage(content=f"Eres DevSecOps. OBLIGATORIO: Usa 'escribir_archivo' con ruta absoluta ({os.getcwd()}) para crear el archivo solicitado.")
    mensajes = list(state['messages'])
    for _ in range(3):
        res = sec_con_herramientas.invoke([instruccion] + mensajes)
        if res.tool_calls:
            notificar("SEC", "Herramienta", res.tool_calls[0]['name'])
            return {"messages": [res]}
        mensajes.extend([res, HumanMessage(content="Usa escribir_archivo ahora.")])
    return {"messages": [arq_llm.bind_tools(herramientas).invoke([instruccion] + state['messages'])]}

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
                            if "herramientas" in salida: print(f"  [SO]: {salida['herramientas']['messages'][-1].content}")
                        notificar("ARQ", "Tarea finalizada", "Listo para la siguiente orden")
        except: time.sleep(3)
