# Requisitos — Web UI ME12

**Fecha:** 2026-08-05
**Spec de referencia:** `docs/superpowers/specs/2026-08-05-web-ui-me12-design.md`

---

## Alcance

### Incluido

- **Solo la capa web**: servidor HTTP + WebSocket, página única de carga/ejecución
- Ciclo de vida SAP automatizado: login → ejecución → logout/cierre
- Logs en tiempo real vía WebSocket
- Reutilizar `script/` como librería de solo lectura
- Despliegue como servicio Windows con auto-arranque (nssm)
- Todo el código nuevo vive en `web/` en la raíz del repo

### No incluido

- ❌ Modificaciones a `script/` (automatización congelada)
- ❌ Reporte ABAP (`src/`)
- ❌ Autenticación / LDAP (red interna, no requerida)
- ❌ Historial de cargas / log de auditoría
- ❌ Ejecuciones concurrentes (una corrida a la vez)
- ❌ Docker / contenedorización
- ❌ API REST para acceso programático
- ❌ Tests automatizados de la capa web
- ❌ Framework CSS / assets externos

---

## Decisiones

| ID | Decisión | Racional | Alternativa descartada |
|----|----------|----------|------------------------|
| D1 | Código nuevo solo en `web/` | `script/` está congelado y terminado | Poner `web_server.py` dentro de `script/` (spec §8) |
| D2 | Flask + Flask-SocketIO | Stack simple, sin build step, alineado con Python 3.8 | FastAPI, Django, frameworks CSS |
| D3 | HTML/CSS/JS embebido | Cero tooling frontend, página única | React, Vue, Tailwind, Bootstrap |
| D4 | Import perezoso de `script/` | `sap.py` importa `win32com` a nivel módulo; falla en Linux | Import a nivel módulo |
| D5 | Sin autenticación | Red interna; decisión explícita del stakeholder | LDAP, OAuth, Sesiones |
| D6 | Una ejecución a la vez | Lock en servidor; simplifica manejo de estado | Cola de trabajos, concurrencia |
| D7 | nssm para deploy | Servicio Windows nativo, auto-arranque | Docker, systemd (Linux) |

---

## Contexto

- **Runtime:** Windows 10 VM con SAP GUI instalado
- **Lenguaje:** Python 3.8 (alineado con `script/mise.toml`)
- **Desarrollo:** máquina Linux actual
- **Ejecución real:** VM Windows (`http://vm-windows:5000`)
- **Credenciales:** solo en `.env` (no trackeado)
- **Dependencias existentes:** pywin32, python-dotenv, pandas, openpyxl (ya instaladas en VM)

### Estructura de archivos a crear

```
web/
├── server.py            # Flask + SocketIO + rutas (/ /upload /execute /status)
├── templates/
│   └── index.html       # UI página única (CSS/JS inline)
└── requirements.txt
```

### Patrón de integración con `script/`

`web/server.py` agrega `script/` al `sys.path` e importa `SapGui` de forma **perezosa (dentro de las funciones)**, porque `sap.py` importa `win32com` a nivel módulo y fallaría al importar en Linux.

---

## Dependencias

- **Fase 0 (Scaffolding):** Crear estructura `web/` y servidor mínimo
- **Fase 1 (Página estática):** UI completa sin funcionalidad
- **Fase 2 (Upload + validación):** Conexión con `validators.py` de `script/`
- **Fase 3 (Ejecución SocketIO):** Integración completa con `SapGui`
- **Fase 4 (Robustez):** Manejo de errores y auto-reconexión
- **Fase 5 (Servicio Windows):** Deploy con nssm
- **Fase 6 (UAT):** Validación con usuario real

---

## Riesgos identificados

| Riesgo | Mitigación |
|--------|------------|
| `win32com` falla al importar en Linux | Import perezoso dentro de funciones; solo se importa en la VM |
| SAP GUI no responde / sesión muerta | Auto-reconexión en fase 4; `try/finally` para limpieza |
| Excel temporal no se borra | Limpieza obligatoria tras cada corrida; `safe_close_window()` |
| Servicio Windows cae tras reboot | nssm con auto-arranque; verificación en fase 5 |
| Credenciales expuestas | Solo en `.env`; nunca en código, logs ni HTTP |

---

## Reglas de oro (no negociables)

1. **`script/` es read-only.** `git diff -- script/` vacío en cada merge.
2. **Credenciales solo en `.env`** (no trackeado).
3. **Una ejecución a la vez** y limpieza obligatoria tras cada corrida.
4. **Desarrollo en Linux, ejecución en Windows:** imports perezosos de `script/`.
5. **Stack fijo:** Flask + Flask-SocketIO + HTML/CSS/JS embebido.
