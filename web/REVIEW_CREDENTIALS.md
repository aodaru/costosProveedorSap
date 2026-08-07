# Review — Credenciales SAP (Web UI)

**Fecha:** 2026-08-07
**Revisor:** Agente Revisor (mimo-v2.5)
**Archivos revisados:**
- `web/server.py` (diff: 28 líneas añadidas/4 modificadas)
- `web/templates/index.html` (diff: 51 líneas añadidas)
- `web/.env.example` (diff: 5 líneas añadidas)

---

## 1. Correctness — ¿El override de globals funciona?

**Veredicto: ✅ PASS**

`script/sap.py` declara las credenciales como globals de módulo (líneas 18-22):
```python
system_sap = os.getenv("SYSTEM")
mandt = os.getenv("MANDT")
username = os.getenv("USER")
password = os.getenv("PASSWD")
language = os.getenv("LANGUAGE")
```

`sapLogin()` las lee como variables libres que resuelven al namespace global del módulo (líneas 69-75).

`web/server.py` hace `import sap as sap_module` y asigna:
```python
sap_module.username = username   # línea 210
sap_module.password = password   # línea 211
```

Esto modifica el dict de atributos del módulo `sap`. Cuando `sapLogin()` ejecuta `self.session.findById(...).text = username`, Python resuelve `username` contra los globals del módulo `sap` en tiempo de ejecución → **lee el valor overrideado**. Correcto.

**Nota:** La importación `from sap import SapGui` (línea 204) ejecuta el código de nivel de módulo de `sap.py`, incluyendo `load_dotenv()` y `os.getenv()`. Esto carga las variables de `script/.env` inicialmente, pero el override en líneas 209-213 ocurre inmediatamente después y antes de `sapLogin()` (línea 225). No hay conflicto.

---

## 2. Security — Manejo seguro de credenciales

**Veredicto: ⚠️ 1 ISSUE MENOR**

| Criterio | Estado | Detalle |
|---|---|---|
| Credenciales NO logueadas | ✅ | `_emit_log` solo envía mensajes genéricos ("Iniciando conexión con SAP...") |
| Credenciales NO persistidas | ✅ | Solo viven en memoria (globals del módulo `sap`), no se escriben a disco |
| Credenciales NO en respuestas HTTP | ✅ | `/execute` retorna `{"ok": True, "message": "Ejecución iniciada"}` — sin eco |
| Password enmascarada en UI | ✅ | `type="password"` en `index.html` línea 160 |
| autocomplete="off" | ✅ | Ambos campos lo tienen (líneas 158-160) |
| username strip() server-side | ✅ | Línea 290: `(body.get("username") or "").strip()` |

**⚠️ ISSUE MENOR: Desviación de spec `mission.md` línea 60**

> "Credenciales SAP solo en `.env` (no trackeado); **la web no pide ni almacena credenciales de usuario**."

La implementación solicita usuario/contraseña desde el formulario web. Esto contradice literalmente la regla de oro heredada. Sin embargo:
- El usuario/stakeholder solicitó explícitamente este cambio (el prompt de review describe este diseño como intencional).
- El enfoque es **más seguro** que una cuenta de servicio compartida: cada usuario usa su propia identidad SAP (mejor trazabilidad en auditoría).
- Las variables fijas (MANDANT, LANGUAGE, SYSTEM) siguen en `.env` y no se exponen al usuario.

**Recomendación:** Actualizar `mission.md` línea 60 para reflejar el nuevo diseño. No es bloqueante para el review.

---

## 3. Constraints — `script/` intacto

**Veredicto: ✅ PASS**

```
$ git diff -- script/
(no output)
```

Confirmado: cero modificaciones en `script/`.

---

## 4. UX — Campos de formulario

**Veredicto: ✅ PASS**

**Estilo (CSS):**
- Clase `.credentials-row` con flex layout consistente con `.row` existente (líneas 37-61)
- Focus state con borde azul y sombra sutil (líneas 57-61), consistente con el patrón del resto de la UI
- Labels con `font-weight: 600` y `color: #555` — legible y alineado visualmente

**Validación client-side (JS, líneas 319-329):**
- Trim del username antes de validar
- Mensajes de error claros: "Error: ingrese el usuario SAP" / "Error: ingrese la contraseña SAP"
- Botón se deshabilita si falta alguno

**Validación server-side (líneas 293-300):**
- Username vacío → 400 + mensaje claro
- Password vacío → 400 + mensaje claro

**Nota:** No hay indicador visual de campos obligatorios (asterisco `*`). Mínimo, no bloqueante.

---

## 5. Error handling — Variables .env faltantes

**Veredicto: ✅ PASS (con observación)**

```python
sap_module.mandt = os.environ.get("SAP_MANDANT", "")
sap_module.language = os.environ.get("SAP_LANG", "")
sap_module.system_sap = os.environ.get("SAP_SYSTEM", "")
```

Si alguna variable falta en `web/.env`, el valor por defecto es `""`. El flujo de error es:

1. `sapLogin()` intenta abrir conexión con `system_sap=""` → falla con excepción
2. Excepción atrapada en el `try/except` de `_run_sap_process` (línea 253)
3. Se emite log de error al usuario vía WebSocket
4. Badge cambia a "Error"
5. `finally` ejecuta `_do_cleanup()` → SAP se cierra

**Observación:** El error solo se detecta al momento del login, no al iniciar el servidor. Sería mejor UX validar la existencia de `SAP_MANDANT`, `SAP_LANG`, `SAP_SYSTEM` en el startup del servidor (similar a como se valida `FLASK_SECRET_KEY` en líneas 28-33). No es bloqueante pero mejora la experiencia de deployment.

---

## 6. Mission/Tech-Stack compliance

**Veredicto: ✅ PASS**

| Requisito | Estado | Evidencia |
|---|---|---|
| Stack: Flask + Flask-SocketIO + HTML/CSS/JS embebido | ✅ | Sin frameworks CSS ni dependencias nuevas |
| `script/` read-only | ✅ | `git diff -- script/` vacío |
| Imports perezosos de `script/` | ✅ | `from sap import SapGui` dentro de `_run_sap_process` (línea 204) |
| Ejecución única | ✅ | Lock check en línea 279: `if SERVER_STATUS == "processing"` |
| Credenciales en `.env` (las fijas) | ✅ | SAP_SYSTEM, SAP_MANDANT, SAP_LANG en `.env.example` |
| No auth framework | ✅ | Sin dependencias de autenticación agregadas |
| No Docker/REST externa | ✅ | Solo endpoints internos necesarios |
| python-dotenv para .env | ✅ | `load_dotenv()` al inicio de `server.py` (línea 17) |

---

## Resumen de Issues

### BLOCKERS: 0

### CRITICAL: 0

### MINOR (no bloqueantes):

1. **Spec deviation** (`mission.md:60`): La regla dice "la web no pide credenciales de usuario" pero la implementación sí lo hace. Actualizar spec para reflejar la decisión.
2. **Startup validation**: `SAP_MANDANT`, `SAP_LANG`, `SAP_SYSTEM` no se validan al arrancar el servidor. Un deployment sin estas variables fallará silenciosamente hasta el primer login. Recomendación: validarlas en `__main__` igual que `FLASK_SECRET_KEY`.
3. **`.env.example` comment**: Línea 7 dice "fijos, no se ingresan desde el formulario" — la palabra "fijos" es correcta (son las 3 variables de .env), pero puede confundir. Considerar: "Variables de conexión SAP fijas (las credenciales de usuario se ingresan desde el formulario)".

---

## Veredicto Final

# APPROVED

La implementación es correcta, segura dentro del contexto de red interna, y respeta las restricciones del proyecto. Los 3 issues menores son mejoras recomendadas, no bloqueantes.
