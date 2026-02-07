# sequential_processor.py
import numpy as np

class StreamProcessor:
    def __init__(self, ai_engine, threshold=0.65):
        self.ai = ai_engine
        self.threshold = threshold # عتبة الفصل بين المواضيع

    def process_surah(self, surah_name, verses):
        """
        Input: قائمة آيات السورة
        Output: قائمة بالمواضيع المستخلصة (Local Topics)
        """
        extracted_topics = []
        
        # الحالة الحالية للموضوع
        current_topic = {
            "surah": surah_name,
            "verses": [],     # قائمة الآيات في الموضوع الحالي
            "centroid": None  # متوسط المتجهات للموضوع (Topic Vector)
        }

        for ayah_num, text in verses:
            # 1. فهم الآية الحالية
            vec = self.ai.embed(text)

            # 2. إذا كان هذا أول موضوع في السورة
            if not current_topic["verses"]:
                current_topic["verses"].append({"ayah": ayah_num, "text": text})
                current_topic["centroid"] = vec
                continue

            # 3. اختبار الاستمرارية (Continuity Check)
            # نقارن الآية الجديدة بـ "مركز" الموضوع الحالي وليس فقط آخر آية
            score = self.ai.similarity(current_topic["centroid"], vec)

            if score >= self.threshold:
                # ✅ نفس الموضوع: أضف الآية وحدث المركز
                current_topic["verses"].append({"ayah": ayah_num, "text": text})
                # تحديث المتوسط (Moving Average)
                n = len(current_topic["verses"])
                current_topic["centroid"] = (current_topic["centroid"] * (n-1) + vec) / n
            else:
                # ❌ موضوع جديد: أغلق القديم وابدأ الجديد
                extracted_topics.append(current_topic)
                
                # بدء موضوع جديد
                current_topic = {
                    "surah": surah_name,
                    "verses": [{"ayah": ayah_num, "text": text}],
                    "centroid": vec
                }

        # إضافة آخر موضوع تبقى
        if current_topic["verses"]:
            extracted_topics.append(current_topic)

        return extracted_topics