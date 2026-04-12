import csv
import io
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


class ReportGenerator:
    def __init__(
        self,
        phase1_report: dict,
        phase2_findings: dict,
        phase3_verified: dict,
        execution_history: List[dict] = None,
    ):
        self.phase1_report = phase1_report
        self.phase2_findings = phase2_findings
        self.phase3_verified = phase3_verified
        self.execution_history = execution_history or []

    def generate_json_report(self) -> dict:
        return {
            "metadata": self._compute_metadata(),
            "summary": self._compute_summary_stats(),
            "by_type": self._compute_by_type(),
            "by_risk": self._compute_by_risk(),
            "execution_history": self._compute_progress(),
            "recommendations": self._compute_recommendations(),
        }

    def _compute_metadata(self) -> dict:
        phases_run = [1]
        if self.phase2_findings:
            phases_run.append(2)
        if self.phase3_verified:
            phases_run.append(3)
        if self.execution_history:
            phases_run.append(5)

        project = (
            self.phase1_report.get("project", {}).get("name", "unknown")
            if self.phase1_report
            else "unknown"
        )

        start_time = self.phase1_report.get("start_time") if self.phase1_report else None
        duration = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                duration = round((datetime.now() - start_dt).total_seconds() / 60, 1)
            except (ValueError, TypeError):
                duration = None

        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "project": project,
            "phases_run": phases_run,
            "audit_duration_minutes": duration,
        }

    def _compute_summary_stats(self) -> dict:
        findings = self.phase2_findings.get("findings", []) if self.phase2_findings else []
        total_findings = len(findings)

        removed_ids = self._get_removed_ids()
        removed = len(removed_ids)
        remaining = total_findings - removed

        # Estimated lines removable from phase3 verified items
        verified = self.phase3_verified.get("verified", []) if self.phase3_verified else []
        estimated_lines_removable = sum(
            item.get("lines", 0) for item in verified
        )

        # Lines already removed from execution history
        lines_removed = sum(
            batch.get("lines_removed", 0) for batch in self.execution_history
        )
        estimated_lines_remaining = max(0, estimated_lines_removable - lines_removed)

        # Safety percentage: average confidence of verified items
        confidences = [
            item.get("confidence", 0) for item in verified if "confidence" in item
        ]
        safety_percentage = (
            round(sum(confidences) / len(confidences) * 100)
            if confidences
            else 0
        )

        return {
            "total_findings": total_findings,
            "removed": removed,
            "remaining": remaining,
            "estimated_lines_removable": estimated_lines_removable,
            "estimated_lines_remaining": estimated_lines_remaining,
            "safety_percentage": safety_percentage,
        }

    def _compute_by_type(self) -> dict:
        findings = self.phase2_findings.get("findings", []) if self.phase2_findings else []
        removed_ids = self._get_removed_ids()

        type_map = {
            "unused_exports": "unused_export",
            "orphan_files": "orphan_file",
            "unused_imports": "unused_import",
        }

        result = {}
        for label, finding_type in type_map.items():
            items = [f for f in findings if f.get("type") == finding_type]
            removed = [f for f in items if f.get("id") in removed_ids]
            result[label] = {
                "total": len(items),
                "removed": len(removed),
                "remaining": len(items) - len(removed),
            }

        return result

    def _compute_by_risk(self) -> dict:
        findings = self.phase2_findings.get("findings", []) if self.phase2_findings else []
        removed_ids = self._get_removed_ids()

        risk_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        result = {}
        for level in risk_levels:
            items = [f for f in findings if f.get("risk") == level]
            removed = [f for f in items if f.get("id") in removed_ids]
            result[level] = {
                "total": len(items),
                "removed": len(removed),
                "remaining": len(items) - len(removed),
            }

        return result

    def _compute_progress(self) -> list:
        batches = []
        for batch in self.execution_history:
            batches.append({
                "batch_id": batch.get("batch_id", ""),
                "timestamp": batch.get("timestamp", ""),
                "items": batch.get("items", []),
                "item_names": batch.get("item_names", []),
                "lines_removed": batch.get("lines_removed", 0),
                "commit_hash": batch.get("commit_hash", ""),
                "branch": batch.get("branch", ""),
            })
        return batches

    def _compute_recommendations(self) -> list:
        verified = self.phase3_verified.get("verified", []) if self.phase3_verified else []
        removed_ids = self._get_removed_ids()

        # Filter to LOW risk, not yet removed, sorted by lines descending
        candidates = [
            item for item in verified
            if item.get("id") not in removed_ids and item.get("risk", "HIGH") == "LOW"
        ]
        candidates.sort(key=lambda x: x.get("lines", 0), reverse=True)

        return [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "estimated_lines": item.get("lines", 0),
                "estimated_safety": round(item.get("confidence", 0) * 100),
            }
            for item in candidates[:10]
        ]

    def _get_removed_ids(self) -> set:
        removed = set()
        for batch in self.execution_history:
            removed.update(batch.get("items", []))
        return removed


class HTMLExporter:
    _RISK_COLORS = {
        "CRITICAL": ("#dc3545", "#f8d7da"),
        "HIGH":     ("#fd7e14", "#fff3cd"),
        "MEDIUM":   ("#ffc107", "#fff8e1"),
        "LOW":      ("#198754", "#d1e7dd"),
    }

    def __init__(self, report_data: dict):
        self.data = report_data

    def generate_html(self) -> str:
        return "\n".join([
            "<!DOCTYPE html>",
            '<html lang="en" data-bs-theme="light">',
            self._generate_head(),
            "<body>",
            self._generate_header(),
            '<main class="container-xl py-4">',
            self._generate_summary_section(),
            self._generate_charts_section(),
            self._generate_findings_table(),
            "</main>",
            self._generate_footer_scripts(),
            "</body>",
            "</html>",
        ])

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    def _generate_head(self) -> str:
        meta = self.data.get("metadata", {})
        project = meta.get("project", "Unknown Project")
        return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Code Audit Report – {self._esc(project)}</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet"
        href="https://cdn.datatables.net/1.13.8/css/dataTables.bootstrap5.min.css">
  <style>
    :root {{
      --ca-primary: #0d6efd;
      --ca-critical: #dc3545;
      --ca-high: #fd7e14;
      --ca-medium: #ffc107;
      --ca-low: #198754;
    }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; }}
    .report-header {{
      background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
      color: #fff;
      padding: 2.5rem 0 2rem;
    }}
    .score-circle {{
      width: 90px; height: 90px;
      border-radius: 50%;
      border: 4px solid rgba(255,255,255,0.6);
      display: flex; align-items: center; justify-content: center;
      font-size: 1.5rem; font-weight: 700;
    }}
    .kpi-card {{ border: none; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .kpi-value {{ font-size: 2rem; font-weight: 700; line-height: 1; }}
    .kpi-label {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; }}
    .chart-card {{ border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .risk-CRITICAL {{ background: #f8d7da !important; color: #842029 !important; font-weight: 600; }}
    .risk-HIGH     {{ background: #fff3cd !important; color: #664d03 !important; font-weight: 600; }}
    .risk-MEDIUM   {{ background: #fff8e1 !important; color: #664d03 !important; }}
    .risk-LOW      {{ background: #d1e7dd !important; color: #0f5132 !important; }}
    .status-removed  {{ color: #198754; font-weight: 600; }}
    .status-remaining {{ color: #6c757d; }}
    #theme-toggle {{ cursor: pointer; }}
    @media print {{
      .report-header {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .no-print {{ display: none !important; }}
    }}
    [data-bs-theme="dark"] body {{ background: #121212; color: #e0e0e0; }}
    [data-bs-theme="dark"] .kpi-card,
    [data-bs-theme="dark"] .chart-card {{ background: #1e1e1e; color: #e0e0e0; }}
    [data-bs-theme="dark"] .risk-CRITICAL {{ background: #4a1520 !important; color: #f5c2c7 !important; }}
    [data-bs-theme="dark"] .risk-HIGH     {{ background: #3d2800 !important; color: #ffda6a !important; }}
    [data-bs-theme="dark"] .risk-MEDIUM   {{ background: #332600 !important; color: #ffda6a !important; }}
    [data-bs-theme="dark"] .risk-LOW      {{ background: #051b11 !important; color: #75b798 !important; }}
  </style>
</head>"""

    def _generate_header(self) -> str:
        meta = self.data.get("metadata", {})
        summary = self.data.get("summary", {})
        project = self._esc(meta.get("project", "Unknown Project"))
        ts = self._esc(meta.get("timestamp", datetime.now().isoformat(timespec="seconds")))
        score = summary.get("safety_percentage", 0)
        score_cls = "text-success" if score >= 80 else ("text-warning" if score >= 50 else "text-danger")
        phases = ", ".join(f"Phase {p}" for p in meta.get("phases_run", []))
        duration = meta.get("audit_duration_minutes")
        duration_str = f"{duration} min" if duration else "N/A"

        return f"""<header class="report-header">
  <div class="container-xl">
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-3">
      <div>
        <h1 class="mb-1 fw-bold">Code Audit Report</h1>
        <p class="mb-1 opacity-75 fs-5">{project}</p>
        <small class="opacity-60">{ts} &nbsp;·&nbsp; {phases} &nbsp;·&nbsp; {duration_str}</small>
      </div>
      <div class="d-flex align-items-center gap-3">
        <div class="text-center">
          <div class="score-circle mx-auto mb-1">
            <span class="{score_cls}">{score}%</span>
          </div>
          <small class="opacity-75">Safety Score</small>
        </div>
        <button id="theme-toggle" class="btn btn-outline-light btn-sm no-print"
                onclick="toggleTheme()">🌙 Dark</button>
        <button class="btn btn-outline-light btn-sm no-print"
                onclick="window.print()">🖨 Print</button>
      </div>
    </div>
  </div>
</header>"""

    def _generate_summary_section(self) -> str:
        s = self.data.get("summary", {})
        cards = [
            ("Total Findings",   s.get("total_findings", 0),           "primary", "🔍"),
            ("Items Removed",    s.get("removed", 0),                   "success", "✅"),
            ("Lines Removed",    s.get("estimated_lines_removable", 0), "info",    "📉"),
            ("Safety Score",     f"{s.get('safety_percentage', 0)}%",   "warning", "🛡️"),
        ]
        cols = []
        for label, value, color, icon in cards:
            cols.append(f"""
      <div class="col-6 col-lg-3">
        <div class="card kpi-card p-3 h-100">
          <div class="d-flex align-items-center gap-2 mb-2">
            <span class="fs-4">{icon}</span>
            <span class="kpi-label text-{color}">{label}</span>
          </div>
          <div class="kpi-value text-{color}">{value}</div>
        </div>
      </div>""")

        # Progress bar
        total = s.get("total_findings", 1) or 1
        removed = s.get("removed", 0)
        pct = round(removed / total * 100)
        progress_html = f"""
      <div class="col-12 mt-2">
        <div class="card kpi-card p-3">
          <div class="d-flex justify-content-between mb-1">
            <span class="fw-semibold">Removal Progress</span>
            <span class="text-muted">{removed} / {total} ({pct}%)</span>
          </div>
          <div class="progress" style="height:14px; border-radius:8px;">
            <div class="progress-bar bg-success" role="progressbar"
                 style="width:{pct}%" aria-valuenow="{pct}"
                 aria-valuemin="0" aria-valuemax="100">{pct}%</div>
          </div>
        </div>
      </div>"""

        return f"""<section class="mb-4">
  <h2 class="h5 fw-semibold mb-3">Summary</h2>
  <div class="row g-3">
    {''.join(cols)}
    {progress_html}
  </div>
</section>"""

    def _generate_charts_section(self) -> str:
        by_type = self.data.get("by_type", {})
        by_risk = self.data.get("by_risk", {})

        # Pie data – by type
        type_labels = list(by_type.keys())
        type_totals = [by_type[k].get("total", 0) for k in type_labels]
        type_colors = ["#0d6efd", "#20c997", "#fd7e14"]

        # Bar data – by risk
        risk_labels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        risk_totals = [by_risk.get(r, {}).get("total", 0) for r in risk_labels]
        risk_removed = [by_risk.get(r, {}).get("removed", 0) for r in risk_labels]
        risk_colors = ["#dc3545", "#fd7e14", "#ffc107", "#198754"]

        return f"""<section class="mb-4">
  <h2 class="h5 fw-semibold mb-3">Analytics</h2>
  <div class="row g-3">
    <div class="col-md-5">
      <div class="card chart-card p-3 h-100">
        <h3 class="h6 fw-semibold mb-3">Findings by Type</h3>
        <canvas id="pieChart" style="max-height:240px;"></canvas>
      </div>
    </div>
    <div class="col-md-7">
      <div class="card chart-card p-3 h-100">
        <h3 class="h6 fw-semibold mb-3">Findings by Risk Level</h3>
        <canvas id="barChart" style="max-height:240px;"></canvas>
      </div>
    </div>
  </div>
</section>
<script>
  window._chartData = {{
    pie: {{
      labels: {type_labels},
      totals: {type_totals},
      colors: {type_colors}
    }},
    bar: {{
      labels: {risk_labels},
      totals: {risk_totals},
      removed: {risk_removed},
      colors: {risk_colors}
    }}
  }};
</script>"""

    def _generate_findings_table(self) -> str:
        findings = (
            self.data.get("_findings_raw", [])
            or self.data.get("findings", [])
        )
        if not findings:
            return """<section class="mb-4">
  <h2 class="h5 fw-semibold mb-3">Findings</h2>
  <div class="alert alert-info">No findings data available in this report.</div>
</section>"""

        rows = []
        for f in findings:
            fid = self._esc(str(f.get("id", "")))
            ftype = self._esc(f.get("type", ""))
            ffile = self._esc(f.get("file", f.get("path", "")))
            fname = self._esc(f.get("name", f.get("item", "")))
            risk = f.get("risk", "LOW")
            risk_safe = self._esc(risk)
            conf = f.get("confidence", 0)
            conf_pct = f"{round(conf * 100)}%" if isinstance(conf, float) else self._esc(str(conf))
            status = "Removed" if f.get("removed") else "Remaining"
            status_cls = "status-removed" if f.get("removed") else "status-remaining"

            rows.append(f"""<tr>
      <td><code class="small">{fid}</code></td>
      <td>{ftype}</td>
      <td class="text-break small">{ffile}</td>
      <td>{fname}</td>
      <td><span class="badge risk-{risk_safe} px-2 py-1">{risk_safe}</span></td>
      <td>{conf_pct}</td>
      <td class="{status_cls}">{status}</td>
    </tr>""")

        rows_html = "\n    ".join(rows)
        return f"""<section class="mb-4">
  <h2 class="h5 fw-semibold mb-3">Findings Detail</h2>
  <div class="card chart-card p-3">
    <table id="findingsTable" class="table table-hover table-sm w-100">
      <thead class="table-light">
        <tr>
          <th>ID</th>
          <th>Type</th>
          <th>File</th>
          <th>Item</th>
          <th>Risk</th>
          <th>Confidence</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
    {rows_html}
      </tbody>
    </table>
  </div>
</section>"""

    def _generate_footer_scripts(self) -> str:
        return """<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.8/js/dataTables.bootstrap5.min.js"></script>
<script>
// ── Charts ──────────────────────────────────────────────────────────────
(function () {
  const d = window._chartData || {};

  if (d.pie) {
    new Chart(document.getElementById('pieChart'), {
      type: 'doughnut',
      data: {
        labels: d.pie.labels,
        datasets: [{ data: d.pie.totals, backgroundColor: d.pie.colors, hoverOffset: 6 }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}` } }
        }
      }
    });
  }

  if (d.bar) {
    new Chart(document.getElementById('barChart'), {
      type: 'bar',
      data: {
        labels: d.bar.labels,
        datasets: [
          { label: 'Total',   data: d.bar.totals,   backgroundColor: d.bar.colors.map(c => c + '99') },
          { label: 'Removed', data: d.bar.removed,  backgroundColor: d.bar.colors }
        ]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }
})();

// ── DataTable ────────────────────────────────────────────────────────────
$(function () {
  if ($('#findingsTable').length) {
    $('#findingsTable').DataTable({
      pageLength: 25,
      order: [[4, 'asc']],
      columnDefs: [{ orderable: false, targets: [] }],
      language: { search: '🔍 Search:' }
    });
  }
});

// ── Dark / Light toggle ──────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-bs-theme') === 'dark';
  html.setAttribute('data-bs-theme', isDark ? 'light' : 'dark');
  document.getElementById('theme-toggle').textContent = isDark ? '🌙 Dark' : '☀️ Light';
}
</script>"""

    @staticmethod
    def _esc(text: str) -> str:
        """Minimal HTML escaping for untrusted strings."""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )


class CSVExporter:
    """Export audit findings to CSV (importable by Excel / Google Sheets)."""

    COLUMNS = ["ID", "Type", "File", "Item", "Risk", "Confidence", "Status", "Execution", "Notes"]

    def __init__(self, report_data: dict):
        self.data = report_data
        # Build lookup: finding_id -> (batch_id, notes) from execution history
        self._execution_map: dict[str, tuple[str, str]] = {}
        for batch in report_data.get("execution_history", []):
            batch_id = batch.get("batch_id", "")
            lines = batch.get("lines_removed", 0)
            note = f"Removed {lines} lines" if lines else "Removed"
            for fid in batch.get("items", []):
                self._execution_map[str(fid)] = (batch_id, note)

    def generate_csv(self) -> str:
        findings = (
            self.data.get("_findings_raw", [])
            or self.data.get("findings", [])
        )

        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
        writer.writerow(self.COLUMNS)

        for f in findings:
            fid = str(f.get("id", ""))
            ftype = f.get("type", "")
            ffile = f.get("file", f.get("path", ""))
            fname = f.get("name", f.get("item", ""))
            risk = f.get("risk", "")
            confidence = f.get("confidence", "")
            if isinstance(confidence, float):
                confidence = f"{confidence:.2f}"

            if fid in self._execution_map:
                status = "REMOVED"
                execution, notes = self._execution_map[fid]
            else:
                status = f.get("status", "PENDING").upper()
                execution = ""
                notes = f.get("notes", f.get("reason", ""))

            writer.writerow([fid, ftype, ffile, fname, risk, confidence, status, execution, notes])

        return buf.getvalue()


class DashboardGenerator:
    """Generate a beautiful ASCII dashboard for the terminal."""

    _RISK_ICONS = {
        "CRITICAL": "🚫",
        "HIGH":     "⚠️ ",
        "MEDIUM":   "⚡",
        "LOW":      "✅",
    }
    _TYPE_ICONS = {
        "unused_exports": "📤",
        "orphan_files":   "🗂️ ",
        "unused_imports": "📥",
    }
    _WIDTH = 60  # inner content width (between ║ borders)

    def __init__(self, report_data: dict):
        self.data = report_data

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def generate_dashboard(self) -> str:
        W = self._WIDTH
        lines: List[str] = []

        lines += self._box_top(W)
        lines += self._box_row("  CODE AUDIT DASHBOARD", W, center=True)
        lines += self._box_divider(W)

        lines += self._section_overall_progress(W)
        lines += self._box_divider(W)

        lines += self._section_by_type(W)
        lines += self._box_divider(W)

        lines += self._section_by_risk(W)
        lines += self._box_divider(W)

        lines += self._section_execution_history(W)
        lines += self._box_divider(W)

        lines += self._section_next_batch(W)
        lines += self._box_divider(W)

        lines += self._section_key_metrics(W)
        lines += self._box_bottom(W)

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Sections                                                              #
    # ------------------------------------------------------------------ #

    def _section_overall_progress(self, W: int) -> List[str]:
        s = self.data.get("summary", {})
        total     = s.get("total_findings", 0)
        removed   = s.get("removed", 0)
        remaining = s.get("remaining", total - removed)
        pct       = round(removed / total * 100) if total else 0

        lines  = self._box_row("  OVERALL PROGRESS", W)
        lines += self._box_row(f"  Total findings : {total}", W)
        lines += self._box_row(f"  Removed        : {removed}", W)
        lines += self._box_row(f"  Remaining      : {remaining}", W)
        # overhead: "  [" (3) + "] " (2) + "100%" (4) = 9 chars
        bar    = self._format_progress_bar(removed, total, width=W - 9)
        lines += self._box_row(f"  [{bar}] {pct:3d}%", W)
        return lines

    def _section_by_type(self, W: int) -> List[str]:
        by_type = self.data.get("by_type", {})
        lines   = self._box_row("  BY TYPE", W)
        for key, icon in self._TYPE_ICONS.items():
            stats = by_type.get(key, {})
            total   = stats.get("total", 0)
            removed = stats.get("removed", 0)
            label   = key.replace("_", " ").title()
            lines  += self._box_row(
                f"  {icon} {label:<22} {total:>4} total  {removed:>4} removed", W
            )
        return lines

    def _section_by_risk(self, W: int) -> List[str]:
        by_risk = self.data.get("by_risk", {})
        lines   = self._box_row("  BY RISK", W)
        for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            stats     = by_risk.get(level, {})
            total     = stats.get("total", 0)
            remaining = stats.get("remaining", total)
            icon      = self._RISK_ICONS[level]
            suffix    = "  ← best targets" if level == "LOW" else ""
            lines    += self._box_row(
                f"  {icon} {level:<10} {remaining:>4} remaining{suffix}", W
            )
        return lines

    def _section_execution_history(self, W: int) -> List[str]:
        history = self.data.get("execution_history", [])
        lines   = self._box_row("  EXECUTION HISTORY", W)
        if not history:
            lines += self._box_row("  No executions yet.", W)
            return lines

        for batch in history[-5:]:  # show last 5 batches
            bid     = batch.get("batch_id", "?")
            ts      = batch.get("timestamp", "")[:16].replace("T", " ")
            items   = len(batch.get("items", []))
            lremoved = batch.get("lines_removed", 0)
            commit  = batch.get("commit_hash", "")[:7]
            lines  += self._box_row(f"  ▸ {bid}", W)
            lines  += self._box_row(
                f"    {ts}  items={items}  lines={lremoved}  commit={commit}", W
            )
        return lines

    def _section_next_batch(self, W: int) -> List[str]:
        candidates = self._calculate_next_batch()
        lines = self._box_row("  RECOMMENDED NEXT BATCH", W)
        if not candidates:
            lines += self._box_row("  No safe candidates available.", W)
            return lines

        recs = self.data.get("recommendations", [])
        rec_map = {r["id"]: r for r in recs}
        for cid in candidates:
            rec   = rec_map.get(cid, {})
            name  = rec.get("name", cid)[:28]
            lines_est = rec.get("estimated_lines", 0)
            safety    = rec.get("estimated_safety", 0)
            lines    += self._box_row(
                f"  ✦ {name:<30} ~{lines_est:>4}L  safety={safety}%", W
            )
        return lines

    def _section_key_metrics(self, W: int) -> List[str]:
        s         = self.data.get("summary", {})
        removable = s.get("estimated_lines_removable", 0)
        removed   = s.get("estimated_lines_remaining", 0)
        safety    = s.get("safety_percentage", 0)

        total_lines_removed = sum(
            b.get("lines_removed", 0)
            for b in self.data.get("execution_history", [])
        )

        # Rough ETA: if we know average batch size from history
        history = self.data.get("execution_history", [])
        remaining_items = s.get("remaining", 0)
        if history and remaining_items:
            avg_per_batch = sum(
                len(b.get("items", [])) for b in history
            ) / len(history)
            batches_left = round(remaining_items / avg_per_batch) if avg_per_batch else "?"
            eta_str = f"~{batches_left} more batch(es)"
        else:
            eta_str = "N/A"

        lines  = self._box_row("  KEY METRICS", W)
        lines += self._box_row(f"  Total lines removable  : {removable:>6}", W)
        lines += self._box_row(f"  Total lines removed    : {total_lines_removed:>6}", W)
        lines += self._box_row(f"  Lines still remaining  : {removed:>6}", W)
        lines += self._box_row(f"  Average safety         : {safety:>5}%", W)
        lines += self._box_row(f"  Est. to completion     : {eta_str}", W)
        return lines

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _format_progress_bar(current: int, total: int, width: int = 40) -> str:
        if total == 0:
            filled = 0
        else:
            filled = round(current / total * width)
        filled = max(0, min(filled, width))
        bar = "█" * filled + "░" * (width - filled)
        return bar

    def _calculate_next_batch(self) -> List[str]:
        """Return IDs of top 3-5 LOW-risk candidates not yet removed."""
        recs = self.data.get("recommendations", [])
        return [r["id"] for r in recs[:5]]

    # ------------------------------------------------------------------ #
    # Box-drawing primitives                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _box_top(W: int) -> List[str]:
        return [f"╔{'═' * (W + 2)}╗"]

    @staticmethod
    def _box_bottom(W: int) -> List[str]:
        return [f"╚{'═' * (W + 2)}╝"]

    @staticmethod
    def _box_divider(W: int) -> List[str]:
        return [f"╠{'═' * (W + 2)}╣"]

    @staticmethod
    def _box_row(text: str, W: int, center: bool = False) -> List[str]:
        if center:
            inner = text.center(W)
        else:
            inner = text.ljust(W)
        # Truncate if overflowing (keeps box intact)
        if len(inner) > W:
            inner = inner[:W - 1] + "…"
        return [f"║ {inner} ║"]
