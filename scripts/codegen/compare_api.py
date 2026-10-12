#!/usr/bin/env python
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Compare two generated API modules, for example the committed
`playwright/async_api/_generated.py` and a freshly generated one.

The files are parsed, not imported. For every class and member the tool
compares what users can see and what the generated code does:

- base classes, member names, member kind (property, def, async def);
- positional parameters (names, order, defaults);
- keyword-only parameters (names and defaults; the order is reported
  separately, because it is allowed to differ);
- every annotation and the return annotation, after normalization
  (unions are flattened and sorted, Optional[X] is Union[X, None],
  quotes are removed, Literal values are sorted and merged);
- the body: the call into the implementation, with keyword arguments sorted;
- docstrings (reported separately; they are allowed to differ);
- for TypedDicts (`playwright/_impl/_api_structures.py`): `total=`, the field
  names and the field annotations (the field order is reported separately,
  because it is allowed to differ).

Exit code is 1 if any difference outside the allowed kinds is found.
"""

import argparse
import ast
import difflib
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

ALLOWED_KINDS = {"kwonly-order", "docstring", "member-inherited", "field-order"}


@dataclass
class Param:
    name: str
    annotation: str
    default: Optional[str]


@dataclass
class Func:
    name: str
    is_async: bool
    decorators: List[str]
    positional: List[Param]
    kwonly: List[Param]
    returns: str
    docstring: Optional[str]
    body: str


@dataclass
class Klass:
    name: str
    bases: List[str]
    keywords: List[str] = field(default_factory=list)
    members: Dict[str, Func] = field(default_factory=dict)
    fields: Dict[str, str] = field(default_factory=dict)


def _strip_typing(name: str) -> str:
    return re.sub(r"^typing\.", "", name)


def _union_members(node: Optional[ast.AST]) -> List[Optional[ast.AST]]:
    if node is None:
        return [None]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        try:
            return _union_members(ast.parse(node.value, mode="eval").body)
        except SyntaxError:
            return [node]
    if isinstance(node, ast.Constant) and node.value is None:
        return [None]
    if isinstance(node, ast.Subscript):
        base = _strip_typing(ast.unparse(node.value))
        args = (
            list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
        )
        if base == "Union":
            result: List[Optional[ast.AST]] = []
            for arg in args:
                result.extend(_union_members(arg))
            return result
        if base == "Optional":
            return _union_members(args[0]) + [None]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _union_members(node.left) + _union_members(node.right)
    return [node]


def canon(node: Optional[ast.AST]) -> str:
    """Normalized text of an annotation."""
    if node is None:
        return "None"
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            try:
                return canon(ast.parse(node.value, mode="eval").body)
            except SyntaxError:
                return repr(node.value)
        return "None" if node.value is None else repr(node.value)
    if isinstance(node, (ast.Name, ast.Attribute)):
        return _strip_typing(ast.unparse(node))
    if isinstance(node, ast.Subscript):
        base = _strip_typing(ast.unparse(node.value))
        args = (
            list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
        )
        if base == "Literal":
            values = sorted(
                repr(a.value) if isinstance(a, ast.Constant) else ast.unparse(a)
                for a in args
            )
            return f"Literal[{', '.join(values)}]"
        if base in ("Union", "Optional"):
            return _canon_union(_union_members(node))
        return f"{base}[{', '.join(canon(a) for a in args)}]"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _canon_union(_union_members(node))
    if isinstance(node, ast.List):
        return f"[{', '.join(canon(a) for a in node.elts)}]"
    return ast.unparse(node)


def _canon_union(members: List[Optional[ast.AST]]) -> str:
    items: Set[str] = set()
    literals: Set[str] = set()
    for member in members:
        text = canon(member)
        match = re.match(r"^Literal\[(.*)\]$", text)
        if match:
            literals.update(v.strip() for v in match.group(1).split(", "))
        else:
            items.add(text)
    if literals:
        items.add(f"Literal[{', '.join(sorted(literals))}]")
    ordered = sorted(items, key=lambda i: "~" if i == "None" else i)
    if len(ordered) == 1:
        return ordered[0]
    return f"Union[{', '.join(ordered)}]"


class _SortKeywords(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        node.keywords.sort(key=lambda k: k.arg or "")
        return node


def _body_text(func: ast.AST) -> str:
    assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
    statements = list(func.body)
    if (
        statements
        and isinstance(statements[0], ast.Expr)
        and isinstance(statements[0].value, ast.Constant)
        and isinstance(statements[0].value.value, str)
    ):
        statements = statements[1:]
    returns_none = func.returns is not None and ast.unparse(func.returns) == "None"
    text = []
    for statement in statements:
        # In a function that returns None, `return mapping.from_maybe_impl(X)`
        # and a plain `X` do the same thing.
        if (
            returns_none
            and isinstance(statement, ast.Return)
            and isinstance(statement.value, ast.Call)
            and ast.unparse(statement.value.func) == "mapping.from_maybe_impl"
            and len(statement.value.args) == 1
        ):
            statement = ast.Expr(statement.value.args[0])
        statement = _SortKeywords().visit(ast.parse(ast.unparse(statement)))
        text.append(ast.unparse(statement))
    return "\n".join(text)


def _params(args: ast.arguments) -> Tuple[List[Param], List[Param]]:
    positional_nodes = [*args.posonlyargs, *args.args]
    defaults: List[Optional[ast.expr]] = [None] * (
        len(positional_nodes) - len(args.defaults)
    ) + list(args.defaults)
    positional = []
    for arg, default in zip(positional_nodes, defaults):
        if arg.arg == "self":
            continue
        positional.append(
            Param(
                arg.arg,
                canon(arg.annotation) if arg.annotation else "",
                ast.unparse(default) if default is not None else None,
            )
        )
    kwonly = []
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults):
        kwonly.append(
            Param(
                arg.arg,
                canon(arg.annotation) if arg.annotation else "",
                ast.unparse(kw_default) if kw_default is not None else None,
            )
        )
    return positional, kwonly


def _member_key(func: ast.AST, decorators: List[str]) -> str:
    assert isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef))
    if "typing.overload" not in decorators:
        return func.name
    # Overloads are keyed by the annotation of their first parameter, which is
    # the event name literal in all overloads we generate.
    args = [a for a in func.args.args if a.arg != "self"]
    first = canon(args[0].annotation) if args and args[0].annotation else ""
    return f"{func.name}@overload({first})"


def load(path: str) -> Dict[str, Klass]:
    with open(path, encoding="utf-8") as f:
        module = ast.parse(f.read())
    classes: Dict[str, Klass] = {}
    for node in module.body:
        if not isinstance(node, ast.ClassDef):
            continue
        klass = Klass(
            node.name,
            [ast.unparse(b) for b in node.bases],
            [ast.unparse(k) for k in node.keywords],
        )
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                klass.fields[item.target.id] = canon(item.annotation)
                continue
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorators = [ast.unparse(d) for d in item.decorator_list]
            positional, kwonly = _params(item.args)
            func = Func(
                name=item.name,
                is_async=isinstance(item, ast.AsyncFunctionDef),
                decorators=decorators,
                positional=positional,
                kwonly=kwonly,
                returns=canon(item.returns) if item.returns else "",
                docstring=ast.get_docstring(item, clean=True),
                body=_body_text(item),
            )
            klass.members[_member_key(item, decorators)] = func
        classes[node.name] = klass
    return classes


@dataclass
class Difference:
    kind: str
    where: str
    old: str
    new: str


def _signature_text(params: List[Param]) -> str:
    return ", ".join(
        f"{p.name}: {p.annotation}" + (f" = {p.default}" if p.default else "")
        for p in params
    )


def compare_funcs(where: str, old: Func, new: Func, out: List[Difference]) -> None:
    if old.is_async != new.is_async:
        out.append(
            Difference(
                "async",
                where,
                "async" if old.is_async else "def",
                "async" if new.is_async else "def",
            )
        )
    if sorted(old.decorators) != sorted(new.decorators):
        out.append(
            Difference("decorators", where, str(old.decorators), str(new.decorators))
        )
    old_pos = [(p.name, p.annotation, p.default) for p in old.positional]
    new_pos = [(p.name, p.annotation, p.default) for p in new.positional]
    if [p[0] for p in old_pos] != [p[0] for p in new_pos]:
        out.append(
            Difference(
                "positional",
                where,
                _signature_text(old.positional),
                _signature_text(new.positional),
            )
        )
    else:
        for o, n in zip(old.positional, new.positional):
            if o.annotation != n.annotation:
                out.append(
                    Difference(
                        "annotation", f"{where}({o.name}=)", o.annotation, n.annotation
                    )
                )
            if o.default != n.default:
                out.append(
                    Difference(
                        "default", f"{where}({o.name}=)", str(o.default), str(n.default)
                    )
                )
    old_kw = {p.name: p for p in old.kwonly}
    new_kw = {p.name: p for p in new.kwonly}
    if set(old_kw) != set(new_kw):
        out.append(
            Difference(
                "kwonly",
                where,
                ", ".join(sorted(set(old_kw) - set(new_kw))) or "-",
                ", ".join(sorted(set(new_kw) - set(old_kw))) or "-",
            )
        )
    elif [p.name for p in old.kwonly] != [p.name for p in new.kwonly]:
        out.append(
            Difference(
                "kwonly-order",
                where,
                ", ".join(p.name for p in old.kwonly),
                ", ".join(p.name for p in new.kwonly),
            )
        )
    for name in sorted(set(old_kw) & set(new_kw)):
        o, n = old_kw[name], new_kw[name]
        if o.annotation != n.annotation:
            out.append(
                Difference(
                    "annotation", f"{where}({name}=)", o.annotation, n.annotation
                )
            )
        if o.default != n.default:
            out.append(
                Difference(
                    "default", f"{where}({name}=)", str(o.default), str(n.default)
                )
            )
    if old.returns != new.returns:
        out.append(Difference("return", where, old.returns, new.returns))
    if old.body != new.body:
        out.append(Difference("body", where, old.body, new.body))
    if (old.docstring or "") != (new.docstring or ""):
        out.append(
            Difference("docstring", where, old.docstring or "", new.docstring or "")
        )


def _inherited(classes: Dict[str, Klass], klass: Klass, member: str) -> Optional[Func]:
    for base in klass.bases:
        if base not in classes:
            continue
        if member in classes[base].members:
            return classes[base].members[member]
        found = _inherited(classes, classes[base], member)
        if found:
            return found
    return None


def compare_fields(
    where: str, old: Dict[str, str], new: Dict[str, str], out: List[Difference]
) -> None:
    for name in old:
        if name not in new:
            out.append(Difference("field-missing", f"{where}.{name}", old[name], "-"))
        elif old[name] != new[name]:
            out.append(
                Difference("field-type", f"{where}.{name}", old[name], new[name])
            )
    for name in new:
        if name not in old:
            out.append(Difference("field-extra", f"{where}.{name}", "-", new[name]))
    common_old = [n for n in old if n in new]
    common_new = [n for n in new if n in old]
    if common_old != common_new:
        out.append(
            Difference(
                "field-order", where, ", ".join(common_old), ", ".join(common_new)
            )
        )


def compare(old: Dict[str, Klass], new: Dict[str, Klass]) -> List[Difference]:
    out: List[Difference] = []
    for name in sorted(set(old) - set(new)):
        out.append(Difference("class-missing", name, name, "-"))
    for name in sorted(set(new) - set(old)):
        out.append(Difference("class-extra", name, "-", name))
    for name in sorted(set(old) & set(new)):
        o, n = old[name], new[name]
        if o.bases != n.bases:
            out.append(Difference("bases", name, str(o.bases), str(n.bases)))
        if o.keywords != n.keywords:
            out.append(Difference("keywords", name, str(o.keywords), str(n.keywords)))
        compare_fields(name, o.fields, n.fields, out)
        for member in sorted(set(o.members) - set(n.members)):
            inherited = _inherited(new, n, member)
            if inherited:
                details: List[Difference] = []
                compare_funcs(name, o.members[member], inherited, details)
                if all(d.kind == "docstring" for d in details):
                    out.append(
                        Difference("member-inherited", f"{name}.{member}", member, "-")
                    )
                    continue
            out.append(Difference("member-missing", f"{name}.{member}", member, "-"))
        for member in sorted(set(n.members) - set(o.members)):
            out.append(Difference("member-extra", f"{name}.{member}", "-", member))
        for member in sorted(set(o.members) & set(n.members)):
            compare_funcs(f"{name}.{member}", o.members[member], n.members[member], out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("old", help="reference file, for example the committed one")
    parser.add_argument("new", help="file to check")
    parser.add_argument(
        "--show",
        action="append",
        default=[],
        help="print the details of this kind of difference (repeatable; 'all' for every kind)",
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="KIND:WHERE",
        help="accept one reviewed difference, for example 'body:Browser.new_context' (repeatable)",
    )
    args = parser.parse_args()

    differences = compare(load(args.old), load(args.new))
    allowed = set(args.allow)
    unused_allows = set(allowed)
    by_kind: Dict[str, List[Difference]] = {}
    for d in differences:
        key = f"{d.kind}:{d.where}"
        if key in allowed:
            unused_allows.discard(key)
            by_kind.setdefault("accepted", []).append(d)
            continue
        by_kind.setdefault(d.kind, []).append(d)
    for key in sorted(unused_allows):
        print(f"--allow {key} matched nothing")
    ALLOWED_KINDS.add("accepted")

    show_all = "all" in args.show
    for kind in sorted(by_kind):
        items = by_kind[kind]
        note = " (allowed)" if kind in ALLOWED_KINDS else ""
        print(f"{kind}: {len(items)}{note}")
        if not show_all and kind not in args.show:
            continue
        for d in items:
            if kind == "docstring":
                print(f"  {d.where}:")
                for line in difflib.unified_diff(
                    d.old.splitlines(), d.new.splitlines(), lineterm="", n=0
                ):
                    if line.startswith(("---", "+++", "@@")):
                        continue
                    print(f"      {line}")
            else:
                print(f"  {d.where}")
                print(f"      old: {d.old}")
                print(f"      new: {d.new}")

    failing = [k for k in by_kind if k not in ALLOWED_KINDS]
    if failing:
        print(f"FAIL: unexpected differences: {', '.join(sorted(failing))}")
        return 1
    print("OK: no unexpected differences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
