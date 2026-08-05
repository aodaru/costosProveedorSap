# Checklist de Aceptación de Usuario (UAT) — Web UI ME12

**Proposito:** validar con el equipo de compras que la interfaz web permite ejecutar la actualizacion masiva ME12 desde el navegador, sin intervencion directa en la VM Windows.

**Ambiente:** VM Windows 10 con SAP GUI instalado, servicio `ME12WebUI` gestionado por nssm, SAP QA/test disponible y un usuario de compras con autorizacion para ejecutar ME12.

**Nota importante:** la UAT real debe ejecutarla un usuario de compras en la VM Windows con acceso a SAP. Este documento solo registra las pruebas y su resultado.

---

## Preparacion

- [ ] La VM Windows esta encendida y el servicio `ME12WebUI` aparece en `services.msc` como `Running`.
- [ ] La URL `http://vm-windows:5000` es accesible desde el PC del usuario de compras sin entrar a la VM.
- [ ] Se dispone de un Excel de prueba valido con el formato `script/template_me12.xlsx` y datos de condiciones PB00/PB01 de prueba.
- [ ] Se dispone de un Excel de prueba con errores (columnas faltantes, materiales inexistentes, proveedores bloqueados, etc.).
- [ ] El sistema SAP destino es QA/test y el usuario de compras tiene acceso y autorizacion para ME12.
- [ ] `RM06INP0` puede ejecutarse manualmente despues de la corrida para sincronizar `EINE-NETPR`.

---

## Checklist

- [ ] Usuario abre `http://vm-windows:5000` desde su PC sin entrar a la VM.
- [ ] Descarga la plantilla Excel desde el enlace.
- [ ] Carga un Excel valido y el boton "Ejecutar" se habilita.
- [ ] Carga un Excel invalido y se ven errores claros en el log.
- [ ] Presiona "Ejecutar" y ve los logs en tiempo real durante el login SAP.
- [ ] Observa logs de progreso de ME12 (registro por registro).
- [ ] Al terminar con exito, el badge vuelve a "Listo" y el log muestra "Ejecucion completada".
- [ ] SAP se cierra automaticamente (no queda `saplogon.exe` colgado).
- [ ] El Excel temporal no queda en el servidor (verificar carpeta temporal).
- [ ] Forzar un error (ej. desconectar red de SAP durante ejecucion): el badge queda rojo, el log muestra el error, SAP se cierra y el estado vuelve a consistente.
- [ ] Reiniciar la VM: el servicio arranca solo y la URL responde.
- [ ] Ejecutar `RM06INP0` en SAP manualmente despues de la corrida (segun README/script).

---

## Criterio de cierre

Todas las casillas del checklist anterior deben estar marcadas por el usuario de compras. Cuando se cumpla, la Fase 6 se dara por cerrada y el paso a produccion quedara habilitado.

---

## Documentacion final

- [ ] Confirmar que `git diff -- script/` esta vacio: la automatizacion existente no fue modificada.
- [ ] Confirmar que `README.md` y `web/RUNBOOK.md` estan actualizados y referencian `web/UAT_CHECKLIST.md`.
- [ ] Confirmar que `web/UAT_CHECKLIST.md` esta completo y archivado en el repositorio.

---

## Resultado de la UAT

| Fecha | Usuario de compras | Resultado | Observaciones |
|---|---|---|---|
| | | [ ] Aprobado / [ ] Rechazado | |
