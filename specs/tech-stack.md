# Tech Stack — Web UI ME12

**Fecha:** 2026-08-05
**Fuente:** Spec aprobado `docs/superpowers/specs/2026-08-05-web-ui-me12-design.md` §3, §10, §11 + entrevista con stakeholders.

---

## 1. Stack confirmado (simple, sin sorpresas)

| Capa | Tecnología | Notas |
|---|---|---|
| Runtime | **Windows 10 VM** con SAP GUI instalado | Obligatorio: `win32com`/`pywin32` solo existen en Windows |
| Lenguaje | **Python 3.8** | Alineado con `script/mise.toml` |
| Web server | **Flask ≥ 3.0** | HTTP API + serve de la página |
| Tiempo real | **Flask-SocketIO ≥ 5.3** (+ python-socketio ≥ 5.10, python-engineio ≥ 4.8) | Eventos `log` / `status` / `complete` |
| Frontend | **HTML/CSS/JS embebido** (página única) | Sin build step, sin framework CSS, sin assets externos |
| Backend SAP | `script/` importado como librería (**solo lectura**) | `SapGui.sapLogin/massive_change/safe_close_window` ya exponen `log_func` |
| Validación Excel | `script/validators.py` (reutilizado tal cual) | La web no reimplementa reglas |
| Config | `.env` existente (`SYSTEM/MANDT/USER/PASSWD/LANGUAGE`) | Sin cambios; nunca commiteado |
| Deploy | **nssm** → servicio Windows con auto-arranque | Gap a cerrar (ver §3) |

### requirements.txt (nuevo, en `web/`)

```
flask>=3.0
flask-socketio>=5.3
python-socketio>=5.10
python-engineio>=4.8
```

Las dependencias existentes de `script/` (pywin32, python-dotenv, pandas, openpyxl) se asumen ya instaladas en la VM.

## 2. Estructura de archivos (código nuevo)

> **Desviación deliberada del spec §8:** el spec ubicaba `web_server.py` dentro de `script/`. Como `script/` está congelado (decisión del stakeholder), todo lo nuevo vive en `web/` en la raíz.

```
web/
├── server.py            # Flask + SocketIO + rutas (/ /upload /execute /status)
├── templates/
│   └── index.html       # UI página única (CSS/JS inline)
└── requirements.txt
```

**Patrón de integración con `script/`:** `web/server.py` agrega `script/` al `sys.path` e importa `SapGui` de forma **perezosa (dentro de las funciones)**, porque `sap.py` importa `win32com` a nivel módulo y fallaría al importar en Linux (máquina de desarrollo). El servidor solo se *ejecuta* en la VM Windows.

## 3. Gaps del tech stack

### Gap a cerrar en esta fase

| Gap | Resolución | Fase del roadmap |
|---|---|---|
| El servidor hoy no corre como servicio: si la VM reinicia, la web queda caída | Instalar con **nssm** (`nssm install ME12WebUI`), auto-arranque, documentar runbook (install/start/stop/logs) | Fase 5 |

### Gaps evaluados y descartados explícitamente (no se cierran en esta fase)

| Gap descartado | Motivo |
|---|---|
| Tests automatizados de la capa web (endpoints/SocketIO) | No seleccionado por el stakeholder; la verificación es manual en la VM según spec §15 |
| Framework CSS / assets externos (Tailwind, Bootstrap) | Se confirma CSS inline para cero tooling frontend |
| Autenticación | Red interna; fuera de alcance (mission.md §3) |
| Auditoría, concurrencia, Docker, REST API | Fuera de alcance (mission.md §3) |

## 4. Restricciones técnicas

1. **`script/` es read-only.** Cualquier adaptación se hace en `web/` (wrappers, callbacks), nunca editando archivos de `script/`.
2. **Una ejecución a la vez.** Lock en servidor: mientras `status = processing`, `/execute` rechaza nuevas corridas.
3. **Limpieza obligatoria tras cada corrida:** borrar el Excel temporal y ejecutar `safe_close_window()` (logoff + `taskkill saplogon.exe`) incluso ante error.
4. **Credenciales** solo via `.env`; jamás en código, logs ni respuestas HTTP.
5. **Desarrollo en Linux, ejecución en Windows:** nada de `import win32com` a nivel módulo en `web/`; los imports de `script/` son perezosos.
