"""
pdf_export.py — Timetable Planner Phase 2
==========================================
Generates a printable PDF timetable using WeasyPrint.

The PDF includes:
  - Organisation name + week range header
  - Full weekly grid (workers × days) with shift times
  - Per-worker hour summary table
  - Colour-coded work types (FULL_TIME / PART_TIME / MINIJOB)
  - Footer with generation timestamp
"""

import datetime
from typing import Optional

from timetable_app.models import Timetable, Shift

DAY_ORDER  = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
DAY_LABELS = {
    'MON': 'Monday', 'TUE': 'Tuesday',  'WED': 'Wednesday',
    'THU': 'Thursday', 'FRI': 'Friday', 'SAT': 'Saturday', 'SUN': 'Sunday',
}

WORK_TYPE_COLOURS = {
    'FULL_TIME': '#2d6a2d',   # dark green
    'PART_TIME': '#1a5276',   # dark blue
    'MINIJOB':   '#7d3c0a',   # dark brown
}

WORK_TYPE_BG = {
    'FULL_TIME': '#eafaea',
    'PART_TIME': '#eaf2fb',
    'MINIJOB':   '#fdf2e9',
}


def _fmt_time(t) -> str:
    """Format a time object as HH:MM."""
    if not t:
        return '–'
    return t.strftime('%H:%M')


def _date_for_day(week_start: datetime.date, day_code: str) -> str:
    """Return the date string for a given day code within the week."""
    offset = DAY_ORDER.index(day_code)
    d = week_start + datetime.timedelta(days=offset)
    return d.strftime('%d %b')


def build_timetable_html(timetable: Timetable) -> str:
    """
    Build a full HTML string representing the timetable.
    This is rendered to PDF by WeasyPrint, but can also be
    served directly as a digital timetable view.
    """
    org        = timetable.org
    week_start = timetable.week_start
    week_end   = week_start + datetime.timedelta(days=6)

    # Index shifts: { worker_pk → { day → Shift } }
    shifts_qs = (
        timetable.shifts
        .select_related('worker')
        .order_by('worker__full_name', 'day')
    )

    worker_shifts: dict = {}    # { worker → { day: Shift } }
    worker_totals: dict = {}    # { worker → total_hours }

    for shift in shifts_qs:
        w = shift.worker
        if w not in worker_shifts:
            worker_shifts[w] = {}
            worker_totals[w] = 0.0
        worker_shifts[w][shift.day] = shift
        worker_totals[w] += float(shift.hours)

    # Sort workers alphabetically
    sorted_workers = sorted(worker_shifts.keys(), key=lambda w: w.full_name)

    generated_at = datetime.datetime.now().strftime('%d %b %Y %H:%M')

    # ------------------------------------------------------------------
    # Build HTML
    # ------------------------------------------------------------------
    # Day header columns
    day_headers = ''.join(
        f'<th class="day-hdr">'
        f'<div class="day-name">{DAY_LABELS[d][:3]}</div>'
        f'<div class="day-date">{_date_for_day(week_start, d)}</div>'
        f'</th>'
        for d in DAY_ORDER
    )

    # Worker rows
    worker_rows = ''
    for worker in sorted_workers:
        shifts_for_worker = worker_shifts[worker]
        total_h = worker_totals[worker]
        wt      = worker.work_type or 'FULL_TIME'
        colour  = WORK_TYPE_COLOURS.get(wt, '#333')
        bg      = WORK_TYPE_BG.get(wt, '#f9f9f9')
        budget  = worker.get_weekly_hour_limit()
        pct     = round(100 * total_h / budget, 0) if budget else 0

        cells = ''
        for day in DAY_ORDER:
            shift = shifts_for_worker.get(day)
            if shift:
                cells += (
                    f'<td class="shift-cell">'
                    f'<div class="shift-time">{_fmt_time(shift.start_time)}</div>'
                    f'<div class="shift-sep">↓</div>'
                    f'<div class="shift-time">{_fmt_time(shift.end_time)}</div>'
                    f'<div class="shift-hrs">{float(shift.hours):.1f}h</div>'
                    f'</td>'
                )
            else:
                cells += '<td class="off-cell"><span class="off-label">–</span></td>'

        worker_rows += f'''
        <tr style="background:{bg}">
            <td class="worker-cell">
                <div class="worker-name" style="color:{colour}">{worker.full_name}</div>
                <div class="worker-meta">{wt.replace("_", " ")}</div>
            </td>
            {cells}
            <td class="total-cell">
                <div class="total-hrs">{total_h:.1f}h</div>
                <div class="total-pct">{pct:.0f}%</div>
                <div class="total-budget">/ {budget}h</div>
            </td>
        </tr>'''

    # Summary table rows
    summary_rows = ''
    for worker in sorted_workers:
        total_h = worker_totals[worker]
        budget  = worker.get_weekly_hour_limit()
        pct     = round(100 * total_h / budget, 0) if budget else 0
        wt      = (worker.work_type or '').replace('_', ' ')
        colour  = WORK_TYPE_COLOURS.get(worker.work_type or '', '#333')
        bar_w   = min(int(pct), 100)

        summary_rows += f'''
        <tr>
            <td style="color:{colour};font-weight:600">{worker.full_name}</td>
            <td>{wt}</td>
            <td>{worker.user_id}</td>
            <td style="text-align:right">{budget}h</td>
            <td style="text-align:right;font-weight:600">{total_h:.1f}h</td>
            <td>
                <div class="bar-wrap">
                    <div class="bar-fill" style="width:{bar_w}%;background:{colour}"></div>
                </div>
                <span style="font-size:0.7rem;color:{colour}">{pct:.0f}%</span>
            </td>
        </tr>'''

    if not sorted_workers:
        worker_rows   = f'<tr><td colspan="{2 + len(DAY_ORDER)}" class="empty-row">No shifts scheduled this week.</td></tr>'
        summary_rows  = '<tr><td colspan="6" class="empty-row">No data.</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      font-size: 11px;
      color: #1a1a1a;
      background: #fff;
      padding: 20px 24px;
  }}

  /* ── Header ── */
  .hdr {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      border-bottom: 3px solid #3d6b1f;
      padding-bottom: 10px;
      margin-bottom: 18px;
  }}
  .hdr-left h1 {{
      font-size: 20px;
      color: #3d6b1f;
      font-weight: 700;
      letter-spacing: -0.3px;
  }}
  .hdr-left h2 {{
      font-size: 12px;
      color: #555;
      font-weight: 400;
      margin-top: 2px;
  }}
  .hdr-right {{
      text-align: right;
      font-size: 10px;
      color: #777;
      line-height: 1.6;
  }}
  .status-badge {{
      display: inline-block;
      background: {'#2d6a2d' if timetable.status == 'PUBLISHED' else '#c0392b'};
      color: #fff;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
  }}

  /* ── Timetable grid ── */
  .section-title {{
      font-size: 11px;
      font-weight: 700;
      color: #3d6b1f;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      margin-bottom: 8px;
      margin-top: 18px;
  }}
  table.grid {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 10px;
  }}
  table.grid th, table.grid td {{
      border: 1px solid #ddd;
      padding: 5px 4px;
      vertical-align: middle;
      text-align: center;
  }}
  table.grid thead tr {{
      background: #3d6b1f;
      color: #fff;
  }}
  .worker-hdr {{
      text-align: left !important;
      padding-left: 8px !important;
      min-width: 120px;
  }}
  .day-hdr {{ min-width: 72px; }}
  .day-name {{ font-weight: 700; font-size: 10px; }}
  .day-date {{ font-size: 9px; opacity: 0.85; margin-top: 1px; }}
  .total-hdr {{ min-width: 60px; }}

  .worker-cell {{
      text-align: left !important;
      padding: 6px 8px !important;
      border-right: 2px solid #ccc !important;
  }}
  .worker-name {{ font-weight: 700; font-size: 10.5px; }}
  .worker-meta {{ font-size: 8.5px; color: #888; margin-top: 1px; }}

  .shift-cell {{ background: #f0fff0; }}
  .shift-time {{ font-weight: 700; font-size: 10px; color: #1a3a1a; }}
  .shift-sep  {{ font-size: 8px; color: #aaa; line-height: 1; }}
  .shift-hrs  {{ font-size: 9px; color: #2d7a2d; margin-top: 1px; }}

  .off-cell {{ background: #fafafa; }}
  .off-label {{ color: #ccc; font-size: 14px; }}

  .total-cell {{
      background: #f5f5f5 !important;
      border-left: 2px solid #ccc !important;
  }}
  .total-hrs   {{ font-weight: 700; font-size: 11px; color: #1a1a1a; }}
  .total-pct   {{ font-size: 9px; color: #888; }}
  .total-budget {{ font-size: 8.5px; color: #bbb; }}

  .empty-row {{ color: #aaa; font-style: italic; padding: 20px !important; }}

  /* ── Summary table ── */
  table.summary {{
      width: 100%;
      border-collapse: collapse;
  }}
  table.summary th {{
      background: #f5f5f0;
      text-align: left;
      padding: 5px 8px;
      font-size: 9.5px;
      font-weight: 700;
      color: #555;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid #ddd;
  }}
  table.summary td {{
      padding: 5px 8px;
      border-bottom: 1px solid #eee;
      font-size: 10px;
  }}
  .bar-wrap {{
      background: #eee;
      border-radius: 3px;
      height: 6px;
      width: 80px;
      display: inline-block;
      vertical-align: middle;
      margin-right: 4px;
  }}
  .bar-fill {{
      height: 6px;
      border-radius: 3px;
  }}

  /* ── Legend ── */
  .legend {{
      display: flex;
      gap: 16px;
      margin-top: 14px;
      flex-wrap: wrap;
  }}
  .legend-item {{
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 9.5px;
      color: #555;
  }}
  .legend-dot {{
      width: 10px; height: 10px;
      border-radius: 2px;
  }}

  /* ── Footer ── */
  .footer {{
      margin-top: 20px;
      border-top: 1px solid #eee;
      padding-top: 8px;
      font-size: 9px;
      color: #aaa;
      display: flex;
      justify-content: space-between;
  }}

  /* ── Page breaks for WeasyPrint ── */
  @page {{
      size: A4 landscape;
      margin: 15mm 12mm;
  }}
  .no-break {{ page-break-inside: avoid; }}
</style>
</head>
<body>

<div class="hdr">
  <div class="hdr-left">
    <h1>{org.name}</h1>
    <h2>Weekly Timetable &nbsp;·&nbsp;
        {week_start.strftime("%d %b")} – {week_end.strftime("%d %b %Y")}
    </h2>
  </div>
  <div class="hdr-right">
    <div><span class="status-badge">{timetable.status}</span></div>
    <div style="margin-top:4px">Shop hours: {_fmt_time(org.shop_open)} – {_fmt_time(org.shop_close)}</div>
    <div>Generated: {generated_at}</div>
  </div>
</div>

<div class="section-title">Shift Schedule</div>
<div class="no-break">
<table class="grid">
  <thead>
    <tr>
      <th class="worker-hdr">Worker</th>
      {day_headers}
      <th class="total-hdr">Total</th>
    </tr>
  </thead>
  <tbody>
    {worker_rows}
  </tbody>
</table>
</div>

<div class="section-title" style="margin-top:22px">Hours Summary</div>
<div class="no-break">
<table class="summary">
  <thead>
    <tr>
      <th>Worker</th>
      <th>Type</th>
      <th>User ID</th>
      <th style="text-align:right">Budget</th>
      <th style="text-align:right">Assigned</th>
      <th>Utilisation</th>
    </tr>
  </thead>
  <tbody>
    {summary_rows}
  </tbody>
</table>
</div>

<div class="legend">
  <div class="legend-item">
    <div class="legend-dot" style="background:{WORK_TYPE_BG['FULL_TIME']};border:1px solid {WORK_TYPE_COLOURS['FULL_TIME']}"></div>
    Full Time (40h/week)
  </div>
  <div class="legend-item">
    <div class="legend-dot" style="background:{WORK_TYPE_BG['PART_TIME']};border:1px solid {WORK_TYPE_COLOURS['PART_TIME']}"></div>
    Part Time (20h/week)
  </div>
  <div class="legend-item">
    <div class="legend-dot" style="background:{WORK_TYPE_BG['MINIJOB']};border:1px solid {WORK_TYPE_COLOURS['MINIJOB']}"></div>
    Mini Job (10h/week)
  </div>
</div>

<div class="footer">
  <span>Timetable Planner · {org.name}</span>
  <span>Week {week_start.strftime("%W")} · {generated_at}</span>
</div>

</body>
</html>'''

    return html


def generate_pdf_bytes(timetable: Timetable) -> bytes:
    """
    Render the timetable HTML to a PDF and return raw bytes.
    Uses WeasyPrint for rendering.
    """
    from weasyprint import HTML as WeasyHTML
    html_str = build_timetable_html(timetable)
    pdf_bytes = WeasyHTML(string=html_str).write_pdf()
    return pdf_bytes
