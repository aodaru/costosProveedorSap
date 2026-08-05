# Validación — Web UI ME12

**Feature:** Web UI para Actualización Masiva ME12
**Spec de referencia:** `specs/mission.md` §5 (Criterios de éxito)

---

## Estado de la fase

**⬜ PENDIENTE**

---

## Criterios de éxito

### 1. Funcionalidad básica

- [ ] `http://vm-windows:5000` responde y muestra la página completa
- [ ] Selector de archivo permite cargar Excel
- [ ] Botón Ejecutar está deshabilitado hasta que Excel valide OK
- [ ] Badge de estado muestra "● Listo" al inicio
- [ ] Panel de log muestra mensajes de validación y ejecución
- [ ] Link "Descargar Plantilla Excel" funciona

### 2. Upload y validación

- [ ] Excel inválido muestra errores claros en el panel de log
- [ ] Excel válido habilita el botón Ejecutar
- [ ] Temporal se borra tras cada upload

### 3. Ejecución SAP

- [ ] Login automático a SAP funciona
- [ ] Logs de ejecución se ven en tiempo real (WebSocket)
- [ ] Badge cambia a "● Procesando" durante ejecución
- [ ] Al terminar (OK o error): SAP cierra sesión
- [ ] `saplogon.exe` queda terminado tras ejecución
- [ ] Badge vuelve a "● Listo" al finalizar
- [ ] Temporal se borra tras ejecución

### 4. Robustez

- [ ] Si SAP se cae, la siguiente ejecución reconecta automáticamente
- [ ] Si el Excel es inválido, se muestra error y SAP se cierra
- [ ] Si hay error de ejecución, SAP se cierra y badge muestra error
- [ ] Lock de ejecución única funciona (rechaza si status = processing)

### 5. Deploy

- [ ] Servicio Windows (nssm) está instalado y corriendo
- [ ] Auto-arranque tras reboot de VM funciona
- [ ] `http://vm-windows:5000` responde tras reinicio sin intervención

### 6. UAT

- [ ] Usuario real de compras ejecuta corrida de punta a punta
- [ ] Checklist §15 completo:
  - Cargar Excel
  - Ejecutar
  - Ver logs en tiempo real
  - Cierre de SAP
  - Badge vuelve a Listo
- [ ] `git diff -- script/` vacío
- [ ] README actualizado con URL y runbook

---

## Criterios de éxito del spec (mission.md §5)

1. [ ] Un usuario de compras abre `http://vm-windows:5000`, selecciona el Excel y presiona **Ejecutar** — sin tocar la VM.
2. [ ] Los logs de la corrida ME12 se ven en tiempo real en el navegador (WebSocket).
3. [ ] Al terminar (OK o error), SAP cierra sesión y `saplogon.exe` queda terminado; el badge vuelve a **Listo**.
4. [ ] Si SAP se cae entre corridas, la siguiente ejecución reconecta automáticamente.
5. [ ] El servidor sobrevive reinicios de la VM (servicio Windows con auto-arranque).
6. [ ] `git diff` sobre `script/` vacío al final de la fase — la automatización existente queda intacta.

---

## Criterio de merge a main

- [ ] Todos los criterios de éxito marcados
- [ ] PR abierto y revisado
- [ ] Validación manual ejecutada en la VM
- [ ] `git diff -- script/` vacío
- [ ] README actualizado

---

## Anti-criterios (lo que NO debe pasar)

- ❌ `script/` se modifica en algún commit
- ❌ Credenciales aparecen en código, logs o respuestas HTTP
- ❌ Excel temporal queda huérfano tras ejecución
- ❌ `saplogon.exe` queda corriendo tras ejecución
- ❌ Servicio Windows no sobrevive reboot
- ❌ Dos ejecuciones corren simultáneamente
- ❌ UI muestra errores sin contexto al usuario

---

## Comandos de verificación

```bash
# Verificar que script/ no se modificó
git diff main -- script/

# Verificar estructura web/
ls -la web/
ls -la web/templates/

# Verificar que el servidor arranca (en VM)
cd web && pip install -r requirements.txt && python server.py

# Verificar servicio Windows (en VM)
nssm status ME12WebUI

# Verificar que la web responde (en VM)
curl http://localhost:5000
curl http://localhost:5000/status
```
