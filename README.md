# Python

A collection of small Python projects, written as a learning exercise to build fluency in the language. Each subdirectory is a self-contained tool with its own requirements and docs.

## Projects

| Project | What it does | Status |
| --- | --- | --- |
| [`brewery-scraper/`](brewery-scraper/) | CLI tool that fetches the Brewers Association JSON dataset, normalizes it into Pydantic `Brewery` models, classifies it, and exports JSON stats and diagnostic reports. | Most developed — full test suite, docs, and lint setup. See its [README](brewery-scraper/README.md). |
| [`FolderCleanup/`](FolderCleanup/) | `argparse` CLI that recursively deletes files older than a given age (in days) under a target path, with optional readonly handling (`-f`) and empty-folder removal (`-e`). A Python rework of an earlier PowerShell script. | Working script. |
| [`Quiz/`](Quiz/) | Interactive console quiz app (PyQuiz) that loads `QuizML` XML question banks from `Quiz/Quizzes/` (multi-choice and true/false), lets you pick a quiz, and optionally saves results. | Early, learning-stage. |

## Working in this repo

- Every project is standalone — there is no monorepo tooling or shared config. `cd` into a project directory to work in it.
- `brewery-scraper/` has a `.venv/`, `requirements(-dev).txt`, a pytest suite, and ruff, and is the only one with automated tests. Follow [AGENTS.md](AGENTS.md) for its exact commands and gotchas.
- `FolderCleanup/` and `Quiz/` are single-script experiments with no packaging or tests; run their entry points directly (e.g. `python FolderCleanup/foldercleanup.py --path ... --age ...`).
- `py -m venv` / `virtualenv` and the usual editor/cache artifacts are gitignored at the root (see `.gitignore`).

## License

GNU GPL v3 — see [LICENSE](LICENSE).
