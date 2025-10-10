# ⚡ Hızlı Başlangıç - 5 Dakikada MoonLight

## 🎯 Hedef

5 dakikada MoonLight'ı çalıştırıp ilk API çağrısını yapmak.

## 📝 Adımlar

### 1. Gereksinimler (30 saniye)

```bash
# Python 3.10+ var mı?
python --version
# ✅ Python 3.10.x veya üzeri olmalı

# Git var mı?
git --version
```

### 2. İndir (30 saniye)

```bash
# Klonla
git clone <repo-url>
cd moonlight

# Veya
# ZIP indir → çıkart → klasöre gir
```

### 3. Kur (2 dakika)

```bash
# Virtual environment
python -m venv venv
venv\Scripts\activate

# Bağımlılıklar
pip install -r requirements.txt
```

### 4. Ayarla (30 saniye)

```bash
# Config kopyala
copy configs\config.example.yaml configs\config.yaml

# Database başlat
python -c "import asyncio; from moonlight.core.storage import init_database; asyncio.run(init_database('data/db/moonlight.db'))"
```

### 5. Çalıştır (30 saniye)

```bash
# Engine başlat
python -m moonlight.core.main configs/config.yaml
```

**Beklenen çıktı**:
```
MoonLight Fixed-Time Trading AI başlatılıyor...
...
Server starting on 127.0.0.1:8750
```

### 6. Test Et (30 saniye)

Yeni terminal:

```bash
# API çağrısı
curl http://127.0.0.1:8750/status
```

**Beklenen**:
```json
{
  "api_version": "1.0",
  "service": {"state": "running", ...},
  "core": {"workers": 0, ...}
}
```

## ✅ Başarılı!

MoonLight çalışıyor! 🎉

## 🚀 Sonraki Adımlar

### A. İlk İşlemi Başlat (Paper Mode)

1. **Config'i düzenle**:
   ```yaml
   features:
     trade_enabled: true  # false → true
   
   products:
     - product: EURUSD
       enabled: true
       strategies: [5]  # EMA+RSI
   ```

2. **Worker başlat**:
   ```bash
   curl -X POST http://127.0.0.1:8750/start
   ```

3. **İzle**:
   ```bash
   # Metrikler
   curl http://127.0.0.1:8750/metrics
   
   # İşlemler
   curl http://127.0.0.1:8750/orders
   ```

### B. Smoke Test Çalıştır

```bash
python tests/smoke_test.py
```

Tüm testler ✅ olmalı.

### C. Dokümantasyonu Oku

- `README.md`: Genel bakış
- `INSTALL.md`: Detaylı kurulum
- `docs/OPERATIONS.md`: Günlük kullanım
- `docs/STRATEGIES.md`: Strateji geliştirme

## 🛟 Sorun mu var?

### "ModuleNotFoundError"
```bash
# Virtual env aktif mi?
venv\Scripts\activate

# Requirements tekrar
pip install -r requirements.txt
```

### "Port already in use"
```yaml
# config.yaml'da port değiştir
ui:
  port: 8751
```

### "Database not found"
```bash
# Klasörler var mı?
mkdir data\db data\logs

# Database init
python -c "import asyncio; from moonlight.core.storage import init_database; asyncio.run(init_database('data/db/moonlight.db'))"
```

### Hâlâ sorun?
```bash
# Logları kontrol
type data\logs\moonlight.log

# Veya smoke test
python tests/smoke_test.py
```

## 📚 Daha Fazla

- **Detaylı Kurulum**: `INSTALL.md`
- **Mimari**: `docs/ARCHITECTURE.md`
- **Operasyon**: `docs/OPERATIONS.md`
- **Katkı**: `CONTRIBUTING.md`

---

**5 dakika bitti!** Artık MoonLight'ı keşfedebilirsiniz. 🌙✨
