import requests
import re
import streamlit as st
import random

# ==========================================
# 1. تحميل ومعالجة البيانات (Backend Core)
# ==========================================

def normalize_text(text):
    """تطبيع النص (إزالة التشكيل وتوحيد الألف)"""
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED\u06E5\u06E6]', '', text)
    text = re.sub(r'[أإآ]', 'ا', text)
    return text

@st.cache_resource
def load_quran_db():
    """تحميل المصحف مرة واحدة وتخزينه في الذاكرة المشتركة"""
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

# تحميل البيانات عند استدعاء الملف
QURAN_DATA = load_quran_db()

# ==========================================
# 2. أدوات البحث (Search Tools)
# ==========================================

def search_multi_roots_tool(roots_list):
    """للوكيل المحلل: البحث عن جذور لغوية"""
    if not QURAN_DATA: return "⚠️ قاعدة البيانات غير جاهزة."
    report = ""
    total_hits = 0
    for root in roots_list:
        root = normalize_text(root.strip())
        if len(root) < 3: continue
        chars = list(root)
        pattern = fr"\w*{chars[0]}\w*{chars[1]}\w*{chars[2]}\w*"
        matches = []
        for ayah in QURAN_DATA:
            if re.search(pattern, ayah["normalized"]):
                matches.append(f"- {ayah['uthmani']} [{ayah['ref']}]")
        count = len(matches)
        if count > 0:
            total_hits += 1
            sample = matches[:3]
            if count > 6: sample += random.sample(matches[3:], 3)
            elif count > 3: sample += matches[3:]
            report += f"\n💎 **الجذر ({root}):** ورد {count} مرة. شواهد:\n" + "\n".join(sample) + "\n___\n"
    if total_hits == 0: return "لم يتم العثور على تطابق."
    return report

def search_prophet_story_tool(prophet_name):
    """للوكيل القصصي: البحث عن آيات نبي معين"""
    if not QURAN_DATA: return None
    name = normalize_text(prophet_name.strip())
    matches = []
    for ayah in QURAN_DATA:
        if name in ayah["normalized"]:
            matches.append(f"[{ayah['ref']}] {ayah['uthmani']}")
    
    if not matches: return None
    # نرجع أكبر قدر ممكن من الآيات لبناء السياق (أول 60 آية مثلاً)
    return "\n".join(matches[:60])