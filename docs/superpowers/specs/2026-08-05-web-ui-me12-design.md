# Spec: Web UI for ME12 Mass Price Update

**Date:** 2026-08-05
**Branch:** feature/web-ui-me12
**Status:** APPROVED

---

## 1. Overview

Add a web-based UI to the existing ME12 mass price update script, allowing users to upload Excel files and execute the automation from a browser. The server runs on the Windows 10 VM where SAP GUI is installed.

## 2. Goals

- Replace the desktop GUI (PySide2/Tkinter) with a web interface
- Enable remote access from any browser on the network
- Automate SAP login/logout lifecycle
- Provide real-time execution logs via WebSocket

## 3. Architecture

`
Browser (PC) ←→ Flask + SocketIO (VM Windows) ←→ SAP GUI Scripting
`

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Server | Flask + Flask-SocketIO | HTTP API + WebSocket |
| Web UI | HTML/CSS/JS (embebido) | Interface de usuario |
| SAP Backend | win32com.client (existente) | Automatización SAP GUI |
| Config | .env (existente) | Credenciales SAP |

## 4. User Flow

`
1. Abrir browser → http://vm-windows:5000
2. Seleccionar archivo Excel
3. Click "Ejecutar"
4. Ver logs en tiempo real
5. Al terminar → SAP cierra automáticamente
6. Badge vuelve a "Listo"
`

## 5. API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Serve Web UI |
| POST | /upload | Receive Excel, save temporary |
| POST | /execute | Run ME12, stream logs via WebSocket |
| GET | /status | SAP connection status |

## 6. WebSocket Events

| Event | Direction | Payload | Description |
|-------|-----------|---------|-------------|
| log | Server→Client | {message: string} | Log line from execution |
| status | Server→Client | {state: "ready"|"processing"|"error"} | UI status badge |
| complete | Server→Client | {result: "OK"|"ERROR", summary: string} | Execution finished |

## 7. SAP Lifecycle

### Server Start
`python
sap = SapGui()
sap.sapLogin(log_func=emit_log)  # Connect SAP GUI
# SAP ready for execution
`

### After Each Execution
`python
sap.safe_close_window()  # Logoff + close saplogon.exe
sap.session = None       # Clear reference
# Ready for next execution (reconnects on next "Ejecutar")
`

### Auto-Reconnect
If SAP disconnects unexpectedly, the next execution attempt will reconnect automatically.

## 8. File Structure

### New Files
`
script/
├── web_server.py          # Flask + SocketIO + API routes
├── templates/
│   └── index.html         # Web UI (single page)
├── requirements.txt       # Python dependencies
└── static/
    └── (empty, all assets inline)
`

### Modified Files
`
script/
├── sap.py                 # Add log callback parameter
└── me12_massmod.py        # Already supports log_func (no changes)
`

## 9. Web UI Design

### Layout
`
┌─────────────────────────────────────────────────┐
│  ME12 - Actualización Masiva de Precio          │
├─────────────────────────────────────────────────┤
│                                                 │
│  [Seleccionar archivo]  nombre_archivo.xlsx     │
│                                                 │
│  [Ejecutar]                                     │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  Status: ● Listo                        │   │
│  │                                         │   │
│  │  > Iniciando Proceso ME12...            │   │
│  │  > Procesando registro 1 de 3...        │   │
│  │  > Fila 0: OK - 10013038001/10000598   │   │
│  │  > ...                                  │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Descargar Plantilla Excel                      │
└─────────────────────────────────────────────────┘
`

### Status Badge States
- **● Listo** (green) — Ready to execute
- **● Procesando...** (yellow) — Execution in progress
- **● Completado** (green) — Execution finished successfully
- **● Error** (red) — Execution failed

## 10. Dependencies

### requirements.txt
`
flask>=3.0
flask-socketio>=5.3
python-socketio>=5.10
python-engineio>=4.8
`

### Existing (no changes)
`
pywin32 (win32com.client)
python-dotenv
pandas
openpyxl
PySide2 (kept for backward compatibility)
`

## 11. Configuration

### .env (existing, no changes)
`
SYSTEM=PRD
MANDT=100
USER=sap_user
PASSWD=sap_password
LANGUAGE=ES
`

### Server Config
`python
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000
DEBUG = False
`

## 12. Error Handling

| Scenario | Behavior |
|----------|----------|
| SAP not installed | Server fails to start with clear error message |
| SAP login fails | Status badge → red, error in logs |
| Excel invalid | Return validation errors to UI |
| SAP disconnects | Auto-reconnect on next execution |
| Execution error | Status badge → red, error in logs, SAP closes |

## 13. Security Considerations

- .env contains SAP credentials — must not be committed
- No authentication on web UI (internal network only)
- Temporary Excel files deleted after execution
- SAP session closed after each execution

## 14. Deployment

### On Windows VM
`ash
# Install dependencies
pip install -r requirements.txt

# Run server
python web_server.py

# Or install as Windows service (optional)
# Use nssm: nssm install ME12WebUI python web_server.py
#           nssm start ME12WebUI
`

### Access
`
http://vm-windows-ip:5000
`

## 15. Testing

1. Start server: python web_server.py
2. Open browser: http://localhost:5000
3. Upload test Excel file
4. Click "Ejecutar"
5. Verify logs appear in real-time
6. Verify SAP closes after execution
7. Verify status badge returns to "Listo"

## 16. Future Enhancements (Out of Scope)

- [ ] Authentication (basic auth or LDAP)
- [ ] Upload history / audit log
- [ ] Multiple concurrent executions
- [ ] Docker containerization
- [ ] REST API for programmatic access
