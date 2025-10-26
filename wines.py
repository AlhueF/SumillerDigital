import pdfplumber
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=api_key)

menu_pdf = 'El Tribut - Fichas platos para Sala.pdf'

texto_extraido = ''
with pdfplumber.open(menu_pdf) as pdf:
    for pagina in pdf.pages:
        texto_extraido += pagina.extract_text() + '\n'

import json
import re
from pprint import pprint
from resources import *

if 'texto_extraido' not in globals():
    raise ValueError('La variable texto_extraido no está definida. Ejecuta la celda que extrae el PDF primero.')

prompt = f"""
Eres un asistente que convierte texto de menú en JSON estructurado.
Recibirás a continuación un bloque de texto (en español/ING/otros) que contiene múltiples entradas de platos.
Devuelve únicamente un JSON (sin texto adicional) con un array de objetos. Cada objeto debe tener EXACTAMENTE estas claves:
- nombre_plato (string)
- categoria (string)  # p.ej. Entrante, Principal, Postre
- ingredientes_clave (array de strings)  # 3-6 ingredientes o componentes clave
- carne ("Sí" o "No")
- proteina_principal (string)  # p.ej. Pescado, Ternera, Lácteo, Marisco, N/A
- salsa (string)  # breve descripción o "N/A"
- coccion (string)  # p.ej. Frito, Horneado, Crudo / Marinado, etc.
- alergenos (array de strings)

Normaliza los nombres en español cuando sea posible. No incluyas explicaciones ni texto fuera del JSON.
Texto a procesar:


{texto_extraido}

"""
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    response = model.generate_content(prompt)
    raw = response.text
except Exception as e:
    print('Error en la llamada a Gemini:', e)
    raw = None

menu_data = None
if raw:
    # intentar parsear directamente
    try:
        menu_data = json.loads(raw)
    except Exception:
        # intentar extraer primer bloque JSON del texto
        m = re.search(r"(\[\s*\{[\s\S]*\}\s*\])", raw)
        if m:
            try:
                menu_data = json.loads(m.group(1))
            except Exception as e:
                print('Error parseando el bloque JSON extraído:', e)
        else:
            print('No se encontró un JSON evidente en la respuesta de Gemini. Mostrando salida cruda:')
            print(raw[:2000])
if menu_data:
    print(f'✅ JSON parseado correctamente. Platos extraídos: {len(menu_data)}')
    pprint(menu_data[:3])
    
    # Guardar cada plato en MongoDB
    for plato in menu_data:
        id_guardado = guardar_plato_en_mongodb(plato)
        if id_guardado:
            print(f"✅ Plato '{plato['nombre_plato']}' guardado con ID: {id_guardado}")
    
    # Guardar en variable global para usar en otras celdas
    globals()['menu_data'] = menu_data
else:
    print('❌ No se pudo generar menu_data. Revisa la salida anterior.')

