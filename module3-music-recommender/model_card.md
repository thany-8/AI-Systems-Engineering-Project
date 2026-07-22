# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFlow 1.0**

VibeFlow is a small music recommendation system that suggests songs based on a user’s preferred vibe, mood, genre, and musical characteristics.

---

## 2. Intended Use

VibeFlow is designed mainly for young adults and other listeners who want to discover songs that match their current mood or preferred musical style.

The system generates song recommendations by comparing the user’s taste profile with the features of each song in the catalog. It assumes that the user’s preferences can be represented through features such as favorite genre, preferred mood, energy, tempo, valence, danceability, and acousticness.

This project is intended for classroom exploration and learning. It is not a production-level recommendation system and should not be treated as a replacement for real-world platforms such as Spotify, Apple Music, or YouTube Music.

---

## 3. How the Model Works

VibeFlow uses a content-based recommendation approach.

Each song is described using the following features:

- Genre
- Mood
- Energy
- Tempo
- Valence
- Danceability
- Acousticness

The user profile stores preferred genres and moods, along with target values for the numerical features.

The recommender compares every song with the user profile and calculates a score. Songs receive more points when their genre or mood matches the user’s preferences. They also receive similarity points when their energy, tempo, valence, danceability, and acousticness are close to the user’s target values.

After every song is scored, the system sorts the songs from the highest score to the lowest score and returns the top recommendations.

Compared with the starter logic, I added more musical features, created weighted scoring rules, included support for related genre families, and added written explanations that show why each song was recommended.

---

## 4. Data

The current dataset contains **30 songs**.

The catalog includes several genres, such as:

- Pop
- Reggaeton
- Salsa
- Dance-pop
- Alternative pop
- Indie pop
- Hip-hop
- Afrobeats
- Latin pop
- Rock-related styles

The dataset also includes moods such as:

- Happy
- Sad
- Relaxed
- Romantic
- Energetic
- Confident
- Emotional
- Playful
- Dark


I added and organized song data manually in a CSV file. Each song includes categorical and numerical features.

Because the dataset is small, many musical styles are missing or underrepresented. The catalog does not fully represent classical music, jazz, country, regional music, experimental music, or many international genres.

The numerical features also have different levels of variation:

| Feature | Standard deviation | Range | Interpretation |
|---|---:|---:|---|
| Acousticness | 0.31 | 0.01–0.93 | Widest spread and most useful for separating songs |
| Energy | 0.22 | 0.28–0.93 | Strong variation across the catalog |
| Valence | 0.21 | 0.12–0.96 | Strong variation and useful for mood differences |
| Tempo | 25.8 | 60–171 BPM | Good variation, but it must be normalized |
| Danceability | 0.14 | 0.35–0.88 | Narrower range, so it may have less influence |

Acousticness appears to be the most discriminating feature in the current dataset. Danceability is more clustered, so it may not separate songs as strongly.

---

## 5. Strengths

VibeFlow works best for users whose preferences are clearly represented in the dataset.

For example, it performs reasonably well for users who prefer:

- Happy pop songs
- Energetic reggaeton
- Relaxed acoustic music
- Danceable music with high valence
- Calm songs with low energy

The scoring system captures several useful patterns. It can distinguish between songs that belong to the same genre but have different energy, tempo, or acousticness.

The recommendations often match intuition when a song matches both the user’s preferred genre and mood while also being close to the user’s numerical targets.

For example, `Sunrise City` ranked first for a happy pop profile because it matched the preferred genre and mood and was also close to the user’s targets for energy, positivity, tempo, danceability, and acousticness.

Another strength is that the system provides an explanation for each recommendation. This makes the result easier to understand instead of only showing a score.

---

## 6. Limitations and Bias

VibeFlow has several limitations:

- The dataset contains a small number of songs.
- Song features were manually labeled and may be subjective.
- Mood and genre do not always have one correct label.
- The system may over-prioritize genre because genre receives a large weight.
- It may ignore good songs from unfamiliar genres even when their mood and numerical features match the user.
- A single user profile cannot represent every listening situation.
- A user may prefer different music while studying, exercising, relaxing, driving, or attending a party.
- The system does not analyze lyrics or language.
- It does not learn from likes, skips, repeated plays, ratings, or listening history.
- Songs with missing or inaccurate feature values may receive unfair scores.
- The recommender may repeatedly suggest similar songs and reduce musical variety.
- Some genres and moods are underrepresented in the dataset.
- Related genre families are manually defined, which may introduce additional bias.
- Danceability has a narrower range in the dataset, so it may contribute less than expected.
- Tempo uses a different scale from the other features, so incorrect normalization could affect the ranking.

Because the system depends on manually selected features and weights, the designer’s choices directly influence the recommendations.

---

## 7. Evaluation

I evaluated the recommender by testing different user profiles and comparing the results with what I expected.

I tested profiles such as:

- Happy and energetic pop
- Danceable reggaeton
- Calm and acoustic music
- Intense rock
- Chill lofi-style music

I looked for several things in the results:

- Whether the top songs matched the preferred genre
- Whether the mood matched the user profile
- Whether the numerical features were close to the target values
- Whether related genres appeared when appropriate
- Whether the explanation matched the actual scoring logic

One important test was checking whether the system could distinguish between intense rock and chill lofi. These profiles have different energy, tempo, mood, and acousticness values, so the recommender should rank them differently.

I also compared the effect of changing feature weights. Increasing the genre weight produced more exact genre matches, but it reduced variety. Including mood and numerical similarity created more balanced recommendations.

One surprising result was that a song from a related genre could rank highly when its mood and numerical features matched the user better than an exact genre match.

The project also includes tests using `pytest` to check the main recommendation behavior.

---

## 8. Future Work

Future versions of VibeFlow could be improved by:

- Expanding the song catalog
- Adding more genres, moods, and international music
- Allowing users to create multiple profiles
- Creating separate profiles for studying, exercising, relaxing, and partying
- Learning from likes, dislikes, skips, and repeated plays
- Adding song language and release year
- Analyzing lyrics and themes
- Improving genre-family relationships
- Normalizing all numerical features more carefully
- Adding diversity rules so the top results are not too similar
- Preventing repeated recommendations
- Showing a detailed score breakdown for every feature
- Allowing users to adjust the importance of genre, mood, or energy
- Building a visual interface with Flask or Streamlit
- Connecting to a real music API
- Using collaborative filtering in addition to content-based filtering

A future version could combine content-based recommendations with user behavior to produce more personalized results.

---

## 9. Personal Reflection

This project helped me understand how a recommender system turns data into predictions. I learned that each song must first be represented through features, and the user must also be represented through a taste profile. The system then compares those values, calculates scores, and ranks the songs.

One interesting discovery was how much the feature weights affect the final recommendations. A small change in the genre or mood weight can change which songs appear at the top. I also learned that numerical features such as energy, valence, and acousticness can help distinguish between songs that belong to the same genre.

This project changed the way I think about music recommendation apps. Before, recommendations seemed automatic and simple. Now I understand that they depend on data quality, feature selection, scoring decisions, and possible bias. Real music platforms likely use much more complex systems, but this project helped me understand the basic ideas behind them.