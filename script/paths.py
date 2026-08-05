# Copyright (c) 2026 Adal Michael Garcia
# Licensed under the MIT License - see LICENSE file for details

import os
import sys
from pathlib import Path


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))
