import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
print('--- Diagnosticando API Key de Google ---')
if not api_key:
    print('Error: GEMINI_API_KEY no se encontró en el archivo .env')
else:
    try:
        genai.configure(api_key=api_key)
        print('Modelos disponibles para tu API Key:')
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if modelos:
            for nombre in modelos:
                print(f' - {nombre}')
        else:
            print(' No se encontraron modelos para esta clave.')
    except Exception as e:
        print(f'Error de conexión: {e}')
