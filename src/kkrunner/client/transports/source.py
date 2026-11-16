"""Extract explicitly marked portable function sources for SSH delivery.

Only the @portable marker is checked at runtime. Validation of source
dependencies, globals and defaults belongs in the direct-backend tests.
"""

from __future__ import annotations

import ast
import inspect
import textwrap


def function_definition(fn, *, static=False, name=None):
    """Assemble an explicitly marked function and its declared dependencies.

    Dependencies are emitted before their users. Source extraction is not
    responsible for verifying portability (which the tests enforce).
    """
    emitted = {}
    visiting = set()
    definitions = []

    def visit(function, *, name=None):
        if not getattr(function, "__kkrunner_portable__", False):
            raise TypeError("Remote operation must be marked with @portable")
        binding = name or function.__name__
        if function in visiting:
            raise TypeError("Cyclic remote source dependencies")
        if binding in emitted:
            if emitted[binding] is not function:
                raise TypeError(f"Conflicting remote dependency name: {binding}")
            return
        emitted[binding] = function
        visiting.add(function)
        for dependency in getattr(function, "__source_dependencies__", ()):
            visit(dependency)
        definitions.append((function, name))
        visiting.remove(function)

    visit(fn, name=name)
    return "".join(_function_definition(function, name=binding)
                   for function, binding in definitions)


def _function_definition(fn, *, name=None):
    """Extract source, erasing client-side decorators and annotations."""
    source = textwrap.dedent(getattr(fn, "__source__", None) or inspect.getsource(fn))
    node = ast.parse(source).body[0]
    # Client-side decorators have no meaning on the target. Tests reject
    # unsupported ones, avoiding the need to validate on every operation.
    node.decorator_list = []
    node.returns = None
    for parameter in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs,
                      node.args.vararg, node.args.kwarg):
        if parameter is not None:
            parameter.annotation = None
    if name is not None:
        node.name = name
    return ast.unparse(node) + "\n"
