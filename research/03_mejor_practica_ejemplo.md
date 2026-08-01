# Investigación técnica: actualización masiva del precio neto (condiciones PB00/PB01) en la vista compras del material maestro

**Pregunta de investigación**: "Para actualizar masivamente el precio neto (condición PB00/PB01 de la vista compras del material maestro, la de MM42) de varios materiales, ¿cuál es la MEJOR PRÁCTICA SAP y cómo se ve un reporte ABAP de ejemplo?"

**Fecha**: 2026-08-01
**Estado**: Investigación (NO es la entrega final — se documenta el enfoque recomendado y un esqueleto ilustrativo)

---

## 0. Aclaración conceptual importante (VERIFICADO con fuentes SAP)

El precio que se ve en la vista compras del material maestro (MM02/MM42, pantalla "Datos de compras") **no es un campo editable del material maestro**: proviene de la **condición de precio del registro de información de compras (info record)** y se mantiene con los T-codes:

| Objeto | T-code | Notas |
|---|---|---|
| Crear / modificar registro de información (infosatz) | **ME11 / ME12 / ME13** | Los precios PB00/PB01 viven aquí, en la pestaña "Condiciones" |
| Mantenimiento de condiciones de compras (tablas de condiciones) | **MEK1 (crear) / MEK2 (cambiar) / MEK3 (mostrar)** | Aplicación `M` (purchasing), condición PB00 (precio bruto) / PB01 (descuento) |
| Historial de precios | **ME1E / ME1M / ME1L** | Muestra el historial de precios por material/proveedor |
| Cambio masivo de condiciones del info record | **MEKP / MASS** | Herramienta estándar de cambio masivo |

- Los campos `NETPR`/`PEINH` de la tabla **EINE** (registro de información por organización de compras) se alimentan desde la condición de precio; si se cambia solo `EINE-NETPR` directamente **no se genera el registro de condición** (KONH/KONP) y **ME1E no muestra nada**. Esto está documentado en hilos de SAP Community (ver fuentes [C3], [C6]).

> Conclusión: "cambiar el precio en MM42" técnicamente significa **mantener la condición PB00/PB01 del info record del proveedor/material/planta**. Toda la discusión de abajo aplica a eso.

---

## 1. Recomendación de SAP: ¿BDC / FM / BAPI / IDoc / LSMW?

### 1.1 Resumen de la mejor práctica (VERIFICADO con fuentes)

No existe un BAPI "perfecto" para condiciones de compra. Las evidencias de SAP y la comunidad convergen en lo siguiente:

1. **`BAPI_PRICES_CONDITIONS` NO debe usarse.** La nota SAP **1135984** dice textualmente: *"When you use this function module, inconsistencies may occur; you should therefore not use it!"* (VERIFICADO, citado en [C4], [C5], [C7]). Además no maneja solapamiento de valideces, no genera historial de condiciones por sí solo y hay que llamar `RV_KONDITION_SICHERN_V13A` para actualizar el historial (VERIFICADO, [C7]).
2. **`ME_INFORECORD_MAINTAIN_MULTI` NO puede crear/actualizar condiciones** en info records — solo los datos generales/org de compras. VERIFICADO con SAP KBA **3659315** ([C1]). Su uso masivo está pensado para crear/actualizar el info record; la condición hay que tratarla aparte.
3. **`ME_INFORECORD_MAINTAIN` SÍ procesa condiciones** (parámetros `COND_VALIDITY`, `CONDITION`, `COND_SCALE_VALUE`, `COND_SCALE_QUAN`) y usa la lógica estándar de ME11/ME12, pero es **lento y frágil**: hay notas conocidas de problemas (**2787315**) y problemas de rendimiento cuando un info record tiene muchas valideces (VERIFICADO, [C2], [C10]).
4. **Para CASCADAS/ESCALAS** (scales, p. ej. precios por cantidad) la vía robusta sigue siendo **BDC sobre ME12** o **IDoc COND_A01** (VERIFICADO, [C3], [C5]).
5. **Para S/4HANA moderno**: SAP recomienda **LTMC/LTMC o LTMC con objeto de migración estándar** (nuevo LSMW), y a nivel API la familia **CND_** (p. ej. `CND_PRICES_DETAILS_SAVE`, clases `CL_CND_...`) — VERIFICADO parcialmente, mencionado en [C6]; se debe validar la versión del sistema.
6. **La vía que "recomienda SAP" para cambio masivo de precios de info records sin código es el programa batch input estándar `RM06IBI0`** (carga de info records con condiciones) y/o **IDoc `INFREC` + `COND_A`** (VERIFICADO, [C1], [C2], [C10]).

### 1.2 Árbol de decisión

```text
¿Hay registro de información (info record) existente?

├─ NO (se crea info record + precio):
│     ─ LSMW/LTMC con programa estándar RM06IBI0  (masivo, sin código)
│     ─ ME_INFORECORD_MAINTAIN_MULTI (crea info record) + condición aparte
│     ─ IDoc INFREC01 + COND_A01
│
└─ SÍ (solo cambiar el precio PB00/PB01):

    ¿El precio se mantiene por proveedor/material/planta (info record)
    y hay condiciones con validez/escalas?

    ├─ Sin escalas (solo precio simple PB00):
    │     ─ BAPI_INFORECORD_CHANGE / BAPI_INFORECORD_MAINTAIN con
    │       PRICECONDITIONS + PRICECONDITIONSX   (soporte limitado de condiciones, ver nota)
    │     ─ ME_INFORECORD_MAINTAIN con tabla CONDITION  (lógica ME12, lento)
    │
    ├─ Con escalas / múltiples valideces:
    │     ─ BDC sobre ME12 (recording SHDB + CALL TRANSACTION o LSMW recording)
    │     ─ IDoc COND_A01
    │
    └─ ¿Solo una condición con KNUMH ya conocido (tabla KONP)?
          ─ ME_UPDATE_INFORECORD_COND  (actualiza NETPR del info record)
          ─ RV_CONDITION_COPY + RV_CONDITION_SAVE + RV_CONDITION_RESET
            (mantenimiento de condiciones "como VK11/MEK1", maneja solapamiento)
          ─ ⚠ BAPI_PRICES_CONDITIONS  → EVITAR (nota 1135984)

Volumen de datos:
  - Volumen alto (>miles) en background → BDC/LSMW en background (SM35) o IDoc.
  - Volumen medio, con control transaccional → reporte ABAP con FM/BAPI y
    BAPI_TRANSACTION_COMMIT por paquete.

Sin código en absoluto:
  - LSMW con recording de ME12 (o ME11), o LTMC con objeto de migración estándar.
  - MASS / MEKP para cambio masivo manual.
```

### 1.3 Cuándo usar cada mecanismo (VERIFICADO salvo indicación)

| Mecanismo | Cuándo usarlo | Problemas / notas |
|---|---|---|
| **BDC / recording (SHDB, LSMW)** | Cambio masivo de precios con escalas o múltiples valideces; cuando los FM/BAPI fallan; sin developers disponibles | Frágil a cambios de pantalla; lento (cada transacción es un dynpro); la lógica de precios la hace el programa estándar (correcto) |
| **ME_INFORECORD_MAINTAIN** | Crear/actualizar info records con sus condiciones (lógica ME11/ME12) en ABAP | Lento con muchos períodos de validez; notas 2787315, errores ME816, ME819 |
| **ME_INFORECORD_MAINTAIN_MULTI** | Crear info records masivos | **NO toca condiciones** (KBA 3659315) |
| **BAPI_INFORECORD_CHANGE / _MAINTAIN** | BAPI estándar "oficial" para info records; soporta `PRICECONDITIONS` | Soporte de condiciones limitado/incómodo; muchos prefieren ME_INFORECORD_MAINTAIN para condiciones |
| **ME_UPDATE_INFORECORD_COND** | Actualizar solo el precio del info record (EINE-NETPR) desde una condición ya existente | Solo actualiza el precio, **no crea** el registro de condición ni llena historial ME1E (VERIFICADO [C3]) |
| **RV_CONDITION_COPY + RV_CONDITION_SAVE + RV_CONDITION_RESET** | Mantener condiciones de compras (aplicación `M`) de forma "como transacción MEK1", con manejo de solapamiento de valideces | Hay que armar KOMG/KOMK/KOMP/T_KOMV manualmente; `MAINTAIN_MODE A/B`; `OVERLAP_CONFIRMED` |
| **BAPI_PRICES_CONDITIONS** | ❌ No recomendado | Nota 1135984; inconsistencias; no maneja overlaps; requiere `RV_KONDITION_SICHERN_V13A` para historial |
| **IDoc COND_A01 (IDOC_INPUT_COND_A)** | Migración SAP→SAP de condiciones con valideces | Campo E1KOMG-KAPPL debe ser `M`; revisar condición PB00 en M/06 (VERIFICADO [C8]) |
| **LSMW (recording ME12)** | Sin código, volúmenes medios, con plantillas | Ver sección 5 |
| **LTMC / LTMOM (S/4HANA)** | Migración estándar moderna en S/4HANA | Requiere objeto de migración estándar para info records |

---

## 2. Firma verificada de las APIs

### 2.1 `ME_INFORECORD_MAINTAIN` (VERIFICADO — SAP Community [C3], ABAPforum [C9])

- **Función**: crear/actualizar registro de información (lógica ME11/ME12), **incluida la condición de precio**.
- Grupo de funciones: `MEWIPIR` (lógica de info records modernizada). Firma (fragmento relevante):

```abap
CALL FUNCTION 'ME_INFORECORD_MAINTAIN'
  EXPORTING
    i_eina            = ls_eina      " TYPE MEWIEINA   (general: MATNR, LIFNR, ...)
    i_einax           = ls_einax     " TYPE MEWIEINAX  (flags X para campos)
    i_eine            = ls_eine      " TYPE MEWIEINE   (org. compras: EKORG, WERKS, INFNR, ...)
    i_einex           = ls_einex     " TYPE MEWIEINEX  (flags X)
    testrun           = lv_test      " 'X' = no graba
  IMPORTING
    e_eina            = le_eina
    e_eine            = le_eine
  TABLES
    txt_lines         = lt_txt_lines       " TYPE MEWIPIRTEXT_TT
    cond_validity     = lt_cond_validity   " TYPE MEWIVALIDITY_TT   (DATAB/DATBI por infrate)
    condition         = lt_condition       " TYPE MEWICONDITION_TT  (COND_TYPE='PB00', COND_VALUE, ...)
    cond_scale_value  = lt_cond_scale_value " TYPE MEWISCALEVAL_TT   (escalas)
    cond_scale_quan   = lt_cond_scale_quan  " TYPE MEWISCALEQUAN_TT  (escalas)
    return            = lt_return.         " TYPE MEWI_TT_RETURN
```

Campos clave de `MEWICONDITION` (estructura de la condición): `SERIAL_ID`, `INFO_REC`, `COND_COUNT`, `COND_TYPE` (PB00), `COND_VALUE` (precio), `CURRENCY`, `COND_P_UNT` (PEINH), `COND_UNIT`, `CHANGE_ID` ('I'/'U'/'X'). VERIFICADO en [C3], [C9].

### 2.2 `ME_INFORECORD_MAINTAIN_MULTI` (VERIFICADO — KBA 3659315 [C1], SAP Community [C2])

```abap
CALL FUNCTION 'ME_INFORECORD_MAINTAIN_MULTI'
  IMPORTING
    et_eina  = lt_eina_e     " TYPE MEWIEINA_MIG_T
    et_eine  = lt_eine_e     " TYPE MEWIEINE_T
  TABLES
    t_eina        = lt_eina        " TYPE MEWIEINA_MIG_T
    t_einax       = lt_einax
    t_eine        = lt_eine
    t_einex       = lt_einex
    cond_validity = lt_cond_validity
    condition     = lt_condition
    return        = lt_return.     " TYPE FS4MIG_T_BAPIRET2
```

> ⚠ KBA 3659315: **NO se pueden crear/actualizar condiciones** con este FM. Si necesitas precios, usa ME11/ME12 (BDC), IDoc INFREC, o `ME_INFORECORD_MAINTAIN` (single, con condición).

### 2.3 `BAPI_INFORECORD_CHANGE` / `BAPI_INFORECORD_MAINTAIN` (parcialmente VERIFICADO — estructuras MEIRPRCGCONDREC/X [C11]; firma genérica del BAPI = conocimiento previo a confirmar en SE37)

Parámetros del BAPI (estándar de info records de compras, grupo `INFORECORD`):

```abap
CALL FUNCTION 'BAPI_INFORECORD_CHANGE'
  EXPORTING
    inforecordchange        = ls_inforecordchange   " TYPE BAPI_IR_CHANGE (INFNR, ...)
    inforecordchangex       = ls_inforecordchangex  " TYPE BAPI_IR_CHANGE_X
  IMPORTING
    inforecordnumber        = lv_infnr              " TYPE BAPI_IR_DATA-MATERIAL  (retorno)
  TABLES
    priceconditions         = lt_priceconditions    " TYPE MEIRPRCGCONDREC_T
    priceconditionsx        = lt_priceconditionsx   " TYPE MEIRPRCGCONDRECX_T
    pricevalidity           = lt_pricevalidity      " TYPE MEIRPRCGVALIDITY_T
    pricescales             = lt_pricescales        " TYPE MEIRPRCGSCALE_T
    pricescalesx            = lt_pricescalesx
    return                  = lt_return.            " TYPE BAPIRET2_T
```

**Estructura `MEIRPRCGCONDREC` (registro de condición del info record)** — campos clave (VERIFICADO por nombres en [C11]; el resto conocimiento previo a confirmar en SE11):

| Campo | Data element | Descripción |
|---|---|---|
| CONDITIONAPPLICATION | KAPPL | Aplicación (debe ser `M`) |
| CONDITIONCOUNT | KOPOS | Nº de línea de la condición |
| CONDITIONTYPE | KSCHL | Tipo de condición (PB00 / PB01) |
| CONDITIONRECORD | KNUMH | Nº de registro de condición |
| CONDITIONVALIDFROM | DATAB | Válido desde |
| CONDITIONVALIDTO | DATBI | Válido hasta |
| CONDITIONVALUE | KBETR | Valor de la condición (precio) |
| CONDITIONCURRENCY | KONWA | Moneda |
| CONDITIONPRICINGUNIT | KPEIN | Unidad de precio |
| CONDITIONUNIT | KMEIN | Unidad de medida |
| PRICINGSCALEBASIS | KZBZG | Escala base |
| PRICINGSCALELINE | KLF_KAL | Nº de escala |

**Estructura `MEIRPRCGCONDRECX`**: misma lista + flags `BAPIUPDATE` ('X' = a actualizar) para cada campo.

### 2.4 `BAPI_PRICES_CONDITIONS` (VERIFICADO — sapdatasheet [C12], SAP Community [C4])

```abap
CALL FUNCTION 'BAPI_PRICES_CONDITIONS'
  EXPORTING
    pi_initialmode       = lv_initial  " XFELD
    pi_blocknumber       = lv_blk      " BAPICRMDH2-BLOCKNO
    pi_physical_deletion = lv_del      " XFELD
  TABLES
    ti_bapicondct  = lt_bapicondct   " TYPE BAPICONDCT  (tabla de condiciones: TABLE_NO, COND_USAGE='A', APPLICATIO='M', COND_TYPE, OPERATION='004'/'009', VAKEY, VALID_FROM/TO, COND_NO)
    ti_bapicondhd  = lt_bapicondhd   " TYPE BAPICONDHD  (KONH: KNUMH, VAKEY, fechas)
    ti_bapicondit  = lt_bapicondit   " TYPE BAPICONDIT  (KONP: COND_VALUE=KBETR, COND_CURR, COND_P_UNT, COND_UNIT)
    ti_bapicondqs  = lt_bapicondqs   " TYPE BAPICONDQS  (KONM escalas)
    ti_bapicondvs  = lt_bapicondvs   " TYPE BAPICONDVS  (KONW escalas)
    to_bapiret2    = lt_ret          " TYPE BAPIRET2
    to_bapiknumhs  = lt_knumhs       " TYPE BAPIKNUMHS
    to_mem_initial = lt_mem_initial
  EXCEPTIONS
    update_error = 1
    OTHERS       = 2.
```

- OPERATION: `009` = crear, `004` = cambiar, `003` = borrar (VERIFICADO [C4]).
- ⚠ NO usar según nota 1135984.

### 2.5 `RV_CONDITION_COPY` / `RV_CONDITION_MAINTENANCE` / `RV_CONDITION_SAVE` / `RV_CONDITION_RESET` (VERIFICADO — sapdatasheet [C13], SAP Community [C5], [C7])

La pila usada internamente por ME12/MEK1 (VERIFICADO [C5], [C7]):

```abap
CALL FUNCTION 'RV_CONDITION_COPY'
  EXPORTING
    application         = 'M'               " Aplicación compras (KAPPL)
    condition_table     = lv_kotabnr        " Tabla de condiciones (A017/A018/A025 → '017'/'018'/'025')
    condition_type      = 'PB00'            " KSCHL
    date_from           = lv_datab
    date_to             = lv_datbi
    enqueue             = 'X'
    i_komk              = ls_komk
    i_komp              = ls_komp
    key_fields          = ls_komg           " KOMG: MATNR, LIFNR, EKORG, WERKS, ... (clave del infrate)
    maintain_mode       = 'A'               " A=crear B=cambiar C=mostrar
    no_authority_check  = 'X'
    no_field_check      = 'X'
    selection_date      = sy-datum
    keep_old_records    = 'X'
    overlap_confirmed   = 'X'
  IMPORTING
    e_komk   = ls_komk
    e_komp   = ls_komp
    new_record = lv_new_record
  TABLES
    copy_records = lt_komv                  " TYPE KOMV (con KBETR, KPEIN, KMEIN, WAERS, KRECH)
  EXCEPTIONS
    enqueue_on_record      = 1
    invalid_application    = 2
    invalid_condition_number = 3
    invalid_condition_type = 4
    no_authority_ekorg     = 5
    no_authority_kschl     = 6
    no_authority_vkorg     = 7
    no_selection           = 8
    table_not_valid        = 9
    OTHERS                 = 99.

CALL FUNCTION 'RV_CONDITION_SAVE'.   " graba (vía update task)
CALL FUNCTION 'RV_CONDITION_RESET'.  " limpia buffers
COMMIT WORK.
```

- `RV_CONDITION_MAINTENANCE`: alternativa directa para **cambiar** una condición existente (`RECORD_NUMBER` = KNUMH, `MAINTAIN_MODE` = 'B', `KEY_FIELDS` = KOMG). VERIFICADO [C13].

### 2.6 `ME_UPDATE_INFORECORD_COND` (VERIFICADO — sapdatasheet [C14], [C3])

- Parámetro: **tabla `REINE` de tipo `EINE`** (una fila por infrate a actualizar: `INFNR`, `EKORG`, `WERKS`, `ESOKZ`, `NETPR`, `PEINH`, `WAERS`, `BPRME`, `PRDAT`).
- ⚠ Solo actualiza el precio del info record (EINE-NETPR); **no crea/actualiza KONH/KONP** → ME1E no muestra historial (VERIFICADO [C3]).

### 2.7 `ME_CONDITION_MAINTAIN` (⚠ CONOCIMIENTO PREVIO — NO verificado en la web)

El FM `ME_CONDITION_MAINTAIN` (grupo de funciones `MECI` / lógica de condiciones de infosatz) mantiene condiciones de compras a partir de las estructuras de comunicación de pricing. Firma que se debe confirmar en SE37 (conocimiento previo, sin fuente externa encontrada):

```abap
CALL FUNCTION 'ME_CONDITION_MAINTAIN'
  EXPORTING
    komg            = ls_komg     " CLAVE (MATNR, LIFNR, EKORG, WERKS,...)
    komk            = ls_komk
    komp            = ls_komp
    wa_komv         = ls_komv
    kvorg           = lv_kvorg    " evento (p.ej. 'ME12')
    kposi           = lv_kposi
    maintain_mode   = lv_mode     " 'A' crear / 'B' cambiar
    reset           = abap_false
    xkomg           = lv_xkomg
    xkomk           = lv_xkomk
    xkomp           = lv_xkomp
  IMPORTING
    wa_komv         = ls_komv
  TABLES
    t_komv          = lt_komv
  EXCEPTIONS
    no_condition    = 1
    OTHERS          = 2.
```

> ⚠ **IMPORTANTE**: NO se encontró documentación/ejemplo externo fiable de `ME_CONDITION_MAINTAIN`; el patrón documentado y probado en la web para compras es `ME_INFORECORD_MAINTAIN` (+`CONDITION`), la pila `RV_CONDITION_*`, el BAPI `BAPI_INFORECORD_*`, o BDC. Verificar firma exacta con SE37 en el sistema destino antes de usarlo.

---

## 3. Esqueleto de reporte ABAP de ejemplo (ilustrativo, NO final)

**Opción recomendada** para el caso más común (info records existentes, precio simple PB00, volumen medio): **`BAPI_INFORECORD_CHANGE` con `PRICECONDITIONS`**, con **modo test**, **commit/rollback por registro** y **log de aplicación (BAL) + tabla Z**. Se incluye también el patrón BDC como alternativa cuando haya escalas.

### 3.1 Selección y estructura de entrada

```abap
REPORT zr_mass_pir_price.

TYPES: BEGIN OF ty_in,
         matnr TYPE matnr,      " Material
         lifnr TYPE lifnr,      " Proveedor
         ekorg TYPE ekorg,      " Org. de compras
         werks TYPE werks_d,    " Planta
         infnr TYPE infnr,      " Nº infote (opcional, derivable)
         kschl TYPE kschl,      " PB00 / PB01
         kbetr TYPE kbetr,      " Nuevo precio
         konwa TYPE konwa,      " Moneda
         peinh TYPE kpein,      " Unidad de precio
         kmein TYPE kmein,      " Unidad de medida
         datab TYPE datab,      " Válido desde
         datbi TYPE datbi,      " Válido hasta
       END OF ty_in.

TYPES: ty_in_t TYPE STANDARD TABLE OF ty_in WITH EMPTY KEY.

" --- Input: ALV con tabla interna (o archivo Excel/CSV vía gui_upload) ---
DATA gt_input TYPE ty_in_t.

SELECTION-SCREEN BEGIN OF BLOCK b1 WITH FRAME TITLE TEXT-b01.
PARAMETERS: p_file  TYPE rlgrap-filename LOWER CASE,  " archivo Excel/CSV (opcional)
            p_test  TYPE abap_bool DEFAULT abap_true, " test run
            p_pkg   TYPE i DEFAULT 50,               " tamaño de paquete
            p_alv   TYPE abap_bool DEFAULT abap_true. " mostrar datos en ALV
SELECTION-SCREEN END OF BLOCK b1.
```

```abap
" --- Carga desde archivo CSV/Excel (legado) ---
DATA lt_csv TYPE TABLE OF string.
DATA ls_in  TYPE ty_in.

IF p_file IS NOT INITIAL.
  CALL METHOD cl_gui_frontend_services=>gui_upload
    EXPORTING filename = p_file
    CHANGING  data_tab = lt_csv.
  LOOP AT lt_csv INTO DATA(lv_line) FROM 2.            " salta cabecera
    SPLIT lv_line AT ';' INTO DATA(lv_mat) lv_lif lv_ekorg
                              lv_werks lv_kschl lv_kbetr lv_konwa
                              lv_peinh lv_kmein lv_datab lv_datbi.
    ls_in = VALUE #( matnr = lv_mat lifnr = lv_lif ekorg = lv_ekorg
                     werks = lv_werks kschl = lv_kschl kbetr = lv_kbetr
                     konwa = lv_konwa peinh = lv_peinh kmein = lv_kmein
                     datab = lv_datab datbi = lv_datbi ).
    " ALPHA conversions
    ls_in-matnr = |{ ls_in-matnr ALPHA = IN }|.
    ls_in-lifnr = |{ ls_in-lifnr ALPHA = IN }|.
    APPEND ls_in TO gt_input.
  ENDLOOP.
ENDIF.

" --- Validación previa de datos (matriz de validación) ---
"   1) Material existe en MARA
"   2) Proveedor existe en LFA1 (MARA/LFA1 con ALPHA=IN)
"   3) Info record existe (EINA/EINE por MATNR+LIFNR+EKORG+WERKS)
"   4) Moneda válida (TCURC), unidades válidas (T006)
"   5) Datab <= Datbi; precio > 0; condición PB00 configurada (M/06)
"   6) Autorización S_LCD? / M_BANF... (autorización de org. compras)
```

```abap
" --- Validación con SELECTS 7.40+ (@, tablas internas) ---
DATA lt_mara TYPE SORTED TABLE OF mara WITH UNIQUE KEY matnr.
DATA lt_eina TYPE SORTED TABLE OF eina WITH UNIQUE KEY matnr lifnr.
DATA lt_eine TYPE SORTED TABLE OF eine WITH UNIQUE KEY infnr ekorg werks.

SELECT matnr FROM mara INTO TABLE @lt_mara
  FOR ALL ENTRIES IN @gt_input
  WHERE matnr = @gt_input-matnr.

SELECT eina~matnr, eina~lifnr, eina~infnr FROM eina
  INNER JOIN eine ON eine~infnr = eina~infnr
  INTO TABLE @lt_eina
  FOR ALL ENTRIES IN @gt_input
  WHERE eina~matnr = @gt_input-matnr
    AND eina~lifnr = @gt_input-lifnr
    AND eine~ekorg = @gt_input-ekorg
    AND eine~werks = @gt_input-werks.

LOOP AT gt_input ASSIGNING FIELD-SYMBOL(<fs_in>).
  IF NOT line_exists( lt_mara[ matnr = <fs_in>-matnr ] ).
    <fs_in>-msg = 'Material no existe'.           " columna mensaje
    CONTINUE.
  ENDIF.
  IF NOT line_exists( lt_eina[ matnr = <fs_in>-matnr
                               lifnr = <fs_in>-lifnr ] ).
    <fs_in>-msg = 'No hay info record'.           " ⚠ decide: crear o abortar
    CONTINUE.
  ENDIF.
ENDLOOP.
```

### 3.2 Procesamiento con BAPI_INFORECORD_CHANGE (opción recomendada, ilustrativo)

```abap
" --- BAPI: por cada fila válida ---
DATA lt_priceconditions  TYPE TABLE OF meirprcgcondrec.
DATA lt_priceconditionsx TYPE TABLE OF meirprcgcondrecx.
DATA lt_return           TYPE TABLE OF bapiret2.
DATA ls_inforecordchange TYPE bapi_ir_change.
DATA lv_infnr            TYPE bapi_ir_data-material.

LOOP AT gt_input ASSIGNING <fs_in> WHERE msg IS INITIAL.

  REFRESH: lt_priceconditions, lt_priceconditionsx, lt_return.
  CLEAR:   ls_inforecordchange.

  " clave: Nº de infote + X-flag para el campo del infote (solo cambio de precio)
  ls_inforecordchange-inforecord = <fs_in>-infnr.

  " condición de precio (PB00/PB01)
  APPEND VALUE #( conditionapplication = 'M'
                  conditiontype        = <fs_in>-kschl
                  conditionvalidfrom   = <fs_in>-datab
                  conditionvalidto     = <fs_in>-datbi
                  conditionvalue       = <fs_in>-kbetr
                  conditioncurrency    = <fs_in>-konwa
                  conditionpricingunit = <fs_in>-peinh
                  conditionunit        = <fs_in>-kmein )
         TO lt_priceconditions.

  APPEND VALUE #( conditionapplication = 'X'
                  conditiontype        = 'X'
                  conditionvalidfrom   = 'X'
                  conditionvalidto     = 'X'
                  conditionvalue       = 'X'
                  conditioncurrency    = 'X'
                  conditionpricingunit = 'X'
                  conditionunit        = 'X' )
         TO lt_priceconditionsx.

  CALL FUNCTION 'BAPI_INFORECORD_CHANGE'
    EXPORTING
      inforecordchange  = ls_inforecordchange
      inforecordchangex = ls_inforecordchangex
    IMPORTING
      inforecordnumber  = lv_infnr
    TABLES
      priceconditions  = lt_priceconditions
      priceconditionsx = lt_priceconditionsx
      return           = lt_return.

  " --- Manejo de errores / commit / rollback ---
  IF line_exists( lt_return[ type = 'E' ] ).      " error → rollback de esta LUW
    CALL FUNCTION 'BAPI_TRANSACTION_ROLLBACK'.
    <fs_in>-msg = |ERROR: { lt_return[ 1 ]-message }|.
  ELSE.
    CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'       " wait = abap_true síncrono
      EXPORTING wait = abap_true.
    <fs_in>-msg = 'OK'.
  ENDIF.

  " --- Logging ---
  PERFORM write_log USING <fs_in> lt_return.      " BAL o Z-tabla (ver 3.4)

  " --- Paquetes: cada N filas, COMMIT agrupado ---
  " (controlar contador; evita desbordes de rollback area)
ENDLOOP.
```

### 3.3 Patrón BDC sobre ME12 (alternativa con escalas / cuando el BAPI falla)

```abap
" Recording SHDB de ME12 (ver sección 5). Luego se puede regenerar el
" programa de BDC o escribir CALL TRANSACTION:

CALL TRANSACTION 'ME12' USING bdcdata
  MODE 'A'                      " A=mostrar errores, N=background
  UPDATE 'S'                    " S=síncrono (para leer mensajes)
  MESSAGES INTO it_msg.         " log de mensajes de la transacción
```

- Recomendación práctica: grabar el recording una vez en QA, generar el programa de BDC con la función `BDC_INSERT` + `CALL TRANSACTION` (o por LSMW), y **no** documentar pantallas a mano.

### 3.4 Logging

**Opción A — Application Log (BAL)** (recomendada, estándar):

```abap
DATA lo_log TYPE REF TO cl_bali_log.
DATA lo_msg TYPE REF TO cl_bali_message_setter.
DATA lv_number TYPE bal_s_lognumber-lognumber.

" crear log
lo_log = cl_bali_log=>create( ).
lo_msg = cl_bali_message_setter=>create( severity = if_bali_constants=>c_severity_error
                                         msgid    = sy-msgid msgty = sy-msgty
                                         msgno    = sy-msgno msgv1 = sy-msgv1
                                         msgv2    = sy-msgv2 msgv3 = sy-msgv3
                                         msgv4    = sy-msgv4 ).
lo_log->add_item( lo_msg ).
" persistir
cl_bali_log_db=>get_instance( )->save_log( log = lo_log ).
" (SLG1 para visualizar; o BAL_CREATE/BAL_LOG_MSG en versiones clásicas)
```

**Opción B — Z-tabla de log** (para trazabilidad por material):

```abap
" ZPIR_LOG:  GUID / UNAME / DATUM / UZEIT / MATNR / LIFNR / EKORG /
"            WERKS / KSCHL / KBETR_OLD / KBETR_NEW / DATAB / DATBI /
"            MSGTY / MSGID / MSGNO / MSGV1..4 / TCODE / TESTFLAG
MODIFY zpir_log FROM ls_log.   " dentro de un paquete; COMMIT por paquete
```

---

## 4. Validación en QA (checklist)

1. **Config funcional**: verificar condición PB00 en `M/06` (cálculo tipo "C", cambios permitidos "monto/porcentaje" y "valor" marcados) y procedimiento de cálculo en `M/08` — si no, ME12 no deja guardar el precio. VERIFICADO [C15].
2. **Test run**: ejecutar siempre primero con `p_test = 'X'` y `BAPI_TRANSACTION_COMMIT` NO llamado (o `TESTRUN`), revisar `return`.
3. **Comparar antes/después**:
   - `EINE-NETPR`, `EINE-PEINH`, `EINE-WAERS` para el infrate.
   - `KONH`/`KONP` (KNUMH, KBETR, KOPOS) para la condición PB00/PB01.
   - Historial en **ME1E** (debe reflejar el nuevo precio — esto valida que se creó la condición, no solo el campo).
   - Tabla de condiciones A017/A018/A025 (VAKEY = MATNR+LIFNR+EKORG+WERKS+ESOKZ).
4. **Integración**: crear un pedido de compra de prueba (ME21N) para el proveedor/material y comprobar que el precio propuesto es el nuevo (net price). Verificar precios escalonados si los hay.
5. **Rollback/commit**: en QA inducir un error (p. ej. infote inexistente) y verificar que `BAPI_TRANSACTION_ROLLBACK` deja la BD sin cambios parciales y el log marca la fila.
6. **Volumen/rendimiento**: probar con el paquete elegido (p. ej. 50); vigilar uso de rollback area (SM04/ST05) y duración; para miles de registros valorar background + parallel (SM35 batch input o bgRFC).
7. **Autorizaciones**: usuario con autorización de mantenimiento de info records (M_BANF, org. compras).
8. **Reproceso**: con la Z-tabla de log identificar filas OK/ERROR y poder re-lanzar solo las erróneas.

---

## 5. Alternativa sin código: LSMW con recording de ME12 (VERIFICADO [C16], [C17], [C18])

**Cuál se graba**: como "actualizar precio del info record" se hace en **ME12** (pestaña Condiciones → crear/cambiar condición PB00 con validez y valor), el recording se crea sobre **ME12** (no sobre MM42, que no es editable para precios).

Campos que se graban (dependen del recording exacto):

| Pantalla (dynpro) | Campos grabados |
|---|---|
| Selección ME12 | `RM06I-INFNR` (o MATNR/LIFNR/EKORG/WERKS), ESOKZ |
| "Datos org. compras 1" | entrada a botón **Condiciones** (si se cambia el net price directo: `EINE-NETPR`, `EINE-PEINH`, `EINE-BPRME`, `EINE-WAERS`) |
| "Condiciones" (SAPLV14A) | condición `KSCHL=PB00`, `KONP-KBETR`, `KONP-KPEIN`, `KONP-KMEIN`, `KONP-KONWA`, fechas `DATAB/DATBI` |
| Guardado | botón Guardar (`OK-CODE`), mensaje de éxito |

Pasos LSMW (recording, método "Batch Input Recording"):
1. **Maintain Object Attributes** → import method = **Batch Input Recording** → crear recording, transacción **ME12**.
2. Ejecutar ME12 manualmente una vez con el caso típico (cambiar condiciones), **Default All**, guardar.
3. **Maintain Source Structures / Source Fields**: estructura (p. ej. `INFOPRECIO`) con los campos del archivo (MATNR, LIFNR, EKORG, WERKS, INFNR, KSCHL, KBETR, PEINH, KMEIN, WAERS, DATAB, DATBI).
4. **Maintain Field Mapping and Conversion Rules**: mapear campos fuente → campos del recording (auto field mapping + corregir).
5. **Specify/Assign Files** (CSV plano o Excel convertido a texto).
6. **Read Data → Convert Data**.
7. **Create Batch Input Session** (mantener carpetas) → **Run** (SM35: procesar en foreground para 1 registro de prueba, luego background).
8. Para **S/4HANA** usar **LTMC** con objeto de migración estándar de info records (recommendación SAP). VERIFICADO [C16].

**Ventajas**: usa la lógica estándar de precios (no hay que replicarla); sin desarrollo.
**Desventajas**: frágil a cambios de pantalla; el error "No batch input data for dynpro SAPLV14A 0102" es típico cuando el recording no llegó a la pantalla de condiciones (VERIFICADO [C16]).

---

## 6. Notas SAP y referencias clave

| Nota | Contenido |
|---|---|
| **1135984** | `BAPI_PRICES_CONDITIONS` no está liberado; "inconsistencies may occur; you should therefore not use it". (VERIFICADO vía citas en [C4], [C5], [C7]) |
| **3659315** | `ME_INFORECORD_MAINTAIN_MULTI` NO crea/actualiza condiciones de info records. (VERIFICADO [C1]) |
| **2787315** | Problemas conocidos de `ME_INFORECORD_MAINTAIN`; sugiere alternativas: `ME_INFORECORD_MAINTAIN_MULTI`, IDoc `INFREC`, programa `RM06IBI0`. (VERIFICADO [C2], [C10]) |

---

## 7. Fuentes (URLs)

- **[C1]** SAP KBA 3659315 — *Creating or updating conditions in an Info Record using ME_INFORECORD_MAINTAIN_MULTI*: https://userapps.support.sap.com/sap/support/knowledge/en/3659315
- **[C2]** SAP KBA 2787315 — *Issues when using ME_INFORECORD_MAINTAIN*: https://userapps.support.sap.com/sap/support/knowledge/en/2787315
- **[C3]** SAP Community — *How to create Purchase Information Records With Pricing Condition Record* (firma ME_INFORECORD_MAINTAIN + MEWICONDITION; "ME_UPDATE_INFORECORD_COND no llena historial"; recomendación BDC): https://community.sap.com/t5/enterprise-resource-planning-q-a/how-to-create-purchase-information-records-with-pricing-condition-record/qaq-p/12675375
- **[C4]** SAP Community blog — *How to use BAPI_PRICES_CONDITIONS to mass upload price conditions* (estructuras TI_BAPICONDCT/HD/IT; operaciones 003/004/009; cambio pointers): https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-members/how-to-use-bapi-prices-conditions-to-mass-upload-price-conditions/ba-p/13410500
- **[C5]** SAP Community — *BAPI or FM to create a new conditions price PB00* (nota 1135984; CND_PRICES_DETAILS_SAVE; blog IDoc COND_A): https://community.sap.com/t5/supply-chain-management-q-a/bapi-or-fm-to-create-a-new-conditions-price-pb00/qaq-p/12099983
- **[C6]** SAP Community — *How to update pricing condition in PIR* (nota 1135984; RV_KONDITION_SICHERN_V13A para historial; 3 fases para valideces solapadas): https://community.sap.com/t5/enterprise-resource-planning-q-a/how-to-update-pricing-condition-in-pir/qaq-p/12157217
- **[C7]** SAP Community — *Bapi for updating condition prices in info-record* (ME_UPDATE_INFORECORD_COND; recomendación batch recording): https://community.sap.com/t5/enterprise-resource-planning-q-a/bapi-for-updating-condition-prices-in-info-record/qaq-p/7817356
- **[C8]** SAP Community — *Creation of Purchasing Info Record MEK1* (IDoc COND_A01; E1KOMG-KAPPL='M'; condición PB00 en M/06): https://community.sap.com/t5/application-development-and-automation-discussions/creation-of-purchasing-info-record-mek1/m-p/7951276
- **[C9]** ABAPforum — *Automatische Anlage von Staffelpreisen mit ME_INFORECORD_MAINTAIN* (tipos MEWI* y firma): https://www.abapforum.com/forum/viewtopic.php?t=25328
- **[C10]** SAP Community — *Performance Issue in ME_INFORECORD_MAINTAIN* (método PROCESS_VAL_PERIODS; alternativas INFREC/RM06IBI0): https://community.sap.com/t5/enterprise-resource-planning-q-a/performance-issue-in-me-inforecord-maintain/qaq-p/14234777
- **[C11]** Trailsap — *MEIRPRCGCONDRECX Change Indicators for Info Record Pricing Condition Record* (campos CONDITIONAPPLICATION, PRICINGSCALEBASIS, PRICINGSCALELINE, BAPIUPDATE): https://www.trailsap.com/sap/?sap-table=meirprcgcondrecx
- **[C12]** SAP Datasheet — *BAPI_PRICES_CONDITIONS* (firma completa TI_/TO_): https://www.sapdatasheet.org/abap/func/bapi_prices_conditions.html
- **[C13]** SAP Datasheet — *RV_CONDITION_MAINTENANCE* (firma: KEY_FIELDS=KOMG, I_KOMK, I_KOMP, RECORD_NUMBER, MAINTAIN_MODE): https://www.sapdatasheet.org/abap/func/rv_condition_maintenance.html
- **[C14]** SAP Datasheet — *ME_UPDATE_INFORECORD_COND* (tabla REINE tipo EINE; campos INFNR/NETPR/PEINH/WAERS/PRDAT): https://www.sapdatasheet.org/abap/func/me_update_inforecord_cond.html
- **[C15]** SAP Community — *Unable to Change Net Price in Info Record* (config M/06 y M/08 para PB00): https://community.sap.com/t5/enterprise-resource-planning-q-a/unable-to-change-net-price-in-info-record/qaq-p/11569950
- **[C16]** SAP Community — *LSMW for MM (PIR)* (error SAPLV14A 0102; recomendación RM06IBI0; LTMC en S/4): https://community.sap.com/t5/enterprise-resource-planning-q-a/lsmw-for-mm-pir/qaq-p/12239285
- **[C17]** gauravconsulting.com — *LSMW Step-by-Step Guide in SAP* (pasos batch input recording): https://www.gauravconsulting.com/post/lsmw-step-by-step-guide-in-sap
- **[C18]** SAP Community — *LSMW: Upload Master Data Using Batch Input Recording Part 1* (los 14 pasos): https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-members/lsmw-upload-master-data-using-batch-input-recording-part-1/ba-p/13240785
- **[C19]** Programmer Sought — *ME11 Create Procurement Information Record and Condition BAPI: ME_INFORECORD_MAINTAIN_MULTI* (código completo T_EINA/T_EINAX/T_EINE/T_EINEX + COND_VALIDITY/CONDITION + COMMIT/ROLLBACK): https://www.programmersought.com/article/878510944168/
- **[C20]** SAP Community — *PIR price condition update when contract is created via BAPI* (2025; BAPI_INFORECORD_MAINTAIN soporte limitado de condiciones; ME_UPDATE_INFORECORD): https://community.sap.com/t5/enterprise-resource-planning-q-a/pir-price-condition-update-when-contract-is-created-via-bapi/qaq-p/14132003

---

## 8. Leyenda de verificación

| Marca | Significado |
|---|---|
| **VERIFICADO** | Confirmado con fuente externa citada arriba |
| **parcialmente VERIFICADO** | Parte confirmado con fuente, parte confirmado contra SE11/SE37 del sistema destino |
| **CONOCIMIENTO PREVIO (sin verificar)** | De mi base de conocimiento; debe confirmarse en SE11/SE37/SE16N del sistema destino antes de usarlo en código |

| Punto | Estado |
|---|---|
| BAPI_PRICES_CONDITIONS no recomendado (nota 1135984) | ✅ VERIFICADO [C4][C5][C7] |
| ME_INFORECORD_MAINTAIN_MULTI no toca condiciones (KBA 3659315) | ✅ VERIFICADO [C1] |
| ME_INFORECORD_MAINTAIN con CONDITION/COND_VALIDITY procesa precios | ✅ VERIFICADO [C3][C9] |
| Firma MEWICONDITION (COND_TYPE, COND_VALUE, CURRENCY, COND_P_UNT, COND_UNIT, CHANGE_ID) | ✅ VERIFICADO [C3][C9] |
| Firma BAPI_PRICES_CONDITIONS (TI_BAPICONDCT/HD/IT, operaciones 003/004/009) | ✅ VERIFICADO [C12][C4] |
| Pila RV_CONDITION_COPY/SAVE/RESET + MAINTAIN_MODE + OVERLAP_CONFIRMED | ✅ VERIFICADO [C5][C7][C13] |
| ME_UPDATE_INFORECORD_COND solo toca EINE (no crea KONH/KONP/historial ME1E) | ✅ VERIFICADO [C3][C14] |
| BAPI_INFORECORD_CHANGE: parámetros PRICECONDITIONS/PRICECONDITIONSX | ⚠ parcialmente VERIFICADO [C11]; confirmar en SE37 |
| Estructura MEIRPRCGCONDREC/X (campos + flags BAPIUPDATE) | ⚠ parcialmente VERIFICADO [C11] |
| Firma exacta de ME_CONDITION_MAINTAIN (KOMG/KOMK/KOMP/T_KOMV/WA_KOMV/XKOMG/XKOMK/XKOMP/KVORG/KPOSI) | ⚠ CONOCIMIENTO PREVIO sin fuente web; confirmar en SE37 |
| LSMW recording ME12 + pasos (SM35, RM06IBI0, LTMC) | ✅ VERIFICADO [C16][C17][C18] |
| Config M/06 y M/08 para que PB00 sea editable | ✅ VERIFICADO [C15] |
| IDoc COND_A01, E1KOMG-KAPPL='M' | ✅ VERIFICADO [C8] |
| Historial ME1E requiere registro de condición (no solo EINE-NETPR) | ✅ VERIFICADO [C3] |
| Sintaxis ABAP 7.40+ (SELECT @, VALUE #, line_exists, FOR ALL ENTRIES) | ✅ skill sap-abap (fuentes SAP Cheat Sheets) |

---

## 9. Conclusión corta (recomendación)

1. **Primera opción (sin desarrollo)**: LSMW (recording ME12) en ERP clásico, o **LTMC** en S/4HANA. Para volúmenes grandes: programa batch input estándar **RM06IBI0** o IDoc **COND_A01/INFREC**.
2. **Con desarrollo, cambio simple de precio PB00 sobre info records existentes**: reporte ABAP con **`ME_INFORECORD_MAINTAIN`** (tabla `CONDITION`, lógica ME12) o **`BAPI_INFORECORD_CHANGE`** con `PRICECONDITIONS`; commit/rollback con `BAPI_TRANSACTION_COMMIT/ROLLBACK` por paquete; log con **BAL** o Z-tabla; siempre test-run.
3. **Con escalas o múltiples valideces**: **BDC sobre ME12** (recording) o pila **RV_CONDITION_COPY/SAVE/RESET**.
4. **Evitar**: `BAPI_PRICES_CONDITIONS` (nota 1135984) y `ME_INFORECORD_MAINTAIN_MULTI` para precios (KBA 3659315). No escribir directo sobre EINE/KONH/KONP.
