# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

"""Módulo SAP autocontenido para la Web UI ME12.

Reemplaza la dependencia de script/sap.py y script/me12_massmod.py.
Diseñado para ejecutarse en la VM Windows con SAP GUI.

win32com y pywintypes se importan DENTRO de métodos (no a nivel módulo)
para permitir importar este módulo en Linux sin error.
"""
import subprocess
import time
import os
from pathlib import Path


class SapClient:
    """Cliente SAP completo: conexión, login, ME12, cierre."""

    def __init__(self, system: str, mandt: str, username: str,
                 password: str, language: str):
        self.system = system
        self.mandt = mandt
        self.username = username
        self.password = password
        self.language = language

        self.session = None
        self.connection = None
        self.application = None

        # Delays configurables (segundos) — originals from me12_massmod.py
        self.delay_after_enter = 0.5
        self.delay_after_click = 0.3
        self.delay_between_rows = 1.0

        # Indice 0-based de la fila de condicion en la tabla de SAP
        self.condition_row = 2

        # Fecha por defecto de SAP (31.12.9999)
        self.sap_default_date = "31.12.9999"

    # ------------------------------------------------------------------ #
    #  Conexión y Login                                                    #
    # ------------------------------------------------------------------ #

    def _open_sap_logon(self):
        """Abre saplogon.exe."""
        path = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
        subprocess.Popen(path)

    def connect(self, log_func=print):
        """Abre SAP Logon y establece conexión.

        Retorna True si la conexión se estableció, False en caso contrario.
        """
        import win32com.client  # type: ignore
        import pywintypes

        self._open_sap_logon()
        time.sleep(3)

        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
        except pywintypes.com_error as e:
            log_func(f"{'=' * 50}")
            log_func(f"SAP GUI no encontrado: {e}")
            log_func("Asegúrese de que SAP GUI esté instalado y disponible.")
            log_func(f"{'=' * 50}")
            return False

        self.application = SapGuiAuto.GetScriptingEngine

        try:
            self.connection = self.application.OpenConnection(self.system, True)
        except Exception as e:
            log_func(f"{'=' * 50}")
            log_func(f"Error tratando de conectar con SAP: {e}")
            log_func("La red no está accesible o el sistema SAP no está disponible.")
            log_func(f"{'=' * 50}")
            return False

        time.sleep(3)
        self.session = self.connection.Children(0)
        self.session.findById("wnd[0]").maximize()
        return True

    def login(self, log_func=print):
        """Llena campos de login y envía.

        Retorna True si el login fue exitoso, False en caso contrario.
        """
        if not self.session:
            log_func("No hay sesión SAP para autenticar.")
            return False

        try:
            # CLIENTE
            self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = self.mandt
            # USUARIO
            self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = self.username
            # CONTRASEÑA
            self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = self.password
            # IDIOMA
            self.session.findById("wnd[0]/usr/txtRSYST-LANGU").text = self.language
            # ENTER
            self.session.findById("wnd[0]").sendVKey(0)
            time.sleep(2)

            # Manejar popup "Session already open" si aparece
            try:
                popup = self.session.findById("wnd[1]")
                if popup and "already open" in str(popup.Text):
                    popup.findById("tbar[0]/btn[0]").press()
            except Exception:
                pass  # No apareció el popup, todo OK

        except Exception as e:
            log_func(f"Error tratando de autenticar en SAP: {e}")
            return False

        return True

    # ------------------------------------------------------------------ #
    #  Ejecución ME12                                                      #
    # ------------------------------------------------------------------ #

    def run_me12(self, file_path, log_func=print):
        """Ejecuta la modificación masiva ME12."""
        # Import perezoso de validators (solo disponible en VM Windows)
        from validators import validate_excel, print_validation_errors

        if not self.session:
            raise RuntimeError(
                "SAP session no iniciada. Ejecute connect + login primero."
            )

        log_func(f"{'=' * 50}")
        log_func("Iniciando Proceso ME12 - Actualización Masiva de Precio...")
        log_func(f"{'=' * 50}")

        data, errors = validate_excel(file_path, log_func)

        if errors:
            print_validation_errors(errors, log_func)

        if data.empty:
            log_func("No hay registros válidos para procesar.")
            return

        self.session.findById("wnd[0]").maximize()

        total = len(data)
        ok_count = 0
        error_count = 0

        for index, row in data.iterrows():
            log_func(f"Procesando registro {index + 1} de {total}...")
            result = self._procesar_registro(row, index, log_func)

            if result.startswith("OK"):
                ok_count += 1
            else:
                error_count += 1

            time.sleep(self.delay_between_rows)

        log_func(f"{'=' * 50}")
        log_func("Proceso completado.")
        log_func(f"  Total: {total}")
        log_func(f"  Exitosos: {ok_count}")
        log_func(f"  Con errores: {error_count}")
        log_func(f"{'=' * 50}")

    def _procesar_registro(self, row, index, log_func):
        """Procesa un registro individual de ME12 — lógica completa de me12_massmod.py."""
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
        validez_desde, validez_hasta = self._compute_validity_dates(
            valido_desde_raw, valido_hasta_raw
        )

        try:
            # PASO 1: Navegar a ME12
            self.session.findById("wnd[0]/tbar[0]/okcd").Text = "/nME12"
            self.session.findById("wnd[0]").SendVKey(0)
            time.sleep(self.delay_after_enter)

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
            time.sleep(self.delay_after_enter)

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
            time.sleep(self.delay_after_enter)

            # PASO 6c: Boton Condiciones
            # Usar F8 (SendVKey 8) en lugar de btn[8].Press porque el COM reference
            # al boton de toolbar no ejecuta la accion (problema conocido de SAP GUI Scripting)
            self.session.findById("wnd[0]").SendVKey(8)
            time.sleep(self.delay_after_click)

            # DEBUG: Diagnosticar toolbar y botones
            log_func(f"  [DEBUG] Diagnosticando toolbar tbar[1]:")
            try:
                tbar1 = self.session.findById("wnd[0]/tbar[1]")
                log_func(f"    tbar[1] encontrado: type={tbar1.Type}, children={tbar1.Children.Count}")
                for j in range(tbar1.Children.Count):
                    btn = tbar1.Children(j)
                    log_func(f"      btn[{j}]: type={btn.Type}, ID='{btn.Id}', enabled={btn.Enabled}, visible={btn.Visible}")
            except Exception as e:
                log_func(f"  [DEBUG] Error accediendo a tbar[1]: {e}")

            # DEBUG: Listar ventanas abiertas para diagnosticar popup
            log_func(f"  [DEBUG] Ventanas SAP abiertas:")
            try:
                for i in range(self.session.Children.Count):
                    wnd = self.session.Children(i)
                    log_func(f"    wnd[{i}]: type={wnd.Type}, text='{wnd.Text}', ID='{wnd.Id}'")
            except Exception as e:
                log_func(f"  [DEBUG] Error listando ventanas: {e}")

            # PASO 7: Manejar popup "Períodos de validez de condiciones"
            time.sleep(1.0)  # Dar tiempo a SAP para procesar F8

            # Detectar popup por texto (más confiable que solo verificar existencia)
            popup_detected = False
            popup_text = ""
            try:
                wnd1 = self.session.findById("wnd[1]")
                popup_text = wnd1.Text
                popup_detected = True
                log_func(f"  [DEBUG] Popup detectado: '{popup_text}'")
            except Exception:
                pass

            if popup_detected:
                if "Períodos de validez" in popup_text or "validez" in popup_text.lower():
                    # Es el popup de períodos — seleccionar período existente
                    log_func(f"  [INFO] Popup de períodos detectado — seleccionando período")

                    # Diagnosticar tabla de períodos
                    try:
                        tbl = self.session.findById("wnd[1]/usr/tblSAPLV14ATCTRL_D0102")
                        log_func(f"  [DEBUG] Tabla períodos: rows={tbl.Rows.Count}, columns={tbl.Columns.Count}")

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
                            log_func(f"    Fila {r}:{row_text}")
                    except Exception as e:
                        log_func(f"  [DEBUG] Error diagnosticando tabla: {e}")

                    # Crear nuevo período con F7 y luego llenar fechas
                    log_func(f"  [INFO] Creando nuevo período con F7")

                    # Paso 1: Presionar F7 para crear nuevo período
                    try:
                        self.session.findById("wnd[1]").SendVKey(7)  # F7 = Nuevo período
                        time.sleep(1.0)  # Dar tiempo para que aparezcan los campos
                        log_func(f"  [INFO] F7 presionado — esperando campos de fecha")
                    except Exception as e:
                        log_func(f"  [WARN] Error presionando F7: {e}")

                    # Paso 2: Diagnosticar TODAS las ventanas después de F7
                    log_func(f"  [DEBUG] Ventanas después de F7:")
                    try:
                        for i in range(self.session.Children.Count):
                            wnd = self.session.Children(i)
                            log_func(f"    wnd[{i}]: type={wnd.Type}, text='{wnd.Text}', ID='{wnd.Id}'")
                            # Listar hijos de cada ventana
                            try:
                                for c in range(wnd.Children.Count):
                                    child = wnd.Children(c)
                                    child_id = child.Id if hasattr(child, 'Id') else 'N/A'
                                    child_type = child.Type if hasattr(child, 'Type') else 'N/A'
                                    child_text = ""
                                    try:
                                        child_text = child.Text if hasattr(child, 'Text') else ''
                                    except Exception:
                                        pass
                                    log_func(f"      [{c}] type={child_type}, ID='{child_id}', text='{child_text}'")
                            except Exception:
                                pass
                    except Exception as e:
                        log_func(f"    [DEBUG] Error listando ventanas: {e}")

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
                            log_func(f"    Campo desde = {validez_desde} (ID: {desde_id})")
                            desde_found = True
                            break
                        except Exception:
                            pass

                    for hasta_id in hasta_ids:
                        try:
                            field = self.session.findById(hasta_id)
                            field.Text = validez_hasta
                            log_func(f"    Campo hasta = {validez_hasta} (ID: {hasta_id})")
                            hasta_found = True
                            break
                        except Exception:
                            pass

                    if not desde_found:
                        log_func(f"  [WARN] No se encontró campo 'desde' en ninguna ventana")
                    if not hasta_found:
                        log_func(f"  [WARN] No se encontró campo 'hasta' en ninguna ventana")

                    # Paso 4: Confirmar — intentar Enter en cada ventana
                    time.sleep(0.3)
                    for wnd_id in ["wnd[2]", "wnd[1]"]:
                        try:
                            self.session.findById(wnd_id).SendVKey(0)
                            time.sleep(self.delay_after_click)
                            log_func(f"  [INFO] Confirmado con Enter en {wnd_id}")
                            break
                        except Exception:
                            pass
                else:
                    # Otro tipo de popup — intentar confirmar con Enter
                    log_func(f"  [DEBUG] Popup desconocido: '{popup_text}', intentando Enter")
                    try:
                        self.session.findById("wnd[1]").SendVKey(0)
                        time.sleep(self.delay_after_click)
                    except Exception:
                        pass
            else:
                # No hay popup — verificar si la tabla de condiciones ya está en wnd[0]
                try:
                    self._wait_for_control(
                        "wnd[0]/usr/tblSAPMV13ATCTRL_D0201",
                        timeout=3.0,
                        log_func=log_func,
                    )
                except Exception:
                    log_func("  [WARN] No se detectó popup ni tabla de condiciones")

            # PASO 8: Modificar precio en tabla de condiciones
            precio_id = (
                f"wnd[0]/usr/tblSAPMV13ATCTRL_D0201/"
                f"txtKONP-KBETR[{self.condition_row},0]"
            )
            self._wait_for_control(
                precio_id, timeout=10.0, log_func=log_func
            ).Text = nuevo_precio
            time.sleep(self.delay_after_click)

            # PASO 9: Guardar — usar SendVKey(11) en lugar de btn[11].Press
            # (mismo problema COM que btn[8])
            self.session.findById("wnd[0]").SendVKey(11)
            time.sleep(1.0)

            # PASO 10: Verificar status bar
            status_bar = ""
            try:
                status_bar = self.session.findById("wnd[0]/sbar").Text
            except Exception:
                pass

            if "error" in status_bar.lower():
                log_func(f"Fila {index}: ERROR SAP: {status_bar}")
                return f"ERROR SAP: {status_bar}"

            log_func(f"Fila {index}: OK - {material}/{proveedor}")
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

            log_func(f"Fila {index}: ERROR: {error_msg}")
            return f"ERROR: {error_msg}"

    # ------------------------------------------------------------------ #
    #  Cierre                                                              #
    # ------------------------------------------------------------------ #

    def close(self, log_func=print):
        """Cierra sesión SAP y SAP Logon.

        Equivalente a ``safe_close_window`` de ``script/sap.py``.
        """
        import pywintypes  # noqa: F811 — import local intentionally shadowed

        try:
            self.session.findById("wnd[0]").maximize()
            self.connection.CloseSession("ses[0]")
        except pywintypes.com_error as e:
            log_func(f"{'=' * 50}")
            log_func(f"Error al cerrar sesión SAP: {e}")
            log_func(f"{'=' * 50}")
        except Exception as e:
            log_func(f"{'=' * 50}")
            log_func(f"Error al cerrar sesión SAP: {e}")
            log_func(f"{'=' * 50}")
        finally:
            subprocess.run(["taskkill", "/f", "/im", "saplogon.exe"])

    # ------------------------------------------------------------------ #
    #  Helpers — fechas y controles                                         #
    # ------------------------------------------------------------------ #

    def _compute_validity_dates(self, valido_desde_raw: str,
                                valido_hasta_raw: str) -> tuple:
        """Calcula las fechas de validez para SAP según las reglas:
        - VALIDO_DESDE: siempre hoy o después. Si es anterior a hoy → usar hoy.
        - VALIDO_HASTA: si viene vacío o es anterior/igual a hoy → usar 31.12.9999.

        Retorna: (desde_dd.mm.yyyy, hasta_dd.mm.yyyy)
        """
        from datetime import datetime

        today = datetime.now().strftime("%Y%m%d")

        # === VALIDO_DESDE ===
        desde_fmt = self._parse_date(valido_desde_raw)
        if not desde_fmt or desde_fmt < today:
            desde_final = today
        else:
            desde_final = desde_fmt

        # === VALIDO_HASTA ===
        hasta_fmt = self._parse_date(valido_hasta_raw)
        if not hasta_fmt or hasta_fmt <= today:
            hasta_final = self.sap_default_date  # "31.12.9999"
        else:
            hasta_final = self._format_date_sap(hasta_fmt)

        # Convertir desde a dd.mm.yyyy
        desde_final = self._format_date_sap(desde_final)

        return (desde_final, hasta_final)

    @staticmethod
    def _parse_date(value: str) -> str:
        """Convierte dd.mm.yyyy o YYYYMMDD a YYYYMMDD. Retorna string vacío si no puede."""
        value = value.strip()
        if not value:
            return ""
        # Formato dd.mm.yyyy
        if "." in value:
            parts = value.split(".")
            if (len(parts) == 3
                    and len(parts[0]) == 2
                    and len(parts[1]) == 2
                    and len(parts[2]) == 4):
                if all(p.isdigit() for p in parts):
                    return f"{parts[2]}{parts[1]}{parts[0]}"  # YYYYMMDD
        # Formato YYYYMMDD
        if value.isdigit() and len(value) == 8:
            return value
        return ""

    @staticmethod
    def _format_date_sap(yyyymmdd: str) -> str:
        """Convierte YYYYMMDD a dd.mm.yyyy para SAP. Ejemplo: '20260805' → '05.08.2026'"""
        if not yyyymmdd or len(yyyymmdd) != 8:
            return yyyymmdd
        return f"{yyyymmdd[6:8]}.{yyyymmdd[4:6]}.{yyyymmdd[0:4]}"

    def _wait_for_control(self, control_id, timeout=5.0, log_func=None):
        """Reintenta findById hasta que el control exista o se agote el timeout."""
        start = time.time()
        attempts = 0
        while time.time() - start < timeout:
            try:
                ctrl = self.session.findById(control_id)
                if attempts > 0 and log_func:
                    log_func(f"  Control '{control_id}' encontrado tras {attempts} intentos")
                return ctrl
            except Exception:
                attempts += 1
                time.sleep(0.2)
        raise TimeoutError(
            f"Control '{control_id}' no encontrado tras {timeout}s ({attempts} intentos)"
        )
