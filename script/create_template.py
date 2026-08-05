"""
Generador de template_me12.xlsx
Ejecutar una vez para crear la plantilla: python create_template.py
"""
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Datos"

headers = [
    "Material", "Proveedor", "Org_Compras", "Tipo_Info",
    "Tipo_Condicion", "Nuevo_Precio", "Moneda", "Unidad_Precio",
    "Unidad_Medida", "Valido_Desde", "Valido_Hasta",
]
ws.append(headers)
ws.append(["10000123", "10000456", "1000", "0", "PB00", "150.50", "MXN", "1", "ST", "20260801", "99991231"])
ws.append(["10000789", "10000456", "1000", "0", "PB00", "200.00", "MXN", "1", "ST", "20260801", "99991231"])

wb.save("template_me12.xlsx")
print("template_me12.xlsx creado exitosamente.")
