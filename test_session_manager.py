"""
Test Session Manager functionality
"""

from session_manager import SessionManager
import os
from dotenv import load_dotenv

load_dotenv()

def test_session_manager():
    """Test basic session operations"""
    print("🧪 Testing Session Manager...")
    
    # Initialize
    sm = SessionManager()
    print("✅ Connected to Neo4j")
    
    # Create session
    session_id = sm.create_session(
        "ما العلاقة بين الخلق الأول والبعث؟",
        "50:15-16"
    )
    print(f"✅ Created session: {session_id}")
    
    # Save turns
    sm.save_turn(session_id, "user", "السؤال الأول")
    sm.save_turn(session_id, "assistant", "الإجابة الأولى", context_package={"test": "data"})
    print("✅ Saved 2 turns")
    
    # Load session
    loaded = sm.load_session(session_id)
    print(f"✅ Loaded session: {loaded['metadata']['user_name']}")
    print(f"   Turns: {len(loaded['conversation'])}")
    
    # List sessions
    sessions = sm.list_sessions(limit=5)
    print(f"✅ Listed {len(sessions)} sessions")
    
    # Rename
    sm.rename_session(session_id, "اختبار تجريبي")
    print("✅ Renamed session")
    
    # Search
    results = sm.search_sessions("اختبار")
    print(f"✅ Search found {len(results)} results")
    
    # Clean up
    sm.delete_session(session_id)
    print("✅ Deleted test session")
    
    sm.close()
    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    test_session_manager()
