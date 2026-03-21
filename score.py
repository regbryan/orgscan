from checks import Finding

WEIGHTS = {"Critical": 15, "Warning": 5, "Info": 1}


def compute_score(findings: list[Finding]) -> int:
    deductions = sum(WEIGHTS.get(f.severity, 0) for f in findings)
    return max(0, 100 - deductions)
