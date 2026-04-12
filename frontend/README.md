# `frontend/` — Next.js 15 Frontend

The customer-facing web application built with **Next.js 15**, **TypeScript**,
and **Tailwind CSS**. Provides the login page, customer dashboard, ticket
detail/chat view, admin panel, and analytics dashboard.

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| Next.js 15 | React framework with App Router (file-system routing) |
| TypeScript | Type-safe JavaScript |
| Tailwind CSS | Utility-first CSS framework |
| Supabase Auth | Client-side authentication (sign-up, sign-in, JWT management) |

## Folder Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router (pages)
│   │   ├── layout.tsx          # Root layout — wraps all pages, auth guard
│   │   ├── page.tsx            # Dashboard — ticket list + create ticket form
│   │   ├── login/
│   │   │   └── page.tsx        # Login/Sign-up page (Supabase Auth)
│   │   ├── tickets/
│   │   │   └── [id]/
│   │   │       └── page.tsx    # Ticket detail — chat view, resolve, send messages
│   │   ├── admin/
│   │   │   └── page.tsx        # Admin panel — all conversations, reply as agent
│   │   ├── analytics/
│   │   │   └── page.tsx        # Analytics dashboard — charts, metrics
│   │   └── globals.css         # Global styles
│   │
│   ├── hooks/
│   │   └── useAuth.ts          # React hook for Supabase authentication
│   │
│   └── lib/
│       ├── api.ts              # Backend API client (axios-based)
│       └── supabase.ts         # Supabase browser client setup
│
├── public/                     # Static assets
├── next.config.ts              # Next.js configuration
├── tailwind.config.ts          # Tailwind CSS configuration
├── tsconfig.json               # TypeScript configuration
├── package.json                # Node.js dependencies
└── .env.local                  # Environment variables (Supabase URL + key)
```

## Key Files Explained

### `src/hooks/useAuth.ts` — Authentication Hook

A custom React hook that manages the entire auth lifecycle:
- Listens for Supabase auth state changes (login, logout, token refresh)
- Extracts user role from JWT metadata (`customer` vs `admin`)
- Provides `user`, `role`, `loading`, and `signOut` to any component
- Redirects unauthenticated users to `/login`

### `src/lib/api.ts` — Backend API Client

Wraps all backend API calls in typed functions:
```typescript
api.getTickets()                    // GET /api/v1/tickets
api.createTicket(data)              // POST /api/v1/tickets
api.getTicket(id)                   // GET /api/v1/tickets/{id}
api.sendMessage(ticketId, content)  // POST /api/v1/tickets/{id}/messages
api.resolveTicket(id)               // PATCH /api/v1/tickets/{id}/resolve
```
Automatically attaches the JWT token to every request.

### `src/lib/supabase.ts` — Supabase Client

Creates the Supabase browser client using `NEXT_PUBLIC_SUPABASE_URL`
and `NEXT_PUBLIC_SUPABASE_ANON_KEY` environment variables.

## How to Run

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start dev server at http://localhost:3000
```

## Environment Variables

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...your-anon-key
```
