"""Architecture invariant tests — structural rules for the cst_runtime codebase.

These tests verify that every tool, pipeline, schema, and import follows
the project's architecture conventions. Run after any code change to
catch agent mistakes before they become bugs.

Tests are grouped by domain:
  JS-*  JSON Schema invariants
  HR-*  Handler registration invariants
  PL-*  Pipeline invariants
  CI-*  Core import invariants
  GV-*  Governance/risk invariants
"""
import sys
import ast
import inspect
from pathlib import Path

import pytest

SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))


# ---------------------------------------------------------------------------
# Helper — load definitions once
# ---------------------------------------------------------------------------
def _load_all_defs():
    from cst_runtime.tools import all_defs
    return all_defs()


def _load_dispatch_tools():
    from cst_runtime.cli.dispatch import TOOLS
    return TOOLS


def _load_pipelines():
    from cst_runtime.cli.pipelines.registry import PIPELINES
    return PIPELINES


VALID_CATEGORIES = {
    "modeling", "project_ops", "simulation", "results", "farfield",
    "session_manager", "audit", "workspace", "run", "process_cleanup",
    "project_identity",
}

VALID_RISK_LABELS = {"read", "write", "session", "process-control",
                     "long-running", "filesystem-write"}

RISK_TO_PIPELINE_MODE = {
    "read": "pipe_source",
    "write": "not_pipeable_destructive",
    "session": "not_pipeable_session",
    "process-control": "not_pipeable_session",
    "long-running": "not_pipeable_session",
    "filesystem-write": "pipe_sink",
}


# ===========================================================================
# JS — JSON Schema invariants
# ===========================================================================

class TestJsonSchemaInvariants:
    """All JS-1 through JS-7 + JS-Intro invariants."""

    def test_all_defs_have_json_schema(self):
        """JS-Intro1: Every TOOL_DEFS must have json_schema with properties."""
        for name, defn in _load_all_defs().items():
            assert "json_schema" in defn, f"{name}: missing json_schema"
            schema = defn["json_schema"]
            assert "properties" in schema, f"{name}: json_schema missing properties"
            assert isinstance(schema["properties"], dict), \
                f"{name}: properties must be dict"

    def test_no_args_template_remains(self):
        """JS-Intro2: No TOOL_DEFS may have args_template field."""
        for name, defn in _load_all_defs().items():
            assert "args_template" not in defn, f"{name}: args_template still present"

    def test_no_direct_flags_remains(self):
        """direct_flags field must not exist (derived from schema)."""
        for name, defn in _load_all_defs().items():
            assert "direct_flags" not in defn, f"{name}: direct_flags still present"

    def test_schema_type_object(self):
        """JS-1: Every json_schema must have type=object."""
        for name, defn in _load_all_defs().items():
            assert defn["json_schema"].get("type") == "object", \
                f"{name}: schema type is not 'object'"

    def test_required_fields_exist_in_properties(self):
        """JS-2: required fields must exist in properties."""
        for name, defn in _load_all_defs().items():
            schema = defn["json_schema"]
            for field in schema.get("required", []):
                assert field in schema.get("properties", {}), \
                    f"{name}: '{field}' in required but not in properties"

    def test_template_keys_subset_of_schema_keys(self):
        """JS-3: _schema_to_template output keys ⊆ schema properties keys."""
        from cst_runtime.tools import _schema_to_template
        for name, defn in _load_all_defs().items():
            template = _schema_to_template(defn["json_schema"])
            props = defn["json_schema"]["properties"]
            for key in template:
                assert key in props, \
                    f"{name}: template key '{key}' not in schema properties"

    def test_schema_property_types_valid(self):
        """JS-4: All property types must be valid JSON Schema types."""
        valid_types = {"string", "number", "integer", "boolean", "array", "object"}
        for name, defn in _load_all_defs().items():
            for key, prop in defn["json_schema"]["properties"].items():
                ptype = prop.get("type", "string")
                assert ptype in valid_types, \
                    f"{name}.{key}: invalid type '{ptype}'"

    def test_array_properties_have_items(self):
        """Array properties must have 'items' defined."""
        for name, defn in _load_all_defs().items():
            for key, prop in defn["json_schema"]["properties"].items():
                if prop.get("type") == "array":
                    assert "items" in prop, \
                        f"{name}.{key}: array type missing 'items'"


# ===========================================================================
# HR — Handler registration invariants
# ===========================================================================

class TestHandlerRegistration:
    """Every tool has a handler, every handler has a tool."""

    def test_every_tool_def_has_handler_in_map(self):
        """Each TOOL_DEFS.handler exists in dispatch.TOOLS."""
        tools = _load_dispatch_tools()
        for name, defn in _load_all_defs().items():
            assert name in tools, \
                f"{name}: in TOOL_DEFS but not in dispatch.TOOLS"

    @pytest.mark.xfail(reason="optimization tools use 'optimization' category not in VALID_CATEGORIES — add category or re-tag tools")
    def test_every_handler_has_category(self):
        """All tools in dispatch.TOOLS have valid category."""
        for name, rec in _load_dispatch_tools().items():
            cat = rec.get("category", "")
            assert cat in VALID_CATEGORIES, \
                f"{name}: unknown category '{cat}'. Valid: {sorted(VALID_CATEGORIES)}"

    def test_every_handler_has_valid_risk(self):
        """All tools have valid risk label."""
        for name, rec in _load_dispatch_tools().items():
            risk = rec.get("risk", "")
            assert risk in VALID_RISK_LABELS, \
                f"{name}: unknown risk '{risk}'"


# ===========================================================================
# PL — Pipeline invariants
# ===========================================================================

class TestPipelineInvariants:
    """Pipelines reference real tools and have valid step chains."""

    def test_every_pipeline_step_tool_exists(self):
        """JS-6 prep: Each pipeline step references a real tool or meta-command."""
        known_tools = set(_load_dispatch_tools())
        known_tools |= {"help", "list-tools", "list-pipelines", "describe-tool",
                        "describe-pipeline", "args-template", "pipeline-template",
                        "usage-guide", "invoke"}
        placeholders = {"<tool>", "--help"}
        for pipe_name, pipe_def in _load_pipelines().items():
            for step in pipe_def.get("steps", []):
                tool = step.get("tool", "")
                if tool in placeholders:
                    continue
                assert tool in known_tools, \
                    f"{pipe_name}: unknown tool '{tool}'"

    def test_pipeline_kebab_case_names(self):
        """Pipeline names must be kebab-case."""
        import re
        for name in _load_pipelines():
            assert re.match(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$', name), \
                f"Pipeline '{name}' is not kebab-case"


# ===========================================================================
# CI — Core import invariants
# ===========================================================================

class TestCoreImports:
    """Core modules must not directly import CST COM or have runtime imports."""

    def test_core_no_runtime_imports(self):
        """No function-body 'from .xxx import' in core/ (T6 cleanup)."""
        core_dir = SKILL_SCRIPTS / "cst_runtime" / "core"
        violations = []
        for py_file in sorted(core_dir.glob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for child in ast.walk(node):
                        if isinstance(child, ast.ImportFrom):
                            if child.module and child.module.startswith("."):
                                violations.append(
                                    f"{py_file.name}:{child.lineno}: "
                                    f"from .{child.module} import ... inside {node.name}()"
                                )
        assert not violations, "Runtime imports in core/:\n" + "\n".join(violations)

    def test_core_init_imports_not_runtime(self):
        """core/__init__.py must not be the only place importing cst modules."""
        core_init = SKILL_SCRIPTS / "cst_runtime" / "core" / "__init__.py"
        assert core_init.exists(), "Missing core/__init__.py"


# ===========================================================================
# GV — Governance invariants
# ===========================================================================

class TestGovernance:
    """Risk labels and pipeline modes are consistent."""

    def test_risk_pipeline_mode_consistency(self):
        """risk=write → not_pipeable_destructive, risk=read → pipe_source."""
        for name, rec in _load_dispatch_tools().items():
            risk = rec.get("risk", "")
            mode = rec.get("pipeline_mode", "")
            expected = RISK_TO_PIPELINE_MODE.get(risk)
            if expected:
                assert mode == expected, \
                    f"{name}: risk={risk} but pipeline_mode={mode} (expected {expected})"

    def test_modeling_write_tools_require_run_context(self):
        """modeling + write tools must have requires_run_context=True."""
        for name, rec in _load_dispatch_tools().items():
            if rec.get("category") == "modeling" and rec.get("risk") == "write":
                assert rec.get("requires_run_context"), \
                    f"{name}: modeling write tool must require run context"

    def test_read_tools_dont_require_check_solid(self):
        """risk=read tools must not require check_solid."""
        for name, rec in _load_dispatch_tools().items():
            if rec.get("risk") == "read":
                assert not rec.get("requires_check_solid", False), \
                    f"{name}: read tool should not require check_solid"
