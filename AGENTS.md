# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

DeepIntoPep is a documentation/educational project about Python Enhancement Proposals (PEPs). The main deliverable is a PDF generated from Markdown files using `reportlab`.

### Key commands

- **Build PDF**: `python3 scripts/build_pdf.py` (from repo root)
  - Reads `README.md` + `LICENSE` → writes `docs/DeepIntoPep.pdf`
  - Supports `--input`, `--output`, `--title` flags

### Dependencies

- **Python 3.10+** (uses `str | None` union syntax)
- **`reportlab`** (pip package, the only runtime dependency)
- **CJK font** (`fonts-wqy-microhei` apt package) for proper Chinese character rendering in PDF output. Without it, the script falls back to Helvetica and CJK text won't render correctly.

### Notes

- There are no automated tests, no linter config, and no CI in this repo. The "test" for correctness is running `python3 scripts/build_pdf.py` and verifying the PDF is generated without errors.
- The generated PDF at `docs/DeepIntoPep.pdf` is committed to the repo. After rebuilding, check `git diff` to see if content changed.
- The script resolves `repo_root` as `Path(__file__).resolve().parents[1]`, so it must be run from within the repo structure (the working directory doesn't matter).
