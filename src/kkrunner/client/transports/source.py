"""Validate and extract explicit function dependencies for source delivery."""

from __future__ import annotations

import ast
import dis
import inspect
import textwrap
import types


def function_definition(fn, *, static=False, name=None):
    """Extract a function and its explicitly declared source dependencies.

    Each dependency is emitted once, before its users. Cycles, ambiguous names
    and undeclared globals are errors. No module namespace is copied.
    """
    emitted = {}
    visiting = set()
    definitions = []

    def visit(function, *, static=False, name=None):
        if not inspect.isfunction(function):
            raise TypeError("Remote operation must be a top-level Python function")
        binding = name or function.__name__
        if function in visiting:
            raise TypeError("Cyclic remote source dependencies")
        if binding in emitted:
            if emitted[binding] is not function:
                raise TypeError(f"Conflicting remote dependency name: {binding}")
            return
        emitted[binding] = function
        dependencies = getattr(function, "__source_dependencies__", ())
        bindings = {}
        visiting.add(function)
        for dependency in dependencies:
            if not inspect.isfunction(dependency):
                raise TypeError("Remote source dependencies must be Python functions")
            dependency_name = dependency.__name__
            if function.__globals__.get(dependency_name) is not dependency:
                raise TypeError(f"Dependency must be bound as {dependency_name}")
            bindings[dependency_name] = dependency
            visit(dependency)
        definitions.append((function, static, name, bindings))
        visiting.remove(function)

    visit(fn, static=static, name=name)
    return "".join(_function_definition(
        function, static=static, name=name, dependencies=bindings, namespace_names=emitted,
    ) for function, static, name, bindings in definitions)


def _function_definition(fn, *, static=False, name=None, dependencies, namespace_names):
    """Extract one function, checking its explicit dependencies.

    Functions may import only target-available modules inside their own body.
    Nonlocal state and module-level referenced objects are rejected rather
    than implicitly copied across the client/target boundary. ``name`` can
    bind an internal bootstrap under a name distinct from the operation.
    """
    if not inspect.isfunction(fn) or (not static and fn.__qualname__ != fn.__name__):
        raise TypeError("Remote operation must be a top-level Python function")
    if fn.__closure__:
        raise TypeError("Remote operation must not depend on module globals or closures")

    def globals_used(code):
        instructions = tuple(dis.get_instructions(code))
        for index, instruction in enumerate(instructions):
            if instruction.opname == "LOAD_NAME" and instruction.argval == "__name__":
                # Class bodies implicitly set __module__ from the interpreter
                # namespace. This compiler-generated metadata is portable;
                # explicit global references in methods remain forbidden.
                following = instructions[index + 1] if index + 1 < len(instructions) else None
                if following is not None and following.opname == "STORE_NAME" and following.argval == "__module__":
                    continue
            if instruction.opname in ("LOAD_GLOBAL", "LOAD_NAME"):
                yield instruction.argval
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                yield from globals_used(constant)

    # Attribute names and function-local imports are not global references.
    # Walk nested code too: a callback may hide a dependency on the client.
    if any((name in fn.__globals__ or name in namespace_names) and name not in dependencies
           for name in globals_used(fn.__code__)):
        raise TypeError("Remote operation must not depend on module globals or closures")
    source = textwrap.dedent(getattr(fn, "__source__", None) or inspect.getsource(fn))
    node = ast.parse(source).body[0]
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise TypeError("Remote operation must be a Python function")
    node.decorator_list = [
        decorator for decorator in node.decorator_list
        if not (
            static and isinstance(decorator, ast.Name) and decorator.id == "staticmethod"
            or hasattr(fn, "__source_dependencies__") and isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Name) and decorator.func.id == "depends_on"
        )
    ]
    if node.decorator_list:
        raise TypeError("Remote operation must be an undecorated function")
    # Type annotations describe the client API, not dependencies of the target
    # implementation. Erase them from the actual syntax tree; keep the same
    # function body rather than maintaining a separate remote implementation.
    node.returns = None
    for parameter in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs,
                      node.args.vararg, node.args.kwarg):
        if parameter is not None:
            parameter.annotation = None
    for default in (*node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)):
        try:
            ast.literal_eval(default)
        except (ValueError, TypeError, SyntaxError) as exc:
            raise TypeError("Portable defaults must be literal values") from exc

    if name is not None:
        node.name = name
    return ast.unparse(node) + "\n"
