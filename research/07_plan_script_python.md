# Plan — Script Python: Actualización Masiva del Precio (PB00/PB01) de Info Records vía ME12

> **Feature ID:** `PYTHON_ME12_MASSCOND`
> **Fecha:** 2026-08-01
> **Estado:** PROPUESTO — pendiente de confirmar "Decisiones abiertas" antes de implementar.
> **Fuentes:** research/04 (ciclo de vida SAP), research/05 (arquitectura de referencia), research/06 (objetivo), scripts/me12_price_change.vba (precedente VBA), README.md (reglas de oro).

---

## 1. Objetivo

Crear en costosProveedorSap un **script Python para Windows** que automatice en SAP GUI la **actualización masiva del precio neto (condición PB00/PB01, KONP-KBETR) de los info records de compras** mediante la transacción **ME12**, replicando:

1. El **patrón de inicio de sesión, cierre de sesión y cierre de programa** del proyecto sapCondMassMod (sap.py: open_sap, connection_sap, sapLogin, safe_close_window).
2. El **flujo por registro de ME12** ya probado en scripts/me12_price_change.vba (IDs del recording real).
3. La **arquitectura** de sapCondMassMod (paths.py, validadores pandas, runner por inyección de sesión, log por callback, .env, GUI PySide2 o CLI).

NO se toca el reporte ABAP existente (src/) ni el README salvo que las decisiones abiertas lo pidan.

## 2. Qué se copia del proyecto de referencia sapCondMassMod

| Pieza | Archivo fuente | Qué copiar | Mejora requerida |
|---|---|---|---|
| Rutas | paths.py | get_base_path() con sys.frozen | Tal cual |
| Login | sap.py::open_sap | subprocess.Popen a saplogon.exe | Tal cual |
| Conexión COM | sap.py::connection_sap | GetObject("SAPGUI") -> GetScriptingEngine -> Children(0) -> Children(0) -> maximize() | Envolver en try/except de pywintypes.com_error |
| Login | sap.py::sapLogin | OpenConnection + rellenar RSYST + sendVKey(0) | Retornar/levantar si OpenConnection falla; manejar popup "session already open"; verificar sesión |
| Cierre de sesión | sap.py::safe_close_window | CloseSession('ses[0]') + taskkill | try/finally para garantizar cierre |
| Fachada | sap.py::massive_change | Guard RuntimeError si session is None; construir runner | Tal cual |
| Credenciales | .env / .env.example | SYSTEM, MANDT, USER, PASSWD, LANGUAGE | Tal cual |
| Validación | validators.py | Patrón pandas validate_field + validate_excel | Campos/dominios ME12 |
| Runner | sap_vk12_massmod.py | __init__(session, log_func), run_*, dispatch por getattr | Transacción ME12, campos del VBA |
| Entry point | main.py | GUI PySide2 o CLI | Según decisión |
| Tests | test_project.py | pytest + tempfile Excel + session mock | Dominio nuevo |

## 3. Estructura de archivos a crear

| Archivo | Contenido |
|---|---|
| paths.py | get_base_path() frozen-aware |
| sap.py | Clase SapGui (login / cierre sesión / cierre programa / massive_change) |
| me12_massmod.py | Clase SapMe12MassMod(session, log_func) — runner ME12 |
| validators.py | Validación del archivo de entrada (pandas) |
| main.py | Entry point (GUI o CLI) |
| .env.example | Credenciales SAP + parámetros de validación |
| template_me12.xlsx | Plantilla de entrada (hoja "Datos") |
| test_project.py | Tests pytest |
| mise.toml | Entorno/dependencias |
| .gitignore | Añadir .env, .venv/, __pycache__/, build/, dist/ |

## 4. Roadmap de implementación

1. **P1 — Infraestructura:** paths.py, .env.example, mise.toml, .gitignore, template_me12.xlsx.
2. **P2 — Capa SAP (el corazón del pedido):** sap.py con login / cierre sesión / cierre programa (patrón sapCondMassMod + mejoras de robustez).
3. **P3 — Validadores:** validators.py (reglas del ABAP y del VBA) + tests de validadores.
4. **P4 — Runner ME12:** me12_massmod.py (flujo por registro según VBA).
5. **P5 — Entry point:** main.py (GUI o CLI) que orquesta login -> ejecución -> logout/cierre.
6. **P6 — Tests:** test_project.py completo (validadores + runner con sesión mockeada).
7. **P7 — Docs:** nota en README o scripts/README_python_script.md.

## 5. Especificación por módulo

### 5.1 paths.py
get_base_path(): si sys.frozen -> os.path.dirname(sys.executable); si no -> os.path.dirname(os.path.abspath(__file__)).

### 5.2 sap.py

A nivel de módulo: BASE_DIR = Path(get_base_path()), load_dotenv(BASE_DIR / ".env"), credenciales: SYSTEM, MANDT, USER, PASSWD, LANGUAGE.

**open_sap():**
subprocess.Popen(r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe")

**connection_sap():**
GetObject("SAPGUI") -> .GetScriptingEngine -> self.connection = application.Children(0) -> self.session = self.connection.Children(0) -> session.findById("wnd[0]").maximize(). Envolver GetObject en try/except pywintypes.com_error.

**sapLogin(log_func=print):**
1. open_sap() + time.sleep(3)
2. GetObject("SAPGUI") en try/except pywintypes.com_error -> log "SAP GUI no encontrado" y RETURN
3. GetScriptingEngine
4. OpenConnection(system_sap, True) en try/except -> log error y RETURN (el original no hace return: corregir)
5. time.sleep(3), self.session = self.connection.Children(0)
6. Rellenar wnd[0]/usr/txtRSYST-MANDT, txtRSYST-BNAME, pwdRSYST-BCODE, txtRSYST-LANGU, sendVKey(0)
7. Manejar popup "session already open" si aparece
8. Verificar sesión activa antes de reportar éxito

**safe_close_window(log_func=print):**
try: connection_sap(); self.connection.CloseSession('ses[0]') except -> log
finally: subprocess.run(["taskkill", "/f", "/im", "saplogon.exe"])

**massive_change(file_path, log_func=print):**
Guard RuntimeError si session is None. Runner = SapMe12MassMod(self.session, log_func). return runner.run_me12_massmod(file_path).

### 5.3 me12_massmod.py (runner ME12)

Constantes: T_CODE = "ME12", CONDITION_ROW (default 2, 0-based), delays configurables.

**run_me12_massmod(file_path):**
1. Log inicio
2. validate_excel -> data, errors; listar errores
3. maximize wnd[0]
4. Por cada fila -> _procesar_registro(session, row, index)

**_procesar_registro(session, row, index) — pasos de pantalla (IDs del VBA):**

| Paso | ID SAP | Acción |
|---|---|---|
| 1 | wnd[0]/tbar[0]/okcd = /nME12 + sendVKey(0) | Navegar |
| 2 | wnd[0]/usr/ctxtEINA-LIFNR | Proveedor |
| 3 | wnd[0]/usr/ctxtEINA-MATNR | Material |
| 4 | wnd[0]/usr/ctxtEINE-EKORG (+ setFocus/caretPosition) | Org. compras |
| 5 | sendVKey(0) | Enter |
| 6 | wnd[0]/tbar[1]/btn[8] | Botón Condiciones |
| 7 | wnd[1]/tbar[0]/btn[7] | Popup confirmación (tolerante) |
| 8 | wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[{CONDITION_ROW},0] | Nuevo precio |
| 9 | Opcionales: KONP-KPEIN, KONP-KONWA, KONP-KMEIN, DATAB/DATBI | Según columnas |
| 10 | wnd[0]/tbar[0]/btn[11] | Guardar (F11) |
| 11 | wnd[0]/sbar | Leer status bar -> OK/ERROR |

### 5.4 validators.py

Columnas de entrada (hoja "Datos"): Material, Proveedor, Org_Compras, Tipo_Info, Tipo_Condicion, Nuevo_Precio, Moneda, Unidad_Precio, Unidad_Medida, Valido_Desde, Valido_Hasta.

Reglas del ABAP:
- Clave obligatoria: Material, Proveedor, Org_Compras
- Material/Proveedor numéricos (ALPHA: ceros a la izquierda)
- Nuevo_Precio numérico > 0
- Valido_Desde <= Valido_Hasta
- Defaults: Tipo_Condicion=PB00, Unidad_Precio=1, Valido_Desde=hoy, Valido_Hasta=99991231

### 5.5 main.py

GUI PySide2 (patrón sapCondMassMod) o CLI (argparse). Login -> Ejecutar (con confirmación) -> Logout -> Cierre.

### 5.6 .env.example

```
SYSTEM="ERQ"
MANDT="200"
USER="user"
PASSWD="password"
LANGUAGE="ES"
```

### 5.7 template_me12.xlsx

Hoja "Datos" con cabeceras de §5.4 y 1-2 filas de ejemplo.

### 5.8 test_project.py

- TestValidators: validate_field/validate_excel con Excel temporales
- TestSapMe12MassMod: runner con sesión MagicMock
- Comando: pytest test_project.py

### 5.9 Dependencias

Python 3.8+ (o 3.12+ según decisión). Librerías: pywin32, pandas, openpyxl, python-dotenv, pytest, PySide2 (si GUI).

## 6. Flujo de ejecución completo

1. Login (patrón sapCondMassMod)
2. Validación del archivo (fail-soft)
3. Bucle ME12 por fila (navegar -> clave -> condiciones -> editar KONP-KBETR -> guardar -> status bar -> log)
4. Post-proceso opcional: RM06INP0
5. Cierre: CloseSession + taskkill

## 7. Reglas de oro y riesgos

1. NO SQL directo sobre KONH/KONP/A017/A018
2. NO BAPI_PRICES_CONDITIONS ni ME_INFORECORD_MAINTAIN_MULTI
3. Tras cambiar condiciones -> RM06INP0 para resincronizar EINE-NETPR
4. Los POs ya creados no cambian
5. Requiere sapgui/user_scripting=TRUE y autorizaciones M_EINK + M_EIKO
6. Probar primero en Desarrollo/Quality con 1 registro
7. Frágil ante cambios de pantalla -> grabar recording propio en sistema destino
8. CONDITION_ROW puede variar según condiciones existentes
9. Credenciales en .env: nunca versionar

## 8. Decisiones abiertas (bloqueantes)

1. **Transacción:** ME12 directo / reporte Z vía SA38 / MEKP?
2. **Entrada:** Excel "Datos" o CSV `;`? Incluir WERKS (planta)?
3. **UI o CLI:** GUI PySide2 o línea de comandos?
4. **Modo test:** Primera pasada "solo validación"?
5. **RM06INP0:** Ejecutar automáticamente al final o paso manual?
6. **Python:** 3.8 (referencia) o 3.12+?
7. **Escalas/múltiples valideces:** Cambio simple o complejo?
8. **Sistema destino:** ECC/S/4HANA, sapgui/user_scripting, autorizaciones?

## 9. Criterios de aceptación

- Login/cierre sesión/cierre programa replican sapCondMassMod con mejoras
- Flujo ME12 replica IDs del VBA
- Validadores portan reglas del ABAP
- pytest en verde
- .env ignorado por git
- RM06INP0 documentada (ejecutada o paso manual)
- Sin credenciales reales en el repo
