from checks import Finding

# Severity weights — Critical findings hurt more, but the score
# scales proportionally so large orgs aren't auto-zeroed.
WEIGHTS = {"Critical": 10, "Warning": 3, "Info": 1}

# Each check category contributes a "possible score" bucket.
# An org with zero findings in a category gets full marks for it.
# The overall score is the percentage of total weight NOT deducted.
CATEGORY_BUDGET = 30  # max weighted deductions per category before it bottoms out


def compute_score(findings: list[Finding]) -> int:
    """Compute org health 0–100.

    Strategy: group findings by category, cap deductions per category
    so one noisy area can't tank the entire score, then compute the
    percentage of total budget that remains.
    """
    if not findings:
        return 100

    # Collect weighted deductions per category
    cats: dict[str, float] = {}
    for f in findings:
        w = WEIGHTS.get(f.severity, 0)
        cats[f.category] = cats.get(f.category, 0) + w

    # Cap each category's deductions at CATEGORY_BUDGET
    total_budget = len(cats) * CATEGORY_BUDGET
    total_deducted = sum(min(d, CATEGORY_BUDGET) for d in cats.values())

    if total_budget == 0:
        return 100

    score = round(100 * (1 - total_deducted / total_budget))
    return max(0, min(100, score))
