# 2. Hukuk, Uyumluluk ve Etik (Ön Koşullar)

## 2.1 Hukuki & Platform Uyum İlkeleri

### 2.1.1 Kendi Hesapların
- Yalnızca sana ait Olymp Trade hesaplarına erişim
- Üçüncü taraf hesabı erişimi yok
- Hesap sahipliği doğrulaması gerekli

### 2.1.2 Çoklu Hesap (4 Oturum)
- Teknik olarak desteklenir
- Platform Hizmet Şartları (TOS) uygunluğu kullanıcı sorumluluğundadır
- Aynı kişi adına birden fazla hesap kullanımı platform kurallarına uygun olmalı

### 2.1.3 İzinli Erişim
- Sadece resmî/izinli API/kanallar kullanılır
- Anti bot atlatma, tersine mühendislik yok
- Platform güvenlik önlemlerini atlatma yasak

### 2.1.4 Finansal Uyarı
- Sonuçlar garanti değildir
- Yazılım yatırım tavsiyesi vermez
- Kullanıcı kendi riskini üstlenir

## 2.2 Kimlik & Oturum Güvenliği

### 2.2.1 Parola Kasası
- Windows DPAPI/keyring kullanımı
- Config'te parola yok, yalnız keyring_service + username tutulur
- Şifreler disk üzerinde AES-GCM ile ek şifreleme

### 2.2.2 Token Yaşam Döngüsü
- Kısa ömürlü erişim token'ları + refresh
- Hesap başına profiles/accX/ altında şifreli saklama
- Token/çerezler loglanmaz

### 2.2.3 2FA/OTP (Opsiyonel)
- Şu an kapalı; gerektiğinde UI modalıyla TOTP/SMS/e-posta tek seferlik kod girişi
- Kodlar loglanmaz, bellekte geçici
- OTP timeout ve retry mekanizmaları

### 2.2.4 Oturum İzolasyonu
- Her hesap için ayrı HTTP/WS oturumu
- Çerez/jar ve header seti ayrı
- Session locking ile karışma önlenir

## 2.3 Ağ Güvenliği

### 2.3.1 TLS Zorunlu
- Sertifika doğrulaması açık
- Downgrade engeli
- TLS 1.2+ zorunlu

### 2.3.2 Host Allow List
- Yanlış yönlendirmeyi azaltmak için isteğe bağlı alan adı sabitleme
- Sadece güvenilir broker API'leri

### 2.3.3 Rate Limit Uyumu
- Exponential backoff + jitter
- Gereksiz istek yok
- Kalp atışı (heartbeat) aralığı sınırlandırılmış

### 2.3.4 Loopback Erişimi
- UI↔Core iletişimi localhost üzerinden
- Windows Firewall allow list kuralı
- Dış ağdan erişim yok

## 2.4 Loglama & Gizlilik

### 2.4.1 PII Redaksiyonu
- Kullanıcı adı/e-posta/token/OTP maskeleme
- Loglara düşmez
- Hash (sha256:...) veya mask kullanımı

### 2.4.2 Yapılandırılmış Log
- JSON log formatı
- Ayrı kanallar → trade.log (işlem olayları), system.log (servis ve hatalar)
- Structured logging ile makine okunabilir

### 2.4.3 Rotasyon
- Boyut/süre bazlı rotating
- Maksimum dosya adedi UI'dan ayarlanabilir
- Arşivler sıkıştırılır (.gz)

## 2.5 Ayrıcalık ve Erişim İlkeleri

### 2.5.1 En Az Ayrıcalık
- Core yalnız gerekli dosya/portlara erişir (loopback)
- Yönetici hakları gerekmez
- Minimal sistem izinleri

### 2.5.2 Profil Ayrımı
- account_id alanı tüm tablolarda zorunlu
- İstenirse her hesap için ayrı DB dosyası
- Veri izolasyonu garantisi

### 2.5.3 Config Değişimi
- UI'dan onaylı değişiklik
- Kritik alanlarda atomik devreye alma
- Hot reload ya da kontrollü restart

## 2.6 Hata, Retry ve Güvenli Durma

### 2.6.1 Idempotent Emir
- client_request_id ile çift emir önleme
- Durum makinesi: PREPARE → SEND → CONFIRM → (SETTLED | ABORT)
- At-most-once gönderim kuralı

### 2.6.2 Retry Politikası
- Sadece ağ/5xx sınıfı
- Finansal yan etkili noktalarda tekrar yok
- Exponential backoff + jitter

### 2.6.3 Fail Safe
- Bağlantı kopması, latency sapması, veri tutarsızlığı tespitinde otomatik durdurma
- Kullanıcı uyarısı
- Güvenli durma modu

## 2.7 Guardrails (Bariyerler)

### 2.7.1 Kill Switch / Panic
- UI'da tek tıkla tüm emir süreçlerini durdur
- Acil durum çıkışı
- Manuel kontrol

### 2.7.2 Circuit Breaker
- Günlük kayıp ≥ limit → durdur
- Ardışık kayıp ≥ limit → durdur + cool down artır
- Permit penceresi dışı payout/win rate → yeni işlem yok
- Latency > abort_ms → yeni işlem engeli

### 2.7.3 Concurrency Kuralı
- (hesap, ürün, TF) başına tek açık işlem
- 1/5/15 bağımsız
- Re-entrancy lock

### 2.7.4 Paralellik Sınırları
- Kullanıcı belirler
- Belirlenmemişse core "paper/gözlem" modunda kalır
- Global ve hesap bazında sınırlar

## 2.8 Tedarik Zinciri Güvenliği & Güncelleme

### 2.8.1 İmzalı Paket
- Kurulum ve güncellemeler kod imzalı
- Güvenilir dağıtım
- Sahte paket koruması

### 2.8.2 Bağımlılıklar
- requirements.txt sabit sürüm + hash doğrulaması
- SBOM (Software Bill of Materials) opsiyonel
- Güvenlik taraması

### 2.8.3 Sürüm Bütünlüğü
- Release SHA 256 doğrulaması
- İsteğe bağlı GPG imzalı commitler
- Değişiklik takibi

## 2.9 Veri Koruma, Yedek & Arşiv

### 2.9.1 Disk Koruması
- BitLocker önerilir
- Kritik kolonlar için uygulama katmanı şifreleme (ops.)
- Veri şifreleme

### 2.9.2 Yedekleme
- Günlük şifreli .backup
- Anahtar yönetimi kullanıcıda
- Otomatik yedekleme

### 2.9.3 Arşiv
- 90+ gün features satırlarını Parquet arşivine taşı
- DB'yi incelt
- Uzun vadeli saklama

## 2.10 Telemetry & Dışa Veri

### 2.10.1 Varsayılan KAPALI
- Dışa hiçbir telemetry gönderilmez
- Kullanıcı açık izin verirse anonimleştirilmiş metrikler gönderilebilir
- Gizlilik öncelikli

## 2.11 Go Live Kontrol Listesi

- [ ] TOS/yerel mevzuat kontrol edildi (kullanıcı)
- [ ] 4 hesap profili izolasyonu doğrulandı
- [ ] DPAPI/keyring kasası çalışıyor
- [ ] TLS & sertifika doğrulama açık
- [ ] PII redaksiyonu test edildi
- [ ] Kill switch / circuit breaker senaryoları geçti
- [ ] Idempotent emir ve retry/abort akışları test edildi
- [ ] Güncelleme + bağımlılık güvenliği doğrulandı

## 2.12 Kabul Kriterleri

- Güvenlik/uyumluluk ilkeleri uygulanabilir ve test edilebilir durumda
- Çoklu hesap izolasyonu, anahtar kasası, TLS, log gizliliği, guardrails ve idempotent emir akışı tasarlandı
- Paralellik sınırı kullanıcı kontrolünde; set edilmediğinde core'un paper modu davranışı net
