# Implementation Plan: Retry wait control timing fix

**Branch:** `feature/retry-wait-control`
**Spec:** `docs/superpowers/specs/2026-08-04-retry-wait-control-design.md`
**File:** `script/me12_massmod.py`

---

## Tareas

### T1: Agregar función `wait_for_control`

**Ubicación:** Al inicio de `me12_massmod.py`, después de los imports y constantes (línea ~14), antes de la clase `SapMe12MassMod`.

**Código a agregar:**

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

**Validación:** La función debe estar visible globalmente (no dentro de la clase).

### T2: Reemplazar findById del botón Condiciones (línea 97)

**Antes:**
```python
self.session.findById("wnd[0]/tbar[1]/btn[8]").Press
```

**Después:**
```python
wait_for_control(self.session, "wnd[0]/tbar[1]/btn[8]", log_func=self.log).Press
```

### T3: Reemplazar findById de la tabla de precio (línea 108)

**Antes:**
```python
self.session.findById(precio_id).Text = nuevo_precio
```

**Después:**
```python
wait_for_control(self.session, precio_id, log_func=self.log).Text = nuevo_precio
```

---

## Checklist de validación

- [ ] `wait_for_control` está definida como función global (fuera de la clase)
- [ ] Línea 97 usa `wait_for_control` con `log_func=self.log`
- [ ] Línea 108 usa `wait_for_control` con `log_func=self.log`
- [ ] No hay cambios en `sap.py`, `main.py`, `validators.py`
- [ ] El código es sintácticamente válido (sin errores de indentación)
- [ ] Los delays existentes (`DELAY_AFTER_ENTER`, etc.) se mantienen intactos

## Notas

- No ejecutar pytest (no hay Python en el entorno de validación)
- La validación real es manual: ejecutar el script contra SAP y verificar que el error 619 desaparece
