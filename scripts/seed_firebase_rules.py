"""
Seed Script for Firebase Firestore Moderation Rules.
Conforms to Master Prompt Section 2, Section 7, Section 8, Section 11.

Initializes Firestore with:
- badWords collection
- harassmentPatterns collection
- categories collection
- severityLevels collection
- improvementSuggestions collection

Can run directly with Firebase Admin credentials or export to local seed_rules.json.
"""

import os
import sys
import json
from typing import Dict, Any, List

CATEGORIES = [
    {"id": "insult", "description": "Words or phrases that disparage, belittle, or insult an individual."},
    {"id": "profanity", "description": "Crude, vulgar, or obscene language unsuitable for constructive communication."},
    {"id": "personal_attack", "description": "Direct attacks targeting a person rather than their actions or ideas."},
    {"id": "threat", "description": "Expressions of intention to inflict harm, violence, or severe negative action."},
    {"id": "harassment", "description": "Persistent unwanted behavior or intimidating language."},
    {"id": "sexual_harassment", "description": "Unwanted or inappropriate comments of a sexual or suggestive nature."},
    {"id": "bullying", "description": "Coercive or exclusionary language intended to demean or isolate someone."},
    {"id": "hate_or_abuse", "description": "Demeaning language targeting identity, background, or protected status."},
    {"id": "aggressive_language", "description": "Hostile, dismissive, or excessively combative phrasing."}
]

SEVERITY_LEVELS = [
    {"level": 0, "name": "Safe", "description": "Respectful, constructive, and professional language."},
    {"level": 1, "name": "Mild", "description": "Minor informal friction or mildly blunt phrasing."},
    {"level": 2, "name": "Warning", "description": "Noticeably aggressive or casually insulting language."},
    {"level": 3, "name": "Harmful", "description": "Direct personal attacks, bullying, or harassment."},
    {"level": 4, "name": "Severe", "description": "Explicit threats, severe hate speech, or abuse."}
]

BAD_WORDS = [
    {"word": "useless", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "stupid", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "idiot", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "moron", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "dumb", "category": "insult", "severity": 1, "active": True, "language": "en"},
    {"word": "loser", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "worthless", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "pathetic", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "incompetent", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"word": "clueless", "category": "aggressive_language", "severity": 1, "active": True, "language": "en"},
    {"word": "shut up", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"word": "trash", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "disgusting", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"word": "kill", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"word": "destroy", "category": "threat", "severity": 3, "active": True, "language": "en"},
    {"word": "hurt", "category": "threat", "severity": 3, "active": True, "language": "en"},
    {"word": "fool", "category": "insult", "severity": 1, "active": True, "language": "en"},
    {"word": "clown", "category": "insult", "severity": 1, "active": True, "language": "en"},
    # Multilingual examples (Hindi / Tamil) conforming to Section 11
    {"word": "pagal", "category": "insult", "severity": 2, "active": True, "language": "hi"},
    {"word": "bewakoof", "category": "insult", "severity": 2, "active": True, "language": "hi"},
    {"word": "muttal", "category": "insult", "severity": 2, "active": True, "language": "ta"}
]

HARASSMENT_PATTERNS = [
    {"phrase": "you are useless", "category": "personal_attack", "severity": 3, "active": True, "language": "en"},
    {"phrase": "your idea is stupid", "category": "insult", "severity": 2, "active": True, "language": "en"},
    {"phrase": "you have no brain", "category": "personal_attack", "severity": 3, "active": True, "language": "en"},
    {"phrase": "nobody likes you", "category": "bullying", "severity": 3, "active": True, "language": "en"},
    {"phrase": "i will hurt you", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "i will destroy you", "category": "threat", "severity": 4, "active": True, "language": "en"},
    {"phrase": "get lost", "category": "aggressive_language", "severity": 1, "active": True, "language": "en"},
    {"phrase": "you never know anything", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"phrase": "you are a waste of time", "category": "harassment", "severity": 3, "active": True, "language": "en"},
    {"phrase": "you should be fired", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"phrase": "don't ever talk to me", "category": "aggressive_language", "severity": 2, "active": True, "language": "en"},
    {"phrase": "you will regret this", "category": "threat", "severity": 3, "active": True, "language": "en"}
]

IMPROVEMENT_SUGGESTIONS = {
    "insult": {
        "category": "insult",
        "suggestion": "Express disagreement with the idea or outcome without attacking the person.",
        "example": "I don't agree with this approach. Could we consider another solution?"
    },
    "personal_attack": {
        "category": "personal_attack",
        "suggestion": "Focus on the specific work challenge rather than personal traits.",
        "example": "I'm concerned about how this project is progressing. Let's look at where we can make improvements together."
    },
    "aggressive_language": {
        "category": "aggressive_language",
        "suggestion": "Frame your request constructively to invite collaboration rather than resistance.",
        "example": "Could we pause to align our perspectives and discuss what is needed to move forward?"
    },
    "threat": {
        "category": "threat",
        "suggestion": "De-escalate the situation. State your boundaries and expectations calmly.",
        "example": "Let us take a brief pause and return to this discussion with a constructive mindset."
    },
    "bullying": {
        "category": "bullying",
        "suggestion": "Practice supportive, inclusive workplace communication.",
        "example": "Everyone brings valuable input to the team. Let's ensure every perspective is considered objectively."
    },
    "harassment": {
        "category": "harassment",
        "suggestion": "Maintain clear professional boundaries and respectful language.",
        "example": "Let's focus strictly on the project goals and keep our exchange professional."
    },
    "profanity": {
        "category": "profanity",
        "suggestion": "Replace profanity with clear, professional terms that convey urgency without disrespect.",
        "example": "This situation requires urgent attention so that we avoid potential complications."
    }
}


def export_seed_data(output_path: str):
    """Save seed data to JSON for local engine fallback and offline bootstrapping."""
    data = {
        "categories": [c["id"] for c in CATEGORIES],
        "category_details": CATEGORIES,
        "severity_levels": SEVERITY_LEVELS,
        "bad_words": BAD_WORDS,
        "harassment_patterns": HARASSMENT_PATTERNS,
        "improvement_suggestions": IMPROVEMENT_SUGGESTIONS
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Seed] Successfully exported seed rules to: {output_path}")


def seed_firestore():
    """Seed directly into Firebase Firestore if firebase-admin credentials are configured."""
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    project_id = os.getenv("FIREBASE_PROJECT_ID", "conversx-moderation")

    if not cred_path or not os.path.exists(cred_path):
        print("[Seed] No Firebase service account file provided. Exporting seed file for local engine fallback.")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"projectId": project_id})

        db = firestore.client()
        print(f"[Seed] Connected to Firestore project: {project_id}")

        # Seed categories
        cat_batch = db.batch()
        for cat in CATEGORIES:
            doc_ref = db.collection("categories").document(cat["id"])
            cat_batch.set(doc_ref, cat)
        cat_batch.commit()
        print(f"[Seed] Seeded {len(CATEGORIES)} categories.")

        # Seed severity levels
        sev_batch = db.batch()
        for sev in SEVERITY_LEVELS:
            doc_ref = db.collection("severityLevels").document(str(sev["level"]))
            sev_batch.set(doc_ref, sev)
        sev_batch.commit()
        print(f"[Seed] Seeded {len(SEVERITY_LEVELS)} severity levels.")

        # Seed bad words
        bw_batch = db.batch()
        for bw in BAD_WORDS:
            doc_ref = db.collection("badWords").document(bw["word"])
            bw_batch.set(doc_ref, bw)
        bw_batch.commit()
        print(f"[Seed] Seeded {len(BAD_WORDS)} bad words.")

        # Seed harassment patterns
        hp_batch = db.batch()
        for idx, hp in enumerate(HARASSMENT_PATTERNS):
            doc_id = f"hp_{idx+1}_{hp['phrase'].replace(' ', '_')}"
            doc_ref = db.collection("harassmentPatterns").document(doc_id)
            hp_batch.set(doc_ref, hp)
        hp_batch.commit()
        print(f"[Seed] Seeded {len(HARASSMENT_PATTERNS)} harassment patterns.")

        # Seed improvement suggestions
        sug_batch = db.batch()
        for cat_id, sug in IMPROVEMENT_SUGGESTIONS.items():
            doc_ref = db.collection("improvementSuggestions").document(cat_id)
            sug_batch.set(doc_ref, sug)
        sug_batch.commit()
        print(f"[Seed] Seeded {len(IMPROVEMENT_SUGGESTIONS)} improvement suggestions.")

        print("[Seed] Firestore seeding completed successfully!")
        return True
    except Exception as e:
        print(f"[Seed] Error seeding Firestore: {e}")
        return False


if __name__ == "__main__":
    local_path = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "services", "seed_rules.json")
    export_seed_data(os.path.abspath(local_path))
    seed_firestore()
