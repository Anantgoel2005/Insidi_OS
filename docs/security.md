# Security and responsible use

Insidi_OS is designed for owned lab networks and defensive demonstrations. It does not execute captured commands, block traffic, or expose decoy services from the production control plane.

- Production startup rejects missing admin password hashes, weak secrets, and non-HTTPS public URLs.
- Production startup rejects plaintext admin passwords, wildcard CORS, invalid session lifetimes, and missing explicit origins.
- Dashboard mutations require an authenticated HttpOnly session plus a matching CSRF token.
- Session tokens validate a fixed signing algorithm, issuer, audience, subject, expiry, and unique token ID.
- URL canary callbacks record only the source address, bounded user agent, and request path. The token is one-time.
- The Docker socket is absent from the base and production Compose files. It is available only through `docker-compose.lab.yml`.
- Production Compose does not publish PostgreSQL, Redis, FastAPI, or Next.js directly; Caddy is the only public ingress.
- Production demo mode defaults to disabled and must be enabled deliberately.
- Use TEST-NET source addresses in the bundled scenario. Do not identify or target real third parties.

For a public deployment, place the server behind the supplied Caddy configuration, keep the OS patched, restrict SSH administration, retain database backups, and rotate the admin password and application secret if access is suspected. See the [architecture guide](architecture.md) for the complete trust boundary and the root [security policy](../SECURITY.md) for private vulnerability reporting.
