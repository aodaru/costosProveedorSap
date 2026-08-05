# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import subprocess
import time
import os
import sys
from dotenv import load_dotenv
from me12_massmod import SapMe12MassMod
import win32com.client  # type: ignore
import pywintypes
from pathlib import Path
from paths import get_base_path

BASE_DIR = Path(get_base_path())
load_dotenv(BASE_DIR / ".env")

system_sap = os.getenv("SYSTEM")
mandt = os.getenv("MANDT")
username = os.getenv("USER")
password = os.getenv("PASSWD")
language = os.getenv("LANGUAGE")


class SapGui:
    def open_sap(self):
        self.path = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
        subprocess.Popen(self.path)

    def connection_sap(self):
        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
            application = SapGuiAuto.GetScriptingEngine
            self.connection = application.Children(0)
            self.session = self.connection.Children(0)
            self.session.findById("wnd[0]").maximize()
        except pywintypes.com_error as e:
            raise RuntimeError(f"No se pudo conectar a SAP GUI: {e}")

    def sapLogin(self, log_func=print):
        self.open_sap()
        time.sleep(3)

        try:
            self.SapGuiAuto = win32com.client.GetObject("SAPGUI")
        except pywintypes.com_error as e:
            log_func(f"{'='*50}")
            log_func(f"SAP GUI no encontrado: {e}")
            log_func(f"Asegurese de que SAP GUI esta instalado y disponible.")
            log_func(f"{'='*50}")
            return

        self.application = self.SapGuiAuto.GetScriptingEngine

        try:
            self.connection = self.application.OpenConnection(system_sap, True)
        except Exception as e:
            log_func(f"{'='*50}")
            log_func(f"Error tratando de conectar con SAP: {e}")
            log_func(f"La red no esta accesible o el sistema SAP no esta disponible.")
            log_func(f"{'='*50}")
            return

        time.sleep(3)
        self.session = self.connection.Children(0)

        try:
            # CLIENTE
            self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = mandt
            # USUARIO
            self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = username
            # CONTRASENA
            self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = password
            # IDIOMA
            self.session.findById("wnd[0]/usr/txtRSYST-LANGU").text = language
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

    def safe_close_window(self, log_func=print):
        try:
            self.connection_sap()
            self.connection.CloseSession('ses[0]')
        except Exception as e:
            log_func(f"{'='*50}")
            log_func(f"Error al cerrar sesion SAP: {e}")
            log_func(f"{'='*50}")
        finally:
            subprocess.run(["taskkill", "/f", "/im", "saplogon.exe"])

    def massive_change(self, file_path, log_func=print):
        if not hasattr(self, "session") or self.session is None:
            raise RuntimeError("SAP session no iniciada. Ejecute sapLogin primero.")

        runner = SapMe12MassMod(self.session, log_func)
        return runner.run_me12_massmod(file_path)
