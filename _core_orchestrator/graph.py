import sys
import os
import operator
from typing import TypedDict, Annotated, Sequence

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from main import obtener_arquitecto, obtener_desarrollador
from tools import leer_archivo, escribir_archivo, listar_directorio
from middleware import TokenMiddleware

class EstadoOficina(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

print("--- Inicializando Nodos de la Oficina ---")
arquitecto_llm = obtener_arquitecto()
desarrollador_llm = obtener_desarrollador()
middleware = TokenMiddleware()

herramientas = [leer_archivo, escribir_archivo, listar_directorio]
desarrollador_con_herramientas = desarrollador_llm.bind_tools(herramientas)
nodo_herramientas = ToolNode(herramientas)

def nodo_arquitecto(state: EstadoOficina):
    print("\n[Arquitecto]: Diseñando arquitectura y delegando...")
    instruccion = SystemMessage(
        content="Eres el Arquitecto Líder. Delega las instrucciones a Claude, tu desarrollador. Ordena explícitamente usar 'escribir_archivo'."
    )
    respuesta = arquitecto_llm.invoke([instruccion] + state['messages'])
    return {"messages": [respuesta]}

def nodo_desarrollador(state: EstadoOficina):
    print("\n[Desarrollador - Claude]: Recibiendo planos. Ejecutando código y operando herramientas...")
    instruccion = SystemMessage(
        content="Eres Claude, el Desarrollador. Tienes prohibido responder con texto plano. DEBES invocar la herramienta 'escribir_archivo' para cumplir la tarea."
    )
    
    max_reintentos = 3
    mensajes_actuales = list(state['messages'])
    
    for intento in range(max_reintentos):
        try:
            respuesta = desarrollador_con_herramientas.invoke([instruccion] + mensajes_actuales)
            
            if not respuesta.tool_calls:
                print(f"  [ALERTA] Claude respondió con texto.")
                print(f"  -> Forzando uso de herramienta (Intento {intento + 1}/{max_reintentos})...")
                mensajes_actuales.extend([respuesta, HumanMessage(content="Obligatorio: Ejecuta la función escribir_archivo en disco. No des explicaciones.")])
                continue
            
            print(f"  -> ¡Éxito! Claude activó herramienta en disco: {respuesta.tool_calls[0]['name']}")
            print(f"  -> Argumentos enviados: {respuesta.tool_calls[0]['args']}")
            return {"messages": [respuesta]}
            
        except Exception as e:
            if middleware.manejar_error_api(str(e)):
                continue
            print(f"  [FALLO] OpenRouter devolvió un error incompatible: {e}")
            break
            
    print("  [CRÍTICO] Claude no puede accionar herramientas. El Arquitecto (Gemini) tomará el control del teclado...")
    arq_con_herramientas = arquitecto_llm.bind_tools(herramientas)
    
    mensajes_rescate = list(state['messages']) + [
        HumanMessage(content="SISTEMA: Claude ha fallado. Como Arquitecto, asume el control de emergencia AHORA e invoca la herramienta 'escribir_archivo' para completar la orden original.")
    ]
    
    respuesta_rescate = arq_con_herramientas.invoke([instruccion] + mensajes_rescate)
    
    if respuesta_rescate.tool_calls:
        print(f"  -> Arquitecto activando herramienta: {respuesta_rescate.tool_calls[0]['name']}")
        print(f"  -> Argumentos enviados: {respuesta_rescate.tool_calls[0]['args']}")
    else:
        print("  [ERROR] El Arquitecto tampoco invocó la herramienta.")
        
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
    print("\n--- Ejecutando Prueba Definitiva del Motor LangGraph ---")
    
    # Inyectamos la ruta absoluta para evitar que Windows se confunda
    ruta_exacta = os.path.join(os.getcwd(), 'prueba_oficina.txt').replace('\\', '/')
    inputs = {"messages": [HumanMessage(content=f"Crea un archivo de texto en la ruta exacta '{ruta_exacta}' que diga 'El motor está vivo'.")]}
    
    for salida in oficina_app.stream(inputs):
        for nodo, datos in salida.items():
            if nodo == "herramientas":
                resultado_tool = datos['messages'][-1].content
                print(f"\n[Sistema Operativo]: {resultado_tool}")
    
    print("\n¡Grafo completado con éxito!")
