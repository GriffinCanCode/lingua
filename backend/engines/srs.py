"""Spaced Repetition System Engine

Implements SM-2 algorithm variant with syntactic pattern awareness.
Tracks mastery per grammatical pattern, not just words.
"""
from datetime import datetime, timedelta
from typing import Optional


class SRSEngine:
    """Engine for spaced repetition scheduling"""
    
    def __init__(self):
        # SM-2 parameters
        self.min_ease_factor = 1.3
        self.default_ease_factor = 2.5
    
    def calculate_sm2(
        self,
        quality: int,
        repetitions: int,
        ease_factor: float,
        interval: int,
    ) -> dict:
        """Calculate next review parameters using SM-2 algorithm
        
        Args:
            quality: User rating 0-5 (0-2 = again, 3 = hard, 4 = good, 5 = easy)
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
            # Failed review - reset
            new_repetitions = 0
            new_interval = 1
        else:
            new_repetitions = repetitions + 1
            
            if new_repetitions == 1:
                new_interval = 1
            elif new_repetitions == 2:
                new_interval = 6
            else:
                new_interval = round(interval * new_ef)
        
        # Apply quality modifiers
        if quality == 3:  # Hard
            new_interval = max(1, round(new_interval * 0.8))
        elif quality == 5:  # Easy
            new_interval = round(new_interval * 1.3)
        
        next_review = datetime.utcnow() + timedelta(days=new_interval)
        
        return {
            "ease_factor": new_ef,
            "interval": new_interval,
            "repetitions": new_repetitions,
            "next_review": next_review,
        }
    
    def get_review_priority(
        self,
        pattern_difficulty: int,
        user_mastery: float,
        days_overdue: int,
    ) -> float:
        """Calculate review priority for a pattern
        
        Higher score = higher priority.
        Considers pattern difficulty, user mastery, and how overdue it is.
        """
        # Base priority from being overdue
        overdue_factor = min(days_overdue / 7, 2.0)  # Cap at 2x for very overdue
        
        # Difficulty factor - harder patterns get slight priority
        difficulty_factor = 1 + (pattern_difficulty - 5) * 0.05  # 5 is baseline
        
        # Mastery factor - lower mastery = higher priority
        mastery_factor = 2 - user_mastery  # 0-2 range
        
        return overdue_factor * difficulty_factor * mastery_factor
    
    def estimate_time_to_mastery(
        self,
        current_mastery: float,
        target_mastery: float = 0.9,
        avg_quality: float = 4.0,
    ) -> int:
        """Estimate days to reach target mastery
        
        Returns estimated number of days.
        """
        if current_mastery >= target_mastery:
            return 0
        
        # Simple estimation based on typical learning curves
        mastery_gap = target_mastery - current_mastery
        
        # Assume ~15% mastery gain per successful review at quality 4
        reviews_needed = mastery_gap / 0.15
        
        # Assume reviews spread over time based on SRS intervals
        # Average interval progression: 1, 3, 7, 14, 30...
        avg_days_between = 7  # Rough average
        
        return round(reviews_needed * avg_days_between)
    
    def get_session_recommendations(
        self,
        due_patterns: list[dict],
        session_length_minutes: int = 15,
        items_per_minute: float = 2.0,
    ) -> list[dict]:
        """Get recommended items for a study session
        
        Args:
            due_patterns: List of patterns with their data
            session_length_minutes: Target session length
            items_per_minute: Expected review speed
        
        Returns:
            Sorted list of patterns to review
        """
        max_items = int(session_length_minutes * items_per_minute)
        
        # Sort by priority
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

