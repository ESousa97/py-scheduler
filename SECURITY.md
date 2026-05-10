# Security policy

## Supported versions

Security updates are applied to the **latest minor release** on the default branch (`main`). Older tags may not receive backports unless explicitly agreed with maintainers.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for undisclosed security vulnerabilities.

Instead, report sensitive issues privately so they can be handled responsibly:

1. Use **GitHub Security Advisories** for this repository (**Security** tab → **Report a vulnerability**), if enabled; or
2. Contact the maintainer via the channels linked on their GitHub profile, with enough detail to reproduce and assess impact.

Include:

- A clear description of the issue and affected components
- Steps to reproduce (proof-of-concept if safe to share)
- Potential impact (confidentiality, integrity, availability)
- Suggested fix or mitigation (optional)

You should receive an initial acknowledgement within a reasonable timeframe. Maintainers may coordinate disclosure (for example CVE assignment or release notes) once a fix is available.

## Scope

In scope: the **py-scheduler** codebase as shipped in this repository (CLI, library, Docker image defaults). Out of scope: vulnerabilities in third-party dependencies unless they affect this project’s usage in a material way—those should also be reported upstream.
