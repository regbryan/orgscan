import sys
from unittest.mock import MagicMock, patch
import pytest

# Mock weasyprint before importing report
sys.modules['weasyprint'] = MagicMock()

from checks import Finding
from report import generate_pdf, load_branding


def sample_findings():
    return [
        Finding("Users", "Critical", "2 inactive users", "John, Jane", "Deactivate them"),
        Finding("Flows", "Warning", "Flow missing desc", "Lead_Assignment", "Add description", flow_api_name="Lead_Assignment"),
    ]


def test_load_branding_returns_dict(tmp_path, monkeypatch):
    import report as report_mod
    config = tmp_path / "report_config.toml"
    config.write_text('[branding]\nconsultant_name = "Test"\nlogo_path = ""\nprimary_color = "#000"\n')
    monkeypatch.setattr(report_mod, "CONFIG_FILE", config)
    branding = load_branding()
    assert branding["consultant_name"] == "Test"


def test_generate_pdf_returns_bytes():
    findings = sample_findings()
    with patch("report.HTML") as mock_html:
        mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
        result = generate_pdf(
            client_name="Acme Corp",
            findings=findings,
            score=75,
            narrative="The org is in good shape.",
            branding={"consultant_name": "Reggie", "logo_path": "", "primary_color": "#1e40af"},
        )
    assert isinstance(result, bytes)


def test_generate_pdf_groups_findings_by_category():
    findings = sample_findings()
    with patch("report.HTML") as mock_html:
        mock_html.return_value.write_pdf.return_value = b"%PDF"
        generate_pdf("Client", findings, 75, "Good.", {"consultant_name": "R", "logo_path": "", "primary_color": "#000"})
    mock_html.assert_called_once()
