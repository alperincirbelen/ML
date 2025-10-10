"""
MoonLight AI Server Launcher
Sunucu başlatma scripti
"""

import asyncio
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import main

if __name__ == "__main__":
    # Sunucu modunu varsayılan yap
    if '--mode' not in sys.argv:
        sys.argv.extend(['--mode', 'server'])
    
    asyncio.run(main())