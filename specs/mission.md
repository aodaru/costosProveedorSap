# Misión — Web UI para Actualización Masiva ME12

**Fecha:** 2026-08-05
**Estado:** APROBADO (entrevista con stakeholders)
**Spec de referencia:** `docs/superpowers/specs/2026-08-05-web-ui-me12-design.md` (APPROVED)

---

## 1. Misión

Permitir que el **equipo de compras** ejecute la actualización masiva del precio neto (PB00/PB01) del info record de compras en SAP **desde un navegador web**, cargando un archivo Excel, sin necesidad de acceder a la VM Windows ni operar la GUI de escritorio.

## 2. Problema

La automatización ME12 existe y funciona (`script/`, Python + SAP GUI Scripting sobre win32com), pero es una aplicación de escritorio (PySide2) que solo puede ejecutarse dentro de la VM Windows donde está instalado SAP GUI. Esto obliga al usuario a entrar a la VM, manejar credenciales y operar la sesión SAP manualmente.

## 3. Alcance de esta fase

### En alcance

- **Solo la capa web**: servidor HTTP + WebSocket, página única de carga/ejecución, ciclo de vida SAP automatizado (login → ejecución → logout/cierre), logs en tiempo real.
- Reutilizar `script/` **como librería de solo lectura**: `SapGui.sapLogin()`, `SapGui.massive_change()` y `SapGui.safe_close_window()` ya aceptan `log_func` — la capa web se conecta por esos callbacks **sin modificar ningún archivo de `script/`**.
- Despliegue como **servicio Windows con auto-arranque** en la VM (nssm).
- Todo el código nuevo vive en un directorio nuevo (`web/` en la raíz del repo), no dentro de `script/`.

### Fuera de alcance (confirmado con stakeholders)

- ❌ Modificaciones a `script/` (la automatización está terminada y congelada).
- ❌ Reporte ABAP (`src/`) — vía alternativa, no relacionada con esta fase.
- ❌ Autenticación / LDAP (red interna, no requerida).
- ❌ Historial de cargas / log de auditoría.
- ❌ Ejecuciones concurrentes (una corrida a la vez).
- ❌ Docker / contenedorización.
- ❌ API REST para acceso programático.

## 4. Audiencia objetivo

| Aspecto | Decisión |
|---|---|
| Usuarios | Equipo de compras |
| Acceso | Red interna únicamente: `http://vm-windows:5000` |
| Autenticación | Ninguna (decisión explícita del stakeholder) |
| Concurrencia | 1 ejecución a la vez; el badge de estado bloquea nuevas corridas |
| Datos | Excel según `script/template_me12.xlsx`; temporales borrados tras cada ejecución |

## 5. Criterios de éxito

1. Un usuario de compras abre `http://vm-windows:5000`, selecciona el Excel y presiona **Ejecutar** — sin tocar la VM.
2. Los logs de la corrida ME12 se ven en tiempo real en el navegador (WebSocket).
3. Al terminar (OK o error), SAP cierra sesión y `saplogon.exe` queda terminado; el badge vuelve a **Listo**.
4. Si SAP se cae entre corridas, la siguiente ejecución reconecta automáticamente.
5. El servidor sobrevive reinicios de la VM (servicio Windows con auto-arranque).
6. `git diff` sobre `script/` vacío al final de la fase — la automatización existente queda intacta.

## 6. Reglas de oro heredadas (no negociables)

Heredadas del README y reviews del proyecto:

- La escritura de precios la hace **únicamente** la lógica existente de `script/` (SAP GUI Scripting sobre ME12). La capa web **nunca** toca SAP directamente, ni SQL, ni BAPIs.
- Credenciales SAP solo en `.env` (no trackeado); la web no pide ni almacena credenciales de usuario.
- Tras la corrida corresponde ejecutar `RM06INP0` en SAP (manual, fuera de esta automatización) — documentado en `script/scripts/README_python_script.md`.
