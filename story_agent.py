import google.generativeai as genai
from quran_utils import search_prophet_story_tool

# --- عقل المهندس القصصي ---
STORY_SYSTEM_PROMPT = """
### الهوية: أنت "مهندس السياق القصصي" في القرآن.
مهمتك: بناء "سياق زمني وموضوعي" من الآيات المبعثرة لنبي معين، لمساعدة المحلل اللغوي في فهم الآية المطلوبة.

### البروتوكول (صارم جداً):
1. **القرآن فقط:** لا تستعن بالإسرائيليات أو كتب التاريخ. رتب الأحداث بناءً على المنطق القرآني.
2. **الترتيب الزمني:** اقرأ الآيات المرفقة ورتب المشهد: هل هذا في البداية (الضعف)؟ أم في الرسالة؟ أم في المواجهة؟ أم في التمكين؟
3. **الربط:** حدد أين تقع "الآية التي سأل عنها المستخدم" ضمن هذا الخط الزمني؟

### المخرجات:
اكتب فقرة مركزة جداً تبدأ بـ: "سياق هذه الآية يقع في مرحلة..."
"""

def run_story_agent(model, prophet_name, user_question):
    """
    دالة تشغيل الوكيل القصصي
    """
    # 1. استخدام الأداة لجمع الآيات
    all_verses = search_prophet_story_tool(prophet_name)
    
    if not all_verses:
        return None
        
    # 2. التفكير والترتيب
    full_prompt = f"""
    {STORY_SYSTEM_PROMPT}
    
    ---
    الآيات التي ذكر فيها النبي ({prophet_name}) في القرآن:
    {all_verses}
    ---
    
    سؤال المستخدم أو الآية المطلوبة: {user_question}
    
    المطلوب: حدد السياق الزمني والموضوعي لهذه الآية تحديداً.
    """
    
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"خطأ في تحليل القصة: {e}"