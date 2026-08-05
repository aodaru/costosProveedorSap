Option Explicit

'=============================================================================
' ME12 Price Change Script - SAP GUI Scripting
' 
' Descripcion: Actualiza masivamente el precio neto (condicion PB00) en 
'              registros de informacion de compras usando ME12
'
' IDs basados en recording real del usuario (ME12)
' Requiere: SAP GUI Scripting habilitado (RZ11: sapgui/user_scripting = TRUE)
'
' ADVERTENCIA: 
'   - Usar solo en entornos controlados (Desarrollo/Quality)
'   - Hacer backup de los datos antes de ejecutar
'   - Verificar resultados con ME13 despues de cada ejecucion
'   - Este script modifica datos de produccion - usar bajo tu responsabilidad
'=============================================================================

' --- CONFIGURACION ---
Private Const SHEET_NAME As String = "Datos"
Private Const SAP_CONNECTION As String = "SAP"  ' Nombre de la conexion en SAP Logon

' Fila de la tabla de condiciones para el precio
' IMPORTANTE: El indice [CONDITION_ROW-1, 0] depende del recording.
' En el recording del usuario el precio esta en [2,0] (tercera fila, columna 0).
' Si tu SAP muestra la condicion en otra fila, ajustar este valor.
Private Const CONDITION_ROW As Long = 2  ' Indice 0-based: [2,0] = fila 3 de la tabla

' Indices de columna en Excel (1-based, columna A = 1)
' Los info records son a nivel de organizacion de compras (EKORG), sin planta
Private Const COL_MATERIAL As Long = 1      ' A: Material
Private Const COL_PROVEEDOR As Long = 2    ' B: Proveedor
Private Const COL_ORG_COMPRAS As Long = 3  ' C: Org Compras
Private Const COL_TIPO_INFO As Long = 4    ' D: Tipo Info Record (default: 0)
Private Const COL_TIPO_COND As Long = 5    ' E: Tipo Condicion (default: PB00)
Private Const COL_NUEVO_PRECIO As Long = 6 ' F: Nuevo Precio
Private Const COL_MONEDA As Long = 7       ' G: Moneda (default: MXN)
Private Const COL_UNIDAD_PRECIO As Long = 8 ' H: Unidad Precio (default: 1)
Private Const COL_UNIDAD_MEDIDA As Long = 9 ' I: Unidad Medida
Private Const COL_VALIDEZ_DESDE As Long = 10 ' J: Valido Desde
Private Const COL_VALIDEZ_HASTA As Long = 11 ' K: Valido Hasta
Private Const COL_RESULTADO As Long = 12   ' L: Resultado (output)
Private Const COL_LOG As Long = 13         ' M: Log detallado (output)

' Configuracion de delays (milisegundos)
Private Const DELAY_AFTER_ENTER As Long = 500
Private Const DELAY_AFTER_CLICK As Long = 300
Private Const DELAY_BETWEEN_ROWS As Long = 1000

' --- VARIABLES GLOBALES ---
Private sapGuiApp As Object
Private sapSession As Object
Private logFile As String

'=============================================================================
' MAIN PROCEDURE
'=============================================================================
Public Sub ActualizarPrecioPB00()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim i As Long
    Dim totalRegistros As Long
    Dim registrosOK As Long
    Dim registrosError As Long
    
    ' Inicializar
    logFile = Environ("TEMP") & "\ME12_Log_" & Format(Now, "yyyymmdd_hhmmss") & ".txt"
    
    ' Verificar SAP GUI
    If Not ConectarSAP() Then
        MsgBox "No se pudo conectar a SAP GUI. Verificar que:" & vbCrLf & _
               "1. SAP GUI esta abierto" & vbCrLf & _
               "2. Hay una sesion activa" & vbCrLf & _
               "3. SAPGUI/user_scripting = TRUE en RZ11", _
               vbCritical, "Error de Conexion"
        Exit Sub
    End If
    
    ' Verificar hoja de datos
    If Not VerificarHojaDatos(ws, lastRow) Then
        Exit Sub
    End If
    
    totalRegistros = lastRow - 1  ' Restar fila de cabecera
    
    ' Confirmacion
    If MsgBox("Se procesaran " & totalRegistros & " registros." & vbCrLf & vbCrLf & _
              "Desea continuar?", vbYesNo + vbQuestion, "Confirmar Ejecucion") = vbNo Then
        Exit Sub
    End If
    
    ' Procesar cada registro
    registrosOK = 0
    registrosError = 0
    
    Application.StatusBar = "Procesando registro 1 de " & totalRegistros & "..."
    
    For i = 2 To lastRow  ' Desde fila 2 (fila 1 es cabecera)
        Application.StatusBar = "Procesando registro " & (i - 1) & " de " & totalRegistros & "..."
        
        Dim resultado As String
        resultado = ProcesarRegistro(ws, i)
        
        If Left(resultado, 2) = "OK" Then
            registrosOK = registrosOK + 1
        Else
            registrosError = registrosError + 1
        End If
        
        DoEvents  ' Permitir que Excel responda
        
        ' Delay entre registros
        Sleep DELAY_BETWEEN_ROWS
    Next i
    
    ' Resumen final
    Application.StatusBar = False
    
    Dim msg As String
    msg = "Proceso completado." & vbCrLf & vbCrLf & _
          "Total: " & totalRegistros & vbCrLf & _
          "Exitosos: " & registrosOK & vbCrLf & _
          "Con errores: " & registrosError & vbCrLf & vbCrLf & _
          "Log guardado en: " & logFile
    
    MsgBox msg, IIf(registrosError = 0, vbInformation, vbExclamation), "Resultado"
    
    ' Abrir log si hubo errores
    If registrosError > 0 Then
        Shell "notepad.exe """ & logFile & """", vbNormalFocus
    End If
End Sub

'=============================================================================
' CONEXION A SAP GUI
'=============================================================================
Private Function ConectarSAP() As Boolean
    On Error GoTo ErrorHandler
    
    Set sapGuiApp = GetObject("SAPGUI")
    Set sapGuiApp = sapGuiApp.GetApplication
    
    If sapGuiApp.Connections.Count = 0 Then
        ConectarSAP = False
        Exit Function
    End If
    
    Set sapSession = sapGuiApp.Connections(0).Children(0)
    
    ConectarSAP = True
    Exit Function
    
ErrorHandler:
    ConectarSAP = False
End Function

'=============================================================================
' VERIFICACION DE HOJA DE DATOS
'=============================================================================
Private Function VerificarHojaDatos(ByRef ws As Worksheet, ByRef lastRow As Long) As Boolean
    On Error GoTo ErrorHandler
    
    Set ws = ThisWorkbook.Sheets(SHEET_NAME)
    
    ' Verificar que hay datos
    lastRow = ws.Cells(ws.Rows.Count, COL_MATERIAL).End(xlUp).Row
    
    If lastRow < 2 Then
        MsgBox "No se encontraron datos en la hoja '" & SHEET_NAME & "'", _
               vbExclamation, "Sin Datos"
        VerificarHojaDatos = False
        Exit Function
    End If
    
    ' Verificar cabeceras
    If ws.Cells(1, COL_MATERIAL) <> "Material" Or _
       ws.Cells(1, COL_NUEVO_PRECIO) <> "Nuevo Precio" Then
        MsgBox "Formato de hoja incorrecto. Verificar cabeceras.", _
               vbExclamation, "Formato Invalido"
        VerificarHojaDatos = False
        Exit Function
    End If
    
    VerificarHojaDatos = True
    Exit Function
    
ErrorHandler:
    MsgBox "Error accediendo a la hoja '" & SHEET_NAME & "': " & Err.Description, _
           vbCritical, "Error"
    VerificarHojaDatos = False
End Function

'=============================================================================
' PROCESAMIENTO DE REGISTRO INDIVIDUAL
' IDs basados en recording real: EINA-LIFNR, EINA-MATNR, EINE-EKORG,
' tbar[1]/btn[8], wnd[1]/tbar[0]/btn[7], tbl.../txtKONP-KBETR[row,0],
' tbar[0]/btn[11]
'=============================================================================
Private Function ProcesarRegistro(ws As Worksheet, row As Long) As String
    Dim material As String
    Dim proveedor As String
    Dim orgCompras As String
    Dim tipoInfo As String
    Dim tipoCond As String
    Dim nuevoPrecio As String
    Dim moneda As String
    Dim unidadPrecio As String
    Dim unidadMedida As String
    Dim validezDesde As String
    Dim validezHasta As String
    
    On Error GoTo ErrorHandler
    
    ' Leer datos de la fila
    material = Trim(CStr(ws.Cells(row, COL_MATERIAL).Value))
    proveedor = Trim(CStr(ws.Cells(row, COL_PROVEEDOR).Value))
    orgCompras = Trim(CStr(ws.Cells(row, COL_ORG_COMPRAS).Value))
    tipoInfo = Trim(CStr(ws.Cells(row, COL_TIPO_INFO).Value))
    tipoCond = Trim(CStr(ws.Cells(row, COL_TIPO_COND).Value))
    nuevoPrecio = Trim(CStr(ws.Cells(row, COL_NUEVO_PRECIO).Value))
    moneda = Trim(CStr(ws.Cells(row, COL_MONEDA).Value))
    unidadPrecio = Trim(CStr(ws.Cells(row, COL_UNIDAD_PRECIO).Value))
    unidadMedida = Trim(CStr(ws.Cells(row, COL_UNIDAD_MEDIDA).Value))
    validezDesde = Trim(CStr(ws.Cells(row, COL_VALIDEZ_DESDE).Value))
    validezHasta = Trim(CStr(ws.Cells(row, COL_VALIDEZ_HASTA).Value))
    
    ' Validaciones basicas
    If material = "" Or proveedor = "" Or orgCompras = "" Then
        ProcesarRegistro = "ERROR: Faltan datos obligatorios (Material/Proveedor/OrgCompras)"
        GoTo WriteResult
    End If
    
    If nuevoPrecio = "" Then
        ProcesarRegistro = "ERROR: Falta precio"
        GoTo WriteResult
    End If
    
    ' Valores por defecto
    If tipoInfo = "" Then tipoInfo = "0"
    If tipoCond = "" Then tipoCond = "PB00"
    If moneda = "" Then moneda = "MXN"
    If unidadPrecio = "" Then unidadPrecio = "1"
    If validezDesde = "" Then validezDesde = Format(Now, "yyyymmdd")
    If validezHasta = "" Then validezHasta = "99991231"
    
    ' ===== PASO 1: Navegar a ME12 =====
    sapSession.FindById("wnd[0]/tbar[0]/okcd").Text = "/nME12"
    sapSession.FindById("wnd[0]").SendVKey 0
    Sleep DELAY_AFTER_ENTER
    
    ' ===== PASO 2: Pantalla inicial - ingresar datos del registro =====
    ' ID real del recording: ctxtEINA-LIFNR (Proveedor)
    sapSession.FindById("wnd[0]/usr/ctxtEINA-LIFNR").Text = proveedor
    
    ' ID real del recording: ctxtEINA-MATNR (Material)
    sapSession.FindById("wnd[0]/usr/ctxtEINA-MATNR").Text = material
    
    ' ID real del recording: ctxtEINE-EKORG (Org Compras) + setFocus + caretPosition
    sapSession.FindById("wnd[0]/usr/ctxtEINE-EKORG").SetFocus
    sapSession.FindById("wnd[0]/usr/ctxtEINE-EKORG").CaretPosition = Len(orgCompras)
    sapSession.FindById("wnd[0]/usr/ctxtEINE-EKORG").Text = orgCompras
    
    ' Enter para validar datos
    sapSession.FindById("wnd[0]").SendVKey 0
    Sleep DELAY_AFTER_ENTER
    
    ' ===== PASO 3: Boton Condiciones =====
    ' ID real del recording: tbar[1]/btn[8]
    sapSession.FindById("wnd[0]/tbar[1]/btn[8]").Press
    Sleep DELAY_AFTER_CLICK
    
    ' ===== PASO 4: Popup de confirmacion (puede no aparecer) =====
    ' ID real del recording: wnd[1]/tbar[0]/btn[7]
    ' Este popup aparece cuando hay condiciones existentes o requiere confirmacion.
    ' Se envuelve en On Error Resume Next porque puede no aparecer siempre.
    On Error Resume Next
    sapSession.FindById("wnd[1]/tbar[0]/btn[7]").Press
    Sleep DELAY_AFTER_CLICK
    On Error GoTo ErrorHandler
    
    ' ===== PASO 5: Modificar precio en tabla de condiciones =====
    ' ID real del recording: tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[CONDITION_ROW,0]
    ' El indice [CONDITION_ROW,0] corresponde a la fila de la condicion en la tabla.
    ' CONDITION_ROW = 2 significa la tercera fila visual ([2,0] en indices 0-based).
    ' Si tu SAP muestra la condicion en otra fila, ajustar la constante CONDITION_ROW.
    sapSession.FindById("wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[" & CONDITION_ROW & ",0]").Text = nuevoPrecio
    Sleep DELAY_AFTER_CLICK
    
    ' ===== PASO 6: Guardar (F11) =====
    ' ID real del recording: tbar[0]/btn[11]
    sapSession.FindById("wnd[0]/tbar[0]/btn[11]").Press
    Sleep DELAY_AFTER_ENTER
    
    ' ===== PASO 7: Verificar mensaje de status bar =====
    Dim statusBar As String
    statusBar = ""
    On Error Resume Next
    statusBar = sapSession.FindById("wnd[0]/sbar").Text
    On Error GoTo ErrorHandler
    
    ' Detectar errores en el mensaje de SAP
    If InStr(1, statusBar, "error", vbTextCompare) > 0 Or _
       InStr(1, statusBar, "Error", vbTextCompare) > 0 Or _
       InStr(1, statusBar, "no se pudo", vbTextCompare) > 0 Then
        ProcesarRegistro = "ERROR SAP: " & statusBar
        GoTo WriteResult
    End If
    
    ProcesarRegistro = "OK - " & Format(Now, "hh:mm:ss")
    
WriteResult:
    ' Escribir resultado en Excel
    ws.Cells(row, COL_RESULTADO).Value = Left(ProcesarRegistro, 50)
    ws.Cells(row, COL_LOG).Value = ProcesarRegistro
    
    EscribirLog material & "|" & proveedor & "|" & orgCompras & "|" & ProcesarRegistro
    
    Exit Function
    
ErrorHandler:
    Dim errMsg As String
    errMsg = Err.Description
    
    ' Intentar capturar mensaje de SAP
    On Error Resume Next
    If Not sapSession Is Nothing Then
        errMsg = errMsg & " | SAP: " & sapSession.FindById("wnd[0]/sbar").Text
    End If
    On Error GoTo 0
    
    ProcesarRegistro = "ERROR VBA: " & errMsg
    ws.Cells(row, COL_RESULTADO).Value = Left(ProcesarRegistro, 50)
    ws.Cells(row, COL_LOG).Value = ProcesarRegistro
    
    EscribirLog material & "|" & proveedor & "|" & orgCompras & "|" & ProcesarRegistro
End Function

'=============================================================================
' LOGGING
'=============================================================================
Private Sub EscribirLog(mensaje As String)
    Dim f As Integer
    f = FreeFile
    
    On Error Resume Next
    Open logFile For Append As #f
    Print #f, Format(Now, "yyyy-mm-dd hh:mm:ss") & " | " & mensaje
    Close #f
    On Error GoTo 0
End Sub

'=============================================================================
' DECLARACION DE Sleep (pausa en milisegundos)
'=============================================================================
Private Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As LongPtr)

'=============================================================================
' INSTRUCCIONES DE USO
'=============================================================================
'
' 1. PRERREQUISITOS:
'    - SAP GUI Scripting habilitado (RZ11: sapgui/user_scripting = TRUE)
'    - SAP GUI abierto con sesion activa
'    - Hoja "Datos" en Excel con formato correcto
'
' 2. FORMATO DE LA HOJA:
'    Columna A: Material             (obligatorio)
'    Columna B: Proveedor            (obligatorio)
'    Columna C: Org Compras          (obligatorio)
'    Columna D: Tipo Info Record     (default: 0)
'    Columna E: Tipo Condicion       (default: PB00)
'    Columna F: Nuevo Precio         (obligatorio, formato: 8.90)
'    Columna G: Moneda               (default: MXN)
'    Columna H: Unidad Precio        (default: 1)
'    Columna I: Unidad Medida
'    Columna J: Valido Desde         (formato: YYYYMMDD)
'    Columna K: Valido Hasta         (formato: YYYYMMDD)
'    Columna L: Resultado            (output - se llena automaticamente)
'    Columna M: Log                  (output - se llena automaticamente)
'
' 3. IDs DEL RECORDING (ME12):
'    - ctxtEINA-LIFNR        -> Proveedor
'    - ctxtEINA-MATNR        -> Material
'    - ctxtEINE-EKORG        -> Org Compras
'    - tbar[1]/btn[8]        -> Boton Condiciones
'    - wnd[1]/tbar[0]/btn[7] -> Popup confirmacion (puede no aparecer)
'    - tbl.../txtKONP-KBETR[row,0] -> Precio en tabla de condiciones
'    - tbar[0]/btn[11]       -> Guardar (F11)
'
' 4. CONFIGURACION:
'    - CONDITION_ROW = 2 (indice 0-based, equivale a [2,0])
'    - Ajustar si la condicion aparece en otra fila de la tabla
'    - Delays: ENTER=500ms, CLICK=300ms, BETWEEN_ROWS=1000ms
'
' 5. IMPORTANTES:
'    - Probar con UN registro antes de ejecutar masivamente
'    - Hacer backup de los datos
'    - Verificar resultados con ME13 despues
'    - NO tocar SAP GUI mientras corre el script
'
' 6. LIMITACIONES:
'    - Velocidad: ~1-2 segundos por registro
'    - Fragil ante cambios de pantalla SAP
'    - No oficialmente soportado para produccion
'    - Requiere que la condicion PB00 este configurada en M/06
'    - No usa planta (info records son a nivel EKORG)
'
'=============================================================================
