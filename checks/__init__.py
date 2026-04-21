from dataclasses import dataclass, field


@dataclass
class Finding:
    category: str           # "Users", "Flows", "Fields", "Permissions", "Validation"
    severity: str           # "Critical", "Warning", "Info"
    title: str              # Short description shown in dashboard
    detail: str             # Full detail / affected records
    recommendation: str     # What the consultant should do
    flow_api_name: str | None = None  # Set only for flow findings (Salesforce DeveloperName)
    link: str = ""                    # Direct Salesforce URL for this specific record
