# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

"""
Script de build para generar el ejecutable ME12_MassMod.exe con PyInstaller.

Uso:
    python build_exe.py

Requisitos:
    - Python 3.8+
    - Dependencias instaladas: pip install -r requirements.txt
    - PyInstaller incluido en requirements.txt

Salida:
    - dist/ME12_MassMod.exe  (ejecutable autocontenido)
    - build/                 (archivos temporales de PyInstaller)

Notas:
    - El .exe es windowed (sin consola) — usa la GUI para logs.
    - template_me12.xlsx y .env.example se incluyen como datos empaquetados.
    - Para development/QA, ejecutar main.py directamente en vez del .exe.
"""

import subprocess
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent
SPEC_FILE = BASE_DIR / "me12_massmod.spec"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"


def run_build():
    """Ejecuta PyInstaller con el spec y verifica el resultado."""

    # Limpiar builds previos
    if DIST_DIR.exists():
        print(f"Limpiando {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        print(f"Limpiando {BUILD_DIR}...")
        shutil.rmtree(BUILD_DIR)

    # Verificar spec
    if not SPEC_FILE.exists():
        print(f"ERROR: {SPEC_FILE} no encontrado.")
        sys.exit(1)

    # Comando PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
    ]

    print(f"Ejecutando: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode != 0:
        print("=" * 60)
        print("ERROR: PyInstaller falló.")
        sys.exit(result.returncode)

    # Verificar output
    exe_path = DIST_DIR / "ME12_MassMod.exe"
    if not exe_path.exists():
        print(f"ERROR: No se generó {exe_path}")
        sys.exit(1)

    # Información del build
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print("=" * 60)
    print(f"BUILD EXITOSO: {exe_path}")
    print(f"Tamaño: {size_mb:.1f} MB")
    print("=" * 60)
    print()
    print("NOTAS:")
    print("  - El .exe es autocontenido (no requiere Python instalado).")
    print("  - template_me12.xlsx está empaquetado; se extrae junto al .exe.")
    print("  - Crear .env junto al .exe con las credenciales SAP.")
    print("  - Requiere SAP GUI instalado en la máquina destino.")


if __name__ == "__main__":
    run_build()
