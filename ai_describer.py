import os
import re as _re2
from collections import defaultdict as _defaultdict
from anthropic import Anthropic
from dotenv import load_dotenv
from checks import Finding

load_dotenv(override=True)

_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


# =====================================================================
# Visio-geometry DOT post-processor
# =====================================================================
# Deterministic topology-aware pass that enforces Visio-style flowchart
# routing on Graphviz DOT returned by the model. It does three things:
#
#   1. Parses nodes + edges out of the DOT string.
#   2. Detects "decision chains" — runs of diamond nodes linked by NO/False
#      edges, where each diamond's YES/True branch drops to a process below.
#   3. Rewrites compass ports on every edge and injects `rank=same`
#      subgraphs to force:
#         * Chained decisions into one horizontal row (NO goes `:e -> :w`)
#         * Each diamond's YES-target process into a second horizontal row
#           below (YES goes `:s -> :n`)
#         * Isolated processes with multi-output: primary `:s`, fault `:w`
# =====================================================================

_VG_IDENT = r'(?:"(?:[^"\\]|\\.)*"|[A-Za-z_][A-Za-z0-9_]*)'
_VG_EDGE_RE = _re2.compile(
    rf'({_VG_IDENT})(?::([nsew]{{1,2}}))?\s*->\s*({_VG_IDENT})(?::([nsew]{{1,2}}))?(\s*\[([^\]]*)\])?\s*;?',
    _re2.MULTILINE,
)
_VG_NODE_RE = _re2.compile(rf'({_VG_IDENT})\s*\[([^\]]*)\]\s*;?', _re2.MULTILINE)
_VG_DEFAULT_RE = _re2.compile(r'(?:graph|node|edge)\s*\[[^\]]*\]\s*;?', _re2.IGNORECASE | _re2.MULTILINE)


def _vg_extract_label(attrs_body: str) -> str:
    m = _re2.search(r'label\s*=\s*"([^"]*)"', attrs_body)
    if m:
        return m.group(1)
    m = _re2.search(r'label\s*=\s*<(.*?)>', attrs_body, _re2.DOTALL)
    if m:
        return _re2.sub(r'<[^>]+>', '', m.group(1)).strip()
    return ''


def _vg_classify_edge(attrs_body: str, label: str) -> str:
    a = (attrs_body or '').lower().replace(' ', '')
    l = (label or '').strip().lower()
    if l == 'no' or l.startswith('no') or l == 'false' or l.startswith('false'):
        return 'no'
    if l == 'yes' or l.startswith('yes') or l == 'true' or l.startswith('true'):
        return 'yes'
    if 'style=dashed' in a or 'style="dashed"' in a:
        return 'fault'
    if '#dc2626' in a or 'color=red' in a or 'color="red"' in a:
        return 'fault'
    return 'primary'


def _vg_quote_if_needed(name: str) -> str:
    if _re2.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        return name
    if name.startswith('"') and name.endswith('"'):
        return name
    return f'"{name}"'


def _apply_visio_geometry(dot: str) -> str:
    """Rewrite a DOT string to enforce Visio-style orthogonal routing.

    Adds compass ports to every edge and injects rank=same subgraphs for
    detected horizontal decision chains and their process rows.
    """
    # Pass 1: collect edges
    edges = []
    for m in _VG_EDGE_RE.finditer(dot):
        attrs_body = m.group(6) or ''
        edges.append({
            'match': m,
            'src': m.group(1).strip('"'),
            'tgt': m.group(3).strip('"'),
            'attrs_block': m.group(5) or '',
            'attrs_body': attrs_body,
            'label': _vg_extract_label(attrs_body),
        })
    for e in edges:
        e['kind'] = _vg_classify_edge(e['attrs_body'], e['label'])

    # Pass 2: extract node declarations (mask edges + default attrs first)
    masked = list(dot)
    for e in edges:
        for i in range(e['match'].start(), e['match'].end()):
            masked[i] = ' '
    masked_str = ''.join(masked)
    for m in _VG_DEFAULT_RE.finditer(masked_str):
        masked_str = masked_str[:m.start()] + (' ' * (m.end() - m.start())) + masked_str[m.end():]

    nodes: dict[str, dict] = {}
    for m in _VG_NODE_RE.finditer(masked_str):
        name = m.group(1).strip('"')
        if name in ('graph', 'node', 'edge', 'digraph', 'subgraph', 'strict'):
            continue
        attrs = m.group(2)
        shape_m = _re2.search(r'shape\s*=\s*"?(\w+)"?', attrs, _re2.IGNORECASE)
        shape = shape_m.group(1).lower() if shape_m else 'box'
        nodes[name] = {'shape': shape}
    for e in edges:
        for n in (e['src'], e['tgt']):
            nodes.setdefault(n, {'shape': 'box'})

    def is_diamond(n: str) -> bool:
        return nodes.get(n, {}).get('shape') == 'diamond'

    # Pass 3: adjacency
    outgoing = _defaultdict(list)
    incoming = _defaultdict(list)
    for e in edges:
        outgoing[e['src']].append(e)
        incoming[e['tgt']].append(e)

    # Pass 4: detect decision chains
    chains: list[list[str]] = []
    visited: set[str] = set()
    for name in nodes:
        if not is_diamond(name) or name in visited:
            continue
        # Only consider chain starts (no NO-predecessor that is itself a diamond)
        is_start = True
        for inc in incoming[name]:
            if is_diamond(inc['src']) and inc['kind'] == 'no':
                is_start = False
                break
        if not is_start:
            continue
        chain = [name]
        cur = name
        visited.add(cur)
        while True:
            no_out = [e for e in outgoing[cur] if e['kind'] == 'no']
            if not no_out:
                break
            nxt = no_out[0]['tgt']
            if is_diamond(nxt) and nxt not in visited:
                chain.append(nxt)
                visited.add(nxt)
                cur = nxt
            else:
                break
        chains.append(chain)

    chain_diamonds = {d for c in chains for d in c}

    horizontal_rows: list[list[str]] = []
    for c in chains:
        row = list(c)
        last = c[-1]
        no_out = [e for e in outgoing[last] if e['kind'] == 'no']
        if no_out:
            tail = no_out[0]['tgt']
            if not is_diamond(tail):
                row.append(tail)
        horizontal_rows.append(row)

    process_rows: list[list[str]] = []
    for c in chains:
        row = []
        for d in c:
            yes_out = [e for e in outgoing[d] if e['kind'] == 'yes']
            if yes_out:
                tgt = yes_out[0]['tgt']
                if not is_diamond(tgt):
                    row.append(tgt)
        process_rows.append(row)

    # Pass 5: assign compass ports
    for e in edges:
        src, kind = e['src'], e['kind']
        src_is_diamond = is_diamond(src)
        if src_is_diamond and src in chain_diamonds:
            if kind == 'no':
                e['sp'], e['tp'] = 'e', 'w'
            elif kind == 'yes':
                e['sp'], e['tp'] = 's', 'n'
            else:
                e['sp'], e['tp'] = 's', 'n'
        elif src_is_diamond:
            if kind == 'yes':
                e['sp'], e['tp'] = 's', 'n'
            elif kind == 'no':
                e['sp'], e['tp'] = 'e', 'w'
            else:
                e['sp'], e['tp'] = 's', 'n'
        else:
            outs = outgoing[src]
            if len(outs) == 1:
                e['sp'], e['tp'] = 's', 'n'
            else:
                primaries = [oe for oe in outs if oe['kind'] == 'primary']
                first_primary = primaries[0] if primaries else None
                if kind == 'fault':
                    # Fault branches to the EAST (side) so the primary flow stays
                    # on the vertical spine on the left.
                    e['sp'], e['tp'] = 'e', 'w'
                elif e is first_primary:
                    e['sp'], e['tp'] = 's', 'n'
                elif kind == 'primary':
                    e['sp'], e['tp'] = 'e', 'w'
                else:
                    e['sp'], e['tp'] = 's', 'n'

    # Pass 6: rewrite edges in the source text (reverse order keeps offsets valid)
    for e in sorted(edges, key=lambda x: -x['match'].start()):
        m = e['match']
        src = m.group(1)
        tgt = m.group(3)
        attrs_block = m.group(5) or ''
        new_edge = f'{src}:{e["sp"]} -> {tgt}:{e["tp"]}{attrs_block};'
        dot = dot[:m.start()] + new_edge + dot[m.end():]

    # Pass 7: inject rank=same subgraphs
    rank_blocks: list[str] = []
    for row in horizontal_rows:
        if len(row) >= 2:
            rank_blocks.append('  { rank=same; ' + '; '.join(_vg_quote_if_needed(n) for n in row) + '; }')
    for row in process_rows:
        if len(row) >= 2:
            rank_blocks.append('  { rank=same; ' + '; '.join(_vg_quote_if_needed(n) for n in row) + '; }')
    # Pin fault-branch targets to the same rank as their source process, so they
    # sit side-by-side instead of Graphviz pushing them to another row.
    # Only for SIDE branches (source has 2+ outputs), not vertical continuations
    # of a fault chain (where the fault node has a single downstream step).
    for e in edges:
        if (
            e['kind'] == 'fault'
            and not is_diamond(e['src'])
            and len(outgoing[e['src']]) >= 2
        ):
            pair = [e['src'], e['tgt']]
            rank_blocks.append('  { rank=same; ' + '; '.join(_vg_quote_if_needed(n) for n in pair) + '; }')

    if rank_blocks:
        last_brace = dot.rfind('}')
        if last_brace > 0:
            injection = '\n' + '\n'.join(rank_blocks) + '\n'
            dot = dot[:last_brace] + injection + dot[last_brace:]

    # ------------------------------------------------------------------
    # Pass 8: enforce uniform node size.
    # Every shape (box, diamond, oval, etc.) gets the SAME bounding box
    # so the diagram looks consistent. We:
    #   (a) strip per-node width/height/fixedsize attributes, and
    #   (b) inject fixedsize=true + uniform width/height into the node
    #       default attribute block.
    # ------------------------------------------------------------------
    UNIFORM_W, UNIFORM_H = 1.8, 0.7

    def _strip_size_attrs(body: str) -> str:
        body = _re2.sub(r'\b(?:width|height|fixedsize)\s*=\s*"[^"]*"\s*,?\s*', '', body)
        body = _re2.sub(r'\b(?:width|height|fixedsize)\s*=\s*[^,\]\s]+\s*,?\s*', '', body)
        # clean trailing/leading commas left by the strips
        body = _re2.sub(r',\s*,', ',', body)
        body = body.strip().strip(',').strip()
        return body

    # Strip size attrs from every node declaration (but NOT from edges or defaults)
    # Rebuild by walking _VG_NODE_RE over a masked copy (edges+defaults already masked).
    new_parts = []
    last_idx = 0
    # Re-mask edges and defaults in the current dot
    m_buf = list(dot)
    for m in _VG_EDGE_RE.finditer(dot):
        for i in range(m.start(), m.end()):
            m_buf[i] = ' '
    masked2 = ''.join(m_buf)
    for m in _VG_DEFAULT_RE.finditer(masked2):
        masked2 = masked2[:m.start()] + (' ' * (m.end() - m.start())) + masked2[m.end():]

    node_matches = list(_VG_NODE_RE.finditer(masked2))
    out_buf = []
    cursor = 0
    for m in node_matches:
        name = m.group(1).strip('"')
        if name in ('graph', 'node', 'edge', 'digraph', 'subgraph', 'strict'):
            continue
        body = m.group(2)
        cleaned = _strip_size_attrs(body)
        new_decl = f'{m.group(1)} [{cleaned}]'
        out_buf.append(dot[cursor:m.start()])
        out_buf.append(new_decl)
        cursor = m.end()
    out_buf.append(dot[cursor:])
    dot = ''.join(out_buf)

    # Inject/rewrite the node default block to enforce uniform size.
    node_default_re = _re2.compile(r'node\s*\[([^\]]*)\]\s*;?', _re2.IGNORECASE)
    nd = node_default_re.search(dot)
    if nd:
        inner = nd.group(1)
        inner = _strip_size_attrs(inner)
        if inner and not inner.endswith(','):
            inner = inner + ','
        new_default = f'node [{inner} fixedsize=true, width={UNIFORM_W}, height={UNIFORM_H}]'
        dot = dot[:nd.start()] + new_default + dot[nd.end():]
    else:
        # No node default present — insert one after `digraph NAME {`
        open_brace = dot.find('{')
        if open_brace > 0:
            insertion = f'\n  node [fixedsize=true, width={UNIFORM_W}, height={UNIFORM_H}];\n'
            dot = dot[:open_brace + 1] + insertion + dot[open_brace + 1:]

    # ------------------------------------------------------------------
    # Pass 9: fix Claude-emitted attribute bugs.
    #   - `fill=` is not valid Graphviz; the attribute is `fillcolor=`.
    #     Without this rewrite every node renders gray.
    #   - `shape=note` (the folded-corner document glyph) looks odd mixed
    #     with rectangles/ovals; normalize to `shape=box`.
    # ------------------------------------------------------------------
    dot = _re2.sub(r'\bfill\s*=', 'fillcolor=', dot)
    dot = _re2.sub(r'shape\s*=\s*note\b', 'shape=box', dot)

    return dot

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
    "- Flowchart lines MUST be orthogonal (right angles only, never curved). Use `splines=ortho`.\n"
    "- Every edge MUST attach to the MIDDLE of a node side via compass ports on BOTH ends (`:n`, `:s`, `:e`, `:w`). No corners.\n"
    "- CONNECTION GEOMETRY (Visio convention — follow EXACTLY):\n"
    "    * Main flow is a vertical spine running top-to-bottom. Spine edges ALWAYS use `A:s -> B:n`.\n"
    "    * From a DECISION diamond, the YES (or 'true' / happy-path) branch ALWAYS exits EAST: `Decision:e -> NextStep:n` (or `:w` if the next node sits to the right).\n"
    "    * From a DECISION diamond, the NO (or 'false' / alt-path) branch ALWAYS exits SOUTH — continuing the main spine: `Decision:s -> NextStep:n`.\n"
    "    * The east-side YES branch does its work on the right, then re-enters the main spine by going DOWN and connecting back with `LastSideStep:s -> Rejoin:e` (entering the rejoin node from its east side).\n"
    "    * Never mix directions — do NOT send YES south and NO east. YES = east, NO = south. Every decision in the chart follows this same geometry.\n"
    "    * ACTION / PROCESS nodes with MULTIPLE outgoing edges (e.g. main success path + fault path, main path + alternate branch): the two edges MUST exit from DIFFERENT sides of the node so each edge gets its own clean L-shaped route. Use `Node:s ->` for the primary success path (continuing the spine) and `Node:w ->` for the fault/error path going to a node on the west side (or `Node:e ->` for an alternate branch on the east). NEVER let two edges exit from the same side of the same node — Graphviz will cram them into the same port and the routing will look broken.\n"
    "- FAULT / ERROR paths use a DASHED red edge to visually separate them from the success path: `[style=dashed, color=\"#DC2626\"]`. The fault-target node has `fill=#FEE2E2`.\n"
    "- DECISION EDGE LABELS must be rendered as colored pill badges using HTML-like labels, NOT plain text. Format:\n"
    "    * YES / True label:  `label=<<TABLE BORDER=\"0\" CELLBORDER=\"0\" CELLPADDING=\"2\"><TR><TD BGCOLOR=\"#16A34A\"><FONT COLOR=\"white\" POINT-SIZE=\"9\"><B> YES </B></FONT></TD></TR></TABLE>>`\n"
    "    * NO / False label:  `label=<<TABLE BORDER=\"0\" CELLBORDER=\"0\" CELLPADDING=\"2\"><TR><TD BGCOLOR=\"#DC2626\"><FONT COLOR=\"white\" POINT-SIZE=\"9\"><B> NO </B></FONT></TD></TR></TABLE>>`\n"
    "    * For non-boolean branches (e.g. a named condition), use BGCOLOR=\"#64748B\" (slate) with the condition name.\n"
    "    * Every edge leaving a decision diamond MUST carry one of these pill-badge labels. No plain-text edge labels on decision branches.\n"
    "- Graph defaults: `graph [fontname=\"Helvetica\", bgcolor=\"white\", pad=0.25, ranksep=0.55, nodesep=0.45, size=\"7,9\", dpi=200, splines=ortho]; "
    "node [fontname=\"Helvetica\", fontsize=11, margin=\"0.18,0.1\", height=0.45, width=1.6, style=\"filled\"]; "
    "edge [fontname=\"Helvetica\", fontsize=9, color=\"#64748b\", penwidth=1.1, arrowsize=0.7];`\n"
    "- Follow ISO 5807 / ANSI X3.5 flowchart conventions (the same standard Visio uses by default):\n"
    "    * START / END (terminator)    → `shape=oval`,   fill=#E8F0FE   — rounded oval; every chart has exactly ONE start and at least one end.\n"
    "    * PROCESS / ACTION            → `shape=box`,    fill=#EFF6FF   — any action, assignment, calculation.\n"
    "    * DECISION                    → `shape=diamond`, fill=#FEF3C7  — any yes/no or conditional branch. BOTH outgoing edges MUST have labels (`label=\"Yes\"`, `label=\"No\"`, etc.).\n"
    "    * DATA I/O (Get/Create/Update/Delete Records, input/output) → `shape=parallelogram`, fill=#F5F3FF.\n"
    "    * DATABASE / STORED DATA      → `shape=cylinder`, fill=#F5F3FF — persistent storage operations.\n"
    "    * DOCUMENT                    → `shape=note`,   fill=#F5F3FF   — generated docs, emails, PDFs.\n"
    "    * SCREEN / DISPLAY            → `shape=hexagon`, fill=#F5F3FF  — user-facing screen elements.\n"
    "    * PREDEFINED PROCESS (subflow, Apex action, invocable) → `shape=box, style=\"filled,dashed\"`, fill=#EFF6FF.\n"
    "    * DELAY / WAIT                → `shape=trapezium`, fill=#FEF3C7.\n"
    "    * ERROR / FAULT               → `shape=box`,    fill=#FEE2E2   — fault paths, error handling.\n"
    "    * ON-PAGE CONNECTOR (when ≥2 edges converge to the same node, use this small circle to make the merge explicit) → `shape=circle, label=\"\", width=0.25, height=0.25, fixedsize=true`, fill=#CBD5E1.\n"
    "- Flow direction: top-to-bottom for the main path; branches go left and right; converge back to the vertical spine below.\n"
    "- EVERY decision-diamond outgoing edge MUST carry an explicit `label=\"...\"` (Yes, No, True, False, or the condition name). No unlabeled decision edges.\n"
    "- When two or more edges merge back into the main flow, insert an on-page connector (circle) node at the merge point rather than hitting the next node with multiple arrows at once.\n"
    "- Lines must NEVER cross. If a crossing is unavoidable, add an on-page connector to break the line.\n"
    "- Keep to 10-12 nodes max. Labels 2-4 words. No periods at end of labels.\n"
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

    # Force orthogonal edges — flowcharts must have right-angle lines, never curves.
    # If the model omitted splines=ortho, inject it into the first graph[...] attr
    # block; if there is no graph attribute statement at all, add one right after
    # the opening brace.
    if diag and "splines=ortho" not in diag and "splines = ortho" not in diag:
        graph_attr_re = _re.compile(r'(graph\s*\[)([^\]]*)\]', _re.IGNORECASE)
        m = graph_attr_re.search(diag)
        if m:
            inner = m.group(2).strip().rstrip(',;')
            sep = '' if not inner else (', ' if ',' in inner else ' ')
            new_attrs = f"{inner}{sep}splines=ortho"
            diag = diag[:m.start()] + f"{m.group(1)}{new_attrs}]" + diag[m.end():]
        else:
            diag = _re.sub(
                r'(digraph[^{]*\{)',
                r'\1\n  graph [splines=ortho];',
                diag,
                count=1,
            )

    # --------------------------------------------------------------------
    # Deterministic Visio-geometry post-processor.
    # Replaces the previous port-only rewriter with a topology-aware pass that
    # also injects `rank=same` subgraphs. See _apply_visio_geometry docstring.
    # --------------------------------------------------------------------
    if diag:
        # Capture pre-processor DOT for debugging (what Claude emitted)
        try:
            from pathlib import Path as _DbgPath
            _DbgPath(r"C:\Users\reggi\Downloads\orgscan_last_flow_raw.dot").write_text(diag, encoding="utf-8")
        except Exception:
            pass
        diag = _apply_visio_geometry(diag)
        # Capture post-processor DOT for debugging (what goes to Graphviz)
        try:
            from pathlib import Path as _DbgPath2
            _DbgPath2(r"C:\Users\reggi\Downloads\orgscan_last_flow_final.dot").write_text(diag, encoding="utf-8")
        except Exception:
            pass

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
