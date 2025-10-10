# MoonLight AI - Kullanım Rehberi

## İçindekiler
1. [Hızlı Başlangıç](#hızlı-başlangıç)
2. [Sunucu Modu](#sunucu-modu)
3. [İstemci Kullanımı](#istemci-kullanımı)
4. [API Referansı](#api-referansı)
5. [Strateji Geliştirme](#strateji-geliştirme)
6. [Risk Yönetimi](#risk-yönetimi)
7. [İleri Seviye Kullanım](#ileri-seviye-kullanım)

## Hızlı Başlangıç

### 1. Demo Modu ile Test

En hızlı test yolu demo modunu kullanmaktır:

```bash
# Demo modunu başlat
python run_demo.py

# Çıktı:
# 🎯 Demo modu başlatılıyor...
# ✅ Demo kullanıcı girişi başarılı
# ✅ Demo strateji eklendi
# 📊 Market connector simülasyonu başlatılıyor...
# 🚀 Demo işlem başlatılıyor...
```

Demo modu:
- Gerçek para kullanmaz
- Simüle edilmiş market verisi
- Otomatik strateji çalıştırması
- Gerçek zamanlı sinyal üretimi

### 2. Sunucu + İstemci Kullanımı

**Terminal 1 - Sunucu:**
```bash
python run_server.py
```

**Terminal 2 - İstemci:**
```bash
python run_client.py --mode cli
```

## Sunucu Modu

### Başlatma Seçenekleri

```bash
# Varsayılan ayarlarla
python run_server.py

# Özel port ile
python main.py --mode server --port 8080

# Debug modu ile
python main.py --mode server --log-level DEBUG

# Özel konfigürasyon ile
python main.py --mode server --config my_config.yaml
```

### Sunucu Durumu Kontrolü

```bash
# Sağlık kontrolü
curl http://localhost:8000/health

# Sistem durumu (giriş gerekli)
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/status
```

### API Dokümantasyonu

Sunucu çalışırken otomatik API dokümantasyonu:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## İstemci Kullanımı

### CLI İstemci

#### Giriş Yapma
```bash
moonlight> login
E-posta: demo@example.com
Şifre: demo123
Broker (varsayılan: demo): demo
Demo hesap? (E/h, varsayılan: E): E
```

#### Temel Komutlar
```bash
# Yardım
moonlight> help

# Sistem durumu
moonlight> status

# İşlem başlatma
moonlight> start EURUSD,GBPUSD,USDJPY

# İşlem durdurma
moonlight> stop

# Strateji listesi
moonlight> strategies

# Risk raporu
moonlight> risk

# İşlem geçmişi
moonlight> history 20

# WebSocket bağlantısı
moonlight> connect
moonlight> subscribe market_data,trade_signals

# Çıkış
moonlight> exit
```

### GUI İstemci

```bash
# GUI istemcisini başlat
python run_client.py --mode gui
```

GUI özellikleri:
- **Giriş Sekmesi**: Kullanıcı kimlik doğrulama
- **İşlem Sekmesi**: İşlem kontrolü ve WebSocket
- **Stratejiler Sekmesi**: Strateji yönetimi
- **Risk Sekmesi**: Risk raporları
- **Geçmiş Sekmesi**: İşlem geçmişi
- **Loglar Sekmesi**: Sistem logları

## API Referansı

### Kimlik Doğrulama

#### Giriş
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "demo123",
    "broker": "demo",
    "demo_account": true
  }'
```

**Yanıt:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "message": "Giriş başarılı",
  "session_info": {
    "email": "demo@example.com",
    "broker": "demo",
    "demo_account": true,
    "expires_at": "2024-01-01T13:00:00"
  }
}
```

#### Çıkış
```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### İşlem Yönetimi

#### İşlem Başlatma
```bash
curl -X POST http://localhost:8000/trading/start \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '["EURUSD", "GBPUSD", "USDJPY"]'
```

#### İşlem Durdurma
```bash
curl -X POST http://localhost:8000/trading/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Veri Sorgulama

#### İşlem Geçmişi
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/trades/history?limit=50"
```

#### Piyasa Verisi
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/market/data/EURUSD?hours=24"
```

#### Risk Raporu
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/risk/report
```

### WebSocket API

#### Bağlantı
```javascript
const ws = new WebSocket('ws://localhost:8001');

// Kimlik doğrulama
ws.send(JSON.stringify({
  type: 'auth',
  token: 'YOUR_JWT_TOKEN'
}));

// Kanallara abone ol
ws.send(JSON.stringify({
  type: 'subscribe',
  channels: ['market_data', 'trade_signals', 'trade_results']
}));
```

#### Mesaj Türleri

**Market Data:**
```json
{
  "type": "market_data",
  "channel": "market_data",
  "data": {
    "symbol": "EURUSD",
    "bid": 1.08450,
    "ask": 1.08452,
    "last": 1.08451,
    "volume": 1500.0,
    "spread": 0.00002,
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

**Trade Signal:**
```json
{
  "type": "trade_signal",
  "channel": "trade_signals",
  "data": {
    "symbol": "EURUSD",
    "direction": "CALL",
    "amount": 10.0,
    "confidence": 0.75,
    "strategy_name": "demo_trend",
    "expiry_time": 60,
    "validation": {
      "approved": true,
      "suggested_amount": 10.0,
      "risk_level": "low"
    }
  }
}
```

## Strateji Geliştirme

### Yeni Strateji Oluşturma

```python
from core.strategy_engine.base_strategy import BaseStrategy, StrategyConfig
from core.market_connector.base_connector import MarketData, TradeSignal
from datetime import datetime

class MyCustomStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        # Özel parametreler
        self.my_parameter = config.parameters.get('my_parameter', 10)
    
    def get_required_history_length(self) -> int:
        return 20  # En az 20 bar gerekli
    
    async def analyze(self, market_data: MarketData) -> Optional[TradeSignal]:
        # Yeterli veri kontrolü
        if len(self.market_data_history[market_data.symbol]) < 20:
            return None
        
        # DataFrame'e dönüştür
        df = self.get_market_data_df(market_data.symbol)
        if df is None or df.empty:
            return None
        
        # Teknik analiz
        df = self.calculate_technical_indicators(df)
        current = df.iloc[-1]
        
        # Sinyal mantığı
        if self._should_buy(current):
            return TradeSignal(
                symbol=market_data.symbol,
                direction="CALL",
                expiry_time=60,
                amount=self.config.risk_per_trade,
                confidence=0.8,
                timestamp=datetime.utcnow(),
                strategy_name=self.config.name
            )
        
        return None
    
    def _should_buy(self, data) -> bool:
        # Özel sinyal mantığı
        return data['rsi'] < 30 and data['ema_5'] > data['ema_20']
```

### Strateji Kaydetme

```python
from core.engine import get_engine

# Strateji konfigürasyonu
config = StrategyConfig(
    name="my_custom_strategy",
    enabled=True,
    risk_per_trade=5.0,
    symbols=["EURUSD", "GBPUSD"],
    parameters={'my_parameter': 15}
)

# Strateji oluştur ve ekle
strategy = MyCustomStrategy(config)
engine = get_engine()
engine.add_strategy(strategy)
```

### Backtest Örneği

```python
import pandas as pd
from datetime import datetime, timedelta

async def backtest_strategy():
    # Geçmiş veri yükle
    data = pd.read_csv('historical_data.csv')
    
    # Strateji oluştur
    strategy = MyCustomStrategy(config)
    
    # Her veri noktası için test et
    for _, row in data.iterrows():
        market_data = MarketData(
            symbol=row['symbol'],
            timestamp=row['timestamp'],
            bid=row['bid'],
            ask=row['ask'],
            last=row['close'],
            volume=row['volume']
        )
        
        signal = await strategy.update_market_data(market_data)
        if signal:
            print(f"Sinyal: {signal.symbol} {signal.direction} @ {signal.timestamp}")
    
    # Sonuçları analiz et
    print(f"Toplam Sinyal: {strategy.state.total_signals}")
    print(f"Başarı Oranı: %{strategy.state.win_rate_percentage:.1f}")
```

## Risk Yönetimi

### Risk Parametreleri

```yaml
risk_management:
  max_daily_loss: 100.0          # Günlük maksimum kayıp ($)
  max_position_size: 10.0        # Maksimum pozisyon boyutu ($)
  max_concurrent_trades: 3       # Maksimum eşzamanlı işlem
  max_daily_trades: 50           # Günlük maksimum işlem sayısı
  stop_loss_percentage: 5.0      # Stop loss yüzdesi
  take_profit_percentage: 10.0   # Take profit yüzdesi
  max_drawdown_percentage: 20.0  # Maksimum drawdown yüzdesi
  risk_per_trade_percentage: 2.0 # İşlem başına risk yüzdesi
```

### Risk Seviyesi İzleme

```python
# Risk durumunu kontrol et
risk_report = engine.risk_manager.get_risk_report()
metrics = risk_report['metrics']

if metrics['risk_level'] == 'critical':
    print("⚠️ KRİTİK RİSK SEVİYESİ!")
    # İşlemleri durdur
    await engine.stop_trading()
elif metrics['current_drawdown'] > 15.0:
    print("⚠️ Yüksek drawdown tespit edildi")
    # Risk parametrelerini azalt
```

### Özel Risk Kuralları

```python
class CustomRiskManager(RiskManager):
    async def validate_trade(self, signal, current_balance):
        # Temel doğrulama
        result = await super().validate_trade(signal, current_balance)
        
        # Özel kurallar
        if signal.symbol == "USDJPY" and current_balance < 500:
            result['approved'] = False
            result['reason'] = "USDJPY için minimum bakiye gerekli"
        
        # Volatilite kontrolü
        if self._is_high_volatility_time():
            result['suggested_amount'] *= 0.5  # Tutarı yarıya indir
            result['warnings'].append("Yüksek volatilite - tutar azaltıldı")
        
        return result
    
    def _is_high_volatility_time(self) -> bool:
        # Piyasa açılış/kapanış saatleri
        from datetime import datetime
        hour = datetime.utcnow().hour
        return hour in [8, 9, 13, 14, 21, 22]  # UTC
```

## İleri Seviye Kullanım

### Çoklu Strateji Yönetimi

```python
# Farklı strateji türleri
strategies = [
    SimpleTrendStrategy(trend_config),
    MeanReversionStrategy(mr_config),
    BreakoutStrategy(bo_config)
]

# Stratejileri ekle
for strategy in strategies:
    engine.add_strategy(strategy)

# Strateji performansını karşılaştır
for name, strategy in engine.strategies.items():
    perf = await engine.data_manager.get_strategy_performance(name, days=30)
    print(f"{name}: ROI %{perf.get('roi_percentage', 0):.1f}")
```

### Özel Market Connector

```python
from core.market_connector.base_connector import BaseConnector

class MyBrokerConnector(BaseConnector):
    async def connect(self) -> bool:
        # Broker API'sine bağlan
        self.api_client = MyBrokerAPI(self.config)
        return await self.api_client.connect()
    
    async def authenticate(self, credentials) -> bool:
        # Kimlik doğrulama
        return await self.api_client.login(
            credentials['email'], 
            credentials['password']
        )
    
    async def subscribe_market_data(self, symbols) -> bool:
        # Piyasa verisi aboneliği
        for symbol in symbols:
            await self.api_client.subscribe(symbol, self._on_price_update)
        return True
    
    async def place_trade(self, signal) -> Dict[str, Any]:
        # İşlem açma
        result = await self.api_client.place_order(
            symbol=signal.symbol,
            direction=signal.direction,
            amount=signal.amount,
            expiry=signal.expiry_time
        )
        return result
```

### Performans İzleme

```python
# Detaylı performans analizi
async def analyze_performance():
    # Strateji performansı
    for strategy_name in engine.strategies.keys():
        perf = await engine.data_manager.get_strategy_performance(
            strategy_name, days=30
        )
        
        print(f"\n📊 {strategy_name} Performansı (30 gün):")
        print(f"  Toplam İşlem: {perf['total_trades']}")
        print(f"  Kazanan İşlem: {perf['winning_trades']}")
        print(f"  Kazanma Oranı: %{perf['win_rate']:.1f}")
        print(f"  Net P&L: ${perf['net_pnl']:.2f}")
        print(f"  ROI: %{perf['roi_percentage']:.1f}")
    
    # Risk metrikleri
    risk_report = engine.risk_manager.get_risk_report()
    print(f"\n⚠️ Risk Durumu:")
    print(f"  Güncel Drawdown: %{risk_report['metrics']['current_drawdown']:.1f}")
    print(f"  Risk Seviyesi: {risk_report['metrics']['risk_level'].upper()}")
```

### Otomatik Yedekleme

```python
import schedule
import time

def backup_system():
    # Veritabanı yedeği
    engine.data_manager.create_backup()
    
    # Konfigürasyon yedeği
    shutil.copy('config/config.yaml', f'backups/config_{datetime.now().strftime("%Y%m%d")}.yaml')
    
    print("✅ Sistem yedeği oluşturuldu")

# Her gün saat 02:00'da yedek al
schedule.every().day.at("02:00").do(backup_system)

# Yedekleme görevini çalıştır
while True:
    schedule.run_pending()
    time.sleep(60)
```

### Monitoring ve Alerting

```python
import smtplib
from email.mime.text import MIMEText

class AlertManager:
    def __init__(self, email_config):
        self.email_config = email_config
    
    async def check_system_health(self):
        # Sistem sağlığını kontrol et
        status = engine.get_status()
        
        if status['state'] == 'error':
            await self.send_alert("Sistem Hatası", "MoonLight AI'da hata tespit edildi")
        
        # Risk kontrolü
        risk = engine.risk_manager.get_risk_report()
        if risk['metrics']['risk_level'] == 'critical':
            await self.send_alert("Kritik Risk", f"Drawdown: %{risk['metrics']['current_drawdown']:.1f}")
    
    async def send_alert(self, subject, message):
        # E-posta gönder
        msg = MIMEText(message)
        msg['Subject'] = f"MoonLight AI Alert: {subject}"
        msg['From'] = self.email_config['from']
        msg['To'] = self.email_config['to']
        
        with smtplib.SMTP(self.email_config['smtp_server']) as server:
            server.send_message(msg)
```

## En İyi Uygulamalar

### 1. Güvenlik
- Güçlü şifreler kullanın
- JWT secret'larını düzenli değiştirin
- HTTPS kullanın (üretim ortamında)
- API rate limiting uygulayın

### 2. Risk Yönetimi
- Küçük pozisyonlarla başlayın
- Drawdown limitlerini aşmayın
- Çeşitlendirme yapın (farklı semboller/stratejiler)
- Demo hesapta test edin

### 3. Performans
- Log seviyesini optimize edin
- Veritabanı bakımını düzenli yapın
- Sistem kaynaklarını izleyin
- Gereksiz verileri temizleyin

### 4. İzleme
- Sistem durumunu düzenli kontrol edin
- Performans metriklerini takip edin
- Hata loglarını inceleyin
- Yedekleme stratejisi uygulayın