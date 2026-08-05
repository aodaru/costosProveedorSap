# AGENTS.md — Guía para agentes

## Dónde están las specs

La **constitución del proyecto** (fuente de verdad para planificar e implementar) vive en:

```
specs/
├── mission.md      # Misión, alcance, audiencia, criterios de éxito
├── tech-stack.md   # Stack confirmado, gaps, restricciones técnicas
└── roadmap.md      # Fases de implementación (0–6) con criterios de "done"
```

**Trabaja siempre contra `specs/`.** Los archivos en `docs/superpowers/specs/` son specs históricos de diseño (ya aprobados/implementados); consúltalos solo como referencia, nunca como plan vigente. No existe `TODO.md`.

## Reglas innegociables al implementar

1. **`script/` es read-only.** La automatización ME12 está terminada. Nunca edites archivos ahí; úsalo como librería (`SapGui.sapLogin/massive_change/safe_close_window` ya aceptan `log_func`).
2. **Código nuevo solo en `web/`** (raíz del repo), no dentro de `script/`.
3. **Imports perezosos de `script/`**: `sap.py` importa `win32com` a nivel módulo → importa dentro de funciones, nunca a nivel módulo en `web/` (el desarrollo es en Linux; la ejecución, en la VM Windows).
4. **Credenciales solo en `.env`** (no trackeado). Nunca en código, logs ni respuestas HTTP.
5. **Una ejecución a la vez** y limpieza obligatoria tras cada corrida (borrar Excel temporal + `safe_close_window()` incluso ante error).
6. Stack fijo: Flask + Flask-SocketIO + HTML/CSS/JS embebido. **No agregar** framework CSS, auth, Docker, ni REST API (fuera de alcance — ver `specs/mission.md` §3).

## Contexto rápido

- **Qué se construye:** interfaz web para que compras ejecute la actualización masiva de precios ME12 en SAP cargando un Excel desde el navegador (spec de diseño: `docs/superpowers/specs/2026-08-05-web-ui-me12-design.md`).
- **Desarrollo:** esta máquina (Linux). **Ejecución real:** VM Windows 10 con SAP GUI (`http://vm-windows:5000`).
- **Deploy:** servicio Windows vía nssm (fase 5 del roadmap).
- Documentación SAP de fondo: `README.md` y `research/` (tablas de condiciones, RM06INP0, advertencias críticas).
