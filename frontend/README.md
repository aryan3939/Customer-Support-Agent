# `frontend/` — Next.js Dashboard

The customer support dashboard built with **Next.js 14** (App Router),
**TypeScript**, and **Tailwind CSS**. Provides a visual interface for
managing tickets, viewing AI responses, and monitoring analytics.

## Pages

| Route | File | What It Shows |
|-------|------|--------------|
| `/` | `app/page.tsx` | **Ticket List** — table of all tickets + "New Ticket" dialog form |
| `/tickets/[id]` | `app/tickets/[id]/page.tsx` | **Ticket Detail** — chat thread with AI, classification sidebar, audit trail |
| `/analytics` | `app/analytics/page.tsx` | **Dashboard** — metric cards (total, open, resolved, escalated) + breakdowns |

## Key Files

| File | Purpose |
|------|---------|
| `src/lib/api.ts` | **Typed API client** — all `fetch()` calls to the backend with TypeScript interfaces matching Pydantic schemas |
| `src/app/layout.tsx` | Root layout — sidebar navigation, dark theme, Google Fonts (Inter) |
| `src/app/globals.css` | CSS variables for the dark color theme |
| `next.config.ts` | **Critical** — proxies `/api/v1/*` requests to `http://localhost:8000` so frontend and backend can run on different ports |
| `package.json` | Dependencies: next, react, tailwindcss |

## API Proxy

The frontend runs on `:3000`, the backend on `:8000`. Instead of dealing with
CORS for every request, `next.config.ts` proxies all `/api/v1/*` calls:

```
Browser → localhost:3000/api/v1/tickets → (proxy) → localhost:8000/api/v1/tickets
```

This means the frontend code just calls `/api/v1/tickets` without knowing
about the backend port.

## How to Run

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

## Design

- **Dark theme** with custom CSS variables
- **Responsive layout** with sidebar navigation
- **Chat interface** for ticket conversations
- **Status badges** with color coding (green=resolved, yellow=open, red=escalated)
- **Real-time AI classification** visible in the sidebar

## How to Explain This

> "The frontend is a Next.js dashboard that communicates with the FastAPI
> backend through an API proxy. The typed client in `api.ts` mirrors the
> backend Pydantic schemas exactly, giving end-to-end type safety.
> The chat interface shows the AI's response alongside a classification
> sidebar (intent, priority, sentiment) and a full audit trail of every
> action the agent took."
