/** Program içi kullanım kılavuzu / In-app user guide. */
import { BookOpen, ChevronRight, GraduationCap, Search, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { Card, EmptyState, PageHeader } from '@/components/ui'

interface HelpSection {
  id: string
  title_tr: string
  title_en: string
  body_tr: string[]
  body_en: string[]
  steps_tr: string[]
  steps_en: string[]
  route: string
}

// ---------------------------------------------------------------------------
// Kılavuz içeriği: sistemin gerçek davranışını anlatır
// ---------------------------------------------------------------------------
const SECTIONS: HelpSection[] = [
  {
    id: 'intro',
    title_tr: 'Programa Giriş',
    title_en: 'Getting Started',
    body_tr: [
      'Akıllı Yüzme Okulu Yönetim Sistemi; öğrenci, ders, havuz, üyelik, tahsilat, performans ve yarışma verilerini tek bir veritabanında toplar. Giriş yaptığınızda hesabınıza tanımlı rollere göre sol menüdeki modüller açılır; yetkiniz olmayan ekranlar menüde hiç görünmez.',
      'Üst çubuktaki arama kutusu öğrenci, veli, eğitmen ve ders kayıtlarında aynı anda arama yapar. Ctrl+K kısayolu komut paletini açar; buradan "Yeni öğrenci", "Yoklama al" gibi işlemlere ekran değiştirmeden ulaşabilirsiniz.',
      'Sağ üstteki ay/güneş düğmesi açık ve koyu tema arasında geçiş yapar, tercih hesabınıza kaydedilir. İlk girişte parolanızı değiştirmeniz istenirse bu zorunludur; parola değişmeden diğer ekranlar kullanılamaz.',
    ],
    body_en: [
      'The Smart Swimming School Management System keeps students, lessons, pools, memberships, payments, performance and competition data in a single database. After you sign in, the left menu shows only the modules your roles allow; screens you cannot access are hidden entirely.',
      'The search box in the top bar queries students, guardians, instructors and lessons at once. Ctrl+K opens the command palette so you can jump to actions such as "New student" or "Take attendance" without leaving the current screen.',
      'The sun/moon button at the top right switches between light and dark themes and the preference is stored on your account. If you are asked to change your password at first login this is mandatory; other screens stay locked until you do.',
    ],
    steps_tr: [
      'E-posta ve parolanızla giriş yapın.',
      'İlk giriş uyarısı çıkarsa parolanızı değiştirin.',
      'Sol menüden çalışacağınız modülü seçin.',
      'Ctrl+K ile komut paletini deneyin.',
    ],
    steps_en: [
      'Sign in with your e-mail and password.',
      'Change your password if prompted at first login.',
      'Pick the module you will work in from the left menu.',
      'Try the command palette with Ctrl+K.',
    ],
    route: '/',
  },
  {
    id: 'dashboard',
    title_tr: 'Dashboard Kullanımı',
    title_en: 'Using the Dashboard',
    body_tr: [
      'Kontrol paneli okulun o anki durumunu özetler: aktif öğrenci sayısı, bugünkü dersler, havuz doluluk oranı, aktif eğitmen sayısı ve finans göstergeleri. Veriler iki dakikada bir kendiliğinden tazelenir, bekleme yapmadan güncel rakamı görürsünüz.',
      'Sayfanın üstündeki uyarı kartları biten üyelik, geciken ödeme, yoklaması alınmamış ders gibi aksiyon gerektiren durumları gösterir. Bir uyarıya tıkladığınızda ilgili listeye doğrudan gidersiniz.',
      '"Bugünün Programı" tablosunda dersin saati, havuzu, kulvarı, eğitmeni ve kayıtlı öğrenci sayısı yer alır. Yoklaması alınmış dersler yeşil "Yoklama alındı" rozetiyle işaretlenir, böylece hangi dersin eksik kaldığını tek bakışta görürsünüz.',
      'Alt bölümdeki grafikler 30 günlük gelir eğilimini ve saatlik havuz yoğunluğunu gösterir. Finans göstergeleri yalnızca finans okuma yetkisi olan kullanıcılara açılır.',
    ],
    body_en: [
      'The dashboard summarises the current state of the school: active students, today\'s lessons, pool occupancy, active instructors and financial indicators. Figures refresh automatically every two minutes.',
      'Alert cards at the top surface anything that needs action: expiring memberships, overdue payments, lessons without attendance. Clicking an alert takes you straight to the matching list.',
      'The "Today\'s Schedule" table shows each lesson\'s time, pool, lane, instructor and enrolled count. Lessons whose attendance is already recorded carry a green badge, so missing ones stand out immediately.',
      'The charts below show the 30-day revenue trend and hourly pool load. Financial figures appear only for users with finance read permission.',
    ],
    steps_tr: [
      'Uyarı kartlarını gözden geçirin.',
      'Bugünün programında yoklaması alınmamış dersleri belirleyin.',
      'Havuz doluluk oranını kontrol edin.',
      'Gelir eğilimi grafiğinden ay içi seyri izleyin.',
    ],
    steps_en: [
      'Review the alert cards.',
      'Spot lessons without attendance in today\'s schedule.',
      'Check the pool occupancy rate.',
      'Follow the month with the revenue trend chart.',
    ],
    route: '/',
  },
  {
    id: 'students',
    title_tr: 'Öğrenci Ekleme',
    title_en: 'Adding a Student',
    body_tr: [
      'Öğrenciler ekranında sağ üstteki "Yeni Öğrenci" butonu kayıt formunu açar. Ad, soyad ve doğum tarihi zorunludur; öğrenci numarasını boş bırakırsanız sistem OGR00001 biçiminde otomatik üretir.',
      'Yüzme seviyesi (başlangıçtan elit seviyeye) ders planlamasında ve raporlarda filtre olarak kullanılır. Grup ataması zorunlu değildir, sonradan da değiştirilebilir.',
      'KVKK onay kutusu kişisel veri işleme rızasını kaydeder. Onay işaretlenmezse CAIO denetim modülü bu kaydı eksik olarak raporlar.',
      'Kaydettikten sonra öğrenci profilinde devam oranı, üyelik, ödemeler, performans ve geçmiş sekmeleri oluşur. Listede arama, durum, seviye, grup, eğitmen ve yaş aralığı filtreleri ile sayfalama vardır.',
    ],
    body_en: [
      'On the Students screen the "New Student" button at the top right opens the form. First name, last name and birth date are required; leaving the student number blank generates one automatically in the OGR00001 format.',
      'The swim level (beginner through elite) is used as a filter in scheduling and reports. Assigning a group is optional and can be changed later.',
      'The data-protection consent box records explicit consent for processing personal data. If it is not ticked, the CAIO audit module reports the record as incomplete.',
      'After saving, the student profile gains tabs for attendance rate, membership, payments, performance and history. The list supports search plus status, level, group, instructor and age-range filters with pagination.',
    ],
    steps_tr: [
      'Öğrenciler ekranını açın.',
      '"Yeni Öğrenci" butonuna basın.',
      'Ad, soyad ve doğum tarihini girin.',
      'Yüzme seviyesini seçin, gerekiyorsa grup atayın.',
      'KVKK onayını işaretleyip kaydedin.',
    ],
    steps_en: [
      'Open the Students screen.',
      'Click "New Student".',
      'Enter first name, last name and birth date.',
      'Select the swim level and assign a group if needed.',
      'Tick the consent box and save.',
    ],
    route: '/students',
  },
  {
    id: 'guardians',
    title_tr: 'Veli Ekleme',
    title_en: 'Adding a Guardian',
    body_tr: [
      'Veliler ekranı, öğrencilerin yasal temsilcilerini tutar. Bir veli birden fazla öğrenciye bağlanabilir; kardeşler için ayrı veli kaydı açmanız gerekmez.',
      'Yakınlık alanı (anne, baba, veli, büyükanne/büyükbaba, kardeş, diğer) iletişim listelerinde ve raporlarda kullanılır. Telefon ve e-posta alanları bildirim gönderiminde esas alınır.',
      'Öğrenciye veli bağlarken bir kişiyi "birincil veli" olarak işaretleyebilirsiniz; acil durum iletişiminde önce bu kişi listelenir.',
      'Veli portalı yetkisi verilen kullanıcılar "Çocuklarım" ekranından yaklaşan dersleri, son yoklamaları ve bakiye durumunu görebilir.',
    ],
    body_en: [
      'The Guardians screen stores the legal representatives of students. One guardian can be linked to several students, so siblings do not need duplicate guardian records.',
      'The relationship field (mother, father, parent, grandparent, sibling, other) is used in contact lists and reports. Phone and e-mail are the basis for notifications.',
      'When linking a guardian to a student you can mark one person as the primary guardian; that contact is listed first in emergencies.',
      'Users granted portal access can see upcoming lessons, recent attendance and balance from the "My Children" screen.',
    ],
    steps_tr: [
      'Veliler ekranını açın.',
      'Yeni veli kaydı oluşturun ve yakınlık türünü seçin.',
      'Telefon ve e-posta bilgilerini girin.',
      'Öğrenci profilinden veliyi bağlayın ve birincil veliyi işaretleyin.',
    ],
    steps_en: [
      'Open the Guardians screen.',
      'Create a guardian record and choose the relationship type.',
      'Enter phone and e-mail details.',
      'Link the guardian from the student profile and mark the primary one.',
    ],
    route: '/guardians',
  },
  {
    id: 'instructors',
    title_tr: 'Eğitmen Ekleme',
    title_en: 'Adding an Instructor',
    body_tr: [
      'Eğitmenler ekranında ad, soyad ve unvan girilerek kayıt açılır; personel numarası EGT0001 biçiminde otomatik üretilir. Uzmanlık alanları (bebek yüzmesi, adaptif yüzme, yarışma antrenörlüğü gibi) ders atamasında filtre olarak çalışır.',
      'Sertifika sekmesinden cankurtaran, ilk yardım veya antrenörlük belgelerini geçerlilik tarihiyle ekleyebilirsiniz. Süresi dolan sertifikalar listede uyarı rengiyle gösterilir.',
      'Müsaitlik takvimi haftalık olarak tanımlanır. Ders oluştururken sistem, eğitmenin müsait olmadığı saatlerde çakışma uyarısı verir.',
      'İzin kayıtları girildiğinde o tarihlerdeki ders atamaları çakışma denetiminde işaretlenir. İş yükü ekranı, seçilen tarih aralığında eğitmen başına toplam ders ve saat dağılımını gösterir.',
    ],
    body_en: [
      'On the Instructors screen a record is created with first name, last name and job title; the employee number is generated automatically as EGT0001. Specialties (baby swimming, adaptive swimming, competition coaching and so on) act as filters when assigning lessons.',
      'From the certificates tab you can add lifeguard, first-aid or coaching documents with their expiry dates. Expired certificates are highlighted in the list.',
      'Availability is defined per week. When creating a lesson the system raises a conflict warning for hours the instructor is not available.',
      'Once leave records are entered, lesson assignments on those dates are flagged during conflict checks. The workload screen shows total lessons and hours per instructor for the selected date range.',
    ],
    steps_tr: [
      'Eğitmenler ekranını açın ve yeni kayıt oluşturun.',
      'Uzmanlık alanlarını seçin.',
      'Sertifikaları geçerlilik tarihleriyle ekleyin.',
      'Haftalık müsaitlik takvimini doldurun.',
      'Varsa izin kayıtlarını girin.',
    ],
    steps_en: [
      'Open the Instructors screen and create a record.',
      'Select the specialties.',
      'Add certificates with their expiry dates.',
      'Fill in the weekly availability calendar.',
      'Enter leave records if any.',
    ],
    route: '/instructors',
  },
  {
    id: 'pools',
    title_tr: 'Havuz ve Kulvar Oluşturma',
    title_en: 'Creating Pools and Lanes',
    body_tr: [
      'Havuzlar ekranında her tesis için uzunluk, derinlik, kulvar sayısı ve çalışma saatleri tanımlanır. Havuz uzunluğu (25 m / 50 m) performans kayıtlarında kısa/uzun kulvar ayrımı için kullanılır.',
      'Kulvarlar havuza bağlı olarak eklenir; her kulvara numara, ad ve kullanım amacı verilebilir. Ders oluştururken kulvar seçilmezse sistem boş kulvarlardan birini önerir.',
      'Kulvar planı ekranı seçtiğiniz gün için saat-kulvar ızgarasında hangi dersin nerede olduğunu gösterir. Boş kulvar sorgusu, verilen saat aralığında kaç kulvarın müsait olduğunu döndürür.',
      'Bakım kayıtları girildiğinde havuz o tarihlerde kapalı sayılır ve ders planlamasında uyarı üretir. Su kalitesi kayıtlarında klor ve pH değerleri geçmişe dönük izlenir.',
    ],
    body_en: [
      'On the Pools screen you define length, depth, lane count and operating hours for each facility. Pool length (25 m / 50 m) determines the short/long course distinction in performance records.',
      'Lanes are added under a pool; each lane can have a number, name and intended use. If no lane is chosen when creating a lesson, the system suggests one of the free lanes.',
      'The lane plan screen shows an hour-by-lane grid for the selected day. The free-lane query returns how many lanes are available in a given time range.',
      'When maintenance records are entered the pool counts as closed on those dates and scheduling raises a warning. Water-quality records track chlorine and pH values over time.',
    ],
    steps_tr: [
      'Havuzlar ekranından yeni havuz oluşturun.',
      'Uzunluk, derinlik ve çalışma saatlerini girin.',
      'Havuzun kulvarlarını numaralayarak ekleyin.',
      'Kulvar planı ekranından günlük dolulukları kontrol edin.',
      'Planlı bakımları takvime işleyin.',
    ],
    steps_en: [
      'Create a new pool on the Pools screen.',
      'Enter length, depth and operating hours.',
      'Add the lanes with their numbers.',
      'Check daily occupancy on the lane plan screen.',
      'Record planned maintenance on the calendar.',
    ],
    route: '/pools',
  },
  {
    id: 'lessons',
    title_tr: 'Ders Oluşturma',
    title_en: 'Creating a Lesson',
    body_tr: [
      'Ders oluştururken başlık, tür, başlangıç-bitiş saati, havuz, kulvar, eğitmen ve kapasite belirlenir. Öğrencileri aynı formda seçerek dersi kayıtla birlikte açabilirsiniz.',
      'Kaydetmeden önce sistem çakışma denetimi yapar: aynı kulvarda başka ders, eğitmenin başka dersi veya izni, öğrencinin aynı saatte başka dersi. Çakışma varsa kayıt reddedilir ve çakışan kayıtlar listelenir.',
      'Bilinçli olarak üst üste ders açmak isterseniz "Yine de oluştur" seçeneği çakışma denetimini zorlayarak geçer. Bu seçim denetim kaydına yazılır.',
      'Seri ders özelliği ile haftanın belirli günlerinde tekrarlayan program oluşturulur; tatil günlerini atlama seçeneği açıksa resmi tatillerde ders üretilmez.',
    ],
    body_en: [
      'A lesson is created with title, type, start and end time, pool, lane, instructor and capacity. You can enrol students in the same form so the lesson opens with its roster.',
      'Before saving, the system checks conflicts: another lesson in the same lane, the instructor busy or on leave, or a student already booked at that hour. If there is a conflict the record is rejected and the clashing entries are listed.',
      'If you deliberately want overlapping lessons, the "Create anyway" option forces past the conflict check. That choice is written to the audit log.',
      'The lesson series feature creates a repeating programme on selected weekdays; when the skip-holidays option is on, no lesson is generated on public holidays.',
    ],
    steps_tr: [
      'Dersler ekranından yeni ders oluşturun.',
      'Havuz, kulvar, eğitmen ve saat aralığını seçin.',
      'Kapasiteyi belirleyin ve öğrencileri ekleyin.',
      'Çakışma uyarısı çıkarsa kayıtları inceleyin.',
      'Tekrarlayan program için seri ders oluşturun.',
    ],
    steps_en: [
      'Create a new lesson from the Lessons screen.',
      'Select pool, lane, instructor and time range.',
      'Set the capacity and add students.',
      'Review the records if a conflict warning appears.',
      'Use lesson series for a repeating programme.',
    ],
    route: '/lessons',
  },
  {
    id: 'calendar',
    title_tr: 'Ders Takvimi',
    title_en: 'Lesson Calendar',
    body_tr: [
      'Takvim ekranı seçilen tarih aralığındaki tüm dersleri renk kodlu olarak gösterir. Havuz, eğitmen, grup ve ders türü filtreleriyle görünüm daraltılabilir.',
      'Bir derse tıkladığınızda kayıtlı öğrenciler, kulvar ve eğitmen bilgisi açılır; buradan yoklama ekranına geçebilirsiniz.',
      'Dersi taşımak için yeni saat, kulvar veya eğitmen seçilir. Taşıma işlemi de çakışma denetiminden geçer ve gerekirse zorlama seçeneği sunar.',
      'İptal edilen dersler takvimde ayrı renkte kalır ve iptal gerekçesi kayıt altına alınır; silinmez, böylece geçmiş raporlar tutarlı kalır.',
    ],
    body_en: [
      'The calendar shows every lesson in the selected date range with colour coding. Pool, instructor, group and lesson-type filters narrow the view.',
      'Clicking a lesson reveals the enrolled students, lane and instructor; from there you can jump to the attendance screen.',
      'To move a lesson you pick a new time, lane or instructor. The move also passes the conflict check and offers the force option if needed.',
      'Cancelled lessons stay on the calendar in a distinct colour with the cancellation reason recorded; they are not deleted so historical reports stay consistent.',
    ],
    steps_tr: [
      'Takvim ekranını açın ve tarih aralığını seçin.',
      'Havuz veya eğitmen filtresini uygulayın.',
      'Ders detayını görmek için karta tıklayın.',
      'Gerekirse dersi yeni saate taşıyın.',
    ],
    steps_en: [
      'Open the calendar and choose a date range.',
      'Apply the pool or instructor filter.',
      'Click a card to see lesson details.',
      'Move the lesson to a new time if needed.',
    ],
    route: '/calendar',
  },
  {
    id: 'attendance',
    title_tr: 'Yoklama Alma',
    title_en: 'Taking Attendance',
    body_tr: [
      'Yoklama ekranında ders seçilir ve kayıtlı öğrenciler listelenir. Her öğrenci için geldi, gelmedi, geç kaldı veya mazeretli işaretlenir; geç kalma dakikası ve mazeret gerekçesi ayrıca girilebilir.',
      '"Kredi düş" seçeneği açıkken yoklama kaydedildiğinde öğrencinin aktif üyeliğinden bir ders kredisi düşülür. Kapalı bırakırsanız devam kaydı tutulur ama üyelik hakkı harcanmaz.',
      'QR ile giriş için derse özel bir kod üretilir; kod belirlediğiniz süre boyunca geçerlidir ve öğrenci kartı okutulduğunda yoklama otomatik işlenir.',
      'Gelmeyen bir öğrenci için telafi dersi tanımlanabilir; telafi kaydı orijinal yoklamaya bağlanır ve öğrenci geçmişinde izlenir.',
    ],
    body_en: [
      'On the attendance screen you pick a lesson and its enrolled students are listed. Each student is marked present, absent, late or excused; late minutes and an excuse reason can also be entered.',
      'With the "consume credits" option on, saving attendance deducts one lesson credit from the student\'s active membership. Leaving it off records attendance without spending the entitlement.',
      'For QR check-in a lesson-specific code is generated; it stays valid for the period you set and attendance is recorded automatically when the student card is scanned.',
      'A make-up lesson can be defined for an absent student; the make-up record is linked to the original attendance and tracked in the student history.',
    ],
    steps_tr: [
      'Yoklama ekranından dersi seçin.',
      'Öğrencileri geldi/gelmedi olarak işaretleyin.',
      'Geç kalanlar için dakika girin.',
      'Kredi düşme seçeneğini kontrol edip kaydedin.',
      'Gerekirse telafi dersi tanımlayın.',
    ],
    steps_en: [
      'Select the lesson on the attendance screen.',
      'Mark students present or absent.',
      'Enter late minutes where relevant.',
      'Check the credit option and save.',
      'Define a make-up lesson if needed.',
    ],
    route: '/attendance',
  },
  {
    id: 'memberships',
    title_tr: 'Üyelik Oluşturma',
    title_en: 'Creating a Membership',
    body_tr: [
      'Önce paketler tanımlanır: ders adedi, geçerlilik süresi ve fiyat. Üyelik açarken öğrenci ve paket seçilir, başlangıç tarihi girilir; bitiş tarihi paket süresine göre hesaplanır.',
      'İndirim tutarı ve gerekçesi girilebilir. "Ödeme oluştur" seçeneği işaretlenirse üyelikle birlikte tahsilat kaydı da açılır ve finans modülünde görünür.',
      'Dondurma işlemi başlangıç ve bitiş tarihi ister; dondurulan gün sayısı üyelik bitişine eklenir. Çözme işlemi üyeliği kaldığı yerden devam ettirir.',
      'Biten üyelikler ve kredisi azalan öğrenciler ayrı listelerde izlenir. Yenileme sırasında aynı veya farklı bir paket seçilebilir, isteğe bağlı olarak yeni ödeme kaydı üretilir.',
    ],
    body_en: [
      'Packages are defined first: lesson count, validity period and price. When opening a membership you pick the student and package and enter the start date; the end date is calculated from the package duration.',
      'A discount amount and reason can be entered. If "create payment" is ticked, a payment record is opened alongside the membership and appears in the finance module.',
      'Freezing asks for a start and end date; the frozen days are added to the membership end. Unfreezing resumes it where it left off.',
      'Expiring memberships and students with low credit are tracked in separate lists. On renewal you can choose the same or a different package and optionally generate a new payment.',
    ],
    steps_tr: [
      'Paketleri tanımlayın (ders adedi, süre, fiyat).',
      'Üyelikler ekranından yeni üyelik açın.',
      'Öğrenci ve paketi seçin, indirim varsa girin.',
      'Gerekiyorsa ödeme kaydını birlikte oluşturun.',
      'Biten üyelikler listesini düzenli kontrol edin.',
    ],
    steps_en: [
      'Define packages (lesson count, duration, price).',
      'Open a new membership from the Memberships screen.',
      'Select the student and package, enter any discount.',
      'Create the payment record together if needed.',
      'Check the expiring memberships list regularly.',
    ],
    route: '/memberships',
  },
  {
    id: 'payments',
    title_tr: 'Ödeme Alma',
    title_en: 'Recording a Payment',
    body_tr: [
      'Tahsilat kaydı öğrenci, tutar, para birimi, ödeme yöntemi ve tarih ile oluşturulur. Ödeme bir üyeliğe veya faturaya bağlanabilir; bağlandığında ilgili kaydın bakiyesi otomatik güncellenir.',
      'Yöntem alanı nakit, kredi kartı, havale gibi seçenekleri içerir ve gün sonu raporlarında kırılım olarak kullanılır. Referans alanına dekont veya işlem numarası yazılabilir.',
      'İade işleminde tutar ve gerekçe zorunludur; orijinal ödeme silinmez, iade ayrı bir hareket olarak eklenir. Bu sayede kasa hareketleri geriye dönük izlenebilir kalır.',
      'Ödeme silme yalnızca gerekçe girilerek yapılır ve denetim kaydına yazılır.',
    ],
    body_en: [
      'A payment is created with student, amount, currency, method and date. It can be linked to a membership or invoice; when linked, the related balance is updated automatically.',
      'The method field covers cash, card, bank transfer and similar options and is used as a breakdown in end-of-day reports. The reference field can hold a receipt or transaction number.',
      'Refunds require an amount and a reason; the original payment is not deleted, the refund is added as a separate movement. Cash movements therefore stay auditable.',
      'Deleting a payment is only possible with a reason and is written to the audit log.',
    ],
    steps_tr: [
      'Finans ekranından yeni ödeme oluşturun.',
      'Öğrenciyi ve tutarı girin.',
      'Ödeme yöntemini ve tarihini seçin.',
      'Varsa üyelik veya fatura ile eşleştirin.',
      'İade gerekirse gerekçesiyle kaydedin.',
    ],
    steps_en: [
      'Create a new payment from the Finance screen.',
      'Enter the student and amount.',
      'Choose the method and date.',
      'Match it to a membership or invoice if applicable.',
      'Record refunds with their reason.',
    ],
    route: '/finance',
  },
  {
    id: 'finance',
    title_tr: 'Finans Modülü',
    title_en: 'Finance Module',
    body_tr: [
      'Finans modülü tahsilatları, faturaları, giderleri ve indirimleri tek ekranda toplar. Tarih aralığı seçildiğinde gelir, gider ve net sonuç özet olarak hesaplanır.',
      'Alacak yaşlandırma raporu açık tutarları güncel, 1-30 gün, 31-60 gün ve 60 günden fazla olarak gruplar. Bu kırılım hangi velilerin aranacağını önceliklendirmenizi sağlar.',
      'Gider kayıtlarına kategori verilir (personel, kimyasal, bakım, kira gibi) ve aylık gider dağılımı grafikte gösterilir.',
      'İndirim tanımları kampanya adı, oran veya tutar ve geçerlilik tarihiyle tutulur; üyelik açarken listeden seçilir. Finans ekranlarına yalnızca finans yetkisi olan kullanıcılar erişebilir.',
    ],
    body_en: [
      'The finance module brings payments, invoices, expenses and discounts together on one screen. Selecting a date range computes income, expense and net result.',
      'The receivables ageing report groups open amounts as current, 1-30 days, 31-60 days and over 60 days. This breakdown helps prioritise which guardians to contact.',
      'Expenses are categorised (staff, chemicals, maintenance, rent and so on) and the monthly distribution is shown on a chart.',
      'Discount definitions hold a campaign name, rate or amount and validity dates, and are picked from a list when opening a membership. Only users with finance permission can reach these screens.',
    ],
    steps_tr: [
      'Finans ekranında tarih aralığını seçin.',
      'Gelir-gider özetini inceleyin.',
      'Alacak yaşlandırmasından gecikenleri listeleyin.',
      'Gider kayıtlarını kategorileyerek girin.',
    ],
    steps_en: [
      'Choose a date range on the Finance screen.',
      'Review the income and expense summary.',
      'List overdue balances from the ageing report.',
      'Enter expenses with categories.',
    ],
    route: '/finance',
  },
  {
    id: 'performance',
    title_tr: 'Performans Kaydı',
    title_en: 'Recording Performance',
    body_tr: [
      'Performans kaydında öğrenci, stil (serbest, sırtüstü, kurbağalama, kelebek, karışık), mesafe, kulvar tipi ve derece girilir. Derece 1:35.12 biçiminde yazılır ve saniyeye çevrilerek saklanır.',
      'Split zamanları, kulaç sayısı, kulaç frekansı, çıkış tepki süresi ve dönüş süresi isteğe bağlı alanlardır; girildiğinde analiz ekranlarında ayrı grafiklerde gösterilir.',
      'Kayıt yarışmada alındıysa "yarışma" işareti konur; kişisel rekor hesabı yarışma ve antrenman derecelerini ayırarak yapar.',
      'Öğrenci özeti ekranında kişisel rekorlar, gelişim eğrisi ve en zayıf stil analizi bulunur. Sistem ayrıca en çok gelişen ve performansı gerileyen sporcuları otomatik listeler.',
    ],
    body_en: [
      'A performance record takes the student, stroke (freestyle, backstroke, breaststroke, butterfly, medley), distance, course type and time. Times are typed as 1:35.12 and stored in seconds.',
      'Splits, stroke count, stroke rate, reaction time and turn time are optional; when entered they appear in dedicated charts on the analysis screens.',
      'If the record comes from a competition it is flagged as such; personal-best calculation separates competition and training times.',
      'The student summary shows personal bests, the progression curve and the weakest-stroke analysis. The system also lists top improvers and declining athletes automatically.',
    ],
    steps_tr: [
      'Performans ekranından yeni kayıt açın.',
      'Öğrenci, stil ve mesafeyi seçin.',
      'Dereceyi 1:35.12 biçiminde girin.',
      'Yarışma kaydıysa işaretleyin.',
      'Öğrenci özetinden gelişim eğrisini inceleyin.',
    ],
    steps_en: [
      'Create a new record on the Performance screen.',
      'Select student, stroke and distance.',
      'Enter the time in the 1:35.12 format.',
      'Flag it if it is a competition result.',
      'Review the progression curve in the student summary.',
    ],
    route: '/performance',
  },
  {
    id: 'competitions',
    title_tr: 'Yarışma Yönetimi',
    title_en: 'Competition Management',
    body_tr: [
      'Yarışma kaydında ad, düzenleyen kurum, seviye (kulüp, il, bölge, ulusal, uluslararası), tarih aralığı ve son kayıt tarihi tutulur. Yarışmaya etkinlikler (stil + mesafe + cinsiyet kategorisi) eklenir.',
      'Sporcular etkinliklere seed derecesiyle kaydedilir. Seri oluşturma işlemi seed derecelerine göre sporcuları serilere ve kulvarlara otomatik dağıtır.',
      'Yarışma sonrası her kayda derece, sıralama ve madalya girilir; diskalifiye durumunda gerekçe zorunludur. Girilen dereceler kulüp rekoru eşiğini geçerse rekor listesi güncellenir.',
      'Madalya özeti seçilen yıl için altın, gümüş, bronz dağılımını ve sporcu bazlı kırılımı verir.',
    ],
    body_en: [
      'A competition record holds the name, organiser, level (club, local, regional, national, international), date range and registration deadline. Events (stroke + distance + gender category) are added to it.',
      'Athletes are entered into events with a seed time. Heat seeding distributes athletes into heats and lanes automatically according to seed times.',
      'After the meet, each entry gets a result time, rank and medal; a disqualification requires a reason. When a time beats the club record threshold the record list is updated.',
      'The medal summary gives the gold, silver and bronze distribution for the selected year with a per-athlete breakdown.',
    ],
    steps_tr: [
      'Yarışmalar ekranından yeni yarışma oluşturun.',
      'Etkinlikleri (stil, mesafe, kategori) ekleyin.',
      'Sporcuları seed derecesiyle kaydedin.',
      'Serileri otomatik oluşturun.',
      'Yarışma sonrası sonuçları ve madalyaları girin.',
    ],
    steps_en: [
      'Create a competition on the Competitions screen.',
      'Add the events (stroke, distance, category).',
      'Enter athletes with their seed times.',
      'Generate the heats automatically.',
      'Enter results and medals after the meet.',
    ],
    route: '/competitions',
  },
  {
    id: 'reports',
    title_tr: 'Rapor Oluşturma',
    title_en: 'Creating Reports',
    body_tr: [
      'Raporlar ekranı yalnızca yetkiniz olan rapor tanımlarını listeler. Rapor seçtikten sonra dönem, tarih aralığı, havuz, eğitmen, grup ve öğrenci filtreleri uygulanır.',
      'Önizleme, dışa aktarmadan önce satır sayısını ve içeriği ekranda gösterir; böylece yanlış filtreyle büyük dosya üretmezsiniz.',
      'Dışa aktarma PDF, XLSX, CSV ve JSON biçimlerini destekler. Rapor dili seçilebilir; PDF çıktısında grafik ekleme seçeneği vardır.',
      'Sık kullandığınız filtre setini şablon olarak kaydedebilir, sonraki seferde tek tıkla çağırabilirsiniz.',
    ],
    body_en: [
      'The Reports screen lists only the report definitions you are allowed to run. After picking a report you apply period, date range, pool, instructor, group and student filters.',
      'Preview shows the row count and content on screen before export, so you do not generate a large file with the wrong filter.',
      'Export supports PDF, XLSX, CSV and JSON. The report language can be selected and PDF output offers an include-charts option.',
      'A frequently used filter set can be saved as a template and recalled with one click next time.',
    ],
    steps_tr: [
      'Raporlar ekranından rapor türünü seçin.',
      'Dönem ve filtreleri belirleyin.',
      'Önizleme ile içeriği doğrulayın.',
      'Biçimi seçip dışa aktarın.',
      'Filtre setini şablon olarak kaydedin.',
    ],
    steps_en: [
      'Choose a report type on the Reports screen.',
      'Set the period and filters.',
      'Verify the content with preview.',
      'Pick a format and export.',
      'Save the filter set as a template.',
    ],
    route: '/reports',
  },
  {
    id: 'statistics',
    title_tr: 'İstatistik Merkezi',
    title_en: 'Statistics Center',
    body_tr: [
      'İstatistik merkezi öğrenci, eğitmen, havuz, yoklama ve KPI sekmelerinden oluşur. Tüm sekmeler ortak dönem seçicisini kullanır; özel aralık seçilirse başlangıç ve bitiş tarihi girilir.',
      'KPI sekmesinde hedef değerler tanımlanır ve gerçekleşen değerle karşılaştırılır. Hedefin altında kalan göstergeler uyarı rengiyle işaretlenir.',
      'Kohort analizi aylık kayıt gruplarının kaç ay sonra hâlâ aktif olduğunu gösterir; bu, öğrenci elde tutma oranını değerlendirmenin en doğrudan yoludur.',
      'Gelişmiş sekmesinde devam-performans korelasyonu, devamsızlık aykırı değerleri ve yaş/doluluk dağılımları yer alır. Buradaki tüm sayılar veritabanından hesaplanır, tahmin içermez.',
    ],
    body_en: [
      'The statistics center has student, instructor, pool, attendance and KPI tabs. All tabs share the period selector; choosing a custom range asks for start and end dates.',
      'On the KPI tab you define target values and compare them with actuals. Indicators below target are highlighted.',
      'Cohort analysis shows how many students from each monthly intake are still active after N months, which is the most direct way to judge retention.',
      'The advanced tab covers the attendance-performance correlation, attendance outliers and age/occupancy distributions. Every number here is computed from the database and contains no estimates.',
    ],
    steps_tr: [
      'İstatistik merkezini açın ve dönemi seçin.',
      'İlgili sekmeye geçin.',
      'KPI hedeflerini tanımlayın.',
      'Kohort analizinden elde tutma oranını okuyun.',
    ],
    steps_en: [
      'Open the statistics center and select a period.',
      'Switch to the relevant tab.',
      'Define the KPI targets.',
      'Read retention from the cohort analysis.',
    ],
    route: '/statistics',
  },
  {
    id: 'backup',
    title_tr: 'Yedekleme',
    title_en: 'Backup',
    body_tr: [
      'Yedekleme ekranı mevcut yedekleri, boyutlarını ve doğrulama durumlarını listeler. Yeni yedek alırken tür seçilir, açıklama girilir ve yüklenen dosyaların ile günlüklerin dahil edilip edilmeyeceği belirtilir.',
      'Önemli yedekler "koru" işaretiyle kilitlenir; temizlik işlemi korumalı yedekleri silmez.',
      'Doğrulama işlemi yedek dosyasının bütünlüğünü kontrol eder ve bozuksa listede kırmızı durumla gösterir. Geri yüklemeden önce doğrulama yapmanız önerilir.',
      'Zamanlanmış yedekleme ayarlardan açılır; açık olduğunda sistem belirlenen aralıkta otomatik yedek üretir ve sonucu bildirim olarak gönderir.',
    ],
    body_en: [
      'The backup screen lists existing backups with their size and verification status. When taking a new backup you choose the type, add a note and decide whether uploads and logs are included.',
      'Important backups can be locked with the "protect" flag; the cleanup routine never deletes protected backups.',
      'Verification checks the integrity of the backup file and marks corrupted ones in red. Verifying before a restore is recommended.',
      'Scheduled backups are enabled in settings; when on, the system produces backups at the chosen interval and sends the result as a notification.',
    ],
    steps_tr: [
      'Yedekleme ekranını açın.',
      'Yeni yedek alın ve açıklama girin.',
      'Yedeği doğrulayın.',
      'Kritik yedeği koruma altına alın.',
      'Zamanlanmış yedeklemeyi etkinleştirin.',
    ],
    steps_en: [
      'Open the backup screen.',
      'Take a new backup and add a note.',
      'Verify the backup.',
      'Protect the critical backup.',
      'Enable scheduled backups.',
    ],
    route: '/settings',
  },
  {
    id: 'restore',
    title_tr: 'Geri Yükleme',
    title_en: 'Restore',
    body_tr: [
      'Geri yükleme mevcut veritabanının üzerine yazar; bu nedenle işlem öncesi önizleme ekranı hangi tabloların ve kaç kaydın geleceğini gösterir.',
      '"Güvenlik yedeği oluştur" seçeneği açıkken sistem geri yüklemeden hemen önce mevcut durumun yedeğini alır. Beklenmedik bir sonuçta bu yedekle eski duruma dönebilirsiniz.',
      'İşlem açık onay ister; onay kutusu işaretlenmeden geri yükleme başlamaz. Geri yükleme sırasında diğer kullanıcıların sistemi kullanmaması gerekir.',
      'Tüm geri yükleme denemeleri geçmiş listesinde tarih, kullanıcı ve sonuç bilgisiyle saklanır.',
    ],
    body_en: [
      'A restore overwrites the current database, so the preview screen first shows which tables and how many records will be written.',
      'With "create safety backup" enabled the system takes a snapshot of the current state right before restoring. If the result is unexpected you can return to the previous state with it.',
      'The operation requires explicit confirmation; it will not start until the confirm box is ticked. Other users should stay out of the system while it runs.',
      'Every restore attempt is stored in the history list with date, user and outcome.',
    ],
    steps_tr: [
      'Geri yüklenecek yedeği seçin.',
      'Önizleme ile içeriği kontrol edin.',
      'Güvenlik yedeği seçeneğini açık bırakın.',
      'Onay kutusunu işaretleyip işlemi başlatın.',
      'Sonucu geri yükleme geçmişinden doğrulayın.',
    ],
    steps_en: [
      'Select the backup to restore.',
      'Check the content with preview.',
      'Leave the safety backup option on.',
      'Tick the confirmation box and start.',
      'Verify the outcome in the restore history.',
    ],
    route: '/settings',
  },
  {
    id: 'ai',
    title_tr: 'AI Merkezi',
    title_en: 'AI Center',
    body_tr: [
      'AI merkezi, sağlayıcı durumlarını, model listelerini ve analiz ekranını bir arada tutar. Bir soru sorduğunuzda sistem önce veritabanından ilgili metrikleri hesaplar, sonra bu metrikleri modele gönderir.',
      'Sonuç ekranında yeşil panel hesaplanmış gerçek veriyi, mor panel modelin yorumunu gösterir. Bu ayrım bilinçlidir: karar verirken hangi bilginin ölçüm, hangisinin tahmin olduğunu her zaman görürsünüz.',
      'Analiz kapsamları arasında öğrenci performansı, gerileyen sporcular, devamsızlık, finans, elde tutma, eğitmen iş yükü ve program optimizasyonu bulunur.',
      'AI bağlantısı yoksa yorum paneli yerine uyarı gösterilir; hesaplanan veri paneli yine görünür, yani AI kapalıyken de sayısal analiz çalışır.',
    ],
    body_en: [
      'The AI center brings provider status, model lists and the analysis screen together. When you ask a question the system first computes the relevant metrics from the database and only then sends them to the model.',
      'In the result view the green panel holds computed real data and the purple panel holds the model interpretation. The separation is deliberate: you always see which part is measurement and which is inference.',
      'Analysis scopes include student performance, declining athletes, attendance, finance, retention, instructor workload and schedule optimisation.',
      'If no AI connection is available a warning replaces the interpretation panel; the computed data panel still appears, so numeric analysis works even with AI off.',
    ],
    steps_tr: [
      'AI merkezini açın ve sağlayıcı durumunu kontrol edin.',
      'Analiz kapsamını seçin.',
      'Soruyu yazın ve çalıştırın.',
      'Yeşil paneldeki gerçek veriyi okuyun.',
      'Mor paneldeki yorumu değerlendirme olarak kullanın.',
    ],
    steps_en: [
      'Open the AI center and check provider status.',
      'Choose the analysis scope.',
      'Write the question and run it.',
      'Read the real data in the green panel.',
      'Treat the purple panel as commentary.',
    ],
    route: '/ai',
  },
  {
    id: 'localAi',
    title_tr: 'Local AI',
    title_en: 'Local AI',
    body_tr: [
      'Yerel AI, modeli kendi bilgisayarınızda veya kurum ağınızda çalıştırır. Veriler dışarı çıkmaz; kişisel verilerin bulunduğu analizler için tercih edilen yöntem budur.',
      'Bağlantı için uç nokta adresi ve model adı girilir. "Sağlık kontrolü" butonu servisin ayakta olup olmadığını, gecikmesini ve kaç model sunduğunu ölçer.',
      'Model listesi servisten canlı olarak çekilir; kurulu olmayan bir model seçilirse analiz hata döndürür. Yönlendirme ekranından hangi görev için hangi modelin kullanılacağını belirleyebilirsiniz.',
      'Yerel modeller genellikle bulut modellerden yavaştır; uzun analizlerde zaman aşımı süresini artırmanız gerekebilir.',
    ],
    body_en: [
      'Local AI runs the model on your own machine or inside your network. Data never leaves the premises, which makes it the preferred option for analyses involving personal data.',
      'The connection needs an endpoint address and a model name. The health check button measures whether the service is up, its latency and how many models it serves.',
      'The model list is fetched live from the service; selecting a model that is not installed makes the analysis fail. The routing screen lets you decide which model handles which task.',
      'Local models are usually slower than cloud models, so long analyses may need a higher timeout.',
    ],
    steps_tr: [
      'Yerel AI servisini başlatın.',
      'AI ayarlarında uç nokta adresini girin.',
      'Sağlık kontrolü ile bağlantıyı doğrulayın.',
      'Model listesinden varsayılan modeli seçin.',
      'Görev bazlı yönlendirmeyi düzenleyin.',
    ],
    steps_en: [
      'Start the local AI service.',
      'Enter the endpoint in the AI settings.',
      'Verify the connection with the health check.',
      'Pick a default model from the list.',
      'Adjust the per-task routing.',
    ],
    route: '/ai',
  },
  {
    id: 'nvidiaAi',
    title_tr: 'NVIDIA AI',
    title_en: 'NVIDIA AI',
    body_tr: [
      'NVIDIA sağlayıcısı bulut üzerinden büyük modellere erişim sağlar. Anahtar girildikten sonra ekranda yalnızca maskeli hali görünür, tam anahtar arayüze geri döndürülmez.',
      'Bağlantı testi anahtarın geçerliliğini, erişilebilen model sayısını ve yanıt gecikmesini raporlar. Test başarısızsa hata mesajı ekranda gösterilir.',
      'Bulut sağlayıcı kullanıldığında analiz için gönderilen metrik özetleri dışarı çıkar; kişisel veri içeren analizlerde yerel sağlayıcıyı tercih edin.',
      'Görev yönlendirmesinde ağır analizleri buluta, hızlı ve sık çalışan görevleri yerel modele yönlendirmek dengeli bir kurulum sağlar.',
    ],
    body_en: [
      'The NVIDIA provider gives cloud access to large models. Once a key is entered only its masked form is shown; the full key is never returned to the interface.',
      'The connection test reports key validity, the number of reachable models and response latency. Failures are displayed with their error message.',
      'When a cloud provider is used, the metric summaries sent for analysis leave the premises; prefer the local provider for analyses containing personal data.',
      'Routing heavy analyses to the cloud and frequent quick tasks to the local model gives a balanced setup.',
    ],
    steps_tr: [
      'AI ayarlarında NVIDIA sağlayıcısını etkinleştirin.',
      'API anahtarını girin ve kaydedin.',
      'Bağlantı testini çalıştırın.',
      'Kullanılacak modeli seçin.',
      'Görev yönlendirmesini gözden geçirin.',
    ],
    steps_en: [
      'Enable the NVIDIA provider in the AI settings.',
      'Enter and save the API key.',
      'Run the connection test.',
      'Select the model to use.',
      'Review the task routing.',
    ],
    route: '/ai',
  },
  {
    id: 'aiDeveloper',
    title_tr: 'AI Developer Console',
    title_en: 'AI Developer Console',
    body_tr: [
      'Geliştirici konsolu, yazılı bir talimattan kod değişikliği planı üretir. Plan hangi dosyaların değişeceğini ve önerilen yamayı içerir; hiçbir değişiklik siz onaylamadan uygulanmaz.',
      'Yama uygulanmadan önce sistem otomatik olarak bir kontrol noktası oluşturur. Sonuç beklediğiniz gibi değilse geri alma işlemiyle dosyalar önceki hâline döner.',
      'Komut politikası hangi kabuk komutlarının çalıştırılabileceğini belirler; izin dışındaki komutlar gerekçesiyle birlikte reddedilir.',
      'Testleri çalıştır seçeneği yama sonrası test paketini tetikler ve sonucu ekranda gösterir. Bu ekran yalnızca geliştirici yetkisi olan kullanıcılara açıktır.',
    ],
    body_en: [
      'The developer console turns a written instruction into a code-change plan. The plan lists which files change and the proposed patch; nothing is applied until you approve it.',
      'Before a patch is applied the system creates a checkpoint automatically. If the outcome is not what you expected, rollback returns the files to their previous state.',
      'The command policy defines which shell commands may run; anything outside the allowlist is rejected with a reason.',
      'The run-tests option triggers the test suite after a patch and shows the result on screen. This screen is available only to users with developer permission.',
    ],
    steps_tr: [
      'Geliştirici konsolunu açın.',
      'Talimatı açık bir cümleyle yazın.',
      'Üretilen planı ve yamayı inceleyin.',
      'Onaylayarak uygulayın ve testleri çalıştırın.',
      'Sorun çıkarsa kontrol noktasına geri dönün.',
    ],
    steps_en: [
      'Open the developer console.',
      'Write the instruction as one clear sentence.',
      'Review the generated plan and patch.',
      'Approve, apply and run the tests.',
      'Roll back to the checkpoint if something breaks.',
    ],
    route: '/ai-developer',
  },
  {
    id: 'caio',
    title_tr: 'CAIO',
    title_en: 'CAIO',
    body_tr: [
      'CAIO, sistemi düzenli olarak denetleyen iç kontrol modülüdür. Veri bütünlüğü, eksik onaylar, atıl kayıtlar, güvenlik ve operasyon başlıklarında bulgular üretir.',
      'Gözlem modu yalnızca ölçüm yapar ve yapay zekâ çağırmaz; hızlıdır ve her zaman çalıştırılabilir. Tam çalıştırma, ölçümlerin üzerine model yorumu ekler.',
      'Her bulgunun önem derecesi (kritik, yüksek, orta, düşük) ve durumu vardır. Bulguyu inceledikten sonra kapatabilir veya not ekleyerek açık bırakabilirsiniz.',
      'Özet ekranı açık bulgu sayısını, önem ve kategori dağılımını ve son çalıştırma zamanını gösterir; kritik bulgular öne çıkarılır.',
    ],
    body_en: [
      'CAIO is the internal control module that audits the system regularly. It produces findings around data integrity, missing consents, dormant records, security and operations.',
      'Observation mode only measures and never calls the AI; it is fast and can be run at any time. A full run adds model commentary on top of the measurements.',
      'Every finding has a severity (critical, high, medium, low) and a status. After reviewing you can close it or leave it open with a note.',
      'The summary screen shows the open finding count, severity and category distribution and the last run time, with critical findings highlighted.',
    ],
    steps_tr: [
      'CAIO ekranını açın.',
      'Gözlem modunu çalıştırıp ölçümleri görün.',
      'Bulguları önem derecesine göre filtreleyin.',
      'İncelediğiniz bulguyu not ekleyerek kapatın.',
    ],
    steps_en: [
      'Open the CAIO screen.',
      'Run observation mode to see the measurements.',
      'Filter findings by severity.',
      'Close reviewed findings with a note.',
    ],
    route: '/caio',
  },
  {
    id: 'settings',
    title_tr: 'Ayarlar',
    title_en: 'Settings',
    body_tr: [
      'Ayarlar ekranı kurum bilgileri, arayüz tercihleri, AI yapılandırması ve yedekleme ayarlarını kategoriler hâlinde tutar. Kurum adı, iletişim bilgileri ve para birimi buradan girilir.',
      'Para birimi ayarı tüm ekranlardaki tutar biçimlendirmesini anında değiştirir; ayrı ayrı düzenleme gerekmez.',
      'Profil sekmesinden kendi parolanızı değiştirebilir, tema ve dil tercihinizi kaydedebilirsiniz. Bu tercihler hesabınıza bağlıdır, başka bir cihazda giriş yaptığınızda da geçerlidir.',
      'Ayar değişiklikleri denetim kaydına yazılır; kimin neyi ne zaman değiştirdiği geriye dönük izlenebilir.',
    ],
    body_en: [
      'The settings screen groups organisation details, interface preferences, AI configuration and backup settings into categories. Organisation name, contact details and currency are entered here.',
      'Changing the currency updates amount formatting across every screen at once; no per-screen edit is needed.',
      'From the profile tab you can change your own password and store your theme and language preference. These are tied to your account and follow you to other devices.',
      'Setting changes are written to the audit log, so who changed what and when stays traceable.',
    ],
    steps_tr: [
      'Ayarlar ekranını açın.',
      'Kurum bilgilerini ve para birimini girin.',
      'Profil sekmesinden parolanızı değiştirin.',
      'Tema ve dil tercihinizi kaydedin.',
    ],
    steps_en: [
      'Open the settings screen.',
      'Enter organisation details and currency.',
      'Change your password on the profile tab.',
      'Save your theme and language preference.',
    ],
    route: '/settings',
  },
  {
    id: 'permissions',
    title_tr: 'Kullanıcı Yetkileri',
    title_en: 'User Permissions',
    body_tr: [
      'Yetkilendirme rol tabanlıdır. Her rol bir izin kümesi taşır (örneğin öğrenci okuma, ders yazma, finans silme) ve bir kullanıcıya birden fazla rol atanabilir.',
      'Kullanıcı ekranından yeni hesap açılır, roller seçilir ve "ilk girişte parola değiştirsin" işareti konur. Süper kullanıcı tüm izinlere sahiptir ve yetki denetiminden muaftır.',
      'Yetkisi olmayan kullanıcı için ilgili menü öğesi hiç görünmez; adresi elle yazsa bile ekran erişim reddi mesajı verir.',
      'Hassas öğrenci bilgileri (sağlık notları gibi) ayrı bir izinle korunur; bu izni olmayan kullanıcı profilde bu alanların gizlendiğini görür.',
    ],
    body_en: [
      'Authorisation is role based. Each role carries a set of permissions (for example student read, lesson write, finance delete) and a user can hold several roles.',
      'New accounts are created on the users screen where you pick roles and can require a password change at first login. A superuser holds every permission and bypasses the checks.',
      'Menu items are hidden entirely for users without the permission; typing the address manually returns an access-denied screen.',
      'Sensitive student information such as health notes is protected by a separate permission; users without it see those fields marked as hidden on the profile.',
    ],
    steps_tr: [
      'Kullanıcılar ekranını açın.',
      'Yeni kullanıcı oluşturun ve rolleri seçin.',
      'İlk girişte parola değiştirme seçeneğini işaretleyin.',
      'Rol izin listesini gözden geçirin.',
      'Ayrılan personelin hesabını devre dışı bırakın.',
    ],
    steps_en: [
      'Open the users screen.',
      'Create a user and select the roles.',
      'Require a password change at first login.',
      'Review the role permission list.',
      'Deactivate accounts of departing staff.',
    ],
    route: '/settings',
  },
  {
    id: 'language',
    title_tr: 'Dil Değiştirme',
    title_en: 'Changing the Language',
    body_tr: [
      'Sistem Türkçe ve İngilizce çalışır. Dil, üst çubuktaki dil düğmesinden anında değiştirilir; sayfayı yenilemenize gerek yoktur.',
      'Dil seçimi yalnızca arayüz metinlerini değil, tarih, saat, sayı ve para birimi biçimlendirmesini de etkiler. Türkçede tarih 15.08.2026, İngilizcede farklı biçimde gösterilir.',
      'Rapor dışa aktarımında rapor dili ayrıca seçilebilir; arayüzünüz Türkçe kalırken İngilizce rapor üretebilirsiniz.',
      'Tercih hesabınıza kaydedilir, başka bir cihazdan girdiğinizde de aynı dille açılır.',
    ],
    body_en: [
      'The system runs in Turkish and English. The language is switched instantly from the language button in the top bar; no page reload is needed.',
      'The choice affects not only interface text but also date, time, number and currency formatting. A date shown as 15.08.2026 in Turkish appears differently in English.',
      'Report exports have their own language selector, so you can produce an English report while keeping a Turkish interface.',
      'The preference is stored on your account and applies when you sign in from another device.',
    ],
    steps_tr: [
      'Üst çubuktaki dil düğmesine tıklayın.',
      'Türkçe veya İngilizce seçin.',
      'Tarih ve para biçimlerinin değiştiğini doğrulayın.',
      'Rapor dilini dışa aktarma ekranından ayrıca seçin.',
    ],
    steps_en: [
      'Click the language button in the top bar.',
      'Choose Turkish or English.',
      'Confirm date and currency formats changed.',
      'Set the report language on the export screen.',
    ],
    route: '/settings',
  },
  {
    id: 'maintenance',
    title_tr: 'Sistem Bakımı',
    title_en: 'System Maintenance',
    body_tr: [
      'Sistem sağlığı ekranı sunucu, veritabanı, arayüz ve AI servislerinin durumunu tek bakışta gösterir. Kısıtlı veya çalışmıyor durumundaki bileşenler renkle ayrılır.',
      'Denetim kaydı kim, ne zaman, hangi kayıt üzerinde hangi işlemi yaptı sorusunu yanıtlar. Kullanıcı, işlem türü, kayıt türü ve gün aralığı ile filtrelenebilir.',
      'Üyelik durumlarını tazeleme işlemi süresi dolmuş üyelikleri toplu olarak günceller; ay başlarında çalıştırılması önerilir.',
      'Bildirim tarama işlemi biten üyelik, geciken ödeme ve yaklaşan yarışma gibi durumları tarayıp yeni bildirim üretir. Çeviri doğrulama uçları eksik dil anahtarlarını listeler.',
    ],
    body_en: [
      'The system health screen shows server, database, interface and AI service status at a glance, with degraded or down components colour coded.',
      'The audit log answers who did what to which record and when. It can be filtered by user, action type, entity type and day range.',
      'Refreshing membership statuses updates expired memberships in bulk; running it at the start of each month is recommended.',
      'The notification scan looks for expiring memberships, overdue payments and upcoming competitions and creates new notifications. The i18n validation endpoints list missing translation keys.',
    ],
    steps_tr: [
      'Sistem sağlığı ekranını kontrol edin.',
      'Denetim kaydından son işlemleri inceleyin.',
      'Üyelik durumlarını tazeleyin.',
      'Bildirim taramasını çalıştırın.',
      'Yedeğin güncel olduğunu doğrulayın.',
    ],
    steps_en: [
      'Check the system health screen.',
      'Review recent actions in the audit log.',
      'Refresh membership statuses.',
      'Run the notification scan.',
      'Verify the backup is current.',
    ],
    route: '/settings',
  },
  {
    id: 'troubleshooting',
    title_tr: 'Sorun Giderme',
    title_en: 'Troubleshooting',
    body_tr: [
      'Bir ekran boş geliyorsa önce filtreleri temizleyin: tarih aralığı veya durum filtresi çoğu zaman sonucu daraltmıştır. Listelerde "Filtreleri temizle" bağlantısı bunun için vardır.',
      '"Oturumunuz sona erdi" uyarısı alırsanız tekrar giriş yapın; sistem güvenlik gereği belirli süre sonra oturumu kapatır. Yetki hatası alıyorsanız hesabınızda ilgili izin tanımlı değildir, yöneticinize başvurun.',
      'Ders kaydedilmiyorsa çakışma denetimi devrededir; hata mesajındaki çakışan kayıtları inceleyin, gerçekten üst üste olması gerekiyorsa zorlama seçeneğini kullanın.',
      'AI analizleri hata veriyorsa AI merkezinden sağlayıcı sağlık kontrolünü çalıştırın. Yerel serviste model kurulu değilse veya bulut anahtarı geçersizse hata mesajı sebebi açıkça yazar.',
      'Sorun sürüyorsa sistem sağlığı ekranındaki durum bilgisiyle birlikte denetim kaydından son işlemleri not alın; destek için bu iki bilgi yeterlidir.',
    ],
    body_en: [
      'If a screen looks empty, clear the filters first: a date range or status filter has usually narrowed the result. The "clear filters" link in every list exists for this.',
      'If you see "your session has expired", sign in again; the system closes sessions after a period for security. A permission error means your account lacks that permission, so contact your administrator.',
      'If a lesson will not save, the conflict check is blocking it; review the clashing records in the error message and use the force option only when overlapping is genuinely intended.',
      'If AI analyses fail, run the provider health check in the AI center. The error message states the reason clearly when a local model is not installed or a cloud key is invalid.',
      'If the problem persists, note the status from the system health screen together with the last entries in the audit log; those two are enough for support.',
    ],
    steps_tr: [
      'Filtreleri temizleyip listeyi yenileyin.',
      'Oturum uyarısı varsa yeniden giriş yapın.',
      'Hata mesajındaki ayrıntıyı okuyun.',
      'Sistem sağlığı ekranını kontrol edin.',
      'Denetim kaydından son işlemleri not alın.',
    ],
    steps_en: [
      'Clear the filters and refresh the list.',
      'Sign in again if the session expired.',
      'Read the detail in the error message.',
      'Check the system health screen.',
      'Note the last entries in the audit log.',
    ],
    route: '/settings',
  },
]

export default function HelpPage() {
  const { t, i18n } = useTranslation()
  const isTR = i18n.language === 'tr'
  const [query, setQuery] = useState('')
  const [activeId, setActiveId] = useState(SECTIONS[0].id)

  // Arama: başlık, paragraflar ve adımlar üzerinde çalışır
  const sections = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase(isTR ? 'tr' : 'en')
    if (!needle) return SECTIONS
    return SECTIONS.filter((section) => {
      const haystack = [
        section.title_tr,
        section.title_en,
        ...section.body_tr,
        ...section.body_en,
        ...section.steps_tr,
        ...section.steps_en,
      ]
        .join(' ')
        .toLocaleLowerCase(isTR ? 'tr' : 'en')
      return haystack.includes(needle)
    })
  }, [query, isTR])

  function scrollToSection(id: string) {
    setActiveId(id)
    document.getElementById(`help-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <>
      <PageHeader
        title={t('help.title')}
        subtitle={t('help.subtitle')}
        icon={<BookOpen className="h-5 w-5" />}
        actions={
          <Link to="/training" className="btn-secondary btn-sm">
            <GraduationCap className="h-4 w-4" />
            {t('training.title')}
          </Link>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
        {/* İçindekiler */}
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <Card title={t('help.contents')} bodyClassName="p-3">
            <div className="relative mb-3">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                className="input pl-9 pr-9"
                placeholder={t('help.search')}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                aria-label={t('help.search')}
              />
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                  aria-label={t('common.clearFilters')}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            <p className="mb-2 px-1 text-xs text-slate-400">
              {sections.length} / {SECTIONS.length}
            </p>

            <nav className="max-h-[60vh] space-y-0.5 overflow-y-auto pr-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => scrollToSection(section.id)}
                  className={
                    activeId === section.id
                      ? 'flex w-full items-center gap-1.5 rounded-lg bg-brand-50 px-2.5 py-1.5 text-left text-sm font-medium text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
                      : 'flex w-full items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-left text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700/50'
                  }
                >
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 opacity-60" />
                  <span className="min-w-0 flex-1 truncate">
                    {isTR ? section.title_tr : section.title_en}
                  </span>
                </button>
              ))}
              {sections.length === 0 && (
                <p className="px-2 py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                  {t('common.noResults')}
                </p>
              )}
            </nav>
          </Card>
        </aside>

        {/* İçerik */}
        <div className="space-y-4">
          {sections.length === 0 ? (
            <Card>
              <EmptyState
                title={t('common.noResults')}
                description={t('help.subtitle')}
                icon={<BookOpen className="h-6 w-6" />}
                action={
                  <button type="button" className="btn-secondary btn-sm" onClick={() => setQuery('')}>
                    {t('common.clearFilters')}
                  </button>
                }
              />
            </Card>
          ) : (
            sections.map((section) => (
              <section key={section.id} id={`help-${section.id}`} className="scroll-mt-4">
                <Card title={isTR ? section.title_tr : section.title_en}>
                  <div className="space-y-3">
                    {(isTR ? section.body_tr : section.body_en).map((paragraph, index) => (
                      <p
                        key={index}
                        className="text-sm leading-relaxed text-slate-600 dark:text-slate-300"
                      >
                        {paragraph}
                      </p>
                    ))}
                  </div>

                  <ol className="mt-4 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
                    {(isTR ? section.steps_tr : section.steps_en).map((step, index) => (
                      <li key={index} className="flex gap-2.5 text-sm text-slate-700 dark:text-slate-200">
                        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700 dark:bg-brand-900/50 dark:text-brand-300">
                          {index + 1}
                        </span>
                        <span className="min-w-0 flex-1">{step}</span>
                      </li>
                    ))}
                  </ol>

                  <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3 dark:border-slate-700">
                    <Link
                      to="/training"
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300"
                    >
                      <GraduationCap className="h-4 w-4" />
                      {t('help.relatedTutorial')}
                    </Link>
                    <Link
                      to={section.route}
                      className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                    >
                      <ChevronRight className="h-4 w-4" />
                      {t('training.goToScreen')}
                    </Link>
                  </div>
                </Card>
              </section>
            ))
          )}
        </div>
      </div>
    </>
  )
}
