# Applied AI System Project

An evolution of my earlier **AI-110** coursework. This repository combines two systems I
built in Modules 2 and 3 into a single applied AI project. Both originals are preserved
here **with their full commit history** in dedicated subfolders.

## Subsystems

| Folder | Project | Summary |
|--------|---------|---------|
| [`module2-pawpal/`](module2-pawpal/) | 🐾 **PawPal+** | Explainable pet-care scheduler (Streamlit + CLI) that builds a prioritized daily plan and says *why*. |
| [`module3-music-recommender/`](module3-music-recommender/) | 🎵 **Music Recommender Simulation** | Content-based recommender that scores, ranks, and explains song matches against a taste profile. |

## Architecture

The system architecture is maintained as **Mermaid source** in
[`diagrams/architecture.mmd`](diagrams/architecture.mmd). Exported diagram images (e.g. PNGs)
belong in [`assets/`](assets/).

## Repository layout

```
.
├── assets/                     # architecture images (PNG exports)
├── diagrams/                   # Mermaid source of truth (.mmd)
│   └── architecture.mmd
├── module2-pawpal/             # Module 2 — PawPal+ (full history)
└── module3-music-recommender/  # Module 3 — Music Recommender (full history)
```

## Getting started

Each subsystem keeps its own `README.md` and `requirements.txt`. See the individual
folders for setup and usage instructions.
