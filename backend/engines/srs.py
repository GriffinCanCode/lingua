"""Spaced Repetition System Engine with Result Types

Implements SM-2 algorithm variant with syntactic pattern awareness.
Uses Result types for predictable error propagation.
"""
from datetime import datetime, timedelta
from dataclasses import dataclass

from core.logging import srs_logger
from core.errors import (
    AppError,
    Ok,
    Result,
    out_of_range,
)

log = srs_logger()


@dataclass(frozen=True, slots=True)
class SM2Result:
    """Result of SM-2 calculation."""
    ease_factor: float
    interval: int
    repetitions: int
    next_review: datetime


class SRSEngine:
    """Engine for spaced repetition scheduling."""
    
    __slots__ = ("min_ease_factor", "default_ease_factor")
    
    def __init__(self):
        self.min_ease_factor = 1.3
        self.default_ease_factor = 2.5
    
    def calculate_sm2(
        self,
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval: int,
    ) -> dict:
        """Calculate next review parameters using SM-2 algorithm.
        
        Args:
            quality: User rating 0-5 (0-2=again, 3=hard, 4=good, 5=easy)
            repetitions: Number of successful reviews
            ease_factor: Current ease factor
            interval: Current interval in days
        
        Returns:
            Dict with new ease_factor, interval, repetitions, next_review
        """
        # Calculate new ease factor
        new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ef = max(self.min_ease_factor, new_ef)
        
        # Calculate new interval
        if quality < 3:
            new_repetitions = 0
            new_interval = 1
        else:
            new_repetitions = repetitions + 1
            new_interval = 1 if new_repetitions == 1 else (6 if new_repetitions == 2 else round(interval * new_ef))
        
        # Apply quality modifiers
        if quality == 3:
            new_interval = max(1, round(new_interval * 0.8))
        elif quality == 5:
            new_interval = round(new_interval * 1.3)
        
        result = {
            "ease_factor": new_ef,
            "interval": new_interval,
            "repetitions": new_repetitions,
            "next_review": datetime.utcnow() + timedelta(days=new_interval),
        }
        log.debug("sm2_calculated", quality=quality, new_interval=new_interval, new_ef=round(new_ef, 2))
        return result
    
    def calculate_sm2_result(
        self,
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval: int,
    ) -> Result[SM2Result, AppError]:
        """Calculate SM-2 with Result type for typed error handling.
        
        Returns:
            Ok(SM2Result) on success
            Err(AppError) if quality out of range
        """
        if not 0 <= quality <= 5:
            log.warning("sm2_quality_out_of_range", quality=quality)
            return out_of_range("quality", quality, 0, 5, origin="srs_engine")
        
        result = self.calculate_sm2(quality, repetitions, ease_factor, interval)
        return Ok(SM2Result(
            ease_factor=result["ease_factor"],
            interval=result["interval"],
            repetitions=result["repetitions"],
            next_review=result["next_review"],
        ))
    
    def get_review_priority(
        self,
        pattern_difficulty: int,
        user_mastery: float,
        days_overdue: int,
    ) -> float:
        """Calculate review priority for a pattern.
        
        Higher score = higher priority.
        """
        overdue_factor = min(days_overdue / 7, 2.0)
        difficulty_factor = 1 + (pattern_difficulty - 5) * 0.05
        mastery_factor = 2 - user_mastery
        return overdue_factor * difficulty_factor * mastery_factor
    
    def estimate_time_to_mastery(
        self,
        current_mastery: float,
        target_mastery: float = 0.9,
        avg_quality: float = 4.0,
    ) -> int:
        """Estimate days to reach target mastery."""
        if current_mastery >= target_mastery:
            return 0
        
        mastery_gap = target_mastery - current_mastery
        reviews_needed = mastery_gap / 0.15
        avg_days_between = 7
        return round(reviews_needed * avg_days_between)
    
    def get_session_recommendations(
        self,
        due_patterns: list[dict],
        session_length_minutes: int = 15,
        items_per_minute: float = 2.0,
    ) -> list[dict]:
        """Get recommended items for a study session."""
        max_items = int(session_length_minutes * items_per_minute)
        
        sorted_patterns = sorted(
            due_patterns,
            key=lambda p: self.get_review_priority(
                p.get("difficulty", 5),
                p.get("mastery", 0.5),
                p.get("days_overdue", 0),
            ),
            reverse=True,
        )
        
        return sorted_patterns[:max_items]
