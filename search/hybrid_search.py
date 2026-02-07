from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def hybrid_search(
    query,
    model,
    topic_vectors,
    topics,
    graph_search,
    alpha=0.6
):
    """
    alpha = weight for graph (semantic certainty)
    """

    # --- Semantic ---
    q_vec = model.encode(query)
    sims = cosine_similarity([q_vec], topic_vectors)[0]

    semantic_hits = {
        topics[i]["id"]: float(sims[i])
        for i in np.argsort(sims)[-5:]
        if sims[i] > 0.3
    }

    # --- Graph ---
    graph_hits = graph_search.search_by_concept(query)

    results = []

    for g in graph_hits:
        score = alpha
        results.append({
            "ref": g["ref"],
            "text": g["text"],
            "concept": g["concept"],
            "law": g["law"],
            "score": score,
            "source": "graph"
        })

    for tid, score in semantic_hits.items():
        results.append({
            "topic_id": tid,
            "score": (1 - alpha) * score,
            "source": "semantic"
        })

    return results
