"""Sunum içeriği / Presentation content — TR + EN.

Slaytlardaki bütün sayılar koda ve veritabanı şemasına karşı doğrulanmıştır;
hiçbir rakam tahmin edilmemiştir. Henüz tamamlanmamış yetenekler ("RFID/NFC
donanımı", "bulut yedekleme") açıkça altyapı/planlanan olarak işaretlenir.
"""

from __future__ import annotations

VERSION = "v0.9.0"

DECK: list[dict] = [
    # -----------------------------------------------------------------  1
    {
        "kind": "cover",
        "badge": {"icon": "🏊", "text": VERSION},
        "title": {
            "tr": "AKILLI YÜZME OKULU YÖNETİM SİSTEMİ",
            "en": "SMART SWIMMING SCHOOL MANAGEMENT SYSTEM",
        },
        "subtitle": {
            "tr": "Havuz Planlamasından Performans Analizine, Yapay Zekâ Destekli Tek Platform",
            "en": "One AI-Assisted Platform — From Pool Scheduling to Performance Analysis",
        },
        "tagline": {
            "tr": "Planla.  Ölç.  Geliştir.",
            "en": "Plan.  Measure.  Improve.",
        },
        "chips": [
            {"tr": "21 Rol · Yetki Tabanlı", "en": "21 Roles · Permission-Based"},
            {"tr": "Yerel Yapay Zekâ", "en": "Local AI First"},
            {"tr": "Yedekli & Kurtarılabilir", "en": "Backed Up & Recoverable"},
            {"tr": "Tam Türkçe / İngilizce", "en": "Full Turkish / English"},
        ],
        "footer": {
            "tr": "Ağustos 2026 · Windows masaüstü + web · MIT lisansı · Kurum içi kurulum",
            "en": "August 2026 · Windows desktop + web · MIT license · On-premise deployment",
        },
    },
    # -----------------------------------------------------------------  2
    {
        "kind": "quad",
        "icon": "🧭",
        "title": {"tr": "Tek Çatı Altında Dört Güç", "en": "Four Capabilities, One System"},
        "subtitle": {
            "tr": "Okul işletmesi · akıllı planlama · sporcu gelişimi · veri güvencesi — hepsi tek programda, yapay zekâsı varsayılan olarak kendi bilgisayarınızda çalışarak.",
            "en": "School operations · smart scheduling · athlete development · data assurance — in one program, with AI running on your own computer by default.",
        },
        "items": [
            {
                "icon": "🏫",
                "accent": "teal",
                "title": {"tr": "Okul İşletmesi", "en": "School Operations"},
                "body": {
                    "tr": "Öğrenci, veli, eğitmen, üyelik, paket ve finans kayıtları tek yerde. 21 rol, 52 izin ile herkes yalnızca yetkili olduğu veriyi görür.",
                    "en": "Students, guardians, instructors, memberships, packages and finance in one place. 21 roles and 52 permissions ensure everyone sees only authorised data.",
                },
            },
            {
                "icon": "📅",
                "accent": "blue",
                "title": {"tr": "Akıllı Planlama", "en": "Smart Scheduling"},
                "body": {
                    "tr": "Çok havuzlu kulvar planı, 13 ders türü, tekrarlı dersler ve çakışma motoru: aynı eğitmen, aynı kulvar veya aynı öğrenci iki yere birden yazılamaz.",
                    "en": "Multi-pool lane planning, 13 lesson types, recurring lessons and a conflict engine: the same instructor, lane or student can never be double-booked.",
                },
            },
            {
                "icon": "📈",
                "accent": "gold",
                "title": {"tr": "Sporcu Gelişimi", "en": "Athlete Development"},
                "body": {
                    "tr": "5 yüzme stili, split ve dönüş süreleri, kişisel rekorlar, yarışma sonuçları ve 28 istatistik fonksiyonuyla ölçülebilir gelişim takibi.",
                    "en": "5 strokes, split and turn times, personal bests, competition results and 28 statistical functions for measurable progress tracking.",
                },
            },
            {
                "icon": "🛡",
                "accent": "green",
                "title": {"tr": "Veri Güvencesi", "en": "Data Assurance"},
                "body": {
                    "tr": "SHA-256 imzalı yedekler, 11 bütünlük kontrolü, güvenli geri yükleme ve denetim kaydı. Verileriniz kurumunuzdan çıkmaz.",
                    "en": "SHA-256 signed backups, 11 integrity checks, safe restore and an audit trail. Your data never leaves your organisation.",
                },
            },
        ],
        "note": {
            "tr": "Yapay zekâ isteğe bağlıdır: kapalıyken ya da bağlantı koptuğunda okul yönetimi kesintisiz çalışmaya devam eder.",
            "en": "AI is optional: when it is disabled or unreachable, school management keeps running without interruption.",
        },
    },
    # -----------------------------------------------------------------  3
    {
        "kind": "stats",
        "icon": "🔢",
        "title": {"tr": "Sayılarla Sistem", "en": "The System in Numbers"},
        "subtitle": {
            "tr": "Aşağıdaki rakamların tamamı çalışan koddan ve veritabanı şemasından ölçülmüştür.",
            "en": "Every figure below is measured from the running code and database schema.",
        },
        "tiles": [
            {
                "value": "240",
                "accent": "teal",
                "label": {
                    "tr": "API ucu — 193 yol, 23 modül grubu",
                    "en": "API endpoints — 193 paths, 23 module groups",
                },
            },
            {
                "value": "55",
                "accent": "blue",
                "label": {
                    "tr": "Veritabanı tablosu, Alembic göçleriyle yönetilir",
                    "en": "Database tables, managed by Alembic migrations",
                },
            },
            {
                "value": "21",
                "accent": "gold",
                "label": {
                    "tr": "Kullanıcı rolü — 52 ayrı izinle sınırlandırılmış",
                    "en": "User roles — constrained by 52 distinct permissions",
                },
            },
            {
                "value": "395",
                "accent": "green",
                "label": {
                    "tr": "Otomatik test fonksiyonu — 533 çalıştırma, tamamı geçiyor",
                    "en": "Automated test functions — 533 runs, all passing",
                },
            },
            {
                "value": "24",
                "accent": "purple",
                "label": {
                    "tr": "Arayüz ekranı — hepsi çalışan uygulamadan, sentetik demo verisiyle",
                    "en": "Application screens — all from the running app, on synthetic demo data",
                },
            },
            {
                "value": "1.027",
                "accent": "teal",
                "label": {
                    "tr": "Türkçe çeviri anahtarı — İngilizce tarafta da 1.027",
                    "en": "Turkish translation keys — 1,027 on the English side too",
                },
            },
            {
                "value": "13",
                "accent": "blue",
                "label": {
                    "tr": "Ders türü: grup, özel, bebek, yarışma takımı, rehabilitasyon…",
                    "en": "Lesson types: group, private, baby, competition team, rehab…",
                },
            },
            {
                "value": "16",
                "accent": "rose",
                "label": {
                    "tr": "Hazır rapor şablonu — PDF, Excel ve CSV çıktısı",
                    "en": "Built-in report templates — PDF, Excel and CSV output",
                },
            },
        ],
        "note": {
            "tr": "Sistem SQLite ile kurulur, tek ayar değişikliğiyle PostgreSQL'e taşınır. Bu sunumdaki BÜTÜN kayıtlar sentetiktir: adlar sabit havuzlardan üretilir, telefonlar aranamayan biçimdedir ve her kayıt veritabanında `is_demo` ile işaretlenir. Gerçek hiçbir kişiye ait veri yoktur.",
            "en": "The system ships on SQLite and moves to PostgreSQL with a single setting change. EVERY record in this deck is synthetic: names are generated from fixed pools, phone numbers are undialable by construction, and each row is flagged `is_demo` in the database. No real person's data appears anywhere.",
        },
    },
    # -----------------------------------------------------------------  4
    {
        "kind": "panels",
        "icon": "🔐",
        "title": {
            "tr": "21 Rol, 52 İzin — Herkes Yalnızca Kendi Verisini Görür",
            "en": "21 Roles, 52 Permissions — Everyone Sees Only Their Own Data",
        },
        "subtitle": {
            "tr": "Yetkilendirme yalnızca menüyü gizlemekle kalmaz; sorgu düzeyinde satır bazlı kısıtlama uygular.",
            "en": "Authorisation does not merely hide menus; it applies row-level restrictions at the query layer.",
        },
        "left": {
            "icon": "🏢",
            "accent": "teal",
            "title": {"tr": "Yönetim ve Destek Rolleri", "en": "Management and Support Roles"},
            "lines": {
                "tr": [
                    "Sistem Yöneticisi · Okul Müdürü · Genel Müdür",
                    "Muhasebe · Finans Sorumlusu · İnsan Kaynakları",
                    "Resepsiyon · Kayıt Görevlisi · Operasyon Sorumlusu",
                    "Havuz Teknisyeni · Temizlik Sorumlusu · Güvenlik",
                    "Pazarlama · Raporlama Uzmanı",
                    "",
                    "Yalnızca Sistem Yöneticisi yapay zekâ geliştirici yetkisine sahiptir. Bu izin hiçbir başka role verilmez.",
                ],
                "en": [
                    "System Administrator · School Director · General Manager",
                    "Accounting · Finance Officer · Human Resources",
                    "Reception · Registration Clerk · Operations Officer",
                    "Pool Technician · Cleaning Supervisor · Security",
                    "Marketing · Reporting Specialist",
                    "",
                    "Only the System Administrator holds the AI developer permission. It is granted to no other role.",
                ],
            },
        },
        "right": {
            "icon": "🎓",
            "accent": "blue",
            "title": {"tr": "Eğitim ve Sporcu Rolleri", "en": "Education and Athlete Roles"},
            "lines": {
                "tr": [
                    "Baş Antrenör · Antrenör · Yardımcı Antrenör",
                    "Cankurtaran · Fizyoterapist · Beslenme Uzmanı",
                    "Öğrenci · Veli",
                    "",
                    "Antrenör yalnızca kendi derslerindeki öğrencilere erişir.",
                    "Veli yalnızca kendi çocuğunun kaydını görür.",
                    "Öğrenci yalnızca kendi verisini görür.",
                    "",
                    "Bu kısıtlar arayüzde değil, veri erişim katmanında uygulanır — doğrudan API çağrısı da aynı sınırla karşılaşır.",
                ],
                "en": [
                    "Head Coach · Coach · Assistant Coach",
                    "Lifeguard · Physiotherapist · Nutritionist",
                    "Student · Guardian",
                    "",
                    "A coach reaches only students in their own lessons.",
                    "A guardian sees only their own child's record.",
                    "A student sees only their own data.",
                    "",
                    "These limits live in the data-access layer, not the interface — a direct API call meets the same boundary.",
                ],
            },
        },
        "note": {
            "tr": "KVKK / GDPR veri minimizasyonu: her rol için yalnızca görevine gereken alanlar döndürülür. Hassas alanlar yetkisiz rollere hiç gönderilmez.",
            "en": "KVKK / GDPR data minimisation: each role receives only the fields its duties require. Sensitive fields are never sent to unauthorised roles.",
        },
    },
    # -----------------------------------------------------------------  5
    {
        "kind": "rows",
        "icon": "👨‍👩‍👧",
        "title": {"tr": "Öğrenci ve Veli Yönetimi", "en": "Student and Guardian Management"},
        "subtitle": {
            "tr": "Kayıttan mezuniyete kadar tüm yaşam döngüsü; veli bağlantısı, sağlık notu ve seviye takibiyle birlikte.",
            "en": "The full lifecycle from enrolment to graduation, with guardian links, health notes and level tracking.",
        },
        "items": [
            {
                "icon": "📇",
                "accent": "teal",
                "title": {"tr": "Tam Öğrenci Kartı", "en": "Complete Student Record"},
                "body": {
                    "tr": "Kimlik, iletişim, doğum tarihi, cinsiyet, kayıt tarihi ve 5 durum: aktif, pasif, deneme, dondurulmuş, ayrıldı.",
                    "en": "Identity, contact, date of birth, gender, enrolment date and 5 statuses: active, passive, trial, frozen, left.",
                },
            },
            {
                "icon": "🏅",
                "accent": "blue",
                "title": {"tr": "6 Yüzme Seviyesi", "en": "6 Swimming Levels"},
                "body": {
                    "tr": "Başlangıç, temel, orta, ileri, yarışma ve elit. Seviye değişimi geçmişiyle birlikte saklanır.",
                    "en": "Beginner, elementary, intermediate, advanced, competitive and elite — stored with full level-change history.",
                },
            },
            {
                "icon": "🔗",
                "accent": "gold",
                "title": {"tr": "Çoklu Veli Bağlantısı", "en": "Multiple Guardian Links"},
                "body": {
                    "tr": "Bir öğrenciye birden fazla veli, bir veliye birden fazla öğrenci bağlanabilir. Yakınlık derecesi ve birincil veli işaretlenir.",
                    "en": "A student can have several guardians and a guardian several students, with relationship type and a primary-guardian flag.",
                },
            },
            {
                "icon": "🩺",
                "accent": "rose",
                "title": {"tr": "Sağlık ve Güvenlik Notları", "en": "Health and Safety Notes"},
                "body": {
                    "tr": "Alerji, kronik rahatsızlık ve acil durum iletişimi. Bu alanlar yalnızca yetkili rollere gösterilir.",
                    "en": "Allergies, chronic conditions and emergency contacts — shown only to authorised roles.",
                },
            },
            {
                "icon": "📊",
                "accent": "green",
                "title": {"tr": "Öğrenci Detay Ekranı", "en": "Student Detail Screen"},
                "body": {
                    "tr": "Dersler, yoklama geçmişi, üyelik, ödemeler, performans ölçümleri ve yarışma sonuçları tek sayfada.",
                    "en": "Lessons, attendance history, membership, payments, performance measurements and competition results on one page.",
                },
            },
            {
                "icon": "🔎",
                "accent": "purple",
                "title": {"tr": "Hızlı Arama ve Süzme", "en": "Fast Search and Filtering"},
                "body": {
                    "tr": "Ada, seviyeye, duruma, gruba ve eğitmene göre süzme; global arama ve Ctrl+K komut paletinden anında erişim.",
                    "en": "Filter by name, level, status, group and instructor; instant access from global search and the Ctrl+K command palette.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  6
    {
        "kind": "rows",
        "icon": "🧑‍🏫",
        "title": {"tr": "Eğitmen Yönetimi", "en": "Instructor Management"},
        "subtitle": {
            "tr": "Uzmanlık, sertifika ve çalışma saatleri planlamaya doğrudan bağlanır — çakışma motoru bu verileri kullanır.",
            "en": "Specialities, certificates and working hours feed directly into scheduling — the conflict engine reads this data.",
        },
        "items": [
            {
                "icon": "🎖",
                "accent": "teal",
                "title": {"tr": "Uzmanlık ve Sertifikalar", "en": "Specialities and Certificates"},
                "body": {
                    "tr": "Antrenörlük belgesi, cankurtaran sertifikası, ilk yardım ve geçerlilik tarihleri kayıt altında.",
                    "en": "Coaching licences, lifeguard certification, first aid and their expiry dates are all on record.",
                },
            },
            {
                "icon": "🕐",
                "accent": "blue",
                "title": {"tr": "Çalışma Saatleri", "en": "Working Hours"},
                "body": {
                    "tr": "Haftalık müsaitlik tanımı. Eğitmen müsait olmadığı saate ders atanamaz — sistem engeller.",
                    "en": "Weekly availability. A lesson cannot be assigned outside an instructor's available hours — the system blocks it.",
                },
            },
            {
                "icon": "📋",
                "accent": "gold",
                "title": {"tr": "Ders Yükü Görünümü", "en": "Workload View"},
                "body": {
                    "tr": "Haftalık ders sayısı, toplam saat ve öğrenci dağılımı. Aşırı yüklenme uyarı olarak gösterilir.",
                    "en": "Weekly lesson count, total hours and student distribution. Overload is surfaced as a warning.",
                },
            },
            {
                "icon": "🌴",
                "accent": "green",
                "title": {"tr": "İzin ve Devamsızlık", "en": "Leave and Absence"},
                "body": {
                    "tr": "İzin girildiğinde ilgili dersler işaretlenir ve yedek eğitmen ataması için bildirim üretilir.",
                    "en": "When leave is recorded the affected lessons are flagged and a notification is raised for substitute assignment.",
                },
            },
            {
                "icon": "📈",
                "accent": "purple",
                "title": {"tr": "Eğitmen Metrikleri", "en": "Instructor Metrics"},
                "body": {
                    "tr": 'Devam oranı, öğrenci gelişimi ve ders doluluk oranı — arayüzde "karar destek amaçlıdır" ibaresiyle sunulur.',
                    "en": 'Attendance rate, student progress and lesson occupancy — presented with an explicit "decision support only" caveat.',
                },
            },
            {
                "icon": "👥",
                "accent": "rose",
                "title": {"tr": "Grup Sorumluluğu", "en": "Group Ownership"},
                "body": {
                    "tr": "Eğitmen kendi grubunun tüm öğrencilerine erişir; grubu dışındaki öğrenciler listesinde görünmez.",
                    "en": "An instructor reaches every student in their own group; students outside it never appear in their lists.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  7
    {
        "kind": "quad",
        "icon": "🏊‍♀️",
        "title": {
            "tr": "Çok Havuzlu Tesis ve Kulvar Yönetimi",
            "en": "Multi-Pool Facility and Lane Management",
        },
        "subtitle": {
            "tr": "Birden fazla havuz, her havuzda ayrı kulvarlar; kapasite ve bakım durumu planlamayı doğrudan etkiler.",
            "en": "Several pools, individual lanes in each; capacity and maintenance status feed straight into scheduling.",
        },
        "items": [
            {
                "icon": "🏊",
                "accent": "teal",
                "title": {"tr": "Havuz Tanımları", "en": "Pool Definitions"},
                "body": {
                    "tr": "Uzunluk (25 m / 50 m), derinlik, sıcaklık, kulvar sayısı ve toplam kapasite. Kısa ve uzun kulvar ayrımı performans kayıtlarına taşınır.",
                    "en": "Length (25 m / 50 m), depth, temperature, lane count and total capacity. The short/long course distinction carries into performance records.",
                },
            },
            {
                "icon": "🚦",
                "accent": "gold",
                "title": {"tr": "3 Havuz Durumu", "en": "3 Pool States"},
                "body": {
                    "tr": "Faal, bakımda, kapalı. Bakıma alınan havuzun kulvarlarına yeni ders atanamaz; mevcut dersler uyarıyla listelenir.",
                    "en": "Operational, under maintenance, closed. Lanes of a pool under maintenance accept no new lessons; existing ones are listed with a warning.",
                },
            },
            {
                "icon": "🛟",
                "accent": "blue",
                "title": {"tr": "Kulvar Planı Ekranı", "en": "Lane Plan Screen"},
                "body": {
                    "tr": "Gün ve saat bazında hangi kulvarda hangi dersin olduğu tek bakışta görülür. Boş kulvarlar ve doluluk oranı ayrı gösterilir.",
                    "en": "See at a glance which lesson occupies which lane by day and hour. Free lanes and occupancy rate are shown separately.",
                },
            },
            {
                "icon": "🧪",
                "accent": "green",
                "title": {"tr": "Bakım ve Kimyasal Takibi", "en": "Maintenance and Chemical Tracking"},
                "body": {
                    "tr": "Bakım kayıtları ve kimyasal giderleri finans modülüne 10 gider kategorisinden biri olarak işlenir.",
                    "en": "Maintenance records and chemical costs post into the finance module as one of 10 expense categories.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  8
    {
        "kind": "quad",
        "icon": "🗓",
        "title": {"tr": "Akıllı Ders Planlama", "en": "Smart Lesson Scheduling"},
        "subtitle": {
            "tr": "Ders oluştururken sistem eğitmeni, kulvarı, öğrenciyi ve kapasiteyi aynı anda denetler.",
            "en": "When a lesson is created the system checks instructor, lane, student and capacity simultaneously.",
        },
        "items": [
            {
                "icon": "⚠️",
                "accent": "rose",
                "title": {"tr": "Engelleyen Hatalar", "en": "Blocking Errors"},
                "body": {
                    "tr": "Aynı eğitmen, aynı kulvar veya aynı öğrenci çakışan saatlere yazılamaz. Kapasite aşımı da kayıt anında engellenir.",
                    "en": "The same instructor, lane or student cannot be booked into overlapping times. Capacity overflow is blocked at enrolment.",
                },
            },
            {
                "icon": "💡",
                "accent": "gold",
                "title": {"tr": "Bilgilendiren Uyarılar", "en": "Informative Warnings"},
                "body": {
                    "tr": "Eğitmen ders yükü yüksek, havuz doluluk oranı kritik, seviye uyumsuzluğu var — bunlar engellemez, karar için gösterilir.",
                    "en": "High instructor workload, critical pool occupancy, level mismatch — these do not block; they inform the decision.",
                },
            },
            {
                "icon": "🔁",
                "accent": "blue",
                "title": {"tr": "Tekrarlı Dersler", "en": "Recurring Lessons"},
                "body": {
                    "tr": "Haftalık tekrar tanımlanır, dönem boyunca otomatik üretilir. Tek bir tarihte iptal, seriyi bozmadan işlenir.",
                    "en": "Define a weekly pattern and the term is generated automatically. Cancelling one date does not break the series.",
                },
            },
            {
                "icon": "📆",
                "accent": "teal",
                "title": {"tr": "Takvim Görünümleri", "en": "Calendar Views"},
                "body": {
                    "tr": "Gün, hafta ve ay görünümü; sürükle-bırak ile saat değişikliği. Taşıma sırasında çakışma anında denetlenir.",
                    "en": "Day, week and month views with drag-and-drop rescheduling. Conflicts are checked the moment a lesson is moved.",
                },
            },
        ],
        "note": {
            "tr": "5 ders durumu: planlandı, devam ediyor, tamamlandı, iptal edildi, ertelendi. Her durum değişikliği denetim kaydına yazılır.",
            "en": "5 lesson states: scheduled, in progress, completed, cancelled, postponed. Every state change is written to the audit log.",
        },
    },
    # -----------------------------------------------------------------  9
    {
        "kind": "flow",
        "icon": "🧠",
        "title": {"tr": "Çakışma Motoru Nasıl Çalışır?", "en": "How the Conflict Engine Works"},
        "subtitle": {
            "tr": "Kural tek satırda tanımlıdır ve her ders kaydında, her taşımada, her tekrar üretiminde aynı biçimde uygulanır.",
            "en": "The rule is a single expression, applied identically on every lesson save, every move and every recurrence.",
        },
        "steps": [
            {
                "icon": "1",
                "accent": "teal",
                "title": {"tr": "Aday Ders Alınır", "en": "Candidate Lesson"},
                "body": {
                    "tr": "Tarih, başlangıç–bitiş saati, eğitmen, havuz ve kulvar bilgisi toplanır.",
                    "en": "Date, start–end time, instructor, pool and lane are collected.",
                },
            },
            {
                "icon": "2",
                "accent": "blue",
                "title": {"tr": "Aynı Gün Taranır", "en": "Same Day Scanned"},
                "body": {
                    "tr": "O güne ait mevcut dersler çekilir; iptal edilenler hesaba katılmaz.",
                    "en": "Existing lessons for that day are fetched; cancelled ones are excluded.",
                },
            },
            {
                "icon": "3",
                "accent": "gold",
                "title": {"tr": "Kesişim Sınanır", "en": "Overlap Tested"},
                "body": {
                    "tr": "başlangıç_A < bitiş_B  ve  başlangıç_B < bitiş_A. Bitişik dersler çakışma sayılmaz.",
                    "en": "start_A < end_B and start_B < end_A. Back-to-back lessons are not conflicts.",
                },
            },
            {
                "icon": "4",
                "accent": "rose",
                "title": {"tr": "Üç Eksen Ayrıştırılır", "en": "Three Axes Separated"},
                "body": {
                    "tr": "Eğitmen, kulvar ve öğrenci çakışmaları ayrı ayrı raporlanır — hangisinin sorun olduğu net görülür.",
                    "en": "Instructor, lane and student conflicts are reported separately, so the actual clash is unambiguous.",
                },
            },
            {
                "icon": "5",
                "accent": "green",
                "title": {"tr": "Hata / Uyarı Ayrımı", "en": "Error vs Warning"},
                "body": {
                    "tr": "Hatalar kaydı durdurur, uyarılar yalnızca gösterilir. Karar kullanıcıya bırakılır.",
                    "en": "Errors stop the save; warnings are only displayed. The decision stays with the user.",
                },
            },
        ],
        "note": {
            "tr": "Bitişik derslerin çakışma sayılmaması bilinçli bir tasarım kararıdır: 10:00–11:00 ile 11:00–12:00 arka arkaya planlanabilir.",
            "en": "Treating back-to-back lessons as non-conflicting is a deliberate design decision: 10:00–11:00 and 11:00–12:00 can be scheduled consecutively.",
        },
    },
    # -----------------------------------------------------------------  10
    {
        "kind": "rows",
        "icon": "🎯",
        "title": {
            "tr": "13 Ders Türü — Her Yaş ve Her Amaç İçin",
            "en": "13 Lesson Types — For Every Age and Purpose",
        },
        "subtitle": {
            "tr": "Ders türü yalnızca etiket değildir: kapasite, süre ve fiyatlandırma varsayılanlarını belirler.",
            "en": "Lesson type is more than a label: it drives default capacity, duration and pricing.",
        },
        "items": [
            {
                "icon": "👥",
                "accent": "teal",
                "title": {"tr": "Grup · Özel · Yarı Özel", "en": "Group · Private · Semi-Private"},
                "body": {
                    "tr": "Kapasite kuralları türe göre değişir; özel derste tek öğrenci, grup dersinde kulvar kapasitesi geçerlidir.",
                    "en": "Capacity rules vary by type: one student for private lessons, lane capacity for group lessons.",
                },
            },
            {
                "icon": "🍼",
                "accent": "blue",
                "title": {"tr": "Bebek · Çocuk · Yetişkin", "en": "Baby · Kids · Adult"},
                "body": {
                    "tr": "Yaş grubuna göre ayrı ders türleri; bebek derslerinde veli katılımı ve daha kısa süre varsayılanı.",
                    "en": "Separate types per age band, with guardian participation and shorter default duration for baby classes.",
                },
            },
            {
                "icon": "📚",
                "accent": "gold",
                "title": {"tr": "Başlangıç · Orta · İleri", "en": "Beginner · Intermediate · Advanced"},
                "body": {
                    "tr": "Seviye bazlı dersler öğrencinin yüzme seviyesiyle eşleştirilir; uyumsuzluk uyarı olarak gösterilir.",
                    "en": "Level-based lessons are matched to the student's swim level; a mismatch is surfaced as a warning.",
                },
            },
            {
                "icon": "🏆",
                "accent": "purple",
                "title": {"tr": "Yarışma Takımı · Antrenman", "en": "Competition Team · Training"},
                "body": {
                    "tr": "Performans ölçümü ve yarışma modülüyle doğrudan bağlantılı; split ve dönüş süreleri bu derslerde toplanır.",
                    "en": "Directly linked to performance measurement and the competition module; splits and turn times are collected here.",
                },
            },
            {
                "icon": "🧘",
                "accent": "green",
                "title": {"tr": "Rehabilitasyon · Aqua Fitness", "en": "Rehabilitation · Aqua Fitness"},
                "body": {
                    "tr": "Fizyoterapist rolüyle ilişkilendirilebilen terapi odaklı dersler ve su içi kondisyon programları.",
                    "en": "Therapy-focused lessons that can be tied to the physiotherapist role, plus in-water conditioning programmes.",
                },
            },
            {
                "icon": "🎁",
                "accent": "rose",
                "title": {"tr": "Deneme Dersi", "en": "Trial Lesson"},
                "body": {
                    "tr": "Deneme durumundaki öğrenci için ayrı tür; dönüşüm oranı istatistik merkezinde izlenir.",
                    "en": "A dedicated type for trial-status students; the conversion rate is tracked in the statistics centre.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  11
    {
        "kind": "panels",
        "icon": "📆",
        "title": {"tr": "Takvim ve Kayıt Yönetimi", "en": "Calendar and Enrolment Management"},
        "subtitle": {
            "tr": "Planlama ekranı ile kayıt listesi aynı veriyi paylaşır; birinde yapılan değişiklik diğerinde anında görünür.",
            "en": "The scheduling view and the enrolment list share the same data; a change in one appears immediately in the other.",
        },
        "left": {
            "icon": "🗓",
            "accent": "blue",
            "title": {"tr": "Takvim Yetenekleri", "en": "Calendar Capabilities"},
            "lines": {
                "tr": [
                    "• Gün, hafta ve ay görünümleri",
                    "• Sürükle-bırak ile saat ve kulvar değişikliği",
                    "• Havuza, eğitmene, ders türüne ve gruba göre süzme",
                    "• Renk kodlu ders durumları",
                    "• Tekrarlı ders serilerinin toplu görünümü",
                    "• Tek tarihte iptal — seri bozulmadan",
                    "• Çakışma anında görsel olarak işaretlenir",
                ],
                "en": [
                    "• Day, week and month views",
                    "• Drag-and-drop time and lane changes",
                    "• Filter by pool, instructor, lesson type and group",
                    "• Colour-coded lesson states",
                    "• Consolidated view of recurring series",
                    "• Cancel a single date without breaking the series",
                    "• Conflicts are marked visually as they occur",
                ],
            },
        },
        "right": {
            "icon": "✍️",
            "accent": "teal",
            "title": {"tr": "Kayıt ve Bekleme Listesi", "en": "Enrolment and Waitlist"},
            "lines": {
                "tr": [
                    "• 3 kayıt durumu: kayıtlı, bekleme listesi, iptal",
                    "• Kapasite dolduğunda otomatik bekleme listesi",
                    "• Kapasite denetimi sayım sorgusuyla yapılır —",
                    "   önbellekten değil, anlık gerçek sayıdan",
                    "• Bir yer boşaldığında bekleme listesi bildirimi",
                    "• Öğrenci başka derse taşınırken çakışma sınanır",
                    "• Kayıt geçmişi denetim kaydında saklanır",
                ],
                "en": [
                    "• 3 enrolment states: enrolled, waitlist, cancelled",
                    "• Automatic waitlisting when capacity is full",
                    "• Capacity is enforced with a count query —",
                    "   from the live figure, never a cached one",
                    "• Waitlist notification when a place frees up",
                    "• Conflicts are checked when moving a student",
                    "• Enrolment history is kept in the audit log",
                ],
            },
        },
        "note": {
            "tr": "Kapasite denetiminin anlık sayım sorgusuyla yapılması, aynı anda birden fazla kayıt girildiğinde kontenjanın aşılmasını önler.",
            "en": "Enforcing capacity with a live count query prevents over-booking when several enrolments are submitted at the same moment.",
        },
    },
    # -----------------------------------------------------------------  12
    {
        "kind": "panels",
        "icon": "✅",
        "title": {
            "tr": "Yoklama — 6 Durum, Birden Çok Yöntem",
            "en": "Attendance — 6 States, Multiple Methods",
        },
        "subtitle": {
            "tr": "Yoklama verisi devam oranı, üyelik hakkı düşümü ve performans analizinin ortak girdisidir.",
            "en": "Attendance data is the shared input for attendance rate, membership deduction and performance analysis.",
        },
        "left": {
            "icon": "📋",
            "accent": "teal",
            "title": {"tr": "6 Yoklama Durumu", "en": "6 Attendance States"},
            "lines": {
                "tr": [
                    "• Geldi — ders hakkından düşülür",
                    "• Gelmedi — mazeretsiz devamsızlık",
                    "• Geç geldi — katılım sayılır, gecikme kaydedilir",
                    "• Mazeretli — hak düşümü uygulanmaz",
                    "• İptal — ders tarafında iptal edilmiş",
                    "• Telafi — kaçırılan dersin yerine sayılır",
                    "",
                    'Devam oranı hesabında yalnızca geldi, geç geldi ve telafi "katıldı" sayılır.',
                ],
                "en": [
                    "• Present — deducted from the lesson allowance",
                    "• Absent — unexcused",
                    "• Late — counts as attendance, delay recorded",
                    "• Excused — no allowance deduction",
                    "• Cancelled — cancelled on the lesson side",
                    "• Make-up — counted in place of a missed lesson",
                    "",
                    'Only present, late and make-up count as "attended" in the attendance rate.',
                ],
            },
        },
        "right": {
            "icon": "📲",
            "accent": "blue",
            "title": {"tr": "Kayıt Yöntemleri", "en": "Capture Methods"},
            "lines": {
                "tr": [
                    "• Manuel — eğitmen veya resepsiyon girişi",
                    "• QR kod — öğrenciye özel kod okutulur",
                    "• Kart — üyelik kartı ile giriş",
                    "• RFID ve NFC — veri modeli hazır,",
                    "   donanım entegrasyonu sonraki sürümde",
                    "",
                    "Toplu yoklama ekranı: bir dersin tüm öğrencileri tek listede işaretlenir.",
                    "",
                    "Her kayıt kimin, ne zaman ve hangi yöntemle girdiğiyle birlikte saklanır.",
                ],
                "en": [
                    "• Manual — entered by instructor or reception",
                    "• QR code — a student-specific code is scanned",
                    "• Card — entry with a membership card",
                    "• RFID and NFC — data model in place,",
                    "   hardware integration in a later release",
                    "",
                    "Bulk attendance screen: mark every student of a lesson in a single list.",
                    "",
                    "Each record stores who entered it, when, and by which method.",
                ],
            },
        },
    },
    # -----------------------------------------------------------------  13
    {
        "kind": "rows",
        "icon": "🎫",
        "title": {"tr": "Üyelik ve Paket Yönetimi", "en": "Membership and Package Management"},
        "subtitle": {
            "tr": "7 paket türü, 5 üyelik durumu; dondurma ve iptal işlemleri geçmişiyle birlikte izlenir.",
            "en": "7 package types and 5 membership states; freeze and cancellation actions are tracked with full history.",
        },
        "items": [
            {
                "icon": "🎟",
                "accent": "teal",
                "title": {"tr": "7 Paket Türü", "en": "7 Package Types"},
                "body": {
                    "tr": "Ders paketi, aylık, 3 aylık, 6 aylık, yıllık, özel ders paketi ve deneme. Her biri süre ve hak sayısı tanımlar.",
                    "en": "Lesson pack, monthly, quarterly, biannual, annual, private pack and trial — each defining duration and entitlement.",
                },
            },
            {
                "icon": "🚦",
                "accent": "blue",
                "title": {"tr": "5 Üyelik Durumu", "en": "5 Membership States"},
                "body": {
                    "tr": "Aktif, süresi dolmuş, dondurulmuş, iptal edilmiş ve beklemede. Durum geçişleri kurallara bağlıdır.",
                    "en": "Active, expired, frozen, cancelled and pending — with rule-governed transitions between them.",
                },
            },
            {
                "icon": "❄️",
                "accent": "gold",
                "title": {"tr": "Dondurma", "en": "Freeze"},
                "body": {
                    "tr": "Üyelik dondurulduğunda kalan gün korunur, çözüldüğünde bitiş tarihi otomatik olarak ileri alınır.",
                    "en": "Freezing preserves remaining days; on resume the end date is automatically extended.",
                },
            },
            {
                "icon": "🔄",
                "accent": "green",
                "title": {"tr": "Yenileme", "en": "Renewal"},
                "body": {
                    "tr": "Süresi yaklaşan üyelikler için otomatik bildirim; yenilemede kalan haklar isteğe bağlı devredilir.",
                    "en": "Automatic notification as expiry approaches; on renewal remaining entitlements can optionally carry over.",
                },
            },
            {
                "icon": "📉",
                "accent": "purple",
                "title": {"tr": "Hak Düşümü", "en": "Entitlement Deduction"},
                "body": {
                    "tr": 'Yoklama "geldi" işaretlendiğinde ders hakkı düşer; mazeretli devamsızlıkta düşmez.',
                    "en": "Marking attendance as present deducts a lesson; an excused absence does not.",
                },
            },
            {
                "icon": "🔔",
                "accent": "rose",
                "title": {"tr": "Bitiş Uyarıları", "en": "Expiry Alerts"},
                "body": {
                    "tr": "14 gün içinde bitecek üyelikler panoda ve bildirimlerde ayrıca listelenir.",
                    "en": "Memberships expiring within 14 days are listed separately on the dashboard and in notifications.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  14
    {
        "kind": "quad",
        "icon": "💰",
        "title": {"tr": "Finans Modülü", "en": "Finance Module"},
        "subtitle": {
            "tr": "Gelir ve gider tek defterde; tahsilat takibi üyelik ve yoklama verisiyle bağlantılı çalışır.",
            "en": "Income and expenses in one ledger; collections are linked to membership and attendance data.",
        },
        "items": [
            {
                "icon": "🧾",
                "accent": "teal",
                "title": {"tr": "Fatura ve Tahsilat", "en": "Invoicing and Collection"},
                "body": {
                    "tr": "6 ödeme durumu: ödendi, beklemede, kısmi, gecikmiş, iade, iptal. Kısmi ödemelerde kalan bakiye otomatik hesaplanır.",
                    "en": "6 payment states: paid, pending, partial, overdue, refunded, cancelled. Remaining balance is computed automatically on partial payments.",
                },
            },
            {
                "icon": "💳",
                "accent": "blue",
                "title": {"tr": "5 Ödeme Yöntemi", "en": "5 Payment Methods"},
                "body": {
                    "tr": "Nakit, kart, havale/EFT, çevrimiçi ve diğer. Yöntem dağılımı istatistik merkezinde raporlanır.",
                    "en": "Cash, card, bank transfer, online and other. Method distribution is reported in the statistics centre.",
                },
            },
            {
                "icon": "📤",
                "accent": "rose",
                "title": {"tr": "10 Gider Kategorisi", "en": "10 Expense Categories"},
                "body": {
                    "tr": "Maaş, kira, faturalar, kimyasal, bakım, ekipman, pazarlama, vergi, sigorta ve diğer — havuz bakımı doğrudan buraya işlenir.",
                    "en": "Salary, rent, utilities, chemicals, maintenance, equipment, marketing, tax, insurance and other — pool upkeep posts straight here.",
                },
            },
            {
                "icon": "📊",
                "accent": "green",
                "title": {"tr": "Gecikme Takibi", "en": "Overdue Tracking"},
                "body": {
                    "tr": "Gecikmiş fatura sayısı, toplam tutar ve gecikme günü panoda ve ödeme riski analizinde ayrıca gösterilir.",
                    "en": "Overdue invoice count, total amount and days late are surfaced on the dashboard and in the payment-risk analysis.",
                },
            },
        ],
        "note": {
            "tr": "Tutarlar Türkçe biçimde gösterilir: 1.250,50 ₺. Dil İngilizce'ye alındığında sayı ve tarih biçimi de birlikte değişir.",
            "en": "Amounts follow Turkish formatting: 1.250,50 ₺. Switching the language to English changes number and date formatting along with it.",
        },
    },
    # -----------------------------------------------------------------  15
    {
        "kind": "quad",
        "icon": "⏱",
        "title": {
            "tr": "Performans Analizi — Ölçülebilir Gelişim",
            "en": "Performance Analysis — Measurable Progress",
        },
        "subtitle": {
            "tr": "Antrenman ve yarışma ölçümleri aynı veri modelinde toplanır; karşılaştırmalar kısa/uzun kulvar ayrımını korur.",
            "en": "Training and competition measurements share one data model; comparisons preserve the short/long course distinction.",
        },
        "items": [
            {
                "icon": "🏊",
                "accent": "teal",
                "title": {"tr": "5 Stil, Serbest Mesafe", "en": "5 Strokes, Any Distance"},
                "body": {
                    "tr": "Serbest, sırtüstü, kurbağalama, kelebek ve karışık. Mesafe serbest tanımlanır: 50, 100, 200, 400 m ve ötesi.",
                    "en": "Freestyle, backstroke, breaststroke, butterfly and medley. Distance is free-form: 50, 100, 200, 400 m and beyond.",
                },
            },
            {
                "icon": "⏲",
                "accent": "blue",
                "title": {"tr": "Split ve Dönüş Süreleri", "en": "Splits and Turn Times"},
                "body": {
                    "tr": "Her 25/50 m için ara derece, dönüş süresi, çıkış tepki süresi ve kulaç frekansı ayrı ayrı kaydedilir.",
                    "en": "Per-25/50 m splits, turn time, start reaction time and stroke rate are each recorded separately.",
                },
            },
            {
                "icon": "🥇",
                "accent": "gold",
                "title": {"tr": "Kişisel Rekorlar", "en": "Personal Bests"},
                "body": {
                    "tr": "Stil, mesafe ve kulvar tipi kombinasyonu başına kişisel rekor otomatik güncellenir; rekor kırıldığında bildirim üretilir.",
                    "en": "A personal best is maintained per stroke, distance and course-type combination; breaking one raises a notification.",
                },
            },
            {
                "icon": "📉",
                "accent": "rose",
                "title": {"tr": "Düşüş Tespiti", "en": "Decline Detection"},
                "body": {
                    "tr": "Doğrusal eğim ve hareketli ortalama ile gerilemeye geçen sporcular listelenir — bu bir istatistik sonucudur, tahmin değildir.",
                    "en": "Linear slope and moving averages list athletes whose trend has turned negative — a statistical result, not a prediction.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  16
    {
        "kind": "rows",
        "icon": "🏆",
        "title": {"tr": "Yarışma Modülü", "en": "Competition Module"},
        "subtitle": {
            "tr": "Kulüp içi seçmeden uluslararası müsabakaya kadar 5 seviye; seri, kulvar ve derece yönetimi.",
            "en": "Five levels from in-club trials to international meets, with heat, lane and result management.",
        },
        "items": [
            {
                "icon": "🎪",
                "accent": "teal",
                "title": {"tr": "5 Yarışma Seviyesi", "en": "5 Competition Levels"},
                "body": {
                    "tr": "Kulüp, yerel, bölgesel, ulusal ve uluslararası. Seviye, rekor karşılaştırmalarında ayrı tutulur.",
                    "en": "Club, local, regional, national and international — kept separate in record comparisons.",
                },
            },
            {
                "icon": "🏁",
                "accent": "blue",
                "title": {"tr": "Seri ve Kulvar Atama", "en": "Heat and Lane Assignment"},
                "body": {
                    "tr": "Katılımcılar serilere ve kulvarlara atanır; kayıt derecesine göre sıralama önerisi üretilir.",
                    "en": "Entrants are assigned to heats and lanes, with a seeding suggestion based on entry times.",
                },
            },
            {
                "icon": "🥇",
                "accent": "gold",
                "title": {"tr": "Derece ve Madalya", "en": "Ranking and Medals"},
                "body": {
                    "tr": "Sıralama, madalya (altın/gümüş/bronz) ve kulüp madalya tablosu otomatik hesaplanır.",
                    "en": "Rankings, medals (gold/silver/bronze) and the club medal table are computed automatically.",
                },
            },
            {
                "icon": "📜",
                "accent": "purple",
                "title": {"tr": "Rekor Takibi", "en": "Record Tracking"},
                "body": {
                    "tr": "Kulüp rekorları ve kişisel rekorlar yarışma sonucu girildiğinde otomatik güncellenir.",
                    "en": "Club records and personal bests update automatically when a competition result is entered.",
                },
            },
            {
                "icon": "📋",
                "accent": "green",
                "title": {"tr": "Katılım Listesi", "en": "Entry List"},
                "body": {
                    "tr": "Hangi sporcunun hangi branşa girdiği, kaç yarışa katıldığı tek ekranda görülür.",
                    "en": "See which athlete entered which event, and how many races each is swimming, on one screen.",
                },
            },
            {
                "icon": "🎯",
                "accent": "rose",
                "title": {"tr": "Yarışmaya Hazırlık", "en": "Competition Readiness"},
                "body": {
                    "tr": "Antrenman derecelerinin son eğilimine bakarak hazır bulunuşluk göstergesi üretilir — karar destek amaçlıdır.",
                    "en": "A readiness indicator derived from recent training trend — offered as decision support only.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  17
    {
        "kind": "quad",
        "icon": "📊",
        "title": {
            "tr": "İstatistik Merkezi — 28 Analiz Fonksiyonu",
            "en": "Statistics Centre — 28 Analytical Functions",
        },
        "subtitle": {
            "tr": "Bütün analizler veritabanındaki gerçek kayıtlar üzerinde çalışır; hiçbir sayı üretilmez veya tahmin edilmez.",
            "en": "Every analysis runs on real database records; no figure is generated or estimated.",
        },
        "items": [
            {
                "icon": "📐",
                "accent": "teal",
                "title": {"tr": "Temel İstatistik", "en": "Core Statistics"},
                "body": {
                    "tr": "Ortalama, medyan, standart sapma, yüzdelik dilim, hareketli ortalama, doğrusal eğim ve aykırı değer tespiti.",
                    "en": "Mean, median, standard deviation, percentile, moving average, linear slope and outlier detection.",
                },
            },
            {
                "icon": "🔥",
                "accent": "gold",
                "title": {"tr": "Isı Haritası ve Doluluk", "en": "Heatmap and Occupancy"},
                "body": {
                    "tr": "Hangi gün ve saatte hangi havuzun ne kadar dolu olduğu; boş kapasitenin nerede olduğu görsel olarak çıkar.",
                    "en": "Which pool is how full on which day and hour — idle capacity becomes visually obvious.",
                },
            },
            {
                "icon": "👥",
                "accent": "blue",
                "title": {"tr": "Kohort ve Elde Tutma", "en": "Cohort and Retention"},
                "body": {
                    "tr": "Aynı dönemde kaydolan öğrenciler birlikte izlenir; kaçının kaldığı, kaçının ayrıldığı aylık olarak görülür.",
                    "en": "Students enrolled in the same period are tracked together, showing month-by-month who stayed and who left.",
                },
            },
            {
                "icon": "🔗",
                "accent": "purple",
                "title": {"tr": "Korelasyon Analizi", "en": "Correlation Analysis"},
                "body": {
                    "tr": "Pearson korelasyonu ile devam oranı, ders sıklığı ve gelişim arasındaki ilişki ölçülür — ilişki, neden değildir.",
                    "en": "Pearson correlation measures the relationship between attendance, lesson frequency and progress — relationship is not cause.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  18
    {
        "kind": "panels",
        "icon": "⚖️",
        "title": {"tr": "Korelasyon Nedensellik Değildir", "en": "Correlation Is Not Causation"},
        "subtitle": {
            "tr": "Bu uyarı bir dipnot değil, arayüzün kalıcı parçasıdır. Her korelasyon sonucunun yanında gösterilir.",
            "en": "This caveat is not a footnote — it is a permanent part of the interface, shown beside every correlation result.",
        },
        "left": {
            "icon": "❌",
            "accent": "rose",
            "title": {"tr": "Sistemin Söylemediği", "en": "What the System Does Not Say"},
            "lines": {
                "tr": [
                    '"Devam oranı arttığı için gelişim hızlandı."',
                    "",
                    '"Bu eğitmen daha başarılı."',
                    "",
                    '"Bu öğrenci önümüzdeki ay ayrılacak."',
                    "",
                    "Bu cümlelerin hiçbiri ölçülen veriden çıkarılamaz. Sistem nedensellik iddia etmez, gelecek tahmini sunmaz ve kişi hakkında hüküm vermez.",
                ],
                "en": [
                    '"Progress accelerated because attendance rose."',
                    "",
                    '"This instructor is more successful."',
                    "",
                    '"This student will leave next month."',
                    "",
                    "None of these follow from the measured data. The system claims no causation, offers no forecast and passes no judgement on individuals.",
                ],
            },
        },
        "right": {
            "icon": "✅",
            "accent": "green",
            "title": {"tr": "Sistemin Söylediği", "en": "What the System Does Say"},
            "lines": {
                "tr": [
                    '"Devam oranı ile gelişim arasında güçlü pozitif ilişki var (r = 0,74)."',
                    "",
                    '"Bu eğitmenin gruplarında ortalama devam oranı %12 yüksek."',
                    "",
                    '"Bu öğrencinin son 8 ölçümünde derece eğilimi negatif."',
                    "",
                    "Ölçülen büyüklük, örneklem sayısı ve ilişkinin gücü birlikte sunulur. Yorum kullanıcıya bırakılır.",
                ],
                "en": [
                    '"There is a strong positive relationship between attendance and progress (r = 0.74)."',
                    "",
                    '"Average attendance in this instructor\'s groups is 12% higher."',
                    "",
                    '"This student\'s trend across the last 8 measurements is negative."',
                    "",
                    "The measured quantity, sample size and strength of relationship are presented together. Interpretation is left to the user.",
                ],
            },
        },
        "note": {
            "tr": 'Eğitmen metrikleri arayüzde açıkça "karar destek amaçlıdır" ibaresiyle sunulur; performans değerlendirmesi yerine geçmez.',
            "en": 'Instructor metrics carry an explicit "decision support only" label and are not a substitute for performance appraisal.',
        },
    },
    # -----------------------------------------------------------------  19
    {
        "kind": "stats",
        "icon": "🎯",
        "title": {"tr": "11 Anahtar Performans Göstergesi", "en": "11 Key Performance Indicators"},
        "subtitle": {
            "tr": "Panoda tek bakışta okulun durumu: her gösterge tıklanarak arkasındaki ham veriye inilebilir.",
            "en": "The school's status at a glance — every indicator drills through to the raw data behind it.",
        },
        "tiles": [
            {
                "value": "👥",
                "accent": "teal",
                "label": {
                    "tr": "Aktif öğrenci sayısı ve dönemsel değişimi",
                    "en": "Active student count and its change over time",
                },
            },
            {
                "value": "✅",
                "accent": "blue",
                "label": {
                    "tr": "Devam oranı — geldi, geç geldi ve telafi dahil",
                    "en": "Attendance rate — includes present, late and make-up",
                },
            },
            {
                "value": "🎫",
                "accent": "gold",
                "label": {
                    "tr": "Aktif üyelik ve yakında bitecek üyelik sayısı",
                    "en": "Active memberships and those expiring soon",
                },
            },
            {
                "value": "💰",
                "accent": "green",
                "label": {
                    "tr": "Dönemsel gelir, gider ve net bakiye",
                    "en": "Period income, expenses and net balance",
                },
            },
            {
                "value": "⚠️",
                "accent": "rose",
                "label": {
                    "tr": "Gecikmiş fatura sayısı ve toplam tutarı",
                    "en": "Overdue invoice count and total amount",
                },
            },
            {
                "value": "🏊",
                "accent": "purple",
                "label": {
                    "tr": "Havuz doluluk oranı ve boş kulvar kapasitesi",
                    "en": "Pool occupancy rate and idle lane capacity",
                },
            },
            {
                "value": "📈",
                "accent": "teal",
                "label": {
                    "tr": "Gelişen ve gerileyen sporcu sayısı",
                    "en": "Number of improving and declining athletes",
                },
            },
            {
                "value": "🔄",
                "accent": "blue",
                "label": {
                    "tr": "Elde tutma oranı ve deneme dersi dönüşümü",
                    "en": "Retention rate and trial-lesson conversion",
                },
            },
        ],
        "note": {
            "tr": "Göstergeler rol bazlıdır: muhasebe finansal KPI'ları görürken antrenör devam ve gelişim göstergelerini görür.",
            "en": "Indicators are role-aware: accounting sees financial KPIs while a coach sees attendance and progress indicators.",
        },
    },
    # -----------------------------------------------------------------  20
    {
        "kind": "rows",
        "icon": "📄",
        "title": {"tr": "16 Rapor Şablonu — PDF, Excel, CSV", "en": "16 Report Templates — PDF, Excel, CSV"},
        "subtitle": {
            "tr": "Hazır şablonların yanında rapor oluşturucu ile kendi raporunuzu tanımlayabilirsiniz.",
            "en": "Alongside the built-in templates, the report builder lets you define your own.",
        },
        "items": [
            {
                "icon": "🎓",
                "accent": "teal",
                "title": {"tr": "Öğrenci Raporları", "en": "Student Reports"},
                "body": {
                    "tr": "Öğrenci listesi, devam karnesi, gelişim raporu, seviye dağılımı ve kohort elde tutma.",
                    "en": "Student roster, attendance report card, progress report, level distribution and cohort retention.",
                },
            },
            {
                "icon": "🧑‍🏫",
                "accent": "blue",
                "title": {"tr": "Eğitmen Raporları", "en": "Instructor Reports"},
                "body": {
                    "tr": "Ders yükü, grup performansı ve eğitmen karşılaştırması — karar destek ibaresiyle.",
                    "en": "Workload, group performance and instructor comparison — with the decision-support caveat.",
                },
            },
            {
                "icon": "💰",
                "accent": "gold",
                "title": {"tr": "Finans Raporları", "en": "Finance Reports"},
                "body": {
                    "tr": "Gelir-gider tablosu, tahsilat durumu, gecikmiş alacaklar ve ödeme yöntemi dağılımı.",
                    "en": "Income-expense statement, collection status, overdue receivables and payment-method breakdown.",
                },
            },
            {
                "icon": "🏊",
                "accent": "purple",
                "title": {"tr": "Havuz ve Doluluk", "en": "Pool and Occupancy"},
                "body": {
                    "tr": "Havuz kullanım oranı, kulvar doluluğu ve saat bazlı yoğunluk ısı haritası.",
                    "en": "Pool utilisation, lane occupancy and an hour-by-hour density heatmap.",
                },
            },
            {
                "icon": "🏆",
                "accent": "green",
                "title": {"tr": "Performans ve Yarışma", "en": "Performance and Competition"},
                "body": {
                    "tr": "Kişisel rekor listesi, yarışma sonuçları, madalya tablosu ve gelişim eğilimi.",
                    "en": "Personal best listings, competition results, medal table and progress trend.",
                },
            },
            {
                "icon": "🛠",
                "accent": "rose",
                "title": {"tr": "Rapor Oluşturucu", "en": "Report Builder"},
                "body": {
                    "tr": "Sütun seçimi, tarih aralığı ve süzgeçlerle özel rapor; önizleme sonrası üç formatta dışa aktarım.",
                    "en": "Custom reports with column selection, date range and filters; preview then export in three formats.",
                },
            },
        ],
        "note": {
            "tr": "PDF çıktısında Türkçe karakterler için TTF font gömülür; CSV, Excel'de doğru açılsın diye UTF-8 BOM ile yazılır.",
            "en": "PDF output embeds a TTF font for Turkish characters; CSV is written with a UTF-8 BOM so Excel opens it correctly.",
        },
    },
    # -----------------------------------------------------------------  21
    {
        "kind": "quad",
        "icon": "🤖",
        "title": {
            "tr": "Yapay Zekâ — Sağlayıcı Sizin Seçiminiz",
            "en": "Artificial Intelligence — The Provider Is Your Choice",
        },
        "subtitle": {
            "tr": "Ortak bir sağlayıcı arayüzü: yerel model, bulut model ya da kendi sunucunuz. Uç nokta koda gömülü değildir.",
            "en": "One shared provider interface: a local model, a cloud model or your own server. The endpoint is never hard-coded.",
        },
        "items": [
            {
                "icon": "💻",
                "accent": "teal",
                "title": {"tr": "LM Studio — Yerel (Varsayılan)", "en": "LM Studio — Local (Default)"},
                "body": {
                    "tr": "Model kendi bilgisayarınızda çalışır. Öğrenci verisi kurumdan çıkmaz, ücret oluşmaz. Bağlantı testi 6 aşamada doğrulanır.",
                    "en": "The model runs on your own machine. Student data never leaves the organisation and there is no cost. Connectivity is verified in 6 stages.",
                },
            },
            {
                "icon": "☁️",
                "accent": "green",
                "title": {"tr": "NVIDIA Build — Bulut", "en": "NVIDIA Build — Cloud"},
                "body": {
                    "tr": "Daha güçlü modeller için isteğe bağlı bulut sağlayıcı. Anahtar yoksa sağlayıcı otomatik olarak devre dışı kalır.",
                    "en": "An optional cloud provider for stronger models. Without a key the provider simply stays disabled.",
                },
            },
            {
                "icon": "🔌",
                "accent": "blue",
                "title": {
                    "tr": "OpenAI Uyumlu — Kendi Sunucunuz",
                    "en": "OpenAI-Compatible — Your Own Server",
                },
                "body": {
                    "tr": "vLLM, Ollama, LiteLLM ya da kurum içi bir uç nokta: aynı arayüzle bağlanır, ek kod gerekmez.",
                    "en": "vLLM, Ollama, LiteLLM or an in-house endpoint connects through the same interface, with no extra code.",
                },
            },
            {
                "icon": "🧭",
                "accent": "purple",
                "title": {"tr": "Yetenek Varsayılmaz", "en": "Capability Is Never Assumed"},
                "body": {
                    "tr": 'Yönlendirici modeli göreve atamadan önce sağlayıcıya sorar. Doğrulanamayan eşleşme "sezgisel" olarak işaretlenir.',
                    "en": 'The router asks the provider before assigning a model to a task. An unverified match is flagged as "heuristic".',
                },
            },
        ],
        "note": {
            "tr": "API anahtarları yalnızca ortam değişkeninde tutulur; koda yazılmaz, sürüm kontrolüne girmez, ekranda ve kayıtlarda maskelenir.",
            "en": "API keys live only in environment variables: never in code, never in version control, and masked on screen and in logs.",
        },
    },
    # -----------------------------------------------------------------  22
    {
        "kind": "panels",
        "icon": "🔍",
        "title": {
            "tr": "Gerçek Veri ile Yapay Zekâ Yorumu Ayrıdır",
            "en": "Real Data and AI Interpretation Stay Separate",
        },
        "subtitle": {
            "tr": "Yapay zekâ ham veriye erişmez. Önce istatistik motoru ölçer, sonra model yalnızca bu ölçümleri yorumlar.",
            "en": "The AI never touches raw data. The statistics engine measures first; the model then interprets only those measurements.",
        },
        "left": {
            "icon": "📊",
            "accent": "teal",
            "title": {"tr": "1. Ölçülen — Gerçek Veri", "en": "1. Measured — Real Data"},
            "lines": {
                "tr": [
                    "Veritabanı → İstatistik Motoru → Yapılandırılmış Ölçüm",
                    "",
                    '"Son 90 günde 9 sporcunun derece eğilimi negatif."',
                    '"23 fatura gecikmiş, toplam 158.202,27 ₺."',
                    '"Salı 18:00 doluluk oranı %94."',
                    "",
                    "Bu satırlar doğrudan sorgudan gelir. Model bunları değiştiremez, ekleyemez, çıkaramaz.",
                ],
                "en": [
                    "Database → Statistics Engine → Structured Metrics",
                    "",
                    '"9 athletes show a negative trend over the last 90 days."',
                    '"23 invoices are overdue, totalling ₺158,202.27."',
                    '"Tuesday 18:00 occupancy is 94%."',
                    "",
                    "These lines come straight from the query. The model cannot alter, add to or remove them.",
                ],
            },
        },
        "right": {
            "icon": "💬",
            "accent": "purple",
            "title": {"tr": "2. Yorumlanan — AI Çıktısı", "en": "2. Interpreted — AI Output"},
            "lines": {
                "tr": [
                    "Yapılandırılmış Ölçüm → Model → Doğal Dil Rapor",
                    "",
                    "Yanıt her zaman dört başlıkta ayrışır:",
                    "  • Gerçek Veri",
                    "  • Yapay Zekâ Yorumu",
                    "  • Olası Nedenler",
                    "  • Öneriler",
                    "",
                    'Yorum bölümü arayüzde ayrı bir renkte ve "bu bir yapay zekâ yorumudur" etiketiyle gösterilir.',
                ],
                "en": [
                    "Structured Metrics → Model → Natural-Language Report",
                    "",
                    "The response always separates into four sections:",
                    "  • Real Data",
                    "  • AI Interpretation",
                    "  • Possible Causes",
                    "  • Recommendations",
                    "",
                    'The interpretation section is shown in a distinct colour and labelled "this is an AI interpretation".',
                ],
            },
        },
        "note": {
            "tr": 'Yapay zekâ tahminleri kesin gerçek olarak sunulmaz. Bilinmeyen için "veri yok" denir; sayı uydurulmaz.',
            "en": "AI predictions are never presented as established fact. Where data is missing the system says so rather than inventing a number.",
        },
    },
    # -----------------------------------------------------------------  23
    {
        "kind": "flow",
        "icon": "🔗",
        "title": {
            "tr": "Yapay Zekâ Kesintiye Uğrarsa Ne Olur?",
            "en": "What Happens If the AI Is Unavailable?",
        },
        "subtitle": {
            "tr": "Yapay zekâ bir kolaylıktır, bağımlılık değil. Zincirin her halkası koparsa okul yönetimi çalışmaya devam eder.",
            "en": "AI is a convenience, not a dependency. Even if every link breaks, school management keeps running.",
        },
        "steps": [
            {
                "icon": "1",
                "accent": "teal",
                "title": {"tr": "Yerel Model Denenir", "en": "Local Model First"},
                "body": {
                    "tr": "Varsayılan sağlayıcı LM Studio. Sağlık kontrolü başarılıysa istek buraya gider.",
                    "en": "The default provider is LM Studio. If the health check passes, the request goes here.",
                },
            },
            {
                "icon": "2",
                "accent": "blue",
                "title": {"tr": "Bulut Sağlayıcıya Geçilir", "en": "Fall Back to Cloud"},
                "body": {
                    "tr": "Yerel model yanıt vermezse ve anahtar tanımlıysa bulut sağlayıcı devreye girer.",
                    "en": "If the local model does not respond and a key is configured, the cloud provider takes over.",
                },
            },
            {
                "icon": "3",
                "accent": "gold",
                "title": {"tr": "Hata Kaydedilir", "en": "Error Recorded"},
                "body": {
                    "tr": "Başarısızlık zaman, süre ve hata tipiyle kaydedilir — anahtar değeri asla yazılmaz.",
                    "en": "The failure is logged with time, duration and error type — the key value is never written.",
                },
            },
            {
                "icon": "4",
                "accent": "green",
                "title": {"tr": "Sistem Çalışmaya Devam Eder", "en": "The System Keeps Running"},
                "body": {
                    "tr": "Yoklama, planlama, finans ve raporlama etkilenmez. Yalnızca yorum kutusu boş kalır.",
                    "en": "Attendance, scheduling, finance and reporting are unaffected. Only the interpretation panel stays empty.",
                },
            },
        ],
        "note": {
            "tr": "Bir gerçek uyumluluk sorunu bu yaklaşımla yakalandı: bazı yerel sunucular belirli bir yanıt biçimi alanını reddediyor. Sistem bunu algılayıp alansız yeniden dener; kullanıcı hiçbir hata görmez.",
            "en": "A real compatibility issue was caught this way: some local servers reject a particular response-format field. The system detects this and retries without it — the user never sees an error.",
        },
    },
    # -----------------------------------------------------------------  24
    {
        "kind": "rows",
        "icon": "🛠",
        "title": {"tr": "Yapay Zekâ Geliştirici Konsolu", "en": "AI Developer Console"},
        "subtitle": {
            "tr": "Yalnızca Sistem Yöneticisi erişebilir. Varsayılan ayarlarda salt okunurdur — kod değiştirmez, komut çalıştırmaz.",
            "en": "Accessible only to the System Administrator. Read-only by default — it changes no code and runs no commands.",
        },
        "items": [
            {
                "icon": "📖",
                "accent": "teal",
                "title": {"tr": "Oku · Ara · Çözümle", "en": "Read · Search · Analyse"},
                "body": {
                    "tr": "Proje dosyalarını okur, arama yapar ve yapı çözümlemesi üretir. Bu üç işlem her zaman açıktır.",
                    "en": "Reads project files, searches them and produces structural analysis. These three are always available.",
                },
            },
            {
                "icon": "📝",
                "accent": "blue",
                "title": {"tr": "Plan ve Yama Önerisi", "en": "Plan and Patch Proposal"},
                "body": {
                    "tr": "Değişiklik planı ve yama üretir; ancak üretmek ile uygulamak ayrı yetkilerdir.",
                    "en": "Produces a change plan and a patch — but generating and applying are separate permissions.",
                },
            },
            {
                "icon": "👁",
                "accent": "gold",
                "title": {"tr": "Fark Önizlemesi", "en": "Diff Preview"},
                "body": {
                    "tr": "Hiçbir değişiklik onaysız uygulanmaz. Önce satır satır fark gösterilir.",
                    "en": "No change is applied without approval. A line-by-line diff is shown first.",
                },
            },
            {
                "icon": "💾",
                "accent": "green",
                "title": {"tr": "Otomatik Kontrol Noktası", "en": "Automatic Checkpoint"},
                "body": {
                    "tr": "Önemli değişiklikten önce sürüm kontrolünde kontrol noktası oluşturulur; geri alma tek adımdır.",
                    "en": "A version-control checkpoint is created before any significant change; rollback is a single step.",
                },
            },
            {
                "icon": "🧪",
                "accent": "purple",
                "title": {"tr": "Test Çalıştırma", "en": "Test Execution"},
                "body": {
                    "tr": "Yama uygulandıktan sonra test paketi çalıştırılır; başarısızlıkta geri alma önerilir.",
                    "en": "After a patch is applied the test suite runs; on failure a rollback is offered.",
                },
            },
            {
                "icon": "🔒",
                "accent": "rose",
                "title": {"tr": "İki Ayrı Kilit", "en": "Two Separate Locks"},
                "body": {
                    "tr": "Yama uygulama ve kabuk komutu yetkileri ayrı ayarlardır ve ikisi de varsayılan olarak kapalıdır.",
                    "en": "Patch application and shell command execution are separate settings, and both are disabled by default.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  25
    {
        "kind": "panels",
        "icon": "🧑‍💼",
        "title": {
            "tr": "CAIO — Gözlemleyen, Öneren, Karar Vermeyen Ajan",
            "en": "CAIO — An Agent That Observes and Proposes, but Does Not Decide",
        },
        "subtitle": {
            "tr": "Chief AI Officer ajanı sistemi sürekli izler ve iyileştirme önerir; ancak hiçbir öneriyi kendi başına uygulamaz.",
            "en": "The Chief AI Officer agent continuously observes the system and proposes improvements — but applies none on its own.",
        },
        "left": {
            "icon": "🔄",
            "accent": "blue",
            "title": {"tr": "Çalışma Döngüsü", "en": "Operating Loop"},
            "lines": {
                "tr": [
                    "1. Gözlemle — kullanım, hata ve performans verisi",
                    "2. Çözümle — tekrar eden örüntüleri çıkar",
                    "3. Öner — somut iyileştirme önerisi üret",
                    "4. Yama Hazırla — değişikliği taslak olarak yaz",
                    "5. Test Et — mevcut test paketini çalıştır",
                    "6. Farkı Göster — satır satır önizleme",
                    "7. Kullanıcı Onayı — bekler, atlamaz",
                    "8. Uygula — yalnızca onaydan sonra",
                ],
                "en": [
                    "1. Observe — usage, error and performance data",
                    "2. Analyse — extract recurring patterns",
                    "3. Propose — produce a concrete improvement",
                    "4. Draft Patch — write the change as a draft",
                    "5. Test — run the existing test suite",
                    "6. Show Diff — line-by-line preview",
                    "7. User Approval — it waits; it never skips",
                    "8. Apply — only after approval",
                ],
            },
        },
        "right": {
            "icon": "🚧",
            "accent": "rose",
            "title": {"tr": "Kalıcı Sınırlar", "en": "Permanent Boundaries"},
            "lines": {
                "tr": [
                    "• Üretim koduna sınırsız değişiklik yapamaz",
                    "• Onay adımı yapılandırmayla atlanamaz",
                    "• Veri silme yetkisi yoktur",
                    "• Kullanıcı hesaplarına dokunamaz",
                    "• Yedekleri değiştiremez veya silemez",
                    "",
                    "Ajan bir denetçidir, bir yönetici değil. Sistemi geliştirmeyi önerir; sistemi yönetmez.",
                ],
                "en": [
                    "• Cannot make unbounded changes to production code",
                    "• The approval step cannot be configured away",
                    "• It has no permission to delete data",
                    "• It cannot touch user accounts",
                    "• It cannot modify or delete backups",
                    "",
                    "The agent is a reviewer, not an administrator. It proposes improvements; it does not run the system.",
                ],
            },
        },
    },
    # -----------------------------------------------------------------  26
    {
        "kind": "panels",
        "icon": "🚫",
        "title": {"tr": "Yapay Zekânın Terminal Sınırları", "en": "The AI's Terminal Boundaries"},
        "subtitle": {
            "tr": "Yapay zekâya sınırsız komut yetkisi verilmez. İzin verilen komutlar beyaz liste ile tanımlıdır.",
            "en": "The AI is never given unbounded command access. Permitted commands are defined by an explicit allowlist.",
        },
        "left": {
            "icon": "⛔",
            "accent": "rose",
            "title": {"tr": "Kesinlikle Engellenen", "en": "Always Blocked"},
            "lines": {
                "tr": [
                    "• Proje klasörü dışına yazma",
                    "• Sistem dosyalarını değiştirme",
                    "• Kayıt defterine (registry) müdahale",
                    "• Disk biçimlendirme veya toplu silme",
                    "• Kullanıcı hesaplarını değiştirme",
                    "• Kimlik bilgilerini okuma",
                    "• Tarayıcı parolalarına erişim",
                    "• Ortam dosyası (.env) ve yedek klasörüne erişim",
                ],
                "en": [
                    "• Writing outside the project folder",
                    "• Modifying system files",
                    "• Touching the Windows registry",
                    "• Formatting disks or bulk deletion",
                    "• Changing user accounts",
                    "• Reading credentials",
                    "• Accessing browser passwords",
                    "• Reaching the .env file or the backup folder",
                ],
            },
        },
        "right": {
            "icon": "🛡",
            "accent": "green",
            "title": {"tr": "Uygulanan Koruma Katmanları", "en": "Protection Layers in Force"},
            "lines": {
                "tr": [
                    "• Komut beyaz listesi — listede yoksa çalışmaz",
                    "• 19 ayrı tehlikeli komut deseni engellenir",
                    "• Yazılabilir dosya uzantıları sınırlıdır",
                    "• Yıkıcı işlem öncesi kullanıcı onayı istenir",
                    "• Değişiklik öncesi otomatik kontrol noktası",
                    "• Her komut denetim kaydına yazılır",
                    "",
                    "Kabuk erişimi varsayılan olarak tamamen kapalıdır ve açılması bilinçli bir ayar değişikliği gerektirir.",
                ],
                "en": [
                    "• Command allowlist — not listed means not run",
                    "• 19 distinct dangerous command patterns blocked",
                    "• Writable file extensions are restricted",
                    "• User confirmation before any destructive action",
                    "• Automatic checkpoint before changes",
                    "• Every command is written to the audit log",
                    "",
                    "Shell access is fully disabled by default and enabling it requires a deliberate configuration change.",
                ],
            },
        },
    },
    # -----------------------------------------------------------------  27
    {
        "kind": "quad",
        "icon": "💾",
        "title": {
            "tr": "Yedekleme — 7 Tür, 11 Bütünlük Kontrolü",
            "en": "Backup — 7 Types, 11 Integrity Checks",
        },
        "subtitle": {
            "tr": "Yedek yalnızca dosya kopyası değildir: imzalanır, doğrulanır ve geri yüklenebilirliği sınanır.",
            "en": "A backup is more than a file copy: it is signed, verified and tested for restorability.",
        },
        "items": [
            {
                "icon": "📦",
                "accent": "teal",
                "title": {"tr": "7 Yedek Türü", "en": "7 Backup Types"},
                "body": {
                    "tr": "Tam, artımlı, elle, zamanlanmış, güncelleme öncesi, göç öncesi ve güvenlik yedeği. Her türün kendi saklama kuralı vardır.",
                    "en": "Full, incremental, manual, scheduled, pre-update, pre-migration and safety. Each type has its own retention rule.",
                },
            },
            {
                "icon": "🔏",
                "accent": "blue",
                "title": {"tr": "SHA-256 İmzalı Manifest", "en": "SHA-256 Signed Manifest"},
                "body": {
                    "tr": "Her yedek bir manifest dosyası taşır: içerik listesi, boyut, tarih ve her dosyanın SHA-256 özeti.",
                    "en": "Every backup carries a manifest: content listing, size, timestamp and a SHA-256 digest for each file.",
                },
            },
            {
                "icon": "🔍",
                "accent": "green",
                "title": {"tr": "11 Bütünlük Kontrolü", "en": "11 Integrity Checks"},
                "body": {
                    "tr": "Arşiv açılabiliyor mu, manifest tutarlı mı, özetler eşleşiyor mu, veritabanı okunabiliyor mu — hepsi ayrı ayrı sınanır.",
                    "en": "Can the archive open, is the manifest consistent, do the digests match, is the database readable — each is tested separately.",
                },
            },
            {
                "icon": "🔐",
                "accent": "rose",
                "title": {"tr": "Sırlar Yedeğe Girmez", "en": "Secrets Stay Out"},
                "body": {
                    "tr": "API anahtarları, parolalar ve güvenlik sırları yedek paketine açık metin olarak dahil edilmez — arşiv taranarak doğrulandı.",
                    "en": "API keys, passwords and security secrets are never included in plain text — verified by scanning the archive itself.",
                },
            },
        ],
        "note": {
            "tr": "Veritabanı yedeği çevrimiçi yedekleme arayüzüyle alınır: sistem çalışırken tutarlı bir kopya çıkarılır, kimsenin işi durmaz.",
            "en": "The database is captured through the online backup API: a consistent copy is taken while the system runs, interrupting no one.",
        },
    },
    # -----------------------------------------------------------------  28
    {
        "kind": "flow",
        "icon": "♻️",
        "title": {
            "tr": "Güvenli Geri Yükleme — Gerçekten Denendi",
            "en": "Safe Restore — Actually Exercised",
        },
        "subtitle": {
            "tr": "Geri yükleme akışı canlı veri üzerinde çalıştırılarak doğrulandı; aşağıdaki adımlar gerçek bir çalıştırmadan alınmıştır.",
            "en": "The restore flow was validated against live data; the steps below come from an actual run.",
        },
        "steps": [
            {
                "icon": "1",
                "accent": "blue",
                "title": {"tr": "Önizleme", "en": "Preview"},
                "body": {
                    "tr": 'Neyin değişeceği önce gösterilir: "3 öğrenci kaybolacak" gibi somut uyarılarla.',
                    "en": 'What will change is shown first, with concrete warnings such as "3 students will be lost".',
                },
            },
            {
                "icon": "2",
                "accent": "gold",
                "title": {"tr": "Güvenlik Yedeği", "en": "Safety Backup"},
                "body": {
                    "tr": "Geri yüklemeden hemen önce mevcut durumun yedeği otomatik alınır.",
                    "en": "A backup of the current state is taken automatically, immediately before the restore.",
                },
            },
            {
                "icon": "3",
                "accent": "teal",
                "title": {"tr": "Doğrulama", "en": "Verification"},
                "body": {
                    "tr": "Geri yüklenecek arşivin bütünlüğü 11 kontrolle sınanır; bozuksa işlem başlamaz.",
                    "en": "The archive's integrity is tested with 11 checks; if it is corrupt the process never starts.",
                },
            },
            {
                "icon": "4",
                "accent": "green",
                "title": {"tr": "Adım Adım Uygulama", "en": "Stepwise Application"},
                "body": {
                    "tr": "İşlem 6 adımda ilerler ve her adımın sonucu ayrı ayrı raporlanır.",
                    "en": "The operation proceeds in 6 steps, each reporting its own result.",
                },
            },
            {
                "icon": "5",
                "accent": "rose",
                "title": {"tr": "Başarısızlıkta Geri Alma", "en": "Rollback on Failure"},
                "body": {
                    "tr": "Herhangi bir adım başarısız olursa güvenlik yedeğinden otomatik dönülür.",
                    "en": "If any step fails, the system automatically reverts from the safety backup.",
                },
            },
        ],
        "note": {
            "tr": "Bulut yedekleme bilinçli olarak yazılmadı: kullanıcı izni olmadan hiçbir veri kurum dışına gönderilmez. Sağlayıcı soyutlaması hazırdır, bağlanacak hedefi kurum seçer.",
            "en": "Cloud backup was deliberately left out: no data leaves the organisation without explicit consent. The provider abstraction is ready; the destination is the institution's choice.",
        },
    },
    # -----------------------------------------------------------------  29
    {
        "kind": "quad",
        "icon": "🔒",
        "title": {"tr": "Güvenlik ve Kişisel Veri Koruması", "en": "Security and Personal Data Protection"},
        "subtitle": {
            "tr": "Yüzme okulu verisi çocuk verisidir; sistem bu sorumlulukla tasarlandı.",
            "en": "Swimming school data is children's data; the system was designed with that responsibility in mind.",
        },
        "items": [
            {
                "icon": "🔑",
                "accent": "teal",
                "title": {"tr": "Kimlik Doğrulama", "en": "Authentication"},
                "body": {
                    "tr": "Parolalar bcrypt ile 12 tur özetlenir. Erişim ve yenileme belirteci ayrıdır; yanıt süresi saldırıya ipucu vermez.",
                    "en": "Passwords are hashed with bcrypt at 12 rounds. Access and refresh tokens are separate, and response timing leaks nothing.",
                },
            },
            {
                "icon": "🛡",
                "accent": "blue",
                "title": {"tr": "Girdi ve Saldırı Koruması", "en": "Input and Attack Protection"},
                "body": {
                    "tr": "Şema doğrulaması, SQL enjeksiyonuna karşı parametreli sorgu, XSS ve CSRF koruması, istek hızı sınırlaması ve güvenli başlıklar.",
                    "en": "Schema validation, parameterised queries against SQL injection, XSS and CSRF protection, rate limiting and secure headers.",
                },
            },
            {
                "icon": "📜",
                "accent": "gold",
                "title": {"tr": "Denetim Kaydı", "en": "Audit Log"},
                "body": {
                    "tr": "Kim, ne zaman, neyi değiştirdi — kritik işlemler kalıcı olarak kaydedilir ve sonradan düzenlenemez.",
                    "en": "Who changed what and when — critical operations are recorded permanently and cannot be edited afterwards.",
                },
            },
            {
                "icon": "🙈",
                "accent": "rose",
                "title": {"tr": "Sır Yönetimi", "en": "Secret Management"},
                "body": {
                    "tr": "Anahtarlar ve parolalar kayıtlara yazılmaz; ekranda maskelenir. Gönderim öncesi kod tabanı otomatik sır taramasından geçer.",
                    "en": "Keys and passwords are never logged and are masked on screen. The codebase passes an automatic secret scan before every push.",
                },
            },
        ],
        "note": {
            "tr": "KVKK / GDPR veri minimizasyonu: her rol yalnızca görevi için gereken alanları alır. Sağlık notu gibi hassas alanlar yetkisiz rollere hiç gönderilmez.",
            "en": "KVKK / GDPR data minimisation: each role receives only the fields its duties require. Sensitive fields such as health notes are never sent to unauthorised roles.",
        },
    },
    # -----------------------------------------------------------------  30
    {
        "kind": "panels",
        "icon": "🌐",
        "title": {
            "tr": "Gerçek İki Dillilik — Arayüz ve Veri Katmanı",
            "en": "Genuine Bilingualism — Interface and Data Layer",
        },
        "subtitle": {
            "tr": "Dil değişimi yalnızca etiketleri çevirmez; tarih, sayı, para birimi ve yapay zekâ yanıt dili birlikte değişir.",
            "en": "Switching language does more than translate labels: dates, numbers, currency and the AI response language change with it.",
        },
        "left": {
            "icon": "🇹🇷",
            "accent": "teal",
            "title": {"tr": "Türkçe (Varsayılan)", "en": "Turkish (Default)"},
            "lines": {
                "tr": [
                    "Tarih:  18.08.2026",
                    "Saat:   14:30",
                    "Sayı:   1.250,50",
                    "Para:   1.250,50 ₺",
                    "",
                    "1.027 çeviri anahtarı — eksik yok.",
                    "",
                    "Tüm dosyalar UTF-8 kodlamasıyla yazılır; ı, ğ, ş, ç, ö, ü karakterleri arayüzde, PDF çıktısında ve CSV dosyalarında sorunsuz görünür.",
                ],
                "en": [
                    "Date:     18.08.2026",
                    "Time:     14:30",
                    "Number:   1.250,50",
                    "Currency: 1.250,50 ₺",
                    "",
                    "1,020 translation keys — none missing.",
                    "",
                    "Everything is written in UTF-8, so Turkish characters render correctly in the interface, in PDF output and in CSV files.",
                ],
            },
        },
        "right": {
            "icon": "🇬🇧",
            "accent": "blue",
            "title": {"tr": "İngilizce", "en": "English"},
            "lines": {
                "tr": [
                    "Tarih:  18/08/2026",
                    "Saat:   2:30 PM",
                    "Sayı:   1,250.50",
                    "Para:   ₺1,250.50",
                    "",
                    "1.027 çeviri anahtarı — eksik yok.",
                    "",
                    "Yapay zekâ yanıt dili ayrı bir ayardır: arayüzü İngilizce kullanıp raporları Türkçe alabilirsiniz.",
                ],
                "en": [
                    "Date:     18/08/2026",
                    "Time:     2:30 PM",
                    "Number:   1,250.50",
                    "Currency: ₺1,250.50",
                    "",
                    "1,020 translation keys — none missing.",
                    "",
                    "AI response language is a separate setting: you can use an English interface and still receive Turkish reports.",
                ],
            },
        },
        "note": {
            "tr": "Çeviri bütünlüğü otomatik denetlenir: kalite kapısı iki dil arasındaki her eksik anahtarı yakalar ve yayını durdurur.",
            "en": "Translation completeness is checked automatically: the quality gate catches any key missing on either side and stops the release.",
        },
    },
    # -----------------------------------------------------------------  31
    {
        "kind": "rows",
        "icon": "🎓",
        "title": {"tr": "Uygulama İçi Eğitim Merkezi", "en": "In-App Training Centre"},
        "subtitle": {
            "tr": "Kullanıcı kılavuzu ayrı bir belge değil, programın içindedir — ve rolünüze göre şekillenir.",
            "en": "The user guide is not a separate document; it lives inside the program and adapts to your role.",
        },
        "items": [
            {
                "icon": "📚",
                "accent": "teal",
                "title": {"tr": "28 Kılavuz Konusu", "en": "28 Guide Topics"},
                "body": {
                    "tr": "Öğrenci kaydından yedek geri yüklemeye kadar her modül için adım adım anlatım, arama kutusuyla.",
                    "en": "Step-by-step coverage for every module, from student enrolment to backup restore, with a search box.",
                },
            },
            {
                "icon": "🖐",
                "accent": "blue",
                "title": {"tr": "12 Etkileşimli Eğitim", "en": "12 Interactive Tutorials"},
                "body": {
                    "tr": "Ekranda yönlendirmeli alıştırmalar; ilerleme kaydedilir, yarıda bırakıp devam edebilirsiniz.",
                    "en": "Guided on-screen exercises with saved progress, so you can stop and resume later.",
                },
            },
            {
                "icon": "🧭",
                "accent": "gold",
                "title": {"tr": "9 Adımlı Kurulum Sihirbazı", "en": "9-Step Onboarding Wizard"},
                "body": {
                    "tr": "İlk açılışta hangi adımların tamamlandığını gerçek veriden okur; boş kurulumu adım adım tamamlatır.",
                    "en": "On first launch it reads completed steps from real data and walks you through the remaining setup.",
                },
            },
            {
                "icon": "👤",
                "accent": "purple",
                "title": {"tr": "Role Göre İçerik", "en": "Role-Aware Content"},
                "body": {
                    "tr": "21 rolün her biri için ayrı eğitim izleği; muhasebeye havuz kimyasalı anlatılmaz.",
                    "en": "A dedicated learning track for each of the 21 roles — accounting is not taught pool chemistry.",
                },
            },
            {
                "icon": "💡",
                "accent": "green",
                "title": {"tr": "Bağlamsal Yardım", "en": "Contextual Help"},
                "body": {
                    "tr": "Her ekranda o ekrana ait yardım; ilgili eğitime tek tıkla geçiş.",
                    "en": "Help specific to the screen you are on, with one-click access to the related tutorial.",
                },
            },
            {
                "icon": "🧪",
                "accent": "rose",
                "title": {"tr": "Eğitim Modu", "en": "Training Mode"},
                "body": {
                    "tr": "Yeni personel demo veri üzerinde çalışır; gerçek kayıtlara dokunmadan pratik yapar.",
                    "en": "New staff practise on demo data, without touching a single real record.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  32
    {
        "kind": "rows",
        "icon": "⚡",
        "title": {"tr": "Günlük Kullanımı Hızlandıran Ayrıntılar", "en": "Details That Speed Up Daily Use"},
        "subtitle": {
            "tr": "Bir yönetim sistemi günde yüzlerce kez açılır; küçük sürtünmeler büyük zaman kaybına dönüşür.",
            "en": "A management system is opened hundreds of times a day; small frictions become large time losses.",
        },
        "items": [
            {
                "icon": "🔍",
                "accent": "teal",
                "title": {"tr": "Global Arama", "en": "Global Search"},
                "body": {
                    "tr": "Öğrenci, veli, eğitmen, ders ve havuz aynı arama kutusundan bulunur; sonuçlar türüne göre gruplanır.",
                    "en": "Students, guardians, instructors, lessons and pools from one box, with results grouped by type.",
                },
            },
            {
                "icon": "⌨️",
                "accent": "blue",
                "title": {"tr": "Ctrl+K Komut Paleti", "en": "Ctrl+K Command Palette"},
                "body": {
                    "tr": "Fareye dokunmadan her ekrana ve her sık işleme klavyeden erişim.",
                    "en": "Reach every screen and every frequent action from the keyboard, without touching the mouse.",
                },
            },
            {
                "icon": "🔔",
                "accent": "gold",
                "title": {"tr": "12 Bildirim Türü", "en": "12 Notification Types"},
                "body": {
                    "tr": "Üyelik bitişi, gecikmiş ödeme, ders iptali, eğitmen izni, havuz bakımı, performans düşüşü ve daha fazlası.",
                    "en": "Membership expiry, overdue payment, lesson cancellation, instructor leave, pool maintenance, performance drop and more.",
                },
            },
            {
                "icon": "🌓",
                "accent": "purple",
                "title": {"tr": "Koyu ve Açık Tema", "en": "Dark and Light Theme"},
                "body": {
                    "tr": "Havuz kenarındaki tablette koyu, ofiste açık; tercih kullanıcı bazında saklanır.",
                    "en": "Dark on the poolside tablet, light in the office; the preference is stored per user.",
                },
            },
            {
                "icon": "📱",
                "accent": "green",
                "title": {"tr": "Duyarlı Tasarım", "en": "Responsive Design"},
                "body": {
                    "tr": "Masaüstü, tablet ve telefonda çalışır — yoklama havuz kenarından telefonla girilebilir.",
                    "en": "Works on desktop, tablet and phone — attendance can be entered poolside from a handset.",
                },
            },
            {
                "icon": "🖥",
                "accent": "rose",
                "title": {"tr": "Masaüstü Uygulaması", "en": "Desktop Application"},
                "body": {
                    "tr": "Tek tıkla açılan Windows uygulaması; tarayıcı gerektirmez, düşük bellek kullanır.",
                    "en": "A one-click Windows application that needs no browser and keeps memory usage low.",
                },
            },
        ],
    },
    # -----------------------------------------------------------------  33
    {
        "kind": "panels",
        "icon": "🏗",
        "title": {"tr": "Teknoloji Temeli", "en": "Technology Foundation"},
        "subtitle": {
            "tr": "Tamamı açık kaynak, tamamı izin veren lisanslı (MIT / BSD / Apache-2.0). Kapalı bağımlılık yoktur.",
            "en": "Entirely open source under permissive licences (MIT / BSD / Apache-2.0). There are no closed dependencies.",
        },
        "left": {
            "icon": "⚙️",
            "accent": "teal",
            "title": {"tr": "Sunucu Tarafı", "en": "Server Side"},
            "lines": {
                "tr": [
                    "• Python 3.11 · FastAPI · SQLAlchemy 2.0",
                    "• Pydantic şema doğrulaması · Alembic göçleri",
                    "• SQLite ile kurulur, PostgreSQL'e hazır",
                    "• numpy ve pandas ile istatistik motoru",
                    "• reportlab (PDF) · openpyxl (Excel)",
                    "• 395 otomatik test · ruff · black · mypy",
                    "",
                    "Bağımlılıklar güvenlik taramasından geçer: bilinen açık bulunmuyor.",
                ],
                "en": [
                    "• Python 3.11 · FastAPI · SQLAlchemy 2.0",
                    "• Pydantic schema validation · Alembic migrations",
                    "• Ships on SQLite, ready for PostgreSQL",
                    "• Statistics engine on numpy and pandas",
                    "• reportlab (PDF) · openpyxl (Excel)",
                    "• 395 automated tests · ruff · black · mypy",
                    "",
                    "Dependencies pass a security audit with no known vulnerabilities.",
                ],
            },
        },
        "right": {
            "icon": "🖼",
            "accent": "blue",
            "title": {"tr": "İstemci Tarafı", "en": "Client Side"},
            "lines": {
                "tr": [
                    "• React 18 · TypeScript (katı kip) · Vite",
                    "• Tailwind CSS · koyu ve açık tema",
                    "• TanStack Query ile veri eşzamanlaması",
                    "• Recharts ile grafikler",
                    "• react-i18next ile TR/EN",
                    "• Masaüstü sarmalayıcı: WebView2 (düşük bellek)",
                    "",
                    "Tip denetimi ve lint kuralları sıfır uyarı ile geçer.",
                ],
                "en": [
                    "• React 18 · TypeScript (strict) · Vite",
                    "• Tailwind CSS · dark and light themes",
                    "• Data synchronisation with TanStack Query",
                    "• Charts with Recharts",
                    "• TR/EN via react-i18next",
                    "• Desktop shell: WebView2 (low memory)",
                    "",
                    "Type checking and lint rules pass with zero warnings.",
                ],
            },
        },
        "note": {
            "tr": "Sürekli tümleştirme her değişiklikte testleri, tip denetimini, lint kurallarını, derlemeyi ve sır taramasını çalıştırır.",
            "en": "Continuous integration runs tests, type checking, lint rules, the build and a secret scan on every change.",
        },
    },
    # -----------------------------------------------------------------  34
    {
        "kind": "flow",
        "icon": "🔄",
        "title": {"tr": "Bir Gün — Uçtan Uca Akış", "en": "A Single Day — End to End"},
        "subtitle": {
            "tr": "Sabah açılıştan akşam kapanışa, aynı veri altı farklı rolde altı farklı işe dönüşür.",
            "en": "From morning opening to evening close, the same data serves six different roles in six different ways.",
        },
        "steps": [
            {
                "icon": "1",
                "accent": "teal",
                "title": {"tr": "08:00 · Resepsiyon", "en": "08:00 · Reception"},
                "body": {
                    "tr": "Panoyu açar: bugünün dersleri, gecikmiş ödemeler ve bitmek üzere olan üyelikler.",
                    "en": "Opens the dashboard: today's lessons, overdue payments and memberships about to expire.",
                },
            },
            {
                "icon": "2",
                "accent": "blue",
                "title": {"tr": "10:00 · Antrenör", "en": "10:00 · Coach"},
                "body": {
                    "tr": "Havuz kenarında tabletten yoklama girer; üyelik hakları anında düşer.",
                    "en": "Enters attendance from a poolside tablet; membership entitlements are deducted instantly.",
                },
            },
            {
                "icon": "3",
                "accent": "gold",
                "title": {"tr": "13:00 · Baş Antrenör", "en": "13:00 · Head Coach"},
                "body": {
                    "tr": "Yarışma takımının split sürelerini girer; kişisel rekor kırılınca bildirim düşer.",
                    "en": "Records the competition squad's splits; a personal best triggers a notification.",
                },
            },
            {
                "icon": "4",
                "accent": "green",
                "title": {"tr": "16:00 · Muhasebe", "en": "16:00 · Accounting"},
                "body": {
                    "tr": "Tahsilatları işler, gecikmiş alacak raporunu Excel olarak dışa aktarır.",
                    "en": "Posts collections and exports the overdue receivables report to Excel.",
                },
            },
            {
                "icon": "5",
                "accent": "purple",
                "title": {"tr": "18:00 · Müdür", "en": "18:00 · Director"},
                "body": {
                    "tr": "İstatistik merkezinden doluluk ısı haritasını inceler, yapay zekâdan yorum ister.",
                    "en": "Reviews the occupancy heatmap in the statistics centre and asks the AI for an interpretation.",
                },
            },
            {
                "icon": "6",
                "accent": "rose",
                "title": {"tr": "23:00 · Sistem", "en": "23:00 · System"},
                "body": {
                    "tr": "Zamanlanmış yedek alınır, bütünlüğü doğrulanır, sonucu bildirime yazılır.",
                    "en": "The scheduled backup runs, its integrity is verified and the outcome is written to notifications.",
                },
            },
        ],
        "note": {
            "tr": "Altı rolün hiçbiri diğerinin verisini göremez; ancak hepsi aynı tek doğruluk kaynağı üzerinde çalışır.",
            "en": "None of the six roles can see another's data — yet all of them work on the same single source of truth.",
        },
    },
    # -----------------------------------------------------------------  35
    {
        "kind": "closing",
        "title": {"tr": "Planla.  Ölç.  Geliştir.", "en": "Plan.  Measure.  Improve."},
        "subtitle": {
            "tr": "Yüzme okulunuzun tüm işleyişi tek platformda — verisi sizde kalarak, yapay zekâsı isteğe bağlı olarak.",
            "en": "Your swimming school's entire operation on one platform — your data stays yours, and the AI stays optional.",
        },
        "items": [
            {
                "icon": "🏫",
                "accent": "teal",
                "title": {"tr": "Okul işletmesi\ntek sistemde", "en": "School operations\nin one system"},
            },
            {
                "icon": "📅",
                "accent": "blue",
                "title": {"tr": "Çakışmasız\nakıllı planlama", "en": "Conflict-free\nsmart scheduling"},
            },
            {
                "icon": "📈",
                "accent": "gold",
                "title": {"tr": "Ölçülebilir\nsporcu gelişimi", "en": "Measurable\nathlete progress"},
            },
            {
                "icon": "🤖",
                "accent": "purple",
                "title": {"tr": "Yerel çalışan\nyapay zekâ", "en": "AI that runs\nlocally"},
            },
            {
                "icon": "🛡",
                "accent": "green",
                "title": {"tr": "Yedekli ve\nkurtarılabilir", "en": "Backed up and\nrecoverable"},
            },
        ],
        "note": {
            "tr": "Bu sürüm bir yayın adayıdır (v0.9.0). Okul yönetimi, planlama, finans, performans ve yedekleme modülleri üretime hazırdır; yapay zekâ geliştirici ajanı deneysel olarak işaretlenmiştir ve varsayılan olarak salt okunur çalışır.",
            "en": "This is a release candidate (v0.9.0). The school management, scheduling, finance, performance and backup modules are production-ready; the AI developer agent is marked experimental and runs read-only by default.",
        },
        "footer": {
            "tr": "MIT lisansı · Kurum içi kurulum · Windows masaüstü ve web · Türkçe / İngilizce",
            "en": "MIT licence · On-premise deployment · Windows desktop and web · Turkish / English",
        },
    },
]
