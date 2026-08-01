# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.3.x   | ✅ Active |

## Reporting a Vulnerability

Report vulnerabilities to security@chatui.dev. Do not open public issues for security concerns.

You should receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible.

## Best Practices

- Do not expose ChatUI directly to the internet without authentication
- Sanitize user input in your `reply()` handler
- Review vendored libraries periodically for CVEs
- Use HTTPS in production (behind a reverse proxy like nginx or Caddy)
