import requests
import json
import numpy as np
import pickle
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

# =========================================================
# 1. CONFIG
# =========================================================

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SIM_THRESHOLD_CONTINUITY = 0.78     # same topic (ayah n → n+1)
SIM_THRESHOLD_GLOBAL = 0.82         # same topic across surahs

# =========================================================
# 2. TEXT NORMALIZATION (semantic-safe)
# =========================================================

def normalize_text(text):
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', text)
    text = text.replace("ٱ", "ا").replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return text.strip()

# =========================================================
# 3. LOAD QURAN (NO INTERPRETATION)
# =========================================================

def load_quran():
    url = "https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json"
    data = requests.get(url).json()

    quran = {}
    for surah in data:
        surah_name = surah["name"]
        verses = []
        for ayah in surah["verses"]:
            verses.append({
                "ayah": ayah["id"],
                "text": ayah["text"],
                "clean": normalize_text(ayah["text"]),
                "ref": f"{surah['id']}:{ayah['id']}"
            })
        quran[surah_name] = verses
    return quran

# =========================================================
# 4. EMBEDDING ENGINE
# =========================================================

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(MODEL_NAME)

    def encode(self, text):
        return self.model.encode(text)

# =========================================================
# 5. CONTINUITY DECISION (ayah → ayah)
# =========================================================

def same_topic(vec1, vec2, threshold):
    score = cosine_similarity([vec1], [vec2])[0][0]
    return score >= threshold, score

# =========================================================
# 6. SURAH ANALYSIS (SEQUENTIAL ONLY)
# =========================================================

def analyze_surah(surah_name, verses, embedder):
    topics = []
    current_topic = None

    for v in verses:
        vec = embedder.encode(v["clean"])

        if current_topic is None:
            current_topic = {
                "surah": surah_name,
                "ayahs": [v],
                "vector": vec
            }
            continue

        same, score = same_topic(current_topic["vector"], vec, SIM_THRESHOLD_CONTINUITY)

        if same:
            current_topic["ayahs"].append(v)
            current_topic["vector"] = (current_topic["vector"] + vec) / 2
        else:
            topics.append(current_topic)
            current_topic = {
                "surah": surah_name,
                "ayahs": [v],
                "vector": vec
            }

    if current_topic:
        topics.append(current_topic)

    return topics

# =========================================================
# 7. GLOBAL TOPIC UNIFICATION (Quran ↔ Quran)
# =========================================================

def unify_topics(local_topics):
    unified = []

    for topic in local_topics:
        merged = False
        for u in unified:
            same, score = same_topic(u["vector"], topic["vector"], SIM_THRESHOLD_GLOBAL)
            if same:
                u["ayahs"].extend(topic["ayahs"])
                u["vector"] = (u["vector"] + topic["vector"]) / 2
                merged = True
                break

        if not merged:
            unified.append({
                "ayahs": topic["ayahs"][:],
                "vector": topic["vector"]
            })

    return unified

# =========================================================
# 8. BUILD SELF-EXPLAINING LINKS
# =========================================================

def build_cross_references(topics):
    ayah_index = defaultdict(list)

    for idx, topic in enumerate(topics):
        for ayah in topic["ayahs"]:
            ayah_index[ayah["ref"]].append(idx)

    return ayah_index

# =========================================================
# 9. MAIN PIPELINE
# =========================================================

def run():
    print("📥 Loading Quran...")
    quran = load_quran()

    print("🧠 Loading model...")
    embedder = Embedder()

    print("⚙️ Sequential analysis...")
    local_topics = []
    for surah, verses in quran.items():
        local_topics.extend(analyze_surah(surah, verses, embedder))

    print(f"📌 Local topics: {len(local_topics)}")

    print("🔗 Global unification...")
    unified_topics = unify_topics(local_topics)

    print(f"🧩 Unified Quran topics: {len(unified_topics)}")

    print("🪢 Building self-references...")
    ayah_topic_map = build_cross_references(unified_topics)

    # -----------------------------------------------------
    # SAVE OUTPUT
    # -----------------------------------------------------

    output = {
        "topics": [
            {
                "id": i,
                "ayahs": [a["ref"] for a in t["ayahs"]]
            }
            for i, t in enumerate(unified_topics)
        ],
        "ayah_index": dict(ayah_topic_map)
    }

    with open("quran_topics_v2.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open("quran_topic_vectors_v2.pkl", "wb") as f:
        pickle.dump([t["vector"] for t in unified_topics], f)

    print("✅ Version 2 complete.")
    print("📁 Files generated:")
    print("   - quran_topics_v2.json")
    print("   - quran_topic_vectors_v2.pkl")

# =========================================================

if __name__ == "__main__":
    run()
