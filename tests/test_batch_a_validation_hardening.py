from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
def source(n):return (ROOT/n).read_text(encoding="utf-8")
def test_sources_parse():
 for n in ("draft_health_routes.py","draft_operations_hardening.py","draft_readiness.py","draft_state_hardening.py"):ast.parse(source(n),filename=n)
def test_publication_gate():
 t=ast.parse(source("draft_readiness.py"));f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=="build_draft_readiness");r=next(n for n in ast.walk(f) if isinstance(n,ast.Return) and isinstance(n.value,ast.Dict));keys=[k.value for k in r.value.keys if isinstance(k,ast.Constant)];assert "publication_allowed" in keys
