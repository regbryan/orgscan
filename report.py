from collections import defaultdict
from datetime import date
from pathlib import Path

import toml
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

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
    findings_by_category = defaultdict(list)
    for f in findings:
        findings_by_category[f.category].append(f)

    counts = {"Critical": 0, "Warning": 0, "Info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
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
