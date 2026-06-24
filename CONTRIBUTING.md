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

## Pull Request Guidelines

- Keep pull requests focused on a single change where possible to make review easier.
- Add or update tests for any behavior you change.
- Update relevant documentation (README, docstrings, SLURM script comments) alongside code changes.
- Be ready to discuss and iterate on feedback. Ccode review is a normal and friendly part of the process.

## Code of Conduct

Be respectful and constructive. We want ProtPen to be a welcoming project for contributors of all backgrounds and experience levels.

## Contributors

- Diya Mathai
- Stefan Schulze

Want to see your name here? Open a pull request!
