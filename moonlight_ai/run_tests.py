"""
Test Runner
Test çalıştırma scripti
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=False):
    """
    Testleri çalıştır
    Args:
        test_type: Test türü (unit, integration, all)
        verbose: Detaylı çıktı
        coverage: Coverage raporu
    """
    
    # Proje kök dizini
    project_root = Path(__file__).parent
    
    # Pytest komutunu oluştur
    cmd = ["python", "-m", "pytest"]
    
    # Test dizinini belirle
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "backtesting":
        cmd.append("tests/backtesting/")
    else:
        cmd.append("tests/")
    
    # Ek parametreler
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=core", "--cov-report=html", "--cov-report=term"])
    
    # Async testler için
    cmd.append("--asyncio-mode=auto")
    
    # Markers
    cmd.extend(["-m", "not slow"])  # Slow testleri varsayılan olarak çalıştırma
    
    print(f"🧪 Testler çalıştırılıyor: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        # Testleri çalıştır
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        if result.returncode == 0:
            print("\n✅ Tüm testler başarılı!")
        else:
            print(f"\n❌ Testler başarısız (Exit code: {result.returncode})")
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⚠️ Testler kullanıcı tarafından durduruldu")
        return 1
    except Exception as e:
        print(f"\n❌ Test çalıştırma hatası: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="MoonLight AI Test Runner")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "backtesting", "all"],
        default="all",
        help="Test türü (varsayılan: all)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Detaylı çıktı"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Coverage raporu oluştur"
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Yavaş testleri de çalıştır"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Test bağımlılıklarını yükle"
    )
    
    args = parser.parse_args()
    
    # Test bağımlılıklarını yükle
    if args.install_deps:
        print("📦 Test bağımlılıkları yükleniyor...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "pytest", "pytest-asyncio", "pytest-cov", "pytest-mock"
        ])
    
    # Slow testler için marker'ı kaldır
    if args.slow:
        # Bu durumda slow testleri de çalıştır
        pass
    
    # Testleri çalıştır
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()