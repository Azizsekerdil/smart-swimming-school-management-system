"""Backend mesaj yerelleştirmesi / Backend message localization.

API hata ve bilgi mesajları anahtar (key) ile döndürülür; hem TR hem EN metni
sözlükte tutulur. İstemci `Accept-Language` başlığı veya `?lang=` parametresi ile
dil seçer.
"""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = ("tr", "en")
DEFAULT_LANGUAGE = "tr"

MESSAGES: dict[str, dict[str, str]] = {
    # --- Kimlik doğrulama ---
    "auth.invalid_credentials": {
        "tr": "E-posta veya parola hatalı.",
        "en": "Invalid email or password.",
    },
    "auth.inactive_user": {
        "tr": "Bu hesap devre dışı bırakılmış.",
        "en": "This account is disabled.",
    },
    "auth.not_authenticated": {
        "tr": "Bu işlem için giriş yapmanız gerekiyor.",
        "en": "Authentication required.",
    },
    "auth.invalid_token": {
        "tr": "Oturum bilgisi geçersiz veya süresi dolmuş.",
        "en": "Session is invalid or expired.",
    },
    "auth.forbidden": {
        "tr": "Bu işlem için yetkiniz bulunmuyor.",
        "en": "You do not have permission for this action.",
    },
    "auth.password_weak": {
        "tr": "Parola politikası karşılanmıyor: en az 8 karakter, harf ve rakam içermeli.",
        "en": "Password policy not met: at least 8 characters with letters and digits.",
    },
    "auth.current_password_wrong": {
        "tr": "Mevcut parola hatalı.",
        "en": "Current password is incorrect.",
    },
    "auth.password_change_required": {
        "tr": (
            "İlk kurulum parolası değiştirilmeden bu bölüme erişilemez. "
            "Lütfen önce parolanızı değiştirin."
        ),
        "en": (
            "This area is unavailable until the initial setup password is "
            "changed. Please change your password first."
        ),
    },
    "auth.bootstrap_local_only": {
        "tr": (
            "Kurulum parolası yalnızca sunucunun çalıştığı cihazdan "
            "kullanılabilir. Ağ üzerinden kurulum girişi kapalıdır."
        ),
        "en": (
            "The setup password can only be used from the device running the "
            "server. Remote setup login is disabled."
        ),
    },
    "auth.rate_limited": {
        "tr": "Çok fazla deneme yapıldı. Lütfen bir dakika sonra tekrar deneyin.",
        "en": "Too many attempts. Please try again in a minute.",
    },
    # --- Genel CRUD ---
    "common.not_found": {"tr": "Kayıt bulunamadı.", "en": "Record not found."},
    "common.already_exists": {
        "tr": "Bu kayıt zaten mevcut.",
        "en": "This record already exists.",
    },
    "common.created": {"tr": "Kayıt oluşturuldu.", "en": "Record created."},
    "common.updated": {"tr": "Kayıt güncellendi.", "en": "Record updated."},
    "common.deleted": {"tr": "Kayıt silindi.", "en": "Record deleted."},
    "common.validation_error": {
        "tr": "Girilen veriler geçersiz.",
        "en": "Submitted data is invalid.",
    },
    "common.internal_error": {
        "tr": "Beklenmeyen bir hata oluştu. Sistem yöneticinize başvurun.",
        "en": "An unexpected error occurred. Please contact your administrator.",
    },
    "common.in_use": {
        "tr": "Bu kayıt başka kayıtlar tarafından kullanıldığı için silinemez.",
        "en": "This record is referenced by other records and cannot be deleted.",
    },
    # --- Öğrenci ---
    "student.not_found": {"tr": "Öğrenci bulunamadı.", "en": "Student not found."},
    "student.number_exists": {
        "tr": "Bu öğrenci numarası zaten kullanılıyor.",
        "en": "This student number is already in use.",
    },
    # --- Eğitmen ---
    "instructor.not_found": {
        "tr": "Eğitmen bulunamadı.",
        "en": "Instructor not found.",
    },
    "instructor.unavailable": {
        "tr": "Eğitmen seçilen saatte müsait değil.",
        "en": "Instructor is not available at the selected time.",
    },
    # --- Havuz / kulvar ---
    "pool.not_found": {"tr": "Havuz bulunamadı.", "en": "Pool not found."},
    "lane.not_found": {"tr": "Kulvar bulunamadı.", "en": "Lane not found."},
    "pool.under_maintenance": {
        "tr": "Havuz seçilen tarihte bakımda.",
        "en": "The pool is under maintenance on the selected date.",
    },
    "pool.outside_hours": {
        "tr": "Seçilen saat havuzun çalışma saatleri dışında.",
        "en": "The selected time is outside the pool's operating hours.",
    },
    # --- Ders / çakışma ---
    "lesson.not_found": {"tr": "Ders bulunamadı.", "en": "Lesson not found."},
    "lesson.conflict_instructor": {
        "tr": "Çakışma: Eğitmen bu saatte başka bir derste görevli.",
        "en": "Conflict: The instructor is already assigned to another lesson at this time.",
    },
    "lesson.conflict_lane": {
        "tr": "Çakışma: Kulvar bu saatte başka bir ders tarafından kullanılıyor.",
        "en": "Conflict: The lane is already occupied by another lesson at this time.",
    },
    "lesson.conflict_student": {
        "tr": "Çakışma: Öğrenci bu saatte başka bir derse kayıtlı.",
        "en": "Conflict: The student is already enrolled in another lesson at this time.",
    },
    "lesson.capacity_full": {
        "tr": "Ders kontenjanı dolu.",
        "en": "The lesson is at full capacity.",
    },
    "lesson.already_enrolled": {
        "tr": "Öğrenci bu derse zaten kayıtlı.",
        "en": "The student is already enrolled in this lesson.",
    },
    "lesson.invalid_time_range": {
        "tr": "Bitiş saati başlangıç saatinden sonra olmalıdır.",
        "en": "End time must be after start time.",
    },
    # --- Üyelik ---
    "membership.not_found": {"tr": "Üyelik bulunamadı.", "en": "Membership not found."},
    "membership.expired": {
        "tr": "Üyelik süresi dolmuş.",
        "en": "The membership has expired.",
    },
    "membership.no_credits": {
        "tr": "Pakette kalan ders hakkı bulunmuyor.",
        "en": "No remaining lesson credits in the package.",
    },
    "membership.frozen": {
        "tr": "Üyelik dondurulmuş durumda.",
        "en": "The membership is frozen.",
    },
    # --- Finans ---
    "payment.not_found": {
        "tr": "Ödeme kaydı bulunamadı.",
        "en": "Payment record not found.",
    },
    "payment.amount_invalid": {
        "tr": "Ödeme tutarı sıfırdan büyük olmalıdır.",
        "en": "Payment amount must be greater than zero.",
    },
    "payment.exceeds_balance": {
        "tr": "Ödeme tutarı kalan borcu aşıyor.",
        "en": "Payment amount exceeds the outstanding balance.",
    },
    # --- Yoklama ---
    "attendance.already_recorded": {
        "tr": "Bu öğrenci için yoklama zaten alınmış.",
        "en": "Attendance has already been recorded for this student.",
    },
    # --- AI ---
    "ai.provider_unavailable": {
        "tr": "Yapay zekâ sağlayıcısına ulaşılamıyor. Yüzme okulu sistemi normal çalışmaya devam ediyor.",
        "en": "The AI provider is unreachable. The swimming school system continues to operate normally.",
    },
    "ai.all_providers_failed": {
        "tr": "Yapılandırılmış tüm yapay zekâ sağlayıcıları başarısız oldu.",
        "en": "All configured AI providers failed.",
    },
    "ai.disabled": {
        "tr": "Yapay zekâ özelliği kapalı.",
        "en": "The AI feature is disabled.",
    },
    "ai.timeout": {
        "tr": "Yapay zekâ yanıtı zaman aşımına uğradı.",
        "en": "The AI response timed out.",
    },
    "ai.developer_disabled": {
        "tr": "AI Developer Console kapalı. Ayarlardan etkinleştirebilirsiniz.",
        "en": "AI Developer Console is disabled. Enable it in Settings.",
    },
    "ai.apply_not_allowed": {
        "tr": "Yama uygulama izni kapalı. Ayarlar > Geliştirici bölümünden açabilirsiniz.",
        "en": "Patch apply permission is disabled. Enable it under Settings > Developer.",
    },
    "ai.path_outside_project": {
        "tr": "Güvenlik: Proje dizini dışındaki dosyalara erişilemez.",
        "en": "Security: Files outside the project directory cannot be accessed.",
    },
    "ai.command_blocked": {
        "tr": "Güvenlik politikası bu komutu engelledi.",
        "en": "The security policy blocked this command.",
    },
    # --- Yedekleme ---
    "backup.not_found": {"tr": "Yedek bulunamadı.", "en": "Backup not found."},
    "backup.created": {
        "tr": "Yedek başarıyla oluşturuldu.",
        "en": "Backup created successfully.",
    },
    "backup.integrity_failed": {
        "tr": "Yedek bütünlük doğrulaması başarısız. Geri yükleme iptal edildi.",
        "en": "Backup integrity verification failed. Restore aborted.",
    },
    "backup.restored": {
        "tr": "Geri yükleme tamamlandı. Değişikliklerin etkin olması için uygulamayı yeniden başlatın.",
        "en": "Restore completed. Restart the application for changes to take effect.",
    },
    "backup.protected": {
        "tr": "Korunan yedekler silinemez.",
        "en": "Protected backups cannot be deleted.",
    },
    # --- Raporlama ---
    "report.no_data": {
        "tr": "Seçilen kriterlere uygun veri bulunamadı.",
        "en": "No data found for the selected criteria.",
    },
    "report.unsupported_format": {
        "tr": "Desteklenmeyen dışa aktarma biçimi.",
        "en": "Unsupported export format.",
    },
}


def normalize_language(lang: str | None) -> str:
    """Accept-Language başlığını desteklenen bir dile indirger."""
    if not lang:
        return DEFAULT_LANGUAGE
    primary = lang.split(",")[0].split("-")[0].strip().lower()
    return primary if primary in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Anahtarı verilen dile çevirir. Bilinmeyen anahtar için anahtarı döndürür."""
    lang = normalize_language(lang)
    entry = MESSAGES.get(key)
    if not entry:
        return key
    text = entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def all_message_keys() -> list[str]:
    return sorted(MESSAGES.keys())


def missing_translations() -> dict[str, list[str]]:
    """Eksik çeviri anahtarlarını raporlar (CI doğrulaması için)."""
    missing: dict[str, list[str]] = {lang: [] for lang in SUPPORTED_LANGUAGES}
    for key, entry in MESSAGES.items():
        for lang in SUPPORTED_LANGUAGES:
            if not entry.get(lang):
                missing[lang].append(key)
    return missing
