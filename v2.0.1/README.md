# سامانه نرمال‌شده نظارت بر مصرف انرژی

نسخه تکمیل‌شده پروژه Flask با حفظ رنگ‌ها، تایپوگرافی، navbar، کارت‌ها و ساختار برندینگ قبلی. اطلاعات پایه ساختمان اکنون مرجع واحد آب، برق، گاز، تولید برق و مخابرات است.

## قابلیت‌های پیاده‌سازی‌شده

- اطلاعات پایه ساختمان‌ها با افزودن، ویرایش، حذف، جستجو، Sort، Import از CSV/XLSX و Export به XLSX
- مدل نرمال‌شده شهر، نوع کاربری، اشتراک‌ها، ژنراتور، مخابرات، اینترنت/MPLS/Intranet، دکل و ارت
- قبوض دوره‌ای و سالیانه آب، برق و گاز با بازه قرائت، مصرف، مبلغ و واحد مناسب
- جمع سالیانه خودکار: اگر دوره‌ای موجود باشد مجموع دوره‌ها و در غیر این صورت رکورد سالیانه مبنا است
- سرانه آب، برق و گاز = مصرف ÷ تعداد افراد ساختمان؛ مقدار مشتق‌شده ذخیره نمی‌شود
- پشتیبانی یک‌به‌چند از چند اشتراک برق، آب و گاز برای هر ساختمان، با اتصال هر قبض به اشتراک دقیق
- فرم قبض با بارگذاری شماره/شناسه قبض و تاریخ نصب و به‌کارگیری اشتراک انتخاب‌شده
- انتخاب هوشمند ساختمان موجود در فرم اطلاعات پایه و تکمیل خودکار آدرس و سایر مشخصات
- تقویم شمسی داخلی با Datepicker و ورود دستی `۱۴۰۵/۰۶/۰۶` در تمام فرم‌ها و خروجی‌ها
- ثبت مقاومت سیستم ارت به‌صورت عددی و بر حسب اهم
- نمایش مبالغ به ریال، بدون اعشار و با جداکننده سه‌رقمی فارسی مانند `۱٬۲۳۴٬۵۶۷ ریال`
- جمع مصرف سالیانه بدون اعشار در نمایش، نمودار و Excel
- ثبت نوع و ظرفیت ژنراتور در هر رکورد تولید و گزارش مجزا برای دیزل، گازسوز، هایبرید، خورشیدی، بادی و سایر
- ثبت مستقل نوع مخابرات E1، آنالوگ، SIP Trunk و SIP روی هر رکورد مخابراتی
- نمودار مقایسه‌ای سرانه شهرها برای دوره‌ای/سالیانه و به تفکیک برق، آب و گاز، همراه میانگین سایر شهرها
- مخفی‌سازی مخابرات برای کاربران غیرادمین با Feature Flag و مجوز اختصاصی کاربر
- کنترل دسترسی هشت ماژول/فرم برای هر کاربر از پنل admin
- نمایش تعداد تلاش‌های باقی‌مانده در صفحه ورود
- پنج خروجی Excel مجزا برای برق، آب، گاز، تولید برق و مخابرات؛ قبوض دارای Sheet جزئیات و خلاصه سالیانه
- گزارش‌ساز پویا با انتخاب منبع داده، فیلدها، شهر، ساختمان، سال، بازه شمسی، نوع انشعاب/سرویس و Sort
- Sort سمت سرور، صفحه‌بندی ۵۰تایی و ایندکس‌های ترکیبی
- پنل کاربر با Import/Export Excel، Backup/Restore JSON، بازه `active_from/active_until`
- نمایش شمارش معکوس نشست در کنار نام کاربر و پایان فوری نشست در زمان انقضای حساب
- قفل ورود بعد از ۵ تلاش ناموفق در پنجره ۱۵ دقیقه‌ای، به‌مدت ۱۵ دقیقه
- CSRF، scrypt password hashing، Jinja escaping، CSP و هدرهای امنیتی، کوکی امن و اعتبارسنجی سمت سرور/مرورگر
- قالب Bootstrap RTL واکنش‌گرا برای موبایل، تبلت و دسکتاپ

جزئیات رابطه جدول‌ها در [`docs/architecture.md`](docs/architecture.md) و نکات استقرار در [`SECURITY.md`](SECURITY.md) آمده است.

## ارتقای دیتابیس تحویلی

فایل `instance/app.db` موجود در این بسته قبلاً با `migrate.py` ارتقا یافته و چهار رکورد قبلی بدون حذف داده به ساختار جدید منتقل شده‌اند. چون دیتابیس قدیمی برای «مشهد» کد شهر نداشت، مهاجرت یک کد موقت مانند `LEG-001` ساخته است؛ ادمین باید آن را از منوی «شهرها» با کد سازمانی صحیح جایگزین کند. نسخه پشتیبان قبل از تبدیل نیز با نام زیر نگهداری شده است:

```text
instance/app-before-normalization-20260828-123724.db
```

برای اعمال ارتقا روی کپی دیگری از دیتابیس قدیمی:

```powershell
# ابتدا app.db قدیمی را در instance قرار دهید
python migrate.py
```

اسکریپت idempotent است، قبل از تغییر یک Backup زمان‌دار می‌گیرد، رکوردها را منتقل می‌کند و فقط پس از Commit موفق جدول‌های قدیمی را حذف می‌کند. ارتقای فعلی با markerهای `module_subscriptions_v4` و `production_snapshot_v5` محدودیت تک‌اشتراکی را بدون حذف رکوردها برمی‌دارد، قبض‌های قبلی را به اشتراک متناظر متصل می‌کند، جدول مجوزها را می‌سازد و نوع/ظرفیت تاریخی تولید را مقداردهی می‌کند. برای تغییرات بعدی مدل‌ها، Flask-Migrate نیز فعال است:

```bash
flask --app app db init       # فقط بار اول در مخزن توسعه
flask --app app db migrate -m "description"
flask --app app db upgrade
```

## اجرای محلی در Windows / PowerShell

Python پایدار 3.11 تا 3.13 پیشنهاد می‌شود. استفاده از نسخه Beta پایتون برای محیط عملیاتی توصیه نمی‌شود.

```powershell
cd D:\Projects\energy-monitoring-webapp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# برای این دیتابیس قبلاً migration اجرا شده است؛ اجرای دوباره مشکلی ندارد
python migrate.py
python app.py
```

سپس `http://127.0.0.1:5700` را باز کنید. پورت اجرای محلی از متغیر محیطی `PORT` قابل تغییر است.

### ورود دیتابیس تحویلی

```text
username: admin
password: admin123
```

این رمز مربوط به دیتابیس اولیه کاربر است؛ **بلافاصله آن را از پنل مدیریت کاربران تغییر دهید**. در نصب کاملاً تازه، رمز مدیر از `INITIAL_ADMIN_PASSWORD` گرفته می‌شود و اگر تنظیم نشده باشد یک رمز تصادفی در Console چاپ می‌شود.

## تنظیمات محیطی

نمونه در `.env.example` است. برنامه فایل `.env` را خودکار نمی‌خواند؛ متغیرها را در سیستم، Docker Compose یا سرویس اجرا تعریف کنید.

```powershell
$env:SECRET_KEY = "یک-رشته-تصادفی-حداقل-۶۴-کاراکتری"
$env:SESSION_MINUTES = "120"
$env:TELECOM_USER_VISIBLE = "0" # مخابرات فقط برای admin؛ برای فعال‌سازی کاربران 1 شود
$env:COOKIE_SECURE = "0"       # فقط اجرای local بدون HTTPS
python app.py
```

در production، `APP_ENV=production` بدون `SECRET_KEY` باعث توقف برنامه می‌شود. پشت HTTPS حتماً `COOKIE_SECURE=1` باشد.

### سوییچ مخابرات و دسترسی ماژولی

مقدار پیش‌فرض `TELECOM_USER_VISIBLE=0` است؛ در این حالت تمام فرم‌ها، فیلدهای API و گزارش‌های مخابرات برای کاربران غیرادمین مخفی و مسیرهای مستقیم نیز با HTTP 403 محافظت می‌شوند. ادمین همچنان به مخابرات دسترسی دارد. برای فعال‌سازی مرحله‌ای، مقدار را `1` کنید؛ سپس مجوز «فرم‌ها و گزارش مخابرات» هر کاربر در پنل مدیریت کاربران تعیین‌کننده خواهد بود. سایر مجوزهای ساختمان، برق، آب، گاز، تولید، گزارش ثابت و گزارش پویا نیز از همان فرم مدیریت می‌شوند.

## Production و ۵۰ کاربر همزمان

SQLite فقط برای توسعه و نصب کوچک نگه داشته شده است. وابستگی‌های PostgreSQL/Gunicorn عمداً در `requirements-production.txt` جدا شده‌اند تا نصب محلی Windows به wheel مربوط به `psycopg-binary` وابسته نباشد. برای سرور Linux ابتدا اجرا کنید:

```bash
pip install -r requirements-production.txt
```

برای ۵۰ کاربر همزمان، PostgreSQL و Gunicorn الزامی/توصیه‌شده‌اند:

```bash
export APP_ENV=production
export SECRET_KEY='long-random-secret'
export DATABASE_URL='postgresql+psycopg://energy:password@127.0.0.1:5432/energy'
export COOKIE_SECURE=1
export TRUST_PROXY=1   # فقط وقتی دقیقاً یک reverse proxy کنترل‌شده در جلو قرار دارد
# در نصب تازه، ایجاد schema را یک‌بار و قبل از workerها انجام دهید؛
# برای نسخه‌های بعدی ابتدا flask db upgrade اجرا شود:
AUTO_CREATE_SCHEMA=1 python -c 'from app import app'
AUTO_CREATE_SCHEMA=0 gunicorn -c gunicorn.conf.py app:app
```

پیکربندی پیش‌فرض Gunicorn حداقل ۲ worker با ۲۵ thread (ظرفیت ۵۰ درخواست همزمان) دارد و از متغیرهای `WEB_CONCURRENCY` و `GUNICORN_THREADS` قابل تنظیم است. در جلوی آن Nginx/Caddy و TLS قرار دهید.

### Docker Compose با PostgreSQL

یک فایل `.env` کنار `docker-compose.yml` بسازید:

```env
POSTGRES_PASSWORD=replace-this-db-password
SECRET_KEY=replace-with-long-random-value
INITIAL_ADMIN_PASSWORD=replace-with-one-time-admin-password
SESSION_MINUTES=120
TELECOM_USER_VISIBLE=0
COOKIE_SECURE=0
```

سپس:

```bash
docker compose up -d --build
```

پس از افزودن reverse proxy و HTTPS، `COOKIE_SECURE=1` را تنظیم کنید.

## تست‌ها

```bash
pip install pytest==8.3.3
pytest -q
```

نتیجه اجرای تحویلی:

```text
16 passed
```

تست همزمانی استاندارد کتابخانه پایتون:

```bash
# ابتدا Gunicorn را اجرا کنید
python tests/load_test.py --url http://127.0.0.1:8000 \
  --username admin --password "رمز-فعلی" --users 50 --requests 5
```

نتیجه اجرای این نسخه در محیط بررسی (۵۰ نشست همزمان و ۲۵۰ درخواست احراز‌شده):

```text
users=50, requests=250, errors=0, average=0.172s, p95=0.559s, max=0.749s
```

این عدد تضمین ظرفیت سخت‌افزار مقصد نیست؛ تست را روی سرور نهایی با PostgreSQL، TLS و حجم داده واقعی نیز اجرا کنید.

## Import / Export

### ساختمان‌ها

ادمین از مسیر «ساختمان‌ها ← Import» قالب استاندارد را دانلود می‌کند. فایل XLSX/XLSM شامل Sheet «ساختمان‌ها» و Sheet «اشتراک‌ها» است؛ هر اشتراک برق/آب/گاز یک ردیف مستقل دارد و بنابراین چنداشتراکی بدون ادغام یا از دست رفتن اطلاعات Import/Export می‌شود. CSV UTF-8 برای قالب تخت سازگار قبلی همچنان پشتیبانی می‌شود. کلید تشخیص ساختمان، ترکیب `شهر + نام ساختمان` است و حالت رد یا به‌روزرسانی قابل انتخاب است.

### کاربران

- Export Excel فاقد رمز و مناسب گزارش اداری است.
- Import Excel رمز اولیه را دریافت و فوراً با scrypt هش می‌کند.
- Backup JSON شامل **هش** رمز (نه متن رمز) است و برای Restore استفاده می‌شود؛ این فایل همچنان حساس است.
- ستون‌های Excel مربوط به `active_from` و `active_until` شمسی و به‌شکل `۱۴۰۵/۰۶/۰۶ ۱۴:۳۰` هستند. تاریخ ISO فقط داخل Backup ماشینی JSON نگهداری می‌شود.

## تاریخ‌ها و سال گزارش

تمام تاریخ‌های قابل مشاهده و قابل ورود در فرم، Import، Export و گزارش‌ها شمسی هستند. کاربر می‌تواند از Datepicker استفاده کند یا تاریخ را به‌شکل `۱۴۰۵/۰۶/۰۶` تایپ کند. سرور تاریخ شمسی را اعتبارسنجی و برای حفظ Sort، Index و سازگاری PostgreSQL به `DATE/DATETIME` استاندارد تبدیل می‌کند؛ بنابراین تاریخ میلادی در رابط کاربری نمایش داده نمی‌شود. زمان‌های شروع/انقضای کاربر با منطقه زمانی `Asia/Tehran` تفسیر می‌شوند. «سال گزارش» نیز سال شمسی مانند `1405` است.

## فایل‌های اصلی

```text
app.py                         routes, security, validation, imports/exports
models.py                      normalized SQLAlchemy models and indexes
migrate.py                     legacy SQLite migration with backup
jalali.py                      Jalali/Gregorian validation and conversion
extensions.py                  SQLAlchemy/Login/CSRF/Migrate extensions
static/app.js, static/app.css   local Jalali datepicker and number formatting
gunicorn.conf.py               threaded production server configuration
Dockerfile / docker-compose.yml PostgreSQL production-like deployment
templates/                     responsive RTL templates preserving branding
tests/test_app.py              security and business-rule tests
tests/load_test.py             50-concurrent-user load smoke test
instance/app.db                upgraded supplied data
```
