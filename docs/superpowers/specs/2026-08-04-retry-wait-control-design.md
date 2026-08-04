# Design: Retry con espera activa para controles SAP GUI

**Fecha:** 2026-08-04
**Feature:** PYTHON_ME12_MASSCOND — Fix timing controls
**Status:** APPROVED

---

## Problema

El script Python de ME12 falla con error `619 - The control could not be found by id` al intentar presionar el botón de Condiciones (`wnd[0]/tbar[1]/btn[8]`). Los IDs son idénticos al VBA que funciona correctamente.

**Causa raíz:** Después de presionar Enter para validar los datos del info record, SAP necesita tiempo para cargar la siguiente pantalla. El Python ejecuta `findById` antes de que el control exista en el DOM de SAP GUI.

## Solución

Implementar **espera activa con retry** para los controles críticos del flujo ME12.

### Nueva función `wait_for_control`

```python
def wait_for_control(session, control_id, timeout=5.0, interval=0.2, log_func=None):
    """Reintenta findById hasta que el control exista o se agote el timeout."""
    start = time.time()
    attempts = 0
    while time.time() - start < timeout:
        try:
            ctrl = session.findById(control_id)
            if attempts > 0 and log_func:
                log_func(f"  Control '{control_id}' encontrado tras {attempts} intentos")
            return ctrl
        except Exception:
            attempts += 1
            time.sleep(interval)
    raise TimeoutError(
        f"Control '{control_id}' no encontrado tras {timeout}s ({attempts} intentos)"
    )
```

**Parámetros:**
- `session`: Objeto sesión SAP GUI
- `control_id`: ID del control (ej. `"wnd[0]/tbar[1]/btn[8]"`)
- `timeout`: Tiempo máximo de espera en segundos (default: 5.0)
- `interval`: Tiempo entre reintentos en segundos (default: 0.2)
- `log_func`: Función de log opcional (para diagnóstico)

**Comportamiento:**
1. Intenta `session.findById(control_id)`
2. Si falla, espera `interval` segundos y reintenta
3. Si tiene éxito, retorna el objeto del control
4. Si agota `timeout`, lanza `TimeoutError` con detalle de intentos

### Cambios en `_procesar_registro`

Reemplazar los `findById` críticos:

| Línea actual | Antes | Después |
|-------------|-------|---------|
| 97 | `self.session.findById("wnd[0]/tbar[1]/btn[8]").Press` | `wait_for_control(self.session, "wnd[0]/tbar[1]/btn[8]", log_func=self.log).Press` |
| 108 | `self.session.findById(precio_id).Text = nuevo_precio` | `wait_for_control(self.session, precio_id, log_func=self.log).Text = nuevo_precio` |

**Controles que NO necesitan retry** (tolerantes al timing):
- `wnd[0]/tbar[0]/okcd` (okcode field — siempre presente)
- `wnd[0]/usr/ctxtEINA-LIFNR`, `ctxtEINA-MATNR`, `ctxtEINE-EKORG` (campos de entrada — siempre presentes en pantalla ME12)
- `wnd[0]/sbar` (status bar — siempre presente)

### Logging de diagnóstico

Cuando el retry es exitoso después de múltiples intentos, se loguea:
```
  Control 'wnd[0]/tbar[1]/btn[8]' encontrado tras 3 intentos
```

Cuando el retry falla (timeout):
```
TimeoutError: Control 'wnd[0]/tbar[1]/btn[8]' no encontrado tras 5.0s (25 intentos)
```

## Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `script/me12_massmod.py` | Agregar función `wait_for_control()`, usar en líneas 97 y 108 |

**No se modifican:** `sap.py`, `main.py`, `validators.py`, ni ningún otro archivo.

## Testing

1. Ejecutar el script con el mismo Excel de prueba
2. Verificar que el log muestra "Login exitoso" y procesa los registros
3. Si hay retry, el log mostrará cuántos intentos tomó encontrar el control
4. Verificar que los registros se procesan sin error 619

## Notas

- El timeout de 5s es conservador — en SAP local típicamente responde en <1s
- El intervalo de 200ms evita saturar el COM sin notar demora
- La función es reutilizable para otros controles si se necesita en el futuro
