# Security Audit

When auditing code for security, apply a systematic methodology inspired by OWASP and Trail of Bits patterns:

## Injection & Input Handling
- Check all user inputs for proper sanitization before use in SQL, shell commands, file paths, or HTML output.
- Verify parameterized queries are used instead of string interpolation for database operations.
- Validate that `subprocess` calls use list arguments, not shell=True with unsanitized input.

## Authentication & Authorization
- Verify authentication is enforced on all sensitive endpoints.
- Check that authorization checks happen on every request, not just at the UI level.
- Look for hardcoded credentials, API keys, or tokens.

## Data Protection
- Ensure secrets are loaded from environment variables or secret stores, never committed to code.
- Check that sensitive data (passwords, tokens) is not logged or included in error messages.
- Verify TLS/HTTPS is enforced for external communications.

## Path & File Safety
- Confirm path traversal protection exists on all file operations (e.g., `resolve()` + `relative_to()`).
- Check that file uploads validate type, size, and filename.

## Dependencies
- Flag known-vulnerable dependency versions when visible in lockfiles.
- Note any dependencies with excessive permissions or unusual install scripts.

Report findings with severity (Critical/High/Medium/Low), affected file:line, and a concrete remediation suggestion.
