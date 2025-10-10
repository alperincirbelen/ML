# 🤝 Katkıda Bulunma Rehberi

MoonLight projesine katkıda bulunmak istediğiniz için teşekkürler!

## 📋 İçindekiler

1. [Kod Standartları](#kod-standartları)
2. [Geliştirme Süreci](#geliştirme-süreci)
3. [Test Gereksinimleri](#test-gereksinimleri)
4. [Dokümantasyon](#dokümantasyon)
5. [Pull Request Süreci](#pull-request-süreci)

## Kod Standartları

### Python Style Guide

- **PEP 8** standardını takip edin
- **Black** formatter kullanın
- **Type hints** ekleyin
- **Docstrings** yazın (Google style)

```bash
# Format
black moonlight/

# Lint
ruff check moonlight/

# Type check
mypy moonlight/
```

### Adlandırma Kuralları

- **Modüller**: `snake_case.py`
- **Sınıflar**: `PascalCase`
- **Fonksiyonlar**: `snake_case()`
- **Sabitler**: `UPPER_CASE`
- **Private**: `_leading_underscore`

### İmportlar

```python
# 1. Standart kütüphane
import os
import sys
from typing import Optional

# 2. Üçüncü taraf
import pandas as pd
import numpy as np

# 3. Lokal
from ..config import AppConfig
from .models import Order
```

## Geliştirme Süreci

### 1. Fork ve Clone

```bash
# Fork edin (GitHub'da)
# Sonra clone
git clone https://github.com/YOUR_USERNAME/moonlight.git
cd moonlight
```

### 2. Branch Oluştur

```bash
# Feature branch
git checkout -b feature/my-new-feature

# Bugfix branch
git checkout -b fix/issue-123
```

### 3. Geliştirme Ortamı

```bash
# Virtual environment
python -m venv venv
venv\Scripts\activate

# Dependencies
pip install -r requirements.txt

# Dev dependencies
pip install pytest pytest-asyncio black ruff mypy
```

### 4. Değişikliklerinizi Yapın

- Küçük, odaklı commit'ler
- Açıklayıcı commit mesajları
- Test ekleyin

## Test Gereksinimleri

### Unit Tests

Her yeni fonksiyon için test yazın:

```python
# tests/test_my_module.py
import pytest

def test_my_function():
    result = my_function(input)
    assert result == expected
```

### Test Çalıştırma

```bash
# Tüm testler
pytest tests/ -v

# Belirli test
pytest tests/test_config.py -v

# Coverage
pytest --cov=moonlight.core tests/
```

### Minimum Kapsam
- **Kritik modüller**: %85+
- **Genel**: %70+

## Dokümantasyon

### Docstrings

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Kısa açıklama (tek satır)
    
    Detaylı açıklama (gerekirse).
    
    Args:
        param1: İlk parametre açıklaması
        param2: İkinci parametre açıklaması
    
    Returns:
        Dönüş değeri açıklaması
    
    Raises:
        ValueError: Ne zaman hata fırlatır
    """
    pass
```

### README Güncellemeleri

Yeni özellik eklediyseniz README'yi güncelleyin:

- Özellikler listesi
- Kullanım örnekleri
- Konfigürasyon seçenekleri

## Pull Request Süreci

### 1. Hazırlık

```bash
# Testler geçiyor mu?
pytest tests/

# Lint temiz mi?
ruff check moonlight/

# Format OK mi?
black --check moonlight/
```

### 2. Commit

```bash
git add .
git commit -m "feat: Add my new feature"

# Commit mesaj formatı:
# feat: Yeni özellik
# fix: Hata düzeltme
# docs: Dokümantasyon
# test: Test ekleme
# refactor: Kod iyileştirme
# style: Format değişikliği
```

### 3. Push

```bash
git push origin feature/my-new-feature
```

### 4. Pull Request Oluştur

GitHub'da PR açın:

**Başlık**: `[Feature] Kısa açıklama`

**Açıklama şablonu**:
```markdown
## Değişiklikler
- Değişiklik 1
- Değişiklik 2

## Test
- [ ] Unit testler eklendi
- [ ] Integration testler geçti
- [ ] Smoke test başarılı

## Dokümantasyon
- [ ] Docstrings eklendi
- [ ] README güncellendi
- [ ] Örnek kullanım eklendi

## Checklist
- [ ] Code review istendi
- [ ] Conflicts çözüldü
- [ ] CI/CD geçti
```

### 5. Code Review

- En az 1 onay gerekli
- Değişiklik istekleri varsa güncelleyin
- Tartışmalara katılın

## Özel Konular

### Yeni Strateji Ekleme

1. `core/strategies/providers/` altında dosya oluştur
2. `@register(ID)` ile kaydet (benzersiz ID)
3. `StrategyProvider` protocol'ünü uygula
4. Test ekle
5. `docs/STRATEGIES.md`'ye ekle

### Yeni İndikatör Ekleme

1. `core/indicators/` altına ekle (basic veya advanced)
2. Pandas/NumPy ile vektörize et
3. Warmup ve NaN handling
4. Doğruluk testi ekle (bilinen veri ile)
5. Performans testi (p90 < 5 ms hedef)

### API Endpoint Ekleme

1. `core/api/server.py`'de endpoint tanımla
2. OpenAPI docs otomatik üretilir
3. Security (localhost, rate-limit) kontrol et
4. Integration test ekle

## Code Review Kriterleri

### Zorunlu
- [ ] Testler var ve geçiyor
- [ ] Lint/format temiz
- [ ] Type hints eklenmiş
- [ ] Docstrings var
- [ ] PII masking kontrol edildi
- [ ] Fail-closed davranış doğrulandı

### Önerilen
- [ ] Performans ölçümü yapıldı
- [ ] Edge case'ler test edildi
- [ ] Backward compatibility korundu
- [ ] Security implications değerlendirildi

## İletişim

### Soru ve Tartışma
- **GitHub Discussions**: Genel sorular
- **GitHub Issues**: Hata raporları ve öneriler

### Kod Yorumları
- Karmaşık mantık için yorum ekleyin
- "Neden?" sorusunu yanıtlayın (nasıl değil)
- TODO/FIXME/HACK etiketleri kullanın

### Commit Mesajları

İyi ✅:
```
feat: Add Supertrend+ADX strategy (ID: 25)

- Implements Supertrend indicator with ADX filter
- Configurable threshold and multiplier
- Tests included with 92% coverage
```

Kötü ❌:
```
update
```

## Lisans

Katkılarınız proje lisansı altında yayınlanacaktır.

## Davranış Kuralları

- Saygılı olun
- Yapıcı eleştiri
- Yardımcı olun
- Öğrenmeye açık olun

---

**Teşekkürler!** Her katkı, MoonLight'ı daha iyi yapar. 🌙
