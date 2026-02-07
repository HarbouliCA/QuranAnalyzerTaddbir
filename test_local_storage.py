"""
Test Local Session Manager
"""
from local_session_manager import LocalSessionManager

print("🧪 Testing Local Session Manager...")

# Initialize
sm = LocalSessionManager()
print("✅ Initialized local storage")

# Create session
sid = sm.create_session("ما العلاقة بين الخلق الأول والبعث؟", "50:15-16")
print(f"✅ Created session: {sid}")

# Save turns
sm.save_turn(sid, "user", "السؤال الأول")
sm.save_turn(sid, "assistant", "الإجابة الأولى", context_package={"test": "data"})
print("✅ Saved 2 turns")

# Load session
data = sm.load_session(sid)
print(f"✅ Loaded session: {data['metadata']['user_name']}")
print(f"   Turns: {len(data['conversation'])}")

# List sessions
sessions = sm.list_sessions(limit=5)
print(f"✅ Listed {len(sessions)} sessions")

# Rename
sm.rename_session(sid, "اختبار محلي")
print("✅ Renamed session")

# Search
results = sm.search_sessions("اختبار")
print(f"✅ Search found {len(results)} results")

# Clean up
sm.delete_session(sid)
print("✅ Deleted test session")

print("\n🎉 Local storage works perfectly!")
print("📁 Session files are stored in: ./conversations/")
