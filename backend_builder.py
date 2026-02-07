import requests
import json
import numpy as np
import pickle
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# --- إعدادات النموذج ---
# نستخدم نموذجاً يدعم العربية بكفاءة عالية للفهم الدلالي
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

def normalize_text(text):
    # توحيد الرسم الإملائي للبحث (اختياري لأن النموذج يفهم المعنى، لكنه مفيد)
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u06E5\u06E6]', '', text)
    text = text.replace("ٱ", "ا").replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    text = text.replace("ة", "ه").replace("ى", "ي")
    return text

def load_quran_data():
    print("📥 تحميل بيانات القرآن...")
    url = "https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json"
    response = requests.get(url)
    data = response.json()
    formatted_data = {}
    
    for surah in data:
        surah_name = surah['name']
        verses = []
        for ayah in surah['verses']:
            # نحتفظ بالنص الأصلي وبالنص المعالج
            clean_text = normalize_text(ayah['text'])
            verses.append({
                "number": ayah['id'],
                "text": ayah['text'],
                "clean_text": clean_text,
                "ref": f"{surah_name} ({surah['id']}:{ayah['id']})"
            })
        formatted_data[surah_name] = verses
    return formatted_data

def process_quran_vectors():
    print("🧠 جاري تحميل نموذج الذكاء الاصطناعي (قد يستغرق وقتاً لأول مرة)...")
    model = SentenceTransformer(MODEL_NAME)
    
    quran = load_quran_data()
    all_topics = []
    global_topic_id = 0
    
    print("⚙️ جاري تقسيم القرآن إلى وحدات موضوعية وحساب المتجهات...")

    for surah_name, verses in quran.items():
        # تجميع مبدئي للآيات (مثلاً كل 3-5 آيات تشكل وحدة سياقية صغيرة)
        # أو استخدام التشابه لدمج الآيات المتشابهة
        
        current_chunk_verses = []
        current_chunk_text = ""
        
        for i, ayah in enumerate(verses):
            current_chunk_verses.append(ayah)
            current_chunk_text += " " + ayah['clean_text']
            
            # منطق التقسيم: نغلق الموضوع إذا وصل حجماً معيناً أو (يمكن تطويره ليعتمد على التشابه)
            # هنا سنستخدم نافذة انزلاقية ذكية لضمان السياق
            
            # إذا وصلنا لنهاية السورة أو تجمعت لدينا 5 آيات (كمتوسط لموضوع قصير)
            if len(current_chunk_verses) >= 5 or i == len(verses) - 1:
                global_topic_id += 1
                
                # *** السحر هنا: نحسب "متجه المعنى" لهذا المقطع كاملاً ***
                topic_vector = model.encode(current_chunk_text.strip())
                
                all_topics.append({
                    "id": global_topic_id,
                    "surah": surah_name,
                    "verses": current_chunk_verses,
                    "full_text": current_chunk_text.strip(), # للنص الكامل
                    "vector": topic_vector # البصمة الرياضية للمعنى
                })
                
                # إعادة تعيين للموضوع القادم
                current_chunk_verses = []
                current_chunk_text = ""

    # فصل البيانات (النصية) عن (الرياضية) للحفظ
    json_data = []
    vectors_data = []
    
    for t in all_topics:
        json_data.append({
            "id": t['id'],
            "surah": t['surah'],
            "verses": t['verses'],
            "full_text": t['full_text']
        })
        vectors_data.append(t['vector'])

    print(f"💾 حفظ {len(json_data)} موضوعاً...")
    
    # 1. حفظ النصوص للعرض
    with open("quran_topic_graph.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
        
    # 2. حفظ المتجهات للبحث الذكي
    with open("topic_embeddings.pkl", "wb") as f:
        pickle.dump(np.array(vectors_data), f)
        
    print("✅ تم بناء الأطلس الذكي بنجاح!")

if __name__ == "__main__":
    process_quran_vectors()