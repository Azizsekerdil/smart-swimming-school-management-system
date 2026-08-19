# AI Developer Console ve CAIO — Güvenlik ve Kullanım Kılavuzu

Bu belge, programın içindeki yapay zekâ geliştirici ajanının (AI Developer
Console) ve sistem gözlemcisi CAIO ajanının ne yapabildiğini, neyi kesinlikle
yapamadığını ve bu özellikleri açmadan önce hangi kontrollerin yapılması
gerektiğini anlatır. Temel ilke tek cümledir: **yapay zekâ Windows terminaline
sınırsız erişemez ve hiçbir dosyayı kullanıcı onayı olmadan değiştiremez.**

**Sürüm:** 0.9.0 · **Kaynak:** `backend/app/services/ai/policy.py`,
`backend/app/services/ai/agent.py`, `backend/app/services/ai/caio.py` ·
**Ekranlar:** AI Developer Console (`/ai-developer`, izin `ai:developer`),
CAIO (`/caio`, izin `ai:caio`)

---

## İçindekiler

1. [Amaç ve kapsam](#1-amaç-ve-kapsam)
2. [Güvenlik politikası](#2-güvenlik-politikası)
3. [İş akışı](#3-i̇ş-akışı)
4. [Checkpoint ve geri alma](#4-checkpoint-ve-geri-alma)
5. [Yapılandırma](#5-yapılandırma)
6. [Kullanım örnekleri](#6-kullanım-örnekleri)
7. [Sınırlamalar](#7-sınırlamalar)
8. [CAIO ajanı](#8-caio-ajanı)
9. [Güvenlik denetim listesi](#9-güvenlik-denetim-listesi)

---

## 1. Amaç ve Kapsam

### 1.1 Ajan ne yapar

AI Developer Console, projenin kendi kaynak kodu üzerinde çalışan bir
yardımcıdır. Verilen bir istemi alır, ilgili dosyaları bulur ve okur, bir
plan çıkarır, dosya bazında **tam içerik** öneren bir yama üretir ve size
birim birim **diff** olarak gösterir. Hiçbir şey uygulanmadan önce durur.

| Yetenek | Uç nokta | Açıklama |
|---------|----------|----------|
| Dosya listeleme | `GET /api/v1/ai/developer/files` | Yalnızca `backend/app`, `frontend/src`, `scripts`, `docs`, `backend/tests` altında |
| Dosya okuma | `GET /api/v1/ai/developer/file?path=...` | Politika denetiminden geçer; azami 200 KB |
| Kaynak kodda arama | `GET /api/v1/ai/developer/search?q=...` | Grep benzeri, azami 60 sonuç |
| Plan + yama üretme | `POST /api/v1/ai/developer/plan` | **Hiçbir dosyayı değiştirmez**, yalnızca önizleme üretir |
| Üretilmiş yamaları listeleme | `GET /api/v1/ai/developer/patches` | |
| Yama detayı | `GET /api/v1/ai/developer/patches/{patch_id}` | Yanıt hafif tutulur (`new_content` çıkarılır) |
| Yama uygulama | `POST /api/v1/ai/developer/apply` | `confirm=true` **zorunlu** |
| Checkpoint listeleme | `GET /api/v1/ai/developer/checkpoints` | |
| Geri alma | `POST /api/v1/ai/developer/rollback` | `confirm=true` **zorunlu** |
| Test çalıştırma | `POST /api/v1/ai/developer/run-tests` | Sabit, güvenli komut |
| Kabuk komutu | `POST /api/v1/ai/developer/shell` | Beyaz liste; varsayılan **kapalı** |
| Komut politika denetimi | `POST /api/v1/ai/developer/check-command` | Çalıştırmadan yalnızca kararı döndürür |
| Politikayı görüntüleme | `GET /api/v1/ai/developer/policy` | Neyin izinli, neyin yasak olduğunu şeffaf gösterir |

Tüm uçlar `ai:developer` iznini gerektirir. Bu izin varsayılan olarak
**yalnızca `system_admin` rolündedir** — okul müdürü rolünde bile yoktur
(`_MANAGER_FULL` kümesinden `Perm.AI_DEVELOPER` çıkarılmıştır).

### 1.2 Ajan ne YAPAMAZ

| Yapamaz | Nasıl engelleniyor |
|---------|--------------------|
| Proje klasörünün dışına yazmak | `CommandPolicy.resolve_path()` — `relative_to()` kontrolü, dışarı çıkışta `SecurityPolicyError` |
| `.env` dosyasını okumak veya yazmak | `FORBIDDEN_PATH_PARTS` içinde `.env` |
| Veritabanı dosyasına dokunmak | `FORBIDDEN_PATH_PARTS` içinde `data/swimming_school.db` |
| Yedekleri okumak/silmek | `FORBIDDEN_PATH_PARTS` içinde `backups` |
| SSH anahtarı, kimlik bilgisi okumak | `id_rsa`, `credentials`, `secrets`, `.git/config` yasak |
| Dosya **silmek** | `action="delete"` önerileri reddedilir ve uyarıya dönüşür |
| Registry değiştirmek | `BLOCKED_PATTERNS` — `reg add`, `Set-ItemProperty HKLM:` vb. |
| Disk biçimlendirmek / bölümlemek | `format c:`, `diskpart` yasak |
| Kullanıcı hesabı / grup değiştirmek | `net user`, `New-LocalUser`, `Add-LocalGroupMember` yasak |
| Windows servisi veya zamanlanmış görev oluşturmak | `sc config`, `Set-Service`, `schtasks` yasak |
| Güvenlik duvarı / antivirüs ayarı değiştirmek | `netsh advfirewall`, `Set-MpPreference` yasak |
| Tarayıcı şifre deposunu okumak | `Login Data`, `logins.json`, `key4.db`, `cookies.sqlite` yasak |
| İnternetten indirdiği betiği çalıştırmak | `curl ... \| bash`, `iwr ... \| iex` yasak |
| Yükseltilmiş yetkiyle (yönetici) komut çalıştırmak | `runas`, `Start-Process -Verb RunAs` yasak |
| Komut zincirlemek veya komut ikamesi yapmak | `;`, `&&`, `\|\|`, `` ` ``, `$(` desenleri yasak |
| Uzak depoya `git push` yapmak | `git push`, `git remote add`, `git config --global` yasak |
| Bağımlılık kurmak | `pip install` yasak |
| Onaysız yama uygulamak | `confirm=true` zorunlu **ve** `AI_DEVELOPER_ALLOW_APPLY=true` gerekir |
| Migration dosyasını sessizce değiştirmek | `alembic/versions` altındaki yazımlar `requires_confirmation` işaretli döner |
| Testleri atlamak | `AI_DEVELOPER_AUTO_TEST=true` iken testler çalışır; uygulamadan sonra başarısızsa **otomatik geri alınır** |

### 1.3 Kapsam dışı

Ajan bir "otonom geliştirici" değildir. Mimari kararlar almaz, veritabanı
şeması tasarlamaz, üretim ortamına dağıtım yapmaz ve kendi kendine görev
başlatmaz. Her çalıştırma bir kullanıcı isteğiyle başlar ve her yazma
işlemi bir kullanıcı onayıyla biter.

---

## 2. Güvenlik Politikası

Kaynak: `backend/app/services/ai/policy.py`.
Politikanın tamamı `GET /api/v1/ai/developer/policy` ile arayüzden
görüntülenebilir — kullanıcıdan gizli bir kural yoktur.

### 2.1 İzin verilen komutlar (beyaz liste)

`ALLOWED_COMMANDS` — bu listede olmayan hiçbir çalıştırılabilir dosya
kabul edilmez. Kontrol, yolun **dosya adı** üzerinden yapılır ve `.exe`
uzantısı düşürülür; yani `C:\tools\pytest.exe` da `pytest` sayılır.

| Komut | Açıklama | İzin verilen alt komutlar |
|-------|----------|---------------------------|
| `pytest` | Test çalıştırma | (sınırsız argüman) |
| `python` | Python betiği (yalnızca proje içinden) | `-m`, `-c`, `-V`, `--version` |
| `ruff` | Lint denetimi | (sınırsız argüman) |
| `black` | Kod biçimlendirme | (sınırsız argüman) |
| `mypy` | Tip denetimi | (sınırsız argüman) |
| `alembic` | Veritabanı migration | (sınırsız argüman) — `upgrade`/`downgrade`/`stamp` **onay ister** |
| `npm` | Frontend paket komutları | `run`, `ci`, `test`, `install`, `list`, `audit` |
| `npx` | Frontend araçları | `tsc`, `eslint`, `prettier`, `vitest` |
| `git` | Sürüm kontrolü | `status`, `diff`, `log`, `show`, `add`, `stash`, `rev-parse`, `branch` |

Kurallar:

* Alt komut listesi tanımlıysa ve komutta bir alt komut varsa, listede
  olmayan alt komut reddedilir (`-` ile başlayan bayraklar muaftır).
* Komut 500 karakterden uzunsa reddedilir.
* Komut `shlex.split(..., posix=False)` ile ayrıştırılır ve
  `subprocess.run(..., shell=False)` ile çalıştırılır — **kabuk yorumlaması
  yoktur**, dolayısıyla kabuk enjeksiyonu mümkün değildir.
* `AI_DEVELOPER_ALLOW_SHELL=false` iken (varsayılan) **hiçbir komut
  çalıştırılmaz**; `check_command()` daha ilk satırda reddeder.

### 2.2 Yasak desenler

`BLOCKED_PATTERNS` listesi **37 düzenli ifade** içerir ve bunlar **30 ayrı
yasak işlem kategorisini** kapsar (bazı kategoriler birden fazla desenle
yakalanır). Desen kontrolü, beyaz liste kontrolünden **önce** ve büyük/küçük
harf duyarsız (`re.IGNORECASE`) çalışır; yani izinli bir komutun içine
gizlenmiş yasak bir işlem de yakalanır.

| # | Desen (regex) | Yasaklanan işlem |
|---|---------------|------------------|
| 1 | `\brm\s+-rf\b` | Özyinelemeli zorla silme |
| 2 | `\bdel\s+/[sqf]` | Toplu dosya silme |
| 3 | `\brmdir\s+/s` | Klasör ağacı silme |
| 4 | `\bRemove-Item\b.*-Recurse.*-Force` | PowerShell özyinelemeli silme |
| 5 | `\bformat\b\s+[a-z]:` | Disk biçimlendirme |
| 6 | `\bdiskpart\b` | Disk yönetimi |
| 7 | `\breg(edit)?\s+(add\|delete\|import)` | Registry değişikliği |
| 8 | `Set-ItemProperty.*HK(LM\|CU):` | Registry değişikliği |
| 9 | `New-ItemProperty.*HK(LM\|CU):` | Registry değişikliği |
| 10 | `\bnet\s+user\b` | Kullanıcı hesabı değişikliği |
| 11 | `\bnet\s+localgroup\b` | Grup üyeliği değişikliği |
| 12 | `New-LocalUser\|Set-LocalUser\|Add-LocalGroupMember` | Kullanıcı hesabı değişikliği |
| 13 | `\bicacls\b\|\bcacls\b\|\btakeown\b` | Dosya izni değişikliği |
| 14 | `\bshutdown\b\|\bRestart-Computer\b\|\bStop-Computer\b` | Sistem kapatma/yeniden başlatma |
| 15 | `\bsc\s+(config\|delete\|stop\|start)\b` | Windows servis değişikliği |
| 16 | `Set-Service\|Stop-Service\|New-Service` | Windows servis değişikliği |
| 17 | `\bschtasks\b\|\bRegister-ScheduledTask\b` | Zamanlanmış görev oluşturma |
| 18 | `\bbcdedit\b\|\bvssadmin\b` | Önyükleme / gölge kopya değişikliği |
| 19 | `\bnetsh\s+(firewall\|advfirewall)` | Güvenlik duvarı değişikliği |
| 20 | `Set-MpPreference\|Add-MpPreference` | Antivirüs ayarı değişikliği |
| 21 | `\bcurl\b.*\\\|\s*(sh\|bash\|powershell)` | İnternetten indirilen betiğin çalıştırılması |
| 22 | `Invoke-WebRequest.*\\\|\s*(iex\|Invoke-Expression)` | İnternetten indirilen betiğin çalıştırılması |
| 23 | `\biwr\b.*\\\|\s*iex` | İnternetten indirilen betiğin çalıştırılması |
| 24 | `\bInvoke-Expression\b\|\biex\b\s` | Dinamik kod çalıştırma |
| 25 | `\bStart-Process\b.*-Verb\s+RunAs` | Yükseltilmiş yetkiyle çalıştırma |
| 26 | `\brunas\b` | Yükseltilmiş yetkiyle çalıştırma |
| 27 | `Get-Credential\|cmdkey\|vaultcmd` | Kimlik bilgisi erişimi |
| 28 | `\bmimikatz\b\|\blsass\b` | Kimlik bilgisi çıkarma |
| 29 | `Login Data\|Local State\|\\Chrome\\User Data` | Tarayıcı şifre deposu erişimi |
| 30 | `logins\.json\|key4\.db\|cookies\.sqlite` | Tarayıcı kimlik deposu erişimi |
| 31 | `\.env\b` | `.env` dosyasına erişim (sır sızıntısı riski) |
| 32 | `\bpip\s+install\b` | Bağımlılık kurulumu (manuel onay gerekir) |
| 33 | `\bnpm\s+(publish\|adduser\|login\|token)` | Paket yayınlama / kimlik işlemi |
| 34 | `\bgit\s+(push\|remote\s+add\|config\s+--global)` | Uzak depo / global yapılandırma değişikliği |
| 35 | `[;&\|]{1,2}\s*\w` | Komut zincirleme (tek komut çalıştırılabilir) |
| 36 | `` ` `` veya `\$\(` | Komut ikamesi |
| 37 | `>\s*[A-Za-z]:\\` | Mutlak yola yönlendirme |

Son üç desen özellikle önemlidir: bunlar "izinli bir komutun arkasına yasak
bir komut eklemek" (`pytest ; format c:`), "komut ikamesiyle çıktı
enjekte etmek" (`` python -c `whoami` ``) ve "proje dışına dosya yazmak"
(`ruff > C:\Windows\x.txt`) yollarını kapatır.

Bir komutun politikadan geçip geçmediğini **çalıştırmadan** test edebilirsiniz:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/ai/developer/check-command?command=pytest%20-q"
```

```json
{
  "command": "pytest -q",
  "allowed": true,
  "reason": "Test çalıştırma çalıştırılabilir",
  "requires_confirmation": false
}
```

### 2.3 Yasak yollar

`FORBIDDEN_PATH_PARTS` — bir yolun **herhangi bir yerinde** (küçük harfe
çevrilmiş ve `\` → `/` normalize edilmiş biçimde) bu parçalardan biri
geçiyorsa okuma da yazma da reddedilir.

| Yol parçası | Neden yasak |
|-------------|-------------|
| `.env` | API anahtarları ve `SECRET_KEY` burada |
| `.git/config` | Uzak depo kimlik bilgileri içerebilir |
| `id_rsa` | SSH özel anahtarı |
| `credentials` | Kimlik bilgisi dosyaları |
| `secrets` | Sır dosyaları |
| `.venv` | Sanal ortam — üçüncü parti kod |
| `node_modules` | Bağımlılıklar — üçüncü parti kod |
| `backups` | Yedek arşivleri |
| `data/swimming_school.db` | Canlı veritabanı dosyası |

Bu kontrole ek olarak **her yol proje köküne göre çözülür**:

```python
def resolve_path(self, relative_path: str) -> Path:
    candidate = (self.project_root / relative_path).resolve()
    try:
        candidate.relative_to(self.project_root)
    except ValueError:
        raise SecurityPolicyError("ai.path_outside_project", ...)
    return candidate
```

`..\..\Windows\System32` gibi bir yol `.resolve()` sonrası proje kökünün
dışına düştüğü için `SecurityPolicyError` ile reddedilir ve girişim
`developer-agent` günlüğüne yazılır.

Kök dizin `AI_DEVELOPER_ROOT` ile daraltılabilir (varsayılan `.` = proje kökü).

### 2.4 Yazılabilir uzantılar

`WRITABLE_EXTENSIONS` — bu 16 uzantı dışındaki hiçbir dosyaya yazılamaz:

```
.py  .ts  .tsx  .js  .jsx  .json  .md  .css  .html
.yml .yaml .txt .toml .cfg .ini .sql
```

Dolayısıyla ajan `.exe`, `.dll`, `.bat`, `.ps1`, `.db`, `.zip`, `.png` gibi
dosyaları **oluşturamaz ve değiştiremez**. Uzantısız dosyalar da reddedilir
(`Yazılamayan dosya türü: (uzantısız)`).

Özel durum: `alembic/versions` altındaki dosyalar yazılabilir sayılır ama
`requires_confirmation=True` işaretiyle döner ve arayüzde
*"Migration dosyası - dikkatli inceleyin"* uyarısı gösterilir.

### 2.5 Kullanıcı onayı gerektiren işlemler

`REQUIRES_CONFIRMATION` listesi (politika çıktısında da görünür):

* Dosya silme
* Veritabanı migration (`alembic upgrade` / `downgrade`)
* Yama uygulama (`apply_patch`)
* Geri alma (`rollback`)
* 10'dan fazla dosyayı etkileyen değişiklik

---

## 3. İş Akışı

```
READ → SEARCH → ANALYZE → PLAN → GENERATE PATCH → RUN TEST → SHOW DIFF
                                                                  │
                                                        ┌─────────┴─────────┐
                                                        │  KULLANICI ONAYI  │
                                                        └─────────┬─────────┘
                                                                  │
                                                          APPLY PATCH
                                                                  │
                                                     (testler başarısızsa)
                                                                  ↓
                                                             ROLLBACK
```

`POST /api/v1/ai/developer/plan` ilk yedi adımı çalıştırır ve **hiçbir
dosyayı değiştirmez**. Uygulama ayrı bir çağrıdır.

### Adım adım

| Adım | Ne yapar | Kod | Başarısızlık davranışı |
|------|----------|-----|------------------------|
| **READ** | İstemden 4+ harfli anahtar kelimeler çıkarır (Türkçe/İngilizce dolgu sözcükleri elenir), dosya adlarında puanlama yapar, en yüksek puanlı `max_files` dosyayı okur. Bağlam `MAX_CONTEXT_CHARS = 60_000` ile sınırlanır, dosya başına `MAX_FILE_BYTES = 200_000`. | `_gather_context()` | Dosya bulunamazsa akış durur, "Daha açık bir istem yazın" uyarısı döner |
| **SEARCH** | Dosya adında yeterli eşleşme yoksa (3'ten az) kaynak kod **içinde** metin araması yapar ve adayları genişletir. | `search_in_files()` | Aday yoksa `failed` |
| **ANALYZE** | Sistem istemi `SYSTEM_DEVELOPER` + toplanan bağlam + JSON şema ipucu ile `AIRouter.chat(task="code", json_mode=True, temperature=0.15, max_tokens=8192)` çağrılır. | `plan_changes()` | Sağlayıcıya ulaşılamazsa akış durur, `apply_allowed=False` döner |
| **PLAN** | Model yanıtındaki JSON ayrıştırılır: `analysis`, `plan[]`, `changes[]`, `warnings[]`, `test_command`. Kod çitleri (```` ``` ````) temizlenir. | `_extract_json()` | Ayrıştırılamazsa ham yanıt `analysis` alanında döner, yama üretilmez |
| **GENERATE PATCH** | Her değişiklik tek tek doğrulanır: `action="delete"` **reddedilir**, `policy.can_write()` çalıştırılır, içerik değişmemişse atlanır. Geçenler için birleşik diff üretilir (`difflib.unified_diff`, ilk 20.000 karakter). Yama JSON olarak `tools/ai_developer/patches/{patch_id}.json` dosyasına yazılır — **henüz uygulanmaz**. | `make_diff()`, `diff_stats()` | Politika reddederse ilgili dosya atlanır ve uyarı listesine yazılır |
| **RUN TEST** | `AI_DEVELOPER_AUTO_TEST=true` ve değişiklik varsa mevcut testler çalıştırılır. **Bu, değişiklik öncesi temel (baseline) ölçümdür** — yamanın kendisini test etmez, çünkü yama henüz uygulanmamıştır. | `run_tests()` | Başarısız olsa da akış durmaz; sonuç raporlanır |
| **SHOW DIFF** | Değişiklik başına yol, işlem türü (`create`/`modify`), diff metni, eklenen/silinen satır sayısı ve boyut bilgisi arayüze döner. | `FileChange` şeması | Değişiklik yoksa `skipped` |
| **KULLANICI ONAYI** | `APPLY_PATCH` adımı `pending` durumunda kalır: *"Kullanıcı onayı bekleniyor"*. `AI_DEVELOPER_ALLOW_APPLY=false` ise ayrıca uyarı eklenir. | — | Onaysız hiçbir şey uygulanmaz |
| **APPLY PATCH** | `POST .../apply` ile `confirm=true` gönderilir. Politika **yeniden** denetlenir (plan üretiminden sonra ayar değişmiş olabilir), checkpoint alınır, dosyalar yazılır. | `apply_patch()` | Yazma sırasında hata olursa **anında rollback** |
| **ROLLBACK** | `run_tests_after=true` (varsayılan) ise testler çalışır; başarısızsa değişiklikler **otomatik geri alınır**. Elle geri alma için `POST .../rollback`. | `rollback_checkpoint()` | — |

### Adım durumları

Her adım `AgentStep` olarak raporlanır:
`step` ∈ {`READ`, `SEARCH`, `ANALYZE`, `PLAN`, `GENERATE_PATCH`, `RUN_TEST`,
`SHOW_DIFF`, `APPLY_PATCH`, `ROLLBACK`},
`status` ∈ {`pending`, `running`, `success`, `failed`, `skipped`}.

Arayüzde bu adımlar sırayla ve süreleriyle birlikte gösterilir.

### Denetim kaydı

Her `plan`, `apply`, `rollback`, `run-tests` ve `shell` çağrısı denetim
kaydına (audit log) yazılır: kim, ne zaman, hangi istem, kaç dosya, sonuç ne.
Ayrıca her çalıştırma `ai_tasks` tablosuna `kind="developer"` olarak kaydedilir
ve `file_changes` ile `test_result` alanları doldurulur.

---

## 4. Checkpoint ve Geri Alma

### 4.1 Nasıl çalışır

Yama uygulanmadan **önce**, değiştirilecek her dosyanın bir kopyası
`.ai_checkpoints/{checkpoint_id}/` dizinine alınır.

```
checkpoint_id = ckpt_20260818_143052_a1b2c3
                 └──┬──┘ └──┬───┘ └──┬──┘
                  önek   zaman damgası  rastgele 6 hane
```

Dosya adları çakışmayı önlemek için düzleştirilir:
`backend/app/api/v1/students.py` → `backend__app__api__v1__students.py`.

### 4.2 Manifest yapısı

Her checkpoint dizininde bir `manifest.json` bulunur:

```json
{
  "checkpoint_id": "ckpt_20260818_143052_a1b2c3",
  "created_at": "2026-08-18T14:30:52.184213+00:00",
  "label": "patch_20260818_143050_9f8e7d: Öğrenci ekranına Excel export ekle",
  "files": [
    {
      "path": "backend/app/api/v1/students.py",
      "stored_as": "backend__app__api__v1__students.py",
      "existed": true
    },
    {
      "path": "backend/app/services/export_students.py",
      "stored_as": null,
      "existed": false
    }
  ]
}
```

`existed` alanı geri alma davranışını belirler:

| `existed` | Geri alma sırasında |
|-----------|---------------------|
| `true` | Yedek dosya orijinal konumuna **geri kopyalanır** (`restored` listesine girer) |
| `false` | Dosya ajan tarafından oluşturulmuştu; **silinir** (`removed` listesine girer) |

Bu sayede hem değiştirilen dosyalar eski haline döner hem de yeni oluşturulan
dosyalar ortada kalmaz.

### 4.3 Ne zaman otomatik geri alınır

İki durumda geri alma **siz istemeden** çalışır:

1. **Yazma sırasında hata** — dosyalardan biri yazılamazsa (izin hatası, disk
   dolu vb.) tüm değişiklikler geri alınır ve yanıt şu olur:

   ```json
   {
     "success": false,
     "rolled_back": true,
     "applied_files": [],
     "message": "Yama uygulanamadı ve geri alındı: PermissionError"
   }
   ```

2. **Testler başarısız** — `run_tests_after=true` (varsayılan) iken uygulama
   sonrası `pytest` çalışır ve başarısız olursa:

   ```json
   {
     "success": false,
     "rolled_back": true,
     "applied_files": [],
     "test_result": { "passed": 305, "failed": 4, "success": false },
     "message": "Testler başarısız oldu (4 hata). Değişiklikler otomatik olarak geri alındı."
   }
   ```

Testler geçerse:

```json
{
  "success": true,
  "rolled_back": false,
  "applied_files": ["backend/app/api/v1/students.py"],
  "message": "1 dosya güncellendi. Testler geçti (310 test)."
}
```

> `run_tests_after=false` göndermek bu güvenlik ağını kapatır. **Önerilmez.**

### 4.4 Elle geri alma

```bash
# Mevcut checkpoint'leri listele
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/developer/checkpoints

# Geri al (onay zorunlu)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"checkpoint_id":"ckpt_20260818_143052_a1b2c3","confirm":true}' \
     http://127.0.0.1:8000/api/v1/ai/developer/rollback
```

`confirm` alanı `false` veya eksikse istek `confirmation_required` hatasıyla
reddedilir. Geri alma işlemi denetim kaydına yazılır.

### 4.5 Test çalıştırma ayrıntısı

`run_tests()` sabit bir komut listesiyle çalışır ve **kullanıcı girdisi
komuta enjekte edilmez**:

```python
command = [str(python_executable), "-m", "pytest", target, "-q", "--tb=short", "--no-header"]
subprocess.run(command, cwd=..., shell=False, timeout=timeout, ...)
```

* Yorumlayıcı önce `.venv/Scripts/python.exe` içinde aranır, bulunamazsa
  `python` kullanılır.
* Çalışma dizini `backend/`, varsayılan hedef `backend/tests`, varsayılan
  zaman aşımı 300 saniye.
* `POST .../run-tests` ucundaki `target` parametresi ayrıca doğrulanır:
  `..`, baştaki `/` veya `\`, ve `:` içeren değerler reddedilir.
* Bu komut kabuk politikasından **bağımsızdır**: `AI_DEVELOPER_ALLOW_SHELL=false`
  iken bile testler çalıştırılabilir, çünkü komut sabittir ve `shell=False` ile
  çalışır.

---

## 5. Yapılandırma

### 5.1 Ayarlar ve risk değerlendirmesi

Dosya: `.env` (şablon: `.env.example`), okuma: `backend/app/core/config.py`

| Değişken | Varsayılan | Ne yapar | Risk | Öneri |
|----------|-----------|----------|------|-------|
| `AI_DEVELOPER_ENABLED` | `true` | Konsolun tamamını açar/kapatır. `false` iken `plan_changes()` `ai.developer_disabled` hatası verir. | **Düşük** — açık olması tek başına yazma yetkisi vermez | Üretimde `false` yapın |
| `AI_DEVELOPER_ALLOW_APPLY` | `false` | Yamaların diske yazılmasına izin verir. `false` iken yalnızca önizleme üretilir. | **YÜKSEK** — kaynak kodu değiştirir | Yalnızca aktif geliştirme sırasında ve sürüm kontrolü altındayken `true` |
| `AI_DEVELOPER_ALLOW_SHELL` | `false` | Beyaz listedeki komutların çalıştırılmasına izin verir. | **YÜKSEK** — komut çalıştırma yüzeyi açar | Gerekli değilse `false` bırakın; CAIO açık bırakıldığında uyarı üretir |
| `AI_DEVELOPER_AUTO_TEST` | `true` | Plan üretiminde temel testleri çalıştırır. | **Yok** — güvenliği artırır | `true` bırakın |
| `AI_DEVELOPER_ROOT` | `.` | Ajanın yazabileceği kök dizin (mutlaklaştırılır ve dışına çıkılamaz). | **Orta** — geniş kök geniş yüzey demektir | Proje kökü yeterlidir; daraltmak isterseniz `backend` gibi bir alt dizin verin |

```dotenv
# ---------- AI DEVELOPER CONSOLE ----------
AI_DEVELOPER_ENABLED=true
AI_DEVELOPER_ALLOW_APPLY=false      # true ise yamalar onay sonrası uygulanabilir
AI_DEVELOPER_ALLOW_SHELL=false      # Kabuk komutlarına izin (varsayılan: kapalı)
AI_DEVELOPER_AUTO_TEST=true
AI_DEVELOPER_ROOT=.                 # Ajanın yazabileceği kök dizin (proje dışına çıkamaz)
```

### 5.2 Risk seviyelerine göre üç profil

**Profil A — Salt okunur inceleme (en güvenli, önerilen başlangıç)**

```dotenv
AI_DEVELOPER_ENABLED=true
AI_DEVELOPER_ALLOW_APPLY=false
AI_DEVELOPER_ALLOW_SHELL=false
AI_DEVELOPER_AUTO_TEST=true
```

Ajan okur, analiz eder, diff gösterir. Hiçbir dosya değişmez. Diff'i
beğenirseniz elle uygularsınız. **Üretim dışı her ortam için varsayılan.**

**Profil B — Denetimli uygulama (aktif geliştirme)**

```dotenv
AI_DEVELOPER_ALLOW_APPLY=true
AI_DEVELOPER_ALLOW_SHELL=false
AI_DEVELOPER_AUTO_TEST=true
```

Onayladığınız yamalar uygulanır, testler otomatik çalışır, başarısızsa
otomatik geri alınır. **Ön koşul: proje bir sürüm kontrol deposunda olmalı ve
çalışma alanı temiz olmalı.**

**Profil C — Üretim**

```dotenv
AI_DEVELOPER_ENABLED=false
AI_DEVELOPER_ALLOW_APPLY=false
AI_DEVELOPER_ALLOW_SHELL=false
```

Üretim ortamında geliştirici konsolu kapalı olmalıdır.

### 5.3 Erişim kontrolü

| İzin | Kim sahip | Neye erişir |
|------|-----------|-------------|
| `ai:developer` | Yalnızca `system_admin` | AI Developer Console'un tamamı |
| `ai:caio` | `system_admin`, `school_director` | CAIO ekranı ve bulgular |
| `ai:configure` | `system_admin`, `school_director` | AI yapılandırması ve bağlantı testi |
| `ai:use` | Çoğu personel rolü | Analiz, sohbet, prompt kütüphanesi |

`_MANAGER_FULL` kümesi `Perm.AI_DEVELOPER` iznini **açıkça dışarıda bırakır**;
yani okul müdürü rolü bile yama uygulayamaz. Bu kasıtlıdır.

---

## 6. Kullanım Örnekleri

### 6.1 İyi istem nasıl yazılır

Ajan, istemdeki 4 harften uzun kelimelere göre dosya arar. Dolgu sözcükleri
(`için`, `ekle`, `yeni`, `dosya`, `kod`, `add`, `create`, `update`, `file`…)
elenir. Bu yüzden **dosya adı, modül adı veya sınıf adı geçirmek** en etkili
yöntemdir.

| ✅ İyi istem | ❌ Zayıf istem | Neden |
|-------------|---------------|-------|
| "`backend/app/api/v1/students.py` içindeki listeleme ucuna `swim_level` filtresi ekle" | "Öğrenci filtresi ekle" | Dosya adı verilmiş; ajan doğru dosyayı bulur |
| "`statistics_engine` modülündeki `cohort_retention` fonksiyonu için `backend/tests` altına test yaz" | "Test yaz" | Modül ve fonksiyon adı verilmiş |
| "`scheduling` servisindeki çakışma denetimi fonksiyonuna docstring ekle" | "Kodu belgele" | Servis adı verilmiş, kapsam dar |

Ek kurallar:

* **Tek bir işi tarif edin.** "Filtre ekle ve testleri yaz ve README'yi
  güncelle" üç ayrı istem olmalıdır.
* **`max_files` küçük tutun.** Varsayılan 8; geniş refactor için artırın ama
  10'un üstü zaten onay gerektirir.
* **Dosya silme istemeyin.** Ajan `delete` önerilerini reddeder.
* **Beklenen davranışı yazın.** "Boş sonuç dönerse 404 yerine boş liste
  dönsün" gibi.

### 6.2 Örnek 1 — Yeni bir sorgu filtresi

**İstem:**

> `backend/app/api/v1/students.py` dosyasındaki öğrenci listeleme ucuna
> `swim_level` sorgu parametresi ekle. Parametre verilmezse mevcut davranış
> değişmesin. Mevcut sayfalama ve izin kontrolünü koru.

**API çağrısı:**

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "instruction": "backend/app/api/v1/students.py dosyasındaki öğrenci listeleme ucuna swim_level sorgu parametresi ekle. Parametre verilmezse mevcut davranış değişmesin.",
       "provider": "auto",
       "max_files": 4,
       "auto_test": true
     }' \
     http://127.0.0.1:8000/api/v1/ai/developer/plan
```

**Beklenen akış:** READ (`students.py` + ilgili şema dosyası) → SEARCH →
ANALYZE → PLAN (2–3 adım) → GENERATE_PATCH (1 dosya) → RUN_TEST (temel) →
SHOW_DIFF → APPLY_PATCH `pending`.

**Onaydan sonra:**

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"patch_id":"patch_20260818_143050_9f8e7d","confirm":true,"run_tests_after":true}' \
     http://127.0.0.1:8000/api/v1/ai/developer/apply
```

### 6.3 Örnek 2 — Eksik test yazma

**İstem:**

> `backend/app/services/statistics_engine.py` içindeki `cohort_retention`
> fonksiyonu için `backend/tests` altına test yaz. Boş veri, tek kohort ve
> çok kohortlu durumları kapsa. Mevcut test dosyalarındaki fixture desenini
> kullan.

Bu istem iyi çalışır çünkü:

* Hem kaynak dosya hem hedef dizin adı geçiyor (READ adımı doğru dosyaları bulur).
* Kapsanacak durumlar sayılmış (model neyi yazacağını biliyor).
* Yeni dosya oluşturma `.py` uzantısı olduğu için politikaya uygundur.

Test dosyası eklemek düşük risklidir: mevcut kod değişmez, `apply` sonrası
testler zaten çalıştırılır ve yeni test başarısız olursa değişiklik otomatik
geri alınır.

### 6.4 Örnek 3 — Belgelendirme ve okunabilirlik

**İstem:**

> `backend/app/services/scheduling.py` dosyasındaki çakışma denetimi
> fonksiyonlarına Türkçe docstring ekle. Mevcut kod stiline uy (tip ipuçları,
> Türkçe yorum). Fonksiyon imzalarını ve davranışı değiştirme.

Bu istem, ajanın en güvenli kullanım alanıdır: davranış değişmez, testler
etkilenmez, diff kolay incelenir.

### 6.5 Kabuk komutu (yalnızca `AI_DEVELOPER_ALLOW_SHELL=true` iken)

```bash
# Önce politika denetimi (çalıştırmaz)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/ai/developer/check-command?command=ruff%20check%20backend"

# Politika geçtiyse çalıştır
curl -X POST -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/ai/developer/shell?command=ruff%20check%20backend"
```

Reddedilen bir örnek:

```json
{
  "command": "pytest -q ; format c:",
  "allowed": false,
  "reason": "Yasak işlem: Komut zincirleme (tek komut çalıştırılabilir)",
  "requires_confirmation": false
}
```

---

## 7. Sınırlamalar

### 7.1 Ajan neyi yapamaz

| Sınırlama | Ayrıntı |
|-----------|---------|
| Dosya silemez | `action="delete"` önerileri reddedilir, uyarıya dönüşür |
| İkili (binary) dosya üretemez | Yalnızca 16 metin uzantısı yazılabilir |
| Bağımlılık kuramaz | `pip install` ve `npm publish/login` yasak; `npm install` beyaz listede olsa da `pip install` deseni ayrıca engellenir |
| Uzak depoya gönderemez | `git push`, `git remote add`, `git config --global` yasak |
| `.env` göremez | Ne okuyabilir ne yazabilir; ayarları değiştiremez |
| Veritabanına yazamaz | `data/swimming_school.db` yasak yol; migration dosyaları onay ister |
| Kendi kendine çalışmaz | Her akış bir kullanıcı isteğiyle başlar |
| Onay olmadan uygulayamaz | `confirm=true` **ve** `AI_DEVELOPER_ALLOW_APPLY=true` gerekir |
| Parçalı yama (patch hunk) üretmez | Model dosyanın **tam yeni içeriğini** döndürmelidir; bu, büyük dosyalarda token maliyetini artırır |
| Aynı anda çok sayıda dosya değiştiremez | `max_files` üst sınırı 40, varsayılan 8; 10 üzeri ayrıca onay konusudur |

### 7.2 Hangi durumlarda başarısız olur

| Durum | Belirti | Çözüm |
|-------|---------|-------|
| İstem çok genel | `READ` adımı `failed`, "İstemle eşleşen dosya bulunamadı" | Dosya/modül adı ekleyin |
| Sağlayıcıya ulaşılamıyor | `ANALYZE` adımı `failed`, "Yapay zekâ sağlayıcısına ulaşılamadı" | LM Studio'yu başlatın veya bulut sağlayıcıyı etkinleştirin |
| Model JSON şemasına uymuyor | `PLAN` adımı `failed`, ham yanıt `analysis` alanında | Talimat takibi güçlü / kod odaklı bir model seçin; bağlantı testinin 4. adımı (`json_output`) `PASS` vermeli |
| Model var olmayan dosya öneriyor | Yeni dosya olarak oluşturulur (uzantı izinliyse) | Diff'i inceleyin; istemediğiniz dosyaları uygulamayın |
| Politika reddi | Uyarı: "Politika reddetti (yol): sebep" | Yasak yol veya yazılamayan uzantı; istemi daraltın |
| Dosya 200 KB'tan büyük | `file_too_large` hatası | Dosyayı bölün veya daha dar bir istem verin |
| Bağlam sınırı doldu | Bazı dosyalar okunmaz | `max_files` değerini düşürün, istemi daraltın |
| Testler zaten kırık | `RUN_TEST` `failed` (uygulama öncesi temel) | Önce mevcut testleri düzeltin; aksi halde `apply` sonrası her yama geri alınır |
| Uygulama izni kapalı | Uyarı: "Yama uygulama izni KAPALI" | `AI_DEVELOPER_ALLOW_APPLY=true` (bilinçli karar) |
| Yama dosyası bulunamıyor | `patch_not_found` | `patch_id` yanlış veya `tools/ai_developer/patches/` temizlenmiş |

### 7.3 Yapısal kısıtlar

* Model yanıtı **tam dosya içeriği** döndürdüğü için çok büyük dosyalarda
  token maliyeti yüksektir ve model içerik kaybedebilir. 700 satırı aşan
  dosyalar için istemi tek fonksiyona daraltın (CAIO zaten uzun dosyaları
  `technical_debt` bulgusu olarak raporlar).
* `RUN_TEST` adımı **yamayı test etmez**, uygulama öncesi temel ölçümdür.
  Yamanın gerçek testi `apply` sırasında yapılır.
* Ajan iş mantığını doğrulamaz; yalnızca testlerin geçmesini kontrol eder.
  Test kapsamı düşükse geçen testler doğruluk garantisi vermez.
* Ajan yalnızca `SEARCHABLE_DIRS` altında arar: `backend/app`, `frontend/src`,
  `scripts`, `docs`, `backend/tests`. Bunların dışındaki dosyaları bulamaz.

---

## 8. CAIO Ajanı

**CAIO** (*Chief AI Officer*), sistemin kendi sağlığını, güvenliğini, teknik
borcunu ve maliyetini gözlemleyen ajandır. Kaynak:
`backend/app/services/ai/caio.py`, ekran: **CAIO** (`/caio`, izin `ai:caio`).

> CAIO üretim koduna **kendi başına değişiklik yapamaz.** Yalnızca gözlem
> yapar, bulgu üretir ve öneri sunar. Yama üretimi ve uygulama, AI Developer
> Console'un onay akışından geçer.

Kural motoru **tamamen deterministiktir ve yapay zekâ olmadan çalışır.**
`include_ai=false` gönderirseniz ya da hiçbir sağlayıcı erişilebilir değilse
bulgular yine tam olarak üretilir.

### 8.1 Gözlem kategorileri (6)

| Kategori | Ne ölçer |
|----------|----------|
| `logs` | `logs/*.log` dosyalarının son 400 KB'ı; hata/uyarı sayısı, normalize edilmiş imzalarla en sık 10 hata |
| `ai_usage` | Toplam/başarılı/başarısız görev, başarı oranı, yerel oran, bulut token sayısı, ortalama süre, fallback sayısı, türe göre dağılım |
| `code_quality` | Backend/frontend dosya ve satır sayısı, test dosyası sayısı, test/kaynak oranı, TODO-FIXME-XXX sayısı, 700 satırı aşan dosyalar, test edilmemiş servis modülleri |
| `database` | Kayıt sayıları, veritabanı boyutu, veri kalitesi (eksik doğum tarihi, eksik iletişim, rızasız aktif öğrenci, yoklaması alınmamış geçmiş dersler), takvim çakışmaları |
| `security` | Başarısız girişler (24 saat), kilitli hesaplar, parolasını değiştirmemiş kullanıcılar, süper kullanıcı sayısı, `.env` durumu ve `.gitignore` kontrolü, debug modu, **kabuk ve yama izinleri**, istem loglama |
| `backups` | Toplam/doğrulanmış/bozuk yedek, son doğrulanmış yedekten bu yana geçen gün, zamanlama durumu, toplam boyut |

Yalnızca ölçüm almak için (hiç AI çağırmaz):

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/caio/observe
```

### 8.2 Bulgu türleri ve önem seviyeleri

| Kategori | Önem | Tetikleyen koşul |
|----------|------|------------------|
| `security` | **critical** | `.env` var ama `.gitignore` içinde değil |
| `security` | high | Üretim ortamında `APP_DEBUG=true` |
| `security` | high | Son 24 saatte 20'den fazla başarısız giriş |
| `security` | medium | Varsayılan parolasını değiştirmemiş kullanıcı var |
| `security` | medium | **`AI_DEVELOPER_ALLOW_SHELL=true`** |
| `security` | low | 3'ten fazla süper kullanıcı |
| `backup` | high | Hiç yedek yok |
| `backup` | high | Bozuk yedek var |
| `backup` | medium | Son doğrulanmış yedek 7 günden eski |
| `testing` | medium | Test/kaynak oranı %10'un altında |
| `testing` | medium | Test edilmemiş servis modülü var |
| `technical_debt` | low | 20'den fazla TODO/FIXME/XXX |
| `technical_debt` | low | 700 satırı aşan dosyalar var |
| `reliability` | high | Loglarda 50'den fazla hata |
| `reliability` | medium | Loglarda 10–50 arası hata |
| `data_quality` | medium | 5'ten fazla geçmiş derste yoklama alınmamış |
| `compliance` | medium | KVKK rızası olmayan aktif öğrenci var |
| `operations` | high | Takvimde çakışma var (−7 / +30 gün penceresi) |
| `ai_quality` | medium | AI görev başarı oranı %70'in altında |
| `ai_quality` | medium | Son 24 saatte 5'ten fazla başarısız AI görevi |
| `cost` | low | Yerel oran %50'nin altında **ve** buluta 50.000'den fazla token gönderilmiş |
| `ai_suggestion` | info | AI'nın ürettiği ek öneriler (`is_ai_generated=true`, en fazla 5) |

Önem sıralaması: `critical` → `high` → `medium` → `low` → `info`.

Her bulgu şu alanları taşır: `category`, `severity`, `title`, `description`,
`recommendation`, `evidence` (JSON kanıt), `source` (`rule_engine` veya `ai`),
`status`, `is_ai_generated`, `ai_provider`, `created_at`, `resolved_at`.

**Yinelenme koruması:** Aynı başlıkta `open` bir bulgu varsa yeni kayıt
açılmaz; mevcut bulgunun `evidence` ve `description` alanları güncellenir.

### 8.3 Bulgu durumu yönetimi

```
open ──► acknowledged ──► in_progress ──► resolved
  │                                          ▲
  └──────────────► dismissed ────────────────┘
```

| Durum | Anlamı | Ne zaman kullanılır |
|-------|--------|---------------------|
| `open` | Yeni tespit, henüz ele alınmadı | Kural motoru veya AI ürettiğinde varsayılan |
| `acknowledged` | Görüldü ve kabul edildi, henüz çalışılmıyor | Bilgi sahibi olundu, sıraya alındı |
| `in_progress` | Üzerinde çalışılıyor | Düzeltme başladı |
| `resolved` | Giderildi | Sorun çözüldü — `resolved_at` damgalanır |
| `dismissed` | Geçerli değil / kabul edilen risk | Bilinçli olarak yok sayıldı — `resolved_at` damgalanır |

Durum güncelleme:

```bash
curl -X PATCH -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"status":"in_progress","note":"Yedekleme zamanlayıcısı açıldı, doğrulama bekleniyor"}' \
     http://127.0.0.1:8000/api/v1/ai/caio/findings/42
```

* `note` gönderilirse bulgunun `recommendation` alanının sonuna
  `[Not] ...` biçiminde eklenir.
* `resolved` ve `dismissed` durumlarında `resolved_at` otomatik doldurulur.
* Her güncelleme denetim kaydına yazılır.

Filtreli listeleme:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/ai/caio/findings?status=open&severity=critical"
```

Kontrol paneli için hafif özet (tam analiz çalıştırmaz):

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/caio/summary
```

Yanıt: `open_findings`, `by_severity`, `by_category`, `critical_count`,
`high_count`, `last_run_at`, `top_findings` (en önemli 5).

### 8.4 CAIO'yu çalıştırma

```bash
# Kural motoru + AI yorumu
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"include_ai": true, "provider": "auto"}' \
     http://127.0.0.1:8000/api/v1/ai/caio/run

# Yalnızca kural motoru (token harcamaz, sağlayıcı gerekmez)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"include_ai": false}' \
     http://127.0.0.1:8000/api/v1/ai/caio/run

# Yalnızca belirli kategoriler
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"include_ai": false, "categories": ["security", "backup"]}' \
     http://127.0.0.1:8000/api/v1/ai/caio/run
```

Her çalıştırma sonunda bir `SystemEvent` kaydı (`event_type="caio_run"`)
oluşturulur ve denetim kaydına yazılır.

---

## 9. Güvenlik Denetim Listesi

Bu özellikleri açmadan **önce** aşağıdaki maddelerin tamamını kontrol edin.

### 9.1 Sürüm kontrolü ve yedek

- [ ] Proje bir Git deposunda mı? (Yama uygulama öncesi zorunlu sayılmalı)
- [ ] Çalışma alanı temiz mi? (`git status` — uygulanmamış değişiklik yoksa geri dönüş kolaydır)
- [ ] Güncel ve **doğrulanmış** bir yedek var mı? (CAIO `backup` bulgularına bakın)
- [ ] `.ai_checkpoints/` dizinine yazma izni var mı?

### 9.2 Sır yönetimi

- [ ] `.env` dosyası var ve `.gitignore` içinde mi?
      `git check-ignore -v .env` çıktısı boşsa **ignore ediliyor** demektir.
- [ ] `git ls-files --error-unmatch .env` **hata veriyor** mu? (Vermiyorsa `.env` takip ediliyor — sorun!)
- [ ] `.env.example` içinde gerçek anahtar var mı? (Olmamalı)
- [ ] `SECRET_KEY` varsayılan/örnek değerden değiştirildi mi?
- [ ] `FIRST_ADMIN_PASSWORD` ilk girişten sonra değiştirildi mi?
- [ ] `AI_LOG_PROMPTS=false` mı?

### 9.3 Ajan yapılandırması

- [ ] `AI_DEVELOPER_ALLOW_APPLY` gerçekten gerekli mi? Değilse `false`.
- [ ] `AI_DEVELOPER_ALLOW_SHELL` gerçekten gerekli mi? Değilse `false`.
- [ ] `AI_DEVELOPER_AUTO_TEST=true` mı?
- [ ] `AI_DEVELOPER_ROOT` beklenen dizini mi gösteriyor?
- [ ] Üretim ortamında `AI_DEVELOPER_ENABLED=false` mı?

### 9.4 Erişim kontrolü

- [ ] `ai:developer` izni yalnızca güvenilen yöneticilerde mi?
- [ ] Süper kullanıcı sayısı en az düzeyde mi? (CAIO 3'ten fazlasında uyarır)
- [ ] Varsayılan parolasını değiştirmemiş kullanıcı var mı?
      (`must_change_password` — CAIO raporlar)
- [ ] Denetim kaydı (audit log) çalışıyor ve inceleniyor mu?

### 9.5 Test altyapısı

- [ ] Mevcut testler **geçiyor** mu? (`cd backend && python -m pytest tests -q`)
      Kırık testlerle çalışırsanız her yama uygulaması otomatik geri alınır.
- [ ] Test kapsamı makul mü? (CAIO test/kaynak oranı %10 altında uyarır)
- [ ] `FINAL_CHECK.bat` kalite kapısı başarıyla geçiyor mu?

### 9.6 Politikayı doğrulama

- [ ] `GET /api/v1/ai/developer/policy` çıktısını okudunuz mu?
      Beyaz liste, yasak desenler, yazma kapsamı ve onay gerektiren işlemler burada.
- [ ] Birkaç yasak komutu `check-command` ucuyla test ettiniz mi?
      Örnek: `pytest ; format c:` → `allowed: false` dönmeli.
- [ ] Proje dışı bir yolu okuma denemesi reddediliyor mu?
      Örnek: `GET /api/v1/ai/developer/file?path=../../Windows/System32/drivers/etc/hosts`

### 9.7 İlk çalıştırma öncesi

- [ ] CAIO'yu `include_ai=false` ile bir kez çalıştırıp `critical` ve `high`
      bulguların tamamını giderdiniz mi?
- [ ] AI sağlayıcı bağlantı testinin **4. adımı (`json_output`)** `PASS` veriyor mu?
      `FAIL` ise yama üretimi güvenilmez olur.
- [ ] İlk denemeyi düşük riskli bir istemle (docstring ekleme, test yazma)
      yaptınız mı?
- [ ] Üretilen diff'i satır satır okudunuz mu? **Okumadığınız hiçbir yamayı
      uygulamayın.**

### 9.8 Sürekli izleme

- [ ] CAIO düzenli olarak çalıştırılıyor mu? (Kontrol panelindeki özet kartı)
- [ ] `ai_tasks` görev geçmişi gözden geçiriliyor mu?
- [ ] `logs/developer-agent` kayıtlarında engellenmiş erişim girişimi var mı?
      (`"Proje dışı yol erişimi engellendi"`, `"Politika komutu engelledi"`)
- [ ] Yama uygulandıktan sonra elle de gözden geçirildi mi?

---

## İlgili belgeler

* [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) — Yapay zekâ mimarisi, sağlayıcı soyutlaması, CAIO akışı
* [LOCAL_AI.md](LOCAL_AI.md) — LM Studio ile yerel model kullanımı
* [NVIDIA_AI.md](NVIDIA_AI.md) — NVIDIA Build bulut entegrasyonu ve anahtar güvenliği
* [../CHANGELOG.md](../CHANGELOG.md) — Sürüm notları ve bilinen kısıtlamalar
* [../.env.example](../.env.example) — Tüm ortam değişkenlerinin şablonu
