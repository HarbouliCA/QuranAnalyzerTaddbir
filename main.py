# main.py
import json
import numpy as np
from data_loader import load_mock_quran
from ai_engine import Semantics
from sequential_processor import StreamProcessor
from global_unifier import unify_global_topics

# دالة مساعدة لحفظ الـ Numpy Arrays في JSON
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

def run_pipeline():
    # 1. التجهيز
    quran_data = load_mock_quran()
    ai = Semantics()
    processor = StreamProcessor(ai_engine=ai, threshold=0.60) 
    # Threshold 0.60 جيد للتفريق بين القصص المختلفة داخل السورة

    all_local_topics = []

    # 2. المرحلة الأولى: المسح التتابعي (Sequential Scan)
    print("🚀 Starting Sequential Analysis...")
    for surah_name, verses in quran_data.items():
        print(f"   Analyzing: {surah_name}...")
        topics = processor.process_surah(surah_name, verses)
        all_local_topics.extend(topics)

    # 3. المرحلة الثانية: التوحيد العالمي (Global Unification)
    final_graph = unify_global_topics(all_local_topics, ai, merge_threshold=0.70)

    # 4. حفظ النتائج
    output = []
    for theme in final_graph:
        # تنظيف البيانات للحفظ (حذف المتجهات الرياضية لتقليل حجم الملف)
        clean_theme = {
            "theme_id": theme["id"],
            "related_segments": theme["occurrences"]
        }
        output.append(clean_theme)

    with open("quran_topic_graph.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4, cls=NumpyEncoder)

    print(f"\n✅ Done! Identified {len(output)} unique global themes.")
    print("📂 Results saved to 'quran_topic_graph.json'")

if __name__ == "__main__":
    run_pipeline()