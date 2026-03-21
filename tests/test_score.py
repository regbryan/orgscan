import pytest
from checks import Finding
from score import compute_score


def make_finding(severity):
    return Finding(
        category="Users", severity=severity,
        title="t", detail="d", recommendation="r"
    )


def test_perfect_score_with_no_findings():
    assert compute_score([]) == 100


def test_single_critical_deducts_15():
    findings = [make_finding("Critical")]
    assert compute_score(findings) == 85


def test_single_warning_deducts_5():
    findings = [make_finding("Warning")]
    assert compute_score(findings) == 95


def test_single_info_deducts_1():
    findings = [make_finding("Info")]
    assert compute_score(findings) == 99


def test_mixed_findings():
    findings = [
        make_finding("Critical"),
        make_finding("Critical"),
        make_finding("Warning"),
        make_finding("Info"),
    ]
    # 100 - 30 - 5 - 1 = 64
    assert compute_score(findings) == 64


def test_score_floors_at_zero():
    findings = [make_finding("Critical")] * 10  # 10 * 15 = 150 deductions
    assert compute_score(findings) == 0
