# Plan — Web UI ME12

Plan secuencial para la implementación de la interfaz web para actualización masiva de precios ME12.
Cada grupo debe completarse antes de pasar al siguiente.
Marcar checkboxes al ejecutar.

**Referencia:** `specs/roadmap.md` (fases 0-6)

---

## Grupo 0: Scaffolding `web/`

1. [x] Crear directorio `web/` con estructura básica
2. [x] Crear `web/requirements.txt` con dependencias Flask
3. [x] Crear `web/server.py` mínimo (Flask sirviendo "Hola ME12")
4. [x] Configurar `sys.path` → `script/` con import perezoso de `SapGui`
5. [ ] Verificar que `pip install -r web/requirements.txt && python web/server.py` responde en `:5000`

## Grupo 1: Página única estática

1. [x] Crear `web/templates/index.html` con:
   - Título de la aplicación
   - Selector de archivo
   - Botón Ejecutar (deshabilitado)
   - Badge de estado "● Listo"
   - Panel de log vacío
   - Link "Descargar Plantilla Excel" (sirve `script/template_me12.xlsx` read-only)
2. [x] Implementar `GET /` para servir la página
3. [x] Implementar `GET /status` (stub que responde `ready`)
4. [x] Verificar que la página se ve completa en el navegador

## Grupo 2: Upload + validación

1. [x] Implementar `POST /upload`:
   - Recibir el Excel
   - Guardar temporal
   - Correr `validators.validate_excel()` (importado de `script/`)
2. [x] Mostrar errores de validación en el panel de log
3. [x] Habilitar botón Ejecutar si valida OK
4. [x] Verificar con Excel inválido (muestra errores) y válido (habilita botón)

## Grupo 3: Ejecución con logs en vivo (SocketIO)

1. [x] Configurar Flask-SocketIO en `server.py`
2. [x] Implementar `POST /execute`:
   - Lanzar `sapLogin(log_func=emit)` + `massive_change(path, log_func=emit)` en thread de fondo
   - Emitir eventos `log`, `status` (`ready|processing|error`), `complete` (`OK|ERROR` + resumen)
3. [x] Implementar lock de ejecución única: `/execute` rechaza si `status = processing`
4. [x] Al terminar (éxito o excepción): `safe_close_window()`, borrar temporal, badge vuelve a **Listo**
5. [ ] Verificar corrida real en la VM con logs en tiempo real  # pendiente: prueba real en VM

## Grupo 4: Robustez del ciclo de vida SAP

1. [x] Implementar auto-reconexión: si la sesión SAP murió, relanzar `sapLogin` sin intervención
2. [x] Implementar matriz de errores (spec §12):
   - SAP no instalado (fallo claro al iniciar)
   - Login fallido
   - Excel inválido
   - Desconexión
   - Error de ejecución
3. [x] Verificar que badge siempre termina en rojo + log + cierre de SAP garantizado (`try/finally`)
4. [ ] Forzar los 5 escenarios de error y verificar estado consistente  # pendiente: prueba real en VM

## Grupo 5: Servicio Windows (nssm)

1. [x] Instalar con nssm: `nssm install ME12WebUI python web/server.py` (documentado en RUNBOOK.md)
2. [x] Configurar auto-arranque: `nssm start ME12WebUI` (documentado en RUNBOOK.md)
3. [x] Crear runbook mínimo en `web/` o README:
   - install / start / stop / logs / update
4. [ ] Verificar que reinicio de VM mantiene `http://vm-windows:5000` activo  # pendiente: prueba real en VM

## Grupo 6: UAT con compras y cierre

1. [ ] Prueba de aceptación con usuario real del equipo de compras
2. [ ] Checklist spec §15:
   - Cargar Excel
   - Ejecutar
   - Ver logs en tiempo real
   - Cierre de SAP
   - Badge vuelve a Listo
3. [x] Verificar `git diff -- script/` vacío
4. [x] Actualizar README con URL y runbook
5. [ ] Compras aprueba corrida de punta a punta

## Grupo Documentación y merge

- [x] Commit de todos los cambios
- [ ] Push de la rama
- [ ] Crear PR
- [ ] Validar criterios de éxito
- [ ] Mergear y limpiar
