# Clínica Salud Integral — Gestión de Turnos con IA
Desarrollo de una aplicación web para la gestión de turnos médicos que presenta la cartilla de especialidades y profesionales de la clínica, permitiendo a los pacientes registrarse, iniciar sesión, reservar turnos verificando disponibilidad horaria y cancelarlos. Incluye un Asistente de Orientación Médica con Inteligencia Artificial que analiza los síntomas del paciente para sugerir la especialidad indicada, el nivel de prioridad y recomendaciones previas a la consulta.

## Requisitos
- Python 3.10 o superior instalado

## Construcción 🛠️
- **Lenguaje:** Python, JavaScript, HTML5 y CSS3
- **Backend y Base de Datos:** Flask, Jinja2, SQLite3 y Werkzeug Security
- **Inteligencia Artificial:** Google Gemini API (`gemini-3.1-flash-lite`)

## Instalación y ejecución
1. Clonar repositorio:
   ```bash
   git clone https://github.com/FlorRoth/TP2--FlorenciaRoth.git
   cd TP2--FlorenciaRoth
   ```
2. Crear y activar el entorno virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instalar las dependencias:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Configurar la clave de API en un archivo `.env` en la raíz del proyecto:
   ```env
   GEMINI_API_KEY= clave_de_gemini
   ```
5. Iniciando el servidor:
   ```bash
   python backend/app.py
   ```
6. Deteniendo el servidor:
   - `Ctrl+C`

## API de Inteligencia Artificial
- **Utilizado:** API REST de **Google Gemini**, utilizada para procesar los síntomas ingresados por el paciente y devolver la especialidad médica sugerida, prioridad y recomendación clínica.
- **Documentación:** ( https://ai.google.dev/gemini-api/docs )

## Autora
- **Florencia Roth** — Trabajo Práctico N.° 2 PROGRAMACIÓN WEB
