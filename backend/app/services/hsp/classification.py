"""Veri sınıflandırma ve haklar etiketleri / Data classification and rights labels.

HSP'nin ilk sorusu "sistem bu insan hakkında ne öğreniyor?" (KNOW) olduğu için,
her alanın iki bağımsız ekseni vardır:

    Gizlilik sınıfı   : PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED
    Kişisel veri türü : NON_PERSONAL / PERSONAL / SENSITIVE / UNKNOWN

Bu iki eksen bilinçli olarak ayrıdır. Bir alan kişisel olmayabilir ama yine de
gizli olabilir (ör. ciro), ya da kişisel olup kurum içinde serbestçe
dolaşabilir (ör. eğitmen adı). Tek bir "hassaslık" skoruna indirgemek §14'teki
"temel hak etkisini yalnızca sayıya indirgeme" ilkesine aykırı olurdu.

`UNKNOWN` asla otomatik olarak `NON_PERSONAL` sayılmaz (§3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Classification(StrEnum):
    """Gizlilik sınıfı — yükselen sırada."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class PersonalDataKind(StrEnum):
    """Kişisel veri niteliği. KVKK m.6 / GDPR Art.9 özel nitelik ayrımı korunur."""

    NON_PERSONAL = "non_personal"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    UNKNOWN = "unknown"


# Gizlilik sınıflarının karşılaştırılabilmesi için sıra değeri
_ORDER: dict[Classification, int] = {
    Classification.PUBLIC: 0,
    Classification.INTERNAL: 1,
    Classification.CONFIDENTIAL: 2,
    Classification.RESTRICTED: 3,
}


def at_least(value: Classification, floor: Classification) -> bool:
    """`value` en az `floor` kadar kısıtlı mı?"""
    return _ORDER[value] >= _ORDER[floor]


def strictest(*values: Classification) -> Classification:
    """Verilen sınıfların en kısıtlı olanı. Boşsa RESTRICTED (fail-safe)."""
    if not values:
        return Classification.RESTRICTED
    return max(values, key=lambda item: _ORDER[item])


class Handling(StrEnum):
    """Bir alanın AI'ya gönderilirken nasıl işleneceği."""

    PASS = "pass"  # olduğu gibi gönderilebilir
    PSEUDONYMIZE = "pseudonymize"  # kararlı takma ad ile değiştirilir
    REDACT = "redact"  # tamamen çıkarılır
    NEVER = "never"  # bu alan hiçbir sağlayıcıya gönderilmez


@dataclass(frozen=True)
class FieldLabel:
    """Tek bir veri alanının HSP etiketi."""

    path: str  # "student.full_name"
    classification: Classification
    kind: PersonalDataKind
    handling: Handling
    subject: str  # veri sahibi kategorisi: student / guardian / instructor / staff
    purpose_tr: str
    purpose_en: str
    # Bu alan çocuğa ait olabilir mi? KVKK ve GDPR Art.8 için ayrı bayrak.
    may_concern_child: bool = False
    categories: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_personal(self) -> bool:
        return self.kind in (PersonalDataKind.PERSONAL, PersonalDataKind.SENSITIVE)


def _label(
    path: str,
    classification: Classification,
    kind: PersonalDataKind,
    handling: Handling,
    subject: str,
    purpose_tr: str,
    purpose_en: str,
    *,
    child: bool = False,
    categories: tuple[str, ...] = (),
) -> FieldLabel:
    return FieldLabel(
        path=path,
        classification=classification,
        kind=kind,
        handling=handling,
        subject=subject,
        purpose_tr=purpose_tr,
        purpose_en=purpose_en,
        may_concern_child=child,
        categories=categories,
    )


# ---------------------------------------------------------------------------
# Yüzme okulu alan kayıt defteri
# ---------------------------------------------------------------------------
# Not: Bu kayıt defteri gerçek SQLAlchemy modellerindeki alan adlarına karşılık
# gelir. Yeni alan eklendiğinde buraya da eklenmelidir; `test_hsp_coverage`
# testi modeldeki kişisel veri adaylarının burada tanımlı olmasını zorunlu kılar.

_FIELDS: tuple[FieldLabel, ...] = (
    # --- Öğrenci: çoğunlukla çocuk ---
    _label(
        "student.full_name",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PSEUDONYMIZE,
        "student",
        "Kayıt ve ders yönetimi",
        "Enrolment and lesson management",
        child=True,
        categories=("identity",),
    ),
    _label(
        "student.first_name",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PSEUDONYMIZE,
        "student",
        "Kayıt ve ders yönetimi",
        "Enrolment and lesson management",
        child=True,
        categories=("identity",),
    ),
    _label(
        "student.last_name",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PSEUDONYMIZE,
        "student",
        "Kayıt ve ders yönetimi",
        "Enrolment and lesson management",
        child=True,
        categories=("identity",),
    ),
    _label(
        "student.birth_date",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "student",
        "Yaş grubu ve ders türü eşleştirme",
        "Age band and lesson type matching",
        child=True,
        categories=("identity",),
    ),
    _label(
        "student.email",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "student",
        "İletişim",
        "Contact",
        child=True,
        categories=("contact",),
    ),
    _label(
        "student.phone",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "student",
        "İletişim",
        "Contact",
        child=True,
        categories=("contact",),
    ),
    _label(
        "student.address",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "student",
        "İletişim",
        "Contact",
        child=True,
        categories=("contact", "location"),
    ),
    _label(
        "student.national_id",
        Classification.RESTRICTED,
        PersonalDataKind.PERSONAL,
        Handling.NEVER,
        "student",
        "Yasal kayıt",
        "Statutory record",
        child=True,
        categories=("identity",),
    ),
    # Sağlık verisi: KVKK m.6 özel nitelikli. Hiçbir AI sağlayıcısına gitmez.
    _label(
        "student.health_notes",
        Classification.RESTRICTED,
        PersonalDataKind.SENSITIVE,
        Handling.NEVER,
        "student",
        "Havuz güvenliği",
        "Poolside safety",
        child=True,
        categories=("health",),
    ),
    _label(
        "student.special_needs",
        Classification.RESTRICTED,
        PersonalDataKind.SENSITIVE,
        Handling.NEVER,
        "student",
        "Havuz güvenliği ve uyarlanmış eğitim",
        "Poolside safety and adapted teaching",
        child=True,
        categories=("health",),
    ),
    _label(
        "student.emergency_contact",
        Classification.RESTRICTED,
        PersonalDataKind.PERSONAL,
        Handling.NEVER,
        "student",
        "Acil durum",
        "Emergency response",
        child=True,
        categories=("contact",),
    ),
    _label(
        "student.notes",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "student",
        "Eğitim takibi",
        "Training follow-up",
        child=True,
        categories=("behaviour",),
    ),
    _label(
        "student.goals",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Eğitim hedefi",
        "Training goal",
        child=True,
        categories=("behaviour",),
    ),
    _label(
        "student.swim_level",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Seviye eşleştirme",
        "Level matching",
        child=True,
    ),
    # --- Veli ---
    _label(
        "guardian.full_name",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PSEUDONYMIZE,
        "guardian",
        "Veli iletişimi",
        "Guardian contact",
        categories=("identity",),
    ),
    _label(
        "guardian.email",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "guardian",
        "İletişim",
        "Contact",
        categories=("contact",),
    ),
    _label(
        "guardian.phone",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "guardian",
        "İletişim",
        "Contact",
        categories=("contact",),
    ),
    _label(
        "guardian.national_id",
        Classification.RESTRICTED,
        PersonalDataKind.PERSONAL,
        Handling.NEVER,
        "guardian",
        "Yasal kayıt",
        "Statutory record",
        categories=("identity",),
    ),
    # --- Eğitmen / personel ---
    _label(
        "instructor.full_name",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PSEUDONYMIZE,
        "instructor",
        "Ders planlama",
        "Lesson scheduling",
        categories=("identity",),
    ),
    _label(
        "instructor.email",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "instructor",
        "İletişim",
        "Contact",
        categories=("contact",),
    ),
    _label(
        "instructor.phone",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "instructor",
        "İletişim",
        "Contact",
        categories=("contact",),
    ),
    _label(
        "instructor.salary",
        Classification.RESTRICTED,
        PersonalDataKind.PERSONAL,
        Handling.NEVER,
        "instructor",
        "Bordro",
        "Payroll",
        categories=("financial",),
    ),
    _label(
        "instructor.certifications",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "instructor",
        "Yetkinlik doğrulama",
        "Competency verification",
    ),
    _label(
        "user.email",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.REDACT,
        "staff",
        "Kimlik doğrulama",
        "Authentication",
        categories=("contact", "authentication"),
    ),
    _label(
        "user.hashed_password",
        Classification.RESTRICTED,
        PersonalDataKind.PERSONAL,
        Handling.NEVER,
        "staff",
        "Kimlik doğrulama",
        "Authentication",
        categories=("authentication",),
    ),
    # --- Finans: kişiye bağlandığında kişisel veri olur ---
    _label(
        "invoice.amount",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Tahsilat takibi",
        "Collection tracking",
        child=True,
        categories=("financial",),
    ),
    _label(
        "invoice.balance",
        Classification.CONFIDENTIAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Tahsilat takibi",
        "Collection tracking",
        child=True,
        categories=("financial",),
    ),
    # --- Performans ---
    _label(
        "performance.time_seconds",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Gelişim ölçümü",
        "Progress measurement",
        child=True,
    ),
    _label(
        "attendance.status",
        Classification.INTERNAL,
        PersonalDataKind.PERSONAL,
        Handling.PASS,
        "student",
        "Devam takibi",
        "Attendance tracking",
        child=True,
    ),
    # --- Kişisel olmayan ---
    _label(
        "pool.name",
        Classification.PUBLIC,
        PersonalDataKind.NON_PERSONAL,
        Handling.PASS,
        "none",
        "Tesis bilgisi",
        "Facility information",
    ),
    _label(
        "lesson.start_time",
        Classification.INTERNAL,
        PersonalDataKind.NON_PERSONAL,
        Handling.PASS,
        "none",
        "Planlama",
        "Scheduling",
    ),
)

FIELD_REGISTRY: dict[str, FieldLabel] = {item.path: item for item in _FIELDS}

# Alan adından (model öneki olmadan) etiketi bulmak için ters dizin.
# Aynı alan adı birden çok varlıkta geçebileceğinden en kısıtlı olan seçilir —
# belirsizlikte güvenli tarafta kalınır.
_BY_NAME: dict[str, FieldLabel] = {}
for _item in _FIELDS:
    _name = _item.path.split(".", 1)[1]
    _current = _BY_NAME.get(_name)
    if _current is None or at_least(_item.classification, _current.classification):
        _BY_NAME[_name] = _item


UNKNOWN_LABEL = FieldLabel(
    path="<unknown>",
    classification=Classification.RESTRICTED,
    kind=PersonalDataKind.UNKNOWN,
    handling=Handling.REDACT,
    subject="unknown",
    purpose_tr="Bilinmiyor — insan incelemesi gerekir",
    purpose_en="Unknown — human review required",
)


def label_for(path: str) -> FieldLabel:
    """Tam yol ile etiket getirir.

    Kayıtlı değilse `UNKNOWN_LABEL` döner: bilinmeyen alan serbest değil,
    kısıtlı sayılır (§3 — `UNKNOWN` otomatik `ALLOW` değildir).
    """
    found = FIELD_REGISTRY.get(path)
    if found is not None:
        return found
    if "." in path:
        by_name = _BY_NAME.get(path.split(".", 1)[1])
        if by_name is not None:
            return by_name
    return _BY_NAME.get(path, UNKNOWN_LABEL)


def classify_payload(
    paths: list[str],
) -> tuple[Classification, PersonalDataKind, list[FieldLabel]]:
    """Bir yük içindeki alanların birleşik sınıfını hesaplar.

    Birleşim daima en kısıtlı alana göre belirlenir: tek bir sağlık notu,
    bütün yükü `RESTRICTED` + `SENSITIVE` yapar.
    """
    labels = [label_for(path) for path in paths]
    if not labels:
        return Classification.PUBLIC, PersonalDataKind.NON_PERSONAL, []

    classification = strictest(*(item.classification for item in labels))
    kinds = {item.kind for item in labels}
    if PersonalDataKind.SENSITIVE in kinds:
        kind = PersonalDataKind.SENSITIVE
    elif PersonalDataKind.UNKNOWN in kinds:
        kind = PersonalDataKind.UNKNOWN
    elif PersonalDataKind.PERSONAL in kinds:
        kind = PersonalDataKind.PERSONAL
    else:
        kind = PersonalDataKind.NON_PERSONAL
    return classification, kind, labels


def involves_child(labels: list[FieldLabel]) -> bool:
    return any(item.may_concern_child and item.is_personal for item in labels)
