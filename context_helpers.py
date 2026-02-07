import requests
import json

# ==========================================
# CONTEXT EXTRACTION HELPERS
# ==========================================

def get_surrounding_verses(verse_ref, verses, before=2, after=2):
    """
    Get verses before and after a specific verse for context
    
    Args:
        verse_ref: str like "50:15"
        verses: list of verse dicts
        before: number of verses before
        after: number of verses after
    
    Returns:
        dict with before, target, after verses
    """
    try:
        surah, ayah = map(int, verse_ref.split(":"))
        
        context = {
            "before": [],
            "target": None,
            "after": [],
            "surah_name": get_surah_name(surah)
        }
        
        # Get verses from same surah
        surah_verses = [v for v in verses if v["surah"] == surah]
        
        for v in surah_verses:
            if v["ayah"] == ayah:
                context["target"] = v
            elif v["ayah"] < ayah and v["ayah"] >= ayah - before:
                context["before"].append(v)
            elif v["ayah"] > ayah and v["ayah"] <= ayah + after:
                context["after"].append(v)
        
        # Sort before/after
        context["before"].sort(key=lambda x: x["ayah"])
        context["after"].sort(key=lambda x: x["ayah"])
        
        return context
        
    except Exception as e:
        return None

def get_surah_name(surah_id):
    """Get surah name from ID"""
    surah_names = [
        "الفاتحة", "البقرة", "آل عمران", "النساء", "المائدة", "الأنعام", 
        "الأعراف", "الأنفال", "التوبة", "يونس", "هود", "يوسف", "الرعد", 
        "إبراهيم", "الحجر", "النحل", "الإسراء", "الكهف", "مريم", "طه",
        # ... rest of surahs
    ]
    try:
        return surah_names[surah_id - 1]
    except:
        return f"سورة {surah_id}"

def find_related_verses_by_root(keyword, verses, max_results=5):
    """
    Find verses containing the same root word
    Simple implementation - could be enhanced with proper Arabic morphology
    """
    from search.search_engine import normalize_arabic
    
    normalized_keyword = normalize_arabic(keyword)
    related = []
    
    for v in verses:
        normalized_text = normalize_arabic(v["text"])
        if normalized_keyword in normalized_text:
            related.append(v)
            if len(related) >= max_results:
                break
    
    return related

def extract_key_concepts(text, api_key=None):
    """
    Extract key concepts from verse text using AI
    Falls back to simple keyword extraction if no API key
    """
    if not api_key:
        # Simple fallback: extract words longer than 3 chars
        words = text.split()
        return [w.strip("،؛.") for w in words if len(w) > 3][:3]
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        
        prompt = f"""من الآية التالية، استخرج المفاهيم المحورية (كلمة أو كلمتين فقط):

الآية: {text}

المطلوب: 3 مفاهيم رئيسية فقط، مفصولة بفواصل (مثال: الصبر, الإيمان, الجزاء)"""
        
        response = model.generate_content(prompt)
        concepts = [c.strip() for c in response.text.split(",")]
        return concepts[:3]
        
    except:
        # Fallback if API fails
        words = text.split()
        return [w.strip("،؛.") for w in words if len(w) > 3][:3]

def build_context_package(verse_refs, verses, api_key=None):
    """
    Build a comprehensive context package for AI analysis
    
    Returns:
        dict with:
        - target_verses: the main verses
        - surrounding_context: verses before/after each
        - key_concepts: extracted concepts
        - related_verses: thematically related verses
    """
    package = {
        "target_verses": [],
        "surrounding_context": {},
        "key_concepts": [],
        "related_verses": []
    }
    
    # Process each reference
    for ref in verse_refs:
        # Get target verse
        target = next((v for v in verses if v["id"] == ref), None)
        if not target:
            continue
            
        package["target_verses"].append(target)
        
        # Get surrounding context
        context = get_surrounding_verses(ref, verses, before=2, after=2)
        if context:
            package["surrounding_context"][ref] = context
        
        # Extract key concepts
        concepts = extract_key_concepts(target["text"], api_key)
        package["key_concepts"].extend(concepts)
    
    # Remove duplicate concepts
    package["key_concepts"] = list(set(package["key_concepts"]))
    
    # Find related verses based on key concepts
    for concept in package["key_concepts"][:2]:  # Limit to top 2 concepts
        related = find_related_verses_by_root(concept, verses, max_results=3)
        package["related_verses"].extend(related)
    
    # Remove duplicates
    seen = set()
    unique_related = []
    for v in package["related_verses"]:
        if v["id"] not in seen and v["id"] not in verse_refs:
            seen.add(v["id"])
            unique_related.append(v)
    package["related_verses"] = unique_related[:5]
    
    return package

def format_context_for_prompt(context_package):
    """
    Format the context package into a readable string for AI prompt
    """
    output = []
    
    # Main verses
    output.append("### الآيات الأساسية للتحليل:")
    for i, v in enumerate(context_package["target_verses"], 1):
        output.append(f"\n**[{v['id']}]** {v['text']}")
    
    # Surrounding context
    if context_package["surrounding_context"]:
        output.append("\n\n### السياق المباشر:")
        for ref, ctx in context_package["surrounding_context"].items():
            output.append(f"\n**سورة {ctx['surah_name']} - حول الآية [{ref}]:**")
            
            if ctx["before"]:
                output.append("\n**ما قبلها:**")
                for v in ctx["before"]:
                    output.append(f"[{v['id']}] {v['text']}")
            
            if ctx["target"]:
                output.append(f"\n**الآية المحورية:** [{ctx['target']['id']}] {ctx['target']['text']}")
            
            if ctx["after"]:
                output.append("\n**ما بعدها:**")
                for v in ctx["after"]:
                    output.append(f"[{v['id']}] {v['text']}")
    
    # Related verses
    if context_package["related_verses"]:
        output.append("\n\n### آيات مرتبطة موضوعياً:")
        for v in context_package["related_verses"]:
            output.append(f"\n[{v['id']}] {v['text']}")
    
    # Key concepts
    if context_package["key_concepts"]:
        output.append(f"\n\n### المفاهيم المحورية المستخلصة:")
        output.append(", ".join(context_package["key_concepts"]))
    
    return "\n".join(output)

# ==========================================
# BENEFIT EXTRACTION
# ==========================================

def extract_practical_benefits(analysis_text):
    """
    Parse AI analysis to extract practical benefits
    This can be used to create a summary or highlights
    """
    benefits = {
        "عقدي": [],
        "نفسي": [],
        "سلوكي": [],
        "معاصر": []
    }
    
    # Simple keyword-based extraction
    lines = analysis_text.split("\n")
    current_category = None
    
    for line in lines:
        if "العقدي" in line or "الفكري" in line:
            current_category = "عقدي"
        elif "النفسي" in line or "الوجداني" in line:
            current_category = "نفسي"
        elif "السلوكي" in line or "العملي" in line:
            current_category = "سلوكي"
        elif "المعاصر" in line or "التطبيق" in line:
            current_category = "معاصر"
        elif current_category and line.strip() and not line.startswith("#"):
            benefits[current_category].append(line.strip())
    
    return benefits

# ==========================================
# USAGE EXAMPLE
# ==========================================

"""
# Example usage in your app:

verse_refs = ["50:15", "50:16"]
verses = load_quran()  # Your existing function
api_key = os.getenv("GOOGLE_API_KEY")

# Build comprehensive context
context_package = build_context_package(verse_refs, verses, api_key)

# Format for AI prompt
formatted_context = format_context_for_prompt(context_package)

# Use in AI analysis
response = ai_analysis_enhanced(
    api_key=api_key,
    question="ما المقصود بالخلق الأول؟",
    verses=[v["text"] for v in context_package["target_verses"]],
    verse_refs=verse_refs,
    context_str=formatted_context  # Add this parameter
)
"""