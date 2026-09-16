from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ---------------------------------------------------------------------------
# کاربران سامانه
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    # نقش: admin (دسترسی کامل به همه شهرستان‌ها) یا user (فقط شهرستان خودش)
    role = db.Column(db.String(20), nullable=False, default="user")
    # فیلد کلیدی محدودیت دسترسی: هر کاربر به داده‌های شهرستان خودش محدود است
    city = db.Column(db.String(100), nullable=True)  # NULL فقط برای admin معنا دارد
    is_active_flag = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):
        return self.is_active_flag


# ---------------------------------------------------------------------------
# ابزار مشترک: mixin برای ثبت متادیتای رکورد
# ---------------------------------------------------------------------------
class AuditMixin:
    city = db.Column(db.String(100), nullable=False, index=True)
    staff_count = db.Column(db.Integer)  # تعداد پرسنل
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# جدول ۱: بازبینه سنجه کاهش مصرف آب دستگاه‌های اجرایی
# ---------------------------------------------------------------------------
class WaterRecord(db.Model, AuditMixin):
    __tablename__ = "water_records"

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.String(100))              # شناسه قبض
    subscription_number = db.Column(db.String(100))     # شماره اشتراک
    consumption_amount = db.Column(db.String(100))      # میزان مصرف
    period = db.Column(db.String(100))                  # دوره
    amount = db.Column(db.String(100))                  # مبلغ
    device_title = db.Column(db.String(255))            # عنوان دستگاه
    device_address = db.Column(db.String(500))          # آدرس دستگاه
    usage_type = db.Column(db.String(255))               # کاربری مورد استفاده

    created_by = db.relationship("User")


# ---------------------------------------------------------------------------
# جدول ۲: بازبینه سنجه کاهش مصرف برق دستگاه‌های اجرایی استان
# ---------------------------------------------------------------------------
class ElectricityRecord(db.Model, AuditMixin):
    __tablename__ = "electricity_records"

    id = db.Column(db.Integer, primary_key=True)
    building_receipt_id = db.Column(db.String(100))     # شناسه قبض ساختمان اداری
    usage_type = db.Column(db.String(255))               # نوع کاربری ساختمان
    kwh_1403 = db.Column(db.Float)                       # مجموع مصرف ۱۴۰۳ (kWh)
    kwh_1404 = db.Column(db.Float)                       # مجموع مصرف ۱۴۰۴ (kWh)
    representative_name = db.Column(db.String(150))      # نام نماینده
    representative_phone = db.Column(db.String(20))      # شماره همراه
    description = db.Column(db.Text)                     # توضیحات

    created_by = db.relationship("User")

    @property
    def reduction_percent(self):
        if self.kwh_1403 and self.kwh_1403 != 0 and self.kwh_1404 is not None:
            return round((self.kwh_1403 - self.kwh_1404) / self.kwh_1403 * 100, 2)
        return None


# ---------------------------------------------------------------------------
# جدول ۳: بازبینه سنجه کاهش مصرف گاز دستگاه‌های اجرایی استان
# ---------------------------------------------------------------------------
class GasRecord(db.Model, AuditMixin):
    __tablename__ = "gas_records"

    id = db.Column(db.Integer, primary_key=True)
    gas_receipt_id = db.Column(db.String(100))            # شناسه قبض گاز
    device_name = db.Column(db.String(255))              # نام دستگاه
    building_name = db.Column(db.String(255))            # نام اداره / ساختمان
    city_village = db.Column(db.String(150))             # شهر / روستا
    address = db.Column(db.String(500))                  # آدرس
    subscription_number = db.Column(db.String(20))       # شماره اشتراک (۱۰ رقمی)
    x_decimal = db.Column(db.Float)                       # طول جغرافیایی
    y_decimal = db.Column(db.Float)                       # عرض جغرافیایی
    start_date = db.Column(db.String(20))                 # تاریخ شروع استفاده از اشتراک

    created_by = db.relationship("User")


# ---------------------------------------------------------------------------
# جدول ۴: بازبینه سنجه تولید برق از انرژی پاک دستگاه‌های اجرایی استان
# ---------------------------------------------------------------------------
class CleanEnergyRecord(db.Model, AuditMixin):
    __tablename__ = "clean_energy_records"

    id = db.Column(db.Integer, primary_key=True)
    org_name = db.Column(db.String(255))                  # نام سازمان / اداره
    annual_consumption_kwh = db.Column(db.Float)           # انرژی مصرفی سالانه انشعاب
    built_capacity_kw = db.Column(db.Float)                 # ظرفیت نیروگاه احداث شده
    mandated_capacity_kw = db.Column(db.Float)              # ظرفیت تکلیفی ۱۰٪ سال ۱۴۰۴
    annual_production_kwh = db.Column(db.Float)             # انرژی تولیدی سالانه نیروگاه

    created_by = db.relationship("User")
    buildings = db.relationship(
        "CleanEnergyBuilding", backref="record", cascade="all, delete-orphan"
    )

    @property
    def renewable_percent(self):
        if self.annual_consumption_kwh and self.annual_production_kwh is not None:
            return round(self.annual_production_kwh / self.annual_consumption_kwh * 100, 2)
        return None


class CleanEnergyBuilding(db.Model):
    """شناسه قبض انشعاب ساختمان‌های تابعه (تا ۱۰ انشعاب برای هر سازمان)"""
    __tablename__ = "clean_energy_buildings"

    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey("clean_energy_records.id"))
    slot_number = db.Column(db.Integer)      # شماره انشعاب ۱ تا ۱۰
    receipt_id = db.Column(db.String(100))   # شناسه قبض انشعاب