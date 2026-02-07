import requests
import re
import streamlit as st
import random
import json
import os

# ==========================================
# 1. تحميل ومعالجة البيانات (Core)
# ==========================================

def normalize_text(text):
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u06E5\u06E6]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    text = text.replace('ة', 'ه') # توحيد التاء المربوطة والهاء
    return text

@st.cache_resource
def load_quran_db():
    url = "https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            quran_list = []
            for surah in data:
                s_name = surah['name']
                s_id = surah['id']
                for ayah in surah['verses']:
                    quran_list.append({
                        "ref": f"{s_name} ({s_id}:{ayah['id']})",
                        "uthmani": ayah['text'],
                        "normalized": normalize_text(ayah['text'])
                    })
            return quran_list
        return None
    except:
        return None

QURAN_DATA = load_quran_db()

# ==========================================
# 2. نظام الفهرسة الحية (Live Indexing System)
# ==========================================
THEMES_FILE = "quran_themes.json"

def load_themes_db():
    """تحميل قاعدة بيانات المواضيع، وإنشاؤها إذا لم تكن موجودة"""
    if not os.path.exists(THEMES_FILE):
        with open(THEMES_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(THEMES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_topic_to_db(topic_name, verses_data):
    """
    حفظ موضوع جديد في قاعدة البيانات لعدم تكرار البحث
    verses_data: قائمة قواميس {title, content}
    """
    db = load_themes_db()
    # تنظيف الاسم لمنع التكرار (مثلاً: موسى = قصة موسى)
    db[topic_name] = verses_data
    with open(THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def live_indexer_agent(model, topic_keyword, status_callback=None):
    """
    العميل المفهرس: يبحث في القرآن، يقسم الآيات لمواضيع، ويحفظها
    """
    if not QURAN_DATA:
        if status_callback: status_callback("⚠️ قاعدة البيانات غير جاهزة.")
        return None

    # 1. معالجة كلمات البحث
    if status_callback: status_callback(f"🔍 تحليل كلمات البحث: {topic_keyword}...")
    raw_keyword = normalize_text(topic_keyword)
    
    # قائمة كلمات التجاهل (Stop Words) التي لا تفيد في البحث
    stop_words = ["قصه", "سوره", "عن", "نبي", "حكايه", "موقف"] 
    
    keywords = [w for w in raw_keyword.split() if w not in stop_words and len(w) > 2]
    
    # إذا لم يبق شيء (مثل كتب "قصة" فقط)، نعود للكلمة الأصلية
    if not keywords:
        keywords = [raw_keyword]
        
    print(f"Searching for keywords: {keywords}")
    if status_callback: status_callback(f"🗝️ الكلمات المفتاحية: {keywords}")

    raw_verses = []
    for ayah in QURAN_DATA:
        # البحث عن أي من الكلمات المفتاحية
        match = False
        for kw in keywords:
            if kw in ayah["normalized"]:
                match = True
                break
        
        if match:
            raw_verses.append(f"{ayah['ref']}: {ayah['uthmani']}")
    
    if not raw_verses:
        if status_callback: status_callback("❌ لم يتم العثور على آيات مطابقة.")
        return None
    
    if status_callback: status_callback(f"✅ تم العثور على {len(raw_verses)} آية. جاري المعالجة بالذكاء الاصطناعي...")
    
    # نأخذ أكبر قدر ممكن من الآيات (حتى 100 آية لتكوين مشهد)
    context_text = "\n".join(raw_verses[:100])

    # 2. طلب الفهرسة من الذكاء الاصطناعي
    prompt = f"""
    لديك نصوص قرآنية تتحدث عن موضوع "{topic_keyword}".
    المهمة: قم بتجميع هذه الآيات وتقسيمها إلى "مشاهد موضوعية" مترابطة.
    
    الشروط:
    1. تجاهل الآيات التي تذكر الكلمة بشكل عابر غير قصصي.
    2. ركز على الآيات التي تشكل "مشهدًا كاملاً".
    3. المخرجات يجب أن تكون JSON حصراً بهذه الصيغة:
    [
      {{ "title": "عنوان المشهد (مثال: بداية الوحي)", "content": "نص الآيات..." }},
      {{ "title": "عنوان المشهد (مثال: المواجهة)", "content": "نص الآيات..." }}
    ]
    
    النصوص الخام:
    {context_text}
    """
    
    try:
        if status_callback: status_callback("🤖 جاري توليد المشاهد (قد يستغرق لحظات)...")
        response = model.generate_content(prompt)
        
        # تنظيف الرد لاستخراج JSON
        json_str = response.text.replace("```json", "").replace("```", "").strip()
        # محاولة تنظيف إضافية في حال وجود نصوص قبل/بعد
        if "{" in json_str:
             start = json_str.find("[")
             end = json_str.rfind("]") + 1
             if start != -1 and end != -1:
                 json_str = json_str[start:end]

        scenes = json.loads(json_str)
        
        # 3. الحفظ التلقائي
        if status_callback: status_callback(f"💾 تم استخراج {len(scenes)} مشهد. جاري الحفظ...")
        save_topic_to_db(topic_keyword, scenes)
        return scenes
        
    except Exception as e:
        error_msg = f"Indexing Error: {str(e)}"
        print(error_msg)
        if status_callback: status_callback(f"❌ حدث خطأ: {str(e)}")
        return None

# ==========================================
# 3. أدوات البحث الجذري (للمحلل)
# ==========================================
def search_multi_roots_tool(roots_list):
    if not QURAN_DATA: return "⚠️ قاعدة البيانات غير جاهزة."
    report = ""
    for root in roots_list:
        # تنظيف الجذر من الرموز (مثل الأقواس)
        root = re.sub(r'[^\w]', '', root)
        root = normalize_text(root.strip())
        if len(root) < 3: continue
        
        chars = list(root)
        # استخدام re.escape لتجنب أخطاء الريجيكس
        pattern = fr"\w*{re.escape(chars[0])}\w*{re.escape(chars[1])}\w*{re.escape(chars[2])}\w*"
        
        matches = []
        try:
            for ayah in QURAN_DATA:
                if re.search(pattern, ayah["normalized"]):
                    matches.append(f"- {ayah['uthmani']} [{ayah['ref']}]")
        except Exception as e:
            print(f"Skipping root {root} due to error: {e}")
            continue

        if matches:
            sample = matches[:4] 
            if len(matches) > 4: sample += random.sample(matches[4:], 2)
            report += f"\n💎 **الجذر ({root}):** ورد {len(matches)} مرة. شواهد:\n" + "\n".join(sample) + "\n___\n"
    return report if report else "لم يتم العثور على تطابق."

def search_prophet_story_tool(prophet_name):
    """
    للوكيل القصصي: البحث عن آيات نبي معين لبناء السياق
    """
    if not QURAN_DATA: return None
    
    name = normalize_text(prophet_name.strip())
    matches = []
    
    for ayah in QURAN_DATA:
        # بحث بسيط عن اسم النبي في النص
        if name in ayah["normalized"]:
            matches.append(f"[{ayah['ref']}] {ayah['uthmani']}")
    
    if not matches: return None
    
    # نرجع أكبر قدر ممكن من الآيات لبناء السياق (أول 70 آية مثلاً)
    return "\n".join(matches[:70])