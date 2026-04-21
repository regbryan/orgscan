# AI Features & Data Privacy

OrgScan includes optional AI-powered features that generate plain-English descriptions
of your Salesforce Flows and an executive summary for your health report. This document
explains exactly what data is and is not sent to the AI provider, so you can make an
informed decision about whether to use these features.

---

## What the AI features do

| Feature | How to trigger it | Purpose |
|---|---|---|
| **Flow Description** | Click "Describe" on any flow | Generates a plain-English summary of what a flow does |
| **Flow Documentation** | Click "Document" on any flow | Produces a full client-ready PDF with steps, config, and recommendations |
| **Report Narrative** | Included when generating a PDF report | Writes a 2-3 sentence executive health summary |

All three features are **opt-in**. None of them run automatically during a scan.

---

## What IS sent to the AI

### Flow Description / Flow Documentation

When you click Describe or Document on a flow, OrgScan sends that flow's **configuration
metadata** to the AI. This includes:

- The flow's element structure (decisions, assignments, loops, actions)
- Field API names referenced in the flow (e.g. `Opportunity.StageName`)
- Conditions and logic (e.g. "if Close Date is blank")
- Hardcoded text values entered by whoever built the flow
- The flow's API version, type, and trigger settings

This is equivalent to the information a Salesforce developer would post in a public
forum when asking for help with a flow. It describes **how the automation is configured**,
not the data flowing through it.

### Report Narrative

The AI receives only three numbers:

- The overall org health score (0–100)
- Count of Critical findings
- Count of Warning findings
- Count of Informational findings

No finding titles, details, or org-specific content are included.

---

## What is NEVER sent to the AI

- **Salesforce records** — no Accounts, Contacts, Opportunities, Cases, or any other
  object records are sent
- **Customer or employee data** — no names, email addresses, phone numbers, or any
  personally identifiable information from your org's data
- **Query results** — all SOQL query results stay local and are used only to generate
  the findings displayed in the app
- **Credentials** — your Salesforce OAuth tokens and API keys never leave your machine
- **Findings text** — the specific finding titles and details shown in the dashboard
  are not included in AI requests (except the three aggregate counts noted above)

---

## How to use OrgScan without the AI features

The AI layer is entirely separate from the health scan. You can:

- Run a full org scan and review all findings
- Generate a PDF report (the narrative will use a static summary instead of AI)
- Export findings to CSV

None of these require an AI API key or send any data to an external AI provider.

---

## Who controls the AI key

OrgScan does not include a shared or bundled AI API key. Each operator runs the app
with their own key, obtained directly from the AI provider. This means:

- You choose whether to enable AI features at all
- You can review the provider's data processing terms before entering a key
- No AI calls are made until you explicitly trigger a feature

---

## AI provider

OrgScan currently uses the **Anthropic Claude API**. Anthropic's data handling policies,
including options for zero data retention and enterprise data agreements, are documented
at [anthropic.com/legal/privacy](https://www.anthropic.com/legal/privacy).

---

## Frequently asked questions

**Can my Salesforce customer data be used to train the AI model?**

OrgScan does not send customer records to the AI. Flow metadata (automation configuration)
is sent for the Flow features. Whether that metadata is used for model training depends on
your agreement with the AI provider. Anthropic's default API terms and enterprise options
are described in their privacy policy linked above.

**Can I see exactly what gets sent before it is submitted?**

Not in the current UI, but the flow metadata sent to the AI is the same JSON that
Salesforce returns from its own Tooling API for that flow. You can inspect any flow's
metadata directly in Salesforce's Developer Console or Workbench.

**What if I am not comfortable with any data leaving the system?**

Do not use the AI features. The health scan, all findings, scoring, and CSV export
are fully local — no external AI calls are made.

**Is the AI key stored anywhere?**

The key is read from an environment variable or a local configuration file on the
machine running OrgScan. It is never transmitted to any server operated by OrgScan.
