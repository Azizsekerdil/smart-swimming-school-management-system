# Katkı Rehberi / Contributing

Katkılarınız memnuniyetle karşılanır. Bu proje tek kişilik ve **en iyi çaba**
ile sürdürülür; yanıt süresi değişebilir.

Contributions are welcome. This project is maintained by one person on a
best-effort basis, so response times vary.

---

## Başlamadan önce

1. **Güvenlik açıkları için issue açmayın.** [`SECURITY.md`](SECURITY.md)
   dosyasındaki özel bildirim yolunu kullanın.
2. Büyük bir değişikliğe başlamadan önce bir issue açıp yaklaşımı konuşun.
   Reddedilen bir tasarımı kodladıktan sonra öğrenmek kimseyi mutlu etmez.
3. [`docs/known-limitations.md`](docs/known-limitations.md) dosyasını okuyun —
   bir "eksik" bilinçli bir tasarım kararı olabilir.

---

## Geliştirme ortamı

```bash
# Backend
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt   # Windows
# source .venv/bin/activate && pip install -r backend/requirements-dev.txt

cd backend
alembic upgrade head
python -m app.db.seed            # sentetik demo verisi (isteğe bağlı)
python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm ci
npm run dev
```

`.env.example` dosyasını `.env` olarak kopyalayın. **Gerçek bir API anahtarını
asla depoya yazmayın.**

---

## Kalite kapıları

Bir değişiklik birleştirilmeden önce sürekli tümleştirmede şunlar
**bloklayıcı** olarak çalışır:

| Kapı | Komut |
|---|---|
| Python lint | `ruff check .` |
| Python biçim | `black --check .` |
| Python testleri | `pytest tests -q` |
| Migration tutarlılığı | `alembic upgrade head && alembic check` |
| TS tip denetimi | `npm run typecheck` |
| TS lint | `npm run lint` |
| Arayüz derlemesi | `npm run build` |
| Çeviri bütünlüğü (TR ↔ EN) | CI adımı |
| Gizli anahtar taraması (metin) | CI adımı |
| API duman testi (ilk kurulum kapısı dâhil) | CI adımı |

Bilgilendirici (bloklamayan): `mypy`, `pip-audit`. Adı da bunu söyler; sessizce
gizlenen bir kapı yoktur.

Yerelde çalıştırmadan önce:

```bash
cd backend && ruff check . && black --check . && pytest -q
cd ../frontend && npm run typecheck && npm run lint && npm run build
```

---

## Kod tarzı

* **Python:** ruff + black varsayılanları. Tip ipuçları beklenir.
* **TypeScript:** eslint + prettier. `any` kullanmaktan kaçının.
* **Yorumlar** *neden*i anlatır, *ne*yi değil. Kodun kendisi *ne*yi anlatır.
* **Diller:** kullanıcıya görünen metinler TR ve EN olarak **her iki** çeviri
  dosyasına da eklenir; CI eksik anahtarda derlemeyi düşürür.
* Kod içi belgeler ve yorumlar Türkçedir; İngilizce bir özet satırı eklemek
  memnuniyetle karşılanır.

---

## Güvenlik ve gizlilik kuralları (pazarlık dışı)

Bir katkı şunlardan birini yaparsa birleştirilmez:

1. **Gerçek bir sır ekler** — anahtar, parola, belirteç, sertifika.
2. **Gerçek kişisel veri ekler** — ad, telefon, e-posta, kimlik numarası,
   sağlık verisi. Demo verisi sentetik üreteçten gelmelidir.
3. **Aranabilir telefon numarası üretir** — demo numaraları `0000` ön ekiyle
   üretilir ve öyle kalmalıdır.
4. **Bir AI çağrısını gizlilik geçidinin dışına çıkarır.** Bütün sağlayıcı
   çağrıları `services/hsp/gateway.py` üzerinden gider; bunu zorlayan bir test
   vardır ve o testi zayıflatmak bir düzeltme değildir.
5. **Satır bazlı kapsam denetimini kaldırır.** Veli/öğrenci/sporcu rollerine
   açık her yeni uç ya `AccessScope.scope_students(...)` ile süzülmeli, ya
   `assert_student_allowed(...)` ile doğrulanmalı, ya da
   `require_org_wide_scope` ile bu rollere kapatılmalıdır.
6. **İlk kurulum kapısını gevşetir.** `backend/tests/test_bootstrap_admin.py`
   içindeki sözleşme bir davranış tanımıdır.
7. **Bir testi silerek veya zayıflatarak** kırmızıyı yeşile çevirir.

---

## Commit ve PR

* Commit mesajları [Conventional Commits](https://www.conventionalcommits.org/)
  biçimindedir: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
* PR açıklamasında: ne değişti, neden, nasıl doğrulandı.
* Davranış değiştiren her düzeltme bir **regresyon testi** ile gelir.
* Sayısal bir iddia (test sayısı, uç sayısı, tablo sayısı) değiştiyse README
  ve sunum içeriğindeki sayıyı da **ölçerek** güncelleyin; elle tahmin etmeyin.

---

## Lisans

Katkınızı gönderdiğinizde, katkınızın projeyle aynı [MIT](LICENSE) lisansı
altında yayımlanmasını kabul etmiş olursunuz.

By submitting a contribution you agree that it is licensed under the project's
[MIT](LICENSE) licence.
