"""
MoonLight AI Client Launcher
Windows istemci başlatma scripti
"""

import asyncio
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from clients.windows.main import main

if __name__ == "__main__":
    asyncio.run(main())