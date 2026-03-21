import os
from anthropic import Anthropic
from dotenv import load_dotenv
from checks import Finding

load_dotenv()

_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

FLOW_SYSTEM = (
    "You are a Salesforce admin assistant. Given the JSON metadata of a Salesforce Flow, "
    "write a plain-English description of what the flow does in 2-3 sentences. "
    "Write for a Salesforce admin audience. Be concise and specific."
)

ORG_SYSTEM = (
    "You are a Salesforce consultant writing an executive summary for a client report. "
    "Write 2-3 sentences summarizing the org's health based on the findings and score provided. "
    "Be professional, specific, and actionable. Do not use bullet points."
)


def generate_flow_description(flow_xml: str) -> str:
    """Generate a plain-English description of a Salesforce flow."""
    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=FLOW_SYSTEM,
        messages=[{"role": "user", "content": f"Flow metadata:\n{flow_xml}"}],
    )
    return msg.content[0].text.strip()


def generate_org_narrative(findings: list[Finding], score: int) -> str:
    """Generate a 2-3 sentence org health narrative for the PDF executive summary."""
    counts = {"Critical": 0, "Warning": 0, "Info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    summary = (
        f"Org health score: {score}/100. "
        f"Critical issues: {counts['Critical']}. "
        f"Warnings: {counts['Warning']}. "
        f"Informational items: {counts['Info']}."
    )
    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        system=ORG_SYSTEM,
        messages=[{"role": "user", "content": summary}],
    )
    return msg.content[0].text.strip()
