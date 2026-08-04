# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import time
from validators import validate_excel, print_validation_errors


# Delays configurables (segundos)
DELAY_AFTER_ENTER = 0.5
DELAY_AFTER_CLICK = 0.3
DELAY_BETWEEN_ROWS = 1.0

# Indice 0-based de la fila de condicion en la tabla de SAP
CONDITION_ROW = 2


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
        validez_desde = str(row.get("VALIDO_DESDE", "")).strip()
        validez_hasta = str(row.get("VALIDO_HASTA", "99991231")).strip()

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

            # PASO 6: Boton Condiciones
            wait_for_control(self.session, "wnd[0]/tbar[1]/btn[8]", log_func=self.log).Press
            time.sleep(DELAY_AFTER_CLICK)

            # PASO 7: Popup de confirmacion (puede no aparecer)
            try:
                self.session.findById("wnd[1]/tbar[0]/btn[7]").Press
                time.sleep(DELAY_AFTER_CLICK)
            except Exception:
                pass  # Popup no aparecio, es normal

            # PASO 8: Modificar precio en tabla de condiciones
            precio_id = f"wnd[0]/usr/tblSAPMV13ATCTRL_D0201/txtKONP-KBETR[{CONDITION_ROW},0]"
            wait_for_control(self.session, precio_id, log_func=self.log).Text = nuevo_precio
            time.sleep(DELAY_AFTER_CLICK)

            # PASO 9: Guardar (F11)
            self.session.findById("wnd[0]/tbar[0]/btn[11]").Press
            time.sleep(DELAY_AFTER_ENTER)

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
