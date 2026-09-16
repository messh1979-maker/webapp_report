# معماری داده نرمال‌شده

```text
City 1 ─── n Building n ─── 1 BuildingUsageType
                 │
                 ├── 1:n UtilitySubscription (چند اشتراک electricity/water/gas)
                 │             └── 1:n UtilityBill (utility_subscription_id)
                 ├── 1:n UtilityBill (building_id برای Scope/Index)
                 ├── 1:1 PowerGenerator
                 ├── 1:1 TelecomService
                 ├── 1:n NetworkService (internet/mpls/intranet)
                 ├── 1:1 Tower
                 ├── 1:1 EarthSystem
                 ├── 1:n EnergyProductionRecord
                 └── 1:n TelecomUsageRecord
```

`UtilityBill` فقط کلیدهای خارجی `building_id` و `utility_subscription_id` را نگه می‌دارد. نام، آدرس، شهر، تعداد افراد، شماره اشتراک و شناسه قبض در قبض تکرار نشده‌اند. `building_id` برای Scope و ایندکس سریع باقی مانده و لایه سرویس هنگام ذخیره سازگاری آن را با ساختمان اشتراک کنترل می‌کند. سرانه مقدار مشتق‌شده است و ذخیره نمی‌شود. مقاومت ارت به‌صورت مقدار عددی `resistance_ohm` نگهداری می‌شود.

مجوزهای ماژولی در `UserModulePermission` با رابطه 1:n و کلید یکتای `(user_id, module_key)` ذخیره می‌شوند. نبود رکورد برای کاربران قدیمی به معنی فعال بودن است تا Migration باعث قطع دسترسی نشود؛ پس از اولین ذخیره فرم admin برای همه ماژول‌ها رکورد صریح ایجاد می‌شود. رکورد تولید، `generator_type` و `capacity_kwh` زمان ثبت را نگه می‌دارد تا تغییر بعدی اطلاعات پایه، دسته‌بندی تاریخی گزارش را جابه‌جا نکند.

تاریخ‌های رابط کاربری شمسی‌اند، اما پس از اعتبارسنجی به `DATE/DATETIME` استاندارد تبدیل می‌شوند تا مرتب‌سازی و ایندکس پایگاه‌داده صحیح بماند. گزارش‌ساز پویا فقط از فهرست مجاز فیلدها و Joinهای ازپیش‌تعریف‌شده استفاده می‌کند و هیچ نام ستون یا SQL خام از کاربر نمی‌پذیرد.

برای جمع سالیانه، اگر برای ساختمان/اشتراک/سال رکورد دوره‌ای وجود داشته باشد، مجموع دوره‌ای مبنا است؛ در غیر این صورت رکورد سالیانه استفاده می‌شود. این قاعده از دوباره‌شماری جلوگیری می‌کند.

ایندکس‌های ترکیبی مهم:

- `buildings(city_id, is_active, name)`
- `utility_bills(building_id, utility_type, year)`
- `utility_bills(utility_type, year, period_type)`
- `utility_bills(utility_subscription_id, year, period_type)`
- `utility_subscriptions(building_id, utility_type)`
- `utility_subscriptions(utility_type, subscription_number)`
- `user_module_permissions(user_id, module_key)`
- `energy_production_records(building_id, year)`
- `energy_production_records(generator_type, year)`
- `telecom_usage_records(building_id, year)`
