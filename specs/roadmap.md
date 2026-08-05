# Roadmap — Web UI ME12

**Fecha:** 2026-08-05
**Base:** No existe `TODO.md` en el repo; el orden de implementación se deriva del spec aprobado `docs/superpowers/specs/2026-08-05-web-ui-me12-design.md` y de las decisiones de `mission.md` / `tech-stack.md`.

> Regla transversal de todas las fases: **`script/` no se modifica** (`git diff -- script/` vacío en cada merge).

---

## Fase 0 — Scaffolding `web/`

- Crear `web/` con `requirements.txt` y `server.py` mínimo (Flask sirviendo "Hola ME12").
- Wiring `sys.path` → `script/` con import perezoso de `SapGui`.
- **Done cuando:** `pip install -r web/requirements.txt && python web/server.py` responde en `:5000` en la VM, sin tocar SAP.

## Fase 1 — Página única estática

- `web/templates/index.html`: título, selector de archivo, botón Ejecutar (deshabilitado), badge de estado "● Listo", panel de log vacío, link "Descargar Plantilla Excel" (sirve `script/template_me12.xlsx` read-only).
- `GET /` y `GET /status` (stub que responde `ready`).
- **Done cuando:** la página se ve completa en el navegador; sin funcionalidad aún.

## Fase 2 — Upload + validación

- `POST /upload`: recibe el Excel, lo guarda temporal, corre `validators.validate_excel()` (importado de `script/`).
- Errores de validación se muestran en el panel de log; si valida OK, se habilita **Ejecutar**.
- **Done cuando:** un Excel inválido muestra errores claros y uno válido habilita el botón. Sin conexión SAP todavía.

## Fase 3 — Ejecución con logs en vivo (SocketIO)

- `POST /execute`: lanza `sapLogin(log_func=emit)` + `massive_change(path, log_func=emit)` en thread de fondo; eventos `log`, `status` (`ready|processing|error`), `complete` (`OK|ERROR` + resumen).
- Lock de ejecución única: `/execute` rechaza si `status = processing`.
- Al terminar (éxito o excepción): `safe_close_window()`, borrar temporal, badge vuelve a **Listo**.
- **Done cuando:** corrida real en la VM vista desde otro PC de la red, con logs en tiempo real y cierre de SAP al final.

## Fase 4 — Robustez del ciclo de vida SAP

- Auto-reconexión: si la sesión SAP murió, la siguiente ejecución relanza `sapLogin` sin intervención.
- Matriz de errores del spec §12: SAP no instalado (fallo claro al iniciar), login fallido, Excel inválido, desconexión, error de ejecución → badge rojo + log + cierre de SAP garantizado (`try/finally`).
- **Done cuando:** se fuerzan los 5 escenarios de error y la UI siempre termina en estado consistente (Listo o Error, SAP cerrado, sin temporales huérfanos).

## Fase 5 — Servicio Windows (cierra el gap de deploy)

- Instalación con nssm: `nssm install ME12WebUI python web/server.py`, `nssm start ME12WebUI`, auto-arranque tras reboot de la VM.
- Runbook mínimo en `web/` o README: install / start / stop / logs / update.
- **Done cuando:** se reinicia la VM y `http://vm-windows:5000` responde solo, sin intervención manual.

## Fase 6 — UAT con compras y cierre

- Prueba de aceptación con un usuario real del equipo de compras (checklist spec §15: cargar, ejecutar, ver logs, cierre de SAP, badge Listo).
- Verificación final: `git diff -- script/` vacío; README actualizado con la URL y el runbook.
- **Done cuando:** compras aprueba la corrida de punta a punta y la fase se da por cerrada.

---

## Backlog explícitamente fuera de este roadmap

Autenticación · historial/auditoría · ejecuciones concurrentes · Docker · API REST · framework CSS · tests automatizados de la capa web. (Ver `mission.md` §3 y `tech-stack.md` §3.)
