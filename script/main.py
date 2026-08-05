# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PySide2.QtGui import QIcon
from PySide2.QtCore import Qt
from sap import SapGui
from ui_me12 import Ui_MainWindow
from paths import get_base_path
import sys
import shutil
from pathlib import Path
import os

BASE_DIR = Path(get_base_path())


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Automatizacion SAP - ME12 Price Change")

        self.btn_open.clicked.connect(self.open_file)
        self.btn_login.clicked.connect(self.login_sap)
        self.btn_ejecutar.clicked.connect(self.massive_change)
        self.btn_logout.clicked.connect(self.logout)
        self.btn_close.clicked.connect(self.close_application)

        self.plainTextEdit.setReadOnly(True)

        if hasattr(self, "lbl_template"):
            self.lbl_template.linkActivated.connect(self.download_template)

    def open_file(self):
        self.file = QFileDialog.getOpenFileName(
            self,
            "Elija la hoja de calculo",
            "",
            "Excel Files (*.xlsx *.xls)",
        )
        self.txt_file.setText(str(self.file[0]))

    def login_sap(self):
        self.sap = SapGui()
        self.sap.sapLogin(self.plainTextEdit.appendPlainText)

        if hasattr(self.sap, "session") and self.sap.session is not None:
            self.plainTextEdit.appendPlainText(f"{'='*50}")
            self.plainTextEdit.appendPlainText("Login exitoso")
            self.plainTextEdit.appendPlainText(f"{'='*50}")
        else:
            self.plainTextEdit.appendPlainText(f"{'='*50}")
            self.plainTextEdit.appendPlainText("Error: No se pudo establecer la sesión SAP")
            self.plainTextEdit.appendPlainText(f"{'='*50}")

    def massive_change(self):
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("Confirmacion de ejecucion masiva ME12")
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText("Esta seguro de ejecutar la actualizacion masiva de precios?")
        msgBox.setInformativeText(
            "Se modificaran los precios netos (PB00) de los info records de compras."
        )
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec_()

        if ret == QMessageBox.Yes:
            try:
                self.sap.massive_change(
                    self.txt_file.text(), self.plainTextEdit.appendPlainText
                )
                self.plainTextEdit.appendPlainText(f"{'='*50}")
                self.plainTextEdit.appendPlainText("Ejecucion completada con exito!")
                self.plainTextEdit.appendPlainText(f"{'='*50}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error durante la ejecucion: {e}")

    def logout(self):
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("Cerrar")
        msgBox.setIcon(QMessageBox.Question)
        msgBox.setText("Esta seguro que desea cerrar la sesion?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        ret = msgBox.exec_()

        if ret == QMessageBox.Yes:
            self.sap.safe_close_window(self.plainTextEdit.appendPlainText)
            self.plainTextEdit.appendPlainText(f"{'='*50}")
            self.plainTextEdit.appendPlainText("Sesion cerrada con exito")
            self.plainTextEdit.appendPlainText(f"{'='*50}")

    def close_application(self):
        self.close()

    def download_template(self):
        base_path = get_base_path()
        template_source = Path(base_path) / "template_me12.xlsx"
        if not template_source.exists():
            QMessageBox.critical(
                self, "Error", "No se encontro el archivo de plantilla."
            )
            return
        dest = QFileDialog.getSaveFileName(
            self, "Guardar plantilla como", "template_me12.xlsx", "Excel Files (*.xlsx)"
        )
        if dest:
            try:
                shutil.copy(template_source, dest[0])
                QMessageBox.information(
                    self, "Exito", "Plantilla descargada exitosamente."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"No se pudo descargar la plantilla: {e}"
                )


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("icon.ico"))
    window = MainWindow()
    window.show()
    app.exec_()
