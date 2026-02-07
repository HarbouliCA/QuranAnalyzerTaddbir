# global_unifier.py
import numpy as np

def unify_global_topics(all_local_topics, ai_engine, merge_threshold=0.75):
    """
    Input: قائمة بكل المواضيع من كل السور
    Output: قائمة مواضيع موحدة (Global Themes)
    """
    global_themes = []

    print(f"🔄 Unifying {len(all_local_topics)} local topics across the Quran...")

    for topic in all_local_topics:
        merged = False
        topic_vec = topic["centroid"]

        # محاولة البحث عن موضوع عالمي موجود يشبه هذا الموضوع المحلي
        for theme in global_themes:
            sim = ai_engine.similarity(theme["theme_vector"], topic_vec)
            
            if sim >= merge_threshold:
                # ✅ وجدنا موضوعاً مشابهاً (مثلاً: قصة يوسف في موضع آخر إن وجدت)
                theme["occurrences"].append({
                    "surah": topic["surah"],
                    "verses": topic["verses"]
                })
                # تحديث متجه الثيم العالمي ليصبح أكثر دقة
                n = len(theme["occurrences"])
                theme["theme_vector"] = (theme["theme_vector"] * (n-1) + topic_vec) / n
                merged = True
                break
        
        if not merged:
            # إنشاء ثيم عالمي جديد
            global_themes.append({
                "id": len(global_themes) + 1,
                "theme_vector": topic_vec,
                "occurrences": [{
                    "surah": topic["surah"],
                    "verses": topic["verses"]
                }]
            })

    return global_themes