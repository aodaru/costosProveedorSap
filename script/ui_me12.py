# -*- coding: utf-8 -*-

# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

################################################################################
## Form generated from reading UI file 'ui_me12.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(639, 547)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.Pages = QStackedWidget(self.centralwidget)
        self.Pages.setObjectName(u"Pages")
        self.Pages.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.pg_sap = QWidget()
        self.pg_sap.setObjectName(u"pg_sap")
        self.verticalLayout_4 = QVBoxLayout(self.pg_sap)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_2 = QLabel(self.pg_sap)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout_4.addWidget(self.label_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.txt_file = QLineEdit(self.pg_sap)
        self.txt_file.setObjectName(u"txt_file")
        font = QFont()
        font.setPointSize(11)
        self.txt_file.setFont(font)
        self.txt_file.setCursor(QCursor(Qt.ArrowCursor))
        self.txt_file.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_2.addWidget(self.txt_file)

        self.btn_open = QPushButton(self.pg_sap)
        self.btn_open.setObjectName(u"btn_open")
        self.btn_open.setMinimumSize(QSize(100, 30))
        self.btn_open.setStyleSheet(u"QPushButton{\n"
"	color:black;\n"
"	background-color: rgb(248,248,248);\n"
"	border-radius: 15px;\n"
"}\n"
"\n"
"QPushButton:hover{\n"
"	background-color: rgb(159,238,238);\n"
"	color:(47,47,47);\n"
"}")

        self.horizontalLayout_2.addWidget(self.btn_open)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.plainTextEdit = QPlainTextEdit(self.pg_sap)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setReadOnly(True)

        self.horizontalLayout_3.addWidget(self.plainTextEdit)

        self.verticalScrollBar = QScrollBar(self.pg_sap)
        self.verticalScrollBar.setObjectName(u"verticalScrollBar")
        self.verticalScrollBar.setOrientation(Qt.Vertical)

        self.horizontalLayout_3.addWidget(self.verticalScrollBar)

        self.frame_2 = QFrame(self.pg_sap)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setStyleSheet(u"QPushButton{\n"
"	color:black;\n"
"	background-color: rgb(248,248,248);\n"
"	border-radius: 15px;\n"
"}\n"
"\n"
"QPushButton:hover{\n"
"	background-color: rgb(159,238,238);\n"
"	color:(47,47,47);\n"
"}")
        self.frame_2.setFrameShape(QFrame.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.btn_login = QPushButton(self.frame_2)
        self.btn_login.setObjectName(u"btn_login")
        self.btn_login.setMinimumSize(QSize(100, 30))
        font1 = QFont()
        font1.setPointSize(10)
        self.btn_login.setFont(font1)
        self.btn_login.setCursor(QCursor(Qt.PointingHandCursor))

        self.verticalLayout_3.addWidget(self.btn_login)

        self.btn_ejecutar = QPushButton(self.frame_2)
        self.btn_ejecutar.setObjectName(u"btn_ejecutar")
        self.btn_ejecutar.setMinimumSize(QSize(100, 30))
        self.btn_ejecutar.setFont(font1)
        self.btn_ejecutar.setCursor(QCursor(Qt.PointingHandCursor))

        self.verticalLayout_3.addWidget(self.btn_ejecutar)

        self.btn_logout = QPushButton(self.frame_2)
        self.btn_logout.setObjectName(u"btn_logout")
        self.btn_logout.setMinimumSize(QSize(100, 30))
        self.btn_logout.setFont(font1)
        self.btn_logout.setCursor(QCursor(Qt.PointingHandCursor))

        self.verticalLayout_3.addWidget(self.btn_logout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.btn_close = QPushButton(self.frame_2)
        self.btn_close.setObjectName(u"btn_close")
        self.btn_close.setMinimumSize(QSize(100, 30))
        self.btn_close.setFont(font1)
        self.btn_close.setCursor(QCursor(Qt.PointingHandCursor))

        self.verticalLayout_3.addWidget(self.btn_close)


        self.horizontalLayout_3.addWidget(self.frame_2)


        self.verticalLayout_4.addLayout(self.horizontalLayout_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lbl_template = QLabel(self.pg_sap)
        self.lbl_template.setObjectName(u"lbl_template")
        self.lbl_template.setCursor(QCursor(Qt.PointingHandCursor))
        self.lbl_template.setOpenExternalLinks(False)

        self.horizontalLayout.addWidget(self.lbl_template)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.Pages.addWidget(self.pg_sap)

        self.verticalLayout.addWidget(self.Pages)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.Pages.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; font-weight:600;\">ME12 - Actualizacion Masiva de Precio Info Records</span></p></body></html>", None))
        self.txt_file.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Seleccione el archivo de excel", None))
        self.btn_open.setText(QCoreApplication.translate("MainWindow", u"Abrir Archivo", None))
        self.btn_login.setText(QCoreApplication.translate("MainWindow", u"Login", None))
        self.btn_ejecutar.setText(QCoreApplication.translate("MainWindow", u"Ejecutar", None))
        self.btn_logout.setText(QCoreApplication.translate("MainWindow", u"Logout", None))
        self.btn_close.setText(QCoreApplication.translate("MainWindow", u"Cerrar SAP", None))
        self.lbl_template.setText(QCoreApplication.translate("MainWindow", u"<a href=\"download\">Descargar Plantilla Excel</a>", None))
    # retranslateUi
