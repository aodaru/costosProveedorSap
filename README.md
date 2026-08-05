# Actualización Masiva del Precio Neto (PB00/PB01) del Info Record de Compras — Guía de Decisión

**Fecha:** 2026-08-01 · **Investigación:** `research/01_data_model_mm42.md`, `research/02_apis_actualizacion_masiva.md`, `research/03_mejor_practica_ejemplo.md` · **Código entregado:** `src/zr_mass_actualiza_precio_cond.abap`

---

## Estructura del proyecto

```
costosProveedorSap/
├── README.md                          # Guia de decision y documentacion principal
├── changelog.md                       # Historial de revisiones y features
├── .gitignore
├── src/
│   └── zr_mass_actualiza_precio_cond.abap   # Reporte ABAP (feature PRECIO_COND_R3)
├── research/                          # Documentacion de investigacion SAP
│   ├── 01_data_model_mm42.md
│   ├── 02_apis_actualizacion_masiva.md
│   ├── 03_mejor_practica_ejemplo.md
│   ├── 04_sap_login_referencia.md
│   ├── 05_arquitectura_referencia.md
│   ├── 06_analisis_script_objetivo.md
│   └── 07_plan_script_python.md
├── script/                            # Feature PYTHON_ME12_MASSCOND
│   ├── main.py                        # GUI PySide2 principal
│   ├── me12_massmod.py                # Logica ME12 GUI Scripting
│   ├── sap.py                         # Conexion SAP GUI
│   ├── validators.py                  # Validaciones de Excel
│   ├── paths.py                       # Utilidades de rutas
│   ├── ui_me12.py                     # UI generada desde Qt Designer
│   ├── create_template.py             # Generador de template Excel
│   ├── test_project.py                # Tests pytest
│   ├── template_me12.xlsx             # Template Excel de entrada
│   ├── .env                           # Credenciales (no trackeado)
│   ├── .env.example                   # Plantilla de credenciales
│   ├── mise.toml                      # Config Python (mise)
│   └── scripts/                       # Referencias y docs internas
│       ├── README_python_script.md
│       ├── README_gui_scripting.md
│       └── me12_price_change.vba
└── docs/
    └── superpowers/implementation/
        └── pab-currency.md
```

## 1. Qué es realmente ese dato (y dónde vive)

"Cambiar el precio en MM42" — el dato que el usuario ve en la sección **"condiciones de precio neto"** de la pestaña Compras de MM42 (Change Material &, el equivalente retail de MM02) — **no es un campo del material master**: la vista de Compras de MM42 no contiene ningún campo de precio editable, y `MARC-NETPR` **no existe** en el estándar. Ese precio proviene del **registro de información de compras (info record)** y de su **registro de condición**:

- **Info record (EINA/EINE):** el precio neto informativo vive en **EINE-NETPR** (con EINE-PEINH unidad de precio y EINE-WAERS moneda). EINE-NETPR es un *snapshot* calculado desde las condiciones; **no es la fuente que usa el pedido** para el pricing.
- **Registro de condición (la fuente real):** el precio bruto **PB00** (y variantes como PB01) se guarda como registro de condición técnico: la tabla de condiciones **A018** (info record sin planta) / **A017** (con planta) contiene la clave (LIFNR + MATNR + EKORG + [WERKS] + ESOKZ) y apunta por **KNUMH** a la cabecera **KONH** (KSCHL, VAKEY, validez DATAB/DATBI) y a la partida **KONP** (**KBETR** = importe, KONWA, KPEIN, KMEIN); las escalas viven en **KONM**. Cuando se crea un PO, las condiciones se copian a **KONV** (vía EKKO-KNUMV).

Por eso **guardar en MM42 no crea ni actualiza condición ni info record** (solo toca tablas del material master), y "actualizar masivamente el precio neto" significa técnicamente: **mantener en masa el registro de condición PB00/PB01 del info record** (pestaña Condiciones de ME12, o MEK2, o MEKP) y, después, **resincronizar EINE-NETPR con el reporte estándar RM06INP0**. Los POs ya creados no cambian (copiaron su condición a KONV al crearse).

---

## 2. Árbol de decisión

```text
¿Hay info record existente para MATNR/LIFNR/EKORG/WERKS?

├─ NO (hay que crear info record + precio):
│     ─ Sin código: LSMW/LTMC con el programa estándar RM06IBI0 (carga inicial)
│     ─ Sin código: IDoc INFREC (crea el info record) + COND_A01 (condiciones)
│     ─ Con código: ME_INFORECORD_MAINTAIN (maestro) + condición PB00 aparte
│
└─ SÍ (solo cambiar el precio PB00/PB01 del info record):

    ¿El cambio es simple (precio plano, sin escalas)?

    ├─ SÍ, sin desarrollo → MEKP (Price Change: Info Records) o LSMW (recording ME12)
    ├─ SÍ, con desarrollo → ME_INFORECORD_MAINTAIN con MEWICONDITION_TT /
    │       MEWIVALIDITY_TT (COND_TYPE='PB00', CHANGE_ID='U')
    │       ★ = el reporte entregado en src/ (validar firma en SE37/SE11)
    │       (BAPI_INFORECORD_CHANGE NO está confirmado como BAPI liberado;
    │        ver §3 y §4 antes de usarlo como alternativa)
    ├─ NO (escalas / múltiples valideces):
    │     ─ Sin desarrollo: LSMW recording ME12 / LTMC (S/4HANA)
    │     ─ Con desarrollo: BDC sobre ME12 (o MEK2)
    └─ NO, pero solo sincronizar EINE-NETPR desde condiciones ya OK
          ─ Ejecutar RM06INP0 (o FM ME_UPDATE_INFORECORD_COND)

S/4HANA moderno (clean core, vía estratégica):
  API OData "Purchasing Info Record" / LTMC (business object 0623)
  → la vía recomendada por SAP para integración en S/4HANA.

Regla de oro (SIEMPRE):
  Después de cualquier vía que toque condiciones → ejecutar RM06INP0
  para dejar EINE-NETPR/PEINH/WAERS consistentes (KBA 685117, KBA 2892806).

Evitar a toda costa:
  SQL directo sobre KONH/KONP/A017/A018  ·  BAPI_PRICES_CONDITIONS (nota 1135984)
  ME_INFORECORD_MAINTAIN_MULTI para precios (KBA 3659315)
```

---

## 3. Tabla de mecanismos

| Mecanismo | Toca condición PB00/PB01 | Logging / doc. de cambio | Riesgo | Soporte SAP |
|---|---|---|---|---|
| **MEKP** (Price Change: Info Records, app estándar) | ✅ Sí (%, signo, validez, escalas) | ✅ Estándar | Bajo | ✅ Pleno — **la vía manual estándar por excelencia** |
| **LSMW** (recording de ME12) | ✅ Sí (lógica ME12) | ✅ Heredado de la transacción | ⚠️ Medio (frágil a cambios de pantalla) | ⚠️ Tolerado, no oficial |
| **LTMC** (S/4HANA, migración estándar) | ✅ Sí | ✅ | Bajo | ✅ Pleno (recomendado por SAP en S/4) |
| **RM06IBI0** (carga batch de info records) | ⚠️ Parcial: crea info records (carga **inicial**); no es un cambio masivo de precios | ✅ | Bajo-Medio | ⚠️ Estándar; validar versión |
| **IDoc COND_A01 / INFREC** | ✅ Sí (COND_A con E1KOMG-KAPPL = 'M'; INFREC crea/actualiza el info record) | ✅ | Medio | ✅ (validar versión/condición en M/06) |
| **BAPI_INFORECORD_CHANGE** (PRICECONDITIONS/PRICECONDITIONSX, estructuras MEIRPRCGCONDREC/X) | ✅ Sí | ✅ | ⚠️ Medio | ⚠️ **No confirmado como BAPI liberado** (research/02 §§39-43) — verificar SE37; no es la vía programática principal |
| **ME_INFORECORD_MAINTAIN** (tablas MEWICONDITION_TT / MEWIVALIDITY_TT, grupo MEWIPIR) | ✅ Sí (lógica ME11/ME12; cond. PB00 con COND_TYPE/COND_VALUE/CHANGE_ID='U') | ✅ | ⚠️ Medio (KBA 2787315: marcado obsoleto) | ⚠️ Parcial — **vía programática principal de este proyecto** (validar firma en SE37/SE11) |
| **ME_INFORECORD_MAINTAIN_MULTI** | ❌ **No** (KBA 3659315) | ✅ (maestro) | ⚠️ Medio | ⚠️ No liberado — no usar para precios |
| **RV_CONDITION_COPY / SAVE / RESET** (pila MEK1/MEK2) | ✅ Sí (directo, con manejo de solapamiento) | ✅ (si se usa la lógica estándar) | ⚠️ Medio-Alto | ⚠️ FM no liberada / parcial |
| **BDC ME12 / MEK2** | ✅ Sí | ✅ Heredado | ⚠️ Alto (frágil, difícil depurar) | ⚠️ Tolerado — elegir con escalas |
| **MASS** (mantenimiento masivo) | ✅ Sí (S/4HANA; KBA 3665364) | ✅ | Bajo-Medio | ⚠️ S/4HANA; en ECC limitado |

Mecanismos que **NO** sirven para el precio: `BAPI_MATERIAL_SAVEDATA` (vista compras del material master: no toca condiciones ni EINE) y `MEMASSIN` (campos de EINA/EINE, sin condiciones; KBA 2190287: no actualiza LOEKZ).

---

## 4. ⚠️ ADVERTENCIAS CRÍTICAS

> ⚠️ **LEER ANTES DE TOCAR NADA**
>
> 1. **`MARC-NETPR` no existe** en el diccionario estándar (MARC no guarda precios; los precios del material master están en MBEW). Si alguien lo referencia, es un campo custom — el precio de compra real es `EINE-NETPR` (info record) y la condición PB00 (KONP-KBETR).
> 2. **NO escribir SQL directo sobre KONH / KONP / A017 / A018 / A025.** No genera doc. de cambio, no valida valideces/unidades, no actualiza EINE-NETPR ni el historial de precios, y no refresca los buffers de determinación de precios. Riesgo alto, sin soporte.
> 3. **NO usar `BAPI_PRICES_CONDITIONS`** (nota SAP **1135984**: "inconsistencies may occur; you should therefore not use it!"). No maneja solapamiento de valideces ni genera historial por sí solo.
> 4. **`ME_INFORECORD_MAINTAIN_MULTI` NO crea/actualiza condiciones** de info records (KBA **3659315**); solo datos generales/org. de compras. `ME_INFORECORD_MAINTAIN` (single) sí procesa condiciones pero está marcado **obsoleto** (nota **2787315**) — es la vía programática principal de este proyecto porque es la única FM confirmada que mantiene condiciones de info record; en S/4HANA moderno migrar al servicio OData "Purchasing Info Record".
> 5. **`BAPI_INFORECORD_CHANGE` NO está confirmado como BAPI liberado** (research/02 §§39-43): puede no existir o no soportar condiciones en tu sistema. Verificar en SE37 antes de usarlo como alternativa. Preferir `ME_INFORECORD_MAINTAIN` (validando su firma) o el OData/LTMC.
> 6. **Después de cambiar las condiciones, ejecutar `RM06INP0`** (info records; RM06ENP0 contratos, RM06ENP1 scheduling agreements) para resincronizar `EINE-NETPR`/`PEINH`/`WAERS`. Sin esto, EINE-NETPR queda desactualizado o en cero (KBA 685117, KBA 2892806).
> 7. **Los POs ya creados no cambian.** El precio de un PO se copia a KONV al crearlo (time-independent). El cambio masivo de condición solo afecta a futuros POs.
> 8. **Validez y escalas:** las condiciones del info record son dependientes de tiempo y pueden tener varias valideces/escalas (KONM). Un cambio simple puede necesitar vencimiento de la validez actual + creación de una nueva (BDC/LSMW o RV_CONDITION_COPY con OVERLAP_CONFIRMED) — validar el caso con el negocio.
> 9. **EINE-NETPR no es la fuente del pricing del PO** (solo informativo): verificar siempre la condición (MEK3/ME1E) y el PO de prueba, no solo el campo NETPR.

---

## 5. Checklist de validación en QA

**Antes de la corrida (preparación):**
- [ ] Config: `M/06` → tipo de condición **PB00** (y PB01 si aplica): cálculo tipo `C`, **"cambios permitidos"** = valor (+ porcentaje si aplica), moneda/unidad consistentes. Si no, ME12/MEKP no deja grabar (validar también PB01 en M/03/V/05).
- [ ] Config: `M/08` → el procedimiento de cálculo (RM0000) incluye el tipo de condición.
- [ ] SLG0: crear el objeto de application log (p. ej. `ZPIR`) para el log BAL del reporte.
- [ ] SE11: crear la Z-tabla de log `ZPIR_PRICELOG` (campos en la sección de logging del reporte).
- [ ] Usuario con autorización de mantenimiento de info records (objeto `M_EINK`, org. de compras) y `S_LCD` si aplica. (Nota: `M_BANF` es de solicitudes de compra y NO aplica para info records.)
- [ ] Ejecutar siempre primero en **test run** (p_test = 'X'): el test NO llama al FM de modificación, solo valida y marca "TEST OK (no aplicado)" — revisar el ALV y confirmar que ninguna fila se marcó como ERROR.

**Después de la corrida (verificar por fila):**
- [ ] **ME13** (info record): EINE-NETPR / PEINH / WAERS con el nuevo valor — **después de ejecutar RM06INP0**.
- [ ] **MEK3** (condición): condición PB00 con KBETR nuevo, KONWA, KPEIN, KMEIN y validez DATAB/DATBI correctas.
- [ ] **ME1E** (historial de precios): debe mostrar el nuevo precio — esto valida que se creó/actualizó el **registro de condición** (no solo EINE).
- [ ] SE16N (solo lectura): A017/A018 → KNUMH; KONH/KONP → KBETR nuevo.
- [ ] **ME21N de prueba**: crear un PO para el proveedor/material → el precio propuesto debe ser el nuevo (net price).
- [ ] Escalas: si existen precios escalonados, verificarlos en MEK3/KONM.
- [ ] SM35 / SLG1: revisar sesiones batch (si se usó BDC) y el log de aplicación del reporte.
- [ ] Rollback: inducir un error (p. ej. info record inexistente) y verificar que el `ROLLBACK WORK` no deja cambios parciales y el log marca la fila como ERROR.

---

## 6. Reporte ABAP entregado

`src/zr_mass_actualiza_precio_cond.abap` — reporte ABAP 7.40+ (listo para adaptar) que actualiza la condición PB00/PB01 de info records existentes vía **ME_INFORECORD_MAINTAIN** (grupo MEWIPIR; tablas **MEWICONDITION_TT** / **MEWIVALIDITY_TT** con COND_TYPE='PB00', COND_VALUE, CURRENCY, COND_P_UNT, COND_UNIT, CHANGE_ID='U', y validez VALID_FROM/VALID_TO con SERIAL_ID):

- Carga de CSV (cl_gui_frontend_services=>gui_upload + SPLIT) con conversión ALPHA.
- Validaciones masivas: MARA (material), LFA1 (proveedor), EINA/EINE (info record por MATNR/LIFNR/EKORG/WERKS, incluye INFNR y excluye LOEKZ='L'), TCURC (moneda).
- **Test run** (p_test): NO llama al FM de modificación — solo valida y marca "TEST OK (no aplicado)" (evita el COMMIT implícito de fin de reporte). En producción: `COMMIT WORK AND WAIT` por registro y `ROLLBACK WORK` ante error.
- Commit/rollback por registro, estadísticas OK/ERROR/SKIP, tamaño de paquete (p_pkg), ALV de resultados (cl_salv_table).
- Logging con Application Log (cl_bali_log / cl_bali_message_setter / cl_bali_free_text_setter / cl_bali_log_db) + Z-tabla sugerida **ZPIR_PRICELOG**.
- Alternativa **BAPI_INFORECORD_CHANGE** documentada (comentada: no está confirmado liberado) y alternativa **BDC sobre ME12** (comentada) para escalas/múltiples valideces.
- TODO de adaptación: nombre/ruta del CSV, columnas exactas, autorización (S_LCD / M_EINK), config M/06.

> ⚠️ **Antes de activar:** verificar en SE37/SE11 la firma de `ME_INFORECORD_MAINTAIN` en el sistema destino. Firma real (research/03 §2.1; SAP Community 12675375 / ABAPforum t=25328):
>
> ```abap
> CALL FUNCTION 'ME_INFORECORD_MAINTAIN'
>   EXPORTING
>     i_eina            = ls_eina      " TYPE MEWIEINA   (general: MATNR, LIFNR, INFO_REC...)
>     i_einax           = ls_einax     " TYPE MEWIEINAX  (flags X)
>     i_eine            = ls_eine      " TYPE MEWIEINE   (org. compras: EKORG, WERKS, INFO_REC...)
>     i_einex           = ls_einex     " TYPE MEWIEINEX  (flags X)
>     testrun           = lv_test      " 'X' = no graba
>   IMPORTING
>     e_eina            = le_eina
>     e_eine            = le_eine
>   TABLES
>     txt_lines         = lt_txt_lines        " TYPE MEWIPIRTEXT_TT
>     cond_validity     = lt_cond_validity    " TYPE MEWIVALIDITY_TT (VALID_FROM/VALID_TO/SERIAL_ID)
>     condition         = lt_condition        " TYPE MEWICONDITION_TT (SERIAL_ID+INFO_REC+COND_COUNT+COND_TYPE='PB00'...)
>     cond_scale_value  = lt_cond_scale_value " TYPE MEWISCALEVAL_TT
>     cond_scale_quan   = lt_cond_scale_quan  " TYPE MEWISCALEQUAN_TT
>     return            = lt_return.          " TYPE MEWI_TT_RETURN
> ```
>
> Notas: `cond_validity`, `condition` y `return` van en **TABLES** (no EXPORTING/IMPORTING); el nº de info record en MEWIEINA/MEWIEINE es **INFO_REC** (no "infnr"); MEWIVALIDITY usa **VALID_FROM/VALID_TO** (no DATAB/DATBI) y requiere **SERIAL_ID**; MEWICONDITION necesita **SERIAL_ID + INFO_REC + COND_COUNT** (sin ellos el FM falla con "Please maintain either the net price or conditions"). Ajustar nombres de campos si difieren.

---

## 7. Web UI ME12

Existe una interfaz web que permite al equipo de compras ejecutar la carga masiva ME12 desde un navegador, sin acceder a la VM Windows:

- **URL:** `http://vm-windows:5000`
- **Stack:** Flask + Flask-SocketIO + HTML/CSS/JS embebido (código en `web/`).
- **Deploy:** servicio Windows auto-arrancable gestionado con **nssm**.
- **Documentación de operaciones:** `web/RUNBOOK.md` (instalación, start/stop, logs, actualización y verificación).
- **Checklist de aceptación:** `web/UAT_CHECKLIST.md` es el checklist de aceptación de usuario (UAT) que debe completar el equipo de compras antes de dar por cerrada la Fase 6.
- **Notas:** las credenciales SAP siguen en `script/.env` (no trackeado) y el secreto de Flask se configura como variable de entorno `FLASK_SECRET_KEY` en el servicio nssm; no se commitean.
