# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import pandas as pd
from typing import Optional, Tuple, List
from pathlib import Path
from datetime import datetime
from paths import get_base_path

# Columnas esperadas en la hoja "Datos" del template ME12
REQUIRED_COLUMNS = [
    "MATERIAL",
    "PROVEEDOR",
    "ORG_COMPRAS",
    "NUEVO_PRECIO",
]

OPTIONAL_COLUMNS = {
    "TIPO_INFO": "0",
    "TIPO_CONDICION": "PB00",
    "MONEDA": "MXN",
    "UNIDAD_PRECIO": "1",
    "UNIDAD_MEDIDA": "",
    "VALIDO_DESDE": datetime.now().strftime("%Y%m%d"),
    "VALIDO_HASTA": "99991231",
}


def is_numeric(value: str) -> bool:
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_integer(value: str) -> bool:
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def solo_numeros(texto: str) -> bool:
    texto = texto.strip()
    return texto.isdigit()


def _normalize_date_to_yyyymmdd(value: str) -> str:
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
    if solo_numeros(value) and len(value) == 8:
        return value
    return ""


def validate_field(field: str, value: str, row_num: int) -> Optional[str]:
    value = str(value).strip()

    if not value or value.lower() == "nan":
        return f"Fila {row_num}: '{field}' es obligatorio"

    if field == "MATERIAL" and not solo_numeros(value):
        return f"Fila {row_num}: 'MATERIAL - {value}' no debe contener letras ni caracteres especiales"

    if field == "PROVEEDOR" and not solo_numeros(value):
        return f"Fila {row_num}: 'PROVEEDOR - {value}' no debe contener letras ni caracteres especiales"

    if field == "ORG_COMPRAS" and not value.strip():
        return f"Fila {row_num}: 'ORG_COMPRAS' es obligatorio"

    if field == "NUEVO_PRECIO":
        if not is_numeric(value):
            return f"Fila {row_num}: 'NUEVO_PRECIO' debe ser numérico"
        if float(value) <= 0:
            return f"Fila {row_num}: 'NUEVO_PRECIO' debe ser mayor a 0"

    if field == "TIPO_CONDICION" and value not in ("PB00", "PB01"):
        return f"Fila {row_num}: 'TIPO_CONDICION' debe ser 'PB00' o 'PB01'"

    if field == "MONEDA" and value not in ("MXN", "USD", "EUR", "PAB"):
        return f"Fila {row_num}: 'MONEDA' debe ser 'MXN', 'USD', 'EUR' o 'PAB'"

    if field == "UNIDAD_PRECIO" and not is_integer(value):
        return f"Fila {row_num}: 'UNIDAD_PRECIO' debe ser un entero"

    if field == "VALIDO_DESDE" or field == "VALIDO_HASTA":
        # Aceptar formato dd.mm.yyyy o YYYYMMDD
        if value and value != "":
            # Verificar formato dd.mm.yyyy
            if "." in value:
                parts = value.split(".")
                if len(parts) != 3 or len(parts[0]) != 2 or len(parts[1]) != 2 or len(parts[2]) != 4:
                    return f"Fila {row_num}: '{field}' debe tener formato dd.mm.yyyy"
                if not all(p.isdigit() for p in parts):
                    return f"Fila {row_num}: '{field}' debe contener solo números"
            # Verificar formato YYYYMMDD
            elif not solo_numeros(value) or len(value) != 8:
                return f"Fila {row_num}: '{field}' debe tener formato dd.mm.yyyy o YYYYMMDD"

    return None


def validate_excel(file_path: str, log_func=print) -> Tuple[pd.DataFrame, List[str]]:
    errors = []

    try:
        data = pd.read_excel(file_path, sheet_name="Datos", dtype=str)
    except Exception as e:
        errors.append(f"Error al leer el archivo Excel: {e}")
        return pd.DataFrame(), errors

    if data.empty:
        errors.append("El archivo está vacío o no contiene datos")
        return data, errors

    data.columns = data.columns.str.strip().str.upper().str.replace(" ", "_")

    # Verificar columnas requeridas
    for col in REQUIRED_COLUMNS:
        if col not in data.columns:
            errors.append(f"Columna requerida '{col}' no encontrada en el archivo")

    if errors:
        return data, errors

    # Aplicar defaults
    for col, default in OPTIONAL_COLUMNS.items():
        if col not in data.columns:
            data[col] = default
        else:
            data[col] = data[col].apply(
                lambda x: default if pd.isna(x) or str(x).strip() == "" else x
            )

    # Validar cada fila
    for index, row in data.iterrows():
        row_num = index + 2  # +2 because index starts at 0 and row 1 is header

        for field in REQUIRED_COLUMNS:
            error = validate_field(field, row.get(field, ""), row_num)
            if error:
                errors.append(error)
                data.drop(index, inplace=True)
                break

        if index not in data.index:
            continue

        for field in OPTIONAL_COLUMNS:
            error = validate_field(field, row.get(field, ""), row_num)
            if error:
                errors.append(error)
                data.drop(index, inplace=True)
                break

        # Validación cruzada: VALIDO_DESDE <= VALIDO_HASTA (ambos en YYYYMMDD)
        if index in data.index:
            if "VALIDO_DESDE" in row and "VALIDO_HASTA" in row:
                desde_raw = str(row.get("VALIDO_DESDE", "")).strip()
                hasta_raw = str(row.get("VALIDO_HASTA", "")).strip()
                if desde_raw and hasta_raw:
                    desde_fmt = _normalize_date_to_yyyymmdd(desde_raw)
                    hasta_fmt = _normalize_date_to_yyyymmdd(hasta_raw)
                    if desde_fmt and hasta_fmt and desde_fmt > hasta_fmt:
                        errors.append(f"Fila {row_num}: 'VALIDO_DESDE' ({desde_raw}) debe ser menor o igual a 'VALIDO_HASTA' ({hasta_raw})")
                        data.drop(index, inplace=True)

    return data, errors


def print_validation_errors(errors: List[str], log_func=print):
    if errors:
        log_func(f"\n{'='*50}")
        log_func(f"Se encontraron {len(errors)} error(es):")
        log_func("=" * 50)
        for error in errors:
            log_func(f"  - {error}")
        log_func("=" * 50)
