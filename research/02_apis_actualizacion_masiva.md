# 02 - APIs / mecanismos para actualización masiva del precio neto (PB00/PB01) en compras

**Fecha:** 2026-08-01
**Ámbito:** Alternativas ABAP/estándar para actualizar en masa el precio neto de compra (condición PB00/PB01 ligada a información de abastecimiento / info record) y el campo informativo `EINE-NETPR`.
**Estado:** Investigación (sin código de solución).

> ⚠️ **Corrección de premisas importante (verificado):**
> 1. **`MARC-NETPR` no existe.** El data element `NETPR` no se usa en la tabla `MARC` (verificado contra where-used del DDIC en sapdatasheet.org: MARC no aparece en la lista de 275 tablas; el net price del info record es `EINE-NETPR`, data element `IPREI`; el del documento es `EKPO-NETPR`, data element `BPREI`). El "precio neto" que se ve en la vista de compras del material maestro es el **proveniente del info record/condiciones**, no un campo propio de `MARC`.
> 2. `MM42` no es una transacción estándar del material maestro (las estándar son `MM01`/`MM02`/`MM03`; la vista de compras es la vista 2). Puede ser un t-code Z propio.
> 3. El precio que **realmente decide** en una orden de compra es el **registro de condición** PB00/PB01 (tablas de condiciones `KONH`/`KONP` + tablas de acceso `A017`/`A018`), no `EINE-NETPR`, que es un campo **meramente informativo** y no se usa en el cálculo de precios (verificado: SAP Community post 7748357).

---

## Modelo de datos de referencia

| Elemento | Tabla(s) | Rol |
|---|---|---|
| Condición de precio (gross) | `KONH` (cabecera), `KONP` (condición), acceso `A017` (info record material/planta) y `A018` (info record material) | **Fuente real del precio** que se copia a la PO |
| Net price informativo del info record | `EINE-NETPR` (data element `IPREI`) | Campo informativo, NO participa en pricing; se refresca desde las condiciones |
| Precio neto de la PO | `EKPO-NETPR` (data element `BPREI`) | Resultado de la determinación de precios |

**Cascada relevante:** condición PB00/PB01 (KONP/A017/A018) → `EINE-NETPR` (vía reporte `RM06INP0` / `ME_UPDATE_INFORECORD_COND`) → propuesta de precio en la PO. El KBA 2892806 documenta que tras actualizar PB00 en `MEK1` las condiciones cambian pero `EINE-NETPR` **no se actualiza o queda en cero** (síntoma típico).

---

## Alternativas analizadas

### 1. `BAPI_MATERIAL_SAVEDATA` (vista de compras del material maestro)

- **Qué toca:** Datos de `MARC` (parámetro `PLANTDATA`/`BAPI_MARC` + `PLANTDATAX`, flag `HEADDATA-PURCHASE_VIEW`). BAPI liberado y RFC.
- **¿Toca la condición PB00/PB01?** **NO.** Actualiza campos de la vista de compras del material maestro (grupo de compras, indicadores, etc.). No mantiene registros de condición ni `EINE`.
- **¿Toca `EINE-NETPR`?** **NO.** `MARC` no tiene campo `NETPR`.
- **Logging:** Doc. de cambio de material maestro (CDHDR/CDPOS vía MM).
- **Riesgo:** Bajo como mecanismo, pero **no resuelve el requerimiento**.
- **Soporte:** ✅ Pleno (BAPI liberado, obsoleto en el sentido "use BAPI" → en S/4 Cloud usar BDEF/API del material master).
- **Verificación:** Firma `PLANTDATA`/`PLANTDATAX`/`PURCHASE_VIEW` y doc. oficial confirmadas en stechno.net y help.sap.com (ejemplo reporte). ✅
- **Veredicto:** ❌ No apta para actualizar precio neto (ni condición ni EINE).

### 2. `BAPI_INFORECORD_CREATE` / `BAPI_INFORECORD_CHANGE`

- **Qué toca:** Info record (EINA/EINE) y sus condiciones (tablas `BAPIEINA`, `BAPIEINE`, `PRICECONDITIONS`/`PRICECONDITIONSX`).
- **Estado de soporte:** ⚠️ **No se encontró evidencia de que existan como BAPIs liberados.** La documentación oficial de "Purchasing Info Record (MM-PUR-VM-REC)" (help.sap.com) indica que el grupo de funciones `MEWI` contiene solo 3 FMs: `BAPI_INFORECORD_GETLIST` (liberado), `ME_INFORECORD_MAINTAIN` (**obsoleto**, nota 2787315) y `ME_INFORECORD_MAINTAIN_MULTI` (**no liberado**, uso solo dentro de programas estándar SAP). No aparece `BAPI_INFORECORD_CREATE/CHANGE` como BAPI oficial.
- **Veredicto:** ❌ No confiar en ellos como API oficial. Usar el API OData/`ME_INFORECORD_MAINTAIN` solo dentro de contexto estándar, o el servicio moderno (ver #11).

### 3. `ME_INFORECORD_MAINTAIN` y `ME_INFORECORD_MAINTAIN_MULTI`

- **Qué toca:** Crea/cambia info record (EINA/EINE) y **puede** recibir condiciones (tablas `CONDITION`/`COND_VALIDITY` de tipo `MEWICONDITION`, p.ej. PB00 con `cond_value`, `currency`, `vendor_no`, `cond_p_unt`).
- **Estado de soporte:** ❌ `ME_INFORECORD_MAINTAIN` declarado **obsoleto** (KBA 2787315: errores ME816 al actualizar condiciones, número externo fuera de rango). ❌ Ambos **no son liberados** — solo soportados dentro de solución estándar SAP/integración, no en código propio (help.sap.com MM-PUR-VM-REC).
- **`ME_INFORECORD_MAINTAIN_MULTI`:** KBA 3659315 confirma que **NO puede crear/actualizar condiciones** en info records (a diferencia de ME11/ME12). ⚠️ Aun así es la opción más usada en la práctica (ejemplo: blog sapsimpleabap 2024 lo usa con condición PB00 + `BAPI_TRANSACTION_COMMIT`).
- **Logging:** Doc. de cambio de info record (`ME_CREATE_CHANGEDOC_INFOREC`).
- **Riesgo:** Medio (FM no liberado, comportamiento dependiente de versión; se usa masivamente pese a ello).
- **Verificación:** ✅ KBA 2787315, KBA 3659315, help.sap.com MM-PUR-VM-REC.
- **Veredicto:** ⚠️ Funciona en la práctica para PB00 en muchos sistemas, pero **sin soporte oficial** para uso en código propio. Alternativa de respaldo.

### 4. FMs clásicas de condiciones: `ME_CONDITION_MAINTAIN`, `RV_CONDITION_COPY`, `BAPI_PRICES_CONDITIONS`

- **Qué tocan:** Registros de condición (KONH/KONP + tablas de acceso, p.ej. A017/A018).
- **`ME_CONDITION_MAINTAIN`:** FM clásica de mantenimiento de condiciones en masa (parámetros del estilo `XKOMG`/`XKOMK`/`XKOMP`/`XKOMV`). Se usa en programas de carga masiva de condiciones de compras. **No verificada** su firma en fuentes públicas durante esta investigación (conocimiento previo, marcar como *no verificado*).
- **`RV_CONDITION_COPY`:** FM para copiar/crear condiciones; requiere llenar estructuras de comunicación (KOMK/KOMP, `SPR_KOMK_KOMP_FILL`) y tiene el conocido problema de **no grabar en BD si faltan parámetros** (Community post 10468213). Usada más en SD; aplicable a compras con KAPPL='M'. Verificada su existencia y limitación. ✅
- **`BAPI_PRICES_CONDITIONS`:** Blog de Community la propone para carga masiva de condiciones usando KONH/KONP/tablas de acceso (A305 en el ejemplo SD). Aplicabilidad a condiciones de compras (KAPPL 'M') **no verificada**. ⚠️
- **Logging:** Documento de cambio de condiciones (tablas condiciones) si se invoca la lógica estándar; depende de la FM.
- **Riesgo:** Medio-alto si se salta la lógica estándar.
- **Veredicto:** ⚠️ Prometedoras para tocar directamente PB00/PB01, pero requieren validación de firma en el sistema destino y cuidado con la grabación incompleta (RV_CONDITION_COPY).

### 5. Cascada condición → `EINE-NETPR`: `ME_UPDATE_INFORECORD_COND` y reporte `RM06INP0`

- **Qué hace:** Tras actualizar las condiciones, refresca el campo informativo `EINE-NETPR`/`EFFPR` del info record para que sea consistente con las condiciones.
- **`ME_UPDATE_INFORECORD_COND`:** "Update price in info record during maintenance from condition transaction" (FM del flujo MEK1/MEK2). Community: actualiza **solo el net price, no el registro de condición** (mensaje 12671781) — exactamente el sentido contrario al requerimiento: esta FM se usa para *sincronizar* EINE-NETPR después de tocar la condición. ⚠️ FM interna, no liberada.
- **`RM06INP0`:** reporte estándar que actualiza el net price del info record desde las condiciones/documentos; Community recomienda ejecutarlo periódicamente como job de fondo para dejar `EINE-NETPR` consistente. ✅ Verificado (post 7748357). KBA 2892806 documenta el desfase cuando no se actualiza.
- **Veredicto:** ✅ **Complemento obligatorio** de cualquier alternativa que toque condiciones: después de actualizar PB00/PB01 en masa, ejecutar `RM06INP0` (o equivalente) para mantener `EINE-NETPR` consistente y el historial de precios (ME1E) coherente.

### 6. Transacción/app estándar de masas: **MEKP** (Price Change: Info Records)

- **Qué toca:** Actualización **masiva del precio (condiciones PB00 y afines)** de info records: %, signo, validez, precio bruto, escala. App Fiori "Price Change: Info Records (MEKP)" documentada en SAP Best Practices ("the Price Change: Info Records (MEKP) app is used to mass update the prices for info records"). ✅
- **Logging:** Doc. de cambio estándar de condiciones.
- **Riesgo:** Bajo (transacción estándar, controles de validez).
- **Soporte:** ✅ Pleno.
- **Veredicto:** ✅ **La vía estándar por excelencia para el caso masivo** (aumento/reducción %, actualización de validez, multi-material/proveedor). Limitación: es interactiva; para automatización total se combina con BDC/LSMW sobre MEKP o con las FMs del punto #4.

### 7. `MEMASSIN` (Mass-Changing of Purchasing Info Records)

- **Qué toca:** Campos de `EINA`/`EINE` (objeto `BUS3003`): materias, plazos, unidades, indicadores, etc.
- **¿Condiciones?** **NO.** MEMASSIN no mantiene condiciones PB00/PB01; solo campos del info record. Podría tocar `EINE-NETPR` (campo informativo) pero eso no cambia el precio real.
- **Advertencias:** KBA 2190287: MEMASSIN **no actualiza** `EINA-LOEKZ`/`EINE-LOEKZ` (borrado lógico). ✅
- **Veredicto:** ❌ No apta para precio (salvo ajustes informativos de EINE).

### 8. `MASS` (Mass Maintenance) para condiciones

- **Qué toca:** Mantenimiento masivo de datos maestros; permite objetos como condiciones.
- **KBA 3665364** "How to update condition records is MASS" (S/4HANA, SD-MD-CM) documenta los enfoques para cambios masivos de registros de condición. Existe la capacidad, **contenido completo detrás de login**. ⚠️
- **Veredicto:** ⚠️ Viable en S/4HANA para condiciones; validar en el sistema el objeto/operación para KAPPL 'M' PB00. En ECC el soporte de condiciones en MASS es más limitado.

### 9. BDC / LSMW sobre `ME12` / `MEK1` / `MEK2` / `MEKP`

- **Qué toca:** Reproduce pantallas de las transacciones de info record/condiciones.
- **Ventaja:** Usa 100% la lógica estándar (validez, escalas, doc. de cambio, mensajes).
- **Riesgo:** Medio-alto: frágil ante cambios de pantalla/versión, difícil manejo de mensajes/errores y paralelización; requiere mantenimiento.
- **Logging:** Doc. de cambio estándar (heredado de la transacción).
- **Veredicto:** ⚠️ Útil cuando no hay BAPI/FM viable o para automatizar MEKP; es el enfoque clásico de "última opción".

### 10. Update directo a `KONH` / `KONP` / `A017` / `A018`

- **Qué toca:** Registros de condición en BD directamente (SQL `UPDATE`).
- **Riesgo:** ❌ **Alto / no soportado**: no genera doc. de cambio, no valida rangos de validez ni unidades, no actualiza `EINE-NETPR` ni historial de precios, no dispara buffers de determinación de precios (puede requerir volcado de buffers). Solo aceptable con validaciones y gestión manual de buffer, y con due diligence de auditoría.
- **Veredicto:** ❌ Evitar salvo caso extremo y con controles propios.

### 11. API moderna S/4HANA: servicio "Purchasing Info Record" (clean core)

- **Qué toca:** Servicio síncrono entrante que permite **crear, leer, actualizar y borrar info records CON condiciones** (datos generales, datos de org. de compras y condiciones). Documentado en help.sap.com (SAP S/4HANA on-premise). ✅
- **Ámbito:** S/4HANA on-premise 2021+ / Cloud; integración típica vía BTP/SAP Integration Suite o RFC del OData service.
- **Logging:** Doc. de cambio estándar (a través de la lógica BAPI/FM subyacente del servicio).
- **Riesgo:** Bajo, es la vía estratégica de SAP.
- **Veredicto:** ✅ **Recomendada como vía moderna y soportada** para actualización programática masiva de precios de info record (PB00/PB01), especialmente si se busca clean core o integración externa.

---

## Tabla comparativa

| # | Alternativa | Toca condición PB00/PB01 | Actualiza EINE-NETPR | Logging / doc. cambio | Riesgo | Soporte SAP |
|---|---|---|---|---|---|---|
| 1 | `BAPI_MATERIAL_SAVEDATA` | ❌ No | ❌ No (MARC no tiene NETPR) | ✅ Material master | Bajo (pero no aplica) | ✅ Pleno (BAPI liberado) |
| 2 | `BAPI_INFORECORD_CREATE/CHANGE` | ⚠️ En teoría (PRICECONDITIONS) | ✅ | ✅ | ⚠️ Medio | ❌ No verificados como BAPI liberado |
| 3 | `ME_INFORECORD_MAINTAIN(_MULTI)` | ⚠️ MAINTAIN sí / **MULTI NO** (KBA 3659315) | ✅ | ✅ | ⚠️ Medio | ❌ Obsoleto / no liberado (KBA 2787315) |
| 4 | `ME_CONDITION_MAINTAIN` / `RV_CONDITION_COPY` / `BAPI_PRICES_CONDITIONS` | ✅ Sí (directo) | ⚠️ Solo si se sincroniza después | ✅ (si usa lógica estándar) | ⚠️ Medio-alto | ⚠️ FM no liberadas / parcial |
| 5 | `ME_UPDATE_INFORECORD_COND` + `RM06INP0` | ❌ (es el efecto inverso: condición→net) | ✅ Sí (sincroniza) | ✅ | Bajo | ⚠️ FM interna; `RM06INP0` estándar ✅ |
| 6 | **`MEKP` (Price Change Info Records)** | ✅ **Sí (masivo, %)**, incluye validez/escalas | ✅ (vía lógica estándar) | ✅ | **Bajo** | ✅ **Pleno (app estándar)** |
| 7 | `MEMASSIN` | ❌ No | ⚠️ EINE sí, pero informativo | ✅ | Bajo | ✅ Pleno (con KBA 2190287) |
| 8 | `MASS` (condiciones) | ✅ Sí (S/4HANA) | ⚠️ | ✅ | Bajo-Medio | ⚠️ S/4HANA; KBA 3665364 |
| 9 | BDC / LSMW (`ME12`/`MEK1`/`MEK2`/`MEKP`) | ✅ Sí | ✅ | ✅ (heredado) | ⚠️ Medio-alto (frágil) | ⚠️ No oficial, tolerado |
| 10 | SQL directo a `KONH`/`KONP`/`A017`/`A018` | ✅ Sí (sin validaciones) | ❌ No | ❌ No | ❌ **Alto** | ❌ No soportado |
| 11 | **API "Purchasing Info Record" (S/4HANA OData)** | ✅ **Sí** | ✅ | ✅ | **Bajo** | ✅ **Pleno / clean core** |

---

## Recomendación preliminar

1. **Para cambio masivo puntual (humano/negocio):** transacción estándar **`MEKP`** (app "Price Change: Info Records"). Es la vía soportada, con control de validez/escalas y doc. de cambio. Complementar con `RM06INP0` si se quiere `EINE-NETPR` consistente.
2. **Para automatización programática:** servicio S/4HANA **"Purchasing Info Record" (OData, #11)** en S/4HANA moderno; en ECC/S/4 clásico usar `ME_INFORECORD_MAINTAIN` (⚠️ obsoleto pero operativo en la práctica) o BDC sobre `MEKP`/`MEK2`, entendiendo la limitación de soporte.
3. **Evitar:** actualización directa de `KONH`/`KONP`/`A017`/`A018` sin lógica estándar, y cualquier vía que asuma un campo `MARC-NETPR` (no existe).

## Pendientes / validar en sistema destino

- Firmas exactas de `ME_CONDITION_MAINTAIN` y `BAPI_PRICES_CONDITIONS` (SE37 en el sistema destino).
- Comportamiento de `ME_INFORECORD_MAINTAIN` para PB00 en la versión concreta (KBA 2787315/3659315 pueden requerir notas).
- Disponibilidad del servicio OData "Purchasing Info Record" en la versión S/4HANA instalada.
- Objeto/operaciones de `MASS` para condiciones PB00 en el sistema real.

## Fuentes clave

- KBA 3659315 (ME_INFORECORD_MAINTAIN_MULTI no mantiene condiciones) — userapps.support.sap.com
- KBA 2787315 (Issues when using ME_INFORECORD_MAINTAIN) — userapps.support.sap.com
- KBA 2892806 (net/effective price no actualizado en info record al cambiar PB00 en MEK1) — userapps.support.sap.com
- KBA 3665364 (How to update condition records in MASS) — userapps.support.sap.com
- KBA 2190287 (MEMASSIN no actualiza LOEKZ) — launchpad.support.sap.com
- help.sap.com, "Purchasing Info Record (MM-PUR-VM-REC)" (grupo MEWI, MEMASSIN, notas relacionadas) — support content SPMM
- help.sap.com, SAP Best Practices: "Mass Price Changes to Purchasing Info Record (MEKP)"
- help.sap.com, S/4HANA on-premise: API service "Purchasing Info Record" (create/read/update/delete con condiciones)
- SAP Community 7748357 ("Function to Update Info Record price": NETPR informativo, RM06INP0)
- SAP Community 10468213 (RV_CONDITION_COPY + SPR_KOMK_KOMP_FILL)
- SAP Community 12671781 (ME_UPDATE_INFORECORD_COND actualiza solo net price)
- Blog community 13410500 (BAPI_PRICES_CONDITIONS carga masiva de condiciones)
- stechno.net: firma de BAPI_MATERIAL_SAVEDATA; sapdatasheet.org: where-used de NETPR (MARC ausente)
