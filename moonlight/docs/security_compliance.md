# Güvenlik ve Uyumluluk

## 🔐 Güvenlik İlkeleri

### 1. Kimlik Bilgisi Yönetimi

**Saklama:**
- ✅ Windows DPAPI/Credential Manager
- ✅ Bellek-içinde AES-256-GCM şifreleme
- ✅ Disk üzerinde plaintext YOK

**Kullanım:**
```python
import keyring

# Kaydet (bir kez)
keyring.set_password("moonlight-olymp", "user@example.com", "password")

# Oku (çalışma zamanında)
password = keyring.get_password("moonlight-olymp", "user@example.com")
```

**Rotasyon:**
- Minimum 90 günde bir
- Olay sonrası acil rotasyon
- Audit trail zorunlu

### 2. API Güvenliği

**Loopback-Only:**
```yaml
api:
  host: 127.0.0.1  # Yalnız yerel erişim
  http_port: 8750
  ws_port: 8751
  cors_enabled: false
```

**Opsiyonel API Key:**
```yaml
api:
  api_key: "your-secret-key-here"
```

Header kullanımı:
```bash
curl -H "X-API-Key: your-secret-key-here" http://127.0.0.1:8750/status
```

### 3. PII (Kişisel Veri) Koruması

**Otomatik Maskeleme:**
- E-posta: `a***r@d***.com`
- Telefon: `+90******12`
- Token: SHA256 hash (ilk 8 karakter)

**Loglarda PII YOK:**
```python
# YANLIŞ
logger.info("login", f"User {email} logged in")

# DOĞRU
from moonlight.core.telemetry import mask_email
logger.info("login", "User logged in", username_mask=mask_email(email))
```

### 4. Veri Şifreleme

**At-Rest:**
- SQLite: OS disk şifreleme (BitLocker önerilir)
- Opsiyonel: Kolon-seviye şifreleme

**In-Transit:**
- Varsayılan: Loopback (şifreleme gerekmez)
- Remote erişim: TLS 1.2+ zorunlu

## 📜 Platform Uyumluluğu (TOS)

### ✅ İzinli Kullanım

1. **Resmî API**: Yalnız platform tarafından yayımlanmış/belgelenmiş uçlar
2. **Kendi Hesaplar**: Sadece size ait hesaplara erişim
3. **Rate-Limit Uyumu**: Platform limitlerini aşmama
4. **2FA/OTP**: Kullanıcı manuel girer, bypass YOK

### ❌ Yasak Davranışlar

1. **Anti-bot Atlatma**: CAPTCHA/bot algılama mekanizmalarını aşma
2. **Scraping**: Sayfa otomasyonu, veri kazıma
3. **2FA Bypass**: OTP/SMS'i otomatik çekme
4. **Yetkisiz Erişim**: Başkasının hesabına giriş
5. **Rate-Limit Aşımı**: Zorla istek gönderme

### 📋 Uyum Kontrol Listesi

- [ ] Platform TOS okundu ve anlaşıldı
- [ ] Yalnız kendi hesaplarınıza erişiyorsunuz
- [ ] İzinli API endpoint'leri kullanıyorsunuz
- [ ] 2FA/OTP manuel giriyorsunuz
- [ ] Rate-limit'lere uyuyorsunuz
- [ ] Yerel mevzuat kontrolü yapıldı

## 🇹🇷 KVKK Uyumu

### Veri Minimizasyonu
- Yalnız gerekli veriler toplanır
- PII minimum düzeyde
- Hesap kimliği → maskeli ID

### Saklama Süreleri
```yaml
logging:
  retention_days: 14     # Log dosyaları

storage:
  retention_days: 180    # İşlem kayıtları
```

### Unutulma Hakkı

Kullanıcı talebi üzerine:
```bash
# Veri silme
python -m moonlight.tools.gdpr_delete --account acc1 --confirm
```

## 🛡️ Guardrails ve Limitler

### Zorunlu Korumalar

1. **Kill Switch**: Tek tık durdur
```yaml
# API
POST /killswitch {"open": true}
```

2. **Circuit Breaker**: Otomatik durdurma
```yaml
limits:
  max_consecutive_losses: 5
  cb_cooldown_sec: 600
```

3. **Daily Loss Cap**: Günlük limit
```yaml
limits:
  max_daily_loss: 5.0  # Tutar birimi
```

4. **Concurrency**: Tek işlem kuralı
```yaml
# Otomatik: Aynı (account, product, TF) için max 1
```

## 🔍 Audit ve İzlenebilirlik

### Tüm Kararlar Kayıt Altında

```json
{
  "time": "2025-10-10T10:30:00Z",
  "event": "router.decision",
  "decision": "order",
  "reason": "permit_ok_threshold_passed",
  "ctx": {
    "account": "acc#1",
    "product": "EURUSD",
    "payout": 90.0,
    "p_hat": 0.73,
    "win_needed": 0.55
  }
}
```

### Destek Paketi

Olay incelemesi için:
```bash
POST /api/support-pack
```

İçerik:
- ✅ Log (PII maskeli)
- ✅ Metrik snapshot
- ✅ Konfig özeti (sırlar çıkarılmış)
- ✅ Sistem bilgisi
- ❌ Parola/token YOK

## 🚨 Olay Yanıtı

### SEV-1: Kritik (Finansal Risk)

**Aksiyon (15 dakika içinde):**
1. Kill Switch ON
2. Destek paketi al
3. Log incele
4. Geçici çözüm (rollback/config)

### SEV-2: Yüksek (Kalite Bozulması)

**Aksiyon (1 saat içinde):**
1. Circuit Breaker kontrol
2. Metrik analizi
3. Parametre düzeltmesi

## 🔒 Secure Development

### Pre-commit Checks
```bash
# Secret scanning
pip install detect-secrets
detect-secrets scan --baseline .secrets.baseline

# PII check
ruff check --select PII

# Dependency audit
pip-audit
```

### Code Review Checklist
- [ ] Yeni API uç noktası izinli mi?
- [ ] Log'larda PII yok mu?
- [ ] Secret plaintext saklanmıyor mu?
- [ ] Rate-limit uyumu var mı?
- [ ] Fail-closed davranış doğru mu?

## 📞 İhlal Bildirimi

Güvenlik açığı tespit ederseniz:
1. **Hemen durdur**: Kill Switch
2. **İzole et**: Ağ bağlantısını kes
3. **Belge**: Destek paketi + screenshot
4. **Rapor**: security@moonlight.local

## 🎓 Eğitim Materyalleri

### Yeni Operatör

1. Güvenlik ve uyumluluk eğitimi (1 saat)
2. Kill Switch ve guardrail tatbikatı
3. Destek paketi oluşturma pratiği
4. Log/metrik yorumlama

### Yeni Geliştirici

1. Secure coding guidelines
2. PII/secret handling
3. TOS ve yasal sınırlar
4. Code review süreci

---

## ⚖️ Yasal Uyarı

**ÖNEMLİ:**

Bu yazılım eğitim ve araştırma amaçlıdır. Kullanıcı:
- Platform hizmet şartlarına uymakla yükümlüdür
- Yerel finans mevzuatını takip etmelidir
- Kendi hesap güvenliğinden sorumludur
- Yazılım yatırım tavsiyesi vermez
- Sonuçlar garanti edilmez

**Kullanım riskleri kullanıcıya aittir.**

---

**MoonLight** - Güvenlik ve uyumluluk öncelikli tasarım.
