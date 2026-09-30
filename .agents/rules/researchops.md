# ResearchOps Development Rules

These rules govern the development, architecture, testing, and Git hygiene for the ResearchOps project (Team: Spideyx | GATEWAYS 2026).

---

## PROJECT PRINCIPLES

1. Never expose API keys.
2. Never hardcode secrets.
3. Use environment variables.
4. Keep frontend and backend separated.
5. Use FastAPI for backend APIs.
6. Use typed Pydantic schemas for API request/response models.
7. Use async code where appropriate.
8. Keep business logic inside services rather than API route files.
9. Every external API integration must have an abstraction/service layer.
10. Every important research claim must preserve its source URL.
11. Never present unsupported information as verified fact.
12. Conflicting sources must be represented explicitly.
13. Missing information must be represented explicitly.
14. The AI must not fabricate sources.
15. The system is a research and decision-support application, not a medical diagnosis or treatment system.
16. Keep components modular and testable.
17. Add tests for important backend logic.
18. Do not unnecessarily rewrite working code.
19. Before making large architectural changes, inspect the existing architecture.
20. After each major implementation, run tests and verify the application.

---

## CODING STYLE

- Python: PEP8
- JavaScript: modern vanilla JavaScript
- Clear function names
- Type hints
- Small reusable functions
- Meaningful error messages
- No unnecessary dependencies

---

## GIT RULES

- Never commit .env
- Never commit credentials
- Use meaningful commits
- Do not force push
- Do not delete branches without explicit instruction
