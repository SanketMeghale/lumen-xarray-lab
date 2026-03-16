from __future__ import annotations

from typing import Any

import numpy as np
import xarray as xr

ROLE_ORDER = ("time", "latitude", "longitude", "vertical")
MIN_ROLE_SCORE = 7

TIME_EXACT_NAMES = {
    "time",
    "times",
    "date",
    "datetime",
    "valid_time",
    "forecast_time",
    "initial_time",
    "reference_time",
    "xtime",
    "ocean_time",
}
LATITUDE_EXACT_NAMES = {
    "lat",
    "latitude",
    "nav_lat",
    "xlat",
    "ylat",
    "rlat",
    "yt_ocean",
    "yu_ocean",
    "yh",
    "yh_center",
    "south_north",
}
LONGITUDE_EXACT_NAMES = {
    "lon",
    "longitude",
    "nav_lon",
    "xlong",
    "xlon",
    "rlon",
    "xt_ocean",
    "xu_ocean",
    "xh",
    "xh_center",
    "west_east",
}
VERTICAL_EXACT_NAMES = {
    "lev",
    "level",
    "levels",
    "depth",
    "height",
    "altitude",
    "pressure",
    "press",
    "isobaric",
    "isobaric1",
    "bottom_top",
    "sigma",
    "sigma_level",
    "st_ocean",
    "s_rho",
    "z",
    "zt",
    "zw",
}

TIME_STANDARD_NAMES = {
    "time",
    "forecast_reference_time",
    "forecast_period",
}
LATITUDE_STANDARD_NAMES = {"latitude", "grid_latitude"}
LONGITUDE_STANDARD_NAMES = {"longitude", "grid_longitude"}
VERTICAL_STANDARD_NAMES = {
    "air_pressure",
    "altitude",
    "atmosphere_sigma_coordinate",
    "atmosphere_hybrid_sigma_pressure_coordinate",
    "depth",
    "geopotential_height",
    "height",
    "model_level_number",
    "ocean_s_coordinate",
}

LATITUDE_UNITS = {
    "degrees_north",
    "degree_north",
    "degrees_n",
    "degree_n",
    "degree_norths",
    "degreesnorth",
    "degreenorth",
}
LONGITUDE_UNITS = {
    "degrees_east",
    "degree_east",
    "degrees_e",
    "degree_e",
    "degree_easts",
    "degreeseast",
    "degreeeast",
}
PRESSURE_UNITS = {
    "pa",
    "hpa",
    "kpa",
    "bar",
    "mbar",
    "millibar",
    "millibars",
    "dbar",
}
VERTICAL_LENGTH_UNITS = {
    "m",
    "meter",
    "meters",
    "metre",
    "metres",
    "km",
    "kilometer",
    "kilometers",
    "kilometre",
    "kilometres",
    "cm",
    "centimeter",
    "centimeters",
    "centimetre",
    "centimetres",
}


def _normalize_text(value: Any) -> str:
    text = str(value).strip().lower()
    for char in (" ", "-", "/", ".", "(", ")", ","):
        text = text.replace(char, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _attribute_strings(coord: xr.DataArray) -> dict[str, str]:
    return {_normalize_text(key): str(value).strip() for key, value in coord.attrs.items()}


def _numeric_bounds(coord: xr.DataArray) -> tuple[float, float] | None:
    if coord.size == 0 or not np.issubdtype(coord.dtype, np.number):
        return None
    values = np.asarray(coord.values, dtype=float).reshape(-1)
    finite = values[np.isfinite(values)]
    if not finite.size:
        return None
    return float(finite.min()), float(finite.max())


def _append_score(condition: bool, score: int, reason: str, reasons: list[str]) -> int:
    if condition:
        reasons.append(reason)
        return score
    return 0


def _score_time(name: str, coord: xr.DataArray, attrs: dict[str, str]) -> tuple[int, list[str]]:
    normalized = _normalize_text(name)
    standard_name = _normalize_text(attrs.get("standard_name", ""))
    long_name = _normalize_text(attrs.get("long_name", attrs.get("description", "")))
    units = attrs.get("units", "").lower()
    axis = _normalize_text(attrs.get("axis", ""))

    reasons: list[str] = []
    score = 0
    score += _append_score(normalized in TIME_EXACT_NAMES, 8, "time-like coordinate name", reasons)
    score += _append_score(
        standard_name in TIME_STANDARD_NAMES or standard_name.endswith("_time"),
        10,
        "CF standard_name indicates time",
        reasons,
    )
    score += _append_score(axis == "t", 7, "axis=T attribute", reasons)
    score += _append_score(np.issubdtype(coord.dtype, np.datetime64), 10, "datetime dtype", reasons)
    score += _append_score(" since " in units, 7, "CF time units", reasons)
    score += _append_score("time" in long_name or "date" in long_name, 4, "long_name suggests time", reasons)
    return score, reasons


def _score_latitude(name: str, coord: xr.DataArray, attrs: dict[str, str]) -> tuple[int, list[str]]:
    normalized = _normalize_text(name)
    standard_name = _normalize_text(attrs.get("standard_name", ""))
    long_name = _normalize_text(attrs.get("long_name", attrs.get("description", "")))
    units = _normalize_text(attrs.get("units", ""))
    axis = _normalize_text(attrs.get("axis", ""))
    bounds = _numeric_bounds(coord)

    reasons: list[str] = []
    score = 0
    score += _append_score(normalized in LATITUDE_EXACT_NAMES, 8, "latitude-style coordinate name", reasons)
    score += _append_score("lat" in normalized and "lon" not in normalized, 5, "latitude token in name", reasons)
    score += _append_score(standard_name in LATITUDE_STANDARD_NAMES, 10, "CF standard_name=latitude", reasons)
    score += _append_score(units in LATITUDE_UNITS, 10, "latitude units", reasons)
    score += _append_score(axis == "y", 3, "axis=Y attribute", reasons)
    score += _append_score("latitude" in long_name, 5, "long_name suggests latitude", reasons)
    score += _append_score(
        bounds is not None and -90.5 <= bounds[0] <= 90.5 and -90.5 <= bounds[1] <= 90.5,
        4,
        "numeric bounds fit latitude range",
        reasons,
    )
    return score, reasons


def _score_longitude(name: str, coord: xr.DataArray, attrs: dict[str, str]) -> tuple[int, list[str]]:
    normalized = _normalize_text(name)
    standard_name = _normalize_text(attrs.get("standard_name", ""))
    long_name = _normalize_text(attrs.get("long_name", attrs.get("description", "")))
    units = _normalize_text(attrs.get("units", ""))
    axis = _normalize_text(attrs.get("axis", ""))
    bounds = _numeric_bounds(coord)

    reasons: list[str] = []
    score = 0
    score += _append_score(normalized in LONGITUDE_EXACT_NAMES, 8, "longitude-style coordinate name", reasons)
    score += _append_score("lon" in normalized, 5, "longitude token in name", reasons)
    score += _append_score(standard_name in LONGITUDE_STANDARD_NAMES, 10, "CF standard_name=longitude", reasons)
    score += _append_score(units in LONGITUDE_UNITS, 10, "longitude units", reasons)
    score += _append_score(axis == "x", 3, "axis=X attribute", reasons)
    score += _append_score("longitude" in long_name, 5, "long_name suggests longitude", reasons)
    score += _append_score(
        bounds is not None and -180.5 <= bounds[0] <= 360.5 and -180.5 <= bounds[1] <= 360.5,
        4,
        "numeric bounds fit longitude range",
        reasons,
    )
    return score, reasons


def _score_vertical(name: str, coord: xr.DataArray, attrs: dict[str, str]) -> tuple[int, list[str]]:
    normalized = _normalize_text(name)
    standard_name = _normalize_text(attrs.get("standard_name", ""))
    long_name = _normalize_text(attrs.get("long_name", attrs.get("description", "")))
    units = _normalize_text(attrs.get("units", ""))
    axis = _normalize_text(attrs.get("axis", ""))
    positive = _normalize_text(attrs.get("positive", ""))

    reasons: list[str] = []
    score = 0
    score += _append_score(normalized in VERTICAL_EXACT_NAMES, 8, "vertical-style coordinate name", reasons)
    score += _append_score(
        any(token in normalized for token in ("depth", "height", "level", "lev", "pressure", "sigma", "alt")),
        5,
        "vertical token in name",
        reasons,
    )
    score += _append_score(
        standard_name in VERTICAL_STANDARD_NAMES or standard_name.endswith(("pressure", "height", "depth")),
        10,
        "CF standard_name indicates vertical axis",
        reasons,
    )
    score += _append_score(axis == "z", 7, "axis=Z attribute", reasons)
    score += _append_score(positive in {"up", "down"}, 6, "positive attribute indicates vertical axis", reasons)
    score += _append_score(units in PRESSURE_UNITS, 7, "pressure units", reasons)
    score += _append_score(units in VERTICAL_LENGTH_UNITS, 4, "length units", reasons)
    score += _append_score(
        any(token in long_name for token in ("depth", "height", "pressure", "altitude", "level")),
        4,
        "long_name suggests vertical axis",
        reasons,
    )
    return score, reasons


def _score_coordinate_roles(name: str, coord: xr.DataArray) -> dict[str, dict[str, Any]]:
    attrs = _attribute_strings(coord)
    scorers = {
        "time": _score_time,
        "latitude": _score_latitude,
        "longitude": _score_longitude,
        "vertical": _score_vertical,
    }
    return {
        role: {
            "score": score,
            "reasons": reasons,
        }
        for role, scorer in scorers.items()
        for score, reasons in [scorer(name, coord, attrs)]
    }


def _confidence_from_score(score: int) -> str:
    if score >= 14:
        return "high"
    if score >= 10:
        return "medium"
    if score >= MIN_ROLE_SCORE:
        return "low"
    return "none"


def _coordinate_analysis(dataset: xr.Dataset) -> tuple[dict[str, str | None], dict[str, dict[str, Any]]]:
    selected = {role: None for role in ROLE_ORDER}
    analysis: dict[str, dict[str, Any]] = {}
    candidates: dict[str, list[tuple[int, int, int, str]]] = {role: [] for role in ROLE_ORDER}

    for name, coord in dataset.coords.items():
        role_scores = _score_coordinate_roles(name, coord)
        best_role, best_spec = max(role_scores.items(), key=lambda item: item[1]["score"])
        best_score = int(best_spec["score"])
        analysis[name] = {
            "best_role": best_role if best_score >= MIN_ROLE_SCORE else None,
            "best_score": best_score,
            "best_reasons": list(best_spec["reasons"]),
            "role_scores": {role: spec["score"] for role, spec in role_scores.items()},
            "role_reasons": {role: list(spec["reasons"]) for role, spec in role_scores.items()},
        }
        for role, spec in role_scores.items():
            score = int(spec["score"])
            if score >= MIN_ROLE_SCORE:
                candidates[role].append((score, int(coord.ndim == 1), -int(coord.ndim), name))

    assigned: set[str] = set()
    for role in ROLE_ORDER:
        ranked = sorted(candidates[role], reverse=True)
        for _score, _is_1d, _ndim_pref, name in ranked:
            if name in assigned:
                continue
            selected[role] = name
            assigned.add(name)
            break

    return selected, analysis


def detect_coordinates(dataset: xr.Dataset) -> dict[str, str | None]:
    detected, _ = _coordinate_analysis(dataset)
    return detected


def get_coordinate_metadata(dataset: xr.Dataset) -> dict[str, dict[str, Any]]:
    role_map, analysis = _coordinate_analysis(dataset)
    selected_reverse = {name: role for role, name in role_map.items() if name is not None}
    info: dict[str, dict[str, Any]] = {}

    for name, coord in dataset.coords.items():
        details = analysis[name]
        role = details["best_role"] or "dimension"
        entry: dict[str, Any] = {
            "role": role,
            "selected": name in selected_reverse,
            "selected_role": selected_reverse.get(name),
            "confidence": _confidence_from_score(details["best_score"]),
            "detection_score": details["best_score"],
            "detection_reasons": details["best_reasons"],
            "role_scores": details["role_scores"],
            "dtype": str(coord.dtype),
            "attrs": dict(coord.attrs),
            "size": int(coord.size),
            "ndim": int(coord.ndim),
            "units": coord.attrs.get("units"),
            "standard_name": coord.attrs.get("standard_name"),
            "axis": coord.attrs.get("axis"),
        }
        if coord.size:
            flat = np.asarray(coord.values).reshape(-1)
            entry["start"] = str(flat[0])
            entry["end"] = str(flat[-1])
        info[name] = entry
    return info
