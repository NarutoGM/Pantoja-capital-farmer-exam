from flask import Flask, render_template, request, jsonify
import sqlite3
import google.generativeai as genai

import datetime
import uuid
import os

import re 
app = Flask(__name__)

API_KEY_GEMINI = "AIzaSyC_tGpAVfd_PWLGQ9wQ8laUAs4bMWj11IE" 


genai.configure(api_key=API_KEY_GEMINI)
# Conexión y creación de la base de datos si no existe
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cotizaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT,
            nombre TEXT,
            email TEXT,
            tipo_servicio TEXT,
            precio INTEGER,
            fecha TEXT,
            descripcion TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Asignar precio según servicio
def calcular_precio(tipo):
    precios = {
        "Constitución de empresa": 1500,
        "Defensa laboral": 2000,
        "Consultoría tributaria": 800
    }
    return precios.get(tipo, 0)

# Generar número único de cotización
def generar_numero():
    codigo = str(uuid.uuid4())[:4].upper()
    return f"COT-2025-{codigo}"


def analizar_con_ia(descripcion, tipo_servicio):
    prompt = f"""
    Eres un asistente legal inteligente. Analiza el siguiente caso y responde en un formato estructurado:

    **Caso**:
    - Tipo de servicio: {tipo_servicio}
    - Descripción: {descripcion}

    **Respuesta** (usa este formato exacto, con secciones delimitadas por ###):
    ### Nivel de Complejidad
    [Baja|Media|Alta]

    ### Ajuste de Precio Recomendado
    [0%|25%|50%] (Justificación: [explicación breve])

    ### Servicios Adicionales
    - [Servicio adicional 1]
    - [Servicio adicional 2]
    - [Servicio adicional 3]
    ...

    ### Propuesta Profesional
    [Propuesta en 2-3 párrafos]
    """

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        texto = response.text

        # Depuración: Imprimir la respuesta cruda
        print("Respuesta cruda de la IA:")
        print(texto)

        # Extraer nivel de complejidad
        complejidad_match = re.search(r'###\s*Nivel\s*de\s*Complejidad\s*\n\s*(Baja|Media|Alta)\s*\n', texto, re.IGNORECASE)
        complejidad = complejidad_match.group(1) if complejidad_match else "No definida"

        # Extraer ajuste de precio
        ajuste_match = re.search(r'###\s*Ajuste\s*de\s*Precio\s*Recomendado\s*\n\s*(\d+%)\s*(?:\(Justificación:[^\)]*\))?\s*\n', texto, re.IGNORECASE)
        ajuste_precio = int(ajuste_match.group(1).replace('%', '')) if ajuste_match else 0

        # Extraer servicios adicionales
        servicios = []
        servicios_section_match = re.search(
            r'###\s*Servicios\s*Adicionales\s*\n((?:-\s*[^\n]+\n)+)\s*###', 
            texto, 
            re.DOTALL | re.IGNORECASE
        )
        if servicios_section_match:
            servicios_block = servicios_section_match.group(1)
            servicios = [line.strip('- ').strip() for line in servicios_block.split('\n') if line.strip().startswith('-')]
        
        # Si no se encuentran servicios, usar fallback
        if not servicios:
            servicios = re.findall(r'-\s*([^\n]+)', texto)
            # Filtrar cualquier elemento que parezca pertenecer a la propuesta profesional
            servicios = [s for s in servicios if not re.search(r'(Estimado|propuesta|servicio integral|gestión completa)', s, re.IGNORECASE)]
        
        # Si no hay servicios válidos, asignar ["Ninguno"]
        servicios = servicios if servicios else ["Ninguno"]

        # Extraer propuesta profesional
        propuesta_match = re.search(
            r'###\s*Propuesta\s*Profesional\s*\n((?:.*?\n)+?)(?=\n\s*###|$)', 
            texto, 
            re.DOTALL | re.IGNORECASE
        )
        propuesta_texto = propuesta_match.group(1).strip() if propuesta_match else texto.strip()

        # Depuración: Imprimir valores extraídos
        print("Valores extraídos:")
        print(f"Complejidad: {complejidad}")
        print(f"Ajuste de precio: {ajuste_precio}%")
        print(f"Servicios adicionales: {servicios}")
        print(f"Propuesta: {propuesta_texto[:100]}...")  # Solo los primeros 100 caracteres para no saturar la consola

        return {
            "complejidad": complejidad,
            "ajuste_precio": ajuste_precio,
            "servicios_adicionales": servicios,
            "propuesta_texto": propuesta_texto,
            "error": None
        }

    except Exception as e:
        print(f"Error en analizar_con_ia: {str(e)}")
        return {
            "error": str(e),
            "complejidad": "Error al analizar",
            "ajuste_precio": 0,
            "servicios_adicionales": ["Ninguno"],
            "propuesta_texto": "No se pudo generar la propuesta debido a un error."
        }


@app.route('/')
def index():
    return render_template('form.html')

@app.route('/cotizar', methods=['POST'])
@app.route('/cotizar', methods=['POST'])
def cotizar():
    nombre = request.form['nombre']
    email = request.form['email']
    tipo = request.form['tipo']
    descripcion = request.form['descripcion']

    numero = generar_numero()
    precio_base = calcular_precio(tipo)
    fecha = datetime.date.today().isoformat()

    analisis = analizar_con_ia(descripcion, tipo)

    ajuste_porcentaje = analisis.get('ajuste_precio', 0)
    precio_final = int(precio_base * (1 + ajuste_porcentaje / 100))

    conn = None
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cotizaciones (numero, nombre, email, tipo_servicio, precio, fecha, descripcion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (numero, nombre, email, tipo, precio_final, fecha, descripcion))
        conn.commit()
    except sqlite3.Error as sql_e:
        print(f"Error de base de datos: {sql_e}")
    finally:
        if conn:
            conn.close()

    return jsonify({
        "numero": numero,
        "nombre": nombre,
        "email": email,
        "tipo_servicio": tipo,
        "precio_base": precio_base,
        "ajuste": f"{ajuste_porcentaje}%",
        "precio_final": precio_final,
        "fecha": fecha,
        "descripcion": descripcion,
        "complejidad": analisis.get('complejidad', 'No definida'),
        "servicios_adicionales": analisis.get('servicios_adicionales', []),
        "propuesta": analisis.get('propuesta_texto', 'No disponible'),
        "error_ia": analisis.get('error')
    })


if __name__ == '__main__':
    init_db()
    app.run(debug=True)     



