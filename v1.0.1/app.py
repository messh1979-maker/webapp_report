# -*- coding: utf-8 -*-
"""
سامانه بازبینه سنجه‌های کاهش مصرف انرژی شرکت آب و فاضلاب خراسان رضوی
------------------------------------------------------------------
یک اپلیکیشن وب چندکاربره با کنترل دسترسی بر اساس فیلد «شهرستان».
هر کاربر عادی فقط داده‌های شهرستان خودش را می‌بیند و ثبت می‌کند؛
کاربر ادمین به همه شهرستان‌ها دسترسی کامل دارد.
"""
import io
import json
import os
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, request,
    flash, abort, send_file, jsonify
)
from sqlalchemy import func
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from werkzeug.middleware.proxy_fix import ProxyFix
from openpyxl import Workbook

from extensions import db, login_manager
from models import (
    User, WaterRecord, ElectricityRecord, GasRecord,
    CleanEnergyRecord, CleanEnergyBuilding
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# تعریف جدول‌ها به صورت متادیتای واحد -> کد فرم‌ها/لیست‌ها را یکسان‌سازی می‌کند
# ---------------------------------------------------------------------------
TABLES = {
    "water": {
        "model": WaterRecord,
        "title": "کاهش مصرف آب",
        "fields": [
            ("receipt_id", "شناسه قبض", "text"),
            ("subscription_number", "شماره اشتراک", "text"),
            ("device_title", "عنوان دستگاه", "text"),
            ("device_address", "آدرس دستگاه", "text"),
            ("usage_type", "کاربری مورد استفاده", "text"),
            ("period", "دوره", "text"),
            ("consumption_amount", "میزان مصرف", "text"),
            ("amount", "مبلغ", "text"),
            ("staff_count", "تعداد پرسنل", "number"),
        ],
    },
    "electricity": {
        "model": ElectricityRecord,
        "title": "کاهش مصرف برق",
        "fields": [
            ("building_receipt_id", "شناسه قبض ساختمان اداری", "text"),
            ("usage_type", "نوع کاربری ساختمان", "text"),
            # فیلد ورودی کاربر: مقدار وارد شده همیشه در ستون ۱۴۰۴ ذخیره می‌شود.
            ("kwh_1404", "مجموع مصرف ۱۴۰۴ (kWh)", "number"),
            # ستون ۱۴۰۳ دیگر از کاربر گرفته نمی‌شود و همیشه صفر ثبت می‌شود
            # (نوع فیلد auto_zero: در فرم رندر نمی‌شود و مقدار آن هنگام ثبت/ویرایش برابر با ۰ است).
            ("kwh_1403", "مجموع مصرف ۱۴۰۳ (kWh)", "auto_zero"),
            ("representative_name", "نام نماینده", "text"),
            ("representative_phone", "شماره همراه", "text"),
            ("description", "توضیحات", "textarea"),
            ("staff_count", "تعداد پرسنل", "number"),
        ],
    },
    "gas": {
        "model": GasRecord,
        "title": "کاهش مصرف گاز",
        "fields": [
            ("gas_receipt_id", "شناسه قبض گاز", "text"),
            ("device_name", "نام دستگاه", "text"),
            ("building_name", "نام اداره / ساختمان", "text"),
            ("city_village", "شهر / روستا", "text"),
            ("address", "آدرس", "text"),
            ("subscription_number", "شماره اشتراک (۱۰ رقمی)", "text"),
            ("x_decimal", "X (طول جغرافیایی)", "number"),
            ("y_decimal", "Y (عرض جغرافیایی)", "number"),
            ("start_date", "تاریخ شروع استفاده از اشتراک", "text"),
            ("staff_count", "تعداد پرسنل", "number"),
        ],
    },
    "clean_energy": {
        "model": CleanEnergyRecord,
        "title": "تولید انرژی پاک",
        "fields": [
            ("org_name", "نام سازمان / اداره", "text"),
            ("annual_consumption_kwh", "انرژی مصرفی سالانه انشعاب (kWh)", "number"),
            ("built_capacity_kw", "ظرفیت نیروگاه احداث شده (kW)", "number"),
            ("mandated_capacity_kw", "ظرفیت تکلیفی ۱۰٪ سال ۱۴۰۴ (kW)", "number"),
            ("annual_production_kwh", "انرژی تولیدی سالانه نیروگاه (kWh)", "number"),
            ("staff_count", "تعداد پرسنل", "number"),
        ],
    },
}


def create_app():
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "your secret key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["TABLES"] = TABLES

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    register_routes(app)

    @app.context_processor
    def inject_globals():
        return {"tables_menu": TABLES}

    with app.app_context():
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    """اگر هیچ کاربری وجود نداشت، یک ادمین پیش‌فرض بساز."""
    if User.query.count() == 0:
        admin = User(
            username="admin",
            full_name="مدیر سامانه",
            role="admin",
            city=None,
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        print("=" * 60)
        print("کاربر ادمین پیش‌فرض ساخته شد -> username: admin / password: admin123")
        print("لطفاً بلافاصله پس از اولین ورود رمز عبور را تغییر دهید.")
        print("=" * 60)


# ---------------------------------------------------------------------------
# دکوراتورهای کنترل دسترسی
# ---------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def visible_query(model):
    """محدود کردن کوئری بر اساس شهرستان کاربر (ستون دسترسی کلیدی سامانه)."""
    q = model.query
    if not current_user.is_admin:
        q = q.filter_by(city=current_user.city)
    return q


def enforce_city_or_403(target_city):
    """کاربر عادی فقط اجازه دارد روی شهرستان خودش کار کند."""
    if not current_user.is_admin and target_city != current_user.city:
        abort(403)


# ---------------------------------------------------------------------------
# روت‌ها
# ---------------------------------------------------------------------------
def register_routes(app):

    # ---------------------- احراز هویت ----------------------
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password) and user.is_active:
                login_user(user)
                flash(f"خوش آمدید، {user.full_name}", "success")
                return redirect(url_for("dashboard"))
            flash("نام کاربری یا رمز عبور نادرست است.", "danger")
        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("با موفقیت خارج شدید.", "info")
        return redirect(url_for("login"))

    # ---------------------- داشبورد ----------------------
    @app.route("/")
    @login_required
    def dashboard():
        counts = {}
        for key, meta in TABLES.items():
            counts[key] = visible_query(meta["model"]).count()
        return render_template("dashboard.html", counts=counts, tables=TABLES)

    # ---------------------- لیست عمومی رکوردهای هر جدول ----------------------
    @app.route("/table/<table_key>")
    @login_required
    def table_list(table_key):
        meta = TABLES.get(table_key)
        if not meta:
            abort(404)
        records = visible_query(meta["model"]).order_by(meta["model"].id.desc()).all()
        return render_template(
            "table_list.html", table_key=table_key, meta=meta, records=records
        )

    # ---------------------- فرم جدید / ویرایش ----------------------
    @app.route("/table/<table_key>/new", methods=["GET", "POST"])
    @login_required
    def table_new(table_key):
        meta = TABLES.get(table_key)
        if not meta:
            abort(404)
        model = meta["model"]

        if request.method == "POST":
            city = request.form.get("city", "").strip() if current_user.is_admin else current_user.city
            enforce_city_or_403(city)

            record = model(city=city, created_by_id=current_user.id)
            _apply_form_to_record(record, meta["fields"])
            db.session.add(record)
            db.session.flush()  # to get record.id for clean_energy sub-buildings

            if table_key == "clean_energy":
                _save_clean_energy_buildings(record)

            db.session.commit()
            flash("رکورد با موفقیت ثبت شد.", "success")
            return redirect(url_for("table_list", table_key=table_key))

        return render_template(
            "table_form.html", table_key=table_key, meta=meta, record=None
        )

    @app.route("/table/<table_key>/<int:record_id>/edit", methods=["GET", "POST"])
    @login_required
    def table_edit(table_key, record_id):
        meta = TABLES.get(table_key)
        if not meta:
            abort(404)
        model = meta["model"]
        record = db.session.get(model, record_id)
        if not record:
            abort(404)
        enforce_city_or_403(record.city)

        if request.method == "POST":
            city = request.form.get("city", "").strip() if current_user.is_admin else current_user.city
            enforce_city_or_403(city)
            record.city = city
            _apply_form_to_record(record, meta["fields"])

            if table_key == "clean_energy":
                CleanEnergyBuilding.query.filter_by(record_id=record.id).delete()
                _save_clean_energy_buildings(record)

            db.session.commit()
            flash("تغییرات ذخیره شد.", "success")
            return redirect(url_for("table_list", table_key=table_key))

        return render_template(
            "table_form.html", table_key=table_key, meta=meta, record=record
        )

    @app.route("/table/<table_key>/<int:record_id>/delete", methods=["POST"])
    @login_required
    def table_delete(table_key, record_id):
        meta = TABLES.get(table_key)
        if not meta:
            abort(404)
        record = db.session.get(meta["model"], record_id)
        if not record:
            abort(404)
        enforce_city_or_403(record.city)
        db.session.delete(record)
        db.session.commit()
        flash("رکورد حذف شد.", "info")
        return redirect(url_for("table_list", table_key=table_key))

    # ---------------------- خروجی اکسل ----------------------
    @app.route("/table/<table_key>/export")
    @login_required
    def table_export(table_key):
        meta = TABLES.get(table_key)
        if not meta:
            abort(404)
        records = visible_query(meta["model"]).order_by(meta["model"].id.desc()).all()

        wb = Workbook()
        ws = wb.active
        ws.sheet_view.rightToLeft = True
        ws.title = meta["title"][:31]

        headers = ["شهرستان"] + [label for (_, label, _) in meta["fields"]]
        ws.append(headers)
        for r in records:
            row = [r.city] + [getattr(r, fname) for (fname, _, _) in meta["fields"]]
            ws.append(row)

        stream = io.BytesIO()
        wb.save(stream)
        stream.seek(0)
        filename = f"{meta['title']}.xlsx"
        return send_file(
            stream, as_attachment=True, download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ---------------------- گزارش‌گیری نموداری ----------------------
    @app.route("/reports")
    @login_required
    def reports():
        return render_template("reports.html", tables=TABLES)

    @app.route("/api/reports/data")
    @login_required
    def reports_data():
        city_filter = None if current_user.is_admin else current_user.city

        def _count_by_city(model):
            q = db.session.query(model.city, func.count(model.id)).group_by(model.city)
            if city_filter:
                q = q.filter(model.city == city_filter)
            return {row[0]: row[1] for row in q.all()}

        def _sum_by_city(model, column):
            q = db.session.query(
                model.city, func.sum(column), func.count(model.id)
            ).group_by(model.city)
            if city_filter:
                q = q.filter(model.city == city_filter)
            result = {}
            for city, total, cnt in q.all():
                result[city] = {"total": float(total or 0), "count": cnt}
            return result

        counts_by_city = {}
        for key, meta in TABLES.items():
            counts_by_city[key] = _count_by_city(meta["model"])

        cities = sorted(set(
            c for data in counts_by_city.values() for c in data.keys()
        ))

        electricity_data = _sum_by_city(
            ElectricityRecord,
            ElectricityRecord.kwh_1404 - ElectricityRecord.kwh_1403
        )
        clean_energy_data = _sum_by_city(
            CleanEnergyRecord,
            CleanEnergyRecord.annual_production_kwh
        )

        totals = {key: sum(data.values()) for key, data in counts_by_city.items()}

        return jsonify({
            "cities": cities,
            "counts_by_city": counts_by_city,
            "totals": totals,
            "electricity_reduction": electricity_data,
            "clean_energy_production": clean_energy_data,
        })

    # ---------------------- مدیریت کاربران (فقط ادمین) ----------------------
    @app.route("/admin/users")
    @login_required
    @admin_required
    def admin_users():
        users = User.query.order_by(User.id).all()
        return render_template("admin_users.html", users=users)

    @app.route("/admin/users/new", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_user_new():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            if User.query.filter_by(username=username).first():
                flash("این نام کاربری قبلاً استفاده شده است.", "danger")
                return redirect(url_for("admin_user_new"))
            user = User(
                username=username,
                full_name=request.form.get("full_name", "").strip(),
                phone=request.form.get("phone", "").strip(),
                role=request.form.get("role", "user"),
                city=request.form.get("city", "").strip() or None,
            )
            user.set_password(request.form.get("password") or "changeme123")
            db.session.add(user)
            db.session.commit()
            flash("کاربر جدید ایجاد شد.", "success")
            return redirect(url_for("admin_users"))
        return render_template("admin_user_form.html", user=None)

    @app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
    @login_required
    @admin_required
    def admin_user_edit(user_id):
        user = db.session.get(User, user_id)
        if not user:
            abort(404)
        if request.method == "POST":
            user.full_name = request.form.get("full_name", "").strip()
            user.phone = request.form.get("phone", "").strip()
            user.role = request.form.get("role", "user")
            user.city = request.form.get("city", "").strip() or None
            user.is_active_flag = bool(request.form.get("is_active"))
            new_password = request.form.get("password")
            if new_password:
                user.set_password(new_password)
            db.session.commit()
            flash("اطلاعات کاربر به‌روزرسانی شد.", "success")
            return redirect(url_for("admin_users"))
        return render_template("admin_user_form.html", user=user)

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @login_required
    @admin_required
    def admin_user_delete(user_id):
        if user_id == current_user.id:
            flash("نمی‌توانید حساب کاربری خودتان را حذف کنید.", "danger")
            return redirect(url_for("admin_users"))
        user = db.session.get(User, user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            flash("کاربر حذف شد.", "info")
        return redirect(url_for("admin_users"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="شما اجازه دسترسی به این بخش را ندارید."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="صفحه مورد نظر یافت نشد."), 404


def _apply_form_to_record(record, fields):
    for fname, _label, ftype in fields:
        if ftype == "auto_zero":
            # این فیلد از کاربر گرفته نمی‌شود؛ همیشه صفر ثبت می‌شود
            # (مثلاً ستون مصرف ۱۴۰۳ برق که دیگر داده‌ورودی کاربر نیست).
            setattr(record, fname, 0)
            continue
        raw = request.form.get(fname, "").strip()
        if ftype == "number":
            value = float(raw) if raw not in ("", None) else None
        else:
            value = raw or None
        setattr(record, fname, value)


def _save_clean_energy_buildings(record):
    for i in range(1, 11):
        receipt = request.form.get(f"building_receipt_{i}", "").strip()
        if receipt:
            db.session.add(
                CleanEnergyBuilding(record_id=record.id, slot_number=i, receipt_id=receipt)
            )


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)