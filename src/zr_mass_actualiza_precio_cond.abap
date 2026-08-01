*&---------------------------------------------------------------------*
*& Report  ZR_MASS_ACTUALIZA_PRECIO_COND
*&---------------------------------------------------------------------*
*& PROPÓSITO
*& --------
*& Actualización MASIVA del precio neto de compra (condición PB00/PB01)
*& de los registros de información de compras (info record) que se
*& visualizan en la sección "condiciones de precio neto" de la vista
*& Compras de MM42.
*&
*& "Cambiar el precio en MM42" técnicamente = mantener el registro de
*& condición PB00/PB01 del info record (A017/A018 -> KONH -> KONP,
*& campo KBETR) y resincronizar el precio neto informativo EINE-NETPR
*& con el reporte estándar RM06INP0.
*&
*& USO
*& ---
*& 1. Preparar un CSV (separador ';') con las columnas de la sección
*&    "ESTRUCTURA DE ENTRADA" (la primera línea se omite como cabecera).
*& 2. Ejecutar el reporte con p_test = 'X' (test run) y revisar el ALV.
*&    El modo test NO llama al FM de modificación (ME_INFORECORD_MAINTAIN):
*&    solo valida las filas y las marca como "TEST OK (no aplicado)".
*&    No se escribe la Z-tabla de log ni se emite COMMIT de datos de
*&    negocio, por lo que es totalmente NO destructivo.
*& 3. Repetir en producción con p_test = ' ' (grabará y hará COMMIT).
*& 4. Después de la actualización ejecutar RM06INP0 para sincronizar
*&    EINE-NETPR / EINE-PEINH / EINE-WAERS a partir de las condiciones.
*&
*& TRANSACCIONES RELACIONADAS
*& -------------------------
*& ME11/ME12/ME13 (info record), MEK1/MEK2/MEK3 (condiciones),
*& MEKP (cambio masivo estándar, vía manual recomendada),
*& ME1E (historial de precios), RM06INP0 (resincroniza EINE-NETPR),
*& SLG1 (visualizar application log), SM35 (sesiones batch si se usa BDC).
*&
*& ⚠ NOTA CRÍTICA - VERIFICAR EN SE37/SE11 ANTES DE ACTIVAR
*& ---------------------------------------------------------
*& El método principal es ME_INFORECORD_MAINTAIN (grupo de funciones
*& MEWIPIR): firma y estructuras MEWIEINA/MEWIEINAX/MEWIEINE/MEWIEINEX,
*& MEWIVALIDITY_TT, MEWICONDITION_TT (COND_TYPE='PB00', COND_VALUE,
*& CURRENCY, COND_P_UNT, COND_UNIT, CHANGE_ID='U') y MEWI_TT_RETURN,
*& documentadas en research/03_mejor_practica_ejemplo.md §2.1.
*& Confirmar nombres exactos de campos en SE11/SE37 del sistema destino.
*&
*& ⚠ BAPI_INFORECORD_CHANGE NO está confirmado como BAPI liberado
*& (research/02 §§39-43): se documenta solo como ALTERNATIVA comentada
*& al final del reporte (estructuras MEIRPRCGCONDREC/MEIRPRCGCONDRECX),
*& pendiente de verificar su firma en SE37 del sistema destino.
*&
*& Nota de soporte: ME_INFORECORD_MAINTAIN está marcado como OBSOLETO
*& (KBA 2787315). Si la versión del sistema lo rechaza, usar la
*& alternativa BDC sobre ME12 (comentada) o, en S/4HANA moderno, el
*& servicio OData "Purchasing Info Record" (clean core) / LTMC.
*&
*& Referencia técnica de la investigación:
*&   research/01_data_model_mm42.md
*&   research/02_apis_actualizacion_masiva.md
*&   research/03_mejor_practica_ejemplo.md
*&---------------------------------------------------------------------*
REPORT zr_mass_actualiza_precio_cond.

*---------------------------------------------------------------------*
*  Tipos de datos
*---------------------------------------------------------------------*
" Estructura de entrada (una fila del CSV / una fila del ALV)
TYPES: BEGIN OF ty_in,
         matnr     TYPE matnr,      " Material
         lifnr     TYPE lifnr,      " Proveedor
         ekorg     TYPE ekorg,      " Organización de compras
         werks     TYPE werks_d,    " Planta
         infnr     TYPE infnr,      " Nº de info record (opcional: se deriva si se omite)
         kschl     TYPE kschl,      " Tipo de condición (default PB00)
         kbetr     TYPE kbetr,      " Nuevo importe de la condición (precio)
         konwa     TYPE konwa,      " Moneda (si se omite, se toma de EINE-WAERS)
         peinh     TYPE kpein,      " Unidad de precio (default 1)
         kmein     TYPE kmein,      " Unidad de medida (base del precio)
         datab     TYPE datab,      " Válido desde (default = hoy)
         datbi     TYPE datbi,      " Válido hasta (default = 31.12.9999)
         netpr_old TYPE eine-netpr, " EINE-NETPR previo (relleno interno, NO se lee del CSV)
         msgid     TYPE msgid,      " Clase del mensaje de error del FM (relleno interno)
         msgno     TYPE msgno,      " Nº de mensaje de error del FM (relleno interno)
         msgty     TYPE msgty,      " Tipo de mensaje del FM (relleno interno)
         msg       TYPE string,     " Mensaje de validación / resultado
       END OF ty_in.

" Info record válido (EINA + EINE) para validación masiva
TYPES: BEGIN OF ty_inforec,
         matnr TYPE matnr,
         lifnr TYPE lifnr,
         ekorg TYPE ekorg,
         werks TYPE werks_d,
         infnr TYPE infnr,          " EINE-INFNR
         waers TYPE eine-waers,     " Moneda del info record (default de konwa)
         netpr TYPE eine-netpr,     " EINE-NETPR previo (para el log)
         peinh TYPE eine-peinh,     " EINE-PEINH previo (para el log)
       END OF ty_inforec.

" Registro de log (espejo de la Z-tabla sugerida ZPIR_PRICELOG)
TYPES: BEGIN OF ty_log,
         logid     TYPE string,     " Identificador (GUID o secuencia)
         uname     TYPE syuname,
         datum     TYPE sy-datum,
         uzeit     TYPE sy-uzeit,
         testflag  TYPE abap_bool,  " 'X' = corrida de prueba
         matnr     TYPE matnr,
         lifnr     TYPE lifnr,
         ekorg     TYPE ekorg,
         werks     TYPE werks_d,
         infnr     TYPE infnr,
         kschl     TYPE kschl,
         netpr_old TYPE eine-netpr, " Precio neto informativo previo
         kbetr_new TYPE kbetr,      " Nuevo importe de condición
         konwa     TYPE konwa,
         peinh     TYPE eine-peinh,
         kmein     TYPE kmein,
         datab     TYPE datab,
         datbi     TYPE datbi,
         msgty     TYPE msgty,
         msgid     TYPE msgid,
         msgno     TYPE msgno,
         msgv1     TYPE msgv1,
         msgv2     TYPE msgv2,
         msgv3     TYPE msgv3,
         msgv4     TYPE msgv4,
         tcode     TYPE tcode,
       END OF ty_log.

" Tipos mínimos para las tablas de validación (evitan asignación
" posicional incorrecta al usar SELECT de columna única)
TYPES: BEGIN OF ty_mara,
         matnr TYPE mara-matnr,
       END OF ty_mara,
       BEGIN OF ty_lfa1,
         lifnr TYPE lfa1-lifnr,
       END OF ty_lfa1,
       BEGIN OF ty_tcurc,
         waers TYPE tcurc-waers,
       END OF ty_tcurc.

" Espejo local tipo BAPIRET2: el RETURN de ME_INFORECORD_MAINTAIN
" (MEWI_TT_RETURN) se transfiere aquí con CORRESPONDING para leer
" mensajes con nombres estándar (verificar en SE11 la estructura real).
TYPES: BEGIN OF ty_bapiret2,
         msgty   TYPE msgty,
         msgid   TYPE msgid,
         msgno   TYPE msgno,
         msgv1   TYPE msgv1,
         msgv2   TYPE msgv2,
         msgv3   TYPE msgv3,
         msgv4   TYPE msgv4,
         message TYPE bapiret2-message,
       END OF ty_bapiret2.

TYPES: ty_in_t      TYPE STANDARD TABLE OF ty_in      WITH EMPTY KEY,
       ty_inforec_t TYPE SORTED TABLE OF ty_inforec
                      WITH NON-UNIQUE KEY matnr lifnr ekorg werks infnr,
       ty_log_t     TYPE STANDARD TABLE OF ty_log     WITH EMPTY KEY.

*---------------------------------------------------------------------*
*  Pantalla de selección
*---------------------------------------------------------------------*
DATA: c_blk TYPE string,            " Título del bloque
      c_ttl TYPE string.            " Comentario explicativo

SELECTION-SCREEN BEGIN OF BLOCK b1 WITH FRAME TITLE c_blk.
SELECTION-SCREEN COMMENT /1(79) c_ttl.
PARAMETERS:
  p_file TYPE rlgrap-filename LOWER CASE,   " Ruta del CSV/Excel de entrada
  p_test TYPE abap_bool DEFAULT abap_true,  " Test run: 'X' = no graba
  p_pkg  TYPE i DEFAULT 50,                 " Tamaño de paquete (flush de log)
  p_alv  TYPE abap_bool DEFAULT abap_true.  " Mostrar resultado en ALV al final
SELECTION-SCREEN END OF BLOCK b1.

INITIALIZATION.
  c_blk = 'Parámetros'.
  c_ttl = 'Actualización masiva del precio neto (PB00/PB01) del info record de compras'.

*---------------------------------------------------------------------*
*  Variables globales
*---------------------------------------------------------------------*
DATA: gt_input  TYPE ty_in_t,
      gt_log    TYPE ty_log_t,
      lt_logbuf TYPE ty_log_t,      " Buffer de log para ZPIR_PRICELOG
      lv_ok     TYPE i,             " Filas actualizadas OK
      lv_err    TYPE i,             " Filas con error
      lv_skip   TYPE i.             " Filas saltadas por validación

*---------------------------------------------------------------------*
*  START-OF-SELECTION
*---------------------------------------------------------------------*
START-OF-SELECTION.

  " ---------- 1. Carga del archivo ----------
  PERFORM load_file.

  IF gt_input IS INITIAL.
    MESSAGE 'No se cargaron filas del archivo (revisar ruta/formato/separador).' TYPE 'E'.
  ENDIF.

  " ---------- 2. Validación previa en masa ----------
  PERFORM validate_input CHANGING lv_skip.

  " ---------- 3. Procesamiento (ME_INFORECORD_MAINTAIN) ----------
  PERFORM process_input CHANGING lv_ok lv_err.

  " ---------- 4. Logging (BAL) y salida ----------
  PERFORM save_log.
  PERFORM show_results.

*---------------------------------------------------------------------*
*  FORM LOAD_FILE: carga el CSV en gt_input
*---------------------------------------------------------------------*
FORM load_file.
  DATA lt_csv TYPE TABLE OF string.
  DATA ls_in  TYPE ty_in.

  IF p_file IS INITIAL.
    MESSAGE 'Indique el archivo de entrada (p_file).' TYPE 'E'.
  ENDIF.

  " TODO: adaptar filetype / codepage / separador al entorno de trabajo.
  CALL METHOD cl_gui_frontend_services=>gui_upload
    EXPORTING
      filename = p_file
      filetype = 'ASC'
    CHANGING
      data_tab = lt_csv.

  " TODO: ajustar las columnas exactas del CSV si difieren.
  " La primera línea se omite (cabecera).
  " Columnas esperadas (en este orden, separadas por ';'):
  "   MATNR;LIFNR;EKORG;WERKS;INFNR;KSCHL;KBETR;KONWA;PEINH;KMEIN;DATAB;DATBI
  " Ejemplo (punto decimal recomendado para KBETR):
  "   1000001;0000012345;1000;3000;;PB00;12.50;EUR;1;ST;01.08.2026;31.12.9999
  LOOP AT lt_csv INTO DATA(lv_line) FROM 2.
    IF lv_line IS INITIAL.
      CONTINUE.
    ENDIF.

    SPLIT lv_line AT ';' INTO
          DATA(lv_mat)    DATA(lv_lif)    DATA(lv_ekorg) DATA(lv_werks)
          DATA(lv_infnr)  DATA(lv_kschl)  DATA(lv_kbetr) DATA(lv_konwa)
          DATA(lv_peinh)  DATA(lv_kmein)  DATA(lv_datab) DATA(lv_datbi).

    CLEAR ls_in.
    ls_in-matnr = lv_mat.
    ls_in-lifnr = lv_lif.
    ls_in-ekorg = lv_ekorg.
    ls_in-werks = lv_werks.
    ls_in-infnr = lv_infnr.
    ls_in-kschl = lv_kschl.
    ls_in-kbetr = lv_kbetr.
    ls_in-konwa = lv_konwa.
    ls_in-peinh = lv_peinh.
    ls_in-kmein = lv_kmein.
    ls_in-datab = lv_datab.
    ls_in-datbi = lv_datbi.

    " Conversión ALPHA (ceros a la izquierda) de material y proveedor
    ls_in-matnr = |{ ls_in-matnr ALPHA = IN }|.
    ls_in-lifnr = |{ ls_in-lifnr ALPHA = IN }|.

    " Fechas: se acepta formato interno YYYYMMDD o DD.MM.YYYY (ver FORM convert_date)
    PERFORM convert_date CHANGING ls_in-datab.
    PERFORM convert_date CHANGING ls_in-datbi.

    " TODO (M1 - separador decimal): la conversión de lv_kbetr (string)
    " a kbetr (CURR) usa el separador decimal del LOCALE del usuario.
    " Recomendación: estandarizar el CSV con PUNTO decimal. Si el CSV
    " llega con coma (locales es-*), normalizar antes del MOVE:
    "   REPLACE ',' WITH '.' IN lv_kbetr.

    APPEND ls_in TO gt_input.
  ENDLOOP.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM CONVERT_DATE: convierte DD.MM.YYYY a YYYYMMDD (si aplica)
*---------------------------------------------------------------------*
FORM convert_date CHANGING cv_date TYPE any.
  DATA lv_date TYPE string.
  DATA lv_d    TYPE string.
  DATA lv_m    TYPE string.
  DATA lv_y    TYPE string.

  lv_date = cv_date.
  SHIFT lv_date LEFT DELETING LEADING space.
  IF lv_date IS INITIAL.
    RETURN.
  ENDIF.
  IF lv_date CS '.'.
    SPLIT lv_date AT '.' INTO lv_d lv_m lv_y.
    lv_date = |{ lv_y }{ lv_m }{ lv_d }|.
  ENDIF.
  cv_date = lv_date.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM VALIDATE_INPUT: validaciones en masa + reglas por fila
*---------------------------------------------------------------------*
FORM validate_input CHANGING cv_skip TYPE i.
  DATA lt_mara     TYPE SORTED TABLE OF ty_mara  WITH UNIQUE KEY matnr.
  DATA lt_lfa1     TYPE SORTED TABLE OF ty_lfa1  WITH UNIQUE KEY lifnr.
  DATA lt_tcurc    TYPE SORTED TABLE OF ty_tcurc WITH UNIQUE KEY waers.
  DATA lt_inforec  TYPE ty_inforec_t.
  DATA ls_inforec  TYPE ty_inforec.

  IF gt_input IS INITIAL.
    RETURN.
  ENDIF.

  " --- Carga en masa de maestros para validación (una sola pasada) ---
  SELECT matnr FROM mara INTO TABLE @lt_mara
    FOR ALL ENTRIES IN @gt_input
    WHERE matnr = @gt_input-matnr.

  SELECT lifnr FROM lfa1 INTO TABLE @lt_lfa1
    FOR ALL ENTRIES IN @gt_input
    WHERE lifnr = @gt_input-lifnr.

  SELECT waers FROM tcurc INTO TABLE @lt_tcurc
    FOR ALL ENTRIES IN @gt_input
    WHERE waers = @gt_input-konwa.

  " Info records existentes y NO borrados lógicamente.
  " Convención del proyecto: excluir registros borrados (EINA-LOEKZ <> 'L').
  " TODO: si en el sistema destino el maestro usa otro indicador de
  " borrado (p. ej. LOEVM_KO en otros maestros), ajustar el WHERE.
  SELECT eina~matnr, eina~lifnr, eine~ekorg, eine~werks, eine~infnr,
         eine~waers, eine~netpr, eine~peinh
    FROM eina AS eina
    INNER JOIN eine AS eine ON eine~infnr = eina~infnr
    INTO CORRESPONDING FIELDS OF TABLE @lt_inforec
    FOR ALL ENTRIES IN @gt_input
    WHERE eina~matnr = @gt_input-matnr
      AND eina~lifnr = @gt_input-lifnr
      AND eina~loekz <> 'L'
      AND eine~ekorg = @gt_input-ekorg
      AND eine~werks = @gt_input-werks.

  " Quitar duplicados: EINE puede tener varias ESOKZ (0 normal, 1
  " consignación, 3 subcontratación, P pipeline) para el mismo INFNR +
  " EKORG + WERKS. La tabla es SORTED NON-UNIQUE por la clave completa;
  " se conserva la primera ocurrencia y el READ TABLE con clave
  " (incluida la de prefijo) usa búsqueda binaria.
  DELETE ADJACENT DUPLICATES FROM lt_inforec
    COMPARING matnr lifnr ekorg werks infnr.

  " --- Validación fila a fila ---
  LOOP AT gt_input ASSIGNING FIELD-SYMBOL(<fs>).
    " TODO: validación de autorización. El objeto correcto para
    " info records es M_EINK (M_BANF es de solicitudes de compra y NO
    " aplica aquí). Ejemplo:
    "   AUTHORITY-CHECK OBJECT 'M_EINK' ID 'EKORG' FIELD <fs>-ekorg.
    "   (verificar también S_LCD / actividad 01-02 según el perfil)

    IF <fs>-matnr IS INITIAL OR <fs>-lifnr IS INITIAL
       OR <fs>-ekorg IS INITIAL OR <fs>-werks IS INITIAL.
      <fs>-msg = 'Faltan campos clave (matnr/lifnr/ekorg/werks)'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.

    IF NOT line_exists( lt_mara[ matnr = <fs>-matnr ] ).
      <fs>-msg = 'Material no existe en MARA'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.

    IF NOT line_exists( lt_lfa1[ lifnr = <fs>-lifnr ] ).
      <fs>-msg = 'Proveedor no existe en LFA1'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.

    " --- Info record: derivar INFNR si no viene en el archivo ---
    IF <fs>-infnr IS INITIAL.
      READ TABLE lt_inforec INTO ls_inforec
           WITH KEY matnr = <fs>-matnr
                    lifnr = <fs>-lifnr
                    ekorg = <fs>-ekorg
                    werks = <fs>-werks.
      IF sy-subrc <> 0.
        <fs>-msg = 'No existe info record para la clave (matnr/lifnr/ekorg/werks)'.
        cv_skip = cv_skip + 1.
        CONTINUE.
      ENDIF.
      <fs>-infnr = ls_inforec-infnr.
    ELSE.
      READ TABLE lt_inforec INTO ls_inforec
           WITH KEY matnr = <fs>-matnr
                    lifnr = <fs>-lifnr
                    ekorg = <fs>-ekorg
                    werks = <fs>-werks
                    infnr = <fs>-infnr.
      IF sy-subrc <> 0.
        <fs>-msg = 'No existe info record para la clave + INFNR'.
        cv_skip = cv_skip + 1.
        CONTINUE.
      ENDIF.
    ENDIF.

    " NOTA (ESOKZ): para la misma clave MATNR/LIFNR/EKORG/WERKS puede
    " haber VARIOS info records según la categoría de info record
    " (EINE-ESOKZ: 0 normal, 1 consignación, 3 subcontratación, P
    " pipeline), cada uno con su propio INFNR y condiciones.
    " - Si el CSV trae INFNR: se usa ese info record exacto.
    " - Si NO trae INFNR: se toma la primera ocurrencia de lt_inforec.
    " - TODO: si el negocio necesita apuntar a otra categoría, ampliar
    "   la estructura con una columna ESOKZ y filtrar lt_inforec.

    " Valor previo del info record (EINE-NETPR) para el log de la fila
    <fs>-netpr_old = ls_inforec-netpr.

    " --- Moneda: por defecto la del info record ---
    IF <fs>-konwa IS INITIAL.
      <fs>-konwa = ls_inforec-waers.
    ENDIF.
    IF <fs>-konwa IS INITIAL.
      <fs>-msg = 'Sin moneda válida (konwa)'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.
    IF NOT line_exists( lt_tcurc[ waers = <fs>-konwa ] ).
      <fs>-msg = 'Moneda no existe en TCURC'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.

    " --- Defaults ---
    IF <fs>-kschl IS INITIAL.
      <fs>-kschl = 'PB00'.   " precio bruto (validar en M/06)
    ENDIF.
    IF <fs>-peinh IS INITIAL OR <fs>-peinh = 0.
      <fs>-peinh = 1.
    ENDIF.
    IF <fs>-datab IS INITIAL.
      <fs>-datab = sy-datum.
    ENDIF.
    IF <fs>-datbi IS INITIAL.
      <fs>-datbi = '99991231'.
    ENDIF.

    " --- Reglas de negocio ---
    IF <fs>-datab > <fs>-datbi.
      <fs>-msg = 'Validez inválida: datab > datbi'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.
    IF <fs>-kbetr <= 0.
      " TODO: relajar si el negocio permite precios 0 o negativos.
      <fs>-msg = 'Precio (kbetr) debe ser mayor que 0'.
      cv_skip = cv_skip + 1.
      CONTINUE.
    ENDIF.

    " TODO: validar configuración del tipo de condición PB00/PB01 en
    " M/06 (cálculo tipo 'C', "cambios permitidos" = valor) y su
    " presencia en el procedimiento de cálculo RM0000 (M/08).
  ENDLOOP.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM PROCESS_INPUT: ME_INFORECORD_MAINTAIN por fila válida (B1)
*---------------------------------------------------------------------*
*  Método principal: ME_INFORECORD_MAINTAIN (grupo de funciones MEWIPIR).
*  Firma REAL (research/03_mejor_practica_ejemplo.md §2.1; SAP Community
*  12675375 / ABAPforum t=25328):
*    CALL FUNCTION 'ME_INFORECORD_MAINTAIN'
*      EXPORTING i_eina / i_einax / i_eine / i_einex / testrun
*      IMPORTING e_eina / e_eine
*      TABLES    txt_lines / cond_validity / condition /
*                cond_scale_value / cond_scale_quan / return
*  - MEWIEINA/MEWIEINAX/MEWIEINE/MEWIEINEX: el nº de info record es
*    INFO_REC (NO "infnr").
*  - MEWIVALIDITY_TT: VALID_FROM / VALID_TO / SERIAL_ID (sin DATAB/DATBI).
*  - MEWICONDITION_TT: SERIAL_ID + INFO_REC + COND_COUNT + COND_TYPE
*    ('PB00') + COND_VALUE + CURRENCY + COND_P_UNT + COND_UNIT +
*    CHANGE_ID ('I'/'U'/'X').
*  CONFIRMAR nombres exactos de campos en SE37/SE11 del sistema destino.
*
*  ⚠ B3 - MODO TEST (p_test = 'X'): NO se llama al FM.
*  Al terminar un reporte ABAP se emite un COMMIT implícito de la LUW
*  actual, por lo que "no hacer COMMIT" NO garantiza que no se grave.
*  Por eso, en modo test esta FORM solo revalida (validate_input ya lo
*  hizo) y marca las filas como 'TEST OK (no aplicado)': no hay llamada
*  de modificación, no se escribe la Z-tabla ni se emite COMMIT de
*  datos de negocio. Es totalmente NO destructivo.
*---------------------------------------------------------------------*
FORM process_input CHANGING cv_ok  TYPE i
                             cv_err TYPE i.
  DATA ls_eina    TYPE mewieina.             " Maestro (cabecera) info record
  DATA ls_einax   TYPE mewieinax.            " X-estructura de EINA (flags X)
  DATA ls_eine    TYPE mewieine.             " Datos por org. compras/planta
  DATA ls_einex   TYPE mewieinex.            " X-estructura de EINE (flags X)
  DATA le_eina    TYPE mewieina.             " Salida EINA del FM (IMPORTING)
  DATA le_eine    TYPE mewieine.             " Salida EINE del FM (IMPORTING)
  DATA lt_txt     TYPE mewipirtext_tt.       " Textos (no se usa)
  DATA lt_valid   TYPE mewivalidity_tt.      " Períodos de validez
  DATA ls_valid   TYPE mewivalidity.         " Elemento de validez
  DATA lt_cond    TYPE mewicondition_tt.     " Condiciones de precio PB00/PB01
  DATA ls_cond    TYPE mewicondition.        " Elemento de condición
  DATA lt_scalev  TYPE mewiscaleval_tt.      " Escalas valor (no se usa)
  DATA lt_scaleq  TYPE mewiscalequan_tt.     " Escalas cantidad (no se usa)
  DATA lt_return  TYPE mewi_tt_return.       " Mensajes del FM (verificar SE11)
  DATA lt_retmir  TYPE STANDARD TABLE OF ty_bapiret2 WITH EMPTY KEY.
  DATA ls_return  TYPE ty_bapiret2.          " Espejo del mensaje (B1)
  DATA lv_serial  TYPE i.                    " SERIAL_ID: vincula condición/validez
  DATA lv_msg     TYPE string.
  DATA lv_error   TYPE abap_bool.
  DATA ls_log     TYPE ty_log.

  LOOP AT gt_input ASSIGNING FIELD-SYMBOL(<fs>) WHERE msg IS INITIAL.

    " ---------- B3: modo test (no destructivo) ----------
    IF p_test = abap_true.
      <fs>-msg = 'TEST OK (no aplicado)'.
      cv_ok = cv_ok + 1.
      CONTINUE.
    ENDIF.

    " ---------- Llenar la condición de precio (PB00/PB01) ----------
    " B1c/B1d: MEWIVALIDITY usa VALID_FROM/VALID_TO/SERIAL_ID y
    " MEWICONDITION requiere SERIAL_ID + INFO_REC + COND_COUNT.
    " VERIFICAR tipos exactos en SE11 (p. ej. cond_value: numérico vs
    " string) y el comportamiento de SERIAL_ID/COND_COUNT para UPDATE
    " de condiciones existentes en QA.
    lv_serial = lv_serial + 1.               " mismo SERIAL_ID en condición y validez
    REFRESH: lt_cond, lt_valid, lt_return, lt_txt, lt_scalev, lt_scaleq.
    CLEAR:   ls_eina, ls_einax, ls_eine, ls_einex, le_eina, le_eine,
             ls_cond, ls_valid, ls_return.

    " Condición de precio (PB00/PB01)
    ls_cond-serial_id   = lv_serial.         " enlace con cond_validity
    ls_cond-info_rec    = <fs>-infnr.        " INFNR del info record
    ls_cond-cond_count  = 1.                 " nº de condición (1 por llamada)
    ls_cond-cond_type   = <fs>-kschl.        " PB00 (bruto) / PB01 (neto)
    ls_cond-cond_value  = <fs>-kbetr.        " nuevo importe
    ls_cond-currency    = <fs>-konwa.        " moneda
    ls_cond-cond_p_unt  = <fs>-peinh.        " unidad de precio
    ls_cond-cond_unit   = <fs>-kmein.        " unidad de medida
    ls_cond-change_id   = 'U'.               " I=insert / U=update / X=delete
    APPEND ls_cond TO lt_cond.

    " Validez de la condición (VALID_FROM/VALID_TO)
    ls_valid-serial_id  = lv_serial.         " debe coincidir con el de la condición
    ls_valid-valid_from = <fs>-datab.
    ls_valid-valid_to   = <fs>-datbi.
    APPEND ls_valid TO lt_valid.

    " Clave del info record (B1b): el campo es INFO_REC (no "infnr").
    " TODO: verificar campos requeridos en SE37/SE11 (p. ej. si el FM
    " exige además ESOKZ, LOEKZ, etc. en EINA/EINE para el sistema destino).
    ls_eina-matnr    = <fs>-matnr.
    ls_eina-lifnr    = <fs>-lifnr.
    ls_eina-info_rec = <fs>-infnr.
    ls_eine-info_rec = <fs>-infnr.
    ls_eine-ekorg    = <fs>-ekorg.
    ls_eine-werks    = <fs>-werks.
    " X-estructuras: 'X' en los campos a actualizar; en las claves se
    " pasa el valor (no 'X'). TODO: verificar en SE37 qué campos exigen
    " flag X para una actualización de solo condición.
    ls_einax-info_rec = <fs>-infnr.
    ls_einex-info_rec = <fs>-infnr.
    ls_einex-ekorg    = <fs>-ekorg.
    ls_einex-werks    = <fs>-werks.

    " ---------- Llamada al FM (firma real, B1a) ----------
    lv_error = abap_false.
    lv_msg   = ''.
    TRY.
        CALL FUNCTION 'ME_INFORECORD_MAINTAIN'
          EXPORTING
            i_eina       = ls_eina
            i_einax      = ls_einax
            i_eine       = ls_eine
            i_einex      = ls_einex
            testrun      = abap_false        " 'X' = no graba; aquí lo controla p_test
          IMPORTING
            e_eina       = le_eina
            e_eine       = le_eine
          TABLES
            txt_lines        = lt_txt
            cond_validity    = lt_valid
            condition        = lt_cond
            cond_scale_value = lt_scalev
            cond_scale_quan  = lt_scaleq
            return           = lt_return.
      CATCH cx_root INTO DATA(lx_exc).
        lv_error = abap_true.
        lv_msg   = lx_exc->get_text( ).
    ENDTRY.

    " ---------- Evaluar RETURN (MEWI_TT_RETURN) ----------
    " Se copia a un espejo BAPIRET2 con CORRESPONDING para leer con
    " nombres estándar. Si algún campo no se mapea en su sistema,
    " verificar la estructura real de MEWI_TT_RETURN en SE11.
    IF lv_error = abap_false.
      CLEAR lt_retmir.
      lt_retmir = CORRESPONDING #( lt_return ).
      CLEAR ls_return.
      READ TABLE lt_retmir INTO ls_return WITH KEY msgty = 'E'.
      IF sy-subrc <> 0.
        READ TABLE lt_retmir INTO ls_return WITH KEY msgty = 'A'.
      ENDIF.
      IF sy-subrc = 0.
        lv_error = abap_true.
        IF ls_return-msgid IS NOT INITIAL AND ls_return-msgno IS NOT INITIAL.
          MESSAGE ID ls_return-msgid TYPE ls_return-msgty
                  NUMBER ls_return-msgno
                  WITH ls_return-msgv1 ls_return-msgv2
                       ls_return-msgv3 ls_return-msgv4
                  INTO lv_msg.
        ELSE.
          lv_msg = 'Error devuelto por ME_INFORECORD_MAINTAIN (RETURN)'.
        ENDIF.
      ENDIF.
    ENDIF.

    " ---------- COMMIT / ROLLBACK y mensaje de resultado ----------
    IF lv_error = abap_true.
      ROLLBACK WORK.                    " deshace la LUW de esta fila
      <fs>-msg = |ERROR: { lv_msg }|.
      cv_err = cv_err + 1.
    ELSE.
      COMMIT WORK AND WAIT.             " graba la LUW de esta fila
      <fs>-msg = 'OK'.
      cv_ok = cv_ok + 1.
    ENDIF.

    " Datos del mensaje del FM para el log
    IF lv_error = abap_true.
      <fs>-msgid = ls_return-msgid.
      <fs>-msgno = ls_return-msgno.
      <fs>-msgty = ls_return-msgty.
    ENDIF.

    " ---------- Registro de log (ZPIR_PRICELOG + BAL) ----------
    " En modo test no se llega aquí (CONTINUE anterior), por lo que la
    " Z-tabla solo se escribe en modo producción.
    CLEAR ls_log.
    ls_log-logid     = cl_system_uuid=>create_uuid_c32_static( ).
    "  ^ [7.40 SP08+] cl_system_uuid. Si no está disponible en la versión
    "    instalada, sustituir por un contador secuencial (p. ej. lv_seq).
    ls_log-uname     = sy-uname.
    ls_log-datum     = sy-datum.
    ls_log-uzeit     = sy-uzeit.
    ls_log-testflag  = p_test.
    ls_log-matnr     = <fs>-matnr.
    ls_log-lifnr     = <fs>-lifnr.
    ls_log-ekorg     = <fs>-ekorg.
    ls_log-werks     = <fs>-werks.
    ls_log-infnr     = <fs>-infnr.
    ls_log-kschl     = <fs>-kschl.
    ls_log-netpr_old = <fs>-netpr_old.   " EINE-NETPR previo (rellenado al validar)
    ls_log-kbetr_new = <fs>-kbetr.
    ls_log-konwa     = <fs>-konwa.
    ls_log-peinh     = <fs>-peinh.
    ls_log-kmein     = <fs>-kmein.
    ls_log-datab     = <fs>-datab.
    ls_log-datbi     = <fs>-datbi.
    ls_log-msgty     = COND #( WHEN lv_error = abap_true
                                 AND ls_return-msgty IS NOT INITIAL
                               THEN ls_return-msgty
                               WHEN lv_error = abap_true THEN 'E'
                               ELSE 'S' ).
    ls_log-msgid     = ls_return-msgid.
    ls_log-msgno     = ls_return-msgno.
    ls_log-msgv1     = ls_return-msgv1.
    ls_log-msgv2     = ls_return-msgv2.
    ls_log-msgv3     = ls_return-msgv3.
    ls_log-msgv4     = ls_return-msgv4.
    ls_log-tcode     = 'ME12'.
    APPEND ls_log TO lt_logbuf.

    " Flush de la Z-tabla cada p_pkg filas (modo producción)
    IF lines( lt_logbuf ) >= p_pkg.
      PERFORM persist_log.
    ENDIF.
  ENDLOOP.

  " Flush final de la Z-tabla
  PERFORM persist_log.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM PERSIST_LOG: MODIFY de ZPIR_PRICELOG + COMMIT WORK
*---------------------------------------------------------------------*
FORM persist_log.
  " Z-tabla sugerida ZPIR_PRICELOG (crear en SE11 con estos campos):
  "   MANDT     CLNT        (cliente)
  "   LOGID     CHAR32      GUID (cl_system_uuid=>create_uuid_c32_static)
  "   UNAME     SYUNAME     Usuario que ejecutó
  "   DATUM     SYDATUM     Fecha
  "   UZEIT     SYUZEIT     Hora
  "   TESTFLAG  CHAR1       'X' = corrida de prueba
  "   MATNR     MATNR       Material
  "   LIFNR     LIFNR       Proveedor
  "   EKORG     EKORG       Org. de compras
  "   WERKS     WERKS_D     Planta
  "   INFNR     INFNR       Info record
  "   KSCHL     KSCHL       Tipo de condición (PB00/PB01)
  "   NETPR_OLD IPREI       Precio neto informativo previo (EINE-NETPR)
  "   KBETR_NEW KBETR       Nuevo importe de condición
  "   KONWA     WAERS       Moneda
  "   PEINH     PEINH       Unidad de precio
  "   KMEIN     MEINS       Unidad de medida
  "   DATAB     DATAB       Válido desde
  "   DATBI     DATBI       Válido hasta
  "   MSGTY     MSGTY       Tipo de mensaje
  "   MSGID     MSGID       Clase de mensaje
  "   MSGNO     MSGNO       Nº de mensaje
  "   MSGV1..4  MSGV1..4    Variables del mensaje
  "   TCODE     TCODE       Transacción (ME12)
  " TODO: confirmar que la Z-tabla existe en el sistema destino.
  MODIFY zpir_pricelog FROM TABLE @lt_logbuf.
  CLEAR lt_logbuf.
  COMMIT WORK AND WAIT.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM SAVE_LOG: Application Log (BAL) con el resultado por fila (B2)
*---------------------------------------------------------------------*
*  API BAL de S/4 (paquete SBL): cabecera con cl_bali_header_setter,
*  items como if_bali_item_setter. Mensajes: cl_bali_message_setter
*  (sin msgty ni msgv1..: solo id/number/variable_1..4). Texto libre:
*  cl_bali_free_text_setter. Guardado: save_log( log = lo_log ).
*---------------------------------------------------------------------*
FORM save_log.
  DATA lo_log  TYPE REF TO cl_bali_log.
  DATA lo_item TYPE REF TO if_bali_item_setter.
  DATA lv_text TYPE string.

  " TODO: crear el objeto de log 'ZPIR' / subobjeto 'PRICELOG' en SLG0.
  lo_log = cl_bali_log=>create_with_header(
             header = cl_bali_header_setter=>create(
                        object    = 'ZPIR'
                        subobject = 'PRICELOG' ) ).

  LOOP AT gt_input ASSIGNING FIELD-SYMBOL(<fs>) WHERE msg IS NOT INITIAL.
    lv_text = |{ <fs>-matnr } / { <fs>-lifnr } / { <fs>-ekorg } / { <fs>-werks } / INFNR { <fs>-infnr }: { <fs>-msg }|.

    IF <fs>-msgid IS NOT INITIAL AND <fs>-msgno IS NOT INITIAL.
      " Mensaje original devuelto por el FM: se guarda clase/nº reales
      " (SLG1 lo formatea con los parámetros del mensaje)
      lo_item = cl_bali_message_setter=>create(
                  severity   = COND #( WHEN <fs>-msgty = 'E' OR <fs>-msgty = 'A'
                                       THEN if_bali_constants=>c_severity_error
                                       ELSE if_bali_constants=>c_severity_warning )
                  id         = <fs>-msgid
                  number     = <fs>-msgno
                  variable_1 = <fs>-msgv1
                  variable_2 = <fs>-msgv2
                  variable_3 = <fs>-msgv3
                  variable_4 = <fs>-msgv4 ).
    ELSE.
      " Validaciones previas y filas OK: mensaje de texto libre
      lo_item = cl_bali_free_text_setter=>create(
                  severity = COND #( WHEN <fs>-msg CS 'ERROR'
                                     THEN if_bali_constants=>c_severity_warning
                                     WHEN <fs>-msg CS 'TEST'
                                     THEN if_bali_constants=>c_severity_information
                                     ELSE if_bali_constants=>c_severity_success )
                  text     = lv_text ).
    ENDIF.
    lo_log->add_item( lo_item ).
  ENDLOOP.

  " Persistir el log (SLG1 > objeto ZPIR).
  " save_log( log = lo_log ): NO devuelve handle en la API actual.
  TRY.
      cl_bali_log_db=>get_instance( )->save_log( log = lo_log ).
      MESSAGE |Application log guardado (SLG1, objeto ZPIR). OK: { lv_ok }, ERROR: { lv_err }, SKIP: { lv_skip }| TYPE 'S'.
    CATCH cx_bali_runtime.
      MESSAGE |Procesados -> OK: { lv_ok }, ERROR: { lv_err }, SKIP: { lv_skip }| TYPE 'S'.
  ENDTRY.
ENDFORM.

*---------------------------------------------------------------------*
*  FORM SHOW_RESULTS: ALV simple de las filas procesadas
*---------------------------------------------------------------------*
FORM show_results.
  DATA lo_alv TYPE REF TO cl_salv_table.

  IF p_alv = abap_false.
    " Sin ALV: lista clásica de resumen
    WRITE: / 'Resumen:', 20 'OK =', lv_ok, ' ERROR =', lv_err, ' SKIP =', lv_skip.
    LOOP AT gt_input ASSIGNING FIELD-SYMBOL(<fs>).
      WRITE: / <fs>-matnr, <fs>-lifnr, <fs>-infnr, <fs>-msg.
    ENDLOOP.
    RETURN.
  ENDIF.

  TRY.
      cl_salv_table=>factory(
        IMPORTING r_salv_table = lo_alv
        CHANGING  t_table      = gt_input ).
      lo_alv->display( ).
    CATCH cx_salv_msg.
      MESSAGE 'No se pudo mostrar el ALV de resultados.' TYPE 'I'.
  ENDTRY.
ENDFORM.

*---------------------------------------------------------------------*
*  ALTERNATIVA 1: BAPI_INFORECORD_CHANGE (comentada - NO activa) (B1/B4)
*---------------------------------------------------------------------*
*  ⚠ NO está confirmado como BAPI liberado (research/02 §§39-43):
*  verificar en SE37 del sistema destino si existe y si su firma
*  soporta condiciones antes de considerarlo como opción.
*
*  Estructuras de las tablas de condiciones (componentes reales):
*    MEIRPRCGCONDREC / MEIRPRCGCONDRECX
*  (p. ej. PURCHASINGINFORECORD, CONDITIONRECORD,
*   CONDITIONVALIDITYSTARTDATE, CONDITIONVALIDITYENDDATE,
*   CONDITIONRATEVALUE, CONDITIONRATEUNIT, CONDITIONUNIT,
*   CONDITIONCURRENCY; la X-estructura con 'X' por campo).
*  TODO: verificar en SE37 la lista exacta de componentes de
*  MEIRPRCGCONDREC/MEIRPRCGCONDRECX en el sistema destino.
*
*  CALL FUNCTION 'BAPI_INFORECORD_CHANGE'
*    EXPORTING
*      inforecordchange   = ls_inforecordchange
*      inforecordchangex  = ls_inforecordchangex
*    IMPORTING
*      inforecordnumber   = lv_inforecordnumber    " <- con IMPORTING
*    TABLES
*      priceconditions    = lt_priceconditions
*      priceconditionsx   = lt_priceconditionsx
*      return             = lt_return.
*
*  Nota (B4): en la estructura X se usa 'X' como indicador de cambio,
*  pero la estructura clave del CALL es INFORECORDX (no "inforecord"):
*    ls_inforecordchange-inforecord  = <fs>-infnr.   " valor
*    ls_inforecordchangex-inforecord = 'X'.          " indicador de cambio
*  Y COMMIT/ROLLBACK con BAPI_TRANSACTION_COMMIT/ROLLBACK.
*  Si el BAPI no soporta condiciones, usar ME_INFORECORD_MAINTAIN
*  (método principal de este reporte) o la alternativa BDC sobre ME12.

*---------------------------------------------------------------------*
*  ALTERNATIVA 2: BDC SOBRE ME12 (comentada - NO activa)
*---------------------------------------------------------------------*
*  ¿CUÁNDO USARLA?
*  - Cuando ME_INFORECORD_MAINTAIN no esté disponible (KBA 2787315:
*    marcado OBSOLETO) y BAPI_INFORECORD_CHANGE no aplique.
*  - Cuando el cambio incluya ESCALAS de cantidad (KONM) o múltiples
*    períodos de validez, donde el FM es limitado.
*  - Ventaja: usa el 100% de la lógica estándar de ME12 (validez,
*    escalas, doc. de cambio, mensajes).
*  - Riesgo: frágil a cambios de pantalla / versión; difícil depurar.
*
*  PASOS:
*  1. Grabar el recording con SHDB sobre ME12 (pantalla de selección
*     por MATNR/LIFNR/EKORG/WERKS/INFNR -> pestaña Condiciones ->
*     condición PB00/PB01 -> Guardar).
*  2. Llenar la tabla interna bdcdata con los dynpros grabados.
*  3. Ejecutar CALL TRANSACTION por fila.
*
*  DATOS DE EJEMPLO (ajustar al recording exacto del sistema):
*
*  DATA lt_bdc TYPE TABLE OF bdcdata.
*  DATA lt_msg TYPE TABLE OF bdcmsgcoll.
*  DATA ls_bdc TYPE bdcdata.
*
*  " --- dynpro 100 (selección ME12) ---
*  ls_bdc-program  = 'SAPMM06I'.
*  ls_bdc-dynpro   = '0100'.
*  ls_bdc-dynbegin = 'X'.
*  APPEND ls_bdc TO lt_bdc.
*  CLEAR ls_bdc.
*  ls_bdc-fnam = 'RM06I-INFNR'.
*  ls_bdc-fval = <fs>-infnr.
*  APPEND ls_bdc TO lt_bdc.
*
*  " --- dynpro 200 (datos del info record -> botón Condiciones) ---
*  ls_bdc-program  = 'SAPMM06I'.
*  ls_bdc-dynpro   = '0201'.
*  ls_bdc-dynbegin = 'X'.
*  APPEND ls_bdc TO lt_bdc.
*  CLEAR ls_bdc.
*  ls_bdc-fnam = 'BDC_OKCODE'.
*  ls_bdc-fval = '=VW1'.        " entrar a condiciones
*  APPEND ls_bdc TO lt_bdc.
*
*  " --- dynpro condiciones (SAPLV14A / 0102) ---
*  ls_bdc-program  = 'SAPLV14A'.
*  ls_bdc-dynpro   = '0102'.
*  ls_bdc-dynbegin = 'X'.
*  APPEND ls_bdc TO lt_bdc.
*  CLEAR ls_bdc.
*  ls_bdc-fnam = 'KONP-KBETR'.      " importe (formato 11,2 sin separador)
*  ls_bdc-fval = '000000012500'.
*  APPEND ls_bdc TO lt_bdc.
*  ls_bdc-fnam = 'KONP-KPEIN'.
*  ls_bdc-fval = '1'.
*  APPEND ls_bdc TO lt_bdc.
*  " KONP-KONWA, KONP-KMEIN, fechas DATAB/DATBI, etc. según el recording
*
*  " --- guardar ---
*  ls_bdc-fnam = 'BDC_OKCODE'.
*  ls_bdc-fval = '=SICH'.
*  APPEND ls_bdc TO lt_bdc.
*
*  " --- ejecución (por fila; MODE 'N' para background) ---
*  CALL TRANSACTION 'ME12' USING lt_bdc
*      MODE   'A'                    " A = mostrar errores, N = sin pantallas
*      UPDATE 'S'                    " S = síncrono (para capturar mensajes)
*      MESSAGES INTO lt_msg.
*
*  " revisar lt_msg (Bdcmsgcoll: MSGTYP 'E' => error) y hacer
*  " ROLLBACK/COMMIT según resultado; el log se puede completar igual.
*---------------------------------------------------------------------*
