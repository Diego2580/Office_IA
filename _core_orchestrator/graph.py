import sys
import os
import operator
import json
import time
from typing import TypedDict, Annotated, Sequence
from websockets.sync.client import connect

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from main import obtener_arquitecto, obtener_desarrollador
from tools import leer_archivo, escribir_archivo, listar_directorio
from middleware import TokenMiddleware

class EstadoOficina(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

arquitecto_llm = obtener_arquitecto()
desarrollador_llm = obtener_desarrollador()
middleware = TokenMiddleware()

herramientas = [leer_archivo, escribir_archivo, listar_directorio]
desarrollador_con_herramientas = desarrollador_llm.bind_tools(herramientas)
nodo_herramientas = ToolNode(herramientas)

def notificar_ui(agente: str, accion: str, estado: str):
    try:
        with connect("ws://127.0.0.1:8000/ws/oficina") as ws:
            ws.send(json.dumps({"agente": agente, "accion": accion, "estado": estado}))
        time.sleep(0.6)
    except:
        pass

def nodo_arquitecto(state: EstadoOficina):
    print("\n[Arquitecto]: Diseñando arquitectura y delegando...")
    notificar_ui("Orquestador", "Diseñando arquitectura", "Estructurando tareas")
    instruccion = SystemMessage(
        content="Eres el Arquitecto Líder. Delega las instrucciones a Claude. Usa herramientas si es necesario."
    )
    respuesta = arquitecto_llm.invoke([instruccion] + state['messages'])
    notificar_ui("Orquestador", "Plan entregado", "Delegando a Claude")
    return {"messages": [respuesta]}

def nodo_desarrollador(state: EstadoOficina):
    print("\n[Desarrollador - Claude]: Ejecutando...")
    notificar_ui("Desarrollador", "Recibiendo planos", "Escribiendo solución")
    instruccion = SystemMessage(content="Eres Claude. Invocas herramientas locales para cumplir la tarea.")
    
    mensajes_actuales = list(state['messages'])
    for intento in range(3):
        try:
            respuesta = desarrollador_con_herramientas.invoke([instruccion] + mensajes_actuales)
            if not respuesta.tool_calls:
                notificar_ui("Desarrollador", f"Reintento {intento+1}", "Esperando función")
                mensajes_actuales.extend([respuesta, HumanMessage(content="Obligatorio: Usa una función en disco.")])
                continue
            notificar_ui("Desarrollador", "Herramienta activada", respuesta.tool_calls[0]['name'])
            return {"messages": [respuesta]}
        except Exception as e:
            if middleware.manejar_error_api(str(e)):
                notificar_ui("Desarrollador", "Pausa", "Enfriamiento de cuota")
                continue
            break
            
    print("  [CRÍTICO] Fallo. Arquitecto toma control...")
    notificar_ui("Orquestador", "Failover", "Tomando teclado")
    arq_con_herramientas = arquitecto_llm.bind_tools(herramientas)
    respuesta_rescate = arq_con_herramientas.invoke([instruccion] + list(state['messages']) + [HumanMessage(content="SISTEMA: Asume el control.")])
    return {"messages": [respuesta_rescate]}

flujo = StateGraph(EstadoOficina)
flujo.add_node("arquitecto", nodo_arquitecto)
flujo.add_node("desarrollador", nodo_desarrollador)
flujo.add_node("herramientas", nodo_herramientas)
flujo.add_edge(START, "arquitecto")
flujo.add_edge("arquitecto", "desarrollador")
flujo.add_conditional_edges("desarrollador", tools_condition, {"tools": "herramientas", END: END})
flujo.add_edge("herramientas", END)
oficina_app = flujo.compile()

if __name__ == '__main__':
    print("\n" + "="*50)
    print(" 🚀 AI OFFICE ENGINE - MODO ESCUCHA WEB")
    print("="*50)
    
    while True:
        try:
            with connect("ws://127.0.0.1:8000/ws/oficina") as ws_listener:
                notificar_ui("Orquestador", "Sistema en línea", "Esperando órdenes de la Web")
                print("  -> Conectado. Esperando tu orden desde el navegador en localhost:8030...")
                
                while True:
                    mensaje = ws_listener.recv()
                    datos = json.loads(mensaje)
                    
                    if datos.get("origen") == "usuario":
                        prompt = datos.get("texto")
                        print(f"\n[Orden recibida de la UI]: {prompt}")
                        notificar_ui("Orquestador", "Orden recibida", "Iniciando análisis")
                        
                        inputs = {"messages": [HumanMessage(content=prompt)]}
                        for salida in oficina_app.stream(inputs):
                            for nodo, datos_salida in salida.items():
                                if nodo == "herramientas":
                                    print(f"\n[Sistema Operativo]: {datos_salida['messages'][-1].content}")
                                    notificar_ui("Orquestador", "Disco local", "Completado")
                        print("\n[OK] Tarea completada. Esperando nueva orden...")
        except Exception as e:
            print(f"  [Desconectado] Reconectando en 3s... ({e})")
            time.sleep(3)
