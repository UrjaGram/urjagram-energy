"""
Jev decision layer + hard safety rules for pumping-energy decisions.

Pattern: a language model writes, Jev decides, code acts.
Jev picks one level from a listed set. The hard rules below can only RAISE a level.

NOTE: the live TypeSafe Jev endpoint is not wired in yet. `classify_status` is a deterministic
stand-in with the same interface (features in -> one of four labels out), the same approach the
water module uses, so the real model can replace it without changing callers.
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import config as C


class AlertLevel(str, Enum):
    NORMAL = "LEVEL_0_NORMAL"
    ADVISORY = "LEVEL_1_ADVISORY"
    WARNING = "LEVEL_2_WARNING"
    EMERGENCY = "LEVEL_3_EMERGENCY"


class ActionDirective(str, Enum):
    RUN_AS_SCHEDULED = "RUN_PUMPS_AS_SCHEDULED"
    SHIFT_TO_SOLAR_WINDOW = "SHIFT_PUMPING_TO_SOLAR_WINDOW"
    STAGGER_HYBRID = "STAGGER_PUMPS_HYBRID_SOLAR_GRID"
    PRIORITISE_DRINKING_WATER = "SERVE_DRINKING_WATER_FIRST_SHED_AGRICULTURAL_LOAD"


_ORDER = [AlertLevel.NORMAL, AlertLevel.ADVISORY, AlertLevel.WARNING, AlertLevel.EMERGENCY]


def _raise_to(current: AlertLevel, minimum: AlertLevel) -> AlertLevel:
    return _ORDER[max(_ORDER.index(current), _ORDER.index(minimum))]


def classify_status(ag_unmet_fraction: float, grid_hours_deficit: float, water_alert: str) -> AlertLevel:
    """Score three dimensions and map to a label (Jev stand-in)."""
    score = 0
    if ag_unmet_fraction >= 0.5:
        score += 4
    elif ag_unmet_fraction >= 0.25:
        score += 3
    elif ag_unmet_fraction >= 0.1:
        score += 2
    elif ag_unmet_fraction > 0:
        score += 1

    if grid_hours_deficit >= 6:
        score += 3
    elif grid_hours_deficit >= 3:
        score += 2
    elif grid_hours_deficit > 0:
        score += 1

    score += {"LEVEL_0_NORMAL": 0, "LEVEL_1_ADVISORY": 0, "LEVEL_2_WARNING": 1, "LEVEL_3_EMERGENCY": 2}.get(water_alert, 0)

    if score >= 7:
        return AlertLevel.EMERGENCY
    if score >= 4:
        return AlertLevel.WARNING
    if score >= 2:
        return AlertLevel.ADVISORY
    return AlertLevel.NORMAL


def enforce_hard_rules(
    jev_level: AlertLevel,
    grid_hours_available_today: float,
    required_pump_hours: float,
    solar_window_available: bool,
) -> Tuple[AlertLevel, ActionDirective, str]:
    """Safety thresholds in code. They can only raise the level Jev returned."""
    level = jev_level
    notes = []

    if grid_hours_available_today <= 0:
        level = _raise_to(level, AlertLevel.EMERGENCY)
        notes.append("no grid hour available: forced to EMERGENCY")
    elif grid_hours_available_today < required_pump_hours * C.MIN_GRID_HOURS_FRACTION_FOR_WARNING:
        level = _raise_to(level, AlertLevel.WARNING)
        notes.append("grid hours below half of required pumping hours: at least WARNING")

    if level == AlertLevel.EMERGENCY:
        directive = ActionDirective.PRIORITISE_DRINKING_WATER
    elif level == AlertLevel.WARNING:
        directive = ActionDirective.SHIFT_TO_SOLAR_WINDOW if solar_window_available else ActionDirective.PRIORITISE_DRINKING_WATER
    elif level == AlertLevel.ADVISORY:
        directive = ActionDirective.STAGGER_HYBRID if solar_window_available else ActionDirective.RUN_AS_SCHEDULED
    else:
        directive = ActionDirective.RUN_AS_SCHEDULED

    note = "; ".join(notes) if notes else "compliant with hard rules"
    if level != jev_level:
        note = "hard rule raised level from {} to {} ({})".format(jev_level.value, level.value, note)
    return level, directive, note


def allowed_pump_hours(required_pump_hours: float, water_alert: str, directive: ActionDirective) -> float:
    """Pump hours cap: the water module's cap always applies; load-shedding sets agricultural hours to zero."""
    cap = C.WATER_ALERT_PUMP_HOURS_CAP.get(water_alert, 24.0)
    hours = min(required_pump_hours, cap)
    if directive == ActionDirective.PRIORITISE_DRINKING_WATER:
        hours = 0.0
    return hours


def log_decision(record: Dict[str, Any], path: Optional[Path] = None) -> Path:
    """Append every decision with its inputs to a JSON-lines file so it can be audited later."""
    path = path or (C.OUTPUT_DIR / "decision_log.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"logged_at": datetime.now(timezone.utc).isoformat(), **record}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return path
