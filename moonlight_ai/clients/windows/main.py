"""
MoonLight AI Windows Client
Windows masaüstü istemcisi - CLI ve GUI seçenekleri
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from clients.windows.cli_client import CLIClient
from clients.windows.gui_client import GUIClient

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Logging ayarları"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('moonlight_client.log')
        ]
    )


async def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description='MoonLight AI Windows Client')
    parser.add_argument('--mode', choices=['cli', 'gui'], default='cli',
                       help='İstemci modu (varsayılan: cli)')
    parser.add_argument('--server', default='http://localhost:8000',
                       help='API sunucu adresi (varsayılan: http://localhost:8000)')
    parser.add_argument('--ws-server', default='ws://localhost:8001',
                       help='WebSocket sunucu adresi (varsayılan: ws://localhost:8001)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log seviyesi (varsayılan: INFO)')
    
    args = parser.parse_args()
    
    # Logging ayarla
    setup_logging(args.log_level)
    
    logger.info("MoonLight AI Windows Client başlatılıyor...")
    logger.info(f"Mod: {args.mode}")
    logger.info(f"API Sunucu: {args.server}")
    logger.info(f"WebSocket Sunucu: {args.ws_server}")
    
    try:
        if args.mode == 'cli':
            # CLI istemci
            client = CLIClient(args.server, args.ws_server)
            await client.run()
        else:
            # GUI istemci
            client = GUIClient(args.server, args.ws_server)
            await client.run()
            
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"İstemci hatası: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())