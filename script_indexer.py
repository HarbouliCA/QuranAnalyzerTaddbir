import google.generativeai as genai
import json
import time
from quran_utils import load_quran_db

# إعداد الـ API
genai.configure(api_key="")
# يمكن استخدام Flash لسرعته، لكن Pro أدق في الفهم الموضوعي
model = genai.GenerativeModel('gemini-3-flash-preview') 

quran = load_quran_db()

def build_thematic_index():
    """
    يقوم بمسح القرآن وبناء فهرس موضوعي
    """
    thematic_index = {}
    
    # لتبسيط العملية وتوفير الوقت في هذا المثال، سنقوم بفهرسة سورة يوسف فقط كمثال عملي
    # في التطبيق الحقيقي، يمكنك عمل حلقة تكرار على كل السور
    
    target_surahs = [12] # سورة يوسف (رقم 12)
    
    print("بدء الفهرسة الذكية...")
    
    for surah_id in target_surahs:
        # 1. تجميع نص السورة كاملاً وتخزين الآيات للوصول السريع
        surah_text = ""
        ayahs_map = {} # خريطة: رقم الآية -> نص الآية
        
        for ayah in quran:
            if f"({surah_id}:" in ayah['ref']:
                # استخراج رقم الآية من المرجع: "يوسف (12:1)" -> 1
                try:
                    verse_part = ayah['ref'].split(':')[1] # 1)
                    verse_num = int(verse_part.replace(')', ''))
                    
                    ayahs_map[verse_num] = ayah['uthmani']
                    surah_text += f"{verse_num}. {ayah['uthmani']}\n"
                except:
                    continue
        
        if not surah_text:
            print(f"لم يتم العثور على آيات للسورة {surah_id}")
            continue

        # 2. إرسال السورة للذكاء الاصطناعي لتقسيمها موضوعياً
        prompt = f"""
        لديك نص سورة كاملة من القرآن (سورة يوسف).
        المهمة: قسم هذه السورة إلى "وحدات موضوعية قصصية" متماسكة (مواضيع فرعية).
        لكل موضوع، حدد عنواناً دقيقاً يعبر عن الحدث، وأرقام الآيات (من.. إلى) التي تغطيه.
        
        النص:
        {surah_text}
        
        المخرجات المطلوبة: JSON فقط بصيغة القائمة التالية (بدون أي نصوص إضافية):
        [
            {{"topic": "عنوان الموضوع", "start_ayah": 1, "end_ayah": 5}},
            {{"topic": "عنوان آخر", "start_ayah": 6, "end_ayah": 15}}
        ]
        """
        
        try:
            response = model.generate_content(prompt)
            # تنظيف الرد للحصول على JSON
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            topics = json.loads(clean_json)
            
            # 3. إثراء البيانات بالنصوص القرآنية
            enriched_topics = []
            for t in topics:
                start = int(t.get('start_ayah'))
                end = int(t.get('end_ayah'))
                
                # تجميع نص الآيات لهذا الموضوع
                topic_verses = []
                for v in range(start, end + 1):
                    if v in ayahs_map:
                        topic_verses.append(f"({v}) {ayahs_map[v]}")
                
                t['content'] = " ".join(topic_verses)
                enriched_topics.append(t)
            
            # تخزين النتائج باسم السورة (يمكن تحسين الاسم لاحقاً)
            # هنا سنستخدم "Surah_12" أو يمكن جلب الاسم من أول آية
            key = f"Surah_{surah_id} (سورة يوسف)" 
            thematic_index[key] = enriched_topics
            
            print(f"تمت فهرسة السورة {surah_id} بنجاح: {len(topics)} موضوع.")
            time.sleep(1) 
            
        except Exception as e:
            print(f"خطأ في فهرسة السورة {surah_id}: {e}")
            # print(response.text) # للديباج

    # حفظ الملف النهائي
    with open("quran_themes.json", "w", encoding="utf-8") as f:
        json.dump(thematic_index, f, ensure_ascii=False, indent=4)
    
    print("تم حفظ الفهرس الموضوعي في quran_themes.json")

if __name__ == "__main__":
    build_thematic_index()