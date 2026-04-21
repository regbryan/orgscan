import os
from anthropic import Anthropic
from dotenv import load_dotenv
from checks import Finding

load_dotenv(override=True)

_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

FLOW_SYSTEM = (
    "You are a senior Salesforce consultant reviewing a Flow for a client. "
    "Given the JSON metadata of a Salesforce Flow, write TWO sections:\n\n"
    "**Description:** 2-3 sentences explaining what this flow does in plain English. "
    "Include the trigger type, what object it runs on, and the key actions it takes.\n\n"
    "**Recommendations:** A short bulleted list of improvements or issues. Look for:\n"
    "- Hardcoded values that should be variables, custom labels, or custom metadata\n"
    "- Missing error handling or fault paths\n"
    "- Empty or unpopulated fields that could cause silent failures\n"
    "- Old API versions that should be upgraded\n"
    "- Performance concerns (queries inside loops, missing filters)\n"
    "- Best practice violations (no description, no naming convention)\n"
    "If the flow looks clean, say so — don't invent issues.\n\n"
    "Write for a Salesforce admin audience. Be concise, specific, and actionable."
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
        max_tokens=600,
        system=FLOW_SYSTEM,
        messages=[{"role": "user", "content": f"Flow metadata:\n{flow_xml}"}],
    )
    return msg.content[0].text.strip()


FLOW_DOCUMENT_SYSTEM = (
    "You are a senior Salesforce consultant producing a client-ready flow automation document. "
    "Given the JSON metadata of a Salesforce Flow, return a SINGLE valid JSON object — no prose, "
    "no markdown fences, no commentary. Start with `{` and end with `}`.\n\n"

    "Schema:\n"
    "{\n"
    '  "overview": "2-4 sentences explaining what this flow does, why it exists, and what business problem it solves. Mention trigger type, object, and run mode.",\n'
    '  "configuration": {\n'
    '    "Flow Type": "Record-Triggered Flow | Screen Flow | Autolaunched Flow | Scheduled Flow | ...",\n'
    '    "Object": "sObject name (for record-triggered) or \'N/A\'",\n'
    '    "Trigger": "When a record is created | created or updated | updated | deleted | N/A",\n'
    '    "Run Mode": "Before Save | After Save | Async | N/A",\n'
    '    "Entry Conditions": "plain-English filter description or \'None\'",\n'
    '    "API Version": "e.g. 60.0",\n'
    '    "Status": "Active | Draft | Obsolete"\n'
    '  },\n'
    '  "steps": [\n'
    '    {\n'
    '      "n": 1,\n'
    '      "name": "Get Matching Records",\n'
    '      "type": "Get Records",\n'
    '      "fields": {\n'
    '        "Object": "Contact",\n'
    '        "Filters": "LastName equals {!$Record.LastName} AND Id not equal to {!$Record.Id}",\n'
    '        "Store": "All records in varMatchedContacts"\n'
    '      },\n'
    '      "description": "One-sentence plain-English explanation of what this step does and why."\n'
    '    }\n'
    '  ],\n'
    '  "resources": {\n'
    '    "Variables":    [{"name": "varX", "detail": "Text, Input. Holds the matched contact id."}],\n'
    '    "Formulas":     [{"name": "fmlEmail", "detail": "Concatenates first + last name for the email body."}],\n'
    '    "Constants":    [{"name": "cnstLimit", "detail": "Number. 50. Max rows processed."}],\n'
    '    "Choices":      [{"name": "chOptionA", "detail": "Label and value for the screen picklist."}],\n'
    '    "TextTemplates":[{"name": "tmplWelcome", "detail": "HTML greeting used in the Send Email action."}]\n'
    '  },\n'
    '  "recommendations": [\n'
    '    {"severity": "Critical | Warning | Best Practice | Positive", "text": "single actionable sentence"}\n'
    '  ],\n'
    '  "diagram": "raw Graphviz DOT starting with `digraph` and ending with `}`"\n'
    "}\n\n"

    "Rules for fields:\n"
    "- Steps MUST cover EVERY element in execution order. Keep each `description` to ONE sentence.\n"
    "- `fields` is a small key-value dict of the most important attributes for that element type:\n"
    "  Get Records → Object, Filters, Store, Sort (if set)\n"
    "  Decision → Outcomes (list outcome names + conditions)\n"
    "  Assignment → Assignments (var = value pairs)\n"
    "  Loop → Collection, Direction\n"
    "  Create/Update/Delete Records → Object, Fields Set, Criteria\n"
    "  Action → Action Type, Inputs\n"
    "  Screen → Components, Required Inputs\n"
    "  Subflow → Referenced Flow, Inputs\n"
    "- Omit any `resources` category that has zero items (do not include an empty array).\n"
    "- Recommendations: at least one Positive if applicable. Each text is ONE sentence, no prefix inside `text`.\n"
    "- Do NOT invent problems; if clean, say so in a Positive.\n\n"

    "Rules for the diagram (Graphviz DOT):\n"
    "- `digraph` with `rankdir=TB`.\n"
    "- Graph defaults: `graph [fontname=\"Helvetica\", bgcolor=\"white\", pad=0.25, ranksep=0.5, nodesep=0.4, size=\"7,9\", dpi=200]; "
    "node [fontname=\"Helvetica\", fontsize=11, margin=\"0.18,0.1\", height=0.45, width=1.6, style=\"filled,rounded\"]; "
    "edge [fontname=\"Helvetica\", fontsize=9, color=\"#64748b\", penwidth=1.1];`\n"
    "- Node shapes: ellipse (start/end), diamond (decision), box (action), box (error/fault with red fill), hexagon (loop), note (screen).\n"
    "- Node fill colors: start=#E8F0FE, decision=#FEF3C7, action=#EFF6FF, error=#FEE2E2, loop=#ECFDF5, screen=#F5F3FF.\n"
    "- Keep to 10-12 nodes max. Labels 2-4 words.\n"
    "- Do NOT include variables, formulas, constants, or resources as nodes.\n"
    "- Output the DOT as a plain JSON string — escape newlines as `\\n` and quotes as `\\\"`.\n\n"

    "Return only the JSON object. No leading or trailing text."
)


def generate_flow_document(flow_metadata: str) -> dict:
    """Generate a structured flow document via Claude.

    Returns a dict with both structured data (for the new renderer) AND legacy
    string fields (for backwards compatibility with older callers):
        {
          "description": str, "configuration": str, "components": str,
          "recommendations": str, "diagram": str,
          "structured": {
            "overview": str, "configuration": {k:v}, "steps": [...],
            "resources": {...}, "recommendations": [{severity,text}],
          }
        }
    """
    import json as _json
    import re as _re

    msg = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=FLOW_DOCUMENT_SYSTEM,
        messages=[{"role": "user", "content": f"Flow metadata:\n{flow_metadata}"}],
    )
    raw = msg.content[0].text.strip()

    # Strip any stray code fences the model may have added
    if raw.startswith("```"):
        raw = _re.sub(r'^```(?:json)?\s*', '', raw)
        raw = _re.sub(r'\s*```$', '', raw).strip()

    # Extract first {...} block if there's leading/trailing prose
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]

    try:
        data = _json.loads(raw)
    except _json.JSONDecodeError:
        # Fallback — return minimal legacy shape so the PDF still renders
        return {
            "description": raw[:2000],
            "configuration": "",
            "components": "",
            "recommendations": "",
            "diagram": "",
            "structured": None,
        }

    # Clean diagram DOT
    diag = (data.get("diagram") or "").strip()
    if diag.startswith("```"):
        diag = _re.sub(r'^```(?:dot|graphviz)?\s*', '', diag)
        diag = _re.sub(r'\s*```$', '', diag).strip()
    if "digraph" in diag:
        diag = diag[diag.index("digraph"):]

    # Build legacy string views so generate_flow_pdf's text path still works
    cfg_dict = data.get("configuration") or {}
    cfg_text = "\n".join(f"{k}: {v}" for k, v in cfg_dict.items())

    # Components text used only as a fallback string — the structured renderer
    # takes precedence when `structured` is non-None.
    components_lines: list[str] = []
    for step in data.get("steps") or []:
        components_lines.append(f"Step {step.get('n', '?')}: {step.get('name', '')}:")
        for k, v in (step.get("fields") or {}).items():
            components_lines.append(f"- {k} -- {v}")
        if step.get("description"):
            components_lines.append(f"- {step['description']}")
    components_text = "\n".join(components_lines)

    rec_lines = []
    for r in data.get("recommendations") or []:
        sev = r.get("severity", "").strip()
        txt = r.get("text", "").strip()
        if sev and txt:
            rec_lines.append(f"- {sev}: {txt}")
        elif txt:
            rec_lines.append(f"- {txt}")
    rec_text = "\n".join(rec_lines)

    return {
        "description": data.get("overview", "").strip(),
        "configuration": cfg_text,
        "components": components_text,
        "recommendations": rec_text,
        "diagram": diag,
        "structured": {
            "overview": data.get("overview", "").strip(),
            "configuration": cfg_dict,
            "steps": data.get("steps") or [],
            "resources": data.get("resources") or {},
            "recommendations": data.get("recommendations") or [],
        },
    }


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
