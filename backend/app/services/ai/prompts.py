"""Prompt kütüphanesi ve sistem istemleri / Prompt library and system prompts."""

from __future__ import annotations

from app.schemas.ai import PromptTemplate

# ---------------------------------------------------------------------------
# Sistem istemleri
# ---------------------------------------------------------------------------
SYSTEM_ANALYST_TR = """Sen bir yüzme okulu yönetim sisteminin analiz asistanısın.

KURALLAR:
1. Sana verilen HESAPLANMIŞ İSTATİSTİKLER gerçek verilerdir. Sayıları asla değiştirme veya uydurma.
2. Veride olmayan bir bilgiyi varmış gibi sunma. Emin değilsen "veri yetersiz" de.
3. Korelasyonu nedensellik olarak sunma.
4. Bireysel çalışanlar hakkında kesin performans yargısı verme; karar desteği sun.
5. Sağlık verisi hakkında tıbbi tanı veya tedavi önerisi verme.
6. Yanıtın kısa, somut ve uygulanabilir olsun.

YANIT BİÇİMİ (tam olarak bu başlıkları kullan):
## Yorum
(2-4 cümle: verinin ne anlattığı)

## Olası Nedenler
- (madde)
- (madde)

## Öneriler
- (uygulanabilir, somut adım)
- (uygulanabilir, somut adım)
"""

SYSTEM_ANALYST_EN = """You are the analysis assistant of a swimming school management system.

RULES:
1. The COMPUTED STATISTICS given to you are real data. Never alter or invent numbers.
2. Do not present information that is not in the data. If unsure, say "insufficient data".
3. Do not present correlation as causation.
4. Do not pass definitive judgement on individual staff performance; provide decision support.
5. Do not give medical diagnosis or treatment advice regarding health data.
6. Keep answers short, concrete and actionable.

RESPONSE FORMAT (use exactly these headings):
## Interpretation
(2-4 sentences: what the data says)

## Possible Causes
- (bullet)

## Recommendations
- (concrete, actionable step)
"""

SYSTEM_COACH_TR = """Sen deneyimli bir yüzme antrenörü asistanısın.

KURALLAR:
1. Sana verilen performans verileri gerçektir; dereceleri değiştirme.
2. Antrenman önerilerin sporcunun yaşına, seviyesine ve mevcut verisine uygun olsun.
3. Aşırı yüklenme (overtraining) riskine dikkat et; haftalık hacmi kademeli artır.
4. Sağlık sorunu şüphesinde sporcuyu sağlık personeline yönlendirmeyi öner.
5. Önerin bir eğitmen tarafından ONAYLANMADAN uygulanmaz; bunu unutma.

YANIT BİÇİMİ:
## Değerlendirme
## Odak Alanları
## Haftalık Plan
(Hafta 1..N: gün, set, mesafe, yoğunluk)
## Ölçüm Noktaları
"""

SYSTEM_COACH_EN = """You are an experienced swimming coach assistant.

RULES:
1. The performance data given to you is real; do not alter times.
2. Training suggestions must suit the athlete's age, level and current data.
3. Watch for overtraining risk; increase weekly volume gradually.
4. If a health issue is suspected, recommend referring the athlete to medical staff.
5. Your suggestion is not applied until APPROVED by an instructor; keep this in mind.

RESPONSE FORMAT:
## Assessment
## Focus Areas
## Weekly Plan
## Measurement Points
"""

SYSTEM_DEVELOPER = """Sen bir Python/FastAPI + React/TypeScript projesinde çalışan kıdemli
bir yazılım geliştirici asistanısın.

PROJE: Akıllı Yüzme Okulu Yönetim Sistemi
- Backend: FastAPI, SQLAlchemy 2.0, Pydantic v2, SQLite/Alembic
- Frontend: React 18, TypeScript, Vite, TanStack Query, Tailwind

KURALLAR:
1. Yalnızca sana gösterilen dosya içeriklerine dayanarak çalış; var olmayan dosya uydurma.
2. Değişiklikleri MİNİMAL tut; ilgisiz kodu yeniden düzenleme.
3. Mevcut kod stiline uy (Türkçe yorumlar, tip ipuçları, mevcut yardımcı fonksiyonlar).
4. Güvenlik: sır yazma, SQL enjeksiyonuna açık kod üretme, RBAC kontrolünü atlama.
5. Yanıtını İSTENEN JSON ŞEMASINDA döndür; şema dışına çıkma.
"""

SYSTEM_CAIO = """Sen bu yazılımın CAIO (Chief AI Officer) ajanısın.

GÖREVİN: Uygulamanın sağlığını, teknik borcunu, güvenliğini ve kullanım verimliliğini
gözlemleyip iyileştirme ÖNERMEK.

KURALLAR:
1. Sana verilen ölçümler gerçektir; uydurma sayı ekleme.
2. Öneriler somut, önceliklendirilmiş ve uygulanabilir olsun.
3. Üretim koduna doğrudan değişiklik YAPAMAZSIN; yalnızca öneri üretirsin.
4. Her öneri için: neden önemli, tahmini etki, tahmini efor belirt.
"""


def analyst_system_prompt(lang: str) -> str:
    return SYSTEM_ANALYST_TR if lang == "tr" else SYSTEM_ANALYST_EN


def coach_system_prompt(lang: str) -> str:
    return SYSTEM_COACH_TR if lang == "tr" else SYSTEM_COACH_EN


# ---------------------------------------------------------------------------
# Hazır prompt kütüphanesi
# ---------------------------------------------------------------------------
PROMPT_LIBRARY: list[PromptTemplate] = [
    PromptTemplate(
        id="student_performance",
        category="performance",
        title_tr="Öğrenci performansını analiz et",
        title_en="Analyse student performance",
        prompt_tr="{student} adlı öğrencinin son 3 aylık performansını analiz et.",
        prompt_en="Analyse the last 3 months of performance for {student}.",
        description_tr="Seçilen sporcunun tüm etkinliklerdeki gelişimini yorumlar.",
        description_en="Interprets the athlete's progress across all events.",
        requires_context=["student_id"],
        icon="activity",
    ),
    PromptTemplate(
        id="declining_students",
        category="performance",
        title_tr="Performansı düşen öğrencileri bul",
        title_en="Find students with declining performance",
        prompt_tr="Performansı düşen öğrencileri bul ve olası nedenleri değerlendir.",
        prompt_en="Find students whose performance is declining and assess possible causes.",
        icon="trending-down",
    ),
    PromptTemplate(
        id="training_suggestion",
        category="performance",
        title_tr="4 haftalık antrenman önerisi oluştur",
        title_en="Create a 4-week training plan",
        prompt_tr="{student} için gelecek 4 haftalık antrenman önerisi oluştur.",
        prompt_en="Create a 4-week training suggestion for {student}.",
        requires_context=["student_id"],
        icon="calendar-check",
    ),
    PromptTemplate(
        id="weakest_stroke",
        category="performance",
        title_tr="En zayıf yüzme stilini belirle",
        title_en="Identify the weakest stroke",
        prompt_tr="Bu sporcunun en zayıf yüzme stilini belirle ve gelişim önerisi ver.",
        prompt_en="Identify this athlete's weakest stroke and suggest improvements.",
        requires_context=["student_id"],
        icon="waves",
    ),
    PromptTemplate(
        id="top_improvers",
        category="performance",
        title_tr="Son 10 antrenmanda en çok gelişenler",
        title_en="Top improvers in the last 10 sessions",
        prompt_tr="Son dönemde en fazla gelişen yüzücüleri getir ve ortak özelliklerini yorumla.",
        prompt_en="List the most improved swimmers recently and interpret their common traits.",
        icon="trending-up",
    ),
    PromptTemplate(
        id="competition_readiness",
        category="performance",
        title_tr="Yarışma öncesi hazır sporcular",
        title_en="Athletes ready for competition",
        prompt_tr="Yarışma öncesi hangi sporcular daha hazır görünüyor? Gerekçeleriyle açıkla.",
        prompt_en="Which athletes appear more prepared for the competition? Explain with reasons.",
        icon="trophy",
    ),
    PromptTemplate(
        id="schedule_optimization",
        category="operations",
        title_tr="Ders programını optimize et",
        title_en="Optimise the lesson schedule",
        prompt_tr="Mevcut ders programını incele ve doluluk açısından iyileştirme öner.",
        prompt_en="Review the current lesson schedule and suggest occupancy improvements.",
        icon="calendar",
    ),
    PromptTemplate(
        id="free_lanes",
        category="operations",
        title_tr="Boş kulvarları bul",
        title_en="Find free lanes",
        prompt_tr="Bu hafta hangi saatlerde kulvarlar boş kalıyor? Değerlendirme öner.",
        prompt_en="Which hours have free lanes this week? Suggest how to use them.",
        icon="grid",
    ),
    PromptTemplate(
        id="instructor_balance",
        category="operations",
        title_tr="Antrenör yükünü dengele",
        title_en="Balance instructor workload",
        prompt_tr="Eğitmen ders yüklerini incele ve dengeleme önerisi getir.",
        prompt_en="Review instructor workloads and suggest rebalancing.",
        icon="users",
    ),
    PromptTemplate(
        id="payment_risk",
        category="finance",
        title_tr="Ödeme riski taşıyan üyelikleri göster",
        title_en="Show memberships with payment risk",
        prompt_tr="Ödeme riski taşıyan üyelikleri belirle ve tahsilat stratejisi öner.",
        prompt_en="Identify memberships with payment risk and suggest a collection strategy.",
        icon="alert-circle",
    ),
    PromptTemplate(
        id="retention_analysis",
        category="management",
        title_tr="Öğrenci kaybı neden arttı?",
        title_en="Why did student churn increase?",
        prompt_tr="Son üç ayda öğrenci kaybımız neden arttı? Verilere dayanarak açıkla.",
        prompt_en="Why did our student churn increase in the last three months? Explain from data.",
        icon="user-minus",
    ),
    PromptTemplate(
        id="weekly_report",
        category="management",
        title_tr="Bu haftanın performans raporunu oluştur",
        title_en="Generate this week's performance report",
        prompt_tr="Bu haftanın operasyon ve performans özetini yönetim için yaz.",
        prompt_en="Write this week's operations and performance summary for management.",
        icon="file-text",
    ),
    PromptTemplate(
        id="attendance_analysis",
        category="operations",
        title_tr="Devam oranlarını analiz et",
        title_en="Analyse attendance rates",
        prompt_tr="Devam oranlarını analiz et ve devamsızlığı azaltmak için öneri ver.",
        prompt_en="Analyse attendance rates and suggest ways to reduce absence.",
        icon="check-square",
    ),
    # --- Geliştirici promptları ---
    PromptTemplate(
        id="dev_analyze_errors",
        category="developer",
        title_tr="Kod hatalarını analiz et",
        title_en="Analyse code errors",
        prompt_tr="Bugünkü uygulama hatalarını incele ve çözüm öner.",
        prompt_en="Review today's application errors and propose fixes.",
        icon="bug",
    ),
    PromptTemplate(
        id="dev_write_test",
        category="developer",
        title_tr="Test yaz",
        title_en="Write tests",
        prompt_tr="{module} modülü için eksik testleri yaz.",
        prompt_en="Write the missing tests for the {module} module.",
        icon="check-circle",
    ),
    PromptTemplate(
        id="dev_refactor",
        category="developer",
        title_tr="Bu modülü refactor et",
        title_en="Refactor this module",
        prompt_tr="{module} modülünü okunabilirlik ve bakım kolaylığı için yeniden düzenle.",
        prompt_en="Refactor the {module} module for readability and maintainability.",
        icon="code",
    ),
    PromptTemplate(
        id="dev_optimize_db",
        category="developer",
        title_tr="Database sorgularını optimize et",
        title_en="Optimise database queries",
        prompt_tr="Yavaş veritabanı sorgularını tespit et ve indeks/sorgu iyileştirmesi öner.",
        prompt_en="Identify slow database queries and suggest index/query improvements.",
        icon="database",
    ),
    PromptTemplate(
        id="dev_add_export",
        category="developer",
        title_tr="Ekrana Excel export ekle",
        title_en="Add Excel export to a screen",
        prompt_tr="Öğrenci ekranına Excel export özelliği ekle.",
        prompt_en="Add an Excel export feature to the students screen.",
        icon="download",
    ),
]

PROMPT_INDEX = {p.id: p for p in PROMPT_LIBRARY}


def get_prompts(category: str | None = None) -> list[PromptTemplate]:
    if category:
        return [p for p in PROMPT_LIBRARY if p.category == category]
    return PROMPT_LIBRARY
