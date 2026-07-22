"""
Command line runner for the Music Recommender Simulation.

Loads the song catalog and the user taste profile, then prints the top
recommendations, each with an explanation of why it was chosen.
"""

try:  # works as `python -m src.main` (from repo root) and `python src/main.py`
    from src.recommender import load_songs, recommend_songs
    from src.user_profile import user_profile
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs
    from user_profile import user_profile


def main() -> None:
    songs = load_songs("data/songs.csv")

    recommendations = recommend_songs(user_profile, songs, k=5)

    print("\nTop recommendations:\n")
    for song, score, explanation in recommendations:
        print(f"{song['title']} - Score: {score:.2f}")
        print(f"Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
