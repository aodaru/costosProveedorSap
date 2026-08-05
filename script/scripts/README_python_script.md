# Scripts - ME12 Price Change

## Script VBA Original

`me12_price_change.vba` — Macro VBA para SAP GUI Scripting que actualiza masivamente el precio neto (condicion PB00) en info records de compras usando ME12.

### IDs del Recording (ME12)

| Elemento | ID SAP | Descripcion |
|---|---|---|
| Proveedor | `wnd[0]/usr/ctxtEINA-LIFNR` | Campo de proveedor |
| Material | `wnd[0]/usr/ctxtEINA-MATNR` | Campo de material |
| Org Compras | `wnd[0]/usr/ctxtEINE-EKORG` | Organizacion de compras |
| Boton Condiciones | `wnd[0]/tbar[1]/btn[8]` | Accede a la pantalla de condiciones |
| Popup Confirmacion | `wnd[1]/tbar[0]/btn[7]` | Confirmacion (puede no aparecer) |
| Precio en tabla | `wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[row,0]` | Precio neto en tabla de condiciones |
| Guardar | `wnd[0]/tbar[0]/btn[11]` | Guardar (F11) |
| Status Bar | `wnd[0]/sbar` | Mensaje de resultado |

### Configuracion

- `CONDITION_ROW = 2` (indice 0-based, equivale a fila 3 visual)
- Delays: ENTER=500ms, CLICK=300ms, BETWEEN_ROWS=1000ms

### Formato de la Hoja "Datos"

| Columna | Campo | Obligatorio | Default | Descripcion |
|---|---|---|---|---|
| A | Material | Si | - | Numero de material (solo digitos) |
| B | Proveedor | Si | - | Numero de proveedor (solo digitos) |
| C | Org Compras | Si | 1000 | Organizacion de compras |
| D | Tipo Info Record | No | 0 | Tipo de registro de informacion |
| E | Tipo Condicion | No | PB00 | Tipo de condicion (PB00/PB01) |
| F | Nuevo Precio | Si | - | Precio neto (formato: 8.90) |
| G | Moneda | No | MXN | Moneda |
| H | Unidad Precio | No | 1 | Unidad de precio |
| I | Unidad Medida | No | - | Unidad de medida |
| J | Valido Desde | No | Hoy | Fecha inicio validez (YYYYMMDD) |
| K | Valido Hasta | No | 99991231 | Fecha fin validez (YYYYMMDD) |

## Script Python (ME12 Mass Price Change)

Script Python que replica la funcionalidad del VBA con mejoras:

### Archivos

| Archivo | Descripcion |
|---|---|
| `sap.py` | Ciclo de vida SAP (login/cierre sesion/cierre programa) |
| `me12_massmod.py` | Runner ME12 — logica por registro |
| `validators.py` | Validacion del archivo de entrada Excel |
| `main.py` | GUI PySide2 |
| `paths.py` | Deteccion de ruta base (frozen-aware) |
| `test_project.py` | Tests pytest |
| `template_me12.xlsx` | Plantilla Excel de entrada |

### Ejecucion

```bash
# Instalar dependencias
pip install pywin32 pandas openpyxl python-dotenv PySide2 pytest

# Ejecutar GUI
python main.py

# Ejecutar tests
pytest test_project.py
```

### Notas

- Requiere SAP GUI Scripting habilitado (`sapgui/user_scripting = TRUE` en RZ11)
- Las credenciales van en `.env` (copiar de `.env.example`)
- El `CONDITION_ROW` puede variar segun el sistema SAP
- Despues de cambiar precios, ejecutar `RM06INP0` para resincronizar `EINE-NETPR`
