# 05 — Arquitectura del Proyecto de Referencia: `sapCondMassMod`

> Documento de investigación para replicar patrones en un script Python nuevo (proyecto `costosProveedorSap`).
> Proyecto analizado: `C:\Users\agarcia\dev\sapCondMassMod` (versión v1.0.0, MIT, Adal Michael Garcia, 2026).
> Alcance: lectura únicamente. No se modificó ningún archivo del proyecto de referencia.

---

## 1. Mapa de archivos y responsabilidades

| Archivo | Líneas | Responsabilidad |
|---|---|---|
| `main.py` | 110 | **Punto de entrada + GUI**. Clase `MainWindow(QMainWindow, Ui_MainWindow)`. Conecta botones, orquesta el flujo completo (login SAP, selección Excel, ejecución masiva, logout, descarga de plantilla). Inyecta el log a la UI mediante `self.plainTextEdit.appendPlainText`. |
| `sap.py` | 94 | **Capa de conexión SAP GUI** (scripting vía COM/pywin32). Clase `SapGui`: `open_sap` (abre `saplogon.exe`), `connection_sap`, `sapLogin` (login con credenciales del `.env`), `safe_close_window`, `massive_change` (fachada que crea el runner de negocio). |
| `sap_vk12_massmod.py` | 251 | **Lógica de negocio**: modificaciones masivas en transacción VK12. Clase `SapVk12MassMod(session, log_func)`. `run_vk12_massmod` valida el Excel, itera filas y despacha a métodos de flujo dinámicamente (`getattr`) según `TIPO_MODIFICACION`. |
| `paths.py` | 13 | **Resolución de rutas base** en modo script y en modo ejecutable PyInstaller (`sys.frozen`). Función `get_base_path()`. |
| `validators.py` | 112 | **Validación de datos del Excel**. Carga config desde `.env` (`VALID_FLOWS`, sets válidos, `FLOW_FIELDS` JSON). `validate_excel` lee hoja `vk12`, normaliza columnas, valida por fila/flujo y **elimina filas inválidas**. `validate_field` valida campo a campo. |
| `ui_sap.py` | 182 | **UI generada por `pyside2-uic`** desde `ui_sap.ui` (Qt 5.15.2). Clase `Ui_MainWindow` con `setupUi`/`retranslateUi`. "No editar a mano" (WARNING del generador). |
| `ui_sap.ui` | 247 | **XML de Qt Designer**. Widgets: `txt_file`, `btn_open`, `btn_login`, `btn_ejecutar`, `btn_logout`, `btn_close`, `plainTextEdit`, `lbl_template`. |
| `test_project.py` | 123 | **Tests pytest** (unit). Clase `TestValidators` (valida `validate_field`/`validate_excel` con Excel temporales) y `TestSapVk12MassMod` (esqueleto con sesión mock `None`). |
| `template_vk12.xlsx` | — | Plantilla descargable desde la UI. Hoja `vk12` con columnas: `MATERIAL, UNIDAD_DE_MEDIDA, IMPORTE, GRUPO_ARTICULO, ORG_VENTA, CAN_DISTR, SECTOR, RAMO, TIPO_MODIFICACION`. |
| `test_vk12.xlsx` | — | Excel de prueba para pruebas integrales. |
| `.env` / `.env.example` | 20 | Configuración: credenciales SAP (`SYSTEM, MANDT, USER, PASSWD, LANGUAGE`) + parámetros de validación (`VALID_FLOWS`, `VALID_ORG_VENTA`, `VALID_CAN_DISTR`, `VALID_SECTOR`, `VALID_RAMO`, `VALID_UNIDAD_MEDIDA`, `FLOW_FIELDS` como JSON string). |
| `main.spec` | 39 | Spec de **PyInstaller**: onefile, `console=False`, `icon=['icon.ico']`, `datas=[('LICENSE', '.')]`. |
| `mise.toml` | 14 | Tool de entorno: `python = "3.8"`, `node = "22"`, `pnpm = "latest"`. Tarea `mise run setup` = `pip install pywin32 pandas dotenv PySide2`. |
| `README.md` | 54 | Documentación: instalación, uso, formato del Excel, estructura, pendientes. |
| `LICENSE` | 21 | MIT. |
| `icon.ico` | ~97 KB | Ícono de la aplicación (usado en `main.py` y `main.spec`). |
| `.gitignore` | 10 | Excluye `.env`, `.venv/`, `node_modules/`, `build/`, `dist/`, `__pycache__/`, `main.spec`, etc. |
| `dist/` | — | Build PyInstaller: `main.exe` (~70 MB), `main.zip`, más copias de `template_vk12.xlsx`, `icon.ico`, `.env.example`, `LICENSE` (copiados manualmente). |

**No existe** `requirements.txt`, `pyproject.toml` ni `setup.py`: las dependencias se declaran únicamente en `mise.toml` (tarea `setup`).

---

## 2. Dependencias y entorno

### Python
- **Versión: 3.8.20**, instalada vía **mise** (`.venv/pyvenv.cfg`):
  `home = C:\Users\agarcia\AppData\Local\mise\installs\python\3.8.20`, `version = 3.8.20`.
- Confirmado por los `.pyc` de `__pycache__` (`cpython-38`).

### Librerías instaladas en `.venv\Lib\site-packages` (versiones reales)

| Paquete | Versión | Uso |
|---|---|---|
| `pywin32` | 311 | COM para automatizar SAP GUI (`win32com.client.GetObject("SAPGUI")`). |
| `PySide2` (+ `shiboken2`) | 5.15.2.1 | GUI Qt. Generador `pyside2-uic`. |
| `pandas` | 2.0.3 | Lectura del Excel (`read_excel`). Última versión con soporte Python 3.8. |
| `numpy` | 1.24.4 | Dependencia de pandas (última para 3.8). |
| `openpyxl` | 3.1.5 | Motor Excel de pandas. |
| `python-dotenv` | 1.0.1 | `load_dotenv` para el `.env`. (También existe un paquete obsoleto `dotenv` 0.9.9 en site-packages; el import real usado es el de python-dotenv.) |
| `pytest` | 8.3.5 | Tests (`test_project.cpython-38-pytest-8.3.5.pyc`). |
| `PyInstaller` | 6.20.0 | Empaquetado (`pyinstaller-hooks-contrib` 2026.4, `altgraph` 0.17.5, `pefile` 2024.8.26, `pywin32-ctypes` 0.2.3). |
| Transitives | `et_xmlfile` 2.0.0, `python-dateutil` 2.9.0.post0, `pytz` 2026.1.post1, `tzdata` 2026.1, `six` 1.17.0, `typing_extensions` 4.13.2, `colorama` 0.4.6, `pluggy` 1.5.0, `iniconfig` 2.1.0, `exceptiongroup` 1.3.1, `importlib_metadata` 8.5.0, `packaging` 26.1, `zipp` 3.20.2, `tomli` 2.4.1 | — |
| pip / setuptools | 23.0.1 / 56.0.0 | — |

> Nota de versionado: la combinación `pandas 2.0.3 + numpy 1.24.4 + PySide2 5.15.2.1` es el techo máximo que soporta Python 3.8. Si el proyecto nuevo apunta a Python moderno (3.12+), se pueden usar versiones más recientes.

---

## 3. Flujo de orquestación (main → sap → negocio → resultado)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ main.py (entry point)                                                      │
│   app = QApplication([]); window = MainWindow(); window.show()              │
│   MainWindow(QMainWindow, Ui_MainWindow): setupUi(self) + connect señales  │
└────────────────────────────────────────────────────────────────────────────┘
          │
          ├─ [btn_login]  ─► login_sap()
          │      self.sap = SapGui()
          │      self.sap.sapLogin(self.plainTextEdit.appendPlainText)  ← log callback
          │      (SapGui.session queda con la sesión SAP activa)
          │
          ├─ [btn_ejecutar] ─► massive_change()
          │      QMessageBox de confirmación (Yes/No)
          │      └─ self.sap.massive_change(self.txt_file.text(), self.plainTextEdit.appendPlainText)
          │           │
          │           ▼  sap.py — SapGui.massive_change(file_path, log_func)
          │           Guard: if session is None → raise RuntimeError
          │           runner = SapVk12MassMod(self.session, log_func)
          │           return runner.run_vk12_massmod(file_path)
          │                │
          │                ▼  sap_vk12_massmod.py — run_vk12_massmod
          │                data, errors = validate_excel(file_path, log)   [validators.py]
          │                print_validation_errors(errors, log)
          │                self.session.findById("wnd[0]").maximize()
          │                for index, row in data.iterrows():
          │                    flow_name = row.TIPO_MODIFICACION.lower().replace("-","_")
          │                    method = getattr(self, flow_name, None)     ← dispatch dinámico
          │                    if method: method(session, row, index)
          │                    else: log advertencia "Flujo no encontrado"
          │                         │
          │                         ▼  método de flujo (p. ej. _mat_orgvent_candistr)
          │                         session.findById("wnd[0]/tbar[0]/okcd").text = "vk12"
          │                         ... sendVKey / press / time.sleep(1) ...
          │                         log(f"Fila {index}: ... completada.")  ← reporte por fila
          │
          ├─ [btn_logout] ─► logout() → sap.safe_close_window(log) → CloseSession + taskkill saplogon.exe
          │
          └─ [lbl_template] ─► download_template() → shutil.copy(template_vk12.xlsx, destino)
```

### Cómo se pasa la sesión SAP
- `SapGui` crea y conserva `self.session` (objeto COM de la sesión SAP GUI) en `sapLogin` / `connection_sap`.
- `SapGui.massive_change` inyecta esa sesión en el runner: `SapVk12MassMod(self.session, log_func)`.
- El runner guarda `self.session` en `__init__` y la usa en cada método de flujo. **No hay conexión ni login dentro de la capa de negocio**: la sesión se pasa por constructor (inyección de dependencias).

### Cómo se procesa el Excel
1. **Lectura**: `pd.read_excel(file_path, sheet_name="vk12", dtype=str)`; columnas normalizadas a mayúsculas y espacios→`_`.
2. **Validación**: por fila → valida `TIPO_MODIFICACION` contra `VALID_FLOWS`; luego valida los campos exigidos por ese flujo según `FLOW_FIELDS` (JSON del `.env`). **Las filas con error se eliminan** (`data.drop(index, inplace=True)`) para no procesarlas en SAP.
3. **Actualización en SAP**: para cada fila válida, se ejecuta la secuencia de scripting (transacción VK12, condición Z004, llaves de selección, captura de importe) y se registra el resultado por fila.
4. **Reporte**: vía callback de log (`log_func`) con separadores `"="*50`; se muestra en `plainTextEdit` de la UI. Los errores de validación se listan con `print_validation_errors`. (El README indica como pendiente exportar errores a Excel.)

---

## 4. Patrones transversales

### 4.1 Manejo de errores
- **Sin excepciones propias** (no hay clases heredadas de `Exception`).
- Excepciones de librería usadas:
  - `ValueError` en `run_flow` cuando el flujo no existe.
  - `RuntimeError` en `SapGui.massive_change` como **guard** cuando no hay sesión iniciada.
- `try/except` **desnudos** (`except:`) con `print(sys.exc_info()[0])` en `sap.py` para errores de conexión, reenviando mensaje al log. **No hay `try/finally`**: la limpieza de sesión se hace en `safe_close_window` (botón Logout) y con `taskkill` del proceso `saplogon.exe`.
- Filosofía general: **no lanzar excepciones por datos inválidos**; la validación devuelve una lista de strings de error y la ejecución continúa con las filas válidas.

### 4.2 Logging
- **No usa el módulo `logging`**. Patrón de **callback inyectable** `log_func` (default `print`):
  - `main.py` pasa `self.plainTextEdit.appendPlainText` → se muestra en tiempo real en la GUI.
  - Los runners aceptan `log_func` en el constructor / parámetro.
- Formato: separadores `"="*50`, mensajes en español, uno por evento (login, error de conexión, avance por fila, fin de ejecución).

### 4.3 Validaciones (`validators.py`)
- Config derivada del `.env` en **tiempo de importación** (módulo se carga una vez):
  - `VALID_FLOWS` = tuple de flujos permitidos.
  - `VALID_ORG_VENTA`, `VALID_CAN_DISTR`, `VALID_SECTOR`, `VALID_RAMO`, `VALID_UNIDAD_MEDIDA` = sets.
  - `FLOW_FIELDS` = dict `{flujo: [campos_requeridos]}` parseado de un JSON string del `.env`.
- Helpers: `is_numeric`, `is_integer`, `solo_numeros` (no usa pandas).
- `validate_field(field, value, row_num) -> Optional[str]`: devuelve mensaje de error o `None`. Reglas: obligatoriedad, IMPORTE numérico, MATERIAL/GPO solo dígitos, valores contra los sets permitidos.
- `validate_excel(file_path, log_func) -> (DataFrame, List[str])`: lee, normaliza, valida por fila y **elimina filas inválidas**.

### 4.4 Rutas (`paths.py`)
- Único módulo de resolución de rutas. Funciona tanto en desarrollo (script) como compilado (PyInstaller):
  ```python
  def get_base_path():
      if getattr(sys, 'frozen', False):
          return os.path.dirname(sys.executable)
      else:
          return os.path.dirname(os.path.abspath(__file__))
  ```
- `main.py`, `sap.py` y `validators.py` hacen `BASE_DIR = Path(get_base_path())` y luego `load_dotenv(BASE_DIR / ".env")`. (Commit `10c0bd4` documenta esta unificación.)

### 4.5 Configuración (`.env`)
- **Carga**: `load_dotenv(BASE_DIR / ".env")` en `sap.py` y `validators.py`.
- Dos bloques de variables:
  1. **Credenciales SAP**: `SYSTEM`, `MANDT`, `USER`, `PASSWD`, `LANGUAGE`.
  2. **Parámetros de validación** (editables sin recompilar): listas y el JSON de campos por flujo.
- `.env.example` versionado como plantilla; `.env` excluido del git.
- Los parámetros de validación viven en `.env` y **no** en el código (decisión tomada en los commits `28bc9e1` y `1f9be6c`).

### 4.6 Empaquetado (PyInstaller)
- `main.spec`: análisis de `main.py`, **onefile**, `console=False` (GUI), `icon=['icon.ico']`, `datas=[('LICENSE', '.')]`.
- `dist/` generado contiene además copias manuales de `template_vk12.xlsx`, `icon.ico` y `.env.example` (para que el usuario final pueda editar credenciales/validaciones sin recompilar). Nota: como `get_base_path()` usa `sys.executable` cuando está frozen, los archivos se buscan junto al `.exe`.
- `icon.ico` se usa también en runtime: `app.setWindowIcon(QIcon("icon.ico"))`.
- Curiosidad: `main.spec` está en `.gitignore` (no versionado).

### 4.7 UI
- Flujo de trabajo Qt Designer: editar `ui_sap.ui` → regenerar `ui_sap.py` con `pyside2-uic`. El `.py` es "generado, no tocar".
- `MainWindow` **hereda de `(QMainWindow, Ui_MainWindow)`** (patrón "multi-herencia" de Qt) y llama `setupUi(self)`.
- Ventana **siempre al frente**: `Qt.WindowStaysOnTopHint`.
- Estilos QSS inline en botones (bordes redondeados, hover celeste).
- Widget de log: `QPlainTextEdit` readonly con scrollbar.

---

## 5. Fragmentos de código literal (patrones clave)

### 5.1 Punto de entrada / main
```python
if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("icon.ico"))
    window = MainWindow()
    window.show()
    app.exec_()
```

### 5.2 Conexión de señales y orquestación (main.py)
```python
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Automatin SAP System")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_login.clicked.connect(self.login_sap)
        self.btn_ejecutar.clicked.connect(self.massive_change)
        self.btn_logout.clicked.connect(self.logout)
        self.btn_close.clicked.connect(self.close_application)
        self.plainTextEdit.setReadOnly(True)

    def login_sap(self):
        self.sap = SapGui()
        self.sap.sapLogin(self.plainTextEdit.appendPlainText)
        self.plainTextEdit.appendPlainText(f"{'='*50}")
        self.plainTextEdit.appendPlainText("Login successful")
        self.plainTextEdit.appendPlainText(f"{'='*50}")

    def massive_change(self):
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("Confirmación de ejecución de procedimiento masivo")
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText("Estas Seguro de ejecutar el procedimiento masivo?")
        msgBox.setInformativeText("Se registraran modificaciones a condiciones de precios.")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            self.sap.massive_change(self.txt_file.text(), self.plainTextEdit.appendPlainText)
            self.plainTextEdit.appendPlainText(f"{'='*50}")
            self.plainTextEdit.appendPlainText("Ejecucion completada con exito!")
            self.plainTextEdit.appendPlainText(f"{'='*50}")
```

### 5.3 Fachada SAP con guard de sesión (sap.py)
```python
def massive_change(self, file_path, log_func=print):
    if not hasattr(self, "session") or self.session is None:
        raise RuntimeError("SAP session no iniciada. Ejecute sapLogin primero.")
    runner = SapVk12MassMod(self.session, log_func)
    return runner.run_vk12_massmod(file_path)
```

### 5.4 Login SAP (sap.py) — patrón de conexión COM
```python
def sapLogin(self, log_func=print):
    self.open_sap()
    time.sleep(3)
    self.SapGuiAuto = win32com.client.GetObject("SAPGUI")
    self.application = self.SapGuiAuto.GetScriptingEngine
    try:
        self.connection = self.application.OpenConnection(system_sap, True)
    except:
        print(sys.exc_info()[0])
        log_func(f"{'='*50}")
        log_func(f"Error tratando de conectar con SAP: {sys.exc_info()[0]}")
        log_func(f"La red no esta accesible o el sistema SAP no esta disponible.")
        log_func(f"{'='*50}")
    time.sleep(3)
    self.session = self.connection.Children(0)
    try:
        self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = mandt
        self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = username
        self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = password
        self.session.findById("wnd[0]/usr/txtRSYST-LANGU").text = language
        self.session.findById("wnd[0]").sendVKey(0)
    except:
        print(sys.exc_info()[0])
        log_func(f"Error tratando de conectar con SAP: {sys.exc_info()[0]}")
```

### 5.5 Runner de negocio: constructor + dispatch dinámico (sap_vk12_massmod.py)
```python
class SapVk12MassMod:
    """Lógica de modificación masiva para el flujo VK12."""

    def __init__(self, session, log_func=print):
        self.session = session
        self.log = log_func

    def run_vk12_massmod(self, file_path):
        self.log(f"{'='*50}")
        self.log("Iniciando Proceso ...")
        self.log(f"{'='*50}")
        data, errors = validate_excel(file_path, self.log)
        if errors:
            print_validation_errors(errors, self.log)
        self.session.findById("wnd[0]").maximize()
        for index, row in data.iterrows():
            flow_name = row.TIPO_MODIFICACION.strip().lower()
            method_name = flow_name.replace("-", "_")
            method = getattr(self, method_name, None)
            if method and callable(method):
                method(self.session, row, index)
            else:
                self.log(f"Advertencia: Flujo '{flow_name}' no encontrado. Fila {index}, Material: {row.MATERIAL}")
```

### 5.6 Método de flujo SAP (patrón de scripting GUI)
```python
def _mat_orgvent_candistr(self, session, row, index):
    session.findById("wnd[0]/tbar[0]/okcd").text = "vk12"
    session.findById("wnd[0]").sendVKey(0)
    time.sleep(1)
    session.findById("wnd[0]/usr/ctxtRV13A-KSCHL").text = "Z004"
    ...
    material_field = session.findById(
        "wnd[0]/usr/tblSAPMV13ATCTRL_FAST_ENTRY/ctxtKOMG-MATNR[0,0]"
    )
    existing_material = material_field.text
    if existing_material:
        self.log(f"Fila {index}: material ya contiene datos: {existing_material}")
    else:
        material_field.text = row.MATERIAL
    ...
    self.log(f"Fila {index}: modificación masiva para material {row.MATERIAL} con el importe [ -{row.IMPORTE}% ] completada.")
```

### 5.7 Validación del Excel (validators.py)
```python
def validate_excel(file_path: str, log_func=print) -> Tuple[pd.DataFrame, List[str]]:
    errors = []
    data = pd.read_excel(file_path, sheet_name="vk12", dtype=str)
    data.columns = data.columns.str.strip().str.upper().str.replace(" ", "_")
    for index, row in data.iterrows():
        flow_name = str(row.get("TIPO_MODIFICACION", "")).strip().lower()
        if flow_name not in VALID_FLOWS:
            errors.append(f"Fila {index}: Flujo '{flow_name}' no válido")
            continue
        for field in FLOW_FIELDS.get(flow_name, []):
            error = validate_field(field, row.get(field, ""), index)
            if error:
                errors.append(error)
                data.drop(index, inplace=True)  # Eliminar fila con error para evitar procesamiento posterior
    return data, errors
```

---

## 6. Convenciones de estilo / código

- **Encabezado de copyright en todos los módulos**:
  ```python
  # Copyright (c) 2026 Adal Michael Garcia
  # Licensed under the MIT License - see LICENSE file for details
  ```
- **Nombres**: `snake_case` para funciones/métodos, `PascalCase` para clases, prefijos de widgets (`btn_`, `txt_`, `lbl_`). Mezcla de español/inglés (`open_file`, `massive_change`, `sapLogin`, `orgvent_candistr_gpoart`).
- **Docstrings**: solo en la clase pública (`SapVk12MassMod`), una línea. Sin docstrings en el resto.
- **Type hints**: parciales — `validators.py` usa `Optional, Tuple, List` de `typing`; el resto de módulos no los usa.
- **f-strings** en todos los mensajes de log/error.
- **`time.sleep(1)`** como espera sincrónica entre pasos de SAP (sin polling ni `Session.WaitForGui`).
- **Constantes/validaciones en mayúsculas** (`VALID_FLOWS`, `BASE_DIR`).
- Comentarios en español (`# Llamada de flujos masivos`).
- Default de callbacks: `log_func=print`.
- Un commit importante (`a1ef578`) describe la intención: "reportar el error pero la ejecución se complete con las líneas procesadas" (fail-soft).

---

## 7. Tests (`test_project.py`)

- **Runner**: `pytest` (v8.3.5). Comando documentado: `pytest test_project.py`.
- **Estructura**: dos clases de tests; no usa fixtures.
  - `TestValidators` (11 tests): unitarios de `validate_field` (material válido/inválido, importe obligatorio/numérico, org venta, canal, sector, ramo, largo/caracteres de grupo artículo, unidad de medida) y de `validate_excel` (datos válidos, flujo inválido, campo faltante).
- **Cómo crean Excels temporales**:
  ```python
  with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
      df.to_excel(tmp.name, sheet_name="vk12", index=False)
      tmp.close()  # Close the file before reading
      validated_data, errors = validate_excel(tmp.name)
      os.unlink(tmp.name)
  ```
- **Qué se mockea**: la sesión SAP **no** se mockea con `MagicMock` todavía; `SapVk12MassMod(None, print)` pasa `None` como sesión para testear solo `available_flows()` y el `ValueError` de `run_flow("invalid", ...)`. El comentario del final sugiere `unittest.mock.MagicMock` para tests futuros de `run_vk12_massmod` usando `test_vk12.xlsx`.
- **Qué se verifica**: substrings de los mensajes de error en español (p. ej. `"no debe contener letras"`, `"debe ser numérico"`) y conteo de errores/filas.

---

## 8. Plantillas a reutilizar para un proyecto nuevo

| # | Plantilla / módulo | Qué copiar | Qué adaptar |
|---|---|---|---|
| 1 | `paths.py` | `get_base_path()` con `sys.frozen` — copiar **tal cual**. | Nada. |
| 2 | `validators.py` | Patrón completo: `load_dotenv(BASE_DIR/.env)`, `VALID_*` desde env, `FLOW_FIELDS` JSON, `validate_field` + `validate_excel` (hoja + normalización + drop de filas inválidas). | Nombres de campos/flujos y sets según el dominio del proveedor. |
| 3 | `sap_vk12_massmod.py` | Patrón runner: `__init__(session, log_func)`, `available_flows()`, `run_flow(flow, path)` con `ValueError`, `run_<flow>` que despacha por `getattr` a métodos por flujo; métodos `_flujo(session, row, index)` con scripting `findById` + `time.sleep`. | Transacción SAP y campos de la pantalla (p. ej. MM42/MRKO en vez de VK12). |
| 4 | `sap.py` | `SapGui` como fachada: `open_sap`, `connection_sap` (COM), `sapLogin`, `safe_close_window`, `massive_change` con **guard de sesión** `RuntimeError` y construcción del runner. | Nada. |
| 5 | `main.spec` | Spec PyInstaller onefile + `console=False` + `icon=['icon.ico']` + `datas`. | Nombre del exe; añadir `datas` para template/`.env.example`. |
| 6 | `mise.toml` | Declarar `python = "3.8"` + tarea `setup` con `pip install`. | Versiones si se sube de Python. |
| 7 | `.env.example` | Bloque de credenciales SAP + bloque de validaciones (listas + JSON). | Valores según sistema. |
| 8 | `test_project.py` | Patrón de tests con `tempfile.NamedTemporaryFile(.xlsx)` + `df.to_excel(tmp.name, sheet_name=...)`; clase de tests para el runner con sesión `None`; directriz de mockeo futuro con `MagicMock`. | Dominio nuevo. |
| 9 | Logging por callback | `log_func=print` como default en constructores y `log_func(self.plainTextEdit.appendPlainText)` desde la GUI. | Si se quiere `logging` de stdlib, sustituir pero manteniendo el inyectado de UI. |

### Lecciones / limitaciones a evitar
- `except:` desnudos y `print(sys.exc_info()[0])` → preferir excepciones tipadas y `logging`.
- `time.sleep(1)` fijo → considerar espera robusta (polling o `Session.WaitForGui`).
- Falta de manejo de popups de error de SAP (no hay `Session.Properties("transaction_info")` ni detección de status bar) → en un script nuevo conviene un helper de "verificar errores de SAP tras cada paso".
- `data.drop(index, inplace=True)` dentro de un `iterrows()` puede generar advertencias; alternativa: recolectar índices inválidos y dropear al final.
- Credenciales en `.env` en texto plano (aceptable para scripting interno; nunca versionar `.env`).
- No hay `try/finally` para cerrar sesión: la limpieza depende del botón Logout / `taskkill`. En un script nuevo conviene garantizar cierre en `finally`.

---
*Fin del documento — generado el 2026-08-01 para `costosProveedorSap/research/05_arquitectura_referencia.md`.*
