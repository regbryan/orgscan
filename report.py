import base64
import io
import re
import tempfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import requests
import toml
from fpdf import FPDF
from jinja2 import Environment, FileSystemLoader

try:
    from weasyprint import HTML
except (OSError, ImportError):
    HTML = None

from checks import Finding

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_FILE = BASE_DIR / "report_config.toml"


def load_branding() -> dict:
    if CONFIG_FILE.exists():
        data = toml.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("branding", {})
    return {"consultant_name": "Consultant", "logo_path": "", "primary_color": "#1e40af"}


def generate_pdf(
    client_name: str,
    findings: list[Finding],
    score: int,
    narrative: str,
    branding: dict,
    flow_descriptions: list[dict] | None = None,
) -> bytes:
    """Render findings to a PDF and return bytes."""
    if HTML is None:
        raise RuntimeError("WeasyPrint is not available. Please install system dependencies: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")

    findings_by_category = defaultdict(list)
    for f in findings:
        findings_by_category[f.category].append(f)

    counts = {"Critical": 0, "Warning": 0, "Info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("report.html")
    html_str = template.render(
        client_name=client_name,
        date=date.today().strftime("%B %d, %Y"),
        branding=branding,
        score=score,
        counts=counts,
        narrative=narrative,
        findings_by_category=dict(findings_by_category),
        flow_descriptions=flow_descriptions or [],
    )

    return HTML(string=html_str, base_url=str(BASE_DIR)).write_pdf()


def _dot_to_png_bytes(dot_text: str) -> bytes | None:
    """Render Graphviz DOT syntax to PNG bytes using the local `dot` command.

    Returns PNG bytes on success, None on failure.
    """
    if not dot_text or not dot_text.strip():
        return None
    import shutil
    import subprocess
    dot_bin = shutil.which("dot")
    if not dot_bin:
        # Try common install paths
        for p in [r"C:\Program Files\Graphviz\bin\dot.exe", "/usr/bin/dot", "/usr/local/bin/dot"]:
            if Path(p).exists():
                dot_bin = p
                break
    if not dot_bin:
        return None
    try:
        result = subprocess.run(
            [dot_bin, "-Tpng", "-Gdpi=200"],
            input=dot_text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout[:4] == b"\x89PNG":
            return result.stdout
    except Exception:
        pass
    return None


def _safe_text(text: str) -> str:
    """Strip non-latin1 characters that fpdf2 built-in fonts can't render."""
    replacements = {
        "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "--", "\u2026": "...", "\u2022": "-",
        "\u2192": "->", "\u2190": "<-", "\u2794": "->", "\u27a4": "->",
        "\u2605": "*", "\u2606": "*", "\u26a0": "[!]", "\u2714": "[ok]",
        "\u2718": "[x]", "\u00b7": "-",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Drop anything still outside latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#1e40af' to (30, 64, 175)."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (30, 64, 175)  # fallback blue


def _classify_recommendation(text: str) -> tuple[str, str, tuple]:
    """Detect severity prefix in a recommendation line.

    Returns (severity_label, cleaned_text, rgb_color).
    """
    lower = text.lower()
    if lower.startswith("critical"):
        cleaned = re.sub(r'^critical\s*[-:]\s*', '', text, flags=re.IGNORECASE).strip()
        return ("CRITICAL", cleaned, (220, 38, 38))   # red
    elif lower.startswith("warning"):
        cleaned = re.sub(r'^warning\s*[-:]\s*', '', text, flags=re.IGNORECASE).strip()
        return ("WARNING", cleaned, (202, 138, 4))     # amber
    elif lower.startswith("best practice") or lower.startswith("info"):
        cleaned = re.sub(r'^(best practice|info)\s*[-:]\s*', '', text, flags=re.IGNORECASE).strip()
        return ("BEST PRACTICE", cleaned, (37, 99, 235))  # blue
    elif lower.startswith("positive") or lower.startswith("good") or "no upgrade needed" in lower or "up to date" in lower:
        return ("OK", text, (22, 163, 74))             # green
    return ("", text, (30, 30, 30))                    # no label


def _draw_section_header(pdf, title: str, pr: int, pg: int, pb: int):
    """Draw a section header with colored underline."""
    pdf.ln(8)
    pdf.set_text_color(pr, pg, pb)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _safe_text(title), ln=True)
    pdf.set_draw_color(pr, pg, pb)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)


def generate_flow_pdf(
    flow_api_name: str,
    flow_label: str,
    description: str,
    configuration: str,
    components: str,
    recommendations: str,
    diagram_mermaid: str,
    branding: dict,
    client_name: str = "",
    structured: dict | None = None,
) -> bytes:
    """Render a single-flow documentation PDF — consulting deliverable format.

    Layout:
      1. Header + Title
      2. Overview (description)
      3. Configuration (key-value table)
      4. Flow Diagram (Graphviz, compact)
      5. Flow Steps & Resources (numbered steps + variables/formulas)
      6. Recommendations (severity-badged)
      7. Footer
    """
    primary = branding.get("primary_color", "#1e40af")
    pr, pg, pb = _hex_to_rgb(primary)
    consultant = branding.get("consultant_name", "Consultant")
    today = date.today().strftime("%B %d, %Y")
    label = flow_label or flow_api_name.replace("_", " ")

    margin = 10
    usable_w = 190  # 210 - 2*10

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Header bar ──────────────────────────────────────────────────────────
    pdf.set_fill_color(pr, pg, pb)
    pdf.rect(margin, margin, usable_w, 14, "F")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(margin + 4, margin + 2)
    pdf.cell(90, 10, _safe_text("Flow Documentation"), ln=False)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(margin + 100, margin + 2)
    pdf.cell(90, 10, _safe_text(f"{consultant}  |  {today}"), ln=True, align="R")

    # ── Flow title ──────────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.set_text_color(pr, pg, pb)
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(180, 10, _safe_text(label))
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(180, 5, _safe_text(f"API Name: {flow_api_name}"))
    if client_name:
        pdf.cell(0, 5, _safe_text(f"Client: {client_name}"), ln=True)

    # ── 1. Overview ──────────────────────────────────────────────────────────
    _draw_section_header(pdf, "Overview", pr, pg, pb)
    y_start = pdf.get_y()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.set_x(16)
    pdf.multi_cell(178, 6, _safe_text(description.strip()))
    y_end = pdf.get_y()
    pdf.set_fill_color(pr, pg, pb)
    pdf.rect(margin, y_start, 3, y_end - y_start, "F")

    # ── 2. Configuration ────────────────────────────────────────────────────
    cfg_dict = (structured or {}).get("configuration") if structured else None
    if cfg_dict:
        _draw_section_header(pdf, "Configuration", pr, pg, pb)
        _render_config_table_dict(pdf, cfg_dict, pr, pg, pb)
    elif configuration and configuration.strip():
        _draw_section_header(pdf, "Configuration", pr, pg, pb)
        _render_config_table(pdf, configuration, pr, pg, pb)

    # ── 3. Flow Diagram (compact) ───────────────────────────────────────────
    diagram_dot = diagram_mermaid
    png_bytes = _dot_to_png_bytes(diagram_dot) if diagram_dot else None
    if png_bytes:
        _draw_section_header(pdf, "Flow Diagram", pr, pg, pb)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        try:
            pdf.image(tmp_path, x=30, w=130)
        except Exception:
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(150, 150, 150)
            pdf.multi_cell(0, 5, _safe_text("[Diagram could not be rendered]"))
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    elif diagram_dot:
        _draw_section_header(pdf, "Flow Diagram (source)", pr, pg, pb)
        pdf.set_font("Courier", "", 7)
        pdf.set_text_color(80, 80, 80)
        pdf.set_fill_color(245, 245, 245)
        pdf.multi_cell(0, 3.5, _safe_text(diagram_dot.strip()), fill=True)

    # ── 4. Flow Steps ───────────────────────────────────────────────────────
    steps = (structured or {}).get("steps") if structured else None
    resources = (structured or {}).get("resources") if structured else None
    if steps:
        _draw_section_header(pdf, "Flow Steps", pr, pg, pb)
        _render_steps_structured(pdf, steps, pr, pg, pb)
        if resources and any(resources.values()):
            _draw_section_header(pdf, "Flow Resources", pr, pg, pb)
            _render_resources_structured(pdf, resources, pr, pg, pb)
    elif components and components.strip():
        _draw_section_header(pdf, "Flow Steps & Resources", pr, pg, pb)
        _render_components(pdf, components, pr, pg, pb)

    # ── 5. Recommendations ──────────────────────────────────────────────────
    recs_list = (structured or {}).get("recommendations") if structured else None
    if recs_list:
        _draw_section_header(pdf, "Recommendations", pr, pg, pb)
        _render_recommendations_structured(pdf, recs_list)
    elif recommendations and recommendations.strip():
        _draw_section_header(pdf, "Recommendations", pr, pg, pb)

        item_num = 0
        rec_lines = [l for l in recommendations.strip().split("\n") if l.strip()]
        for line in rec_lines:
            stripped = line.strip()
            if stripped.startswith("-") or stripped.startswith("*"):
                text = re.sub(r"^[-*]\s*", "", stripped)
            else:
                text = stripped
            text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

            severity, cleaned, sev_color = _classify_recommendation(text)
            item_num += 1

            if severity:
                pdf.set_x(14)
                sr, sg, sb = sev_color
                pdf.set_fill_color(sr, sg, sb)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Helvetica", "B", 7)
                badge_w = pdf.get_string_width(severity) + 6
                pdf.cell(badge_w, 5, severity, fill=True, ln=False)
                pdf.ln(7)

            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_x(14)
            pdf.multi_cell(180, 6, _safe_text(cleaned))
            pdf.ln(2)

            if item_num < len(rec_lines):
                pdf.set_draw_color(230, 230, 230)
                pdf.line(14, pdf.get_y(), 196, pdf.get_y())
                pdf.ln(2)

    # ── Footer ──────────────────────────────────────────────────────────────
    pdf.ln(10)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(margin, pdf.get_y(), margin + usable_w, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 5, _safe_text(f"Generated by OrgScan  |  {consultant}  |  {today}"), align="C")

    return bytes(pdf.output())


def _render_config_table(pdf, config_text: str, pr: int, pg: int, pb: int):
    """Render the configuration section as a clean two-column table."""
    lines = config_text.strip().split("\n")
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Parse "Key: Value" or "Key — Value"
        if ": " in stripped:
            key, val = stripped.split(": ", 1)
            rows.append((key.strip(), val.strip()))
        elif " -- " in stripped:
            key, val = stripped.split(" -- ", 1)
            rows.append((key.strip(), val.strip()))
        else:
            rows.append(("", stripped))

    if not rows:
        return

    border = {"style": "SINGLE", "size": 0.5, "color": (200, 200, 200)}
    label_w = 50
    value_w = 140
    row_h = 7

    for key, val in rows:
        # Label cell (shaded)
        y = pdf.get_y()
        pdf.set_fill_color(pr, pg, pb)
        pdf.set_fill_color(235, 240, 250)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.set_xy(10, y)
        pdf.cell(label_w, row_h, _safe_text(key), border=1, ln=False, fill=True)
        # Value cell
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(value_w, row_h, _safe_text(val), border=1, ln=True)

    pdf.ln(2)


def _render_components(pdf, components_text: str, pr: int, pg: int, pb: int):
    """Render the flow components section with category headers and bullet items."""
    # Strip any markdown bold markers the AI might have used
    components_text = re.sub(r"\*\*(.*?)\*\*", r"\1", components_text)

    lines = components_text.strip().split("\n")
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Category headers end with ':' and don't start with '-'
        if stripped.endswith(":") and not stripped.startswith("-"):
            pdf.ln(3)
            pdf.set_text_color(pr, pg, pb)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_x(12)
            pdf.cell(0, 6, _safe_text(stripped), ln=True)
            # Thin underline
            pdf.set_draw_color(pr, pg, pb)
            pdf.line(12, pdf.get_y(), 100, pdf.get_y())
            pdf.ln(2)
        elif stripped.startswith("-"):
            text = re.sub(r"^-\s*", "", stripped)

            # Try to split on common separators to get name vs description
            sep_match = re.match(r'^([^()\-]+?)\s*[\(\-]\s*(.+)$', text)
            if " -- " in text:
                name_part, desc_part = text.split(" -- ", 1)
            elif sep_match and len(sep_match.group(1)) < 60:
                name_part = sep_match.group(1).strip()
                desc_part = text[len(name_part):].strip()
                # Rejoin with the separator
                name_part = name_part
            else:
                name_part = None
                desc_part = text

            if name_part:
                # Bullet + bold name + regular description
                pdf.set_x(14)
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(4, 5, _safe_text("-"), ln=False)
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(pdf.get_string_width(_safe_text(name_part)) + 1, 5, _safe_text(name_part), ln=False)
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(60, 60, 60)
                remaining = 190 - pdf.get_x()
                if remaining > 20:
                    pdf.multi_cell(remaining, 5, _safe_text(f" {desc_part}"))
                else:
                    pdf.ln(5)
                    pdf.set_x(22)
                    pdf.multi_cell(168, 5, _safe_text(desc_part))
            else:
                # Simple bullet item
                pdf.set_x(14)
                pdf.set_text_color(30, 30, 30)
                pdf.set_font("Helvetica", "", 9)
                pdf.cell(4, 5, _safe_text("-"), ln=False)
                pdf.multi_cell(172, 5, _safe_text(desc_part))
            pdf.ln(1)
        else:
            # Regular text line
            pdf.set_x(14)
            pdf.set_text_color(30, 30, 30)
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(176, 5, _safe_text(stripped))
            pdf.ln(1)


# ── Structured renderers (new, preferred path) ──────────────────────────────

_SEVERITY_COLORS = {
    "critical":      (220, 38, 38),   # red
    "warning":       (202, 138, 4),   # amber
    "best practice": (37, 99, 235),   # blue
    "positive":      (22, 163, 74),   # green
}


def _render_config_table_dict(pdf, cfg: dict, pr: int, pg: int, pb: int):
    """Render configuration from a dict (structured AI output)."""
    if not cfg:
        return
    label_w = 50
    value_w = 140
    row_h = 7
    for key, val in cfg.items():
        if val is None or str(val).strip() == "":
            continue
        y = pdf.get_y()
        pdf.set_fill_color(235, 240, 250)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 30, 30)
        pdf.set_xy(10, y)
        pdf.cell(label_w, row_h, _safe_text(str(key)), border=1, ln=False, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(value_w, row_h, _safe_text(str(val)), border=1, ln=True)
    pdf.ln(2)


_BADGE_NEUTRAL = (71, 85, 105)  # slate-600 — single muted color for all type badges


def _tint(pr: int, pg: int, pb: int, mix: float = 0.9) -> tuple[int, int, int]:
    """Blend color with white by `mix` (1.0 = pure white, 0.0 = pure color)."""
    return (
        int(pr + (255 - pr) * mix),
        int(pg + (255 - pg) * mix),
        int(pb + (255 - pb) * mix),
    )


def _render_steps_structured(pdf, steps: list, pr: int, pg: int, pb: int):
    """Render each step with a prominent banner header, type pill, field rows, and description."""
    margin_l = 10
    inner_l = 14      # inside the banner/content
    usable_w = 190
    content_w = 186   # inside padding

    tint = _tint(pr, pg, pb, 0.9)         # very light band fill
    tint_rule = _tint(pr, pg, pb, 0.6)    # rule under banner

    for idx, step in enumerate(steps):
        n = step.get("n", idx + 1)
        name = (step.get("name") or "").strip()
        stype = (step.get("type") or "").strip()
        fields = step.get("fields") or {}
        desc = (step.get("description") or "").strip()

        # Reserve enough room so the banner doesn't orphan at the page bottom
        if pdf.get_y() > 245:
            pdf.add_page()

        pdf.ln(4)
        banner_y = pdf.get_y()
        banner_h = 12

        # ── Banner background ──────────────────────────────────────────────
        pdf.set_fill_color(*tint)
        pdf.rect(margin_l, banner_y, usable_w, banner_h, "F")
        # Left accent strip
        pdf.set_fill_color(pr, pg, pb)
        pdf.rect(margin_l, banner_y, 2.5, banner_h, "F")

        # ── Number pill ────────────────────────────────────────────────────
        pill_x = margin_l + 6
        pill_y = banner_y + 2
        pill_w = 9
        pill_h = 8
        pdf.set_fill_color(pr, pg, pb)
        pdf.rect(pill_x, pill_y, pill_w, pill_h, "F")
        pdf.set_xy(pill_x, pill_y)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(pill_w, pill_h, _safe_text(str(n)), align="C")

        # ── Step title (bold, large, ink) ─────────────────────────────────
        title_x = pill_x + pill_w + 3
        pdf.set_xy(title_x, banner_y + 1.6)
        pdf.set_text_color(27, 28, 30)
        pdf.set_font("Helvetica", "B", 13)
        # Reserve room on the right for the type badge
        badge_w = 0
        if stype:
            pdf.set_font("Helvetica", "B", 7.5)
            badge_text = _safe_text(stype.upper())
            badge_w = pdf.get_string_width(badge_text) + 8
            pdf.set_font("Helvetica", "B", 13)
        title_max_w = (margin_l + usable_w) - title_x - badge_w - 4
        title_text = _safe_text(f"Step {n}: {name}" if name else f"Step {n}")
        # Clip overlong titles so badge stays visible
        if pdf.get_string_width(title_text) > title_max_w:
            while pdf.get_string_width(title_text + "...") > title_max_w and len(title_text) > 4:
                title_text = title_text[:-1]
            title_text = title_text + "..."
        pdf.cell(title_max_w, 9, title_text, ln=False)

        # ── Type badge (right-aligned, neutral slate) ──────────────────────
        if stype:
            tr, tg, tb = _BADGE_NEUTRAL
            badge_h = 5
            badge_x = margin_l + usable_w - badge_w - 3
            badge_y = banner_y + (banner_h - badge_h) / 2
            pdf.set_fill_color(tr, tg, tb)
            pdf.rect(badge_x, badge_y, badge_w, badge_h, "F")
            pdf.set_xy(badge_x, badge_y)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.cell(badge_w, badge_h, _safe_text(stype.upper()), align="C")

        # Move below the banner
        pdf.set_y(banner_y + banner_h)
        # Subtle rule under banner
        pdf.set_draw_color(*tint_rule)
        pdf.set_line_width(0.2)
        pdf.line(margin_l, pdf.get_y(), margin_l + usable_w, pdf.get_y())
        pdf.ln(3)

        # ── Field rows (two-column definition list) ────────────────────────
        if fields:
            label_w = 34
            value_w = content_w - label_w - 4
            for k, v in fields.items():
                if v is None or str(v).strip() == "":
                    continue
                # Page break inside a field block if needed
                if pdf.get_y() > 270:
                    pdf.add_page()
                key_str = _safe_text(f"{k}")
                val_str = _safe_text(str(v))

                # Measure wrapped value height via dry-run split
                pdf.set_font("Helvetica", "", 9.5)
                try:
                    lines = pdf.multi_cell(value_w, 5.2, val_str, split_only=True)
                    line_count = max(1, len(lines))
                except TypeError:
                    # Older fpdf2 versions may not accept split_only — fall back to rough estimate
                    chars_per_line = max(1, int(value_w / 1.8))
                    line_count = max(1, (len(val_str) + chars_per_line - 1) // chars_per_line)
                row_h = max(6.2, line_count * 5.2)

                y_before = pdf.get_y()
                # Label (bold, ink)
                pdf.set_xy(inner_l, y_before)
                pdf.set_text_color(27, 28, 30)
                pdf.set_font("Helvetica", "B", 9.5)
                pdf.cell(label_w, row_h, key_str, ln=False)
                # Value
                pdf.set_xy(inner_l + label_w + 4, y_before)
                pdf.set_text_color(40, 40, 40)
                pdf.set_font("Helvetica", "", 9.5)
                pdf.multi_cell(value_w, 5.2, val_str)
                if pdf.get_y() < y_before + row_h:
                    pdf.set_y(y_before + row_h)
                pdf.ln(0.5)

        # ── Description (italic paragraph) ─────────────────────────────────
        if desc:
            if pdf.get_y() > 270:
                pdf.add_page()
            pdf.ln(1)
            pdf.set_x(inner_l)
            pdf.set_text_color(70, 70, 70)
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.multi_cell(content_w, 5.2, _safe_text(desc))

        pdf.ln(3)


def _render_resources_structured(pdf, resources: dict, pr: int, pg: int, pb: int):
    """Render resources as a single ledger-style block with small-caps subheads."""
    margin_l = 10
    inner_l = 14
    usable_w = 190

    category_order = ["Variables", "Formulas", "Constants", "Choices", "TextTemplates", "Text Templates"]
    seen = set()
    ordered = [c for c in category_order if c in resources and c not in seen and not seen.add(c)]
    for c in resources.keys():
        if c not in seen:
            ordered.append(c)
            seen.add(c)

    first_category = True
    for category in ordered:
        items = [i for i in (resources.get(category) or []) if isinstance(i, dict)]
        if not items:
            continue
        if pdf.get_y() > 258:
            pdf.add_page()

        display = "Text Templates" if category == "TextTemplates" else category
        count = len(items)

        # ── Small-caps subhead on hairline rule ───────────────────────────
        if not first_category:
            pdf.ln(4)
        first_category = False

        sub_y = pdf.get_y()
        # Top hairline rule
        pdf.set_draw_color(217, 212, 199)  # --rule
        pdf.set_line_width(0.2)
        pdf.line(margin_l, sub_y, margin_l + usable_w, sub_y)
        pdf.ln(2)

        # Category label (uppercase, letter-spaced, ink-dim)
        pdf.set_x(margin_l)
        pdf.set_text_color(90, 91, 94)  # --ink-dim
        pdf.set_font("Helvetica", "B", 9)
        label_txt = _safe_text(display.upper())
        pdf.cell(120, 5, label_txt, ln=False)

        # Count on the right, mono-ish look
        count_txt = _safe_text(f"{count} item" + ("s" if count != 1 else ""))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(140, 140, 140)
        cw = pdf.get_string_width(count_txt) + 2
        pdf.set_xy(margin_l + usable_w - cw, sub_y + 2)
        pdf.cell(cw, 5, count_txt, align="R")

        pdf.ln(8)

        # ── Items ─────────────────────────────────────────────────────────
        for it in items:
            if pdf.get_y() > 272:
                pdf.add_page()
            name = (it.get("name") or "").strip()
            detail = (it.get("detail") or "").strip()
            if not name and not detail:
                continue

            pdf.set_x(inner_l)
            # Bullet (en-dash, ink)
            pdf.set_text_color(27, 28, 30)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(4, 5.2, _safe_text("-"), ln=False)
            # Name (bold, ink)
            pdf.set_font("Helvetica", "B", 9.5)
            name_str = _safe_text(name) if name else ""
            if name_str:
                nw = pdf.get_string_width(name_str) + 0.5
                pdf.cell(nw, 5.2, name_str, ln=False)
            # Detail (regular, muted)
            if detail:
                pdf.set_font("Helvetica", "", 9.5)
                pdf.set_text_color(80, 80, 80)
                remaining = (margin_l + usable_w) - pdf.get_x() - 2
                sep = " -- " if name_str else ""
                pdf.multi_cell(remaining, 5.2, _safe_text(f"{sep}{detail}"))
            else:
                pdf.ln(5.2)
            pdf.ln(0.4)


def _render_recommendations_structured(pdf, recs: list):
    """Render recs from structured list with colored severity badge + one-sentence body."""
    n = len(recs)
    for idx, r in enumerate(recs):
        if not isinstance(r, dict):
            continue
        sev_raw = (r.get("severity") or "").strip()
        text = (r.get("text") or "").strip()
        if not text:
            continue
        label = sev_raw.upper() if sev_raw else ""

        if pdf.get_y() > 258:
            pdf.add_page()

        if label:
            pdf.set_x(14)
            sr, sg, sb = _BADGE_NEUTRAL
            pdf.set_fill_color(sr, sg, sb)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 7.5)
            badge_w = pdf.get_string_width(label) + 6
            pdf.cell(badge_w, 5, label, fill=True, ln=False)
            pdf.ln(7)

        pdf.set_text_color(30, 30, 30)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(14)
        pdf.multi_cell(180, 5.8, _safe_text(text))
        pdf.ln(2)

        if idx < n - 1:
            pdf.set_draw_color(230, 230, 230)
            pdf.line(14, pdf.get_y(), 196, pdf.get_y())
            pdf.ln(2)

