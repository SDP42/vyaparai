# Contributing

## Workflow

1. Pick an item from [docs/PHASES.md](docs/PHASES.md) and open or claim an issue.
2. Branch from `main`: `feat/<phase>-<short-name>`, `fix/<short-name>`, `docs/<short-name>`.
3. Commit small and often using [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(api): …`, `fix(web): …`, `test(api): …`, `docs: …`, `chore: …`, `refactor: …`.
4. Run checks locally with `make lint test`.
5. Open a PR using the template, then update [ROADMAP.md](docs/ROADMAP.md), [DEVLOG.md](docs/DEVLOG.md)
   and [CHANGELOG.md](CHANGELOG.md).

## Definition of done

Implemented · tested · documented · demonstrable. Record assumptions and known limitations
instead of hiding them. A screen backed by mocked data is not a finished feature.

## Backend conventions

- Route handlers stay thin. Business logic goes in `services/`, queries in `repositories/`.
- Every tenant-owned table has `workspace_id`; add a tenancy test for every new resource.
- Money is `Decimal`/`Numeric`, never float.
- After changing models, run `uv run alembic revision --autogenerate -m "…"`, review the migration and commit it.

## Frontend conventions

- Colours, fonts and easings come from tokens in `app/globals.css`. Avoid one-off hex values.
- Keep essential text in HTML, never inside the canvas.
- Every animation needs a reduced-motion path.
