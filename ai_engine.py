# ai_engine.py
from sentence_transformers import SentenceTransformer
import numpy as np

class Semantics:
    def __init__(self):
        print("⏳ Loading AI Model (MiniLM)...")
        # نموذج خفيف وسريع ويدعم العربية بشكل جيد للمقارنات
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    def embed(self, text):
        """تحويل النص إلى متجه رياضي"""
        return self.model.encode(text)

    def similarity(self, vec1, vec2):
        """حساب نسبة التشابه (Cosine Similarity)"""
        # Dot product for normalized vectors is cosine similarity
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))