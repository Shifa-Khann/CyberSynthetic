"""
engine/plan.py
Pydantic plan models, preset plans, and clamp/validate helpers.
The LLM planner returns a dict that is coerced into a Plan via Plan.model_validate().
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ──────────────────────────────────────────────
# Sub-models
# ──────────────────────────────────────────────

class Ratios(BaseModel):
    normal: float = Field(0.70, ge=0.0, le=1.0)
    suspicious: float = Field(0.20, ge=0.0, le=1.0)
    malicious: float = Field(0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _sum_to_one(self) -> "Ratios":
        total = self.normal + self.suspicious + self.malicious
        if abs(total - 1.0) > 1e-6:
            # normalise rather than reject
            self.normal /= total
            self.suspicious /= total
            self.malicious /= total
        return self


class ScenarioSpec(BaseModel):
    name: str
    weight: float = Field(1.0, ge=0.0)


# ──────────────────────────────────────────────
# Main plan
# ──────────────────────────────────────────────

class Plan(BaseModel):
    mode: Literal["scenario", "upload"] = "scenario"
    seed: int = 42
    duration_days: int = Field(7, ge=1, le=90)
    users: int = Field(50, ge=1, le=2000)
    devices: int = Field(30, ge=1, le=1000)
    ratios: Ratios = Field(default_factory=Ratios)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    domains: list[Literal["auth", "email", "endpoint"]] = Field(
        default_factory=lambda: ["auth"]
    )
    scenarios: list[ScenarioSpec] = Field(default_factory=list)
    language: Literal["en", "ur", "both"] = "en"
    generate_documents: bool = True
    use_llm: bool = True
    calibration_profile: str = "default"

    model_config = {"extra": "ignore"}  # reject unknown fields silently

    # clamp helper -------------------------------------------------------
    @model_validator(mode="after")
    def _clamp(self) -> "Plan":
        self.duration_days = max(1, min(90, self.duration_days))
        self.users = max(1, min(2000, self.users))
        self.devices = max(1, min(1000, self.devices))
        # ensure devices <= users (no more devices than users)
        self.devices = min(self.devices, self.users)
        return self


# ──────────────────────────────────────────────
# Presets
# ──────────────────────────────────────────────

PRESETS: dict[str, dict] = {
    "small_auth": {
        "mode": "scenario",
        "seed": 42,
        "duration_days": 7,
        "users": 20,
        "devices": 15,
        "ratios": {"normal": 0.70, "suspicious": 0.20, "malicious": 0.10},
        "difficulty": "easy",
        "domains": ["auth"],
        "generate_documents": True,
        "language": "en",
        "use_llm": False,
    },
    "medium_full": {
        "mode": "scenario",
        "seed": 42,
        "duration_days": 14,
        "users": 100,
        "devices": 70,
        "ratios": {"normal": 0.65, "suspicious": 0.20, "malicious": 0.15},
        "difficulty": "medium",
        "domains": ["auth", "email", "endpoint"],
        "generate_documents": True,
        "language": "both",
        "use_llm": True,
    },
    "hard_stealth": {
        "mode": "scenario",
        "seed": 42,
        "duration_days": 30,
        "users": 200,
        "devices": 150,
        "ratios": {"normal": 0.75, "suspicious": 0.15, "malicious": 0.10},
        "difficulty": "hard",
        "domains": ["auth", "email", "endpoint"],
        "generate_documents": True,
        "language": "en",
        "use_llm": True,
    },
}


def get_preset(name: str) -> Plan:
    """Return a Plan from a named preset. Falls back to small_auth."""
    data = PRESETS.get(name, PRESETS["small_auth"])
    return Plan.model_validate(data)


def plan_from_dict(d: dict) -> Plan:
    """Coerce an arbitrary dict (from LLM or user) into a validated Plan."""
    return Plan.model_validate(d)
