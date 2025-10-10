# 🔧 Operasyon Kılavuzu

## Günlük Kontroller (3 dakika)

### Sabah Rutini

1. **Servis Durumu**
   ```bash
   curl http://127.0.0.1:8750/status
   ```
   - `state`: "running" olmalı
   - `workers`: Beklenen sayıda

2. **Hesaplar**
   ```bash
   curl http://127.0.0.1:8750/accounts
   ```
   - Tüm hesaplar `connected` olmalı

3. **Kill-Switch ve Circuit Breaker**
   - Kill-Switch: `false` olmalı
   - CB state: `CLOSED` olmalı (OPEN değil)

4. **Loglar**
   ```bash
   tail -n 50 data/logs/moonlight.log
   ```
   - ERROR seviyesi log var mı?
   - 429/5xx fırtınası var mı?

5. **Disk Alanı**
   - `data/` klasörü < %80 dolu olmalı

## Başlatma / Durdurma

### Başlatma

```bash
# 1. Konfigürasyonu kontrol et
notepad configs/config.yaml

# 2. Veritabanını kontrol et (ilk kez ise)
python -c "import asyncio; from moonlight.core.storage import init_database; asyncio.run(init_database('data/db/moonlight.db'))"

# 3. Core engine başlat
python -m moonlight.core.main configs/config.yaml
```

### Durdurma

```bash
# Soft stop (API ile)
curl -X POST http://127.0.0.1:8750/stop

# Hard stop (Ctrl+C veya Kill-Switch)
curl -X POST http://127.0.0.1:8750/killswitch -H "Content-Type: application/json" -d '{"enabled": true}'
```

## Olay Yönetimi (Incidents)

### P0: Kritik - Emir hattı durdu

**Belirti:**
- `orders_total` artmıyor
- `router_rounds_total` artıyor
- Dashboard sessiz

**Kontrol:**
```bash
curl http://127.0.0.1:8750/metrics
```

**Aksiyon:**
1. Kill-Switch ON → `/killswitch {"enabled": true}`
2. Logları incele → `data/logs/moonlight.log`
3. Guard rejects kontrol → `guard_reject_total{reason}`
4. Nedene göre:
   - `permit_window` → Permit aralığını genişlet
   - `cb_open` → Circuit breaker resetle
   - `daily_cap` → Risk limitlerini gözden geçir

### P1: 429 Rate Limit Fırtınası

**Belirti:**
- `connector_calls_total{outcome="temp_err"}` artıyor
- Logda "429" mesajları

**Aksiyon:**
1. Paralel limitleri düşür:
   ```yaml
   limits:
     max_parallel_global: 2  # Düşür
     max_parallel_per_account: 1
   ```
2. Restart
3. 10 dakika izle

### P2: Yüksek Gecikme

**Belirti:**
- `order_latency_ms.p90` > 2000 ms

**Aksiyon:**
1. Worker sayısını azalt
2. TF=1 işlemleri geçici durdur
3. Ağ bağlantısını kontrol et

### P3: Günlük Kayıp Limiti

**Belirti:**
- `pnl_day{account}` negatif ve limite yakın
- `guard_reject_total{reason="daily_cap"}` artıyor

**Aksiyon:**
1. Otomatik dur (guardian aktifse)
2. Günün işlemlerini incele
3. Parametreleri gözden geçir
4. Yarın için limit ayarla

## Bakım

### Günlük Yedek

```bash
# Manuel yedek
copy data\db\moonlight.db data\backups\moonlight_%date%.db

# Otomatik (Windows Task Scheduler ile kurulabilir)
```

### Log Rotasyonu

Otomatik (10 MB, 7 dosya). Manuel temizlik:

```bash
del /Q data\logs\moonlight.log.*
```

### Veritabanı Bakımı

```bash
# Haftalık VACUUM (SQLite optimize)
sqlite3 data\db\moonlight.db "VACUUM;"

# Integrity check
sqlite3 data\db\moonlight.db "PRAGMA integrity_check;"
```

## Monitoring Komutları

### API Endpoints

```bash
# Durum
curl http://127.0.0.1:8750/status

# Hesaplar
curl http://127.0.0.1:8750/accounts

# Worker'lar
curl http://127.0.0.1:8750/workers

# Son işlemler
curl http://127.0.0.1:8750/orders?limit=20

# Metrikler
curl http://127.0.0.1:8750/metrics
```

### Loglar

```bash
# Son 100 satır
tail -n 100 data/logs/moonlight.log

# ERROR seviyesi
findstr "ERROR" data\logs\moonlight.log

# Belirli hesap
findstr "acc1" data\logs\moonlight.log
```

### Veritabanı Sorguları

```bash
# SQLite aççık shell
sqlite3 data\db\moonlight.db
```

```sql
-- Son 20 işlem
SELECT * FROM v_trades ORDER BY ts_open_ms DESC LIMIT 20;

-- Günlük PnL
SELECT * FROM v_daily_pnl ORDER BY trade_date DESC LIMIT 7;

-- Win rate (son 100)
SELECT 
  AVG(CASE WHEN status='win' THEN 1.0 WHEN status='lose' THEN 0.0 END) as winrate
FROM results r
JOIN orders o ON o.id = r.order_id
WHERE r.status IN ('win', 'lose')
ORDER BY r.ts_close_ms DESC
LIMIT 100;

-- Ret nedenleri
SELECT reason, COUNT(*) as cnt
FROM trade_skips
WHERE ts_ms > (strftime('%s','now')*1000 - 86400000)
GROUP BY reason
ORDER BY cnt DESC;
```

## Güvenlik

### Parola Yönetimi

```python
# Windows Credential Manager ile saklama
import keyring

# Kaydet (ilk kurulumda)
keyring.set_password("moonlight-olymp", "user@example.com", "PASSWORD")

# Oku (uygulama tarafından)
password = keyring.get_password("moonlight-olymp", "user@example.com")
```

### PII Maskeleme

Loglar otomatik olarak maskeler:
- E-posta: `a***@***`
- Telefon: `+**********`
- Token: Hiç görünmez

## Sorun Giderme

### "İşlem açılmıyor"

```bash
# 1. Son kararları kontrol
curl http://127.0.0.1:8750/metrics | grep decision

# 2. Skip nedenlerini bak
sqlite3 data/db/moonlight.db "SELECT reason, COUNT(*) FROM trade_skips GROUP BY reason;"

# 3. Konfig kontrol
# - permit_min/max uygun mu?
# - win_threshold çok yüksek mi?
# - trade_enabled=true mi?
```

### "Yüksek CPU kullanımı"

1. Worker sayısını azalt
2. Indicator hesaplamalarını optimize et
3. Log seviyesini INFO'ya düşür (DEBUG değil)

### "Veritabanı kilidi"

```bash
# WAL checkpoint
sqlite3 data/db/moonlight.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

## Performance Tuning

### Düşük Gecikme İçin

```yaml
engine:
  tick_interval_ms: 500  # Artır (250 → 500)
  lookback: 200  # Azalt (300 → 200)

limits:
  max_parallel_global: 2  # Azalt
```

### Yüksek Throughput İçin

```yaml
engine:
  queue_maxsize: 5000  # Artır

limits:
  max_parallel_global: 8  # Artır (dikkatli!)
  rate_limit_per_min: 120  # Artır
```

## Upgrade / Rollback

### Upgrade

```bash
# 1. Yedek al
copy data\db\moonlight.db data\backups\pre_upgrade_%date%.db

# 2. Kodu güncelle
git pull origin main

# 3. Bağımlılıkları güncelle
pip install -r requirements.txt --upgrade

# 4. Test
python tests/smoke_test.py

# 5. Başlat
python -m moonlight.core.main configs/config.yaml
```

### Rollback

```bash
# 1. Durdur
# Ctrl+C veya API /stop

# 2. Kodu geri al
git checkout <previous-commit>

# 3. Veritabanını geri yükle
copy data\backups\pre_upgrade_*.db data\db\moonlight.db

# 4. Başlat
python -m moonlight.core.main configs/config.yaml
```

## Destek Paketi

Hata raporlama için:

```bash
# Loglar + config + metrics
mkdir support_package
copy data\logs\moonlight.log support_package\
copy configs\config.yaml support_package\config_redacted.yaml
curl http://127.0.0.1:8750/metrics > support_package\metrics.json

# ZIP oluştur
tar -czf support_%date%.zip support_package\
```

**Önemli**: `config_redacted.yaml`'dan parolaları çıkarın!

## Checklist

### Canlıya Geçiş Öncesi (Paper → Live)

- [ ] Paper mode en az 1000 işlem
- [ ] Win rate ≥ hedef (%70+)
- [ ] Max drawdown kontrollü
- [ ] Kill-Switch test edildi
- [ ] Limitler doğru ayarlandı
- [ ] Yedek alındı
- [ ] `trade_enabled=true` yapıldı
- [ ] İlk işlemi yakın izle

---

**Acil Durum**: Her zaman Kill-Switch hazır tutun!
