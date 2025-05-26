from flask import Flask, render_template, request, jsonify
import sqlite3
import datetime
import uuid
import os

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('form.html')

@app.route('/cotizar', methods=['POST'])
def cotizar():
    nombre = request.form['nombre']
    email = request.form['email']
    tipo = request.form['tipo']
    descripcion = request.form['descripcion']

    numero = generar_numero()
    precio = calcular_precio(tipo)
    fecha = datetime.date.today().isoformat()

    # Guardar en la BD
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cotizaciones (numero, nombre, email, tipo_servicio, precio, fecha, descripcion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (numero, nombre, email, tipo, precio, fecha, descripcion))
    conn.commit()
    conn.close()

    return jsonify({
        "numero": numero,
        "nombre": nombre,
        "email": email,
        "tipo_servicio": tipo,
        "precio": precio,
        "fecha": fecha,
        "descripcion": descripcion
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
