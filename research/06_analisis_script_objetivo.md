# 06 — Análisis del objetivo y alcance del script Python de automatización SAP GUI

**Fecha:** 2026-08-01
**Tipo:** Investigación y documentación (sin escribir código de la solución)
**Proyecto destino:** `C:\Users\agarcia\dev\costosProveedorSap`
**Objetivo:** Definir con precisión QUÉ debe hacer el nuevo script Python que automatice en SAP GUI la "Actualización Masiva del Precio Neto (PB00/PB01) del Info Record de Compras", copiando el patrón de login / cierre de sesión / cierre de programa del proyecto `C:\Users\agarcia\dev\sapCondMassMod` y aprovechando el precedente de scripting GUI (VBA) ya existente en este mismo repositorio.

---

## 1. Resumen ejecutivo

El nuevo script Python debe **automatizar la transacción ME12 (cambio de info record de compras) vía SAP GUI Scripting**, replicando en Python el flujo que ya funciona en VBA en este repositorio (`scripts/me12_price_change.vba`): para cada fila de un archivo de entrada, navegar a ME12, capturar el info record por clave (proveedor/material/org. de compras), entrar a la pestaña **Condiciones**, editar el importe `KONP-KBETR` de la condición PB00, guardar, verificar la barra de estado, y registrar el resultado por fila.

Razones clave (detalladas en §4):

1. **Es la vía que ya tiene precedente probado en el proyecto** (`scripts/me12_price_change.vba` y su README `scripts/README_gui_scripting.md`), con los IDs reales del recording de ME12 documentados.
2. **Es exactamente el patrón que ya implementa el proyecto Python de referencia** `sapCondMassMod` (que automatiza VK12, el análogo en SD de ME12/MEK2 en MM, incluyendo la misma tabla de condiciones `tblSAPMV13ATCTRL_*/txtKONP-KBETR`). El script Python nuevo puede copiar la arquitectura completa (login, ejecución masiva, logout, `.env`, validadores, log en GUI).
3. **Usa el 100% de la lógica estándar de ME12** (validez, escalas, documento de cambio, mensajes), tal como recomienda la investigación (`research/02_apis_actualizacion_masiva.md` §9) y el propio reporte ABAP para su alternativa BDC (`src/zr_mass_actualiza_precio_cond.abap:840-911`).
4. **Evita la dependencia de `ME_INFORECORD_MAINTAIN`**, que es el punto frágil del reporte ABAP entregado: está marcado **obsoleto** (KBA 2787315) y su firma debe validarse en SE37/SE11 del sistema destino (`README.md` §4.4 y §6; `research/02` §3; `src/...:50-53`).

**Alternativas documentadas** (a descartar o confirmar con el usuario, §3): ejecutar el reporte Z `ZR_MASS_ACTUALIZA_PRECIO_COND` desde SE38/SA38 vía scripting (reutiliza la validación y el log ABAP, pero depende del FM y requiere leer el ALV/archivo), o automatizar MEKP (la vía estándar masiva, pero con pantallas de entrada distintas y más complejas de automatizar).

**Complemento obligatorio:** después del cambio de condiciones, ejecutar `RM06INP0` para resincronizar `EINE-NETPR`/`PEINH`/`WAERS` (KBA 685117 / 2892806; `README.md:88`). El script debe contemplarlo como paso final opcional (pregunta abierta, §9).

---

## 2. Flujo de negocio actual

### 2.1 Cómo se entiende el dato (base conceptual)

"Cambiar el precio en MM42" NO es editar el material master: la vista de Compras de MM42 no tiene campos de precio editables y `MARC-NETPR` no existe en el estándar (`research/01_data_model_mm42.md:21-27`, `:69`; `research/02:7-10`). El precio neto que se ve proviene del **info record** y de su **registro de condición**:

- **Info record:** `EINE-NETPR` (CURR 11,2, ref. WAERS), campo informativo tipo *snapshot* calculado desde las condiciones; no es la fuente que usa el pedido para pricing (`research/01:39-43`, `:111-113`).
- **Registro de condición (la fuente real):** condición **PB00** (precio bruto; PB01 ambiguo, validar en M/06) guardada en la tabla de condiciones **A018** (sin planta) / **A017** (con planta), que apunta por **KNUMH** a **KONH** (cabecera: KSCHL, VAKEY, DATAB/DATBI) y **KONP** (partida: **KBETR** = importe, KONWA, KPEIN, KMEIN); escalas en **KONM** (`research/01:45-62`, `:77-84`).
- Al crear un PO, las condiciones se copian a **KONV** (EKKO-KNUMV); los POs ya creados no cambian (`research/01:64-66`, `:114`; `README.md:89`).

Por lo tanto "actualizar masivamente el precio neto" significa técnicamente: **mantener en masa el registro de condición PB00/PB01 del info record** y después **resincronizar `EINE-NETPR` con `RM06INP0`** (`src/...:11-14`, `:26-27`; `README.md:14`).

### 2.2 Cómo se hace hoy (tres mecanismos documentados)

| Vía | Cómo funciona | Dónde está documentado |
|---|---|---|
| **Manual** | ME12 (pestaña Condiciones → cambiar KBETR) o MEK2, o MEKP para masivo | `research/01:34`, `:46`; `research/02:74-78`; `README.md:63` |
| **ABAP (reporte Z entregado)** | `ZR_MASS_ACTUALIZA_PRECIO_COND`: CSV `;` → validación masiva (MARA/LFA1/EINA/EINE/TCURC) → `ME_INFORECORD_MAINTAIN` por fila (test run / commit-rollback) → log BAL + Z-tabla `ZPIR_PRICELOG` → ALV | `src/zr_mass_actualiza_precio_cond.abap` (completo); `README.md:117-127` |
| **VBA (precedente de scripting)** | Excel hoja "Datos" → por fila: `/nME12` → clave (LIFNR/MATNR/EKORG) → botón Condiciones → editar `txtKONP-KBETR[2,0]` → Guardar → leer barra de estado → resultado en columnas L/M + log `.txt` | `scripts/me12_price_change.vba` (408 líneas); `scripts/README_gui_scripting.md` |

### 2.3 El reporte ABAP en detalle (entrada, procesamiento, salida)

**Transacciones/programas que toca o menciona** (`src/...:29-34`): ME11/ME12/ME13 (info record), MEK1/MEK2/MEK3 (condiciones), MEKP (cambio masivo estándar), ME1E (historial de precios), RM06INP0 (resincroniza EINE-NETPR), SLG1 (application log), SM35 (sesiones batch si BDC). También menciona MM42 como la vista donde el usuario visualiza el dato.

**Entrada (CSV separador `;`, primera línea = cabecera que se omite)** (`src/...:18-19`, `:229-234`):

```
MATNR;LIFNR;EKORG;WERKS;INFNR;KSCHL;KBETR;KONWA;PEINH;KMEIN;DATAB;DATBI
1000001;0000012345;1000;3000;;PB00;12.50;EUR;1;ST;01.08.2026;31.12.9999
```

**Procesamiento por registro** (`src/...:490-684`):
- **Modo test** (`p_test = 'X'`, default): NO llama al FM de modificación; solo valida y marca `TEST OK (no aplicado)` — no destructivo (documenta por qué "no hacer COMMIT" no basta: COMMIT implícito al terminar el reporte) (`src/...:482-488`, `:516-520`).
- **Modo producción**: llama `ME_INFORECORD_MAINTAIN` con `MEWICONDITION_TT` (COND_TYPE='PB00', COND_VALUE, CURRENCY, COND_P_UNT, COND_UNIT, CHANGE_ID='U') y `MEWIVALIDITY_TT` (VALID_FROM/VALID_TO/SERIAL_ID); `COMMIT WORK AND WAIT` por fila OK, `ROLLBACK WORK` por fila con error; `p_pkg` (default 50) para flush del log (`src/...:528-683`).
- **Validaciones previas**: material en MARA, proveedor en LFA1, info record en EINA/EINE (excluye LOEKZ='L'), moneda en TCURC; reglas por fila: clave completa obligatoria, `datab <= datbi`, `kbetr > 0`; defaults: KSCHL=PB00, PEINH=1, DATAB=hoy, DATBI=99991231, KONWA=EINE-WAERS (`src/...:301-461`).
- **Salida**: ALV (cl_salv_table) o lista clásica con OK/ERROR/SKIP; Application Log (BAL, objeto `ZPIR`) y Z-tabla sugerida `ZPIR_PRICELOG` (`src/...:686-777`).
- **Alternativas documentadas (comentadas)**: BAPI_INFORECORD_CHANGE (NO confirmado como BAPI liberado; `src/...:805-837`) y **BDC sobre ME12** con los dynpros y campos exactos (`src/...:840-911`): dynpro `SAPMM06I 0100` con `RM06I-INFNR`; dynpro `SAPMM06I 0201` con `BDC_OKCODE = '=VW1'` (entrar a condiciones); dynpro `SAPLV14A 0102` con `KONP-KBETR`, `KONP-KPEIN` (y según recording: KONP-KONWA, KONP-KMEIN, DATAB/DATBI); `BDC_OKCODE = '=SICH'` (guardar); `CALL TRANSACTION 'ME12' MODE 'A' UPDATE 'S' MESSAGES INTO lt_msg`.

### 2.4 El precedente VBA en detalle (lo que automatiza)

- **Transacción:** ME12. **Entrada:** hoja Excel "Datos" (`scripts/me12_price_change.vba:20`, `:360-379`). **Velocidad:** ~1-2 s por registro (delays ENTER=500ms, CLICK=300ms, entre filas=1000ms).
- **Pasos de pantalla por registro** (IDs del recording real; `:246-309`, `:381-388`):

| Paso | Objeto SAP (ID) | Acción |
|---|---|---|
| 1 | `wnd[0]/tbar[0]/okcd` = `/nME12` + SendVKey 0 | Navegar a ME12 |
| 2 | `wnd[0]/usr/ctxtEINA-LIFNR` | Proveedor |
| 3 | `wnd[0]/usr/ctxtEINA-MATNR` | Material |
| 4 | `wnd[0]/usr/ctxtEINE-EKORG` (+ setFocus/caret) | Org. de compras |
| 5 | SendVKey 0 | Enter (validar datos) |
| 6 | `wnd[0]/tbar[1]/btn[8]` | Botón Condiciones |
| 7 | `wnd[1]/tbar[0]/btn[7]` | Popup de confirmación (puede no aparecer; manejado con On Error Resume Next) |
| 8 | `wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[2,0]` | Nuevo precio (CONDITION_ROW=2, índice 0-based, configurable) |
| 9 | `wnd[0]/tbar[0]/btn[11]` | Guardar (F11) |
| 10 | `wnd[0]/sbar` | Leer status bar → detectar errores ("error", "no se pudo") |

- **Salida:** columnas L (Resultado) y M (Log) del Excel + archivo `.txt` en `%TEMP%\ME12_Log_yyyymmdd_hhmmss.txt`; resumen OK/ERROR en MsgBox.
- **Configuraciones:** `CONDITION_ROW` (fila de la condición en la tabla; puede variar según nº de condiciones, versión SAP), `SAP_CONNECTION = "SAP"`, delays.
- **Nota importante del propio script:** "No usa planta (los info records son a nivel EKORG)" (`:31`, `:406`) — a diferencia del ABAP, que sí incluye WERKS.

### 2.5 El patrón Python de referencia (`sapCondMassMod`) — lo que hay que copiar

El usuario pide explícitamente copiar el patrón de login / cierre de sesión / cierre de programa. Del proyecto `C:\Users\agarcia\dev\sapCondMassMod`:

- **`sap.py`** (`sap.py:25-94`):
  - `open_sap()`: abre `C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe` con `subprocess.Popen`.
  - `connection_sap()`: `GetObject("SAPGUI")` → `GetScriptingEngine` → `Children(0)` → `Children(0)` (sesión) → `maximize()`.
  - `sapLogin()`: `OpenConnection(system_sap, True)` y llena `wnd[0]/usr/txtRSYST-MANDT`, `txtRSYST-BNAME`, `pwdRSYST-BCODE`, `txtRSYST-LANGU` y SendVKey 0 (campos de la pantalla de login estándar SAP).
  - `safe_close_window()`: `connection.CloseSession('ses[0]')` y luego `taskkill /f /im saplogon.exe` (cierre del programa).
  - Credenciales desde `.env`: `SYSTEM`, `MANDT`, `USER`, `PASSWD`, `LANGUAGE`.
- **`main.py`**: GUI PySide2 con botones (abrir archivo, Login SAP, Ejecutar con QMessageBox de confirmación, Cerrar sesión, Cerrar app) y log en `QPlainTextEdit` (`main.py:17-110`).
- **`sap_vk12_massmod.py`**: patrón de flujo masivo — por cada fila navega a la transacción por `okcd`, llena campos, presiona botones, guarda y vuelve; usa la misma tabla de condiciones KONP (`tblSAPMV13ATCTRL_FAST_ENTRY/txtKONP-KBETR[...]`) que el VBA de ME12, lo que confirma que **la tabla de condiciones KONP es el elemento común entre VK12 (SD) y ME12 (MM)** (`sap_vk12_massmod.py:71-98`).
- **`validators.py`**: lee el Excel con pandas (`pd.read_excel(..., dtype=str)`), normaliza nombres de columnas, valida cada fila (campos obligatorios, numéricos, dominios) y elimina filas inválidas (`validators.py:83-102`).
- **`paths.py` / `mise.toml`**: gestión de rutas base y dependencias (pywin32, pandas, dotenv, PySide2).

---

## 3. ¿Qué transacción(es) debe automatizar el script Python? (respuesta directa)

Tres opciones reales (el reporte ABAP descarta implícitamente las transacciones que no aplican):

### Opción A — ME12 directo (cambio de info record), replicando el VBA
- **Pros:** precedente VBA probado con IDs de recording reales en este proyecto; usa 100% la lógica estándar (validez, escalas, doc. de cambio, mensajes); patrón idéntico al de `sapCondMassMod` (que automatiza VK12 con la misma tabla KONP); no depende de `ME_INFORECORD_MAINTAIN` (obsoleto, KBA 2787315) ni de que exista el reporte Z en el sistema.
- **Contras:** frágil ante cambios de pantalla/versión; el `CONDITION_ROW` puede variar; el VBA documentado no usa planta (a nivel EKORG); ~1-2 s por registro.
- **Sustento:** `research/02:93-99` (BDC sobre ME12/MEK1/MEK2/MEKP como enfoque de última opción pero válido y "usando 100% la lógica estándar"); `research/03:36`, `:462-474`, `:526-536` (BDC/LSMW sobre ME12 es la vía robusta para escalas/múltiples valideces; campos del recording: selección `RM06I-INFNR`, pestaña condiciones `SAPLV14A` con `KONP-KBETR/KPEIN/KMEIN/KONWA` y DATAB/DATBI).

### Opción B — Ejecutar el reporte Z `ZR_MASS_ACTUALIZA_PRECIO_COND` desde SE38/SA38 vía scripting
- **Pros:** reutiliza toda la lógica ABAP ya entregada (validación masiva, test run, commit/rollback por fila, log BAL + Z-tabla, ALV); el script Python solo tendría que abrir SE38/SA38, llenar `p_file`, `p_test`, `p_pkg`, ejecutar (F8) y esperar el resultado.
- **Contras:** depende de que `ME_INFORECORD_MAINTAIN` exista y funcione en el sistema destino (obsoleto, verificar SE37 — `src/...:36-54`; `README.md:86`); leer el ALV o el resultado por scripting es incómodo y frágil; el CSV debe cargarse vía `gui_upload` (puede haber problemas de codepage/separador); se necesitan dos corridas (test y producción); requiere que el reporte esté instalado/transportado.
- **Sustento:** `README.md:117-127` (sección del reporte), `src/...:191-208` (START-OF-SELECTION), `src/...:213-275` (carga de archivo).

### Opción C — MEKP (Price Change: Info Records) o MEK2
- **Pros:** MEKP es la **vía manual estándar por excelencia** para cambios masivos de precios de info records (%, signo, validez, escalas), riesgo bajo, soporte pleno (`research/02:74-78`; `README.md:63`).
- **Contras:** es una app interactiva de carga/lista (pantalla de selección múltiple, no "1 registro → 1 guardado"), por lo que su automatización vía GUI Scripting es más compleja (tablas de selección, lista de resultados); no encaja con el patrón fila-a-fila de `sapCondMassMod`. Se menciona en el proyecto solo como alternativa manual recomendada (`src/...:32-33`; `research/02:78`).
- **MEK2** (cambio de condición): equivalente a ME12 en la parte de condiciones; el ABAP lo menciona como alternativa BDC (`src/...:31`, `:840`). Podría usarse si el usuario prefiere condiciones puras sin info record, pero ME12 ya cubre el caso.

### Veredicto del análisis
**Opción A (ME12 directo)** como flujo principal del script Python. Las razones:
1. Precedente interno probado (VBA) y patrón de referencia externo (sapCondMassMod) que ya automatiza la misma tabla KONP.
2. No depende de FM obsoleto ni de transporte del reporte Z.
3. Usa la lógica estándar (documento de cambio, mensajes, validez) que la investigación recomienda para el cambio simple PB00 (`research/02:93-99`; `research/03:36`).

Se documenta la **Opción B (SE38/SA38 del reporte Z)** como alternativa si el usuario prefiere reutilizar el ABAP entregado (por su validación y logging) y si el FM está disponible en el sistema destino. La **Opción C (MEKP)** queda como vía manual de respaldo y como posible automatización futura si se confirma que el flujo del negocio es de %/validez/escalas.

---

## 4. Recomendación fundamentada

**Recomendación:** script Python (patrón `sapCondMassMod`) que automatice **ME12** con los IDs del recording VBA existente, con estas características:

- **Arquitectura copiada de `sapCondMassMod`**: `sap.py` (login con saplogon + OpenConnection + campos RSYST, logout con CloseSession + taskkill), `.env` con credenciales, validadores pandas, log en GUI/consola, y cierre controlado.
- **Flujo por registro = flujo del VBA** (tabla del §2.4), con `CONDITION_ROW` configurable y lectura de la barra de estado (`wnd[0]/sbar`) para detectar errores.
- **Entrada**: Excel o CSV (ver §5; pregunta abierta §9).
- **Verificación posterior**: ME13 / MEK3 / ME1E (según `README.md:105-113`).
- **Paso final opcional**: `RM06INP0` para resincronizar `EINE-NETPR` (regla de oro del proyecto, §7.2).

**Justificación con citas:**
- El reporte ABAP dice: "si la versión del sistema lo rechaza, usar la alternativa BDC sobre ME12" (`src/...:50-53`). El script Python es esa "alternativa BDC" pero en GUI Scripting, sin BDC.
- `research/03:36`: "Para CASCADAS/ESCALAS la vía robusta sigue siendo BDC sobre ME12 o IDoc COND_A01".
- `research/02:96-98`: "BDC/LSMW sobre ME12... Ventaja: Usa 100% la lógica estándar (validez, escalas, doc. de cambio, mensajes)."
- `scripts/README_gui_scripting.md:5-7`: "Script VBA... actualiza masivamente el precio neto (condicion PB00)... usando la transaccion ME12. Basado en un recording real del usuario".
- `sapCondMassMod/sap_vk12_massmod.py:89`: usa `tblSAPMV13ATCTRL_FAST_ENTRY/txtKONP-KBETR[3,0]` — el mismo patrón de tabla de condiciones que el VBA de ME12 (`tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[2,0]`), confirmando que el componente UI a automatizar (tabla KONP) es transversal.

---

## 5. Datos de entrada: formato y columnas exactas

### 5.1 Formato del ABAP (CSV `;`, 12 columnas) — `src/...:231-234`

| # | Columna | Campo SAP | Obligatorio | Default |
|---|---|---|---|---|
| 1 | MATNR | Material | Sí | — |
| 2 | LIFNR | Proveedor | Sí | — |
| 3 | EKORG | Org. de compras | Sí | — |
| 4 | WERKS | Planta | Sí (según validación del ABAP) | — |
| 5 | INFNR | Nº info record | No (se deriva) | Derivado de EINA/EINE |
| 6 | KSCHL | Tipo de condición | No | PB00 |
| 7 | KBETR | Nuevo importe | Sí | — |
| 8 | KONWA | Moneda | No | EINE-WAERS |
| 9 | PEINH | Unidad de precio | No | 1 |
| 10 | KMEIN | Unidad de medida | No | — |
| 11 | DATAB | Válido desde | No | hoy (YYYYMMDD) |
| 12 | DATBI | Válido hasta | No | 99991231 |

Reglas del ABAP: primera línea = cabecera (se omite); separador `;`; conversión ALPHA (ceros a la izquierda) en MATNR/LIFNR; fechas en `YYYYMMDD` o `DD.MM.YYYY`; **punto decimal** recomendado para KBETR (si llega coma, normalizar) (`src/...:260-272`).

### 5.2 Formato del VBA (Excel, hoja "Datos", 13 columnas) — `scripts/me12_price_change.vba:30-43`, `:366-379`

| Col | Cabecera | Obligatorio | Default / formato |
|---|---|---|---|
| A | Material | Sí | numérico |
| B | Proveedor | Sí | numérico |
| C | Org Compras | Sí | — |
| D | Tipo Info (ESOKZ) | No | 0 |
| E | Tipo Condición | No | PB00 |
| F | Nuevo Precio | Sí | punto decimal (8.90) |
| G | Moneda | No | MXN |
| H | Unidad Precio | No | 1 |
| I | Unidad Medida | No | — |
| J | Válido Desde | No | YYYYMMDD (default hoy) |
| K | Válido Hasta | No | YYYYMMDD (default 99991231) |
| L | Resultado | Salida | se llena automáticamente |
| M | Log | Salida | se llena automáticamente |

**Diferencia clave:** el VBA **no usa planta** ("los info records son a nivel EKORG", `vba:31`, `:406`); el ABAP **sí** tiene columna WERKS y soporta info records con planta (A017) y sin planta (A018) (`research/01:50-53`).

### 5.3 Recomendación para el script Python
- **Formato:** Excel (como VBA y sapCondMassMod) o CSV `;` (como el ABAP). Ambos son triviales con pandas. Pregunta abierta al usuario (§9).
- **Columnas recomendadas (unión de ambos):** Material, Proveedor, Org Compras, [WERKS opcional según negocio], [INFNR opcional], Tipo Condición (PB00), Nuevo Precio, Moneda, Unidad Precio, Unidad Medida, Válido Desde, Válido Hasta, + columnas de Resultado/Log.
- **Validaciones previas en el script Python** (portables del ABAP, `src/...:301-461`): campos clave no vacíos, material numérico, proveedor numérico, precio > 0, datab <= datbi, moneda/unidad con default, normalización ALPHA de MATNR/LIFNR (ceros a la izquierda).

---

## 6. Flujo paso a paso propuesto (pantallas de SAP)

Basado en el VBA (`scripts/me12_price_change.vba:246-309`), el patrón de login de `sapCondMassMod` (`sap.py:38-74`) y el BDC documentado en el ABAP (`src/...:864-910`):

1. **Login** (patrón `sapCondMassMod/sap.py`):
   - Abrir saplogon.exe (`subprocess.Popen`).
   - `GetObject("SAPGUI")` → `GetScriptingEngine` → `OpenConnection(system, True)`.
   - Llenar `wnd[0]/usr/txtRSYST-MANDT`, `txtRSYST-BNAME`, `pwdRSYST-BCODE`, `txtRSYST-LANGU` → SendVKey 0.
   - Maximizar `wnd[0]`.
2. **Ciclo por registro** (patrón VBA):
   - `wnd[0]/tbar[0]/okcd` = `/nME12` → SendVKey 0.
   - `wnd[0]/usr/ctxtEINA-LIFNR` = proveedor.
   - `wnd[0]/usr/ctxtEINA-MATNR` = material.
   - `wnd[0]/usr/ctxtEINE-EKORG` = org. compras (con setFocus/caret).
   - SendVKey 0 (Enter).
   - `wnd[0]/tbar[1]/btn[8]` (Boton Condiciones).
   - Si aparece popup `wnd[1]/tbar[0]/btn[7]`, presionarlo (manejo tolerante: puede no aparecer).
   - `wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[CONDITION_ROW,0]` = nuevo precio (formato con punto decimal; en BDC el ABAP usa formato 11,2 sin separador, `src/...:890-891`).
   - (Opcional, según el recording: `KONP-KPEIN`, `KONP-KONWA`, `KONP-KMEIN`, DATAB/DATBI.)
   - `wnd[0]/tbar[0]/btn[11]` (Guardar, F11).
   - Leer `wnd[0]/sbar` → si contiene "error"/"no se pudo", marcar la fila como ERROR con el mensaje; si no, OK.
3. **Log por fila**: resultado en Excel (columnas Resultado/Log) y archivo de log en `%TEMP%` (patrón VBA) o en el área de log de la GUI (patrón sapCondMassMod).
4. **Delay entre registros** (p. ej. 1000 ms, configurable).
5. **Post-proceso (opcional):** ejecutar `RM06INP0` (transacción estándar que resincroniza EINE-NETPR) — preguntar al usuario si debe incluirse y cómo (manual o automatizado).
6. **Cierre** (patrón `sapCondMassMod/sap.py:76-87`): `CloseSession('ses[0]')` y `taskkill /f /im saplogon.exe` (o cerrar solo la sesión, dejando la app).

> **Nota sobre variantes de pantalla:** el VBA usa `tblSAPMV13ATCTRL_D0201` mientras el BDC/LSMW de la investigación usan `SAPLV14A 0102` (`src/...:884-887`; `research/03:536`). Depende de la versión/customización del sistema destino. **Regla práctica:** grabar un recording propio (SHDB sobre ME12) en el sistema destino para confirmar IDs y fila de la condición (recomendación explícita de `scripts/README_gui_scripting.md:134-135`).

---

## 7. Qué reutilizar del ABAP entregado vs. del VBA existente

### Reutilizar del ABAP (`src/zr_mass_actualiza_precio_cond.abap`)
1. **Estructura del CSV** de 12 columnas (referencia de datos) y las **reglas de validación** (MARA, LFA1, EINA/EINE con LOEKZ<>'L', TCURC) — portables como validadores Python (`src/...:229-273`, `:301-461`).
2. **Defaults de negocio**: KSCHL=PB00, PEINH=1, DATAB=hoy, DATBI=99991231, KONWA desde EINE (`src/...:431-442`).
3. **El concepto de test run** (`p_test`) → el script Python debe ofrecer un modo "solo validación" que NO guarde (análogo al `p_test='X'`; el reporte NO llama al FM en test, `src/...:516-520`).
4. **La sección "Alternativa 2: BDC sobre ME12"** (`src/...:840-911`): documenta los dynpros, campos y OK-CODES (`RM06I-INFNR`, `=VW1`, `KONP-KBETR`, `KPEIN`, `=SICH`) que son la referencia técnica de las pantallas a automatizar.
5. **Los campos de la Z-tabla de log** (`src/...:690-714`) como modelo de las columnas de Resultado/Log del script Python (MATNR, LIFNR, EKORG, WERKS, INFNR, KSCHL, KBETR_NEW, KONWA, PEINH, KMEIN, DATAB, DATBI, MSGTY, MSGID/MSGNO, TCODE).

### Reutilizar del VBA (`scripts/me12_price_change.vba` + `README_gui_scripting.md`)
1. **Los IDs del recording de ME12** (tabla del §2.4 / `vba:381-388`).
2. **El flujo completo de pantalla por registro** y la **estructura del Excel de entrada** (hoja "Datos").
3. **La verificación de la barra de estado** (`wnd[0]/sbar`) para detectar errores (`vba:294-307`).
4. **Las configuraciones**: `CONDITION_ROW`, delays, log en `%TEMP%`.
5. **Las advertencias del README de scripting** (autorizaciones M_EINK/M_EIKO, `sapgui/user_scripting=TRUE`, probar con 1 registro, no tocar SAP GUI durante la corrida; `README_gui_scripting.md:9-21`, `:76-81`, `:117-135`).

### Copiar del proyecto `sapCondMassMod`
- Login / logout / cierre de programa (`sap.py`), `.env`, GUI PySide2 (o CLI), validadores pandas, log en GUI, confirmación antes de ejecutar (`main.py:57-71`).

---

## 8. Riesgos y reglas de oro aplicables

### 8.1 Del README de scripting GUI (`scripts/README_gui_scripting.md`)
1. **Modifica datos de producción → backup previo y bajo responsabilidad** (`:129`).
2. **SAP no soporta oficialmente GUI Scripting para procesos productivos críticos** (`:131`).
3. **Probar siempre en Desarrollo/Quality primero** y con **1 solo registro** (`:133`, `:78-79`).
4. **Frágil ante cambios de pantalla / versión / customizaciones** (`:120`). Grabar recording propio en el sistema destino (`:134-135`).
5. **Requiere `sapgui/user_scripting = TRUE`** en RZ11 (gestionado por Basis) (`:11-13`).
6. **Requiere autorizaciones M_EINK (consulta info records) y M_EIKO (org. de compras)** (`:19-21`). Nota: `M_BANF` es de solicitudes de compra y NO aplica (`README.md:102`).
7. **No tocar SAP GUI mientras corre el script** (`:81`).
8. **Validar con ME13, ME1E y KONP después** de la corrida (`:84-87`).
9. **El `CONDITION_ROW` puede variar** según condiciones existentes/versión; **no maneja múltiples condiciones del mismo tipo** en la tabla (`:124-125`).
10. **Velocidad ~1-2 s por registro** (`:119`).

### 8.2 Del README principal del proyecto (`README.md`)
1. **`MARC-NETPR` no existe**; el precio de compra real es `EINE-NETPR` + condición PB00 (`README.md:83`).
2. **NO escribir SQL directo sobre KONH/KONP/A017/A018/A025** (riesgo alto, sin soporte) (`:84`).
3. **NO usar `BAPI_PRICES_CONDITIONS`** (nota SAP 1135984) (`:85`).
4. **NO usar `ME_INFORECORD_MAINTAIN_MULTI` para precios** (KBA 3659315); `ME_INFORECORD_MAINTAIN` (single) procesa condiciones pero está **obsoleto** (KBA 2787315) — verificar SE37 antes de depender del reporte Z (`:86`).
5. **`BAPI_INFORECORD_CHANGE` no confirmado como BAPI liberado** — verificar SE37 (`:87`).
6. **Después de cambiar condiciones → ejecutar `RM06INP0`** (RM06ENP0 contratos, RM06ENP1 scheduling agreements) para resincronizar EINE-NETPR/PEINH/WAERS (KBA 685117, 2892806) (`:88`).
7. **Los POs ya creados no cambian** (`:89`).
8. **Validez/escalas:** las condiciones son dependientes de tiempo; un cambio simple puede requerir vencimiento de la validez actual + creación de nueva (`:90`).
9. **EINE-NETPR no es la fuente del pricing del PO** — verificar la condición (MEK3/ME1E) y un PO de prueba, no solo NETPR (`:91`).
10. **Config previa obligatoria:** M/06 (PB00 cálculo tipo 'C', "cambios permitidos" = valor) y M/08 (procedimiento RM0000) — sin esto ME12/MEKP no deja grabar (`:98-99`).

### 8.3 De la investigación (`research/01-03`)
- La cascada correcta es: **condición PB00/PB01 (KONP/A017/A018) → `EINE-NETPR` (vía `RM06INP0`/`ME_UPDATE_INFORECORD_COND`)** (`research/02:22`).
- MEKP es la vía manual estándar recomendada para el masivo puntual; el scripting GUI sobre ME12 es la automatización "tolerada" (`research/02:74-78`, `:96-99`).
- Para escalas/múltiples valideces: BDC sobre ME12 o pila `RV_CONDITION_COPY/SAVE/RESET` (`research/03:36`, `:621`).
- LSMW recording ME12 documenta los campos grabados (selección `RM06I-INFNR`, pestaña condiciones `SAPLV14A` con KSCHL=PB00, `KONP-KBETR/KPEIN/KMEIN/KONWA`, fechas) — referencia para el recording Python (`research/03:530-536`).

---

## 9. Preguntas abiertas para el usuario

1. **Transacción a automatizar:** ¿ME12 directo (recomendado, como el VBA) o ejecutar el reporte Z `ZR_MASS_ACTUALIZA_PRECIO_COND` desde SA38 (reutilizando la lógica ABAP)? ¿O MEKP como flujo masivo estándar?
2. **Formato de entrada:** ¿Excel (hoja "Datos", como el VBA/sapCondMassMod) o CSV `;` (como el ABAP)? ¿Se incluye la columna **WERKS (planta)**? El VBA actual asume info records **sin planta** (a nivel EKORG); el ABAP soporta planta (A017). ¿El negocio usa info records con planta?
3. **UI o CLI:** ¿GUI de escritorio (PySide2, como `sapCondMassMod`) o interfaz de línea de comandos/script? ¿Credenciales por `.env` o pantalla de login manual en SAP GUI?
4. **Modo test:** ¿El script debe ofrecer una primera pasada "solo validación" (análoga al `p_test='X'` del reporte ABAP) antes de la corrida productiva?
5. **RM06INP0:** ¿El script debe ejecutar `RM06INP0` automáticamente al final (regla de oro del proyecto) o se deja como paso manual del usuario?
6. **INFNR:** ¿El usuario conoce el número de info record (columna INFNR) o se busca por clave MATNR/LIFNR/EKORG? (El VBA busca por clave; el ABAP permite ambos.)
7. **Escalas/múltiples valideces:** ¿El cambio es siempre precio plano PB00, o hay casos con escalas de cantidad (KONM) o vencimiento + nueva validez? (Si los hay, el flujo ME12 simple no basta: requiere BDC/vencimiento o `RV_CONDITION_COPY`.)
8. **Sistema destino:** ¿ECC o S/4HANA? ¿Versión del SAP GUI? ¿Está habilitado `sapgui/user_scripting=TRUE` (RZ11)? ¿Existe el reporte Z transportado? ¿`ME_INFORECORD_MAINTAIN` existe en SE37?
9. **Autorizaciones:** ¿El usuario de ejecución tiene `M_EINK` y `M_EIKO` (y actividad 01-02) para la org. de compras correspondiente?
10. **Condición:** ¿Confirmar en M/06 que **PB00** (y PB01 si aplica) está configurado como tipo de condición con "cambios permitidos" = valor? (PB01 es ambiguo según la investigación — `research/01:79-83`.)

---

## 10. Referencias de archivos citados

- `src/zr_mass_actualiza_precio_cond.abap` (reporte ABAP entregado, 911 líneas).
- `research/01_data_model_mm42.md` (modelo de datos: EINA/EINE, A017/A018, KONH/KONP, PB00/PB01, RM06INP0).
- `research/02_apis_actualizacion_masiva.md` (alternativas de API: MEKP, ME_INFORECORD_MAINTAIN, BDC, OData).
- `research/03_mejor_practica_ejemplo.md` (mejor práctica: firma del FM, BDC/LSMW sobre ME12, notas SAP 1135984/3659315/2787315).
- `scripts/me12_price_change.vba` (precedente VBA de scripting ME12).
- `scripts/README_gui_scripting.md` (documentación del scripting GUI, IDs del recording, limitaciones).
- `README.md` (guía de decisión, advertencias críticas, checklist QA).
- `changelog.md` (review APPROVED del reporte ABAP; pendientes de validación SE37/SE11).
- `C:\Users\agarcia\dev\sapCondMassMod\sap.py`, `main.py`, `sap_vk12_massmod.py`, `validators.py`, `README.md` (patrón Python a copiar: login/logout/cierre, GUI, validación, flujo masivo).
