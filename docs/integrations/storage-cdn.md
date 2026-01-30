# Storage y CDN

## Objetivo

Centralizar assets (logos, comprobantes, etc.) en storage y exponerlos por CDN.

## Componentes

- Storage: Backblaze B2.
- CDN: Cloudflare (o equivalente).

## Consideraciones

- URLs públicas deben ser estables.
- No exponer credenciales en cliente.
- Cache-control consistente.
