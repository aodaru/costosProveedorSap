"""Servidor web del Web UI de ME12 (Fase 4).

Nota: este archivo se desarrolla en Linux pero se ejecuta en la VM Windows con
SAP GUI instalado.  `script/sap.py` importa `win32com` a nivel de módulo, por lo
que cualquier import de `SapGui` o `validators` se hará de forma perezosa *dentro*
de las funciones de las fases posteriores.
"""
import os
import sys
import tempfile

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Agregar `script/` al path para poder importar `SapGui` y `validators` de forma
# perezosa en las fases 2-3 sin modificar el árbol de `script/`.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(PROJECT_ROOT, "script")
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

app = Flask(__name__)

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
if not FLASK_SECRET_KEY:
    raise RuntimeError(
        "FLASK_SECRET_KEY no está definida en el entorno. "
        "Configúrala en el archivo .env antes de iniciar el servidor."
    )
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

# Inicialización de SocketIO para logs en tiempo real en fases posteriores.
socketio = SocketIO(app, cors_allowed_origins="*")

# Estado global del servidor: ready / processing / error.
# Fase 2 solo gestiona "ready" y "error" (upload); "processing" se usará en Fase 3.
SERVER_STATUS = "ready"

# Ruta al Excel temporal validado listo para ejecutar (Fase 3).
CURRENT_UPLOAD_PATH = None


def _cleanup_temp(path):
    """Borra un archivo temporal de forma segura; ignora errores."""
    if not path:
        return
    try:
        os.remove(path)
    except Exception:
        pass


@app.get("/")
def index():
    """Renderiza la página única del Web UI ME12."""
    return render_template("index.html")


@app.get("/status")
def status():
    """Devuelve el estado global del servidor."""
    return jsonify({
        "status": SERVER_STATUS,
        "current_upload": bool(CURRENT_UPLOAD_PATH),
    })


@app.get("/download-template")
def download_template():
    """Sirve la plantilla Excel de entrada ubicada en script/ (read-only)."""
    return send_from_directory(SCRIPT_DIR, "template_me12.xlsx", as_attachment=True)


@app.post("/upload")
def upload():
    """Recibe y valida el Excel de entrada.

    Guarda el archivo en un temporal, reutiliza `validators.validate_excel()`
    de `script/` y retorna la ruta temporal y la cantidad de filas cuando la
    validación es exitosa.
    """
    global SERVER_STATUS, CURRENT_UPLOAD_PATH

    if "file" not in request.files:
        return jsonify({"ok": False, "errors": ["No se recibió archivo."]}), 400

    uploaded = request.files["file"]
    filename = uploaded.filename or ""
    if filename == "":
        return jsonify({"ok": False, "errors": ["No se recibió archivo."]}), 400

    if not filename.lower().endswith(".xlsx"):
        return jsonify(
            {"ok": False, "errors": ["El archivo debe tener extensión .xlsx."]}
        ), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_path = tmp.name
    try:
        uploaded.save(temp_path)
    except Exception as exc:
        _cleanup_temp(temp_path)
        return jsonify(
            {"ok": False, "errors": [f"Error al guardar el archivo: {exc}"]}
        ), 500

    # Import perezoso de `script/`; `validators.py` usa pandas/openpyxl.
    from validators import validate_excel, print_validation_errors

    try:
        data, errors = validate_excel(temp_path, log_func=lambda msg: None)
    except Exception as exc:
        _cleanup_temp(temp_path)
        return jsonify(
            {"ok": False, "errors": [f"Error al validar el archivo: {exc}"]}
        ), 500

    if errors:
        _cleanup_temp(temp_path)
        print_validation_errors(errors, log_func=lambda msg: None)
        SERVER_STATUS = "error"
        return jsonify({"ok": False, "errors": errors}), 400

    # Reemplaza cualquier upload anterior pendiente.
    if CURRENT_UPLOAD_PATH:
        _cleanup_temp(CURRENT_UPLOAD_PATH)
    CURRENT_UPLOAD_PATH = temp_path
    SERVER_STATUS = "ready"
    return jsonify({"ok": True, "path": temp_path, "rows": len(data)})


def _run_sap_process(file_path):
    """Ejecuta el ciclo SAP (login → ME12 → cierre) en un thread de fondo.

    Importa `SapGui` y `pywintypes` de forma perezosa para evitar que
    `win32com` se cargue durante el import de este módulo en Linux.

    Robustez (Fase 4):
    - Verifica que SAP GUI esté instalado antes de intentar login.
    - Verifica que exista sesión SAP después de login.
    - Captura errores de desconexión/ejecución de ME12 y propaga para limpieza.
    - El bloque ``finally`` limpia siempre, incluso si el cierre de SAP falla.
    """
    global SERVER_STATUS, CURRENT_UPLOAD_PATH

    try:
        import pywintypes
    except Exception:
        pywintypes = None

    SAPLOGON_PATH = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"

    def _emit_log(message):
        socketio.emit("log", {"message": message}, broadcast=True)

    def _emit_complete(ok, summary):
        socketio.emit(
            "complete",
            {"ok": ok, "summary": summary},
            broadcast=True,
        )

    def _reset_state(target_status="ready"):
        global SERVER_STATUS
        SERVER_STATUS = target_status
        socketio.emit("status", {"status": target_status}, broadcast=True)

    def _do_cleanup(sap_instance):
        """Borra temporales y cierra SAP de forma segura, sin fallar nunca.

        NOTA: no modifica SERVER_STATUS; el estado final se decide en el flujo
        principal de ``_run_sap_process``.
        """
        global CURRENT_UPLOAD_PATH

        try:
            _emit_log("Cerrando sesión SAP y limpiando temporales...")
        except Exception:
            pass

        try:
            sap_instance.safe_close_window(log_func=_emit_log)
        except AttributeError:
            # sap_instance es None (no se llegó a crear el objeto SAP GUI).
            pass
        except Exception as close_exc:
            try:
                _emit_log(f"Aviso al cerrar SAP: {close_exc}")
            except Exception:
                pass

        try:
            _cleanup_temp(CURRENT_UPLOAD_PATH)
        except Exception:
            pass

        CURRENT_UPLOAD_PATH = None

    sap = None
    try:
        from sap import SapGui

        sap = SapGui()
        socketio.emit("status", {"status": "processing"}, broadcast=True)
        _emit_log("Iniciando conexión con SAP...")

        if not os.path.isfile(SAPLOGON_PATH):
            raise RuntimeError(
                "SAP GUI no está instalado o no se encuentra saplogon.exe "
                "en la ruta esperada."
            )

        sap.sapLogin(log_func=_emit_log)

        if not hasattr(sap, "session") or sap.session is None:
            raise RuntimeError(
                "No se pudo iniciar sesión en SAP. "
                "Revise credenciales, sistema y conectividad."
            )

        _emit_log("Sesión SAP iniciada. Ejecutando ME12...")
        try:
            sap.massive_change(file_path, log_func=_emit_log)
        except Exception as me_exc:
            com_error = getattr(pywintypes, "com_error", None) if pywintypes else None
            if com_error and isinstance(me_exc, com_error):
                _emit_log(f"SAP se desconectó durante la ejecución: {me_exc}")
                raise RuntimeError(
                    "SAP se desconectó durante la ejecución. "
                    "Verifique conectividad y reintente."
                ) from me_exc
            if isinstance(me_exc, RuntimeError):
                _emit_log(f"Error durante la ejecución de ME12: {me_exc}")
                raise
            _emit_log(f"Error inesperado durante la ejecución de ME12: {me_exc}")
            raise

        _emit_log("Ejecución completada.")
        _emit_complete(True, "Ejecución completada con éxito")
        _reset_state("ready")
    except Exception as exc:
        _emit_log(f"Error durante la ejecución: {exc}")
        _emit_complete(False, str(exc))
        _reset_state("error")
    finally:
        _do_cleanup(sap)
        if SERVER_STATUS == "processing":
            try:
                _emit_log("Estado no reseteado tras la ejecución; forzando error.")
            except Exception:
                pass
            _emit_complete(False, "Error inesperado del servidor")
            _reset_state("error")


@app.post("/execute")
def execute():
    """Inicia la ejecución ME12 en SAP de forma asíncrona.

    Solo permite una ejecución a la vez. Si ya hay una corrida en proceso
    retorna 409 Conflict.
    """
    global SERVER_STATUS

    if SERVER_STATUS == "processing":
        return jsonify(
            {"ok": False, "message": "Ya hay una ejecución en proceso."}
        ), 409

    if not CURRENT_UPLOAD_PATH:
        return jsonify(
            {"ok": False, "message": "No se ha cargado un archivo válido."}
        ), 400

    SERVER_STATUS = "processing"
    socketio.emit("status", {"status": "processing"}, broadcast=True)
    socketio.start_background_task(_run_sap_process, CURRENT_UPLOAD_PATH)

    return jsonify({"ok": True, "message": "Ejecución iniciada"}), 202


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
