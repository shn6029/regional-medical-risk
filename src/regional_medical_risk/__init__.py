"""지역 의료 취약도 분석 패키지."""

from .risk import score_regions
from .simulation import simulate_hospital_closure

__all__ = ["score_regions", "simulate_hospital_closure"]

