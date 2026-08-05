# PAB Currency Support

Added PAB (Panamanian Balboa) to the allowed currencies in the validation logic.

## Changes Made

### `validators.py` (line 74-75)

**Before:**
```python
if field == "MONEDA" and value not in ("MXN", "USD", "EUR"):
    return f"Fila {row_num}: 'MONEDA' debe ser 'MXN', 'USD' o 'EUR'"
```

**After:**
```python
if field == "MONEDA" and value not in ("MXN", "USD", "EUR", "PAB"):
    return f"Fila {row_num}: 'MONEDA' debe ser 'MXN', 'USD', 'EUR' o 'PAB'"
```

### `test_project.py` (line 75)

**Before:**
```python
assert "debe ser 'MXN', 'USD' o 'EUR'" in error
```

**After:**
```python
assert "debe ser 'MXN', 'USD', 'EUR' o 'PAB'" in error
```

## Test Results

```
34 passed in 6.78s
```

All tests pass, including `test_validate_field_invalid_moneda` which validates the updated error message.
