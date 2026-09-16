"""Idempotent upgrade from the supplied legacy SQLite schema.

Usage: python migrate.py
A timestamped database backup is created before any destructive operation.
For PostgreSQL deployments use Flask-Migrate/Alembic (`flask db upgrade`).
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "instance" / "app.db"
LEGACY_TABLES = (
    "water_records",
    "electricity_records",
    "gas_records",
    "clean_energy_buildings",
    "clean_energy_records",
)


def table_exists(connection, name):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def rows(connection, table):
    if not table_exists(connection, table):
        return []
    connection.row_factory = sqlite3.Row
    return [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]


def rebuild_users_if_needed(con):
    """Rebuild legacy SQLite users table so city_id has a real FK and indexes."""
    if not table_exists(con, "users"):
        return False
    columns = {row[1] for row in con.execute("PRAGMA table_info(users)")}
    required = {"city_id", "active_from", "active_until", "updated_at", "last_login_at"}
    # Presence of old denormalized `city` means this table still needs rebuilding.
    if required.issubset(columns) and "city" not in columns:
        return False

    def expression(name, fallback="NULL"):
        return name if name in columns else fallback

    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("DROP TABLE IF EXISTS users_rebuilt")
    con.execute("""
        CREATE TABLE users_rebuilt (
            id INTEGER NOT NULL PRIMARY KEY,
            username VARCHAR(80) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(150) NOT NULL,
            phone VARCHAR(20),
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            city_id INTEGER REFERENCES cities(id) ON DELETE RESTRICT,
            is_active_flag BOOLEAN NOT NULL DEFAULT 1,
            active_from DATETIME,
            active_until DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            last_login_at DATETIME,
            CONSTRAINT ck_users_role CHECK (role IN ('admin','admin_view','user','view'))
        )
    """)
    con.execute(f"""
        INSERT INTO users_rebuilt
            (id, username, password_hash, full_name, phone, role, city_id,
             is_active_flag, active_from, active_until, created_at, updated_at, last_login_at)
        SELECT id, username, password_hash, full_name, phone, role,
               {expression('city_id')}, {expression('is_active_flag', '1')},
               {expression('active_from')}, {expression('active_until')},
               COALESCE({expression('created_at', 'CURRENT_TIMESTAMP')}, CURRENT_TIMESTAMP),
               COALESCE({expression('updated_at', expression('created_at', 'CURRENT_TIMESTAMP'))}, CURRENT_TIMESTAMP),
               {expression('last_login_at')}
        FROM users
    """)
    con.execute("DROP TABLE users")
    con.execute("ALTER TABLE users_rebuilt RENAME TO users")
    con.execute("CREATE INDEX IF NOT EXISTS ix_users_city_id ON users(city_id)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_users_active_until ON users(active_until)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_users_is_active_flag ON users(is_active_flag)")
    con.commit()
    con.execute("PRAGMA foreign_keys=ON")
    return True


def apply_incremental_v3(con):
    """Add fields introduced after normalized_v2 without losing existing data."""
    changed = False
    if table_exists(con, "earth_systems"):
        columns = {row[1] for row in con.execute("PRAGMA table_info(earth_systems)")}
        if "resistance_ohm" not in columns:
            con.execute("ALTER TABLE earth_systems ADD COLUMN resistance_ohm NUMERIC(12,3)")
            changed = True
    if table_exists(con, "schema_markers"):
        con.execute(
            "INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('jalali_reporting_v3', CURRENT_TIMESTAMP)"
        )
    con.commit()
    return changed


def apply_incremental_v4(con):
    """Enable multiple utility subscriptions, module ACLs and per-record telecom types."""
    changed = False
    con.execute("PRAGMA foreign_keys=OFF")

    if table_exists(con, "utility_subscriptions"):
        create_sql_row = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='utility_subscriptions'"
        ).fetchone()
        create_sql = (create_sql_row[0] or "") if create_sql_row else ""
        if "uq_building_utility" in create_sql:
            con.execute("DROP TABLE IF EXISTS utility_subscriptions_v4")
            con.execute("""
                CREATE TABLE utility_subscriptions_v4 (
                    id INTEGER NOT NULL PRIMARY KEY,
                    building_id INTEGER NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
                    utility_type VARCHAR(20) NOT NULL,
                    subscription_number VARCHAR(100),
                    bill_identifier VARCHAR(100),
                    installed_on DATE,
                    activated_on DATE,
                    deactivated_on DATE,
                    CONSTRAINT ck_subscription_utility_type
                        CHECK (utility_type IN ('electricity','water','gas'))
                )
            """)
            con.execute("""
                INSERT INTO utility_subscriptions_v4
                    (id, building_id, utility_type, subscription_number, bill_identifier,
                     installed_on, activated_on, deactivated_on)
                SELECT id, building_id, utility_type, subscription_number, bill_identifier,
                       installed_on, activated_on, deactivated_on
                FROM utility_subscriptions
            """)
            con.execute("DROP TABLE utility_subscriptions")
            con.execute("ALTER TABLE utility_subscriptions_v4 RENAME TO utility_subscriptions")
            changed = True
        con.execute("CREATE INDEX IF NOT EXISTS ix_utility_subscriptions_building_id ON utility_subscriptions(building_id)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_utility_subscriptions_utility_type ON utility_subscriptions(utility_type)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_subscription_building_type ON utility_subscriptions(building_id, utility_type)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_subscription_type_number ON utility_subscriptions(utility_type, subscription_number)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_utility_subscriptions_subscription_number ON utility_subscriptions(subscription_number)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_utility_subscriptions_bill_identifier ON utility_subscriptions(bill_identifier)")

    if table_exists(con, "utility_bills"):
        bill_columns = {row[1] for row in con.execute("PRAGMA table_info(utility_bills)")}
        if "utility_subscription_id" not in bill_columns:
            con.execute("ALTER TABLE utility_bills ADD COLUMN utility_subscription_id INTEGER REFERENCES utility_subscriptions(id) ON DELETE RESTRICT")
            changed = True
        con.execute("""
            UPDATE utility_bills
               SET utility_subscription_id = (
                   SELECT us.id FROM utility_subscriptions AS us
                    WHERE us.building_id = utility_bills.building_id
                      AND us.utility_type = utility_bills.utility_type
                    ORDER BY us.id LIMIT 1
               )
             WHERE utility_subscription_id IS NULL
        """)
        con.execute("CREATE INDEX IF NOT EXISTS ix_utility_bills_utility_subscription_id ON utility_bills(utility_subscription_id)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_bills_subscription_year_period ON utility_bills(utility_subscription_id, year, period_type)")

    if table_exists(con, "telecom_usage_records"):
        telecom_columns = {row[1] for row in con.execute("PRAGMA table_info(telecom_usage_records)")}
        if "telecom_type" not in telecom_columns:
            con.execute("ALTER TABLE telecom_usage_records ADD COLUMN telecom_type VARCHAR(30)")
            changed = True
        if table_exists(con, "telecom_services"):
            con.execute("""
                UPDATE telecom_usage_records
                   SET telecom_type = (
                       SELECT ts.service_type FROM telecom_services AS ts
                        WHERE ts.building_id = telecom_usage_records.building_id LIMIT 1
                   )
                 WHERE service_kind = 'telecom' AND telecom_type IS NULL
            """)
        con.execute("CREATE INDEX IF NOT EXISTS ix_telecom_usage_records_telecom_type ON telecom_usage_records(telecom_type)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_telecom_usage_type_year ON telecom_usage_records(telecom_type, year)")

    con.execute("""
        CREATE TABLE IF NOT EXISTS user_module_permissions (
            id INTEGER NOT NULL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module_key VARCHAR(40) NOT NULL,
            is_enabled BOOLEAN NOT NULL DEFAULT 1,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_module_permission UNIQUE (user_id, module_key),
            CONSTRAINT ck_user_module_key CHECK (
                module_key IN ('buildings','electricity','water','gas','production','reports','dynamic_reports','telecom')
            )
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS ix_user_module_permissions_user_id ON user_module_permissions(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS ix_user_module_permissions_module_key ON user_module_permissions(module_key)")
    con.execute("CREATE TABLE IF NOT EXISTS schema_markers (name VARCHAR(100) PRIMARY KEY, applied_at DATETIME NOT NULL)")
    con.execute("INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('module_subscriptions_v4', CURRENT_TIMESTAMP)")
    con.commit()
    con.execute("PRAGMA foreign_keys=ON")
    return changed


def apply_incremental_v5(con):
    """Persist generator type/capacity on production records for historical grouping."""
    changed = False
    if table_exists(con, "energy_production_records"):
        columns = {row[1] for row in con.execute("PRAGMA table_info(energy_production_records)")}
        if "generator_type" not in columns:
            con.execute("ALTER TABLE energy_production_records ADD COLUMN generator_type VARCHAR(30) NOT NULL DEFAULT 'other'")
            changed = True
        if "capacity_kwh" not in columns:
            con.execute("ALTER TABLE energy_production_records ADD COLUMN capacity_kwh NUMERIC(14,3)")
            changed = True
        if table_exists(con, "power_generators"):
            con.execute("""
                UPDATE energy_production_records
                   SET generator_type = COALESCE((
                           SELECT pg.generator_type FROM power_generators AS pg
                            WHERE pg.building_id = energy_production_records.building_id LIMIT 1
                       ), 'other'),
                       capacity_kwh = COALESCE(capacity_kwh, (
                           SELECT pg.production_capacity_kwh FROM power_generators AS pg
                            WHERE pg.building_id = energy_production_records.building_id LIMIT 1
                       ))
            """)
        con.execute("CREATE INDEX IF NOT EXISTS ix_energy_production_records_generator_type ON energy_production_records(generator_type)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_production_generator_year ON energy_production_records(generator_type, year)")
    con.execute("CREATE TABLE IF NOT EXISTS schema_markers (name VARCHAR(100) PRIMARY KEY, applied_at DATETIME NOT NULL)")
    con.execute("INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('production_snapshot_v5', CURRENT_TIMESTAMP)")
    con.commit()
    return changed


def add_user_columns_and_snapshot():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        return {}, [], None
    backup = DB_PATH.with_name(f"app-before-normalization-{datetime.now():%Y%m%d-%H%M%S}.db")
    shutil.copy2(DB_PATH, backup)
    con = sqlite3.connect(DB_PATH)
    snapshot = {name: rows(con, name) for name in LEGACY_TABLES}
    legacy_users = rows(con, "users") if table_exists(con, "users") else []
    rebuild_users_if_needed(con)
    con.close()
    return snapshot, legacy_users, backup


def number(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None


def old_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def run():
    if DB_PATH.exists():
        check = sqlite3.connect(DB_PATH)
        already_done = table_exists(check, "schema_markers") and check.execute(
            "SELECT 1 FROM schema_markers WHERE name='normalized_v2'"
        ).fetchone()
        if already_done:
            user_columns = {row[1] for row in check.execute("PRAGMA table_info(users)")} if table_exists(check, "users") else set()
            earth_columns = {row[1] for row in check.execute("PRAGMA table_info(earth_systems)")} if table_exists(check, "earth_systems") else set()
            v4_done = table_exists(check, "schema_markers") and check.execute(
                "SELECT 1 FROM schema_markers WHERE name='module_subscriptions_v4'"
            ).fetchone()
            v5_done = table_exists(check, "schema_markers") and check.execute(
                "SELECT 1 FROM schema_markers WHERE name='production_snapshot_v5'"
            ).fetchone()
            needs_change = "city" in user_columns or "resistance_ohm" not in earth_columns or not v4_done or not v5_done
            backup = None
            if needs_change:
                check.close()
                backup = DB_PATH.with_name(f"app-before-incremental-{datetime.now():%Y%m%d-%H%M%S}.db")
                shutil.copy2(DB_PATH, backup)
                check = sqlite3.connect(DB_PATH)
            repaired = rebuild_users_if_needed(check)
            upgraded = apply_incremental_v3(check)
            upgraded_v4 = apply_incremental_v4(check)
            upgraded_v5 = apply_incremental_v5(check)
            check.close()
            details = []
            if repaired:
                details.append("جدول users نرمال‌سازی شد")
            if upgraded:
                details.append("فیلد مقاومت ارت افزوده شد")
            if upgraded_v4 or not v4_done:
                details.append("چنداشتراکی، دسترسی ماژولی و نوع مخابرات ارتقا یافت")
            if upgraded_v5 or not v5_done:
                details.append("دسته‌بندی تاریخی تولید برق افزوده شد")
            suffix = ("؛ " + "، ".join(details)) if details else ""
            print("Schema normalized_v2 قبلاً اعمال شده است" + suffix + ".")
            if backup:
                print(f"نسخه پشتیبان: {backup}")
            return
        check.close()

    snapshot, legacy_users, backup = add_user_columns_and_snapshot()

    # Import only after legacy users has the columns expected by the new model.
    from app import app
    from extensions import db
    from sqlalchemy import text
    from models import (
        Building,
        BuildingUsageType,
        City,
        EnergyProductionRecord,
        PowerGenerator,
        User,
        UtilityBill,
        UtilitySubscription,
    )

    with app.app_context():
        db.session.execute(text("CREATE TABLE IF NOT EXISTS schema_markers (name VARCHAR(100) PRIMARY KEY, applied_at DATETIME NOT NULL)"))
        if db.session.execute(text("SELECT 1 FROM schema_markers WHERE name='normalized_v2'")).first():
            print("Schema normalized_v2 قبلاً اعمال شده است.")
            return

        city_names = set()
        for user in legacy_users:
            if user.get("city"):
                city_names.add(str(user["city"]).strip())
        for table in ("water_records", "electricity_records", "gas_records", "clean_energy_records"):
            for item in snapshot.get(table, []):
                if item.get("city"):
                    city_names.add(str(item["city"]).strip())
        city_map = {}
        for idx, name in enumerate(sorted(city_names), 1):
            city = City.query.filter_by(name=name).first()
            if not city:
                base_code = f"LEG-{idx:03d}"
                code = base_code
                suffix = 1
                while City.query.filter_by(code=code).first():
                    suffix += 1
                    code = f"{base_code}-{suffix}"
                city = City(code=code, name=name)
                db.session.add(city)
                db.session.flush()
            city_map[name] = city

        for old in legacy_users:
            user = db.session.get(User, old["id"])
            old_city = str(old.get("city") or "").strip()
            if user and old_city:
                user.assigned_city = city_map[old_city]

        usage_lookup = {u.name: u for u in BuildingUsageType.query.all()}
        other_usage = BuildingUsageType.query.filter_by(code="other").first()

        def find_or_create_building(item, preferred_name, address="نشانی ثبت نشده", usage_name=None):
            city_name = str(item.get("city") or "نامشخص").strip()
            city = city_map.get(city_name)
            if not city:
                city = City.query.filter_by(name=city_name).first()
            if not city:
                code = f"LEG-{len(city_map)+1:03d}"
                while City.query.filter_by(code=code).first():
                    code += "X"
                city = City(code=code, name=city_name)
                db.session.add(city)
                db.session.flush()
                city_map[city_name] = city
            staff = int(item.get("staff_count") or 0)
            if staff:
                match = Building.query.filter_by(city_id=city.id, staff_count=staff).first()
                if match:
                    return match
            name = str(preferred_name or "ساختمان قدیمی").strip()
            existing = Building.query.filter_by(city_id=city.id, name=name).first()
            if existing:
                suffix = str(address or item.get("id") or "قدیمی")[:60]
                name = f"{name} - {suffix}"
                counter = 2
                while Building.query.filter_by(city_id=city.id, name=name).first():
                    name = f"{preferred_name} - {suffix} ({counter})"
                    counter += 1
            building = Building(
                name=name,
                city=city,
                usage_type=usage_lookup.get(str(usage_name or "").strip(), other_usage),
                address=str(address or "نشانی ثبت نشده"),
                staff_count=staff,
                created_by_id=item.get("created_by_id"),
                notes="مهاجرت خودکار از ساختار قدیمی",
            )
            db.session.add(building)
            db.session.flush()
            return building

        def subscription(building, utility):
            obj = UtilitySubscription.query.filter_by(building_id=building.id, utility_type=utility).first()
            if not obj:
                obj = UtilitySubscription(building=building, utility_type=utility)
                db.session.add(obj)
            return obj

        for item in snapshot.get("water_records", []):
            building = find_or_create_building(item, item.get("device_title"), item.get("device_address"), item.get("usage_type"))
            sub = subscription(building, "water")
            sub.subscription_number = item.get("subscription_number")
            sub.bill_identifier = item.get("receipt_id")
            consumption, amount = number(item.get("consumption_amount")), number(item.get("amount"))
            if consumption is not None and amount is not None:
                db.session.add(UtilityBill(building=building, utility_subscription=sub, utility_type="water", period_type="annual", year=1404, consumption=consumption, amount=amount, created_by_id=item.get("created_by_id")))

        for item in snapshot.get("electricity_records", []):
            building = find_or_create_building(item, f"ساختمان برق قدیمی {item.get('id')}", "نشانی ثبت نشده", item.get("usage_type"))
            sub = subscription(building, "electricity")
            sub.bill_identifier = item.get("building_receipt_id")
            consumption = number(item.get("kwh_1404"))
            if consumption is not None:
                db.session.add(UtilityBill(building=building, utility_subscription=sub, utility_type="electricity", period_type="annual", year=1404, consumption=consumption, amount=0, created_by_id=item.get("created_by_id"), notes=item.get("description")))

        for item in snapshot.get("gas_records", []):
            building = find_or_create_building(item, item.get("building_name") or item.get("device_name"), item.get("address"), None)
            sub = subscription(building, "gas")
            sub.subscription_number = item.get("subscription_number")
            sub.bill_identifier = item.get("gas_receipt_id")
            sub.activated_on = old_date(item.get("start_date"))
            building.utm_easting = number(item.get("x_decimal"))
            building.utm_northing = number(item.get("y_decimal"))

        clean_children = {}
        for child in snapshot.get("clean_energy_buildings", []):
            clean_children.setdefault(child.get("record_id"), []).append(child.get("receipt_id"))
        for item in snapshot.get("clean_energy_records", []):
            building = find_or_create_building(item, item.get("org_name"), "نشانی ثبت نشده", None)
            if not building.generator:
                building.generator = PowerGenerator(generator_type="other", production_capacity_kwh=number(item.get("built_capacity_kw")))
            production = number(item.get("annual_production_kwh"))
            if production is not None:
                notes = "شناسه قبوض قدیمی تابعه: " + ", ".join(filter(None, clean_children.get(item.get("id"), []))) if clean_children.get(item.get("id")) else None
                db.session.add(EnergyProductionRecord(building=building, year=1404, generator_type=building.generator.generator_type, capacity_kwh=building.generator.production_capacity_kwh, produced_kwh=production, notes=notes, created_by_id=item.get("created_by_id")))

        db.session.commit()
        # Legacy tables are removed only after successful normalized inserts; backup remains available.
        for table in LEGACY_TABLES:
            db.session.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
        db.session.execute(text("INSERT INTO schema_markers(name, applied_at) VALUES ('normalized_v2', CURRENT_TIMESTAMP)"))
        db.session.execute(text("INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('jalali_reporting_v3', CURRENT_TIMESTAMP)"))
        db.session.execute(text("INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('module_subscriptions_v4', CURRENT_TIMESTAMP)"))
        db.session.execute(text("INSERT OR IGNORE INTO schema_markers(name, applied_at) VALUES ('production_snapshot_v5', CURRENT_TIMESTAMP)"))
        db.session.commit()
        print("مهاجرت normalized_v2 با موفقیت انجام شد.")
        if backup:
            print(f"نسخه پشتیبان: {backup}")


if __name__ == "__main__":
    run()
