# Contributing to ProtPen

Thanks for your interest in ProtPen! This project is a community effort, and contributions of any size — bug fixes, documentation tweaks, new tools, or entirely new pipeline modules — are very welcome, whether you're a first-time contributor or a regular.

## Ways to Contribute

- **Report bugs or request features**: please use the [Issues](../../issues) tab. Include enough detail (input data, command run, error message, environment) for others to reproduce the problem.
- **Improve documentation**: fixes to the README, this file, or inline code comments are always appreciated.
- **Add a new tool or module**: ProtPen is designed as a [modular pipeline](README.md#modular-design-and-extensibility), and we'd love to see it grow. New annotation tools, structure search methods, or enrichment steps are a great fit. For more information, see [Adding a New Module](#adding-a-new-module) below.
- **Fix bugs or improve existing code**: pull requests for open issues are very welcome.

No contribution is too small — even a typo fix is appreciated.

## Adding a New Module

Because each pipeline step communicates only through file-based inputs/outputs (mainly TSV and FASTA), adding a new tool doesn't require touching the rest of the codebase. A new module should generally:

- Live in its own file under `protpen/` (e.g. `my_tool.py`), with a corresponding `cli_my_tool.py` wrapper exposing a command-line interface.
- Accept and produce standardized file formats consistent with the rest of the pipeline.
- Include unit tests under `tests/`.
- Be documented in the README's [Scripts](README.md#scripts) table and [Pipeline Workflow](README.md#pipeline-workflow) section.

If you're not sure whether an idea fits, feel free to open an issue to discuss it first.

## Tests and Coding Style

Install the test/dev dependencies first:

```bash
pip install -e ".[test]"
```

**Tests** are written with `pytest` and live under `tests/`. Run the suite with:

```bash
pytest tests/ --ignore=tests/test_eggnog.py --ignore=tests/test_foldseek.py
```

`test_eggnog.py` and `test_foldseek.py` are excluded because they require EggNOG-mapper and Foldseek to be installed locally; CI runs the same exclusion (see [`.github/workflows/tests.yml`](.github/workflows/tests.yml)). If your change touches `eggnog.py` or `foldseek.py`, please also run those two files' tests locally if you have the tools installed.

**Coding style** is enforced with [`black`](https://black.readthedocs.io/). Format your changes before opening a PR:

```bash
black protpen/ tests/
```

CI checks formatting with `black --check protpen/ tests/` and will fail if any file isn't formatted — make sure to run `black` locally first.

## Pull Request Guidelines

- Keep pull requests focused on a single change where possible to make review easier.
- Add or update tests for any behavior you change, and make sure tests pass and code is formatted (see [Tests and Coding Style](#tests-and-coding-style) above) — CI checks both on every PR.
- Update relevant documentation (README, docstrings, SLURM script comments) alongside code changes.
- Be ready to discuss and iterate on feedback. Code review is a normal and friendly part of the process.

## Code of Conduct

Be respectful and constructive. We want ProtPen to be a welcoming project for contributors of all backgrounds and experience levels.

## Contributors

- Diya Mathai
- Stefan Schulze

Want to see your name here? Open a pull request!
