"""Convert a Gitingest digest.txt file into Neo4j-friendly CSVs (v2).

Key changes from v1
-------------------
1. Emits *separate* CSVs for each relationship type (`contains.csv`, `inherits.csv`, `calls.csv`).
   This avoids the dynamic-type import issue that caused `{row.rel_type}` edges.
2. Writes a helper `import.cypher` file with ready-to-run Cypher statements for `cypher-shell` or
   Neo4j Browser.

Usage
-----
    python digest_to_neo4j.py digest.txt output_dir

Files created in ``output_dir``
    nodes.csv        – flat list of nodes (id,label,name,path,lineno)
    contains.csv     – start_id,end_id (file→member and class→method)
    inherits.csv     – start_id,end_id (class→superclass)
    calls.csv        – start_id,end_id (caller→callee)
    import.cypher    – Cypher script to load everything

Import (inside Neo4j) – two options
1. Via cypher-shell on host:
    docker exec -i neo4j cypher-shell -u neo4j -p <pwd> -f /import/import.cypher

2. Copy-paste the content of import.cypher into the Browser.

Requirements
------------
• Standard library only.
"""

from __future__ import annotations

import ast
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

FILE_SPLIT_RE = re.compile(r"^={3,}\nFILE: (.+?)\n={3,}$")

REL_FILES = {
    "CONTAINS": "contains.csv",
    "INHERITS": "inherits.csv",
    "CALLS": "calls.csv",
}


class Context:
    """Collect nodes and per-type relationships."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, str]] = {}
        self.rels: Dict[str, List[Tuple[str, str]]] = {rt: [] for rt in REL_FILES}

    # ---------------------------------------------------------------------
    # Nodes & relationships helpers
    # ---------------------------------------------------------------------

    def add_node(self, node_id: str, label: str, **props: str | int | None) -> None:
        if node_id in self.nodes:
            return
        rec: Dict[str, str] = {"id": node_id, "label": label}
        for k, v in props.items():
            if v is not None:
                rec[k] = str(v)
        self.nodes[node_id] = rec

    def add_rel(self, start: str, end: str, rel_type: str) -> None:
        if rel_type not in self.rels:
            self.rels[rel_type] = []
        self.rels[rel_type].append((start, end))


# -------------------------------------------------------------------------
# Digest parsing
# -------------------------------------------------------------------------

def iter_file_chunks(digest_path: Path):
    current: str | None = None
    buf: List[str] = []
    with digest_path.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if line.startswith("FILE: "):
                if current is not None:
                    yield current, "\n".join(buf)
                current = line[len("FILE: "):].strip()
                buf = []
                continue
            # skip separator lines made of '=' chars
            if set(line) == {"="}:  # line is all '='
                continue
            if current is not None:
                buf.append(raw.rstrip("\n"))
    if current is not None and buf:
        yield current, "\n".join(buf)


# -------------------------------------------------------------------------
# AST processing
# -------------------------------------------------------------------------

def qual_name(stack: List[str], name: str) -> str:
    return ".".join(stack + [name])


def process_ast(ctx: Context, file_id: str, source: str):
    try:
        tree = ast.parse(source, filename=file_id)
    except SyntaxError:
        return

    stack: List[str] = []

    def visit(node: ast.AST):
        nonlocal stack
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            qname = qual_name(stack, node.name)
            label = "Class" if isinstance(node, ast.ClassDef) else "Function"
            ctx.add_node(qname, label, name=node.name, path=file_id, lineno=node.lineno)
            parent = file_id if not stack else qual_name(stack[:-1], stack[-1])
            ctx.add_rel(parent, qname, "CONTAINS")

            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        ctx.add_rel(qname, base.id, "INHERITS")

            stack.append(node.name)
            for child in ast.iter_child_nodes(node):
                visit(child)
            stack.pop()
            return

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            caller = qual_name(stack[:-1], stack[-1]) if stack else file_id
            ctx.add_rel(caller, node.func.id, "CALLS")

        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)


# -------------------------------------------------------------------------
# CSV + Cypher output
# -------------------------------------------------------------------------

def write_output(ctx: Context, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # nodes.csv
    node_fields = sorted({k for n in ctx.nodes.values() for k in n})
    with (out_dir / "nodes.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=node_fields)
        wr.writeheader()
        wr.writerows(ctx.nodes.values())

    # relationship csvs
    for rel_type, rows in ctx.rels.items():
        csv_name = REL_FILES[rel_type]
        with (out_dir / csv_name).open("w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["start_id", "end_id"])
            wr.writerows(rows)

    # generate import.cypher
    cypher_lines = [
        '// Run this in cypher-shell or Browser (adjust user/password as needed)\n',
        "LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row\n",
        "MERGE (n:Entity {id: row.id}) SET n += row;\n\n",
    ]
    for rel_type, csv_name in REL_FILES.items():
        cypher_lines += [
            f"LOAD CSV WITH HEADERS FROM 'file:///{csv_name}' AS row\n",
            "MATCH (a:Entity {id: row.start_id})\n",
            "MATCH (b:Entity {id: row.end_id})\n",
            f"MERGE (a)-[:{rel_type}]->(b);\n\n",
        ]
    (out_dir / "import.cypher").write_text("".join(cypher_lines), encoding="utf-8")

    print(f"Written {len(ctx.nodes)} nodes and relationships to {out_dir}")


# -------------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------------

def main():  # pragma: no cover
    if len(sys.argv) < 3:
        print("Usage: python digest_to_neo4j.py digest.txt output_dir")
        sys.exit(1)

    digest_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    if not digest_path.exists():
        sys.exit(f"Digest not found: {digest_path}")

    ctx = Context()

    for file_path, code in iter_file_chunks(digest_path):
        ctx.add_node(file_path, "File", name=Path(file_path).name, path=file_path)
        if file_path.endswith(".py"):
            process_ast(ctx, file_path, code)

    write_output(ctx, out_dir)


if __name__ == "__main__":
    main() 