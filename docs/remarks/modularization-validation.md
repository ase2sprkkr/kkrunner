# Subpackages and documentation validation — 8 November 2026

Development evidence only; this note is not the public manual or a release guarantee.

- Wheel built from an isolated sdist build and installed without ASE or PSI/J.
- Complete unpacked-sdist suite: 714 passed, 3 optional Docker cases skipped.
- Actual installed-wheel SSH/Slurm Docker integrations: 3 passed.
- Installed-wheel smoke: raw execution, supervised reconnect, remote executable,
  recursive module imports and both console scripts passed without source PYTHONPATH.
- Sphinx HTML with warnings as errors and executable guide examples passed.
- ASE2SPRKKR execution/sprkkr groups plus file-provenance tests: 368 passed, 4 skipped.
- Selected Guy4ASE persistence/API groups: 22 passed, 1 failed. The identical
  SPLEED-versus-ARPES assertion reproduces on the unchanged original checkouts.
- Ruff runtime/test checks and formatting passed; metadata and pip check passed.
- Python 3.14 host and Python 3.12 Docker; hosted CI has not been run.
- The new ASE execution guide builds as a standalone Sphinx/RtD preview without
  warnings. This is not a claim that all historical ASE documentation builds cleanly.

Evidence: /tmp/kkrunner-docs-7_6th5f4/. Documentation content remains a draft
pending the user's requested approval. No source push or Pages/PyPI publication.

Documentation content approved by the user on 8 November 2026, with checkout
paths replaced by the quoted `<path-to-kkrunner>` placeholder. No publication
was performed. This documentation correction does not change runtime behavior.
