import sys, os, operator, json, time, re
from typing import TypedDict, Annotated, Sequence
from websockets.sync.client import connect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
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
    mensajes = [SystemMessage(content=f"{prompt} Ruta base: {ruta}")] + state['messages']
    
    # Sistema de tolerancia a fallos para evadir bloqueos de la API (429/502)
    for intento in range(4):
        try:
            res = llm.invoke(mensajes)
            notificar(rol, "Terminado", "Avanzando")
            time.sleep(1.5) # Pausa preventiva para no saturar la red
            return {"messages": [res]}
        except Exception as e:
            print(f"  [Advertencia] {rol} bloqueado en red. Reintentando ({intento+1}/4)...")
            notificar(rol, "Reintentando", "Esquivando bloqueo de red")
            time.sleep(4) # Esperar a que la API se enfríe
            
    # Fallback si todo falla
    notificar(rol, "Fallo", "Saltando por error de API")
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
    return "UI" # Flujo completo por defecto

def nodo_ui(state): return procesar_agente("UI", state, dev_llm, "Eres Diseñador UI/UX. Define el diseño web en texto.")
def nodo_dev(state): return procesar_agente("DEV", state, dev_llm, "Eres Desarrollador. OBLIGATORIO: Escribe todo el codigo fuente dentro de bloques de triple comilla invertida, ejemplo: ```html ...codigo... ```")
def nodo_qa(state): return procesar_agente("QA", state, dev_llm, "Eres QA. Aprueba el codigo brevemente, no lo reescribas.")

def nodo_sec(state):
    print("\n[SEC]: Verificando y guardando...")
    notificar("SEC", "Auditoria", "Extrayendo codigo puro")
    
    res = AIMessage(content="Fallback", tool_calls=[])
    for intento in range(3):
        try:
            res = sec_con_herramientas.invoke([SystemMessage(content="Usa escribir_archivo.")] + state['messages'])
            break
        except Exception:
            notificar("SEC", "Pausa", "Reintentando conexion")
            time.sleep(3)
    
    if not hasattr(res, 'tool_calls') or not res.tool_calls:
        print("  [Hack] Limpiando conversacion y extrayendo codigo puro...")
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
        
        if not codigo_final:
            codigo_final = state['messages'][-1].content
            
        res = AIMessage(
            content="Guardado exitoso.",
            tool_calls=[{"name": "escribir_archivo", "args": {"ruta": ruta_final, "contenido": codigo_final}, "id": "hack_02"}]
        )
        notificar("SEC", "Herramienta", "Codigo extraido")
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
                                print(f"  [SO]: {salida['herramientas']['messages'][-1].content}")
                        notificar("ARQ", "Tarea finalizada", "Listo")
        except Exception as e:
            time.sleep(3)
