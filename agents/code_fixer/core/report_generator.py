"""ReportGenerator — produce HTML and JSON fix reports."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class ReportGenerator:
    """Generate human- and machine-readable reports for a Code Fixer run.

    Parameters
    ----------
    run_data:
        Dict describing the completed run.  Expected keys: ``run_id``,
        ``started_at``, ``finished_at``, ``risk_filter``, ``batch_size``,
        ``total_candidates``, ``batches_attempted``, ``batches_succeeded``,
        ``batches_failed``, ``items_fixed``, ``items_failed``,
        ``lines_removed``, ``commits``, ``batches``.
    """

    def __init__(self, run_data: Dict[str, Any]) -> None:
        self._data = run_data

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def write_json(self, path: Path) -> None:
        """Write machine-readable JSON report to *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def write_html(self, path: Path) -> None:
        """Write human-readable HTML report to *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._generate_html(), encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Private helpers                                                        #
    # ------------------------------------------------------------------ #

    def _generate_html(self) -> str:
        d = self._data
        run_id = d.get("run_id", "unknown")
        started = d.get("started_at", "")[:19].replace("T", " ")
        finished = d.get("finished_at", "")[:19].replace("T", " ")
        risk = d.get("risk_filter", "LOW")
        candidates = d.get("total_candidates", 0)
        attempted = d.get("batches_attempted", 0)
        succeeded = d.get("batches_succeeded", 0)
        failed_batches = d.get("batches_failed", 0)
        items_fixed = d.get("items_fixed", [])
        items_failed = d.get("items_failed", [])
        lines = d.get("lines_removed", 0)
        commits = d.get("commits", [])
        batches = d.get("batches", [])

        pct = round(succeeded / attempted * 100) if attempted else 0
        status_color = "#198754" if failed_batches == 0 else "#fd7e14"
        status_text = "SUCCESS" if failed_batches == 0 else "PARTIAL"

        batch_rows = ""
        for b in batches:
            ids = ", ".join(b.get("item_ids", []))
            status = b.get("status", "")
            row_cls = "table-success" if status == "success" else "table-danger"
            commit = b.get("commit_hash", "-")[:7]
            err = self._esc(b.get("error") or "")
            batch_rows += (
                f"<tr class='{row_cls}'>"
                f"<td>{b.get('batch_num','')}</td>"
                f"<td>{self._esc(ids)}</td>"
                f"<td>{status}</td>"
                f"<td>{b.get('lines_removed', 0)}</td>"
                f"<td><code>{commit}</code></td>"
                f"<td>{err}</td>"
                f"</tr>"
            )

        failed_items_html = ""
        if items_failed:
            failed_items_html = (
                "<p><strong>Failed items:</strong> "
                + ", ".join(f"<code>{self._esc(x)}</code>" for x in items_failed)
                + "</p>"
            )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fix Report {run_id}</title>
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <style>
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; padding: 2rem; }}
    .kpi {{ font-size: 2rem; font-weight: 700; }}
    .badge-status {{ background: {status_color}; color: #fff;
                     padding: .4rem 1rem; border-radius: 6px; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Code Fixer Run Report</h1>
  <p class="text-muted">Run ID: <code>{run_id}</code> &nbsp;|&nbsp;
     {started} &rarr; {finished}</p>
  <span class="badge-status">{status_text}</span>

  <div class="row g-3 mt-3">
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-success">{len(items_fixed)}</div>
      <div class="text-muted">Items Fixed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-danger">{len(items_failed)}</div>
      <div class="text-muted">Items Failed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-info">{lines}</div>
      <div class="text-muted">Lines Removed</div>
    </div></div>
    <div class="col-sm-3"><div class="card p-3 text-center">
      <div class="kpi text-primary">{pct}%</div>
      <div class="text-muted">Batch Success Rate</div>
    </div></div>
  </div>

  <div class="row g-3 mt-2">
    <div class="col-md-6">
      <div class="card p-3">
        <h5>Run Configuration</h5>
        <table class="table table-sm table-borderless mb-0">
          <tr><td>Risk filter</td><td><strong>{risk}</strong></td></tr>
          <tr><td>Batch size</td><td>{d.get("batch_size", 3)}</td></tr>
          <tr><td>Candidates</td><td>{candidates}</td></tr>
          <tr><td>Batches attempted</td><td>{attempted}</td></tr>
          <tr><td>Batches succeeded</td><td>{succeeded}</td></tr>
          <tr><td>Batches failed</td><td>{failed_batches}</td></tr>
          <tr><td>Commits created</td><td>{len(commits)}</td></tr>
        </table>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card p-3">
        <h5>Commits</h5>
        {"".join(f"<code class='d-block'>{self._esc(c)}</code>" for c in commits[:10])}
        {f"<small class='text-muted'>...and {len(commits)-10} more</small>" if len(commits) > 10 else ""}
      </div>
    </div>
  </div>

  {failed_items_html}

  <h4 class="mt-4">Batch Details</h4>
  <table class="table table-hover table-sm">
    <thead class="table-light">
      <tr><th>#</th><th>Items</th><th>Status</th>
          <th>Lines</th><th>Commit</th><th>Error</th></tr>
    </thead>
    <tbody>{batch_rows}</tbody>
  </table>

  <footer class="mt-4 text-muted">
    <small>Generated by Code Fixer Agent &mdash; {self._esc(run_id)}</small>
  </footer>
</body>
</html>"""

    @staticmethod
    def _esc(text: str) -> str:
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
