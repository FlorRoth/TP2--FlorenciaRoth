import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import date, datetime
from functools import wraps

from flask import (
    Flask,
    flash,
     jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
DB_PATH = os.path.join(BASE_DIR, "clinica.db")
ENV_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", ".env"))

# variables archivo .env 
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as archivo_env:
        for linea in archivo_env:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))

app = Flask(
    __name__,
    template_folder=FRONTEND_DIR,
    static_folder=FRONTEND_DIR,
    static_url_path="/static",
)
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_tp2_florencia_roth_2026")
CORS(app)

# Especialidades médicas y profesionales disponibles
ESPECIALIDADES = {
    "Clínica Médica": {
        "profesional": "Dra. Valeria Méndez",
        "descripcion": "Chequeos generales, fiebre, cansancio, síntomas respiratorios leves y orientación integral.",
        "horarios": ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
    },
    "Cardiología": {
        "profesional": "Dr. Martín Echeverría",
        "descripcion": "Control de presión arterial, palpitaciones, dolor en el pecho, aptos físicos y electrocardiogramas.",
        "horarios": ["09:30", "10:30", "11:30", "15:00", "16:30"],
    },
    "Dermatología": {
        "profesional": "Dra. Lucía Pereyra",
        "descripcion": "Control de lunares, manchas, alergias cutáneas, acné, dermatitis y caída del cabello.",
        "horarios": ["10:00", "11:00", "12:00", "14:30", "15:30"],
    },
    "Traumatología": {
        "profesional": "Dr. Santiago Gómez",
        "descripcion": "Dolores articulares, musculares, esguinces, lesiones deportivas, dolores de espalda y rehabilitación.",
        "horarios": ["09:00", "10:30", "12:00", "16:00", "17:00"],
    },
    "Gastroenterología": {
        "profesional": "Dra. Carolina Ruiz",
        "descripcion": "Acidez, dolor abdominal, digestión lenta, gastritis, intolerancias alimentarias y controles digestivos.",
        "horarios": ["09:00", "10:00", "11:30", "14:00", "15:30"],
    },
    "Oftalmología": {
        "profesional": "Dr. Nicolás Cabrera",
        "descripcion": "Control de agudeza visual, vista cansada, enrojecimiento ocular, recetado de lentes y fondo de ojo.",
        "horarios": ["09:30", "11:00", "14:30", "16:00", "17:00"],
    },
}


#  SQLITE
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    #  Usuarios
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            dni TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    #  Turnos médicos
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            especialidad TEXT NOT NULL,
            profesional TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            motivo TEXT NOT NULL,
            prioridad_ia TEXT DEFAULT 'Normal',
            recomendacion_ia TEXT DEFAULT '',
            estado TEXT DEFAULT 'Confirmado',
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """
    )

    # Tabla de consultas realizadas al Asistente de IA
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consultas_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            sintomas TEXT NOT NULL,
            especialidad_sugerida TEXT NOT NULL,
            prioridad TEXT NOT NULL,
            recomendacion TEXT NOT NULL,
            motor_ia TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """
    )

    conn.commit()
    conn.close()


init_db()


#  INTELIGENCIA ARTIFICIAL (GOOGLE GEMINI)

def consultar_servicio_ia(sintomas_texto: str) -> dict:
    """Consulta la API de Google Gemini para orientar al paciente según sus síntomas"""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    nombres_especialidades = list(ESPECIALIDADES.keys())

    prompt = (
        "Sos exclusivamente un clasificador de síntomas médicos para asignar turnos en una clínica de Argentina. "
        "PROHIBIDO actuar como un chat general o responder preguntas ajenas a la salud. "
        f"Especialidades disponibles: {', '.join(nombres_especialidades)}. "
        f"Texto ingresado por el usuario: '{sintomas_texto}'. "
        "Primero evaluá si el texto describe síntomas médicos, malestares físicos o un estudio/control de salud. "
        "Si el texto NO trata sobre síntomas médicos ni controles de salud (por ejemplo: saludos, preguntas generales, "
        "chistes, programación, cocina, deportes o cualquier otro tema), poné 'es_sintoma_medico' en false. "
        "Respondé ÚNICAMENTE con un objeto JSON válido con las claves exactas: "
        "'es_sintoma_medico' (boolean true o false), "
        "'especialidad' (una de las especialidades disponibles, o vacío si es_sintoma_medico es false), "
        "'prioridad' ('Baja - Control General', 'Media - Programada' o 'Alta - Prioritaria') "
        "y 'recomendacion' (un consejo médico breve para los síntomas de máximo 2 oraciones, o vacío si es_sintoma_medico es false)."
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.1-flash-lite:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            texto_respuesta = (
                data["candidates"][0]["content"]["parts"][0]["text"].strip()
            )
            resultado = json.loads(texto_respuesta)

            if not resultado.get("es_sintoma_medico", True):
                return {
                    "es_valido": False,
                    "error": "Este asistente solo analiza síntomas o consultas médicas. Por favor describí qué malestar o control de salud necesitás.",
                }

            esp = resultado.get("especialidad", "Clínica Médica")
            if esp not in ESPECIALIDADES:
                esp = "Clínica Médica"
            return {
                "es_valido": True,
                "especialidad": esp,
                "profesional": ESPECIALIDADES[esp]["profesional"],
                "prioridad": resultado.get("prioridad", "Media - Programada"),
                "recomendacion": resultado.get(
                    "recomendacion",
                    "Te recomendamos asistir a la consulta con tus estudios previos.",
                ),
                "motor": "Google Gemini AI (gemini-3.1-flash-lite)",
            }
    except Exception:
        return {
            "es_valido": True,
            "especialidad": "Clínica Médica",
            "profesional": ESPECIALIDADES["Clínica Médica"]["profesional"],
            "prioridad": "Media - Programada",
            "recomendacion": "No se pudo conectar con Gemini en este momento. Te sugerimos una consulta inicial en Clínica Médica.",
            "motor": "Gemini AI (sin conexión)",
        }


# SESIÓN
def login_requerido(f):
    @wraps(f)
    def decorada(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Debés iniciar sesión para acceder a esa sección.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorada


@app.context_processor
def inyectar_contexto():
    usuario = None
    if "usuario_id" in session:
        usuario = {
            "id": session.get("usuario_id"),
            "nombre": session.get("usuario_nombre"),
            "email": session.get("usuario_email"),
        }
    return {
        "usuario_actual": usuario,
        "especialidades_catalogo": ESPECIALIDADES,
        "fecha_hoy": date.today().isoformat(),
    }


# VALIDACIONES
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
DNI_REGEX = re.compile(r"^\d{7,8}$")


def validar_registro_servidor(nombre, dni, email, password, password2):
    errores = {}
    if not nombre or len(nombre.strip()) < 3:
        errores["nombre"] = "El nombre y apellido debe tener al menos 3 caracteres."
    if not dni or not DNI_REGEX.match(dni.strip()):
        errores["dni"] = "El DNI debe contener entre 7 y 8 números sin puntos."
    if not email or not EMAIL_REGEX.match(email.strip()):
        errores["email"] = "Ingresá un correo electrónico con formato válido."
    if not password or len(password) < 6:
        errores["password"] = "La contraseña debe tener al menos 6 caracteres."
    if password != password2:
        errores["password2"] = "Las contraseñas ingresadas no coinciden."
    return errores


def validar_turno_servidor(especialidad, fecha_str, hora):
    errores = {}
    if especialidad not in ESPECIALIDADES:
        errores["especialidad"] = "Seleccioná una especialidad médica válida."
    else:
        horarios_validos = ESPECIALIDADES[especialidad]["horarios"]
        if hora not in horarios_validos:
            errores["hora"] = "Seleccioná un horario disponible para esta especialidad."

    if not fecha_str:
        errores["fecha"] = "La fecha del turno es obligatoria."
    else:
        try:
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            if fecha_obj < date.today():
                errores["fecha"] = "No se pueden reservar turnos en fechas pasadas."
        except ValueError:
            errores["fecha"] = "El formato de la fecha no es válido."

    return errores


# Inicio y catálogo de especialidades
@app.route("/")
def index():
    conn = get_db_connection()
    total_turnos = conn.execute("SELECT COUNT(*) AS total FROM turnos WHERE estado = 'Confirmado'").fetchone()["total"]
    total_consultas_ia = conn.execute("SELECT COUNT(*) AS total FROM consultas_ia").fetchone()["total"]
    conn.close()

    return render_template("index.html", total_turnos=total_turnos, total_consultas_ia=total_consultas_ia)


# Registro de usuarios 
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if "usuario_id" in session:
        return redirect(url_for("turnos"))

    errores = {}
    valores = {"nombre": "", "dni": "", "email": ""}

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        dni = request.form.get("dni", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        valores = {"nombre": nombre, "dni": dni, "email": email}
        errores = validar_registro_servidor(nombre, dni, email, password, password2)

        if not errores:
            conn = get_db_connection()
            existente = conn.execute(
                "SELECT id, email, dni FROM usuarios WHERE email = ? OR dni = ?",
                (email, dni),
            ).fetchone()

            if existente:
                if existente["email"] == email:
                    errores["email"] = "Ya existe una cuenta registrada con este correo."
                if existente["dni"] == dni:
                    errores["dni"] = "Ya existe un paciente registrado con este DNI."
                conn.close()
            else:
                password_hash = generate_password_hash(password)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO usuarios (nombre, dni, email, password_hash) VALUES (?, ?, ?, ?)",
                    (nombre, dni, email, password_hash),
                )
                conn.commit()
                nuevo_id = cursor.lastrowid
                conn.close()

                session["usuario_id"] = nuevo_id
                session["usuario_nombre"] = nombre
                session["usuario_email"] = email
                flash(f"¡Bienvenida/o, {nombre}! Tu cuenta fue creada con éxito.", "exito")
                return redirect(url_for("turnos"))

    return render_template("registro.html", errores=errores, valores=valores)


# Inicio de sesión
@app.route("/login", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("turnos"))

    errores = {}
    email_ingresado = ""

    if request.method == "POST":
        email_ingresado = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email_ingresado or not EMAIL_REGEX.match(email_ingresado):
            errores["email"] = "Ingresá un correo electrónico válido."
        if not password:
            errores["password"] = "Ingresá tu contraseña."

        if not errores:
            conn = get_db_connection()
            usuario = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email_ingresado,)).fetchone()
            conn.close()

            if usuario and check_password_hash(usuario["password_hash"], password):
                session["usuario_id"] = usuario["id"]
                session["usuario_nombre"] = usuario["nombre"]
                session["usuario_email"] = usuario["email"]
                flash(f"¡Hola, {usuario['nombre']}!", "exito")
                return redirect(url_for("turnos"))
            else:
                errores["general"] = "El correo electrónico o la contraseña son incorrectos."

    return render_template("login.html", errores=errores, email=email_ingresado)

# Cierre de sesión
@app.route("/logout")
def logout():
    session.clear()
    flash("Cerraste sesión correctamente.", "exito")
    return redirect(url_for("index"))


# Gestión de Turnos 
@app.route("/turnos", methods=["GET", "POST"])
@login_requerido
def turnos():
    errores = {}
    esp_param = request.args.get("especialidad", "")
    motivo_param = request.args.get("motivo", "")

    valores = {
        "especialidad": esp_param if esp_param in ESPECIALIDADES else "",
        "fecha": "",
        "hora": "",
        "motivo": motivo_param,
    }

    if request.method == "POST":
        especialidad = request.form.get("especialidad", "").strip()
        fecha_str = request.form.get("fecha", "").strip()
        hora = request.form.get("hora", "").strip()
        motivo = request.form.get("motivo", "").strip()

        valores = {"especialidad": especialidad, "fecha": fecha_str, "hora": hora, "motivo": motivo}
        errores = validar_turno_servidor(especialidad, fecha_str, hora)

        if not errores:
            conn = get_db_connection()
            ocupado = conn.execute(
                "SELECT id FROM turnos WHERE especialidad = ? AND fecha = ? AND hora = ? AND estado = 'Confirmado'",
                (especialidad, fecha_str, hora),
            ).fetchone()

            if ocupado:
                errores["hora"] = f"El horario de las {hora} hs ya está reservado en esa fecha."
                conn.close()
            else:
                profesional = ESPECIALIDADES[especialidad]["profesional"]
                if len(motivo) >= 10:
                    analisis_ia = consultar_servicio_ia(motivo)
                    if analisis_ia.get("es_valido"):
                        prioridad_ia = analisis_ia["prioridad"]
                        recomendacion_ia = analisis_ia["recomendacion"]
                    else:
                        prioridad_ia = "Normal"
                        recomendacion_ia = "Sin orientación previa de IA."
                else:
                    motivo = motivo if motivo else "Consulta general"
                    prioridad_ia = "Normal"
                    recomendacion_ia = "Sin orientación previa de IA."

                conn.execute(
                    """
                    INSERT INTO turnos (usuario_id, especialidad, profesional, fecha, hora, motivo, prioridad_ia, recomendacion_ia, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Confirmado')
                    """,
                    (
                        session["usuario_id"],
                        especialidad,
                        profesional,
                        fecha_str,
                        hora,
                        motivo,
                        prioridad_ia,
                        recomendacion_ia,
                    ),
                )
                conn.commit()
                conn.close()

                flash(f"¡Turno confirmado para {especialidad} con {profesional} el {fecha_str} a las {hora} hs!", "exito")
                return redirect(url_for("turnos"))

    filtro_estado = request.args.get("estado", "todos")
    conn = get_db_connection()
    if filtro_estado in ("Confirmado", "Cancelado"):
        mis_turnos = conn.execute(
            "SELECT * FROM turnos WHERE usuario_id = ? AND estado = ? ORDER BY fecha ASC, hora ASC",
            (session["usuario_id"], filtro_estado),
        ).fetchall()
    else:
        mis_turnos = conn.execute(
            "SELECT * FROM turnos WHERE usuario_id = ? ORDER BY fecha ASC, hora ASC",
            (session["usuario_id"],),
        ).fetchall()
    conn.close()

    return render_template("turnos.html", turnos=mis_turnos, errores=errores, valores=valores, filtro_estado=filtro_estado)


@app.route("/turnos/cancelar/<int:turno_id>", methods=["POST"])
@login_requerido
def cancelar_turno(turno_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE turnos SET estado = 'Cancelado' WHERE id = ? AND usuario_id = ?",
        (turno_id, session["usuario_id"]),
    )
    conn.commit()
    conn.close()

    flash("El turno fue cancelado correctamente.", "exito")
    return redirect(url_for("turnos"))


# Orientación Médica con IA 
@app.route("/asistente-ia", methods=["GET", "POST"])
def asistente_ia():
    errores = {}
    resultado_ia = None
    sintomas_ingresados = ""

    if request.method == "POST":
        sintomas_ingresados = request.form.get("sintomas", "").strip()
        if not sintomas_ingresados or len(sintomas_ingresados) < 10:
            errores["sintomas"] = (
                "Por favor describí tus síntomas o consulta con al menos 10 caracteres "
                "para que la IA pueda orientarte adecuadamente."
            )
        else:
            analisis = consultar_servicio_ia(sintomas_ingresados)
            if not analisis.get("es_valido"):
                errores["sintomas"] = analisis["error"]
            else:
                resultado_ia = analisis
                conn = get_db_connection()
                conn.execute(
                    """
                    INSERT INTO consultas_ia (usuario_id, sintomas, especialidad_sugerida, prioridad, recomendacion, motor_ia)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session.get("usuario_id"),
                        sintomas_ingresados,
                        resultado_ia["especialidad"],
                        resultado_ia["prioridad"],
                        resultado_ia["recomendacion"],
                        resultado_ia["motor"],
                    ),
                )
                conn.commit()
                conn.close()

    return render_template("asistente_ia.html", errores=errores, resultado_ia=resultado_ia, sintomas=sintomas_ingresados)


# API JSON
@app.route("/api/orientacion-ia", methods=["POST"])
def api_orientacion_ia():
    datos = request.get_json(silent=True) or {}
    sintomas = datos.get("sintomas", "").strip()

    if len(sintomas) < 10:
        return jsonify({"ok": False, "error": "Describí los síntomas con al menos 10 caracteres."}), 400

    resultado = consultar_servicio_ia(sintomas)
    if not resultado.get("es_valido"):
        return jsonify({"ok": False, "error": resultado["error"]}), 400

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO consultas_ia (usuario_id, sintomas, especialidad_sugerida, prioridad, recomendacion, motor_ia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session.get("usuario_id"),
            sintomas,
            resultado["especialidad"],
            resultado["prioridad"],
            resultado["recomendacion"],
            resultado["motor"],
        ),
    )
    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "especialidad": resultado["especialidad"],
        "profesional": resultado["profesional"],
        "prioridad": resultado["prioridad"],
        "recomendacion": resultado["recomendacion"],
        "motor": resultado["motor"],
        "horarios": ESPECIALIDADES[resultado["especialidad"]]["horarios"],
    })


@app.route("/api/horarios/<especialidad>", methods=["GET"])
def api_horarios(especialidad):
    fecha_str = request.args.get("fecha", "").strip()
    if especialidad not in ESPECIALIDADES:
        return jsonify({"ok": False, "error": "Especialidad no encontrada"}), 404

    horarios_totales = ESPECIALIDADES[especialidad]["horarios"]
    ocupados = []

    if fecha_str:
        conn = get_db_connection()
        filas = conn.execute(
            "SELECT hora FROM turnos WHERE especialidad = ? AND fecha = ? AND estado = 'Confirmado'",
            (especialidad, fecha_str),
        ).fetchall()
        conn.close()
        ocupados = [f["hora"] for f in filas]

    return jsonify({
        "ok": True,
        "especialidad": especialidad,
        "profesional": ESPECIALIDADES[especialidad]["profesional"],
        "horarios": horarios_totales,
        "ocupados": ocupados,
    })


if __name__ == "__main__":
    app.run(debug=True)
