# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import time
from datetime import datetime
from validators import validate_excel, print_validation_errors


# Delays configurables (segundos)
DELAY_AFTER_ENTER = 0.5
DELAY_AFTER_CLICK = 0.3
DELAY_BETWEEN_ROWS = 1.0

# Indice 0-based de la fila de condicion en la tabla de SAP
CONDITION_ROW = 2

# Fecha por defecto de SAP (31.12.9999)
SAP_DEFAULT_DATE = "31.12.9999"


def parse_date_to_yyyymmdd(value: str) -> str:
    """Convierte dd.mm.yyyy o YYYYMMDD a YYYYMMDD. Retorna string vacío si no puede."""
    value = value.strip()
    if not value:
        return ""
    # Formato dd.mm.yyyy
    if "." in value:
        parts = value.split(".")
        if len(parts) == 3 and len(parts[0]) == 2 and len(parts[1]) == 2 and len(parts[2]) == 4:
            if all(p.isdigit() for p in parts):
                return f"{parts[2]}{parts[1]}{parts[0]}"  # YYYYMMDD
    # Formato YYYYMMDD
    if value.isdigit() and len(value) == 8:
        return value
    return ""


def format_date_for_sap(yyyymmdd: str) -> str:
    """Convierte YYYYMMDD a dd.mm.yyyy para SAP. Ejemplo: '20260805' → '05.08.2026'"""
    if not yyyymmdd or len(yyyymmdd) != 8:
        return yyyymmdd
    return f"{yyyymmdd[6:8]}.{yyyymmdd[4:6]}.{yyyymmdd[0:4]}"


def compute_validity_dates(valido_desde_raw: str, valido_hasta_raw: str) -> tuple:
    """
    Calcula las fechas de validez para SAP segun las reglas:
    - VALIDO_DESDE: siempre hoy o despues. Si es anterior a hoy -> usar hoy.
    - VALIDO_HASTA: si viene vacio o es anterior/igual a hoy -> usar 31.12.9999.
    
    Retorna: (desde_dd.mm.yyyy, hasta_dd.mm.yyyy)
    """
    today = datetime.now().strftime("%Y%m%d")
    
    # === VALIDO_DESDE ===
    desde_fmt = parse_date_to_yyyymmdd(valido_desde_raw)
    if not desde_fmt or desde_fmt < today:
        desde_final = today
    else:
        desde_final = desde_fmt
    
    # === VALIDO_HASTA ===
    hasta_fmt = parse_date_to_yyyymmdd(valido_hasta_raw)
    if not hasta_fmt or hasta_fmt <= today:
        hasta_final = SAP_DEFAULT_DATE  # "31.12.9999"
    else:
        hasta_final = format_date_for_sap(hasta_fmt)  # Convertir a dd.mm.yyyy
    
    # Convertir desde a dd.mm.yyyy
    desde_final = format_date_for_sap(desde_final)
    
    return (desde_final, hasta_final)


def wait_for_control(session, control_id, timeout=5.0, interval=0.2, log_func=None):
    """Reintenta findById hasta que el control exista o se agote el timeout."""
    start = time.time()
    attempts = 0
    while time.time() - start < timeout:
        try:
            ctrl = session.findById(control_id)
            if attempts > 0 and log_func:
                log_func(f"  Control '{control_id}' encontrado tras {attempts} intentos")
            return ctrl
        except Exception:
            attempts += 1
            time.sleep(interval)
    raise TimeoutError(
        f"Control '{control_id}' no encontrado tras {timeout}s ({attempts} intentos)"
    )


class SapMe12MassMod:
    """Logica de modificacion masiva para la transaccion ME12 (info records de compras)."""

    def __init__(self, session, log_func=print):
        self.session = session
        self.log = log_func

    def run_me12_massmod(self, file_path):
        self.log(f"{'='*50}")
        self.log("Iniciando Proceso ME12 - Actualizacion Masiva de Precio...")
        self.log(f"{'='*50}")

        data, errors = validate_excel(file_path, self.log)

        if errors:
            print_validation_errors(errors, self.log)

        if data.empty:
            self.log("No hay registros validos para procesar.")
            return

        self.session.findById("wnd[0]").maximize()

        total = len(data)
        ok_count = 0
        error_count = 0

        for index, row in data.iterrows():
            self.log(f"Procesando registro {index + 1} de {total}...")
            result = self._procesar_registro(row, index)

            if result.startswith("OK"):
                ok_count += 1
            else:
                error_count += 1

            time.sleep(DELAY_BETWEEN_ROWS)

        self.log(f"{'='*50}")
        self.log(f"Proceso completado.")
        self.log(f"  Total: {total}")
        self.log(f"  Exitosos: {ok_count}")
        self.log(f"  Con errores: {error_count}")
        self.log(f"{'='*50}")

    def _procesar_registro(self, row, index):
        material = str(row.get("MATERIAL", "")).strip()
        proveedor = str(row.get("PROVEEDOR", "")).strip()
        org_compras = str(row.get("ORG_COMPRAS", "")).strip()
        tipo_info = str(row.get("TIPO_INFO", "0")).strip()
        tipo_cond = str(row.get("TIPO_CONDICION", "PB00")).strip()
        nuevo_precio = str(row.get("NUEVO_PRECIO", "")).strip()
        moneda = str(row.get("MONEDA", "MXN")).strip()
        unidad_precio = str(row.get("UNIDAD_PRECIO", "1")).strip()
        unidad_medida = str(row.get("UNIDAD_MEDIDA", "")).strip()
        # Calcular fechas de validez según reglas
        valido_desde_raw = str(row.get("VALIDO_DESDE", "")).strip()
        valido_hasta_raw = str(row.get("VALIDO_HASTA", "")).strip()
        validez_desde, validez_hasta = compute_validity_dates(valido_desde_raw, valido_hasta_raw)

        try:
            # PASO 1: Navegar a ME12
            self.session.findById("wnd[0]/tbar[0]/okcd").Text = "/nME12"
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(DELAY_AFTER_ENTER)

            # PASO 2: Pantalla inicial - proveedor
            self.session.findById("wnd[0]/usr/ctxtEINA-LIFNR").Text = proveedor

            # PASO 3: Material
            self.session.findById("wnd[0]/usr/ctxtEINA-MATNR").Text = material

            # PASO 4: Org. compras (con setFocus/caretPosition como en el VBA)
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").SetFocus
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").CaretPosition = len(org_compras)
            self.session.findById("wnd[0]/usr/ctxtEINE-EKORG").Text = org_compras

            # PASO 5: Enter para validar
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(DELAY_AFTER_ENTER)

            # PASO 5b: Dar foco a la ventana antes de buscar botones
            try:
                self.session.findById("wnd[0]").SetFocus
            except Exception:
                pass
            time.sleep(0.3)

            # PASO 6: Redimensionar panel
            try:
                self.session.findById("wnd[0]").resizeWorkingPane(105, 25, False)
            except Exception:
                pass
            time.sleep(0.3)

            # PASO 6b: Confirmar/Refrescar antes de abrir condiciones
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(DELAY_AFTER_ENTER)

            # PASO 6c: Boton Condiciones
            # Usar F8 (SendVKey 8) en lugar de btn[8].Press porque el COM reference
            # al boton de toolbar no ejecuta la accion (problema conocido de SAP GUI Scripting)
            self.session.findById("wnd[0]").SendVKey(8)
            time.sleep(DELAY_AFTER_CLICK)

            # DEBUG: Diagnosticar toolbar y botones
            self.log(f"  [DEBUG] Diagnosticando toolbar tbar[1]:")
            try:
                tbar1 = self.session.findById("wnd[0]/tbar[1]")
                self.log(f"    tbar[1] encontrado: type={tbar1.Type}, children={tbar1.Children.Count}")
                for j in range(tbar1.Children.Count):
                    btn = tbar1.Children(j)
                    self.log(f"      btn[{j}]: type={btn.Type}, ID='{btn.Id}', enabled={btn.Enabled}, visible={btn.Visible}")
            except Exception as e:
                self.log(f"  [DEBUG] Error accediendo a tbar[1]: {e}")

            # DEBUG: Listar ventanas abiertas para diagnosticar popup
            self.log(f"  [DEBUG] Ventanas SAP abiertas:")
            try:
                for i in range(self.session.Children.Count):
                    wnd = self.session.Children(i)
                    self.log(f"    wnd[{i}]: type={wnd.Type}, text='{wnd.Text}', ID='{wnd.Id}'")
            except Exception as e:
                self.log(f"  [DEBUG] Error listando ventanas: {e}")

            # PASO 7: Manejar popup "Períodos de validez de condiciones"
            time.sleep(1.0)  # Dar tiempo a SAP para procesar F8

            # Detectar popup por texto (más confiable que solo verificar existencia)
            popup_detected = False
            popup_text = ""
            try:
                wnd1 = self.session.findById("wnd[1]")
                popup_text = wnd1.Text
                popup_detected = True
                self.log(f"  [DEBUG] Popup detectado: '{popup_text}'")
            except Exception:
                pass

            if popup_detected:
                if "Períodos de validez" in popup_text or "validez" in popup_text.lower():
                    # Es el popup de períodos — seleccionar período existente
                    self.log(f"  [INFO] Popup de períodos detectado — seleccionando período")
                    
                    # Diagnosticar tabla de períodos
                    try:
                        tbl = self.session.findById("wnd[1]/usr/tblSAPLV14ATCTRL_D0102")
                        self.log(f"  [DEBUG] Tabla períodos: rows={tbl.Rows.Count}, columns={tbl.Columns.Count}")
                        
                        # Listar filas disponibles (diagnóstico)
                        for r in range(min(tbl.Rows.Count, 5)):
                            row_text = ""
                            try:
                                # Leer celdas de la fila
                                for c in range(tbl.Columns.Count):
                                    cell = tbl.GetCell(r, c)
                                    row_text += f" [{c}]={cell.Text}"
                            except Exception:
                                pass
                            self.log(f"    Fila {r}:{row_text}")
                    except Exception as e:
                        self.log(f"  [DEBUG] Error diagnosticando tabla: {e}")
                    
                    # Crear nuevo período con F7 y luego llenar fechas
                    self.log(f"  [INFO] Creando nuevo período con F7")
                    
                    # Paso 1: Presionar F7 para crear nuevo período
                    try:
                        self.session.findById("wnd[1]").SendVKey(7)  # F7 = Nuevo período
                        time.sleep(1.0)  # Dar tiempo para que aparezcan los campos
                        self.log(f"  [INFO] F7 presionado — esperando campos de fecha")
                    except Exception as e:
                        self.log(f"  [WARN] Error presionando F7: {e}")
                    
                    # Paso 2: Diagnosticar TODAS las ventanas después de F7
                    self.log(f"  [DEBUG] Ventanas después de F7:")
                    try:
                        for i in range(self.session.Children.Count):
                            wnd = self.session.Children(i)
                            self.log(f"    wnd[{i}]: type={wnd.Type}, text='{wnd.Text}', ID='{wnd.Id}'")
                            # Listar hijos de cada ventana
                            try:
                                for c in range(wnd.Children.Count):
                                    child = wnd.Children(c)
                                    child_id = child.Id if hasattr(child, 'Id') else 'N/A'
                                    child_type = child.Type if hasattr(child, 'Type') else 'N/A'
                                    child_text = ""
                                    try:
                                        child_text = child.Text if hasattr(child, 'Text') else ''
                                    except:
                                        pass
                                    self.log(f"      [{c}] type={child_type}, ID='{child_id}', text='{child_text}'")
                            except Exception:
                                pass
                    except Exception as e:
                        self.log(f"    [DEBUG] Error listando ventanas: {e}")
                    
                    # Paso 3: Buscar campos de fecha en TODAS las ventanas (wnd[0], wnd[1], wnd[2])
                    desde_found = False
                    hasta_found = False
                    
                    # IDs posibles para campos de fecha
                    desde_ids = [
                        "wnd[0]/usr/ctxtRV13A-DATAB", "wnd[0]/usr/txtRV13A-DATAB",
                        "wnd[1]/usr/ctxtRV13A-DATAB", "wnd[1]/usr/txtRV13A-DATAB",
                        "wnd[2]/usr/ctxtRV13A-DATAB", "wnd[2]/usr/txtRV13A-DATAB",
                        "wnd[0]/usr/ctxtSVALU-LOW", "wnd[0]/usr/txtSVALU-LOW",
                        "wnd[1]/usr/ctxtSVALU-LOW", "wnd[1]/usr/txtSVALU-LOW",
                        "wnd[2]/usr/ctxtSVALU-LOW", "wnd[2]/usr/txtSVALU-LOW",
                    ]
                    
                    hasta_ids = [
                        "wnd[0]/usr/ctxtRV13A-DATBI", "wnd[0]/usr/txtRV13A-DATBI",
                        "wnd[1]/usr/ctxtRV13A-DATBI", "wnd[1]/usr/txtRV13A-DATBI",
                        "wnd[2]/usr/ctxtRV13A-DATBI", "wnd[2]/usr/txtRV13A-DATBI",
                        "wnd[0]/usr/ctxtSVALU-HIGH", "wnd[0]/usr/txtSVALU-HIGH",
                        "wnd[1]/usr/ctxtSVALU-HIGH", "wnd[1]/usr/txtSVALU-HIGH",
                        "wnd[2]/usr/ctxtSVALU-HIGH", "wnd[2]/usr/txtSVALU-HIGH",
                    ]
                    
                    for desde_id in desde_ids:
                        try:
                            field = self.session.findById(desde_id)
                            field.Text = validez_desde
                            self.log(f"    Campo desde = {validez_desde} (ID: {desde_id})")
                            desde_found = True
                            break
                        except Exception:
                            pass
                    
                    for hasta_id in hasta_ids:
                        try:
                            field = self.session.findById(hasta_id)
                            field.Text = validez_hasta
                            self.log(f"    Campo hasta = {validez_hasta} (ID: {hasta_id})")
                            hasta_found = True
                            break
                        except Exception:
                            pass
                    
                    if not desde_found:
                        self.log(f"  [WARN] No se encontró campo 'desde' en ninguna ventana")
                    if not hasta_found:
                        self.log(f"  [WARN] No se encontró campo 'hasta' en ninguna ventana")
                    
                    # Paso 4: Confirmar — intentar Enter en cada ventana
                    time.sleep(0.3)
                    for wnd_id in ["wnd[2]", "wnd[1]"]:
                        try:
                            self.session.findById(wnd_id).SendVKey(0)
                            time.sleep(DELAY_AFTER_CLICK)
                            self.log(f"  [INFO] Confirmado con Enter en {wnd_id}")
                            break
                        except Exception:
                            pass
                else:
                    # Otro tipo de popup — intentar confirmar con Enter
                    self.log(f"  [DEBUG] Popup desconocido: '{popup_text}', intentando Enter")
                    try:
                        self.session.findById("wnd[1]").SendVKey(0)
                        time.sleep(DELAY_AFTER_CLICK)
                    except Exception:
                        pass
            else:
                # No hay popup — verificar si la tabla de condiciones ya está en wnd[0]
                try:
                    wait_for_control(self.session, "wnd[0]/usr/tblSAPMV13ATCTRL_D0201", timeout=3.0, log_func=self.log)
                except Exception:
                    self.log("  [WARN] No se detectó popup ni tabla de condiciones")

            # PASO 8: Modificar precio en tabla de condiciones
            precio_id = f"wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[{CONDITION_ROW},0]"
            wait_for_control(self.session, precio_id, timeout=10.0, log_func=self.log).Text = nuevo_precio
            time.sleep(DELAY_AFTER_CLICK)

            # PASO 9: Guardar — usar SendVKey(11) en lugar de btn[11].Press
            # (mismo problema COM que btn[8])
            self.session.findById("wnd[0]").SendVKey(11)
            time.sleep(1.0)  # era DELAY_AFTER_ENTER (0.5s)

            # PASO 10: Verificar status bar
            status_bar = ""
            try:
                status_bar = self.session.findById("wnd[0]/sbar").Text
            except Exception:
                pass

            if "error" in status_bar.lower():
                self.log(f"Fila {index}: ERROR SAP: {status_bar}")
                return f"ERROR SAP: {status_bar}"

            self.log(f"Fila {index}: OK - {material}/{proveedor}")
            return "OK"

        except Exception as e:
            error_msg = str(e)
            # Intentar capturar mensaje de SAP
            try:
                sap_msg = self.session.findById("wnd[0]/sbar").Text
                if sap_msg:
                    error_msg += f" | SAP: {sap_msg}"
            except Exception:
                pass

            self.log(f"Fila {index}: ERROR: {error_msg}")
            return f"ERROR: {error_msg}"
