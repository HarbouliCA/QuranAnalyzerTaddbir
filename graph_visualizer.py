import networkx as nx
from pyvis.network import Network
import streamlit as st
import streamlit.components.v1 as components
import re

def generate_root_network(quran_data, target_root):
    """
    يبني شبكة تفاعلية تربط الجذر بجميع الكلمات المشتقة منه في القرآن
    """
    # 1. إنشاء الجراف (الشبكة)
    G = nx.Graph()
    
    # تنظيف الجذر
    target_root = re.sub(r'[أإآ]', 'ا', target_root.strip())
    
    # التحقق من طول الجذر
    if len(target_root) != 3:
        # يمكننا هنا إرجاع كود HTML بسيط يعرض رسالة خطأ، أو التعامل معه بمرونة
        # للتبسيط، سنأخذ أول 3 حروف فقط إذا كان أطول، أو نرفض إذا أقصر
        if len(target_root) > 3:
            target_root = target_root[:3]
        else:
            return "<div>⚠️ يرجى إدخال جذر ثلاثي صحيح (3 حروف).</div>"

    l1, l2, l3 = list(target_root)
    
    # النود المركزية (الجذر)
    G.add_node(target_root, label=f"الجذر: {target_root}", color="#ff4b4b", size=40, title="أصل المادة")
    
    # نمط البحث
    pattern = fr"\w*{l1}\w*{l2}\w*{l3}\w*"
    
    # 2. البحث عن العلاقات
    word_counts = {}
    
    for ayah in quran_data:
        # البحث عن الكلمات في الآية
        words = ayah['normalized'].split()
        original_words = ayah['uthmani'].split()
        
        for i, word in enumerate(words):
            if re.search(pattern, word):
                # الكلمة الأصلية (بالرسم العثماني)
                matched_word = original_words[i]
                
                # تجميع التكرارات (لجعل حجم النود أكبر حسب التكرار)
                if matched_word in word_counts:
                    word_counts[matched_word]['count'] += 1
                    word_counts[matched_word]['ayahs'].append(ayah['ref'])
                else:
                    word_counts[matched_word] = {
                        'count': 1,
                        'ayahs': [ayah['ref']]
                    }

    # 3. إضافة نودات الكلمات وربطها بالجذر
    for word, data in word_counts.items():
        # حجم النود يعتمد على تكرارها
        size = 15 + (data['count'] * 2) 
        title_tooltip = f"تكررت {data['count']} مرة.\nأماكن: {', '.join(data['ayahs'][:3])}..."
        
        G.add_node(word, label=word, title=title_tooltip, color="#1f77b4", size=size)
        G.add_edge(target_root, word, color="#dddddd")

    # 4. إعدادات العرض (PyVis)
    net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
    net.from_nx(G)
    
    # تحسين الفيزياء (حركة النودات)
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": { "enabled": true }
      }
    }
    """)
    
    # حفظ وتوليد HTML
    try:
        path = "/tmp"
        net.save_graph(f"{path}/network.html")
        HtmlFile = open(f"{path}/network.html", 'r', encoding='utf-8')
        return HtmlFile.read()
    except:
        # في بيئة ويندوز المحلية
        net.save_graph("network.html")
        HtmlFile = open("network.html", 'r', encoding='utf-8')
        return HtmlFile.read()