"""Small dependency-free Jalali (Solar Hijri) conversion helpers.

The database keeps Gregorian DATE values for portable indexing and comparisons;
all user-facing parsing/formatting is Jalali.
"""
from __future__ import annotations

from datetime import date
import re

_PERSIAN = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC = "٠١٢٣٤٥٦٧٨٩"
_ASCII = "0123456789"
_DIGIT_TABLE = str.maketrans(_PERSIAN + _ARABIC, _ASCII + _ASCII)
_TO_PERSIAN = str.maketrans(_ASCII, _PERSIAN)


def normalize_digits(value) -> str:
    return str(value or "").translate(_DIGIT_TABLE).strip()


def to_persian_digits(value) -> str:
    return str(value).translate(_TO_PERSIAN)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gy -= 1600
    gm -= 1
    gd -= 1
    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400
    for month in range(gm):
        g_day_no += g_days[month]
    if gm > 1 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day_no += 1
    g_day_no += gd
    j_day_no = g_day_no - 79
    cycles, j_day_no = divmod(j_day_no, 12053)
    jy = 979 + 33 * cycles + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm, jd = 1 + j_day_no // 31, 1 + j_day_no % 31
    else:
        j_day_no -= 186
        jm, jd = 7 + j_day_no // 30, 1 + j_day_no % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    if not 1 <= jm <= 12 or jd < 1 or jd > jalali_month_length(jy, jm):
        raise ValueError("تاریخ شمسی نامعتبر است.")
    g_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    jy -= 979
    jm -= 1
    jd -= 1
    j_day_no = 365 * jy + (jy // 33) * 8 + ((jy % 33) + 3) // 4
    for month in range(jm):
        j_day_no += 31 if month < 6 else 30
    j_day_no += jd
    g_day_no = j_day_no + 79
    gy = 1600 + 400 * (g_day_no // 146097)
    g_day_no %= 146097
    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100 * (g_day_no // 36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False
    gy += 4 * (g_day_no // 1461)
    g_day_no %= 1461
    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no // 365
        g_day_no %= 365
    gm = 0
    while True:
        days = g_days[gm] + (1 if gm == 1 and leap else 0)
        if g_day_no < days:
            break
        g_day_no -= days
        gm += 1
    return gy, gm + 1, g_day_no + 1


def is_jalali_leap(year: int) -> bool:
    # The conversion itself is the source of truth: Esfand 30 exists iff it
    # maps back to the same Jalali date.
    try:
        gy, gm, gd = _jalali_to_gregorian_unchecked(year, 12, 30)
        return gregorian_to_jalali(gy, gm, gd) == (year, 12, 30)
    except Exception:
        return False


def _jalali_to_gregorian_unchecked(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    """Internal converter without recursive month-length validation."""
    g_days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    jy0, jm0, jd0 = jy - 979, jm - 1, jd - 1
    day_no = 365 * jy0 + (jy0 // 33) * 8 + ((jy0 % 33) + 3) // 4
    day_no += sum(31 if month < 6 else 30 for month in range(jm0)) + jd0 + 79
    gy = 1600 + 400 * (day_no // 146097)
    day_no %= 146097
    leap = True
    if day_no >= 36525:
        day_no -= 1
        gy += 100 * (day_no // 36524)
        day_no %= 36524
        if day_no >= 365:
            day_no += 1
        else:
            leap = False
    gy += 4 * (day_no // 1461)
    day_no %= 1461
    if day_no >= 366:
        leap = False
        day_no -= 1
        gy += day_no // 365
        day_no %= 365
    gm = 0
    while True:
        length = g_days[gm] + (1 if gm == 1 and leap else 0)
        if day_no < length:
            break
        day_no -= length
        gm += 1
    return gy, gm + 1, day_no + 1


def jalali_month_length(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise ValueError("ماه شمسی نامعتبر است.")
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if is_jalali_leap(year) else 29


def parse_jalali_date(value, required: bool = False) -> date | None:
    raw = normalize_digits(value)
    if not raw:
        if required:
            raise ValueError("تاریخ الزامی است.")
        return None
    match = re.fullmatch(r"(\d{4})\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})", raw)
    if not match:
        raise ValueError("تاریخ شمسی باید به‌شکل ۱۴۰۵/۰۶/۰۶ وارد شود.")
    jy, jm, jd = map(int, match.groups())
    if not 1200 <= jy <= 1600:
        raise ValueError("سال شمسی خارج از محدوده مجاز است.")
    gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
    result = date(gy, gm, gd)
    if gregorian_to_jalali(result.year, result.month, result.day) != (jy, jm, jd):
        raise ValueError("تاریخ شمسی نامعتبر است.")
    return result


def format_jalali_date(value: date | None, persian_digits: bool = True) -> str:
    if not value:
        return ""
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    result = f"{jy:04d}/{jm:02d}/{jd:02d}"
    return to_persian_digits(result) if persian_digits else result
