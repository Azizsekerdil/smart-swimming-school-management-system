"""Ekran görüntüsü slaytları / Screenshot slides.

Bu slaytlar `presentation_content.DECK` içindeki anlatıya **serpiştirilir**:
her ekran, kendisini anlatan özellik slaytının hemen ardından gelir. Böylece
"ne yapıyor" ile "nasıl görünüyor" yan yana okunur.

Görseller `tools/capture_screens.py` ile **çalışan uygulamadan** alınır. Hiçbir
ekran elle çizilmez, taklit edilmez veya mockup ile değiştirilmez. Koyu deste
koyu arayüzü, baskı destesi açık arayüzü gösterir.

`after` alanı, slaytın hangi başlıktan sonra ekleneceğini belirtir (Türkçe
başlıkla eşleşir). Eşleşme bulunamazsa üretim hata verir — sessizce yanlış yere
eklenmez.
"""

from __future__ import annotations


def _p(icon_accent: str, title_tr: str, title_en: str, body_tr: str, body_en: str) -> dict:
    return {
        "accent": icon_accent,
        "title": {"tr": title_tr, "en": title_en},
        "body": {"tr": body_tr, "en": body_en},
    }


SHOTS: list[dict] = [
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Sayılarla Sistem",
        "shot": "dashboard",
        "icon": "🖥",
        "title": {"tr": "Kontrol Paneli", "en": "Dashboard"},
        "subtitle": {
            "tr": "Açılışta okulun bugünkü durumu: bekleyen işler, canlı sayılar ve günün programı.",
            "en": "The school's status on open: pending actions, live figures and today's schedule.",
        },
        "points": [
            _p(
                "rose",
                "Bekleyen işler üstte",
                "Pending actions first",
                "Geciken ödeme, bitmek üzere olan üyelik, alınmamış yoklama ve performans düşüşü uyarı şeridi olarak gösterilir.",
                "Overdue payments, expiring memberships, missing attendance and performance drops appear as alert strips.",
            ),
            _p(
                "teal",
                "12 canlı gösterge",
                "12 live indicators",
                "Aktif öğrenci, bugünkü ders, havuz doluluk, aylık gelir, net gelir ve geciken tahsilat tek bakışta.",
                "Active students, today's lessons, pool occupancy, monthly income, net income and overdue collection at a glance.",
            ),
            _p(
                "blue",
                "Günün programı",
                "Today's schedule",
                "Saat, ders, havuz, kulvar, eğitmen ve doluluk oranı; ders durumu renk kodlu.",
                "Time, lesson, pool, lane, instructor and occupancy, with colour-coded lesson state.",
            ),
            _p(
                "purple",
                "Role göre içerik",
                "Role-aware content",
                "Muhasebe finansal göstergeleri, antrenör devam ve gelişim göstergelerini görür.",
                "Accounting sees financial indicators; a coach sees attendance and progress.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "gallery",
        "after": "21 Rol, 52 İzin — Herkes Yalnızca Kendi Verisini Görür",
        "icon": "🗂",
        "title": {"tr": "Arayüzden Kesitler", "en": "A Look Across the Interface"},
        "subtitle": {
            "tr": "Aynı tasarım dili 24 ekranda tutarlı: sol gezinti, üstte arama ve rol rozeti, içerikte kart ızgarası.",
            "en": "One design language across 24 screens: left navigation, search and role badge on top, card grid in the content area.",
        },
        "columns": 3,
        "items": [
            {"shot": "login", "title": {"tr": "Giriş", "en": "Sign in"}},
            {"shot": "student_detail", "title": {"tr": "Öğrenci Detayı", "en": "Student Detail"}},
            {"shot": "guardians", "title": {"tr": "Veliler", "en": "Guardians"}},
            {"shot": "instructors", "title": {"tr": "Eğitmenler", "en": "Instructors"}},
            {"shot": "pools", "title": {"tr": "Havuzlar", "en": "Pools"}},
            {"shot": "lessons", "title": {"tr": "Dersler", "en": "Lessons"}},
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Öğrenci ve Veli Yönetimi",
        "shot": "students",
        "icon": "🎓",
        "title": {"tr": "Öğrenci Listesi", "en": "Student List"},
        "subtitle": {
            "tr": "50 öğrencinin tamamı tek listede; seviye, durum ve grup süzgeçleriyle saniyede daraltılır.",
            "en": "All 50 students in one list, narrowed in seconds by level, status and group filters.",
        },
        "points": [
            _p(
                "teal",
                "Süzme ve arama",
                "Filter and search",
                "Ada, seviyeye, duruma ve gruba göre süzme; üstteki global aramadan da erişilir.",
                "Filter by name, level, status and group; also reachable from the global search bar.",
            ),
            _p(
                "blue",
                "Durum rozetleri",
                "Status badges",
                "Aktif, pasif, deneme, dondurulmuş ve ayrıldı durumları renk kodlu rozetlerle ayrışır.",
                "Active, passive, trial, frozen and left are separated by colour-coded badges.",
            ),
            _p(
                "gold",
                "Satır düzeyi yetki",
                "Row-level authorisation",
                "Antrenör yalnızca kendi derslerindeki öğrencileri, veli yalnızca kendi çocuğunu görür.",
                "A coach sees only students in their own lessons; a guardian only their own child.",
            ),
            _p(
                "green",
                "Demo kaydı işaretli",
                "Demo records flagged",
                'Deneme verisi arayüzde her zaman "demo" olarak gösterilir; gerçek veriyle karışmaz.',
                'Demo data is always shown as "demo" and never mixes with real records.',
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Çok Havuzlu Tesis ve Kulvar Yönetimi",
        "shot": "lane_plan",
        "icon": "🛟",
        "title": {"tr": "Kulvar Planı", "en": "Lane Plan"},
        "subtitle": {
            "tr": "Hangi kulvarda hangi ders var, hangi kulvar boş — gün ve saat bazında tek bakışta.",
            "en": "Which lesson occupies which lane and which lanes are free — by day and hour, at a glance.",
        },
        "points": [
            _p(
                "teal",
                "Kulvar ızgarası",
                "Lane grid",
                "Her havuzun kulvarları ayrı satır; saat dilimleri sütun olarak yerleşir.",
                "Each pool's lanes form rows and time slots form columns.",
            ),
            _p(
                "gold",
                "Boş kapasite görünür",
                "Idle capacity is visible",
                "Doluluk oranı ve boş kulvarlar ayrı gösterilir; atıl kapasite gizlenmez.",
                "Occupancy rate and free lanes are shown separately; idle capacity is not hidden.",
            ),
            _p(
                "rose",
                "Bakımdaki havuz",
                "Pool under maintenance",
                "Bakıma alınan havuzun kulvarlarına yeni ders atanamaz; mevcut dersler uyarıyla listelenir.",
                "Lanes of a pool under maintenance accept no new lessons; existing ones are flagged.",
            ),
            _p(
                "blue",
                "Çakışma anında görünür",
                "Conflicts surface instantly",
                "Aynı kulvara çakışan saat atanmaya çalışıldığında engel gerekçesiyle birlikte gösterilir.",
                "Attempting an overlapping lane booking is blocked with an explicit reason.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Akıllı Ders Planlama",
        "shot": "calendar",
        "icon": "📆",
        "title": {"tr": "Takvim", "en": "Calendar"},
        "subtitle": {
            "tr": "Gün, hafta ve ay görünümü; sürükle-bırak ile taşıma ve anında çakışma denetimi.",
            "en": "Day, week and month views, drag-and-drop rescheduling and instant conflict checking.",
        },
        "points": [
            _p(
                "teal",
                "Üç görünüm",
                "Three views",
                "Gün, hafta ve ay arasında geçiş; her görünümde aynı süzgeçler geçerlidir.",
                "Switch between day, week and month; the same filters apply in every view.",
            ),
            _p(
                "blue",
                "Sürükle-bırak",
                "Drag and drop",
                "Ders taşındığı anda eğitmen, kulvar ve öğrenci çakışması yeniden denetlenir.",
                "The moment a lesson is moved, instructor, lane and student conflicts are re-checked.",
            ),
            _p(
                "purple",
                "Tekrarlı seriler",
                "Recurring series",
                "Haftalık tekrar tanımlanır, dönem boyunca üretilir; tek tarihte iptal seriyi bozmaz.",
                "Define a weekly pattern, generate the term; cancelling one date does not break the series.",
            ),
            _p(
                "gold",
                "Renk kodlu durum",
                "Colour-coded state",
                "Planlandı, devam ediyor, tamamlandı, iptal ve ertelendi ayrı renklerle gösterilir.",
                "Scheduled, in progress, completed, cancelled and postponed each have their own colour.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Yoklama — 6 Durum, Birden Çok Yöntem",
        "shot": "attendance",
        "icon": "✅",
        "title": {"tr": "Yoklama Ekranı", "en": "Attendance Screen"},
        "subtitle": {
            "tr": "Bir dersin tüm öğrencileri tek listede işaretlenir; üyelik hakkı aynı anda düşer.",
            "en": "Mark every student of a lesson in one list; membership entitlement is deducted at the same moment.",
        },
        "points": [
            _p(
                "teal",
                "Toplu işaretleme",
                "Bulk marking",
                "Dersin katılımcıları tek ekranda; her satır için altı durumdan biri seçilir.",
                "All participants on one screen, each row taking one of six states.",
            ),
            _p(
                "blue",
                "Hak düşümü otomatik",
                "Automatic deduction",
                '"Geldi" işaretlenince ders hakkı düşer; mazeretli devamsızlıkta düşmez.',
                "Marking present deducts a lesson; an excused absence does not.",
            ),
            _p(
                "gold",
                "Kim, ne zaman, nasıl",
                "Who, when and how",
                "Her kayıt girenin kimliği, zamanı ve yöntemiyle (manuel, QR, kart) saklanır.",
                "Every record stores who entered it, when, and by which method (manual, QR, card).",
            ),
            _p(
                "green",
                "Havuz kenarından",
                "From the poolside",
                "Duyarlı tasarım sayesinde tabletten ve telefondan da girilebilir.",
                "Responsive design allows entry from a tablet or phone.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Üyelik ve Paket Yönetimi",
        "shot": "memberships",
        "icon": "🎫",
        "title": {"tr": "Üyelikler", "en": "Memberships"},
        "subtitle": {
            "tr": "Aktif, dondurulmuş ve süresi yaklaşan üyelikler; kalan hak ve bitiş tarihiyle birlikte.",
            "en": "Active, frozen and soon-expiring memberships, with remaining entitlement and end date.",
        },
        "points": [
            _p(
                "teal",
                "7 paket türü",
                "7 package types",
                "Ders paketi, aylık, 3 aylık, 6 aylık, yıllık, özel ders paketi ve deneme.",
                "Lesson pack, monthly, quarterly, biannual, annual, private pack and trial.",
            ),
            _p(
                "blue",
                "Kalan hak görünür",
                "Remaining entitlement visible",
                "Kaç ders kaldığı ve bitiş tarihi her satırda gösterilir.",
                "Lessons remaining and the end date are shown on every row.",
            ),
            _p(
                "gold",
                "Dondurma ve yenileme",
                "Freeze and renew",
                "Dondurulan üyeliğin kalan günü korunur; çözüldüğünde bitiş tarihi ileri alınır.",
                "Freezing preserves remaining days; on resume the end date is extended.",
            ),
            _p(
                "rose",
                "14 gün uyarısı",
                "14-day alert",
                "Bitmek üzere olan üyelikler panoda ve bildirimlerde ayrıca listelenir.",
                "Memberships about to expire are also listed on the dashboard and in notifications.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Finans Modülü",
        "shot": "finance",
        "icon": "💰",
        "title": {"tr": "Finans", "en": "Finance"},
        "subtitle": {
            "tr": "Gelir ve gider tek defterde; tahsilat durumu ve gecikmiş alacaklar ayrı izlenir.",
            "en": "Income and expenses in one ledger, with collection status and overdue receivables tracked separately.",
        },
        "points": [
            _p(
                "teal",
                "6 ödeme durumu",
                "6 payment states",
                "Ödendi, beklemede, kısmi, gecikmiş, iade ve iptal; kısmi ödemede bakiye otomatik hesaplanır.",
                "Paid, pending, partial, overdue, refunded and cancelled; balance is computed automatically.",
            ),
            _p(
                "rose",
                "Gecikme takibi",
                "Overdue tracking",
                "Gecikmiş fatura sayısı, toplam tutar ve gecikme günü ayrı gösterilir.",
                "Overdue invoice count, total amount and days late are surfaced separately.",
            ),
            _p(
                "gold",
                "10 gider kategorisi",
                "10 expense categories",
                "Maaş, kira, kimyasal, bakım, ekipman ve diğerleri; havuz bakımı doğrudan buraya işlenir.",
                "Salary, rent, chemicals, maintenance, equipment and more; pool upkeep posts straight here.",
            ),
            _p(
                "blue",
                "Türkçe para biçimi",
                "Turkish currency format",
                "Tutarlar 1.250,50 ₺ biçiminde; dil değişince sayı ve tarih biçimi de birlikte değişir.",
                "Amounts follow the 1.250,50 ₺ format; switching language changes number and date formats too.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Performans Analizi — Ölçülebilir Gelişim",
        "shot": "performance",
        "icon": "⏱",
        "title": {"tr": "Performans", "en": "Performance"},
        "subtitle": {
            "tr": "Derece geçmişi, kişisel rekorlar ve gelişim eğilimi; antrenman ile yarışma aynı modelde.",
            "en": "Time history, personal bests and progress trend, with training and competition in one model.",
        },
        "points": [
            _p(
                "teal",
                "5 stil, serbest mesafe",
                "5 strokes, any distance",
                "Serbest, sırtüstü, kurbağalama, kelebek ve karışık; mesafe serbest tanımlanır.",
                "Freestyle, backstroke, breaststroke, butterfly and medley; distance is free-form.",
            ),
            _p(
                "blue",
                "Split ve dönüş",
                "Splits and turns",
                "Ara dereceler, dönüş süresi, çıkış tepkisi ve kulaç frekansı ayrı kaydedilir.",
                "Splits, turn time, start reaction and stroke rate are recorded separately.",
            ),
            _p(
                "gold",
                "Kişisel rekorlar",
                "Personal bests",
                "Stil, mesafe ve kulvar tipi başına rekor otomatik güncellenir; kırılınca bildirim düşer.",
                "A best is kept per stroke, distance and course type; breaking one raises a notification.",
            ),
            _p(
                "rose",
                "Düşüş tespiti",
                "Decline detection",
                "Doğrusal eğim ile gerileyen sporcular listelenir — istatistik sonucudur, tahmin değildir.",
                "Linear slope lists athletes whose trend turned negative — a statistical result, not a forecast.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Yarışma Modülü",
        "shot": "competitions",
        "icon": "🏆",
        "title": {"tr": "Yarışmalar", "en": "Competitions"},
        "subtitle": {
            "tr": "Kulüp içi seçmeden uluslararası müsabakaya: seri, kulvar, derece ve madalya yönetimi.",
            "en": "From in-club trials to international meets: heats, lanes, results and medals.",
        },
        "points": [
            _p(
                "teal",
                "5 seviye",
                "5 levels",
                "Kulüp, yerel, bölgesel, ulusal ve uluslararası; seviye rekor karşılaştırmasında ayrı tutulur.",
                "Club, local, regional, national and international, kept separate in record comparisons.",
            ),
            _p(
                "blue",
                "Seri ve kulvar",
                "Heats and lanes",
                "Katılımcılar serilere ve kulvarlara atanır; kayıt derecesine göre sıralama önerilir.",
                "Entrants are assigned to heats and lanes, with seeding suggested from entry times.",
            ),
            _p(
                "gold",
                "Madalya tablosu",
                "Medal table",
                "Sıralama, madalya ve kulüp madalya tablosu sonuç girildiğinde otomatik hesaplanır.",
                "Rankings, medals and the club medal table are computed as results are entered.",
            ),
            _p(
                "purple",
                "Rekor güncelleme",
                "Record updates",
                "Kulüp rekorları ve kişisel rekorlar yarışma sonucundan otomatik güncellenir.",
                "Club and personal records update automatically from competition results.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "İstatistik Merkezi — 28 Analiz Fonksiyonu",
        "shot": "statistics",
        "icon": "📊",
        "title": {"tr": "İstatistik Merkezi", "en": "Statistics Centre"},
        "subtitle": {
            "tr": "Altı sekme: öğrenci, eğitmen, havuz, yoklama, KPI ve gelişmiş analiz — hepsi gerçek kayıtlar üzerinde.",
            "en": "Six tabs — student, instructor, pool, attendance, KPI and advanced — all on real records.",
        },
        "points": [
            _p(
                "teal",
                "Dönem seçici",
                "Period selector",
                "Bu ay, geçen ay, çeyrek ve serbest tarih aralığı; tüm sekmeler seçime uyar.",
                "This month, last month, quarter or a custom range; every tab follows the selection.",
            ),
            _p(
                "blue",
                "Dağılım grafikleri",
                "Distribution charts",
                "Yaş ve seviye dağılımı, doluluk ısı haritası ve kohort elde tutma grafikleri.",
                "Age and level distribution, occupancy heatmap and cohort retention charts.",
            ),
            _p(
                "gold",
                "Karşılaştırmalı değişim",
                "Period-on-period change",
                "Her gösterge önceki döneme göre yüzde değişimiyle birlikte sunulur.",
                "Every indicator is shown with its percentage change against the previous period.",
            ),
            _p(
                "rose",
                "Nedensellik uyarısı",
                "Causation caveat",
                'Korelasyon sonuçlarının yanında "ilişki nedensellik değildir" uyarısı kalıcı olarak gösterilir.',
                'Correlation results permanently carry a "relationship is not causation" caveat.',
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "16 Rapor Şablonu — PDF, Excel, CSV",
        "shot": "reports",
        "icon": "📄",
        "title": {"tr": "Raporlar", "en": "Reports"},
        "subtitle": {
            "tr": "Hazır şablon seç, tarih aralığı ve süzgeç uygula, önizle ve üç formattan birinde dışa aktar.",
            "en": "Pick a template, apply date range and filters, preview, then export in one of three formats.",
        },
        "points": [
            _p(
                "teal",
                "16 şablon",
                "16 templates",
                "Öğrenci, eğitmen, finans, havuz, performans ve yarışma raporları hazır gelir.",
                "Student, instructor, finance, pool, performance and competition reports ship built in.",
            ),
            _p(
                "blue",
                "Önizleme",
                "Preview",
                "Sütunlar, satırlar ve toplamlar dışa aktarmadan önce ekranda gösterilir.",
                "Columns, rows and totals are shown on screen before exporting.",
            ),
            _p(
                "gold",
                "Üç format",
                "Three formats",
                "PDF (Türkçe için gömülü font), Excel ve CSV (UTF-8 BOM ile, Excel'de doğru açılır).",
                "PDF (embedded font for Turkish), Excel and CSV (UTF-8 BOM so Excel opens it correctly).",
            ),
            _p(
                "purple",
                "Rapor oluşturucu",
                "Report builder",
                "Hazır şablon yetmezse sütun seçimi ve süzgeçlerle kendi raporunuzu tanımlarsınız.",
                "If a template is not enough, define your own with column selection and filters.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Yapay Zekâ — Sağlayıcı Sizin Seçiminiz",
        "shot": "ai_center",
        "icon": "🤖",
        "title": {"tr": "Yapay Zekâ Merkezi", "en": "AI Centre"},
        "subtitle": {
            "tr": "Sağlayıcı durumu, model listesi, bağlantı testi ve analiz — hepsi tek ekranda.",
            "en": "Provider status, model list, connection test and analysis — all on one screen.",
        },
        "points": [
            _p(
                "teal",
                "Sağlayıcı sağlığı",
                "Provider health",
                "Yerel ve bulut sağlayıcıların durumu, yanıt süresi ve model listesi canlı gösterilir.",
                "Local and cloud provider status, response time and model list are shown live.",
            ),
            _p(
                "blue",
                "Gerçek veri / AI yorumu",
                "Real data vs AI interpretation",
                "Yanıt dört başlıkta ayrışır: Gerçek Veri, Yapay Zekâ Yorumu, Olası Nedenler, Öneriler.",
                "The response separates into Real Data, AI Interpretation, Possible Causes and Recommendations.",
            ),
            _p(
                "purple",
                "HSP kararı görünür",
                "HSP decision is visible",
                "Her analizde politika kararı, kaç adın takma adlaştırıldığı ve makbuz numarası gösterilir.",
                "Every analysis shows the policy decision, how many names were pseudonymised and the receipt id.",
            ),
            _p(
                "rose",
                "Engellenirse veri yine gelir",
                "Blocked still returns data",
                "Politika engellerse yorum boş kalır, gerekçe gösterilir; hesaplanmış istatistikler yine döner.",
                "If policy blocks, the interpretation is empty with a reason — computed statistics still return.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Yapay Zekâ Geliştirici Konsolu",
        "shot": "ai_developer",
        "icon": "🛠",
        "title": {"tr": "AI Geliştirici Konsolu", "en": "AI Developer Console"},
        "subtitle": {
            "tr": "Yalnızca Sistem Yöneticisi erişir; varsayılan ayarlarda salt okunurdur.",
            "en": "System Administrator only, and read-only under default settings.",
        },
        "points": [
            _p(
                "teal",
                "Oku, ara, çözümle",
                "Read, search, analyse",
                "Bu üç işlem her zaman açıktır; proje dosyalarını okur ve yapı çözümlemesi üretir.",
                "These three are always available: read project files and produce structural analysis.",
            ),
            _p(
                "gold",
                "Fark önizlemesi",
                "Diff preview",
                "Hiçbir değişiklik onaysız uygulanmaz; önce satır satır fark gösterilir.",
                "No change is applied without approval — a line-by-line diff comes first.",
            ),
            _p(
                "green",
                "Otomatik kontrol noktası",
                "Automatic checkpoint",
                "Önemli değişiklikten önce sürüm kontrolünde kontrol noktası oluşturulur.",
                "A version-control checkpoint is created before any significant change.",
            ),
            _p(
                "rose",
                "İki ayrı kilit",
                "Two separate locks",
                "Yama uygulama ve kabuk komutu ayrı ayarlardır; ikisi de varsayılan olarak kapalıdır.",
                "Patch application and shell commands are separate settings, both disabled by default.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "CAIO — Gözlemleyen, Öneren, Karar Vermeyen Ajan",
        "shot": "caio",
        "icon": "🧑‍💼",
        "title": {"tr": "CAIO Ajanı", "en": "CAIO Agent"},
        "subtitle": {
            "tr": "Sistemi izler, iyileştirme önerir; hiçbir öneriyi kendi başına uygulamaz.",
            "en": "Observes the system and proposes improvements — and applies none on its own.",
        },
        "points": [
            _p(
                "blue",
                "Bulgu listesi",
                "Findings list",
                "Kullanım, hata ve performans verisinden çıkarılan somut bulgular önceliğiyle listelenir.",
                "Concrete findings from usage, error and performance data, listed with priority.",
            ),
            _p(
                "teal",
                "Sekiz adımlı döngü",
                "Eight-step loop",
                "Gözlemle, çözümle, öner, yama hazırla, test et, farkı göster, onay al, uygula.",
                "Observe, analyse, propose, draft patch, test, show diff, get approval, apply.",
            ),
            _p(
                "rose",
                "Onay atlanamaz",
                "Approval cannot be skipped",
                "Onay adımı yapılandırmayla kapatılamaz; ajan bir denetçidir, yönetici değil.",
                "The approval step cannot be configured away; the agent is a reviewer, not an administrator.",
            ),
            _p(
                "gold",
                "Yetkisiz alanlar",
                "Out of reach",
                "Veri silme, kullanıcı hesapları ve yedekler ajanın erişimine kapalıdır.",
                "Data deletion, user accounts and backups are outside the agent's reach.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "shot",
        "after": "Uygulama İçi Eğitim Merkezi",
        "shot": "help",
        "icon": "📚",
        "title": {"tr": "Kullanım Kılavuzu", "en": "User Guide"},
        "subtitle": {
            "tr": "28 konu programın içinde; ayrı bir PDF açmaya gerek yok, arama kutusuyla erişilir.",
            "en": "28 topics inside the program — no separate PDF to open, reachable through a search box.",
        },
        "points": [
            _p(
                "teal",
                "28 konu",
                "28 topics",
                "Öğrenci kaydından yedek geri yüklemeye kadar her modül adım adım anlatılır.",
                "Step-by-step coverage of every module, from enrolment to backup restore.",
            ),
            _p(
                "blue",
                "Bağlamsal yardım",
                "Contextual help",
                "Her ekranda o ekrana ait yardım; ilgili eğitime tek tıkla geçiş.",
                "Help specific to the current screen, with one-click access to the related tutorial.",
            ),
            _p(
                "gold",
                "12 etkileşimli eğitim",
                "12 interactive tutorials",
                "Ekranda yönlendirmeli alıştırmalar; ilerleme kaydedilir, yarıda bırakılabilir.",
                "Guided on-screen exercises with saved progress that can be paused and resumed.",
            ),
            _p(
                "purple",
                "Role göre içerik",
                "Role-aware content",
                "21 rolün her biri için ayrı izlek; muhasebeye havuz kimyasalı anlatılmaz.",
                "A dedicated track per role — accounting is not taught pool chemistry.",
            ),
        ],
    },
    # ------------------------------------------------------------------
    {
        "kind": "gallery",
        "after": "Günlük Kullanımı Hızlandıran Ayrıntılar",
        "icon": "🧭",
        "title": {"tr": "Günlük Kullanım Ekranları", "en": "Everyday Screens"},
        "subtitle": {
            "tr": "Eğitim merkezi, bildirimler ve ayarlar — programın her gün dokunulan yardımcı yüzeyleri.",
            "en": "Training centre, notifications and settings — the surfaces touched every day.",
        },
        "columns": 3,
        "items": [
            {"shot": "training", "title": {"tr": "Eğitim Merkezi", "en": "Training Centre"}},
            {"shot": "notifications", "title": {"tr": "Bildirimler", "en": "Notifications"}},
            {"shot": "settings", "title": {"tr": "Ayarlar", "en": "Settings"}},
        ],
    },
]
