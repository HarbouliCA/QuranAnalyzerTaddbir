import streamlit as st
import google.generativeai as genai
import json, os, pickle, requests
import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components
from graph.graph_search import QuranGraphSearch
from search.hybrid_search import hybrid_search
from search.search_engine import search_verses
from context_helpers import (
    build_context_package,
    format_context_for_prompt,
    get_surrounding_verses,
    extract_practical_benefits
)
from session_manager import SessionManager
from local_session_manager import LocalSessionManager

load_dotenv()

# ==========================================
# 0. LETTER PHYSICS DB (KEEP – CORE LAYER)
# ==========================================
LETTER_PHYSICS_DB = """
- أ: ظهور، تجلي، فاعل مطلق.
- ب: وعاء، احتواء، انغلاق جزئي.
- ت: تفرع، انتشار مسار.
- ج: جمع، تكثيف، جسم.
- ح: حيوية، إحاطة دافئة، حياة.
- خ: خفاء، خروج عن المألوف، تخلخل.
- د: دفع، امتداد اتجاهي، ديمومة.
- ذ: ذبذبة، انتشار دقيق.
- ر: تكرار، تردد، ارتداد.
- ز: زحزحة، طاقة مفاجئة.
- س: سريان، امتداد أفقي، سلاسة.
- ش: تفشٍ، انتشار مشتت.
- ص: صدم، صلابة، تماس قوي.
- ض: ضغط، انضغاط.
- ط: طمس، إطباق.
- ظ: ظل، ظهور نسبي.
- ع: عمق، ارتباط.
- غ: غياب، غشاوة.
- ف: فتح، تدفق.
- ق: قانون، قوة، قطعية.
- ك: كف، احتواء صلب.
- ل: إلصاق، لين.
- م: مادة، مركز.
- ن: نفاذ، نور.
- هـ: هواء، هوية.
- و: وصل.
- ي: امتداد، وعي.
"""

SURAH_NAMES = [
    "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", "الأعراف", "الأنفال", "التوبة", "يونس",
    "هود", "يوسف", "الرعد", "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه",
    "الأنبياء", "الحج", "المؤمنون", "النور", "الفرقان", "الشعراء", "النمل", "القصص", "العنكبوت", "الروم",
    "لقمان", "السجدة", "الأحزاب", "سبأ", "فاطر", "يس", "الصافات", "ص", "الزمر", "غافر",
    "فصلت", "الشورى", "الزخرف", "الدخان", "الجاثية", "الأحقاف", "محمد", "الفتح", "الحجرات", "ق",
    "الذاريات", "الطور", "النجم", "القمر", "الرحمن", "الواقعة", "الحديد", "المجادلة", "الحشر", "الممتحنة",
    "الصف", "الجمعة", "المنافقون", "التغابن", "الطلاق", "التحريم", "الملك", "القلم", "الحاقة", "المعارج",
    "نوح", "الجن", "المزمل", "المدثر", "القيامة", "الإنسان", "المرسلات", "النبأ", "النازعات", "عبس",
    "التكوير", "الانفطار", "المطففين", "الانشقاق", "البروج", "الطارق", "الأعلى", "الغاشية", "الفجر", "البلد",
    "الشمس", "الليل", "الضحى", "الشرح", "التين", "العلق", "القدر", "البينة", "الزلزلة", "العاديات",
    "القارعة", "التكاثر", "العصر", "الهمزة", "الفيل", "قريش", "الماعون", "الكوثر", "الكافرون", "النصر",
    "المسد", "الإخلاص", "الفلق", "الناس"
]

def format_ref(ref):
    try:
        s, a = ref.split(":")
        surah_name = SURAH_NAMES[int(s)-1]
        return f"{surah_name}: {a}"
    except:
        return ref

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config("محلل اللسان المبين", "🕋", layout="wide")

st.markdown("""
<style>
.stApp { direction: rtl; text-align: right; font-family: 'Cairo'; }
.ayah-box {
    font-family: 'Amiri';
    font-size: 1.5rem;
    background: #fdfdfd;
    padding: 12px;
    border-right: 5px solid #1a5f45;
    margin-bottom: 8px;
}
.result-box {
    direction: rtl;
    text-align: right;
    background: #f9f9f9;
    padding: 20px;
    border-radius: 10px;
    border: 1px solid #eee;
    font-family: 'Cairo', sans-serif;
    line-height: 1.8;
}
.benefit-card {
    background: linear-gradient(135deg, #1a5f45 0%, #2e7d32 100%);
    color: white;
    padding: 15px;
    border-radius: 10px;
    margin: 10px 0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.benefit-card h4 {
    margin: 0 0 10px 0;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOADERS
# ==========================================
@st.cache_resource
def load_engine():
    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    with open("quran_topics_v2.json", encoding="utf-8") as f:
        topics = json.load(f)["topics"]
    with open("quran_topic_vectors_v2.pkl", "rb") as f:
        vectors = np.array(pickle.load(f))
    return model, topics, vectors

@st.cache_resource
def load_quran():
    data = requests.get(
        "https://raw.githubusercontent.com/risan/quran-json/main/dist/quran.json"
    ).json()
    verses = []
    for s in data:
        for a in s["verses"]:
            verses.append({
                "id": f"{s['id']}:{a['id']}",
                "surah": s["id"],
                "ayah": a["id"],
                "text": a["text"]
            })
    return verses

@st.cache_resource
def load_neo4j():
    try:
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )
        with driver.session() as s:
            s.run("RETURN 1")
        return driver
    except Exception:
        return None

# ==========================================
# 3. NEO4J HELPERS
# ==========================================
def fetch_ayahs(driver, topic_id):
    q = """
    MATCH (a:Ayah)-[:PART_OF]->(t:Topic {id:$id})
    RETURN a.ref ORDER BY a.surah, a.ayah
    """
    with driver.session() as s:
        return [r["a.ref"] for r in s.run(q, id=topic_id)]

def build_network(driver, topic_id, topic_label=None):
    net = Network(height="600px", directed=True)
    q = """
    MATCH (t:Topic {id:$id})<-[:PART_OF]-(a:Ayah)
    RETURN t, collect(a) AS ayahs
    """
    with driver.session() as s:
        res = s.run(q, id=topic_id).single()
        if not res: return net
        
        label = topic_label or f"موضوع {res['t']['id']}"
        net.add_node(res["t"]["id"], label=label, title=label, color="#1a5f45", size=40)
        added = {res["t"]["id"]}
        
        for a in res["ayahs"]:
            display_ref = format_ref(a["ref"])
            if a["ref"] not in added:
                net.add_node(a["ref"], label=display_ref, title=display_ref, color="#fdd835", size=22)
                added.add(a["ref"])
            net.add_edge(a["ref"], res["t"]["id"])

    # Add RELATED_TO edges
    q_edges = """
    MATCH (t:Topic {id:$id})<-[:PART_OF]-(a:Ayah)-[r:RELATED_TO]->(o:Ayah)
    RETURN a.ref AS source, o.ref AS target
    """
    with driver.session() as s:
        for row in s.run(q_edges, id=topic_id):
            display_target = format_ref(row["target"])
            if row["target"] not in added:
                net.add_node(row["target"], label=display_target, title=display_target, color="#42a5f5", size=18)
                added.add(row["target"])
            net.add_edge(row["source"], row["target"])
    return net

# ==========================================
# 4. SEMANTIC TOPIC SEARCH (KEEP)
# ==========================================
def semantic_search(model, topics, vectors, q, k=5):
    v = model.encode(q)
    sims = cosine_similarity([v], vectors)[0]
    idxs = np.argsort(sims)[-k:][::-1]
    return [
        {"id": topics[i]["id"], "ayahs": topics[i]["ayahs"], "score": sims[i]}
        for i in idxs if sims[i] > 0.3
    ]

# ==========================================
# 5. AI ANALYSIS
# ==========================================
# ==========================================
# 5. AI ANALYSIS ENHANCED
# ==========================================
def ai_analysis_enhanced(api_key, question, verses, concept=None, law=None, chat_history=None, verse_refs=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-pro-preview")

    context_str = ""
    for i, verse in enumerate(verses):
        ref = verse_refs[i] if verse_refs and i < len(verse_refs) else f"آية {i+1}"
        context_str += f"\n[{ref}] {verse}"
    
    history_str = ""
    if chat_history:
        history_str = "\n### سياق الحوار السابق:\n"
        for msg in chat_history[-4:]:
            role = "المستخدم" if msg["role"] == "user" else "الوكيل"
            history_str += f"• {role}: {msg['content'][:200]}\n"

    few_shot_example = """
### مثال توضيحي للمنهجية المطلوبة:
السؤال: ما العلاقة بين الخلق الأول والبعث في سورة ق؟

1️⃣ الرابط الموضوعي والسياقي:
الآية (أَفَعَيِينَا بِٱلۡخَلۡقِ ٱلۡأَوَّلِ...) تأتي بعد ذكر مراحل الخلق وعلم الله. القرآن يستخدم قياس القدرة: من قَدِر على البداية قادر على الإعادة.

2️⃣ الآيات المرتبطة موضوعياً:
(يَبۡدَؤُاْ ٱلۡخَلۡقَ ثُمَّ يُعِيدُهُۥ) [الروم:27]، (أَوَلَيۡسَ ٱلَّذِي خَلَقَ ٱلسَّمَٰوَٰتِ...) [يس:81].

3️⃣ التحليل الفيزيائي (كلمة "عَيِينَا"):
- ع: عمق وارتباط.
- ي: وعي وامتداد.
- ن: نفاذ ونور.
المعنى الفيزيائي: "العَيّ" هو استنفاد الوعي (ي) والقدرة (ع) على الامتداد، وهو ما ينفيه الله عن نفسه.

4️⃣ القانون السنني:
وعي بالبدايات + تدبر في القدرة = يقين بالنهايات (الاستقرار النفسي).

5️⃣ الفوائد التطبيقية:
أ. عقدي: كسر الشك في الغيب بالبرهان الحسي اليومي.
ب. نفسي: التحرر من قلق العدم والعبثية.
ج. سلوكي: العيش بمسؤولية لأن كل شيء محسوب.
د. معاصر: في الأزمات، تذكر كيف أخرجك الله من رحم الأم (ضيق→سعة) يمنحك أملاً في تجديد أحوالك.
"""

    prompt = f"""
### الدور والمهمة:
أنت "محلل اللسان العربي المبين". منهجيتك هي "القرآن يفسر نفسه بنفسه". استخدم فيزياء الحرف حصرياً في التحليل اللغوي.

### المرجع العلمي (قاموس فيزياء الحرف):
{LETTER_PHYSICS_DB}

### مثال المنهجية المطلوبة:
{few_shot_example}

---
### بيانات التحليل الحالي:
المفهوم المحوري: {concept or 'سيتم استخلاصه'}
القانون السنني السابق: {law or 'سيتم استنباكه'}

{history_str}

السؤال الحالي: "{question}"

الآيات المرجعية والتحليل السياقي:
{context_str}

### المطلوب منك:
قدم تحليلاً شاملاً (إذا كان سؤالاً جديداً) أو إجابة مركزة (إذا كانت متابعة) تتضمن:
1. التحليل السياقي (ما قبل وما بعد الآيات).
2. الآيات المرتبطة وعلاقتها (القرآن يفسر نفسه).
3. التحليل الفيزيائي لكلمة مفتاحية (بناءً على المرجع أعلاه).
4. القانون السنني (معادلة سلوكية).
5. الفوائد التطبيقية: (أ. عقدي، ب. نفسي، ج. سلوكي، د. معاصر بأمثلة واقعية).

أجب بلسان عربي مبين، عميق، ونافع.
"""
    return model.generate_content(prompt, stream=True)

# ==========================================
# 5.1 DOCTRINE CHECKER (CRITIC/VERIFIER)
# ==========================================
def doctrine_checker(api_key, analysis_text):
    """
    Verifier that checks if the AI followed the methodology:
    1. REJECT if standard traditional/historical Tafsir is used.
    2. RETRY if Letter Physics is missing.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3-pro-preview")
    
    prompt = f"""
    أنت "مراقب المنهجية" لهذا المشروع القرآني المتقدم.
    مهمتك هي مراجعة التحليل التالي والحكم عليه بناءً على معيارين صارمين:

    1. خلو التحليل من "التفسير التقليدي/التاريخي": هل اعتمد التحليل على قصص تاريخية، أو أقوال مفسرين، أو روايات خارجية بدلاً من النص القرآني نفسه؟ (يجب أن يكون الرد: نعم/لا).
    2. تطبيق "فيزياء الحرف": هل قام التحليل بتفكيك كلمة قرآنية واحدة على الأقل إلى حروفها وشرحها بناءً على معاني الحروف الفيزيائية للطاقة والحركة؟ (يجب أن يكون الرد: نعم/لا).

    التحليل المطلوب مراجعته:
    ---
    {analysis_text}
    ---

    أجب بالتنسيق التالي حصراً:
    التفسير التقليدي: [موجود/غير موجود]
    فيزياء الحرف: [مطبق/غير مطبق]
    النتيجة النهائية: [قبول/رفض]
    السبب: [اذكر السبب باختصار باللغة العربية]
    """
    
    try:
        res = model.generate_content(prompt)
        report = res.text
        passed = "النتيجة النهائية: قبول" in report
        needs_retry = "فيزياء الحرف: غير مطبق" in report or "التفسير التقليدي: موجود" in report
        return passed, report, needs_retry
    except:
        return True, "تجاوز تلقائي بسبب خطأ تقني في الفحص", False

def handle_main_agent_query(agent_q, refs_input, agent_api_key, verses_db):
    verse_refs = []
    if refs_input:
        try:
            for part in refs_input.split(","):
                part = part.strip()
                if ":" in part:
                    s_id, a_range = part.split(":")
                    if "-" in a_range:
                        start, end = map(int, a_range.split("-"))
                        for i in range(start, end + 1): verse_refs.append(f"{s_id}:{i}")
                    else: verse_refs.append(f"{s_id}:{part.split(':')[-1]}")
                elif ":" not in part and part.isdigit(): # fallback for single surah full range? no, stick to format s:a
                    pass
        except: pass

    with st.status("🔍 بناء السياق الشامل...", expanded=True) as status:
        st.write("📝 استخراج الآيات المحورية والسياق...")
        context_package = build_context_package(verse_refs, verses_db, agent_api_key)
        st.write(f"🔗 جمع الآيات المرتبطة: {len(context_package['related_verses'])} آية/آيات")
        st.write(f"💡 المفاهيم المستخلصة: {', '.join(context_package['key_concepts'][:3])}")
        formatted_context = format_context_for_prompt(context_package)
        status.update(label="✅ اكتمل بناء السياق", state="complete", expanded=False)

    with st.expander("📊 تفاصيل السياق المستخدم"):
        st.write(f"**المفاهيم:** {', '.join(context_package['key_concepts'])}")
        if context_package['related_verses']:
            for rv in context_package['related_verses'][:3]:
                st.markdown(f"- [{rv['id']}] {rv['text'][:100]}...")

    attempts = 0
    max_retries = 1
    final_out = ""
    
    while attempts <= max_retries:
        res_box = st.empty()
        out = ""
        try:
            enhanced_prompt = f"السؤال: {agent_q}\n\nالسياق:\n{formatted_context}"
            if attempts > 0:
                enhanced_prompt += "\n\n⚠️ تنبيه للمحلل: التحليل السابق تم رفضه. يرجى التأكد من: \n1. تطبيق فيزياء الحرف بدقة (تفكيك الكلمات لحروف).\n2. الابتعاد التام عن القصص التاريخية والتفاسير التقليدية."
            
            v_texts = [v["text"] for v in context_package["target_verses"]]
            for chunk in ai_analysis_enhanced(agent_api_key, enhanced_prompt, v_texts, verse_refs=verse_refs):
                if chunk.text:
                    out += chunk.text
                    res_box.markdown(f"<div class='result-box'>{out}</div>", unsafe_allow_html=True)
            
            # Step: Doctrine Check
            with st.status("🕵️ جاري فحص جودة التحليل ومطابقته للمنهجية...", expanded=False) as checker_status:
                passed, report, retry_needed = doctrine_checker(agent_api_key, out)
                if passed:
                    checker_status.update(label="✅ تم التحقق والموافقة على التحليل", state="complete")
                    final_out = out
                    break
                else:
                    checker_status.update(label="❌ التحليل لم يطابق المعايير", state="error")
                    st.warning(f"تقرير الفحص: {report}")
                    if attempts < max_retries:
                        st.info("🔄 جاري إعادة المحاولة لتحسين النتائج...")
                        attempts += 1
                        continue
                    else:
                        st.error("⚠️ لم نتمكن من الوصول لنتيجة مثالية بعد عدة محاولات، سيتم عرض المحاولة الأخيرة.")
                        final_out = out
                        break
        except Exception as e:
            st.error(f"⚠️ خطأ: {e}")
            return None, None

    # Continue with benefits extraction from final_out
    benefits = extract_practical_benefits(final_out)
    if any(benefits.values()):
        with st.expander("✨ ملخص الفوائد التطبيقية"):
            cols = st.columns(2)
            category_list = list(benefits.items())
            for i, (cat, items) in enumerate(category_list):
                if items:
                    with cols[i%2]:
                        st.markdown(f"<div class='benefit-card'><h4>{cat.upper()}</h4>{'<br>'.join(['• '+it for it in items[:2]])}</div>", unsafe_allow_html=True)
    return final_out, context_package

# ==========================================
# 6. APP
# ==========================================
@st.cache_data
def get_topic_subject(api_key, verses_text):
    if not api_key or not verses_text: return "موضوع"
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3-pro-preview")
        prompt = f"بناءً على الآيات التالية، اعطني عنواناً موضوعياً دقيقاً ومختصراً جداً (من كلمتين إلى 3 كلمات): \n\n" + "\n".join(verses_text[:2])
        res = model.generate_content(prompt)
        return res.text.strip().replace('*', '').replace('#', '')
    except:
        return "موضوع"

def main():
    model, topics, vectors = load_engine()
    verses = load_quran()
    neo = load_neo4j()

    st.title("🕋 محلل اللسان العربي المبين")

    tab_labels = ["🔍 بحث في الآيات", "🧠 تدبر موضوعي", "🤖 الوكيل الرئيسي (تدبر حر)"]
    if "active_tab_name" not in st.session_state:
        st.session_state.active_tab_name = tab_labels[0]

    # Persistent navigation using radio to prevent jumping
    st.session_state.active_tab_name = st.radio(
        "القائمة السريعة:", 
        tab_labels, 
        index=tab_labels.index(st.session_state.active_tab_name),
        horizontal=True,
        label_visibility="collapsed"
    )

    # Initialize session manager (hybrid: Neo4j first, then local fallback)
    if "session_manager" not in st.session_state:
        try:
            st.session_state.session_manager = SessionManager()
            st.session_state.session_storage_type = "Neo4j"
        except Exception as neo_error:
            # Fallback to local JSON storage
            try:
                st.session_state.session_manager = LocalSessionManager()
                st.session_state.session_storage_type = "Local"
                with st.sidebar:
                    st.warning("⚠️ استخدام التخزين المحلي (Neo4j غير متاح)")
            except Exception as local_error:
                st.error(f"⚠️ خطأ في نظام الحفظ: {local_error}")
                st.session_state.session_manager = None
                st.session_state.session_storage_type = None
    
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    
    if "agent_chat" not in st.session_state:
        st.session_state.agent_chat = []
    if "agent_verses" not in st.session_state:
        st.session_state.agent_verses = []

    # Display content based on selection
    if st.session_state.active_tab_name == "🔍 بحث في الآيات":
        # ---------- TAB 1: AYAH SEARCH ----------
        q1 = st.text_input("ابحث في القرآن (كلمة أو معنى):", key="ayah_q")
        if st.button("بحث الآيات", key="ayah_btn") and q1:
            st.session_state.ayah_results = search_verses(q1, verses, model)
        
        if "ayah_results" in st.session_state:
            if not st.session_state.ayah_results:
                st.warning("لا توجد نتائج منضبطة.")
            for r in st.session_state.ayah_results:
                st.markdown(
                    f"<div class='ayah-box'>{r['text']}<br><small>{format_ref(str(r['surah']) + ':' + str(r['ayah']))} — {r['reason']}</small></div>",
                    unsafe_allow_html=True
                )

    elif st.session_state.active_tab_name == "🧠 تدبر موضوعي":
        # ---------- TAB 2: TOPIC + GRAPH ----------
        graph_engine = QuranGraphSearch(neo) if neo else None
        
        col1, col2 = st.columns([2, 1])
        with col1:
            q2 = st.text_input("سؤال للتدبر:", key="topic_q")
        with col2:
            search_mode = st.radio(
                "وضع البحث:",
                ["بحث دلالي", "بحث بنيوي (Graph)", "بحث هجين"],
                horizontal=True,
                key="mode_radio"
            )
            
        api_key = st.text_input("Google API Key", type="password", value=os.getenv("GOOGLE_API_KEY", ""), key="api_key_input")

        if st.button("تدبر", key="tadabbur_btn") and q2:
            st.session_state.active_tadabbur_q = q2
            if search_mode == "بحث بنيوي (Graph)" and graph_engine:
                st.session_state.tadabbur_results = graph_engine.search_by_concept(q2)
                st.session_state.tadabbur_type = "graph"
            elif search_mode == "بحث هجين" and graph_engine:
                st.session_state.tadabbur_results = hybrid_search(q2, model, vectors, topics, graph_engine)
                st.session_state.tadabbur_type = "hybrid"
            else:
                st.session_state.tadabbur_results = semantic_search(model, topics, vectors, q2)
                st.session_state.tadabbur_type = "semantic"

        if "tadabbur_results" in st.session_state:
            results = st.session_state.tadabbur_results
            t_type = st.session_state.tadabbur_type
            active_q = st.session_state.active_tadabbur_q

            if not results:
                st.warning("لا توجد نتائج.")
            
            for i, r in enumerate(results):
                # 1. Logic for Graph results
                if t_type == "graph" or (t_type == "hybrid" and r.get('source') == 'graph'):
                    with st.expander(f"📌 {r.get('concept', 'مفهوم')} — {format_ref(r.get('ref', ''))}"):
                        st.markdown(f"<div class='ayah-box'>{r['text']}</div>", unsafe_allow_html=True)
                        st.info(f"🔁 القانون: {r.get('law') or 'غير مصنف'}")
                        
                        if api_key:
                            if st.button("🤖 استنطاق الوكيل الذكي", key=f"ai_btn_g_{i}"):
                                box = st.empty()
                                out = ""
                                try:
                                    for chunk in ai_analysis(api_key, active_q, [r['text']], concept=r.get('concept'), law=r.get('law')):
                                        if chunk.text:
                                            out += chunk.text
                                            box.markdown(out)
                                except Exception as e:
                                    st.error(f"خطأ: {e}")

                # 2. Logic for Semantic results
                else:
                    score_label = f" (تشابه {int(r['score']*100)}%)" if 'score' in r else ""
                    source_label = "🌐 دلالي" if t_type == "hybrid" else "موضوع"
                    tid = r.get('id', r.get('topic_id'))
                    
                    refs = fetch_ayahs(neo, tid) if neo else next((t['ayahs'] for t in topics if t['id'] == tid), [])
                    topic_texts = []
                    for ref in refs:
                        v = next((x for x in verses if x["id"] == ref), None)
                        if v: topic_texts.append(v["text"])
                    
                    # Generate dynamic subject
                    subject = get_topic_subject(api_key, topic_texts) if api_key else tid
                    
                    with st.expander(f"{source_label} | {subject}{score_label}"):
                        for ref, text in zip(refs, topic_texts):
                            st.markdown(f"<div class='ayah-box'>{text}<br><small>{format_ref(ref)}</small></div>", unsafe_allow_html=True)

                        if api_key:
                            if st.button("🤖 استنطاق الوكيل الذكي", key=f"ai_btn_s_{i}"):
                                box = st.empty()
                                out = ""
                                try:
                                    for chunk in ai_analysis(api_key, active_q, topic_texts):
                                        if chunk.text:
                                            out += chunk.text
                                            box.markdown(out)
                                except Exception as e:
                                    st.error(f"خطأ: {e}")

                            try:
                                net = build_network(neo, tid, topic_label=subject)
                                net.save_graph("graph.html")
                                components.html(open("graph.html", encoding="utf-8").read(), height=600)
                            except:
                                pass

    elif st.session_state.active_tab_name == "🤖 الوكيل الرئيسي (تدبر حر)":
        # ---------- TAB 3: MAIN AGENT (ENHANCED) ----------
        st.subheader("🤖 استنطاق الوكيل الرئيسي للسان العربي المبين")
        st.info("💡 هذا الوكيل يبني سياقاً شاملاً (قبل/بعد الآيات + آيات مرتبطة) لتقديم أفضل تدبر عملي.")
        
        # Session Management Sidebar
        if st.session_state.session_manager:
            with st.sidebar:
                st.markdown("### 💾 إدارة الجلسات")
                
                # Show storage type
                if hasattr(st.session_state, 'session_storage_type'):
                    if st.session_state.session_storage_type == "Neo4j":
                        st.success("🌐 متصل بـ Neo4j")
                    elif st.session_state.session_storage_type == "Local":
                        st.info("📁 التخزين المحلي (JSON)")
                
                # Current session info
                if st.session_state.current_session_id:
                    st.success(f"📂 الجلسة الحالية نشطة")
                    
                    # Rename session
                    new_name = st.text_input("تسمية الجلسة:", key="rename_session_input", placeholder="أدخل اسماً مخصصاً")
                    if st.button("✏️ حفظ الاسم", key="rename_btn"):
                        if new_name:
                            try:
                                st.session_state.session_manager.rename_session(
                                    st.session_state.current_session_id, 
                                    new_name
                                )
                                st.success("✅ تم تحديث الاسم")
                                st.rerun()
                            except Exception as e:
                                st.error(f"خطأ: {e}")
                    
                    # Delete current session
                    if st.button("🗑️ حذف الجلسة الحالية", key="delete_current_btn", type="secondary"):
                        try:
                            st.session_state.session_manager.delete_session(st.session_state.current_session_id)
                            st.session_state.current_session_id = None
                            st.session_state.agent_chat = []
                            st.session_state.agent_context = None
                            st.success("✅ تم حذف الجلسة")
                            st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")
                
                st.markdown("---")
                
                # Load previous sessions
                st.markdown("### 📂 الجلسات المحفوظة")
                
                # Search bar
                search_query = st.text_input("🔍 بحث في الجلسات:", key="session_search", placeholder="ابحث...")
                
                try:
                    if search_query:
                        sessions = st.session_state.session_manager.search_sessions(search_query, limit=10)
                    else:
                        sessions = st.session_state.session_manager.list_sessions(limit=10)
                    
                    if sessions:
                        for sess in sessions:
                            # Format display
                            display_name = sess['user_name'] or sess['session_id'][:8]
                            turn_info = f"({sess['turn_count']} رسالة)"
                            
                            col_a, col_b = st.columns([3, 1])
                            with col_a:
                                if st.button(f"📖 {display_name}", key=f"load_{sess['session_id']}", help=sess['initial_question']):
                                    # Load session
                                    try:
                                        session_data = st.session_state.session_manager.load_session(sess['session_id'])
                                        st.session_state.current_session_id = sess['session_id']
                                        st.session_state.agent_chat = session_data['conversation']
                                        st.session_state.agent_context = session_data['context_package']
                                        st.success(f"✅ تم تحميل: {display_name}")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"خطأ في التحميل: {e}")
                            with col_b:
                                st.caption(turn_info)
                    else:
                        st.info("لا توجد جلسات محفوظة")
                except Exception as e:
                    st.error(f"خطأ في جلب القائمة: {e}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            refs_input = st.text_input("مراجع الآيات:", placeholder="50:15-16, 30:27")
            agent_api_key = st.text_input("Google API Key", type="password", value=os.getenv("GOOGLE_API_KEY", ""), key="agent_api_key")
        with col2:
            agent_q = st.text_area("سؤالك للوكيل:", placeholder="مثال: ما العلاقة بين الخلق الأول والبعث؟ وما الفوائد التطبيقية؟")

        if not st.session_state.agent_chat:
            if st.button("🚀 استنطاق الوكيل الرئيسي", key="main_agent_btn") and agent_q:
                if not agent_api_key: st.error("⚠️ يرجى إدخال مفتاح API أولاً.")
                else:
                    response, context_pkg = handle_main_agent_query(agent_q, refs_input, agent_api_key, verses)
                    if response:
                        # Create session if doesn't exist
                        if st.session_state.session_manager and not st.session_state.current_session_id:
                            try:
                                st.session_state.current_session_id = st.session_state.session_manager.create_session(
                                    agent_q, refs_input or "عام"
                                )
                            except Exception as e:
                                st.warning(f"لم يتم حفظ الجلسة: {e}")
                        
                        # Add to chat
                        st.session_state.agent_chat.append({"role": "user", "content": agent_q})
                        st.session_state.agent_chat.append({"role": "assistant", "content": response})
                        st.session_state.agent_context = context_pkg
                        
                        # Save to Neo4j
                        if st.session_state.session_manager and st.session_state.current_session_id:
                            try:
                                st.session_state.session_manager.save_turn(
                                    st.session_state.current_session_id,
                                    "user",
                                    agent_q
                                )
                                st.session_state.session_manager.save_turn(
                                    st.session_state.current_session_id,
                                    "assistant",
                                    response,
                                    context_package=context_pkg
                                )
                            except Exception as e:
                                st.warning(f"لم يتم حفظ الرسالة: {e}")
                        
                        st.rerun()
        else:
            if st.button("🆕 بدء تدبر جديد", key="new_session_btn"):
                st.session_state.agent_chat = []
                st.session_state.agent_verses = []
                st.session_state.agent_context = None
                st.session_state.current_session_id = None
                st.rerun()

        # Display Chat History & Follow-up
        if st.session_state.agent_chat:
            st.markdown("---")
            for msg in st.session_state.agent_chat:
                role_label = "أنت" if msg["role"] == "user" else "الوكيل الرئيسي"
                if msg["role"] == "assistant":
                    st.markdown(f"<div class='result-box'><strong>{role_label}:</strong><br>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='text-align: right; background: #e3f2fd; padding:15px; border-radius:10px; margin-top:10px; margin-bottom:10px; color:black; border-right:5px solid #2196f3;'><strong>{role_label}:</strong> {msg['content']}</div>", unsafe_allow_html=True)
            
            # Context Summary Expandable
            if "agent_context" in st.session_state and st.session_state.agent_context:
                with st.sidebar:
                    st.markdown("### 📊 سياق التدبر الحالي")
                    st.write(f"**آيات أساسية:** {len(st.session_state.agent_context['target_verses'])}")
                    st.write(f"**مفاهيم:** {', '.join(st.session_state.agent_context['key_concepts'])}")

            follow_up = st.chat_input("اسأل سؤال متابعة...")
            if follow_up:
                st.session_state.agent_chat.append({"role": "user", "content": follow_up})
                
                # Save user turn to Neo4j
                if st.session_state.session_manager and st.session_state.current_session_id:
                    try:
                        st.session_state.session_manager.save_turn(
                            st.session_state.current_session_id,
                            "user",
                            follow_up
                        )
                    except Exception as e:
                        st.warning(f"لم يتم حفظ السؤال: {e}")
                st.rerun()

        if st.session_state.agent_chat and st.session_state.agent_chat[-1]["role"] == "user" and len(st.session_state.agent_chat) > 1:
            user_msg = st.session_state.agent_chat[-1]["content"]
            api_history = st.session_state.agent_chat[:-1]
            ctx = st.session_state.agent_context
            with st.spinner("🤔 الوكيل يفكر..."):
                out_content = ""
                try:
                    v_texts = [v["text"] for v in ctx["target_verses"]] if ctx else []
                    v_refs = [v["id"] for v in ctx["target_verses"]] if ctx else []
                    for chunk in ai_analysis_enhanced(agent_api_key, user_msg, v_texts, verse_refs=v_refs, chat_history=api_history):
                        if chunk.text: out_content += chunk.text
                    st.session_state.agent_chat.append({"role": "assistant", "content": out_content})
                    
                    # Save assistant turn to Neo4j
                    if st.session_state.session_manager and st.session_state.current_session_id:
                        try:
                            st.session_state.session_manager.save_turn(
                                st.session_state.current_session_id,
                                "assistant",
                                out_content,
                                context_package=ctx
                            )
                        except Exception as e:
                            st.warning(f"لم يتم حفظ الإجابة: {e}")
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")

if __name__ == "__main__":
    main()
