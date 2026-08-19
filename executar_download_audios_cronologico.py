#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atalho para executar o script de download cronológico dos 457 áudios do canal IBPM.
"""

import sys
from pathlib import Path

# Adiciona scripts/audio ao path
SCRIPT_PATH = Path(__file__).resolve().parent / "scripts" / "audio" / "baixar_todos_audios_cronologico.py"

if __name__ == "__main__":
    if SCRIPT_PATH.exists():
        import subprocess
        sys.exit(subprocess.call([sys.executable, str(SCRIPT_PATH)]))
    else:
        print(f"❌ Script {SCRIPT_PATH} não encontrado!")
        sys.exit(1)
