"""
MoonLight AI Test Suite
Test framework ve test utilities
"""

import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

__version__ = "0.1.0"