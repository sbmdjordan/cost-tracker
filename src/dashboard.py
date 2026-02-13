"""
HTML dashboard generator.
Reads data from Notion and generates a static HTML page with:
- Total spend cards (Total, Work, Personal) in GBP
- Doughnut chart: spend by project
- Progress bars: credit usage for services with limits
- Subscription table with renewal dates
- Recent usage log
"""

import json
import os
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


def generate_dashboard(subscriptions: list, usage_entries: list, output_path: str):
    """Generate the HTML dashboard file.

    Args:
        subscriptions: List of subscription dicts from Notion
        usage_entries: List of usage entry dicts from Notion
        output_path: Where to write the HTML file
    """
    # --- Calculate totals ---
    active_subs = [s for s in subscriptions if s["status"] == "Active"]

    # Monthly subscription costs
    total_subs_gbp = sum(s["monthly_cost_gbp"] for s in active_subs)
    total_subs_usd = sum(s["monthly_cost_usd"] for s in active_subs)
    work_subs_gbp = sum(s["monthly_cost_gbp"] for s in active_subs if s["category"] == "Work")
    personal_subs_gbp = sum(s["monthly_cost_gbp"] for s in active_subs if s["category"] == "Personal")

    # Usage costs this month
    total_usage_gbp = sum(u["cost_gbp"] for u in usage_entries)
    total_usage_usd = sum(u["cost_usd"] for u in usage_entries)
    work_usage_gbp = sum(u["cost_gbp"] for u in usage_entries if u["category"] == "Work")
    personal_usage_gbp = sum(u["cost_gbp"] for u in usage_entries if u["category"] == "Personal")

    # Combined
    total_gbp = total_subs_gbp + total_usage_gbp
    work_gbp = work_subs_gbp + work_usage_gbp
    personal_gbp = personal_subs_gbp + personal_usage_gbp

    total_usd = total_subs_usd + total_usage_usd

    # --- Spend by project (for doughnut) ---
    project_spend = {}
    for u in usage_entries:
        for p in u["projects"]:
            project_spend[p] = project_spend.get(p, 0) + u["cost_gbp"]
    for s in active_subs:
        for p in s["projects"]:
            project_spend[p] = project_spend.get(p, 0) + (s["monthly_cost_gbp"] / max(len(s["projects"]), 1))

    # --- Spend by service (for second doughnut) ---
    service_spend = {}
    for u in usage_entries:
        service_spend[u["service"]] = service_spend.get(u["service"], 0) + u["cost_gbp"]
    for s in active_subs:
        service_spend[s["name"]] = service_spend.get(s["name"], 0) + s["monthly_cost_gbp"]

    # --- Per-project breakdown (project → {service: cost}) ---
    project_service_breakdown = {}
    for u in usage_entries:
        for p in u["projects"]:
            if p not in project_service_breakdown:
                project_service_breakdown[p] = {}
            svc = u["service"]
            project_service_breakdown[p][svc] = project_service_breakdown[p].get(svc, 0) + u["cost_gbp"]
    for s in active_subs:
        if s["monthly_cost_gbp"] > 0:
            share = s["monthly_cost_gbp"] / max(len(s["projects"]), 1)
            for p in s["projects"]:
                if p not in project_service_breakdown:
                    project_service_breakdown[p] = {}
                project_service_breakdown[p][s["name"]] = project_service_breakdown[p].get(s["name"], 0) + share

    # --- Credit usage (for progress bars) ---
    credit_services = [
        s for s in active_subs
        if s["credits_included"] > 0
    ]

    # --- Build data for template ---
    today = date.today()
    month_name = today.strftime("%B %Y")

    project_labels = json.dumps(list(project_spend.keys()))
    project_values = json.dumps([round(v, 2) for v in project_spend.values()])

    service_labels = json.dumps(list(service_spend.keys()))
    service_values = json.dumps([round(v, 2) for v in service_spend.values()])

    # Subscription table rows
    sub_rows = ""
    for s in sorted(active_subs, key=lambda x: x["monthly_cost_gbp"], reverse=True):
        renewal = s["next_renewal"] or "-"
        cost_display = f"£{s['monthly_cost_gbp']:.2f}" if s["monthly_cost_gbp"] > 0 else f"${s['monthly_cost_usd']:.2f}"
        cycle = s["billing_cycle"]
        projects_str = ", ".join(s["projects"]) if s["projects"] else "-"
        category_class = "work" if s["category"] == "Work" else "personal"
        usage_display = ""
        if s["usage_gbp"] > 0:
            usage_display = f"£{s['usage_gbp']:.2f}"
        elif s["usage_usd"] > 0:
            usage_display = f"${s['usage_usd']:.2f}"
        sub_rows += f"""
            <tr>
                <td>{s['name']}</td>
                <td><span class="badge {category_class}">{s['category']}</span></td>
                <td>{s['service_type']}</td>
                <td class="number">{cost_display}</td>
                <td class="number">{usage_display}</td>
                <td>{cycle}</td>
                <td>{renewal}</td>
                <td class="projects">{projects_str}</td>
            </tr>"""

    # Credit progress bars
    progress_bars = ""
    for s in credit_services:
        used = s["credits_used"]
        included = s["credits_included"]
        pct = min(round((used / included) * 100, 1), 100) if included > 0 else 0
        color = "green" if pct < 60 else ("orange" if pct < 85 else "red")
        progress_bars += f"""
            <div class="progress-item">
                <div class="progress-header">
                    <span class="progress-label">{s['name']}</span>
                    <span class="progress-value">{used:,.1f} / {included:,.1f} ({pct}%)</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {color}" style="width: {pct}%"></div>
                </div>
            </div>"""

    if not progress_bars:
        progress_bars = '<p class="muted">No services with credit limits configured yet. Set "Credits Included" on a subscription in Notion.</p>'

    # Build project→category mapping from actual data
    project_category_map = {}
    for u in usage_entries:
        for p in u["projects"]:
            if p not in project_category_map and u["category"]:
                project_category_map[p] = u["category"]
    for s in active_subs:
        for p in s["projects"]:
            if p not in project_category_map and s["category"]:
                project_category_map[p] = s["category"]

    # Project breakdown rows
    project_breakdown_html = ""
    for proj_name in sorted(project_service_breakdown.keys(), key=lambda p: sum(project_service_breakdown[p].values()), reverse=True):
        services = project_service_breakdown[proj_name]
        proj_total = sum(services.values())
        if proj_total <= 0:
            continue
        proj_cat = project_category_map.get(proj_name, "Work")
        cat_class = "personal" if proj_cat == "Personal" else "work"
        breakdown_parts = []
        for svc_name in sorted(services.keys(), key=lambda k: services[k], reverse=True):
            svc_cost = services[svc_name]
            if svc_cost > 0:
                breakdown_parts.append(f"{svc_name}: £{svc_cost:.2f}")
        breakdown_str = " &middot; ".join(breakdown_parts) if breakdown_parts else "-"
        project_breakdown_html += f"""
            <tr>
                <td><strong>{proj_name}</strong></td>
                <td><span class="badge {cat_class}">{proj_cat}</span></td>
                <td class="number" style="font-size:18px;font-weight:700;">£{proj_total:.2f}</td>
                <td class="projects" style="font-size:13px;">{breakdown_str}</td>
            </tr>"""

    if not project_breakdown_html:
        project_breakdown_html = '<tr><td colspan="4" class="muted">No project costs recorded yet.</td></tr>'

    # Recent usage rows
    usage_rows = ""
    for u in usage_entries[:20]:
        projects_str = ", ".join(u["projects"]) if u["projects"] else "-"
        cost_display = f"£{u['cost_gbp']:.2f}" if u["cost_gbp"] > 0 else f"${u['cost_usd']:.2f}"
        source_class = "auto" if u["source"] == "Auto" else "manual"
        usage_rows += f"""
            <tr>
                <td>{u['date'] or '-'}</td>
                <td>{u['service']}</td>
                <td class="projects">{projects_str}</td>
                <td class="number">{cost_display}</td>
                <td><span class="badge {source_class}">{u['source']}</span></td>
            </tr>"""

    if not usage_rows:
        usage_rows = '<tr><td colspan="5" class="muted">No usage entries this month yet.</td></tr>'

    # Chart colors
    colors = [
        "'#6366f1'", "'#8b5cf6'", "'#ec4899'", "'#f43f5e'",
        "'#f97316'", "'#eab308'", "'#22c55e'", "'#14b8a6'",
        "'#06b6d4'", "'#3b82f6'", "'#a855f7'", "'#d946ef'",
    ]
    project_colors = json.dumps([c.strip("'") for c in colors[:len(project_spend)]])
    service_colors = json.dumps([c.strip("'") for c in colors[:len(service_spend)]])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cost Tracker Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 24px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .subtitle {{
            color: #94a3b8;
            font-size: 14px;
            margin-bottom: 32px;
        }}

        /* Summary Cards */
        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
        }}
        .card-label {{
            font-size: 13px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .card-value {{
            font-size: 36px;
            font-weight: 700;
        }}
        .card-value.total {{ color: #f8fafc; }}
        .card-value.work {{ color: #6366f1; }}
        .card-value.personal {{ color: #ec4899; }}
        .card-sub {{
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }}

        /* Charts section */
        .charts {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 32px;
        }}
        .chart-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
        }}
        .chart-card h2 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        .chart-container {{
            position: relative;
            max-height: 300px;
            display: flex;
            justify-content: center;
        }}

        /* Progress bars */
        .progress-section {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
            margin-bottom: 32px;
        }}
        .progress-section h2 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        .progress-item {{
            margin-bottom: 16px;
        }}
        .progress-item:last-child {{
            margin-bottom: 0;
        }}
        .progress-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
            font-size: 14px;
        }}
        .progress-label {{ font-weight: 500; }}
        .progress-value {{ color: #94a3b8; }}
        .progress-bar {{
            height: 12px;
            background: #334155;
            border-radius: 6px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 6px;
            transition: width 0.5s ease;
        }}
        .progress-fill.green {{ background: linear-gradient(90deg, #22c55e, #4ade80); }}
        .progress-fill.orange {{ background: linear-gradient(90deg, #f97316, #fb923c); }}
        .progress-fill.red {{ background: linear-gradient(90deg, #ef4444, #f87171); }}

        /* Tables */
        .table-section {{
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            border: 1px solid #334155;
            margin-bottom: 32px;
            overflow-x: auto;
        }}
        .table-section h2 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 2px solid #334155;
            color: #94a3b8;
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #1e293b;
        }}
        tr:hover td {{
            background: #253148;
        }}
        td.number {{
            font-variant-numeric: tabular-nums;
            font-weight: 500;
        }}
        td.projects {{
            font-size: 12px;
            color: #94a3b8;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .badge.work {{ background: #312e81; color: #a5b4fc; }}
        .badge.personal {{ background: #831843; color: #f9a8d4; }}
        .badge.auto {{ background: #064e3b; color: #6ee7b7; }}
        .badge.manual {{ background: #78350f; color: #fcd34d; }}

        .muted {{ color: #64748b; font-style: italic; }}

        @media (max-width: 768px) {{
            .charts {{ grid-template-columns: 1fr; }}
            .cards {{ grid-template-columns: 1fr 1fr; }}
            body {{ padding: 16px; }}
            .card-value {{ font-size: 28px; }}
        }}
    </style>
</head>
<body>
    <h1>Cost Tracker</h1>
    <p class="subtitle">Updated {datetime.now().strftime('%d %b %Y at %H:%M')} &middot; {month_name}</p>

    <!-- Summary Cards -->
    <div class="cards">
        <div class="card">
            <div class="card-label">Total Monthly</div>
            <div class="card-value total">&pound;{total_gbp:.2f}</div>
            <div class="card-sub">${total_usd:.2f} USD</div>
        </div>
        <div class="card">
            <div class="card-label">Work</div>
            <div class="card-value work">&pound;{work_gbp:.2f}</div>
        </div>
        <div class="card">
            <div class="card-label">Personal</div>
            <div class="card-value personal">&pound;{personal_gbp:.2f}</div>
        </div>
        <div class="card">
            <div class="card-label">API Usage This Month</div>
            <div class="card-value total">&pound;{total_usage_gbp:.2f}</div>
            <div class="card-sub">${total_usage_usd:.2f} USD</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="charts">
        <div class="chart-card">
            <h2>Spend by Project</h2>
            <div class="chart-container">
                <canvas id="projectChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h2>Spend by Service</h2>
            <div class="chart-container">
                <canvas id="serviceChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Credit Usage -->
    <div class="progress-section">
        <h2>Credit Usage</h2>
        {progress_bars}
    </div>

    <!-- Project Cost Breakdown -->
    <div class="table-section">
        <h2>Cost by Project</h2>
        <table>
            <thead>
                <tr>
                    <th>Project</th>
                    <th>Category</th>
                    <th>Total</th>
                    <th>Breakdown (by service)</th>
                </tr>
            </thead>
            <tbody>
                {project_breakdown_html}
            </tbody>
        </table>
    </div>

    <!-- Subscriptions Table -->
    <div class="table-section">
        <h2>Active Subscriptions &amp; Services</h2>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Type</th>
                    <th>Monthly Cost</th>
                    <th>Usage</th>
                    <th>Cycle</th>
                    <th>Next Renewal</th>
                    <th>Projects</th>
                </tr>
            </thead>
            <tbody>
                {sub_rows}
            </tbody>
        </table>
    </div>

    <!-- Recent Usage -->
    <div class="table-section">
        <h2>Recent Usage ({month_name})</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Service</th>
                    <th>Project</th>
                    <th>Cost</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
                {usage_rows}
            </tbody>
        </table>
    </div>

    <script>
        const chartOptions = {{
            responsive: true,
            maintainAspectRatio: true,
            plugins: {{
                legend: {{
                    position: 'bottom',
                    labels: {{
                        color: '#94a3b8',
                        padding: 16,
                        font: {{ size: 12 }}
                    }}
                }},
                tooltip: {{
                    callbacks: {{
                        label: function(ctx) {{
                            return ctx.label + ': \\u00a3' + ctx.parsed.toFixed(2);
                        }}
                    }}
                }}
            }}
        }};

        new Chart(document.getElementById('projectChart'), {{
            type: 'doughnut',
            data: {{
                labels: {project_labels},
                datasets: [{{
                    data: {project_values},
                    backgroundColor: {project_colors},
                    borderWidth: 0,
                    hoverOffset: 8,
                }}]
            }},
            options: chartOptions
        }});

        new Chart(document.getElementById('serviceChart'), {{
            type: 'doughnut',
            data: {{
                labels: {service_labels},
                datasets: [{{
                    data: {service_values},
                    backgroundColor: {service_colors},
                    borderWidth: 0,
                    hoverOffset: 8,
                }}]
            }},
            options: chartOptions
        }});
    </script>
</body>
</html>"""

    # Write file
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Dashboard generated: {output_path}")
