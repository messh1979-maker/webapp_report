# Test report — 2026-08-28

## Automated functional/security tests

Command:

```bash
pytest -q
```

Result: **16 passed**.

Covered checks:

1. `utility_bills` contains normalized foreign keys and no duplicated building name/address/subscription number/staff fields.
2. Per-capita calculation is correct.
3. Periodic rows take precedence over annual input and are summed without double counting.
4. Expired users cannot log in.
5. CSRF blocks state-changing requests without a token and security headers are present.
6. Building XLSX import normalizes related rows and building XLSX export is valid.
7. User XLSX import hashes plaintext input immediately with scrypt.
8. User creation with Tehran-local Jalali start/expiry dates is converted and persisted correctly in UTC.
9. Jalali parsing/date conversion and Persian-digit, three-grouped Rial input are validated through the bill form.
10. Separate two-sheet utility Excel reports and allowlisted dynamic report preview/export are validated.
11. Remaining login attempts are displayed and decrement after failures.
12. Per-user module ACLs, direct-route HTTP 403 enforcement and telecom rollout flag are validated.
13. Multiple subscriptions, selected-subscription Jalali dates and the separate subscription Excel Sheet are validated.
14. Production form snapshots and generator-type detail/summary Excel sheets are validated.
15. E1, analog, SIP Trunk and SIP are stored/exported as independent telecom records.
16. Periodic city per-capita comparison and smart existing-building selection are validated.

Additional route smoke tests returned HTTP 200 for dashboard, buildings, building edit, consumptions, production, telecom, reports, city/user administration, APIs and health check.

## 50 concurrent authenticated sessions

Command pattern:

```bash
python tests/load_test.py --url http://127.0.0.1:8000 \
  --username admin --password "..." --users 50 --requests 5
```

Result with Gunicorn and supplied SQLite test data:

```text
users=50 requests=250 errors=0 elapsed=4.05s
avg=0.172s p95=0.559s max=0.749s
```

The current Gunicorn default is 2 or more workers (CPU dependent) and 25 threads per worker. PostgreSQL is required/recommended for the final multi-user server, especially when concurrent writes are expected. Re-run this script on production-sized data and target infrastructure before go-live.
