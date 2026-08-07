# SAP Client Migration — Done

**Fecha:** 2026-08-07
**Estado:** COMPLETADO

## Archivos creados

### `web/sap_client.py` (~370 líneas)

Módulo SAP autocontenido que reemplaza la dependencia de `script/sap.py` y `script/me12_massmod.py`.

| Método | Origen | Descripción |
|---|---|---|
| `__init__(system, mandt, username, password, language)` | Nuevo | Credenciales explícitas como parámetros (no globals) |
| `connect(log_func)` | `script/sap.py` → `sapLogin()` (parte 1) | Abre saplogon.exe, obtiene SAPGUI COM, OpenConnection |
| `login(log_func)` | `script/sap.py` → `sapLogin()` (parte 2) | Llena mandt/user/passwd/idioma, maneja popup "already open" |
| `run_me12(file_path, log_func)` | `script/me12_massmod.py` → `run_me12_massmod()` | Valida Excel, itera registros, llama `_procesar_registro` |
| `_procesar_registro(row, index, log_func)` | `script/me12_massmod.py` → `_procesar_registro()` | Lógica completa ME12: navigate, fill, F8, popup, precio, save |
| `close(log_func)` | `script/sap.py` → `safe_close_window()` | CloseSession + taskkill saplogon.exe |
| `_compute_validity_dates()` | `me12_massmod.py` | Reglas de fecha desde/hasta |
| `_parse_date()` | `me12_massmod.py` | dd.mm.yyyy → YYYYMMDD |
| `_format_date_sap()` | `me12_massmod.py` | YYYYMMDD → dd.mm.yyyy |
| `_wait_for_control()` | `me12_massmod.py` | Retry loop para findById |

**Diferencias clave vs. código original:**
1. `win32com` y `pywintypes` importados **DENTRO** de métodos (no a nivel módulo)
2. `validators` importado **DENTRO** de `run_me12()` (no a nivel módulo)
3. Credenciales via `__init__()` explícito, no via globals de módulo
4. `log_func` se pasa explícitamente a todos los métodos
5. Delays y constants son atributos de instancia, no globals

## Archivos modificados

### `web/server.py` (26 líneas cambiadas)

| Cambio | Antes | Después |
|---|---|---|
| Import SAP | `from sap import SapGui` + `import sap as sap_module` | `from sap_client import SapClient` |
| Import pywintypes | `try: import pywintypes` (líneas 151-153) | Eliminado (se importa dentro de `sap_client.py` y localmente en ME12 catch) |
| Credenciales | Monkey-patching de globals `sap_module.mandt = ...` | `SapClient(system=..., mandt=..., username=..., ...)` |
| Login | `sap.sapLogin(log_func=...)` | `sap.connect(log_func=...)` + `sap.login(log_func=...)` |
| ME12 | `sap.massive_change(file_path, log_func=...)` | `sap.run_me12(file_path, log_func=...)` |
| Cierre | `sap.safe_close_window(log_func=...)` | `sap.close(log_func=...)` |
| sys.path comment | "para importar SapGui y validators" | "SOLO para validators (import perezoso en upload)" |
| Docstring | Menciona `script/sap.py` | Menciona `sap_client.py` |

## Archivos NO modificados

- `script/sap.py` — intacto
- `script/me12_massmod.py` — intacto
- `script/validators.py` — intacto
- `script/template_me12.xlsx` — intacto

Verificación: `git diff -- script/` → vacío.

## Dependencias restantes en `script/`

| Archivo | Importado por | Propósito | Acción futura |
|---|---|---|---|
| `validators.py` | `server.py` (upload) + `sap_client.py` (run_me12) | Validación Excel | Migrar a `web/validators.py` en fase futura |
| `template_me12.xlsx` | `server.py` (download) | Plantilla descargable | Mover a `web/templates/` en fase futura |

## Flujo nuevo

```
server.py                          sap_client.py                     SAP GUI
    │                                   │                               │
    ├─ POST /execute(username, pwd)     │                               │
    │   └─ start_background_task        │                               │
    │                                   │                               │
    └─ _run_sap_process(path, u, p)    │                               │
        ├─ SapClient(system, mandt...)  │                               │
        ├─ sap.connect(log_func=emit)   │                               │
        │   ├─ _open_sap_logon()────────┼──────► subprocess.Popen       │
        │   └─ GetObject("SAPGUI")──────┼──────► win32com.client       │
        │   └─ OpenConnection()─────────┼──────► SAP Logon             │
        │                               │                               │
        ├─ sap.login(log_func=emit)     │                               │
        │   └─ fill mandt/user/pwd──────┼──────► SAP Login Screen      │
        │                               │                               │
        ├─ sap.run_me12(path, emit)     │                               │
        │   ├─ validate_excel()          │                               │
        │   ├─ for row in data:          │                               │
        │   │   └─ _procesar_registro()─┼──────► /nME12 → fill → save  │
        │                               │                               │
        └─ sap.close(log_func=emit)     │                               │
            ├─ CloseSession("ses[0]")────┼──────► SAP session close     │
            └─ taskkill saplogon.exe     │                               │
```

## Testing en VM (pendiente)

- [ ] `python web/server.py` arranca sin errores de import
- [ ] `POST /upload` funciona (validators desde script/ via sys.path)
- [ ] `POST /execute` ejecuta login → ME12 → cierre correctamente
- [ ] Logs en tiempo real vía SocketIO funcionan
- [ ] Cierre de SAP funciona tras cada ejecución (éxito y error)
