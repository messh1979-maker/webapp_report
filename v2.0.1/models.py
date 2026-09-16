from datetime import UTC, datetime
from decimal import Decimal

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


def utcnow():
    """UTC naive is used consistently because SQLAlchemy/SQLite do not preserve tzinfo."""
    return datetime.now(UTC).replace(tzinfo=None)


class City(db.Model):
    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    buildings = db.relationship("Building", back_populates="city", lazy="dynamic")

    def __str__(self):
        return self.name


class BuildingUsageType(db.Model):
    __tablename__ = "building_usage_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False, unique=True)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    is_active_flag = db.Column(db.Boolean, nullable=False, default=True, index=True)
    active_from = db.Column(db.DateTime)
    active_until = db.Column(db.DateTime, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    last_login_at = db.Column(db.DateTime)

    assigned_city = db.relationship("City", foreign_keys=[city_id], lazy="joined")
    module_permissions = db.relationship(
        "UserModulePermission", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'admin_view', 'user', 'view')",
            name="ck_users_role",
        ),
    )

    def set_password(self, raw_password):
        # Werkzeug scrypt: memory-hard and salted; never store plaintext passwords.
        self.password_hash = generate_password_hash(raw_password, method="scrypt:32768:8:1")

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_admin_view(self):
        return self.role == "admin_view"

    @property
    def is_view_only(self):
        return self.role == "view"

    @property
    def can_write(self):
        return self.role in ("admin", "user")

    @property
    def can_view_all_cities(self):
        return self.role in ("admin", "admin_view")

    @property
    def city_name(self):
        return self.assigned_city.name if self.assigned_city else None

    @property
    def is_active(self):
        now = utcnow()
        if not self.is_active_flag:
            return False
        if self.active_from and now < self.active_from:
            return False
        if self.active_until and now >= self.active_until:
            return False
        return True

    @property
    def remaining_account_seconds(self):
        if not self.active_until:
            return None
        return max(0, int((self.active_until - utcnow()).total_seconds()))

    def has_module(self, module_key):
        """Missing rows mean enabled, preserving access for users created before v4."""
        if self.is_admin:
            return True
        permission = next((item for item in self.module_permissions if item.module_key == module_key), None)
        return True if permission is None else bool(permission.is_enabled)


class UserModulePermission(db.Model):
    __tablename__ = "user_module_permissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    module_key = db.Column(db.String(40), nullable=False, index=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", back_populates="module_permissions")

    __table_args__ = (
        UniqueConstraint("user_id", "module_key", name="uq_user_module_permission"),
        CheckConstraint(
            "module_key IN ('buildings','electricity','water','gas','production','reports','dynamic_reports','telecom')",
            name="ck_user_module_key",
        ),
    )


class LoginThrottle(db.Model):
    """Persistent login throttling shared by all Gunicorn workers."""

    __tablename__ = "login_throttles"

    id = db.Column(db.Integer, primary_key=True)
    identifier_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
    failure_count = db.Column(db.Integer, nullable=False, default=0)
    window_started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    locked_until = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Building(db.Model):
    __tablename__ = "buildings"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id", ondelete="RESTRICT"), nullable=False, index=True)
    usage_type_id = db.Column(
        db.Integer,
        db.ForeignKey("building_usage_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    address = db.Column(db.String(700), nullable=False)
    utm_zone = db.Column(db.String(10))
    utm_easting = db.Column(db.Numeric(12, 3))
    utm_northing = db.Column(db.Numeric(13, 3))
    staff_count = db.Column(db.Integer, nullable=False, default=0)
    emergency_power_capacity_kw = db.Column(db.Numeric(14, 3))
    phone_line_count = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    city = db.relationship("City", back_populates="buildings", lazy="joined")
    usage_type = db.relationship("BuildingUsageType", lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")
    utility_subscriptions = db.relationship(
        "UtilitySubscription", back_populates="building", cascade="all, delete-orphan", lazy="selectin"
    )
    generator = db.relationship(
        "PowerGenerator", back_populates="building", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    telecom_service = db.relationship(
        "TelecomService", back_populates="building", cascade="all, delete-orphan", uselist=False, lazy="select"
    )
    network_services = db.relationship(
        "NetworkService", back_populates="building", cascade="all, delete-orphan", lazy="select"
    )
    tower = db.relationship(
        "Tower", back_populates="building", cascade="all, delete-orphan", uselist=False, lazy="select"
    )
    earth_system = db.relationship(
        "EarthSystem", back_populates="building", cascade="all, delete-orphan", uselist=False, lazy="select"
    )
    bills = db.relationship("UtilityBill", back_populates="building", cascade="all, delete-orphan", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("city_id", "name", name="uq_building_city_name"),
        CheckConstraint("staff_count >= 0", name="ck_building_staff_nonnegative"),
        CheckConstraint("phone_line_count >= 0", name="ck_building_phone_nonnegative"),
        Index("ix_buildings_city_active_name", "city_id", "is_active", "name"),
    )

    def subscriptions(self, utility_type):
        return sorted(
            (s for s in self.utility_subscriptions if s.utility_type == utility_type),
            key=lambda item: (item.deactivated_on is not None, item.id or 0),
        )

    def subscription(self, utility_type):
        """Compatibility helper returning the first active/preferred subscription."""
        return next(iter(self.subscriptions(utility_type)), None)

    def network_service(self, service_kind):
        return next((s for s in self.network_services if s.service_kind == service_kind), None)


class UtilitySubscription(db.Model):
    """Electricity/water/gas identity is stored once, never copied into bill rows."""

    __tablename__ = "utility_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    utility_type = db.Column(db.String(20), nullable=False, index=True)
    subscription_number = db.Column(db.String(100), index=True)
    bill_identifier = db.Column(db.String(100), index=True)
    installed_on = db.Column(db.Date)
    activated_on = db.Column(db.Date)
    deactivated_on = db.Column(db.Date)

    building = db.relationship("Building", back_populates="utility_subscriptions")

    __table_args__ = (
        CheckConstraint(
            "utility_type IN ('electricity', 'water', 'gas')",
            name="ck_subscription_utility_type",
        ),
        Index("ix_subscription_building_type", "building_id", "utility_type"),
        Index("ix_subscription_type_number", "utility_type", "subscription_number"),
    )


class PowerGenerator(db.Model):
    __tablename__ = "power_generators"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    generator_type = db.Column(db.String(30), nullable=False, default="other")
    production_capacity_kwh = db.Column(db.Numeric(14, 3))

    building = db.relationship("Building", back_populates="generator")

    __table_args__ = (
        CheckConstraint(
            "generator_type IN ('diesel', 'gas', 'hybrid', 'solar', 'wind', 'other')",
            name="ck_generator_type",
        ),
    )


class TelecomService(db.Model):
    __tablename__ = "telecom_services"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    service_type = db.Column(db.String(30), nullable=False, default="analog")
    provider = db.Column(db.String(200))
    case_number = db.Column(db.String(100), index=True)
    installed_on = db.Column(db.Date)

    building = db.relationship("Building", back_populates="telecom_service")

    __table_args__ = (
        CheckConstraint(
            "service_type IN ('e1', 'analog', 'sip_trunk', 'sip')",
            name="ck_telecom_type",
        ),
    )


class NetworkService(db.Model):
    __tablename__ = "network_services"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_kind = db.Column(db.String(20), nullable=False)
    provider = db.Column(db.String(200))
    speed_mbps = db.Column(db.Numeric(12, 3))
    installed_on = db.Column(db.Date)

    building = db.relationship("Building", back_populates="network_services")

    __table_args__ = (
        UniqueConstraint("building_id", "service_kind", name="uq_building_network_kind"),
        CheckConstraint(
            "service_kind IN ('internet', 'mpls', 'intranet')",
            name="ck_network_service_kind",
        ),
    )


class Tower(db.Model):
    __tablename__ = "towers"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tower_type = db.Column(db.String(20), nullable=False, default="self_supporting")
    height_m = db.Column(db.Numeric(8, 2))

    building = db.relationship("Building", back_populates="tower")

    __table_args__ = (
        CheckConstraint(
            "tower_type IN ('polygonal', 'self_supporting')",
            name="ck_tower_type",
        ),
    )


class EarthSystem(db.Model):
    __tablename__ = "earth_systems"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    has_earth = db.Column(db.Boolean, nullable=False, default=False)
    resistance_ohm = db.Column(db.Numeric(12, 3))
    # Kept for backward compatibility; new forms use the numeric resistance.
    last_inspection_status = db.Column(db.String(250))
    last_inspected_on = db.Column(db.Date)

    __table_args__ = (
        CheckConstraint("resistance_ohm IS NULL OR resistance_ohm >= 0", name="ck_earth_resistance_nonnegative"),
    )

    building = db.relationship("Building", back_populates="earth_system")


class UtilityBill(db.Model):
    __tablename__ = "utility_bills"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    utility_subscription_id = db.Column(
        db.Integer, db.ForeignKey("utility_subscriptions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    utility_type = db.Column(db.String(20), nullable=False, index=True)
    period_type = db.Column(db.String(20), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    reading_from = db.Column(db.Date)
    reading_to = db.Column(db.Date)
    consumption = db.Column(db.Numeric(18, 3), nullable=False)
    amount = db.Column(db.Numeric(20, 2), nullable=False)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    building = db.relationship("Building", back_populates="bills", lazy="joined")
    utility_subscription = db.relationship("UtilitySubscription", lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "utility_type IN ('electricity', 'water', 'gas')",
            name="ck_bill_utility_type",
        ),
        CheckConstraint(
            "period_type IN ('annual', 'periodic')", name="ck_bill_period_type"
        ),
        CheckConstraint("consumption >= 0", name="ck_bill_consumption_nonnegative"),
        CheckConstraint("amount >= 0", name="ck_bill_amount_nonnegative"),
        Index("ix_bills_building_utility_year", "building_id", "utility_type", "year"),
        Index("ix_bills_subscription_year_period", "utility_subscription_id", "year", "period_type"),
        Index("ix_bills_utility_year_period", "utility_type", "year", "period_type"),
    )

    @property
    def per_capita(self):
        if self.building and self.building.staff_count and self.consumption is not None:
            return (Decimal(self.consumption) / Decimal(self.building.staff_count)).quantize(Decimal("0.001"))
        return None

    @property
    def unit(self):
        return {"electricity": "kWh", "water": "m³", "gas": "m³"}.get(self.utility_type, "")


class EnergyProductionRecord(db.Model):
    __tablename__ = "energy_production_records"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year = db.Column(db.Integer, nullable=False, index=True)
    period_from = db.Column(db.Date)
    period_to = db.Column(db.Date)
    generator_type = db.Column(db.String(30), nullable=False, default="other", index=True)
    capacity_kwh = db.Column(db.Numeric(14, 3))
    produced_kwh = db.Column(db.Numeric(18, 3), nullable=False)
    notes = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    building = db.relationship("Building", lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "generator_type IN ('diesel','gas','hybrid','solar','wind','other')",
            name="ck_production_generator_type",
        ),
        CheckConstraint("capacity_kwh IS NULL OR capacity_kwh >= 0", name="ck_production_capacity_nonnegative"),
        CheckConstraint("produced_kwh >= 0", name="ck_production_nonnegative"),
        Index("ix_production_building_year", "building_id", "year"),
        Index("ix_production_generator_year", "generator_type", "year"),
    )


class TelecomUsageRecord(db.Model):
    __tablename__ = "telecom_usage_records"

    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(
        db.Integer, db.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_kind = db.Column(db.String(20), nullable=False, index=True)
    telecom_type = db.Column(db.String(30), index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    period_from = db.Column(db.Date)
    period_to = db.Column(db.Date)
    amount = db.Column(db.Numeric(20, 2), nullable=False, default=0)
    usage_description = db.Column(db.String(500))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    building = db.relationship("Building", lazy="joined")
    created_by = db.relationship("User", foreign_keys=[created_by_id], lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "service_kind IN ('telecom', 'internet', 'mpls', 'intranet')",
            name="ck_telecom_usage_kind",
        ),
        CheckConstraint(
            "telecom_type IS NULL OR telecom_type IN ('e1','analog','sip_trunk','sip')",
            name="ck_telecom_usage_type",
        ),
        CheckConstraint("amount >= 0", name="ck_telecom_usage_amount"),
        Index("ix_telecom_usage_building_year", "building_id", "year"),
        Index("ix_telecom_usage_type_year", "telecom_type", "year"),
    )
