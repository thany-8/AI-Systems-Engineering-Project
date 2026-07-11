import csv
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

# --- Scoring configuration -------------------------------------------------
# Weights encode how much each matched feature contributes. Genre outweighs
# mood because genre is orthogonal signal, whereas mood largely mirrors the
# numeric valence/energy terms we already score.
WEIGHTS = {
    "genre": 2.0,
    "mood": 1.0,
    "energy": 1.5,
    "valence": 1.0,
    "tempo": 0.5,
    "dance": 0.5,
    "acoustic": 0.5,
}

# (preference key, song column, weight key, human label)
_NUMERIC_FEATURES = [
    ("energy", "energy", "energy", "energy level"),
    ("valence", "valence", "valence", "positivity"),
    ("tempo", "tempo_bpm", "tempo", "tempo"),
    ("dance", "danceability", "dance", "danceability"),
    ("acoustic", "acousticness", "acoustic", "acousticness"),
]
_NUMERIC_COLUMNS = ["energy", "tempo_bpm", "valence", "danceability", "acousticness"]


def _as_list(value) -> List:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v is not None]
    return [value]


def _tokens(genre: str) -> set:
    return {t for t in re.split(r"[^a-z0-9]+", str(genre).lower()) if t}


def _genre_match(favorites: List[str], song_genre: str) -> float:
    """1.0 exact match, 0.5 same family (shared token, e.g. *pop), else 0.0."""
    song = str(song_genre).lower().strip()
    song_tokens = _tokens(song_genre)
    best = 0.0
    for fav in favorites:
        if str(fav).lower().strip() == song:
            return 1.0
        if _tokens(fav) & song_tokens:
            best = 0.5
    return best


def _mood_match(favorites: List[str], song_mood: str) -> float:
    wanted = {str(m).lower().strip() for m in favorites}
    return 1.0 if str(song_mood).lower().strip() in wanted else 0.0


def _closeness(value: float, target: float, span: float) -> float:
    """Reward proximity: 1.0 at an exact match, falling to 0.0 one span away."""
    span = max(float(span), 1e-9)
    return max(0.0, 1.0 - abs(float(value) - float(target)) / span)


def _normalize_prefs(prefs) -> Dict:
    """Accept a dict (singular or plural keys) or a UserProfile dataclass."""
    if not isinstance(prefs, dict):
        prefs = {
            "favorite_genre": getattr(prefs, "favorite_genre", None),
            "favorite_mood": getattr(prefs, "favorite_mood", None),
            "target_energy": getattr(prefs, "target_energy", None),
            "target_valence": getattr(prefs, "target_valence", None),
            "likes_acoustic": getattr(prefs, "likes_acoustic", None),
        }
    acoustic = prefs.get("target_acousticness")
    if acoustic is None and prefs.get("likes_acoustic") is not None:
        acoustic = 1.0 if prefs["likes_acoustic"] else 0.0
    return {
        "genres": _as_list(prefs.get("favorite_genres")) or _as_list(prefs.get("favorite_genre")) or _as_list(prefs.get("genre")),
        "moods": _as_list(prefs.get("favorite_moods")) or _as_list(prefs.get("favorite_mood")) or _as_list(prefs.get("mood")),
        "energy": prefs.get("target_energy", prefs.get("energy")),
        "valence": prefs.get("target_valence", prefs.get("valence")),
        "tempo": prefs.get("target_tempo_bpm", prefs.get("tempo_bpm")),
        "dance": prefs.get("target_danceability", prefs.get("danceability")),
        "acoustic": acoustic,
    }


def _feature_ranges(songs: List[Dict]) -> Dict[str, float]:
    """Catalog span per numeric column, used to normalize closeness (esp. tempo)."""
    ranges = {}
    for col in _NUMERIC_COLUMNS:
        values = [s[col] for s in songs if s.get(col) is not None]
        ranges[col] = (max(values) - min(values)) if len(values) > 1 else 1.0
    return ranges


def _format_reasons(reasons: List[str]) -> str:
    if not reasons:
        return "A modest overall match for your profile."
    return "Recommended because " + "; ".join(reasons) + "."


def _to_dict(song) -> Dict:
    return song if isinstance(song, dict) else asdict(song)


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        ranges = _feature_ranges([_to_dict(s) for s in self.songs])
        ranked = sorted(
            self.songs,
            key=lambda s: score_song(user, _to_dict(s), ranges)[0],
            reverse=True,
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        ranges = _feature_ranges([_to_dict(s) for s in self.songs])
        _, reasons = score_song(user, _to_dict(song), ranges)
        return _format_reasons(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of typed dicts.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if line.strip()]  # tolerate blank lines
    for row in csv.DictReader(lines):
        songs.append({
            "id": int(row["id"]),
            "title": row["title"].strip(),
            "artist": row["artist"].strip(),
            "genre": row["genre"].strip(),
            "mood": row["mood"].strip(),
            "energy": float(row["energy"]),
            "tempo_bpm": float(row["tempo_bpm"]),
            "valence": float(row["valence"]),
            "danceability": float(row["danceability"]),
            "acousticness": float(row["acousticness"]),
        })
    return songs


def score_song(user_prefs, song: Dict, feature_ranges: Optional[Dict] = None) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    Categorical features (genre, mood) score by match; numeric features
    (energy, valence, ...) score by *closeness* to the user's target, so songs
    near the preference win rather than just high/low values. Returns a 0-1
    score (weighted average over the features the profile actually specifies)
    and a list of human-readable reasons.
    """
    prefs = _normalize_prefs(user_prefs)
    ranges = feature_ranges or {}
    total, active_weight, reasons = 0.0, 0.0, []

    if prefs["genres"]:
        g = _genre_match(prefs["genres"], song["genre"])
        total += WEIGHTS["genre"] * g
        active_weight += WEIGHTS["genre"]
        if g == 1.0:
            reasons.append(f"'{song['genre']}' is a favorite genre")
        elif g == 0.5:
            reasons.append(f"'{song['genre']}' is in a favorite genre family")

    if prefs["moods"]:
        m = _mood_match(prefs["moods"], song["mood"])
        total += WEIGHTS["mood"] * m
        active_weight += WEIGHTS["mood"]
        if m == 1.0:
            reasons.append(f"mood '{song['mood']}' matches your taste")

    for pref_key, column, weight_key, label in _NUMERIC_FEATURES:
        target = prefs[pref_key]
        value = song.get(column)
        if target is None or value is None:
            continue
        closeness = _closeness(value, target, ranges.get(column, 1.0))
        total += WEIGHTS[weight_key] * closeness
        active_weight += WEIGHTS[weight_key]
        if closeness >= 0.85:
            reasons.append(f"{label} is close to your target")

    score = total / active_weight if active_weight else 0.0
    return score, reasons


def recommend_songs(user_prefs, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores every song, then ranks: sort by score (desc) and keep the top k.
    Returns (song, score, explanation) tuples for src/main.py.
    """
    if not songs:
        return []
    ranges = _feature_ranges(songs)
    scored = [(song, *score_song(user_prefs, song, ranges)) for song in songs]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [(song, score, _format_reasons(reasons)) for song, score, reasons in scored[:k]]
