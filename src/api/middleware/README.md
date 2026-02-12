# `middleware/` — Request Middleware

Middleware intercepts every HTTP request **before** it reaches the route handler.
This folder contains cross-cutting concerns that apply to all routes.

## Files

### `auth.py` — API Key Authentication
**Placeholder implementation.** Checks for an `X-API-Key` header and validates
it against a configured key. In production, this would:
- Validate JWTs or API keys against a database
- Extract user identity and attach it to the request
- Return 401/403 for invalid credentials

### `rate_limit.py` — Rate Limiting
**Placeholder implementation.** Tracks request counts per IP address using an
in-memory dictionary. In production, this would:
- Use Redis for distributed rate limiting
- Support different limits per endpoint or user tier
- Return 429 (Too Many Requests) with retry-after headers

## Why Placeholders?

These files demonstrate the **pattern** without requiring external infrastructure.
They show where auth and rate limiting plug into the stack, making it easy to
swap in real implementations later (e.g., Auth0, Redis, CloudFlare).

## How to Explain This

> "Middleware handles cross-cutting concerns like authentication and rate limiting.
> I implemented these as placeholders to demonstrate the integration pattern
> without requiring external services. In production, `auth.py` would validate
> JWTs and `rate_limit.py` would use Redis for distributed limiting."
