# Security

## Reporting a vulnerability

Please do not publish sensitive security issues in a public issue.

Report the issue privately to the repository maintainers with enough detail to reproduce it and identify the affected component.

## Secrets

Never commit:

- Database credentials
- Flask secret keys
- API tokens
- Cloud service credentials
- Local .env files
- Firebase service-account files

Use environment variables for deployment configuration. If a credential is ever committed accidentally, rotate it at the provider before removing it from the working tree.

## Local development

Copy .env.example to .env and provide local or deployment-specific values. The repository should contain only placeholders.
