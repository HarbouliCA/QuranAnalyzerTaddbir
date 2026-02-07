from search.text_normalizer import normalize
from search.root_matcher import root_match
from data.muqattaat import MUQATTAAT_VERSES

SIMILARITY_THRESHOLD = 0.92

def search_verses(
    query: str,
    verses: list,
    embeddings_model=None
):
    results = []
    nq = normalize(query)

    # المرحلة 1️⃣ Exact Match
    for v in verses:
        if v["id"] in MUQATTAAT_VERSES:
            continue

        text_norm = normalize(v["text"])
        if nq in text_norm:
            results.append({**v, "reason": "exact"})
    
    if results:
        return results

    # المرحلة 2️⃣ Root Match
    for v in verses:
        if v["id"] in MUQATTAAT_VERSES:
            continue

        if root_match(nq, normalize(v["text"])):
            results.append({**v, "reason": "root"})
    
    if results:
        return results

    # المرحلة 3️⃣ Semantic (آخر حل)
    if embeddings_model is None:
        return []

    q_vec = embeddings_model.encode(query)

    for v in verses:
        if v["id"] in MUQATTAAT_VERSES:
            continue

        score = embeddings_model.similarity(q_vec, v["embedding"])
        if score >= SIMILARITY_THRESHOLD:
            results.append({
                **v,
                "reason": "semantic",
                "score": round(score * 100, 2)
            })

    return results
