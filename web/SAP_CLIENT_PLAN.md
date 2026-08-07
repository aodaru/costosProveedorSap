# Plan: `web/sap_client.py` — Módulo SAP autocontenido

**Fecha:** 2026-08-07
**Objetivo:** Eliminar la dependencia de `script/sap.py` en `web/server.py` creando un módulo SAP autocontenido que incluya la lógica de conexión Y la lógica ME12.

---

## 1. Decisión de diseño: ¿Inline o Separar ME12?

### **Recomendación: Opción A — Inline en `web/sap_client.py`**

| Criterio | Opción A (Inline) | Opción B (Separado) |
|---|---|---|
| Archivos a crear/Modificar | 1 archivo nuevo, 1 modificado | 2 archivos nuevos, 1 modificado |
| Acoplamiento sesión SAP | La sesión vive dentro de `SapClient` —自然 | Requiere pasar `session` entre archivos |
| Tamaño del archivo | ~500 líneas (manejable) | ~110 + ~400 (dos archivos medianos) |
| Mantenimiento | Un solo lugar para lógica SAP | Dos archivos coordinados |
| Testing futuro | Clase autocontenida | ME12 testeable aisladamente |

**Justificación:** La lógica ME12 (`me12_massmod.py`) está inherentemente acoplada al objeto `session` de SAP GUI. No tiene sentido separarla en un archivo independiente cuando necesita acceso directo a `self.session.findById()`. Inline mantiene la encapsulación: `SapClient` owns la sesión Y la ejecución.

---

## 2. Archivos a crear/modificar

### 2.1. **NUEVO: `web/sap_client.py`** (~500 líneas)

#### Estructura

```python
"""Módulo SAP autocontenido para la Web UI ME12.

Reemplaza la dependencia de script/sap.py y script/me12_massmod.py.
Diseñado para ejecutarse en la VM Windows con SAP GUI.
"""
import subprocess
import time
import os
from pathlib import Path

# win32com se importa DENTRO de métodos (no a nivel módulo)
# para permitir importar este módulo en Linux sin error.


class SapClient:
    """Cliente SAP completo: conexión, login, ME12, cierre."""

    def __init__(self, system, mandt, username, password, language):
        self.system = system
        self.mandt = mandt
        self.username = username
        self.password = password
        self.language = language

        self.session = None
        self.connection = None
        self.application = None

        # Delays configurables (segundos)
        self.delay_after_enter = 0.5
        self.delay_after_click = 0.3
        self.delay_between_rows = 1.0
        self.condition_row = 2
        self.sap_default_date = "31.12.9999"

    # --- Conexión y Login ---

    def connect(self, log_func=print):
        """Abre SAP Logon y establece conexión."""
        # Import perezoso de win32com
        import win32com.client
        import pywintypes

        self._open_sap_logon()
        time.sleep(3)

        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
        except pywintypes.com_error as e:
            log_func(f"SAP GUI no encontrado: {e}")
            return False

        self.application = SapGuiAuto.GetScriptingEngine

        try:
            self.connection = self.application.OpenConnection(self.system, True)
        except Exception as e:
            log_func(f"Error conectando a SAP: {e}")
            return False

        time.sleep(3)
        self.session = self.connection.Children(0)
        return True

    def login(self, log_func=print):
        """Llena campos de login y envía."""
        import pywintypes

        try:
            self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = self.mandt
            self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = self.username
            self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = self.password
            self.session.findById("wnd[0]/usr/txtRSYST-LANGU").text = self.language
            self.session.findById("wnd[0]").sendVKey(0)
            time.sleep(2)

            # Manejar popup "Session already open"
            try:
                popup = self.session.findById("wnd[1]")
                if popup and "already open" in str(popup.Text):
                    popup.findById("tbar[0]/btn[0]").press()
            except Exception:
                pass
        except Exception as e:
            log_func(f"Error de autenticación SAP: {e}")
            return False
        return True

    # --- Ejecución ME12 ---

    def run_me12(self, file_path, log_func=print):
        """Ejecuta la modificación masiva ME12."""
        # Import perezoso de win32com + validators
        from validators import validate_excel, print_validation_errors

        if not self.session:
            raise RuntimeError("SAP session no iniciada. Ejecute connect + login primero.")

        log_func("=" * 50)
        log_func("Iniciando Proceso ME12 - Actualización Masiva de Precio...")
        log_func("=" * 50)

        data, errors = validate_excel(file_path, log_func)
        if errors:
            print_validation_errors(errors, log_func)
        if data.empty:
            log_func("No hay registros válidos para procesar.")
            return

        self.session.findById("wnd[0]").maximize()

        total = len(data)
        ok_count = 0
        error_count = 0

        for index, row in data.iterrows():
            log_func(f"Procesando registro {index + 1} de {total}...")
            result = self._process_record(row, index, log_func)
            if result.startswith("OK"):
                ok_count += 1
            else:
                error_count += 1
            time.sleep(self.delay_between_rows)

        log_func("=" * 50)
        log_func(f"Proceso completado. Total: {total}, Exitosos: {ok_count}, Errores: {error_count}")
        log_func("=" * 50)

    # --- Cierre ---

    def close(self, log_func=print):
        """Cierra sesión SAP y SAP Logon."""
        import subprocess

        try:
            self.session.findById("wnd[0]").maximize()
            self.connection.CloseSession("ses[0]")
        except Exception as e:
            log_func(f"Error al cerrar sesión SAP: {e}")
        finally:
            subprocess.run(["taskkill", "/f", "/im", "saplogon.exe"])

    # --- Métodos privados ---

    def _open_sap_logon(self):
        """Abre saplogon.exe."""
        path = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
        subprocess.Popen(path)

    def _process_record(self, row, index, log_func):
        """Procesa un registro individual de ME12."""
        # Extraer campos del row
        material = str(row.get("MATERIAL", "")).strip()
        proveedor = str(row.get("PROVEEDOR", "")).strip()
        org_compras = str(row.get("ORG_COMPRAS", "")).strip()
        nuevo_precio = str(row.get("NUEVO_PRECIO", "")).strip()

        # Calcular fechas de validez
        valido_desde_raw = str(row.get("VALIDO_DESDE", "")).strip()
        valido_hasta_raw = str(row.get("VALIDO_HASTA", "")).strip()
        validez_desde, validez_hasta = self._compute_validity_dates(
            valido_desde_raw, valido_hasta_raw
        )

        try:
            # PASO 1: Navegar a ME12
            self.session.findById("wnd[0]/tbar[0]/okcd").Text = "/nME12"
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(self.delay_after_enter)

            # PASO 2-5: Llenar campos y confirmar
            self.session.findById("wnd[0]/usr/ctxtEINA-LIFNR").Text = proveedor
            self.session.findById("wnd[0]/usr/ctxtEINA-MATNR").Text = material
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").SetFocus
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").CaretPosition = len(org_compras)
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").Text = org_compras
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(self.delay_after_enter)

            # ... (resto de la lógica ME12 copiada de me12_massmod.py)

            return "OK"

        except Exception as e:
            error_msg = str(e)
            try:
                sap_msg = self.session.findById("wnd[0]/sbar").Text
                if sap_msg:
                    error_msg += f" | SAP: {sap_msg}"
            except Exception:
                pass
            log_func(f"Fila {index}: ERROR: {error_msg}")
            return f"ERROR: {error_msg}"

    def _compute_validity_dates(self, desde_raw, hasta_raw):
        """Calcula fechas de validez para SAP."""
        from datetime import datetime

        today = datetime.now().strftime("%Y%m%d")

        desde_fmt = self._parse_date(desde_raw)
        if not desde_fmt or desde_fmt < today:
            desde_final = today
        else:
            desde_final = desde_fmt

        hasta_fmt = self._parse_date(hasta_raw)
        if not hasta_fmt or hasta_fmt <= today:
            hasta_final = self.sap_default_date
        else:
            hasta_final = self._format_date_sap(hasta_fmt)

        return (self._format_date_sap(desde_final), hasta_final)

    @staticmethod
    def _parse_date(value):
        """Convierte dd.mm.yyyy o YYYYMMDD a YYYYMMDD."""
        value = value.strip()
        if not value:
            return ""
        if "." in value:
            parts = value.split(".")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                return f"{parts[2]}{parts[1]}{parts[0]}"
        if value.isdigit() and len(value) == 8:
            return value
        return ""

    @staticmethod
    def _format_date_sap(yyyymmdd):
        """Convierte YYYYMMDD a dd.mm.yyyy para SAP."""
        if not yyyymmdd or len(yyyymmdd) != 8:
            return yyyymmdd
        return f"{yyyymmdd[6:8]}.{yyyymmdd[4:6]}.{yyyymmdd[0:4]}"

    def _wait_for_control(self, control_id, timeout=5.0, log_func=None):
        """Reintenta findById hasta que el control exista."""
        start = time.time()
        attempts = 0
        while time.time() - start < timeout:
            try:
                ctrl = self.session.findById(control_id)
                return ctrl
            except Exception:
                attempts += 1
                time.sleep(0.2)
        raise TimeoutError(f"Control '{control_id}' no encontrado tras {timeout}s")
```

#### Contenido completo del archivo

Copia la lógica de estos archivos de `script/`:
- **`script/sap.py`** → métodos `connect()`, `login()`, `close()`
- **`script/me12_massmod.py`** → método `run_me12()` + `_process_record()` + helpers (`_parse_date`, `_format_date_sap`, `_compute_validity_dates`, `_wait_for_control`)

**Cambios clave vs. el código original:**
1. **Imports de `win32com` y `pywintypes`** → dentro de cada método (no a nivel módulo)
2. **Credenciales** → via `__init__()` explícito, no via globals de módulo
3. **`log_func`** → se pasa explícitamente a todos los métodos
4. **`validators`** → se importa dentro de `run_me12()` (no a nivel módulo)
5. **Delays y constants** → atributos de instancia, no globals

---

### 2.2. **MODIFICAR: `web/server.py`**

#### Cambios en `_run_sap_process()`

**ANTES (líneas 203-215):**
```python
sap = None
try:
    from sap import SapGui
    import sap as sap_module

    # Override module-level globals so sapLogin() uses the credentials
    sap_module.mandt = os.environ.get("SAP_MANDANT", "")
    sap_module.username = username
    sap_module.password = password
    sap_module.language = os.environ.get("SAP_LANG", "")
    sap_module.system_sap = os.environ.get("SAP_SYSTEM", "")

    sap = SapGui()
    socketio.emit("status", {"status": "processing"})
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
```

**DESPUÉS:**
```python
sap = None
try:
    from sap_client import SapClient

    socketio.emit("status", {"status": "processing"})
    _emit_log("Iniciando conexión con SAP...")

    if not os.path.isfile(SAPLOGON_PATH):
        raise RuntimeError(
            "SAP GUI no está instalado o no se encuentra saplogon.exe "
            "en la ruta esperada."
        )

    sap = SapClient(
        system=os.environ.get("SAP_SYSTEM", ""),
        mandt=os.environ.get("SAP_MANDANT", ""),
        username=username,
        password=password,
        language=os.environ.get("SAP_LANG", ""),
    )

    if not sap.connect(log_func=_emit_log):
        raise RuntimeError(
            "No se pudo conectar a SAP. "
            "Revise la red y que SAP GUI esté disponible."
        )

    if not sap.login(log_func=_emit_log):
        raise RuntimeError(
            "No se pudo iniciar sesión en SAP. "
            "Revise credenciales, mandt y idioma."
        )

    _emit_log("Sesión SAP iniciada. Ejecutando ME12...")
    try:
        sap.run_me12(file_path, log_func=_emit_log)
    except Exception as me_exc:
        try:
            import pywintypes
        except ImportError:
            pywintypes = None
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
```

#### Cambios en `_do_cleanup()`

**ANTES:**
```python
def _do_cleanup(sap_instance):
    # ...
    try:
        sap_instance.safe_close_window(log_func=_emit_log)
    except AttributeError:
        # sap_instance es None
        pass
```

**DESPUÉS:**
```python
def _do_cleanup(sap_instance):
    # ...
    try:
        sap_instance.close(log_func=_emit_log)
    except AttributeError:
        # sap_instance es None (no se llegó a crear)
        pass
```

#### Cambios en imports del archivo

**ANTES (líneas 1-24):**
```python
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
```

**DESPUÉS:**
```python
import os
import sys
import tempfile

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_socketio import SocketIO

# Cargar variables de entorno desde .env (si existe)
load_dotenv()

# Agregar `script/` al path SOLO para validators (import perezoso en upload).
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_DIR = os.path.join(PROJECT_ROOT, "script")
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)
```

> **Nota:** El `sys.path` se mantiene temporalmente para `validators.py` (la otra dependencia de `script/`), pero se documenta que es solo para validación de Excel, no para SAP.

#### Cambio en import de SapGui

**ANTES (dentro de `_run_sap_process`, línea 204):**
```python
from sap import SapGui
import sap as sap_module
```

**DESPUÉS:**
```python
from sap_client import SapClient
```

#### Cambio en import de pywintypes

**ANTES (dentro de `_run_sap_process`, línea 151-153):**
```python
try:
    import pywintypes
except Exception:
    pywintypes = None
```

**DESPUÉS:** Eliminar este bloque. `pywintypes` se importa dentro de `sap_client.py` bajo demanda.

---

## 3. Flujo de ejecución nuevo

```
server.py                          sap_client.py                     SAP GUI
    │                                   │                               │
    ├─ POST /execute(username, pwd)     │                               │
    │   └─ socketio.start_background    │                               │
    │                                   │                               │
    └─ _run_sap_process(path, u, p)    │                               │
        ├─ SapClient(system, mandt...)  │                               │
        ├─ sap.connect(log_func=emit)   │                               │
        │   ├─ open_sap_logon()─────────┼──────► subprocess.Popen       │
        │   └─ GetObject("SAPGUI")──────┼──────► win32com.client       │
        │   └─ OpenConnection()─────────┼──────► SAP Logon             │
        │                               │                               │
        ├─ sap.login(log_func=emit)     │                               │
        │   └─ fill mandt/user/pwd──────┼──────► SAP Login Screen      │
        │                               │                               │
        ├─ sap.run_me12(path, emit)     │                               │
        │   ├─ validate_excel()          │                               │
        │   ├─ for row in data:          │                               │
        │   │   └─ _process_record()────┼──────► /nME12 → fill → save  │
        │                               │                               │
        └─ sap.close(log_func=emit)     │                               │
            ├─ CloseSession("ses[0]")────┼──────► SAP session close     │
            └─ taskkill saplogon.exe     │                               │
```

---

## 4. Checklist de implementación

### Paso 1: Crear `web/sap_client.py`
- [ ] Copiar lógica de conexión de `script/sap.py` → `connect()`, `login()`
- [ ] Copiar lógica ME12 de `script/me12_massmod.py` → `run_me12()`, `_process_record()`
- [ ] Copiar helpers de `script/me12_massmod.py` → `_parse_date`, `_format_date_sap`, `_compute_validity_dates`, `_wait_for_control`
- [ ] Mover imports de `win32com` y `pywintypes` DENTRO de métodos
- [ ] Mover import de `validators` DENTRO de `run_me12()`
- [ ] Reemplazar globals de módulo por parámetros de `__init__()`
- [ ] Verificar que `log_func` se pasa correctamente a todos los métodos
- [ ] Agregar docstrings y type hints

### Paso 2: Modificar `web/server.py`
- [ ] Eliminar bloque `try: import pywintypes` (líneas 151-153)
- [ ] Reemplazar `from sap import SapGui` → `from sap_client import SapClient`
- [ ] Eliminar `import sap as sap_module` y monkey-patching de globals
- [ ] Instanciar `SapClient(system, mandt, username, password, language)`
- [ ] Reemplazar `sap.sapLogin(log_func=...)` → `sap.connect()` + `sap.login()`
- [ ] Reemplazar `sap.massive_change(...)` → `sap.run_me12(...)`
- [ ] Reemplazar `sap.safe_close_window(...)` → `sap.close(...)`
- [ ] Actualizar comentarios y docstrings

### Paso 3: Verificar que `script/` NO fue modificado
- [ ] `git diff -- script/` debe mostrar vacío
- [ ] `script/sap.py` intacto (106 líneas)
- [ ] `script/me12_massmod.py` intacto (398 líneas)
- [ ] `script/validators.py` intacto (189 líneas)

### Paso 4: Testing en VM
- [ ] `python web/server.py` arranca sin errores de import
- [ ] `POST /upload` funciona (validators desde script/ via sys.path)
- [ ] `POST /execute` ejecuta login → ME12 → cierre correctamente
- [ ] Logs en tiempo real vía SocketIO funcionan
- [ ] Cierre de SAP funciona tras cada ejecución (éxito y error)

---

## 5. Dependencias futuras en `script/` (post-migración)

| Archivo de script/ | Importado por web/ | Propósito | Acción futura |
|---|---|---|---|
| `validators.py` | `server.py` (upload) | Validación Excel | Migrar a `web/validators.py` en fase futura |
| `template_me12.xlsx` | `server.py` (download) | Plantilla descargable | Mover a `web/templates/` en fase futura |
| `paths.py` | Solo por validators | `get_base_path()` | Se resuelve al migrar validators |

> **Nota:** La migración completa de `validators.py` a `web/` es un trabajo futuro separado. Por ahora, el sys.path hack se mantiene SOLO para validación de Excel.

---

## 6. Errores comunes a evitar

1. **❌ Importar `win32com` a nivel de módulo en `sap_client.py`** → Falla en Linux
2. **❌ Olvidar pasar `log_func` a métodos internos** → Logs silenciados
3. **❌ No manejar `AttributeError` en `_do_cleanup`** → Crash si SAP no se conectó
4. **❌ Modificar `script/sap.py`** → Viola la regla de solo lectura
5. **❌ No verificar `session` antes de ejecutar ME12** → `NoneType` error
6. **❌ No cerrar SAP en finally** → Proceso saplogon.exe huérfano

---

## 7. Resumen de cambios

| Archivo | Acción | Líneas ~antes | Líneas ~después |
|---|---|---|---|
| `web/sap_client.py` | **CREAR** | 0 | ~500 |
| `web/server.py` | **MODIFICAR** | 310 | ~290 |
| `script/*` | **NO MODIFICAR** | — | — |

**Neto:** +1 archivo nuevo, 1 archivo modificado, 0 archivos en `script/` tocados.
