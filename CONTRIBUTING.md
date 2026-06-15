# Contributing to AARA

Thanks for your interest in improving AARA. This project is early-stage, so contributions of all sizes — bug reports, documentation improvements, feature implementations — are welcome.

## Getting Started

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/your-feature`)
3. Make your changes
4. Run the test suite
5. Submit a pull request

## Development Setup

See [README.md](README.md#local-development) for full setup instructions.

## Code Standards

### Backend (Python)

- Format with Black (`black .`)
- Sort imports with isort (`isort .`)
- Type hints required for all function signatures
- Async-first for I/O operations (database, HTTP calls)
- Pydantic v2 for all request/response schemas

### Frontend (TypeScript/React)

- Format with Prettier (`npx prettier --write .`)
- Use TypeScript strict mode — no `any` without explicit justification
- Prefer Server Components where possible; use `'use client'` only when needed
- Use Zustand for global state, React state for local state

### Testing

- Backend: `pytest` — new features require tests
- Frontend: `npm run build` must succeed
- Security changes must include test coverage for the specific vulnerability

## Pull Request Process

1. Update the CHANGELOG.md with a description of your change
2. Ensure all tests pass
3. Keep PRs focused — one feature or fix per PR
4. Write a clear PR description explaining the problem and solution

## Reporting Issues

- Bug reports: include steps to reproduce, expected behavior, actual behavior
- Feature requests: describe the problem you're solving, not just the solution
- Security issues: see [SECURITY.md](SECURITY.md) for disclosure process
