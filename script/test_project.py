# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import MagicMock
from validators import validate_excel, validate_field, REQUIRED_COLUMNS, OPTIONAL_COLUMNS
from me12_massmod import SapMe12MassMod


# --- Tests para validators.py ---


class TestValidators:
    def test_validate_field_valid_material(self):
        error = validate_field("MATERIAL", "12345678", 1)
        assert error is None

    def test_validate_field_invalid_material(self):
        error = validate_field("MATERIAL", "ABC123", 1)
        assert "no debe contener letras" in error

    def test_validate_field_missing_material(self):
        error = validate_field("MATERIAL", "", 1)
        assert "es obligatorio" in error

    def test_validate_field_missing_proveedor(self):
        error = validate_field("PROVEEDOR", "", 1)
        assert "es obligatorio" in error

    def test_validate_field_invalid_proveedor(self):
        error = validate_field("PROVEEDOR", "ABC123", 1)
        assert "no debe contener letras" in error

    def test_validate_field_valid_proveedor(self):
        error = validate_field("PROVEEDOR", "10000456", 1)
        assert error is None

    def test_validate_field_valid_org_compras(self):
        error = validate_field("ORG_COMPRAS", "1000", 1)
        assert error is None

    def test_validate_field_invalid_org_compras(self):
        error = validate_field("ORG_COMPRAS", "", 1)
        assert "es obligatorio" in error

    def test_validate_field_missing_nuevo_precio(self):
        error = validate_field("NUEVO_PRECIO", "", 1)
        assert "es obligatorio" in error

    def test_validate_field_invalid_nuevo_precio(self):
        error = validate_field("NUEVO_PRECIO", "ABC", 1)
        assert "debe ser numérico" in error

    def test_validate_field_negative_nuevo_precio(self):
        error = validate_field("NUEVO_PRECIO", "-5", 1)
        assert "debe ser mayor a 0" in error

    def test_validate_field_valid_nuevo_precio(self):
        error = validate_field("NUEVO_PRECIO", "150.50", 1)
        assert error is None

    def test_validate_field_invalid_tipo_condicion(self):
        error = validate_field("TIPO_CONDICION", "Z001", 1)
        assert "debe ser 'PB00' o 'PB01'" in error

    def test_validate_field_valid_tipo_condicion(self):
        error = validate_field("TIPO_CONDICION", "PB00", 1)
        assert error is None

    def test_validate_field_invalid_moneda(self):
        error = validate_field("MONEDA", "JPY", 1)
        assert "debe ser 'MXN', 'USD', 'EUR' o 'PAB'" in error

    def test_validate_field_valid_moneda(self):
        error = validate_field("MONEDA", "USD", 1)
        assert error is None

    def test_validate_field_invalid_unidad_precio(self):
        error = validate_field("UNIDAD_PRECIO", "1.5", 1)
        assert "debe ser un entero" in error

    def test_validate_field_valid_unidad_precio(self):
        error = validate_field("UNIDAD_PRECIO", "1", 1)
        assert error is None

    def test_validate_field_invalid_fecha_formato(self):
        error = validate_field("VALIDO_DESDE", "2026-08-01", 1)
        assert "YYYYMMDD" in error

    def test_validate_field_valid_fecha(self):
        error = validate_field("VALIDO_DESDE", "20260801", 1)
        assert error is None

    def test_validate_field_nan_value(self):
        error = validate_field("MATERIAL", "nan", 1)
        assert "es obligatorio" in error


class TestValidateExcel:
    def _create_excel(self, data, sheet_name="Datos"):
        df = pd.DataFrame(data)
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        df.to_excel(tmp.name, sheet_name=sheet_name, index=False)
        tmp.close()
        return tmp.name

    def test_validate_excel_valid_data(self):
        data = {
            "Material": ["10000123"],
            "Proveedor": ["10000456"],
            "Org_Compras": ["1000"],
            "Nuevo_Precio": ["150.50"],
            "Unidad_Medida": ["ST"],
        }
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) == 0
            assert len(validated_data) == 1
        finally:
            os.unlink(file_path)

    def test_validate_excel_multiple_rows(self):
        data = {
            "Material": ["10000123", "10000789"],
            "Proveedor": ["10000456", "10000456"],
            "Org_Compras": ["1000", "1000"],
            "Nuevo_Precio": ["150.50", "200.00"],
            "Unidad_Medida": ["ST", "ST"],
        }
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) == 0
            assert len(validated_data) == 2
        finally:
            os.unlink(file_path)

    def test_validate_excel_missing_required_column(self):
        data = {
            "Material": ["10000123"],
            # Missing Proveedor
            "Org_Compras": ["1000"],
            "Nuevo_Precio": ["150.50"],
        }
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) >= 1
            assert "PROVEEDOR" in errors[0]
        finally:
            os.unlink(file_path)

    def test_validate_excel_invalid_material(self):
        data = {
            "Material": ["ABC123"],
            "Proveedor": ["10000456"],
            "Org_Compras": ["1000"],
            "Nuevo_Precio": ["150.50"],
        }
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) >= 1
            assert "MATERIAL" in errors[0]
        finally:
            os.unlink(file_path)

    def test_validate_excel_defaults_applied(self):
        data = {
            "Material": ["10000123"],
            "Proveedor": ["10000456"],
            "Org_Compras": ["1000"],
            "Nuevo_Precio": ["150.50"],
            "Unidad_Medida": ["ST"],
        }
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) == 0
            assert validated_data.iloc[0]["TIPO_INFO"] == "0"
            assert validated_data.iloc[0]["TIPO_CONDICION"] == "PB00"
            assert validated_data.iloc[0]["MONEDA"] == "MXN"
            assert validated_data.iloc[0]["UNIDAD_PRECIO"] == "1"
            assert validated_data.iloc[0]["VALIDO_HASTA"] == "99991231"
        finally:
            os.unlink(file_path)

    def test_validate_excel_empty_file(self):
        data = {}
        file_path = self._create_excel(data)
        try:
            validated_data, errors = validate_excel(file_path)
            assert len(errors) >= 1
        finally:
            os.unlink(file_path)

    def test_validate_excel_wrong_sheet_name(self):
        data = {"Material": ["10000123"]}
        df = pd.DataFrame(data)
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        df.to_excel(tmp.name, sheet_name="Hoja1", index=False)
        tmp.close()
        try:
            validated_data, errors = validate_excel(tmp.name)
            assert len(errors) >= 1
            assert "Error al leer" in errors[0]
        finally:
            os.unlink(tmp.name)


# --- Tests para me12_massmod.py ---


class TestSapMe12MassMod:
    def test_runner_creation(self):
        runner = SapMe12MassMod(None, print)
        assert runner.session is None

    def test_runner_with_mock_session(self):
        mock_session = MagicMock()
        runner = SapMe12MassMod(mock_session, print)
        assert runner.session is mock_session

    def test_run_me12_massmod_empty_excel(self):
        data = {
            "Material": [],
            "Proveedor": [],
            "Org_Compras": [],
            "Nuevo_Precio": [],
        }
        df = pd.DataFrame(data)
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        df.to_excel(tmp.name, sheet_name="Datos", index=False)
        tmp.close()
        try:
            mock_session = MagicMock()
            runner = SapMe12MassMod(mock_session, print)
            runner.run_me12_massmod(tmp.name)
            # No SAP calls should be made for empty data
            mock_session.findById.assert_not_called()
        finally:
            os.unlink(tmp.name)

    def test_procesar_registro_ok(self):
        mock_session = MagicMock()
        mock_session.findById.return_value.Text = ""
        runner = SapMe12MassMod(mock_session, print)

        row = pd.Series({
            "MATERIAL": "10000123",
            "PROVEEDOR": "10000456",
            "ORG_COMPRAS": "1000",
            "TIPO_INFO": "0",
            "TIPO_CONDICION": "PB00",
            "NUEVO_PRECIO": "150.50",
            "MONEDA": "MXN",
            "UNIDAD_PRECIO": "1",
            "UNIDAD_MEDIDA": "",
            "VALIDO_DESDE": "20260801",
            "VALIDO_HASTA": "99991231",
        })

        result = runner._procesar_registro(row, 0)
        assert result == "OK"

    def test_procesar_registro_sap_error(self):
        mock_session = MagicMock()
        # Simulate SAP returning an error in status bar
        def find_by_id_side_effect(id_str):
            mock_obj = MagicMock()
            if "sbar" in id_str:
                mock_obj.Text = "Error: Info record not found"
            elif "okcd" in id_str:
                mock_obj.Text = ""
            else:
                mock_obj.Text = ""
            return mock_obj

        mock_session.findById.side_effect = find_by_id_side_effect
        runner = SapMe12MassMod(mock_session, print)

        row = pd.Series({
            "MATERIAL": "99999999",
            "PROVEEDOR": "99999999",
            "ORG_COMPRAS": "1000",
            "TIPO_INFO": "0",
            "TIPO_CONDICION": "PB00",
            "NUEVO_PRECIO": "100.00",
            "MONEDA": "MXN",
            "UNIDAD_PRECIO": "1",
            "UNIDAD_MEDIDA": "",
            "VALIDO_DESDE": "20260801",
            "VALIDO_HASTA": "99991231",
        })

        result = runner._procesar_registro(row, 0)
        assert "ERROR" in result

    def test_procesar_registro_exception(self):
        mock_session = MagicMock()
        mock_session.findById.side_effect = Exception("COM error")
        runner = SapMe12MassMod(mock_session, print)

        row = pd.Series({
            "MATERIAL": "10000123",
            "PROVEEDOR": "10000456",
            "ORG_COMPRAS": "1000",
            "TIPO_INFO": "0",
            "TIPO_CONDICION": "PB00",
            "NUEVO_PRECIO": "150.50",
            "MONEDA": "MXN",
            "UNIDAD_PRECIO": "1",
            "UNIDAD_MEDIDA": "",
            "VALIDO_DESDE": "20260801",
            "VALIDO_HASTA": "99991231",
        })

        result = runner._procesar_registro(row, 0)
        assert "ERROR" in result
