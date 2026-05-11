"""
Mood analyzer module for MentalTalk Mental Health Chatbot
Performs keyword-based mood detection from chat text.
"""

import re
from typing import Any, Dict, List, Tuple

# Mood category definitions with keywords and score ranges
MOOD_CATEGORIES = {
    "Very Positive": {
        "keywords": [
            "happy", "great", "wonderful", "hopeful", "grateful", "excited",
            "calm", "peaceful", "better", "joyful", "joy", "love", "loved",
            "amazing", "fantastic", "perfect", "awesome", "delighted"
        ],
        "score_range": (0.8, 1.0),
        "weight": 1.0
    },
    "Positive": {
        "keywords": [
            "okay", "fine", "good", "managing", "coping", "trying",
            "improving", "better", "alright", "doing well", "stable"
        ],
        "score_range": (0.4, 0.7),
        "weight": 0.7
    },
    "Neutral": {
        "keywords": [
            "alright", "nothing", "unsure", "confused", "don't know",
            "maybe", "perhaps", "whatever", "meh", "ok", "fine"
        ],
        "score_range": (0.0, 0.3),
        "weight": 0.3
    },
    "Negative": {
        "keywords": [
            "tired", "stressed", "anxious", "worried", "overwhelmed",
            "sad", "lonely", "upset", "angry", "frustrated", "nervous",
            "down", "unhappy", "struggling", "hard", "difficult"
        ],
        "score_range": (-0.4, -0.1),
        "weight": -0.5
    },
    "Very Negative": {
        "keywords": [
            "hopeless", "worthless", "depressed", "crying", "can't",
            "suicidal", "hurt", "empty", "despair", "give up", "no point",
            "terrible", "awful", "miserable", "suffering", "pain", "hate"
        ],
        "score_range": (-1.0, -0.5),
        "weight": -1.0
    }
}


def _find_keywords_in_text(text: str) -> List[Tuple[str, float]]:
    lower_text = text.lower()
    matches = []

    for category, config in MOOD_CATEGORIES.items():
        for keyword in config["keywords"]:
            # Use word boundaries to match whole words
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, lower_text):
                matches.append((category, config["weight"]))

    return matches


def _calculate_score(matches: List[Tuple[str, float]]) -> Tuple[str, float]:
    if not matches:
        # Default to neutral if no keywords match
        return "Neutral", 0.15

    # Calculate average weight
    total_weight = sum(weight for _, weight in matches)
    avg_weight = total_weight / len(matches)

    # Find the category with the closest score range
    best_category = "Neutral"
    best_distance = float('inf')

    for category, config in MOOD_CATEGORIES.items():
        score_range = config["score_range"]
        # Calculate distance to the middle of the range
        range_mid = (score_range[0] + score_range[1]) / 2
        distance = abs(avg_weight - range_mid)

        if distance < best_distance:
            best_distance = distance
            best_category = category

    # Clamp score to [-1.0, 1.0] and ensure it's a float
    score = float(max(-1.0, min(1.0, avg_weight)))

    return best_category, score


def analyze_mood(text: str) -> Dict[str, Any]:
    # Find keyword matches
    matches = _find_keywords_in_text(text)

    # Calculate score and label
    label, score = _calculate_score(matches)

    # Get snippet (first 100 chars)
    snippet = text[:100]

    return {
        "label": label,
        "score": round(score, 4),
        "snippet": snippet
    }


def get_mood_categories() -> Dict[str, Dict[str, any]]:
    return MOOD_CATEGORIES
