"""Sphinx documentation built against the installed KKRunner distribution."""

import kkrunner

project = "KKRunner"
author = "KKRunner contributors"
release = kkrunner.__version__
version = release
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]
html_theme = "sphinx_rtd_theme"
html_theme_options = {"navigation_depth": 3}
html_title = f"KKRunner {release}"
html_baseurl = "https://ase2sprkkr.github.io/kkrunner/"
html_context = {
    "display_github": True,
    "github_user": "ase2sprkkr",
    "github_repo": "kkrunner",
    "github_version": "develop",
    "conf_py_path": "/docs/",
}
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "remarks/**"]
templates_path = ["_templates"]
autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {"members": True, "undoc-members": True}
# Deliberately do not add src/ to sys.path: CI documents the installed wheel.
