"""Unit tests for cst_runtime.render.* (no CST needed)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from cst_runtime.render.svg_linechart import (
    _svg_axes,
    complex_components,
    safe_log_db,
    scalar_series,
    svg_linechart,
    svg_mini_trend,
)
from cst_runtime.render.svg_heatmap import svg_heatmap
from cst_runtime.render.svg_page import metric_cards_html, svg_page
from cst_runtime.render.canvas_3d import render_3d_farfield
from cst_runtime.render.dashboard import (
    _parse_cli_filename,
    _try_parse_cst_farfield_ascii,
)


class TestSvgLinechart:
    """Tests for render/svg_linechart.py"""

    def test_safe_log_db_positive(self) -> None:
        val = safe_log_db(0.5)
        expected = 20.0 * math.log10(0.5)
        assert abs(val - expected) < 1e-10

    def test_safe_log_db_zero(self) -> None:
        val = safe_log_db(0.0)
        expected = 20.0 * math.log10(1e-15)
        assert abs(val - expected) < 1e-10

    def test_safe_log_db_negative_input(self) -> None:
        val = safe_log_db(-0.5)
        expected = 20.0 * math.log10(0.5)
        assert abs(val - expected) < 1e-10

    def test_complex_components_dict(self) -> None:
        r, i = complex_components({"real": 0.5, "imag": 0.3})
        assert r == 0.5
        assert i == 0.3

    def test_complex_components_scalar(self) -> None:
        r, i = complex_components(0.7)
        assert r == 0.7
        assert i == 0.0

    def test_complex_components_list(self) -> None:
        r, i = complex_components([0.4, 0.6])
        assert r == 0.4
        assert i == 0.6

    def test_complex_components_empty_dict(self) -> None:
        r, i = complex_components({})
        assert r == 0.0
        assert i == 0.0

    def test_scalar_series_complex(self) -> None:
        values = [{"real": 0.5, "imag": 0.3}]
        result, kind = scalar_series(values)
        expected = safe_log_db(math.hypot(0.5, 0.3))
        assert kind == "magnitude_db"
        assert abs(result[0] - expected) < 1e-10

    def test_scalar_series_empty(self) -> None:
        result, kind = scalar_series([])
        assert result == []
        assert kind == "value"

    def test_scalar_series_plain_numbers(self) -> None:
        result, kind = scalar_series([1.0, 2.0, 3.0])
        assert kind == "value"
        assert result == [1.0, 2.0, 3.0]

    def test_svg_linechart_has_svg(self) -> None:
        svg = svg_linechart([{"x": [9, 10, 11], "y": [-10, -15, -12], "name": "test"}])
        assert "<svg" in svg
        assert 'width="960"' in svg
        assert 'xmlns="http://www.w3.org/2000/svg"' in svg

    def test_svg_linechart_empty_traces(self) -> None:
        svg = svg_linechart([])
        assert "无数据" in svg

    def test_svg_mini_trend_has_svg(self) -> None:
        svg = svg_mini_trend([1, 2, 3])
        assert "<svg" in svg
        assert "</svg>" in svg

    def test_svg_mini_trend_empty(self) -> None:
        assert svg_mini_trend([]) == ""

    def test_svg_mini_trend_single_point(self) -> None:
        svg = svg_mini_trend([42.0])
        assert "<svg" in svg

    def test_svg_mini_trend_with_label(self) -> None:
        svg = svg_mini_trend([1, 2, 3], label="S11")
        assert "S11" in svg

    def test_svg_axes_has_rect(self) -> None:
        result, x_min, x_max, y_min, y_max = _svg_axes(
            0, 10, -40, 0, "Freq (GHz)", "S11 (dB)", False
        )
        assert "<rect" in result
        assert "Freq (GHz)" in result
        assert "S11 (dB)" in result
        assert x_min < 0
        assert x_max > 10

    def test_svg_axes_dark_mode(self) -> None:
        result, *_ = _svg_axes(0, 10, -40, 0, "X", "Y", True)
        assert "#18181b" in result

    def test_svg_axes_single_value_range(self) -> None:
        result, *_ = _svg_axes(5, 5, -10, -10, "X", "Y", False)
        assert "<rect" in result


class TestSvgHeatmap:
    """Tests for render/svg_heatmap.py"""

    def test_empty_input(self) -> None:
        svg = svg_heatmap([], [], [], "Title", "X", "Y", "Z")
        assert "无数据" in svg

    def test_partial_none_grid(self) -> None:
        svg = svg_heatmap(
            x=[0, 90],
            y=[0],
            z=[[10, None]],
            title="Partial",
            xlabel="X",
            ylabel="Y",
            zlabel="Z",
        )
        assert "<svg" in svg

    def test_all_none_z(self) -> None:
        svg = svg_heatmap(
            x=[0, 90],
            y=[0],
            z=[[None, None]],
            title="AllNone",
            xlabel="X",
            ylabel="Y",
            zlabel="Z",
        )
        assert "无数据" in svg


class TestSvgPage:
    """Tests for render/svg_page.py"""

    def test_svg_page_doctype(self) -> None:
        html = svg_page("My Title", "<svg></svg>")
        assert "<!doctype html>" in html
        assert "My Title" in html
        assert "<svg></svg>" in html

    def test_svg_page_with_subtitle(self) -> None:
        html = svg_page("T", "<svg></svg>", subtitle="My Subtitle")
        assert "My Subtitle" in html

    def test_svg_page_with_extra_html(self) -> None:
        html = svg_page("T", "<svg></svg>", extra_html="<table></table>")
        assert "<table></table>" in html

    def test_svg_page_dark_mode(self) -> None:
        html = svg_page("T", "<svg></svg>", dark=True)
        assert "<!doctype html>" in html

    def test_metric_cards_html(self) -> None:
        metrics = [
            {"label": "Test", "value": "1.23", "unit": "dB", "css_class": "success"}
        ]
        html = metric_cards_html(metrics)
        assert "1.23" in html
        assert "dB" in html
        assert "metrics-grid" in html

    def test_metric_cards_html_empty(self) -> None:
        assert metric_cards_html([]) == ""

    def test_metric_cards_html_multiple(self) -> None:
        metrics = [
            {"label": "A", "value": "1", "css_class": ""},
            {"label": "B", "value": "2", "unit": "GHz", "css_class": "accent"},
        ]
        html = metric_cards_html(metrics)
        assert "A" in html
        assert "B" in html
        assert "GHz" in html

    def test_metric_cards_html_accent(self) -> None:
        metrics = [{"label": "C", "value": "3", "css_class": "accent"}]
        html = metric_cards_html(metrics)
        assert "accent" in html


class TestDashboard:
    """Tests for render/dashboard.py"""

    def test_try_parse_cst_farfield_ascii(self) -> None:
        text = "Theta Phi Abs(Realized Gain)[dBi]\n0 0 14.5\n10 180 13.6"
        result = _try_parse_cst_farfield_ascii(text)
        assert result is not None
        assert result["kind"] == "2d"
        assert len(result["xpositions"]) > 0
        assert len(result["ypositions"]) > 0
        assert len(result["data"]) > 0

    def test_try_parse_cst_farfield_ascii_no_header(self) -> None:
        result = _try_parse_cst_farfield_ascii("abc\n123")
        assert result is None

    def test_try_parse_cst_farfield_ascii_empty(self) -> None:
        result = _try_parse_cst_farfield_ascii("")
        assert result is None

    def test_try_parse_cst_farfield_ascii_invalid_header(self) -> None:
        result = _try_parse_cst_farfield_ascii("Theta\n0 0 14.5")
        assert result is None

    def test_try_parse_cst_farfield_ascii_with_phi_closure(self) -> None:
        text = "Theta Phi Abs(Gain)[dBi]\n0 0 10\n0 180 11\n0 359 12"
        result = _try_parse_cst_farfield_ascii(text)
        assert result is not None
        assert result["kind"] == "2d"

    def test_try_parse_cst_farfield_ascii_missing_columns(self) -> None:
        text = "Theta Phi Abs(Realized Gain)[dBi]\n0 0 14.5\nbad_line"
        result = _try_parse_cst_farfield_ascii(text)
        assert result is not None

    def test_parse_cli_filename(self) -> None:
        info = _parse_cli_filename("cli_20260101_120000_123456_change-parameter.json")
        assert info["tool"] == "change-parameter"
        assert info["sort_key"] == "20260101120000123456"

    def test_parse_cli_filename_non_cli(self) -> None:
        result = _parse_cli_filename("not_a_cli_file.txt")
        assert result is None

    def test_parse_cli_filename_with_dots(self) -> None:
        info = _parse_cli_filename("cli_20260101_120000_123456_define-brick.json")
        assert info is not None
        assert info["tool"] == "define-brick"


class TestCanvas3D:
    """Tests for render/canvas_3d.py"""

    def test_empty_data(self) -> None:
        html = render_3d_farfield({})
        assert "无可用" in html

    def test_missing_positions(self) -> None:
        html = render_3d_farfield({"data": [[1]]})
        assert "无可用" in html

    def test_minimal_valid_data(self) -> None:
        data = {
            "ypositions": [0, 90],
            "xpositions": [0, 180],
            "data": [[10, 5], [8, 3]],
        }
        html = render_3d_farfield(data)
        assert "<canvas" in html

    def test_partial_none_data(self) -> None:
        data = {
            "ypositions": [0, 45, 90],
            "xpositions": [0, 90, 180],
            "data": [[10, 8, 6], [7, None, 5], [6, 4, 3]],
        }
        html = render_3d_farfield(data)
        assert "<canvas" in html
