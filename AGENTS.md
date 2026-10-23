# Completion contract

- Implement only the requested task. Do not advance to the next task or sprint without instruction. Use relevant installed skills and read only relevant files.
- Follow [ADR-001](docs/architecture/ADR-001.md) and the [MVP](docs/requirements/MVP.md): original Arabic RTL clinic system, one Neurology & Psychiatry doctor, React + TypeScript, FastAPI, PostgreSQL. Doctor PC hosts the application and sole database; receptionist PC is browser-only; deployed LAN traffic uses HTTPS. No extra server machines, microservices or cloud services.
- Keep frontend-to-backend integration real. No fake buttons, counters, endpoints or mock data in live UI. Use synthetic data only; mock fixtures belong only in tests.
- Never read out, commit or upload `.env`, secret keys, credentials or patient data. Any future `.env.example` must contain placeholders only. Follow the ADR secrets strategy.
- Enforce independent doctor/receptionist authentication and permissions in the API, including field-level responses. UI visibility and PC identity are not authorization. Receptionists cannot read clinical notes, diagnoses or prescriptions.
- Use versioned Alembic migrations. Never use `create_all()` as production migration management. Do not run destructive migrations, delete user data or deploy to external machines without approval; complete safe local work and report blockers precisely.
- Add meaningful tests according to risk. Run actual relevant checks and report PASS / FAIL / NOT TESTED with exact commands and evidence. Missing browser or Windows execution means NOT TESTED.
- Update [STATUS](docs/STATUS.md) and a short report in `docs/tasks/` listing changed files, checks, known risks and exact run steps. Continue until this task's acceptance criteria pass or blockers are precisely recorded.
- End with a commit or explicit checkpoint and the next task ID. Do not claim unexecuted tests, deployment or reference workflows as verified.
