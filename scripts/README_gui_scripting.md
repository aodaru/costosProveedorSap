# ME12 Price Change Script - SAP GUI Scripting

## Descripcion

Script VBA para SAP GUI Scripting que actualiza masivamente el precio neto (condicion PB00) en registros de informacion de compras usando la transaccion ME12.

Basado en un recording real del usuario con los IDs especificos de su entorno SAP.

## Prerrequisitos

1. **SAP GUI Scripting habilitado**:
   - Ejecutar RZ11 y activar `sapgui/user_scripting = TRUE`
   - Contactar a Basis para la activacion

2. **SAP GUI abierto** con sesion activa

3. **Microsoft Excel** con macros habilitadas

4. **Autorizaciones SAP**:
   - M_EINK: Consulta de Info Records
   - M_EIKO: Organizacion de Compras

## IDs del Recording (ME12)

Los siguientes IDs corresponden al recording real del usuario y estan integrados en el script:

| Paso | Objeto SAP | ID | Funcion |
|------|-----------|-----|---------|
| 1 | Campo Proveedor | `wnd[0]/usr/ctxtEINA-LIFNR` | Ingresar numero de proveedor |
| 2 | Campo Material | `wnd[0]/usr/ctxtEINA-MATNR` | Ingresar numero de material |
| 3 | Campo Org Compras | `wnd[0]/usr/ctxtEINE-EKORG` | Ingresar organizacion de compras |
| 4 | Boton Condiciones | `wnd[0]/tbar[1]/btn[8]` | Navegar a pantalla de condiciones |
| 5 | Popup confirmacion | `wnd[1]/tbar[0]/btn[7]` | Confirmar popup (puede no aparecer) |
| 6 | Campo Precio | `wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[2,0]` | Modificar precio en tabla |
| 7 | Guardar | `wnd[0]/tbar[0]/btn[11]` | Guardar cambios (F11) |

### Nota sobre el popup `wnd[1]/tbar[0]/btn[7]`

Este popup es **normal** en el flujo ME12. Aparece cuando se presiona el boton de Condiciones y SAP requiere confirmacion (por ejemplo, si ya existen condiciones o para validar la seleccion). El script lo maneja automaticamente con `On Error Resume Next` para que no falle si el popup no aparece en tu version de SAP.

### Nota sobre la fila de la tabla `CONDITION_ROW`

El indice `[2,0]` en `tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[2,0]` es 0-based, lo que significa que corresponde a la **tercera fila visual** de la tabla de condiciones. Este valor puede variar segun:
- Cuantas condiciones existan configuradas para el info record
- La version de SAP
- Si hay condiciones prefijadas

El script define `CONDITION_ROW = 2` como constante configurable. Si tu condicion PB00 aparece en otra fila, ajusta este valor.

## Instrucciones de Uso

### Paso 1: Preparar Hoja Excel

Crear hoja llamada "Datos" con el siguiente formato:

> **Nota**: Los info records son a nivel de organizacion de compras (EKORG), no tienen planta.

| A | B | C | D | E | F | G | H | I | J | K | L | M |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Material | Proveedor | Org Compras | Tipo Info | Tipo Cond | Nuevo Precio | Moneda | Unidad Precio | Unidad Medida | Desde | Hasta | Resultado | Log |
| 10013034054 | 10000598 | 1000 | 0 | PB00 | 8.90 | MXN | 1 | | 20260101 | 99991231 | | |

**Formatos importantes**:
- Precio: usar punto como separador decimal (8.90)
- Fechas: formato YYYYMMDD sin guiones
- Valores por defecto: Tipo Info = 0, Tipo Cond = PB00, Moneda = MXN, Unidad Precio = 1

**Columnas obligatorias**: Material (A), Proveedor (B), Org Compras (C), Nuevo Precio (F)

### Paso 2: Configurar Script

1. Copiar contenido de `me12_price_change.vba` en modulo VBA de Excel (Alt+F11 -> Insertar modulo)
2. Verificar que la constante `CONDITION_ROW` coincida con la posicion de tu condicion
3. Ajustar delays si es necesario

### Paso 3: Ejecutar

1. **PRUEBA INICIAL**: Ejecutar con 1 solo registro
2. Verificar resultado en ME13
3. Si es correcto, ejecutar con todos los registros
4. **No tocar SAP GUI mientras corre el script**

### Paso 4: Validacion

- **ME13**: Verificar precio actualizado en el registro de info
- **ME1E**: Historial de cambios de precio
- **KONP**: Verificar condicion en la tabla de condiciones

## Configuracion del Script

```vba
' Ajustar segun tu entorno
Private Const SHEET_NAME As String = "Datos"
Private Const CONDITION_ROW As Long = 2       ' Fila de la tabla [2,0]
Private Const DELAY_AFTER_ENTER As Long = 500  ' ms despues de Enter
Private Const DELAY_AFTER_CLICK As Long = 300  ' ms despues de click
Private Const DELAY_BETWEEN_ROWS As Long = 1000 ' ms entre registros
```

## Archivos

- `me12_price_change.vba` - Script VBA completo con IDs del recording real
- `README_gui_scripting.md` - Esta documentacion

## Solucion de Problemas

| Problema | Solucion |
|----------|----------|
| No conecta a SAP | Verificar SAP GUI abierto y scripting habilitado (RZ11) |
| Error "User-defined type" | En VBA: Herramientas -> Referencias -> marcar "SAP Front End Controls" |
| Popup interrumpe script | El script maneja `wnd[1]/btn[7]` con On Error Resume Next. Si falla, ajustar el delay o agregar manejo especifico |
| Precio no se modifica | Verificar `CONDITION_ROW`. Usar el recording para identificar la fila correcta de tu condicion |
| Error en status bar | Revisar columna Log en Excel para el mensaje completo de SAP |
| "Material no encontrado" | Verificar que el material exista en ME11/ME12 y este asignado al proveedor |
| "Org Compras no valida" | Verificar que la EKORG este asignada al proveedor en XD02/BP |

## Limitaciones

- Velocidad: ~1-2 segundos por registro
- Fragil ante cambios de pantalla SAP (versiones, patches, customizaciones)
- No oficialmente soportado para produccion por SAP
- Requiere que la condicion PB00 este configurada en M/06
- No usa planta (los info records son a nivel EKORG)
- El `CONDITION_ROW` puede variar segun el entorno SAP
- No maneja multiples condiciones del mismo tipo en la tabla

## Notas Importantes

> **Este script modifica datos de produccion.** Usar bajo tu responsabilidad y siempre con backup previo.

> **SAP no soporta oficialmente GUI Scripting** para procesos productivos criticos.

> **Probar siempre en entorno de Desarrollo/Quality primero.**

> Los IDs de este script corresponden a un recording especifico. Si tu SAP tiene customizaciones o una version diferente, los IDs pueden diferir. Grabar un recording propio es la forma mas confiable de obtener los IDs correctos.
