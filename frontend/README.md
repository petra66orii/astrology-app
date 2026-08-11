# Commercial frontend

This is the Next.js App Router client for the new commercial vertical slice.

## Local setup

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

The frontend expects Django at `http://localhost:8000/api/v1` by default. Authentication uses Django HttpOnly session cookies and CSRF headers. No token is stored in localStorage.

## Routes

- `/`: product introduction
- `/register` and `/login`: session account flow
- `/dashboard`: saved chart list
- `/chart/new`: exact/unknown birth input and GeoNames autocomplete
- `/charts/[id]`: normalized exact or unknown-time result

Read-heavy dashboard/result pages are Server Components. Forms and autocomplete are focused Client Components.

## Checks

```powershell
npm ci
npm test
npm run typecheck
npm run lint
npm run build
npm audit --audit-level=high
```

The result UI intentionally shows no fake wheel for unknown birth time. It omits angles and houses and explains why those values are unavailable.
