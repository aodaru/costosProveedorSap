# 01 — Modelo de datos de las "condiciones de precio neto" en compras (MM42 / info record / condición técnica)

**Fecha de investigación:** 2026-08-01
**Rol:** investigación técnica, sin escribir código de la solución final.
**Alcance:** ¿Dónde se guardan los datos de las condiciones de precio neto de compras, qué tablas/campos intervienen, qué tipo de condición se usa, y cómo se relacionan MM42, MARC-NETPR, EINA/EINE y KONH/KONP + tablas A0xx?

> **Resumen ejecutivo (la respuesta en 10 líneas):**
> La sección "condiciones de precio neto" que se ve al mantener **condiciones** de compra NO pertenece a la vista de compras del material master (MM02/MM42), sino al **registro de información de compras** (ME11/ME12/ME13) y a los **registros de condición** (MEK1/MEK2/MEK3). El precio neto de compras se almacena en **EINE-NETPR** (info record, nivel organización de compras). Las condiciones (precio bruto **PB00**, descuentos, recargos, escalas) se guardan como registros de condición: la **tabla de condiciones A0xx** (A018/A017/A025/A028…) contiene la clave (proveedor, material, org. compras, planta, tipo de info record) y apunta por **KNUMH** a **KONH** (cabecera de condición) y **KONP** (partida de condición, contiene el importe **KBETR**), con escalas en **KONM**. En el documento de compras (PO/contrato) las condiciones se copian a **KONV** (enlazado por **EKKO-KNUMV**). **MARC-NETPR no existe en el diccionario estándar**: MARC no guarda ningún precio; los precios del material master están en **MBEW** (vista contabilidad/coste). Guardar un precio en MM42 NO crea ni actualiza condición ni info record: solo toca tablas de material master (MARC/MARA/MBEW) y su log de cambios.

Leyenda de confiabilidad:
- **[VERIFICADO]** = confirmado con fuente externa (URL en §6).
- **[CONOCIMIENTO PREVIO]** = conocimiento de consultor/experto, sin fuente externa en esta investigación.
- **[PARCIAL]** = fuentes encontradas son ambiguas o de terceros; requiere validación en sistema real.

---

## 1. Corrección de premisas de la pregunta

Antes de la cadena de almacenamiento hay que corregir dos premisas del enunciado:

1. **MM42 NO es "modificar material" del MM estándar.** [VERIFICADO] MM42 es *"Change Material &"* (aplicación LO-Article / IS-Retail, programa `SAPMMG02`), es decir, el equivalente a MM02 para el maestro de artículos; la pantalla y las tablas subyacentes son las del material master (MARC/MARA/MBEW/etc.). Para el MM logístico estándar el cambio de material es **MM02** (creación MM01, visualización MM03). Referencias: erpyourself.net MM42, beneering "SAP MM transactions overview".

2. **La vista de Compras del material master NO tiene una sección "condiciones de precio neto".** [VERIFICADO] La vista de compras (MM01/MM02, MM41/MM42) contiene datos de aprovisionamiento: unidad de pedido, grupo de compras, plazo de entrega planificado, tiempos, tolerancias de exceso/falta (MARC-UEETO/UNETO/UEETK), grupo de materiales, indicador de facturación basada en GR, etc. — pero **ningún campo de precio ni condiciones**. El precio neto de compra vive en el **registro de información de compras** (EINE-NETPR) y los precios condicionados en los **registros de condición**. Referencias: tutorialkart (Purchasing View), SAP Learning "Maintaining Purchasing Info Record".

3. **MARC-NETPR no existe en el diccionario estándar.** [VERIFICADO] En la lista completa de campos de MARC (304 campos, datapanda.eu) **no aparece `NETPR` ni ningún campo de importe**. MARC guarda datos por planta (grupo de compras EKGRP, MRP controller DISPO, plazo de entrega PLIFZ, etc.). El precio neto de compras es **EINE-NETPR**; los precios del material master (precio estándar, precio medio, precios planificados) están en **MBEW** (STPRS, VPRSV, VERPR, LPLPR, ZPLPR, ZPLP1/ZPLP2/ZPLP3). Cualquier "MARC-NETPR" es un campo custom (append) de cliente. [PARCIAL] Los precios planificados 1/2/3 están documentados en MBEW (prospecta "Material Master Module List"); no encontré fuente estándar que los ponga en MARC.

> **Conclusión de premisas:** si el requerimiento del negocio dice "se guarda en MM42 en condiciones de precio neto", lo más probable es que el dato real esté en (a) el info record (EINE-NETPR) o (b) un campo custom del material master, o (c) condiciones vía MEK1. El resto del documento describe dónde vive cada cosa realmente.

---

## 2. Cadena de almacenamiento (qué se guarda en cada tabla)

### 2.1 Registro de información de compras (info record) — precio neto "plano"
Creado/modificado con **ME11** (crear) / **ME12** (cambiar) / **ME13** (mostrar) / **ME14** (log de cambios). [VERIFICADO]

| Tabla | Nivel | Campos clave | Contenido |
|---|---|---|---|
| **EINA** | General (cliente) | INFNR (nº info record), MATNR, MATKL, LIFNR | Datos generales: proveedor, material, grupo de materiales. |
| **EINE** | Org. de compras | INFNR, EKORG, WERKS, ESOKZ (categoría de info record: 0 estándar / 1 consignación / 3 subcontratación / P pipeline) | Datos por org. de compras/planta. **NETPR** = precio neto, **PEINH** (unidad de precio), **WAERS**, **EFFPR** (precio efectivo), **BPUMZ/BPUMN/BPRME** (conversión de unidad de pedido), **PRDAT** (fecha de precio). |
| **EIPA** | Histórico | INFNR + fechas | Histórico de precios de pedido (order price history) del info record. |

- **EINE-NETPR**: campo CURR(11,2), data element `IPREI`, referencia de moneda **WAERS**. [VERIFICADO — sapdatasheet]
- El precio neto del info record se **calcula a partir de las condiciones** (es un "snapshot"); NO es la fuente que usa el PO directamente para precios condicionados (ver §4). [VERIFICADO — KBA 685117, gugulii MM-a06-01]

### 2.2 Registros de condición (condition records) — la parte "Konditionen"
La técnica de condiciones (condition technique) de MM usa: **tabla de condiciones** (A0xx) → **cabecera de condición** (KONH) → **partida de condición** (KONP) → **escalas** (KONM/KONB). Mantenidas con **MEK1** (crear) / **MEK2** (cambiar) / **MEK3** (mostrar) / **MEK31** (cambiar por tipo de condición) / **MBN1** (lista). [VERIFICADO]

| Tabla | Propósito | Campos clave |
|---|---|---|
| **A018** | Tabla de condiciones "Material Info Record" (info record **sin** planta): clave **LIFNR + MATNR + EKORG + ESOKZ + KAPPL + KSCHL** + fechas de validez | **KNUMH** (número de registro de condición), KODATAB/KODATBI |
| **A017** | Tabla de condiciones "Material Info Record (Plant-Specific)" (info record **con** planta): clave anterior **+ WERKS** | **KNUMH**, fechas |
| **A025** | "Info Record for Non-Stock Item (Plant-Specific)": info record de material sin maestro / por grupo de materiales (clave **LIFNR + EKORG + MATKL + INFNR + WERKS + ESOKZ**) | **KNUMH** |
| **A028** | Idem sin planta (non-stock item) | **KNUMH** |
| **A019** | Contratos (Contract Header, EKKO-EBELN) | KNUMH |
| **A020 / A016 / …** | Otras combinaciones (proveedor+planta, proveedor+org.compras, etc.) según acceso de la secuencia | KNUMH |
| **KONH** | Cabecera de condición: **KNUMH**, **KSCHL** (tipo de condición), **KAPPL** (aplicación 'M' = MM), **KVEWE** (uso), **KOTABNR** (nº de tabla de condiciones), **VAKEY** (clave variable, 100 char, concatenación de la clave de acceso), **DATAB/DATBI** (validez), ERDAT/ERNAM (creado por/fecha) | — |
| **KONP** | Partida de condición: **KNUMH**, **KOPOS** (nº secuencial), **KSCHL**, **KBETR** (importe/porcentaje), **KONWA** (moneda o %), **KPEIN** (unidad de precio, "per 100/1000"), **KMEIN** (unidad), **KRECH** (tipo de cálculo), **STFKZ** (tipo de escala), **KSTBM/KONMS** | — |
| **KONM** | Condiciones con escala 1-dimensional (quantity scale): **KSTBM** (cantidad de escala, QUAN, ref. KMEIN), **KBETR/KPEIN/KMEIN** | — |
| **KONV** | Condiciones de **documento** (transacción): copia de runtime para PO/contrato/scheduling agreement; enlazada por **EKKO-KNUMV** y item **EKPO-EBELP → KONV-KPOSN** | KBETR, KWERT |

- **Relación A0xx → KONP:** de la tabla A0xx se toma **KNUMH** y con ese valor se lee **KONP** (y KONH) para obtener el importe. El campo **VAKEY** de KONH es la concatenación de la clave (material + proveedor + org. compras + planta + categoría de info record) y es la "llave" que usa la migración COND_A/IDoc para volver a enlazar. [VERIFICADO — SAP Community 9592388, 2542690, 5354701, 5949853]
- **Info record ↔ condición:** NO hay relación directa por número. La relación es por **clave de negocio**: EINE (INFNR→EINA da MATNR/LIFNR + EKORG/WERKS/ESOKZ) → construir clave → buscar en A017/A018/A025 → obtener KNUMH → leer KONP. O usar el FM `ME_GET_INFORECORD_CONDITIONS[_1]`. [VERIFICADO — SAP Community 5341449]

### 2.3 Documento de compras (PO/contrato/scheduling agreement)
- **EKKO-KNUMV** = número de condición del documento. → **KONV** (partidas de condición del documento, por EBELP/KPOSN). [VERIFICADO — gotothings, SAP Community 2499696]
- **EKPO-NETPR** = precio neto del item de PO (snapshot), como EINE-NETPR. [VERIFICADO — KBA 685117]

### 2.4 Material master (MM42/MM02)
- **MARC**: datos por planta de compras/MRP (EKGRP, DISPO, PLIFZ, WEBAZ, UEETO/UNETO/UEETK, EISBE, MATKL…). **Sin precios.** [VERIFICADO]
- **MBEW**: valoración por área de valoración — STPRS (precio estándar), VPRSV (control de precio S/V), VERPR, LPLPR (precio planificado actual), ZPLPR (futuro), ZPLP1-3 (precios planificados 1/2/3) y fechas ZPLD1-3. [VERIFICADO — prospecta; SAP Learning "Changing Prices"]
- Cambios en el material master se registran en **documentos de modificación** (CDHDR/CDPOS, t-codes MM04/MM44). [VERIFICADO — SAP Learning "Maintaining Material Master Data"]

---

## 3. Tipos de condición y esquemas de cálculo

- **PB00 = precio bruto (gross price), tipo de condición estándar**, con secuencia de acceso y por tanto capacidad de determinación automática. Se mantiene en el info record y en contratos; es la base del cálculo (categoría de condición "H" = precio base). [VERIFICADO — SAP Learning; sapmm.wordpress; KBA 2997609]
- **PBXX = precio bruto manual**, sin secuencia de acceso: se usa cuando no hay registro PB00 (primera compra). En el esquema, PB00 y PBXX comparten step/counter con rutina de exclusión "6" para que nunca aparezcan juntos. [VERIFICADO — SAP Community 6915317]
- **PB01:** fuentes encontradas son **ambiguas**:
  - En material de SAP Academy y guru99, **PB01 aparece como nombre de secuencia de acceso** del precio bruto ("Access sequence: PB01", con tablas 16/17/18/25/28). [PARCIAL]
  - En SAP Community se dice que "PB01 no es estándar" / es un tipo de condición manual de cliente. [PARCIAL]
  - En otros clientes aparece como condición de **precio neto** (bruto − descuentos + recargos). [CONOCIMIENTO PREVIO]
  - **Recomendación:** validar en el sistema destino (t-code M/06, M/03, V/05) qué es PB00/PB01 realmente (condición vs. secuencia de acceso).
- **Otros tipos habituales:** RA00/RA01 (descuento %/importe), FRB1/FRC1 (flete), ZB00 (descuento por pronto pago), RC00 (rebate). [VERIFICADO — gugulii]
- **Esquema de cálculo estándar:** **RM0000** (PO), RM0001/RM1001 (contratos), RM1000 (esquemas alternativos). Se determina por **schema group de proveedor × org. de compras**. [VERIFICADO — sapdatasheet IMG SIMG_CFMENUOLMEOMER5; SAP Learning]
- **Secuencia de acceso estándar del precio:** busca en orden: contrato → info record vendor+material (+planta) → vendor+material group → vendor → general; los accesos son **exclusivos** (el primero que encuentra registró "gana"). [VERIFICADO — guru99; digitalerps; atvarta]

---

## 4. Qué sucede al guardar un "nuevo precio neto"

### 4.1 Guardando en ME11/ME12 (info record) o MEK1/MEK2 (condición)
[VERIFICADO — SAP Community 7366263, 9592388; KBA 685117; gugulii]
1. Se crea/actualiza **EINA** (si no existe) y **EINE** (org. de compras), incluyendo **EINE-NETPR** (valor "plano" calculado a partir de las condiciones en la fecha actual).
2. Se crea/actualiza el **registro de condición**: fila en la tabla A0xx correspondiente (A018 sin planta / A017 con planta / A025-A028 para no-stock) con su **KNUMH**, más **KONH** (cabecera con KSCHL=PB00, VAKEY, validez DATAB/DATBI) y **KONP** (partida con **KBETR** = importe, KPEIN/KMEIN). Si hay escala de cantidad → **KONM**.
3. Se registra **documento de modificación** (cambios) y el histórico de precios (**EIPA**).
4. En los contratos (ME31K) se actualizan a la vez KONP/KONH y **EKPO-NETPR**. [VERIFICADO — KBA 685117]

### 4.2 Guardando en MM42 (o MM02)
[VERIFICADO — SAP Learning "Maintaining Material Master Data"; KBA 2463872; CONOCIMIENTO PREVIO para el detalle interno]
1. Se actualizan **solo tablas de material master** (MARA/MARC/MBEW y dependencias). Por ejemplo, cambiar MRP controller por MM42 graba MARC-DISPO.
2. Se genera **documento de modificación** (CDHDR/CDPOS).
3. **NO se crea ni actualiza** ninguna condición (KONP/KONH/A0xx) ni info record (EINA/EINE). El sistema estándar no propaga el precio del material master hacia compras.
4. **Conclusión:** si el usuario "introduce un precio neto en MM42" y ese campo no existe en el estándar, o es un **campo custom** (solo se guarda en una tabla append de cliente), o el dato realmente se introduce en el info record (ME12) / condiciones (MEK2) / PO (ME22N) — no en MM42. Si existe un BAdI/user exit (p. ej. `BADI_MAT_F_SPEC_SEL` o user exits del material master), podría existir lógica custom que sí propague el precio; hay que revisarla. [CONOCIMIENTO PREVIO]

---

## 5. Advertencias y trampas

1. **MARC-NETPR no existe en el estándar.** [VERIFICADO] Cualquier referencia a él es un campo custom. Si el proyecto lo usa, hay que documentar la tabla append y verificar que tenga lógica de propagación.
2. **EINE-NETPR es un "snapshot", no la fuente operativa.** [VERIFICADO — KBA 685117, 3261722] La determinación de precio en el PO lee la **secuencia de acceso → tablas A0xx → KONP**, NO EINE-NETPR directamente. Por eso puede haber consistencia entre "condición correcta en el PO" y "EINE-NETPR = 0/desactualizado".
3. **Actualizar solo EINE-NETPR (vía SE16/BAPI) no cambia el precio del PO.** [VERIFICADO — KBA 3261722] El PO seguirá tomando la condición (KONP). Hay que actualizar las condiciones (MEK2/MEK1 o la condición PB00).
4. **Actualizar solo las condiciones no actualiza EINE-NETPR** si hay validez temporal: las condiciones del info record son **dependientes de tiempo** y pueden tener varias valideces (escalas/períodos); EINE no tiene validez propia y guarda el valor vigente a la fecha de la última sincronización. Hay que ejecutar el report **RM06INP0** (info records) / **RM06ENP0** (contratos) / **RM06ENP1** (scheduling agreements) para resincronizar NETPR. [VERIFICADO — KBA 685117; SAP Community 7366263]
5. **Cambiar condiciones después de crear el PO no afecta a POs existentes** (los POs son time-independent y copian a KONV en creación). [VERIFICADO — gugulii mm-a06-04]
6. **La clave del registro de condición es crítica:** un key incompleto o un registro con validez vencida hace que el acceso falle en silencio y el PO quede "sin precio" (requiere PBXX manual o da error). [VERIFICADO — guru99; gugulii]
7. **En S/4HANA la técnica de condiciones de MM no cambió** (MEK1/MEK2/MEK3 siguen siendo las transacciones; app Fiori "Manage Purchase Conditions" F2401 en S/4HANA 2020+). [VERIFICADO — gugulii]
8. **ABAP (convención de diccionario, para el que lo lea con la skill sap-abap):** los campos de importe son `CURR` con `Reference Field` de moneda (KBETR→KONWA, EINE-NETPR→WAERS) y los de cantidad `QUAN` con referencia a `UNIT` (KSTBM→KMEIN); claves: primera columna `MANDT`/`CLNT`. [VERIFICADO — skill local abap-dictionary.md] Esto importa si se van a leer las tablas con ABAP SQL: hay que traer siempre el campo de moneda/unidad junto al importe.

---

## 6. Fuentes consultadas

Web:
1. SAP Learning, "Analyzing Price Determination Basics" (PB00, RM0000, escalas, info records): https://learning.sap.com/courses/purchasing-in-sap-s-4hana-br/analyzing-price-determination-basics
2. SAP Learning, "Maintaining Purchasing Info Record" (gross/net/effective price): https://learning.sap.com/courses/business-processes-in-sap-s-4hana-sourcing-procurement-br/maintaining-purchasing-info-record
3. gugulii.com, "SAP MM Price Condition" (MEK1-3, KONP/KONV, A017/A018/A019/A020, acceso 0002, PB00): https://sap.gugulii.com/docs/s4-mm/mm-a06-04/
4. gugulii.com, "SAP MM Purchasing Info Record" (EINA/EINE/KONP, PB00/PBXX/RA00/FRB1): https://sap.gugulii.com/docs/s4-mm/mm-a06-01/
5. KBA 685117, "Net Price in Info Record or Contract is wrong" (RM06INP0/RM06ENP0/RM06ENP1, EINE-NETPR snapshot): http://www.baidusap.com/wp-content/uploads/685117_E_20191202.pdf
6. KBA 3261722, "ZERO net price for info record despite of the price in EINE-NETPR" (KONP/KONH/A018): https://userapps.support.sap.com/sap/support/knowledge/en/3261722
7. KBA 1922892, "Condition supplements for the gross price PB00": https://userapps.support.sap.com/sap/support/knowledge/en/1922892
8. leanx.eu, tablas A017, A018, A019, A025, KONH, KONP, KONV (campos y claves): https://leanx.eu/sap/table/a017/ (y equivalentes para a018, a019, a025, konh, konp, konv)
9. docsfortec.com, KONP/KONH (campos S/4): https://docsfortec.com/sap/S4/tables/KONP/ ; https://docsfortec.com/sap/S4/tables/KONH
10. sapstack.com, KONP fields: https://sapstack.com/tables/tabledetails.php?table=KONP
11. datapanda.eu, MARC (304 campos, sin NETPR): https://datapanda.eu/en/sap/table/MARC
12. sapdatasheet.org, EINE-NETPR (CURR 11/2, ref WAERS): https://www.sapdatasheet.org/abap/tabl/eine-netpr.html
13. SAP Community, "Purchasing Info - link between KONP/KONH and EINA/EINE": https://community.sap.com/t5/enterprise-resource-planning-q-a/purchasing-info-link-between-konp-konh-and-eina-eine/qaq-p/5354701
14. SAP Community, "KONP table & Corresponding Inforecord No" (ME_GET_INFORECORD_CONDITIONS): https://community.sap.com/t5/enterprise-resource-planning-q-a/konp-table-corresponding-inforecord-no/qaq-p/5341449
15. SAP Community, "Info record EINE-NETPR not getting updated with conditional valid price" (RM06INP0): https://community.sap.com/t5/enterprise-resource-planning-q-a/info-record-eine-netpr-not-getting-updated-with-conditional-valid-price/qaq-p/7366263
16. SAP Community, "Get conditions by scales for info Record" (A017/A018, KNUMH→KONP): https://community.sap.com/t5/enterprise-resource-planning-q-a/get-conditions-by-scales-for-info-record/qaq-p/5949853
17. SAP Community, "How to Create pricing Condition Record ... (VAKEY, A017/A018/A025, COND_A)": https://community.sap.com/t5/enterprise-resource-planning-q-a/how-to-create-pricing-condition-record-for-purchase-info-record-through/qaq-p/9592388
18. SAP Community, "How to link to the KONP table from EINE or EKKO/EKPO" (A016/A017→KNUMH): https://community.sap.com/t5/enterprise-resource-planning-q-a/how-to-link-to-the-konp-table-from-eine-or-from-ekko-ekpo/qaq-p/2542690
19. SAP Community, "PB00 & PB25 condition type" y "Conditions PB00 and PBXX" (acceso, determinación): https://community.sap.com/t5/enterprise-resource-planning-q-a/pb00-pb25-condition-type/qaq-p/2635059 ; https://community.sap.com/t5/enterprise-resource-planning-q-a/conditions-pb00-and-pbxx/qaq-p/6812597
20. SAP Community, "difference between pb00 and pb01" (PB01 no estándar): https://community.sap.com/t5/enterprise-resource-planning-q-a/difference-between-pb00-and-pb01/qaq-p/7007482
21. guru99.com, "How to Define Access Sequence and Condition Table" (secuencia PB01, tabla 18, exclusividad, requisitos): https://www.guru99.com/it/how-to-define-access-sequence-and-condition-table.html
22. sapmm.wordpress.com, "What is PB00?" (categoría H, tabla 017): https://sapmm.wordpress.com/2009/03/06/what-is-pb00/
23. sapdatasheet.org, IMG "Define Calculation Schema" (RM0000/RM1000, PB00/PBXX): https://www.sapdatasheet.org/abap/cus0/simg_cfmenuolmeomer5.html
24. erpyourself.net, MM42 (programa SAPMMG02, "Change Material &"): https://erpyourself.net/en/sap-transaction-codes/MM42.html ; tcodesearch.com/sap-tcodes/MM42
25. beneering.com, "SAP MM transactions overview" (MM41/42/43 = Create/Change/Display Material IR-Retail): https://www.beneering.com/en/sap-procurement/sap-mm-guide/sap-mm-transaction/
26. tutorialkart.com, "What is Purchasing View in SAP MM?" (campos de la vista compras): https://www.tutorialkart.com/what-is-purchasing-view-in-sap-mm/
27. sap4tech.net, "SAP Info Record Tables, Transaction Code And ABAP Report" (EINE/EINA/EIPA/A017/A018, ME11-18): https://sap4tech.net/sap-info-record-table-tcodes-report/
28. prospecta.com, "Material Master Module List" (MBEW STPRS/LPLPR/ZPLPR/ZPLP1-3): https://helpcentre.prospecta.com/wp-content/uploads/2023/12/Material-Master-Module-List.pdf
29. SAP Learning, "Maintaining Material Master Data" (change documents, MM02): https://learning.sap.com/courses/business-processes-in-sap-s-4hana-sourcing-procurement-br/maintaining-material-master-data
30. SAP Learning, "Changing Prices in the Material Master" (MR21, precios MBEW): https://learning.sap.com/courses/product-cost-planning-in-sap-s-4hana/changing-prices-in-the-material-master
31. gotothings.com, "Retrieve the Purchase Order Condition Records Table" (EKKO-KNUMV→KONV; KONH KSCHL=PB00; KONP): http://www.gotothings.com/sapab025.htm
32. trailsap.com, KONM "Conditions (1-Dimensional Quantity Scale)" (KSTBM): https://www.trailsap.com/sap/?sap-table=konm

Local:
33. Skill sap-abap (ABAP Dictionary reference — convenciones CURR/QUAN/claves): `/home/agarcia/.agents/skills/sap-abap/references/abap-dictionary.md` y `SKILL.md`.

---

## 7. Estado de verificación por punto (para el revisor)

| Punto | Estado | Fuente |
|---|---|---|
| MM42 = "Change Material &" (LO-Article/IS-Retail, SAPMMG02) | VERIFICADO | erpyourself, beneering |
| La vista Compras del material master no tiene condiciones/precio | VERIFICADO | tutorialkart, SAP Learning |
| MARC no contiene NETPR (ni precios) | VERIFICADO | datapanda (dump 304 campos, sin NETPR) |
| Precio neto de compras = EINE-NETPR (CURR ref WAERS) | VERIFICADO | sapdatasheet, KBA 3261722 |
| EINA (general) / EINE (org compras) / EIPA (histórico) | VERIFICADO | sap4tech, gugulii |
| Tabla de condiciones A0xx (A017/A018/A025/A028/A019) con KNUMH | VERIFICADO | leanx (A017/A018/A019/A025), tcodesearch (A025), SAP Community |
| KONH (cabecera: KNUMH/KSCHL/VAKEY/DATAB/DATBI) | VERIFICADO | leanx, docsfortec |
| KONP (partida: KBETR/KPEIN/KMEIN/KONWA/KRECH) | VERIFICADO | leanx, docsfortec, sapstack |
| KONM = escalas de cantidad (KSTBM) | VERIFICADO | trailsap, sapdatasheet |
| KONV = condiciones de documento; enlace EKKO-KNUMV | VERIFICADO | gotothings, SAP Community 2499696 |
| PB00 = precio bruto automático; PBXX = manual con exclusión 6 | VERIFICADO | SAP Learning, SAP Community 6915317, KBA 1922892/2997609 |
| PB01: condición "no estándar" vs. secuencia de acceso | PARCIAL (ambiguo) | SAP Community 7007482 vs. guru99/SAP Academy |
| RM0000 esquema estándar; schema group proveedor×org.compras | VERIFICADO | sapdatasheet IMG, SAP Learning |
| Guardar info record/condición → EINA/EINE + A0xx + KONH/KONP (+KONM) + log | VERIFICADO | KBA 685117, SAP Community 7366263/9592388 |
| Guardar MM42 → solo material master + change doc, sin condiciones ni info record | VERIFICADO (parte master) / CONOCIMIENTO PREVIO (detalle "no toca condiciones") | SAP Learning; análisis |
| EINE-NETPR snapshot; resync con RM06INP0/RM06ENP0/RM06ENP1 | VERIFICADO | KBA 685117, SAP Community 7366263 |
| Cambios de condición no afectan a POs ya creados | VERIFICADO | gugulii mm-a06-04 |
| S/4HANA: técnica de condiciones sin cambios; F2401 en 2020+ | VERIFICADO | gugulii mm-a06-04 |
| Precios del material master en MBEW (STPRS/VPRSV/ZPLP1-3) | VERIFICADO | prospecta, SAP Learning |
| Convenciones ABAP Dictionary (CURR ref, QUAN ref, claves) | VERIFICADO | skill local abap-dictionary.md |
