# Runbook — Web UI ME12 (Servicio Windows)

## Requisitos previos

- Windows 10 VM con SAP GUI instalado y accesible.
- Python 3.8 (o la versión indicada en `web/mise.toml` / `script/mise.toml`).
- Dependencias del proyecto instaladas:
  ```powershell
  pip install -r web/requirements.txt
  ```
  > `web/requirements.txt` cubre Flask, Flask-SocketIO y sus dependencias. Las
  > librerías de `script/` (`pywin32`, `pandas`, `openpyxl`, `python-dotenv`) deben
  > estar instaladas en la VM.
- Credenciales SAP configuradas en `script/.env` (archivo existente, no trackeado).
- `FLASK_SECRET_KEY` configurada como variable de entorno del sistema (ver
  `web/.env.example`). No usar el mismo valor de ejemplo en producción.

## Instalación del servicio con nssm

1. Descargar `nssm.exe` y ubicarlo en `%PATH%` o en una carpeta conocida.
2. Abrir una terminal como Administrador.
3. Ejecutar:
   ```powershell
   nssm install ME12WebUI
   ```
   En la GUI que se abre configurar:
   - **Path**: `C:\ruta\al\python.exe` (o `py.exe` si se usa launcher).
   - **Startup directory**: `C:\ruta\al\repo\web`.
   - **Arguments**: `server.py`.
   - **Environment**: agregar `FLASK_SECRET_KEY=tu_secreto_aqui`.

   Alternativa completamente por línea de comandos:
   ```powershell
   nssm install ME12WebUI C:\ruta\al\python.exe server.py
   nssm set ME12WebUI AppDirectory C:\ruta\al\repo\web
   nssm set ME12WebUI AppEnvironmentExtra FLASK_SECRET_KEY=tu_secreto_aqui
   nssm set ME12WebUI AppStdout C:\logs\me12webui.log
   nssm set ME12WebUI AppStderr C:\logs\me12webui.log
   nssm set ME12WebUI Start SERVICE_AUTO_START
   nssm start ME12WebUI
   ```

4. Verificar que el servicio figure en `services.msc` como `ME12WebUI`.

## Operaciones

```powershell
# Iniciar
nssm start ME12WebUI

# Detener
nssm stop ME12WebUI

# Reiniciar
nssm restart ME12WebUI

# Eliminar (requiere que esté detenido)
nssm remove ME12WebUI confirm
```

## Logs

 nssm redirige la salida estándar y de error a archivos planos:

```powershell
nssm set ME12WebUI AppStdout C:\logs\me12webui.log
nssm set ME12WebUI AppStderr C:\logs\me12webui.log
```

Crear la carpeta `C:\logs` antes de iniciar el servicio. Para seguir en vivo:

```powershell
Get-Content C:\logs\me12webui.log -Tail 50 -Wait
```

También se puede revisar el registro de eventos de Windows (`eventvwr`) si el
servicio falla antes de que se produzca la redirección.

## Actualización

```powershell
nssm stop ME12WebUI
# Actualizar el repositorio, por ejemplo:
git pull
nssm start ME12WebUI
```

Tras un `git pull` que modifique dependencias, volver a ejecutar:

```powershell
pip install -r web\requirements.txt
```

## Verificación

1. Desde otro equipo de la red, abrir un navegador en:
   ```
   http://vm-windows:5000
   ```
2. Descargar la plantilla, cargar un Excel válido y ejecutar una corrida de
   prueba (preferiblemente en SAP QA/test run).
3. Reiniciar la VM Windows y confirmar que la web responde sin intervención
   manual una vez que el sistema operativo arranca.

> **Validación formal con usuarios:** una vez completadas las verificaciones técnicas
> anteriores, usar `web/UAT_CHECKLIST.md` para la aceptación de usuario (UAT) con
> el equipo de compras. La UAT real debe ejecutarla un usuario de compras en la
> VM Windows con acceso a SAP.

## Notas de seguridad

- Las credenciales SAP viven en `script/.env` (igual que la automatización de
  escritorio). El secreto de Flask (`FLASK_SECRET_KEY`) es una variable de
  entorno separada y **nunca** debe commitearse.
- `web/.env.example` muestra el formato; copiar a `.env` local solo para
  desarrollo/test, no para el servicio de producción.
