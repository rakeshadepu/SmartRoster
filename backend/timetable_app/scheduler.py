"""
scheduler.py — Timetable Planner Phase 2
=========================================
Greedy scheduling algorithm that builds a weekly timetable from:
  - Worker availability submissions (preferred start time per day)
  - Per-worker weekly hour limits (from work_type + WorkTypeLimit)
  - Organisation's per-day BusinessHours (open/close can differ by day)
  - Max 8 hours per shift per day

Algorithm walkthrough
---------------------
1.  Collect all availability records for the target week in this org.
2.  For each worker, look up their weekly hour budget.
3.  Iterate through each day MON→SUN, looking up that day's BusinessHours.
4.  For each worker available that day:
      shift_start = max(worker_preferred_start, day_open)
      remaining   = budget - hours_already_assigned_this_week
      max_today   = min(8h, remaining)
      shift_end   = min(shift_start + max_today, day_close)
      if shift_end > shift_start → create Shift
5.  Accumulate hours assigned per worker across days.
6.  Return a Timetable object with all Shifts attached.

Edge cases handled
------------------
- Worker available but budget exhausted → skipped
- Worker preferred start is after that day's close time → skipped
- A day's open/close times are invalid (open >= close) → day skipped entirely
- Resulting shift < 30 min → skipped (not worth scheduling)
- Existing timetable for same (org, week_start) → overwritten on regenerate
- Workers with no availability for a day → not scheduled that day

Returns
-------
  TimetableResult  namedtuple with:
    timetable   : Timetable instance (saved to DB)
    shifts      : list of Shift instances (saved to DB)
    summary     : dict { worker_name: total_hours_assigned }
    warnings    : list of human-readable warning strings
"""

import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from django.db import transaction

from timetable_app.models import (
    Organisation, User, WorkTypeLimit,
    Availability, Timetable, Shift,
)

# Ordered day sequence used by the algorithm
DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']

# Minimum shift length in minutes — shifts shorter than this are skipped
MIN_SHIFT_MINUTES = 30

# Maximum hours in a single shift
MAX_SHIFT_HOURS = 8


@dataclass
class TimetableResult:
    timetable : object                      # Timetable instance
    shifts    : List[object] = field(default_factory=list)
    summary   : Dict[str, float] = field(default_factory=dict)
    warnings  : List[str] = field(default_factory=list)
    errors    : List[str] = field(default_factory=list)


def _time_to_minutes(t) -> int:
    """Convert a time object (or HH:MM:SS string) to total minutes since midnight."""
    if isinstance(t, str):
        parts = t.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    return t.hour * 60 + t.minute


def _minutes_to_time(minutes: int) -> datetime.time:
    """Convert total minutes since midnight back to a time object."""
    minutes = int(max(0, min(minutes, 23 * 60 + 59)))
    return datetime.time(minutes // 60, minutes % 60)


def _to_time(t) -> datetime.time:
    """Normalise a value to datetime.time (handles string HH:MM:SS from SQLite)."""
    if isinstance(t, datetime.time):
        return t
    if isinstance(t, str):
        parts = t.split(':')
        return datetime.time(int(parts[0]), int(parts[1]))
    return t


def _duration_hours(start: datetime.time, end: datetime.time) -> float:
    """Return the decimal hours between two time objects (end > start assumed)."""
    return (_time_to_minutes(end) - _time_to_minutes(start)) / 60.0


def generate_timetable(
    org: Organisation,
    week_start: datetime.date,
    regenerate: bool = False,
    generated_by: Optional[User] = None,
) -> TimetableResult:
    """
    Main entry point. Generates (or regenerates) a timetable for the given
    organisation and week.

    Parameters
    ----------
    org           : Organisation instance
    week_start    : date — must be a Monday
    regenerate    : if True, deletes any existing timetable for this week first
    generated_by  : the ADMIN/MANAGER User who triggered this run, if any —
                    recorded on Timetable.generated_by

    Returns
    -------
    TimetableResult
    """
    result = TimetableResult(timetable=None)

    # ------------------------------------------------------------------
    # 0. Validate inputs
    # ------------------------------------------------------------------
    if week_start.weekday() != 0:
        result.errors.append(
            f'week_start must be a Monday. Got {week_start.strftime("%A %Y-%m-%d")}.'
        )
        return result

    # Business hours are looked up per day inside the scheduling loop below
    # (each day of the week can have different open/close times).

    # ------------------------------------------------------------------
    # 1. Handle existing timetable
    # ------------------------------------------------------------------
    existing = Timetable.objects.filter(org=org, week_start=week_start).first()
    if existing:
        if not regenerate:
            result.errors.append(
                f'A timetable already exists for week {week_start}. '
                f'Pass regenerate=True to overwrite it.'
            )
            return result
        # Wipe existing shifts and timetable
        existing.shifts.all().delete()
        existing.delete()
        result.warnings.append(
            f'Existing timetable for week {week_start} was deleted and regenerated.'
        )

    # ------------------------------------------------------------------
    # 2. Load all active workers in this org
    # ------------------------------------------------------------------
    workers = list(
        User.objects.filter(
            org=org,
            role=User.Role.WORKER,
            # is_active=True,
        ).select_related('org')
    )

    if not workers:
        result.errors.append('No active workers found in this organisation.')
        return result

    # ------------------------------------------------------------------
    # 3. Build hour budget map  { worker_id → remaining_hours_float }
    # ------------------------------------------------------------------
    budget: Dict[int, float] = {}
    for w in workers:
        limit = w.get_weekly_hour_limit()
        if limit == 0:
            result.warnings.append(
                f'{w.full_name} has no hour limit set (work_type={w.work_type}). Skipping.'
            )
        budget[w.pk] = float(limit)

    # ------------------------------------------------------------------
    # 4. Load availability for this week, indexed by (worker_pk, day)
    # ------------------------------------------------------------------
    avail_qs = Availability.objects.filter(
        worker__org=org,
        # worker__is_active=True,
        week_start=week_start,
    ).select_related('worker')

    # { worker_pk → { day_str → start_time } }
    avail_map: Dict[int, Dict[str, datetime.time]] = defaultdict(dict)
    for av in avail_qs:
        avail_map[av.worker_id][av.day] = av.start_time

    if not avail_map:
        result.warnings.append(
            'No availability submissions found for this week. '
            'Timetable will be empty.'
        )

    # ------------------------------------------------------------------
    # 5. Greedy scheduling loop
    # ------------------------------------------------------------------
    shifts_to_create: List[Shift] = []
    # Track hours assigned this week per worker
    hours_assigned: Dict[int, float] = defaultdict(float)

    for day in DAY_ORDER:
        day_open, day_close = org.get_hours_for_day(day)
        shop_open_min  = _time_to_minutes(day_open)
        shop_close_min = _time_to_minutes(day_close)

        if shop_open_min >= shop_close_min:
            result.warnings.append(
                f'{day}: business hours are invalid (open {day_open} >= close {day_close}). '
                f'Day skipped.'
            )
            continue

        # Workers available this day, sorted by preferred start time (earliest first)
        day_workers = [
            (w, avail_map[w.pk][day])
            for w in workers
            if w.pk in avail_map and day in avail_map[w.pk]
        ]
        day_workers.sort(key=lambda x: x[1])  # sort by start_time

        for worker, preferred_start in day_workers:
            # Skip if budget exhausted
            remaining = budget[worker.pk] - hours_assigned[worker.pk]
            if remaining <= 0:
                result.warnings.append(
                    f'{worker.full_name}: weekly budget exhausted, skipped on {day}.'
                )
                continue

            pref_min = _time_to_minutes(preferred_start)

            # Shift starts at the later of preferred start or shop open
            start_min = max(pref_min, shop_open_min)

            # Can't start at or after shop close
            if start_min >= shop_close_min:
                result.warnings.append(
                    f'{worker.full_name}: preferred start {preferred_start} is at/after '
                    f'shop close {day_close} on {day}. Skipped.'
                )
                continue

            # Available shop time from this start
            available_shop_min = shop_close_min - start_min

            # Cap to max shift length and remaining weekly budget
            max_shift_min = min(
                MAX_SHIFT_HOURS * 60,
                remaining * 60,
                available_shop_min,
            )

            # Skip shifts shorter than minimum
            if max_shift_min < MIN_SHIFT_MINUTES:
                result.warnings.append(
                    f'{worker.full_name}: resulting shift on {day} would be '
                    f'{max_shift_min:.0f} min — below minimum ({MIN_SHIFT_MINUTES} min). Skipped.'
                )
                continue

            end_min   = start_min + max_shift_min
            start_t   = _minutes_to_time(start_min)
            end_t     = _minutes_to_time(int(end_min))
            shift_hrs = _duration_hours(start_t, end_t)

            shifts_to_create.append(
                Shift(
                    worker=worker,
                    day=day,
                    start_time=start_t,
                    end_time=end_t,
                    hours=round(shift_hrs, 2),
                )
            )
            hours_assigned[worker.pk] += shift_hrs

    # ------------------------------------------------------------------
    # 6. Persist to database atomically
    # ------------------------------------------------------------------
    with transaction.atomic():
        timetable = Timetable.objects.create(
            org=org,
            week_start=week_start,
            status=Timetable.Status.DRAFT,
            generated_by=generated_by,
        )

        for s in shifts_to_create:
            s.timetable = timetable

        Shift.objects.bulk_create(shifts_to_create)

    # ------------------------------------------------------------------
    # 7. Build summary
    # ------------------------------------------------------------------
    summary = {}
    for w in workers:
        assigned = hours_assigned.get(w.pk, 0.0)
        budget_h = budget.get(w.pk, 0.0)
        if assigned > 0:
            summary[w.full_name] = {
                'assigned_hours' : round(assigned, 2),
                'budget_hours'   : budget_h,
                'utilisation_pct': round(100 * assigned / budget_h, 1) if budget_h else 0,
                'work_type'      : w.work_type,
            }

    # Workers with availability but zero shifts get a warning
    for w in workers:
        if w.pk in avail_map and hours_assigned.get(w.pk, 0) == 0:
            result.warnings.append(
                f'{w.full_name} submitted availability but received no shifts '
                f'(budget={budget.get(w.pk, 0)}h).'
            )

    result.timetable = timetable
    result.shifts    = shifts_to_create
    result.summary   = summary

    return result
