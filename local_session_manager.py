"""
Local Session Manager - JSON fallback when Neo4j is unavailable
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class LocalSessionManager:
    """Manage conversation sessions using local JSON files"""
    
    def __init__(self, storage_dir="./conversations"):
        """Initialize local storage"""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self._load_index()
    
    def _load_index(self):
        """Load session index"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {"sessions": []}
    
    def _save_index(self):
        """Save session index"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def create_session(self, user_question: str, verse_refs: str) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        session_data = {
            "session_id": session_id,
            "created_at": timestamp,
            "last_updated": timestamp,
            "user_name": f"تدبر {verse_refs}",
            "verse_refs": verse_refs,
            "initial_question": user_question,
            "conversation": [],
            "context_package": None
        }
        
        # Save session file
        session_file = self.storage_dir / f"{session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # Update index
        self.index["sessions"].append({
            "session_id": session_id,
            "user_name": session_data["user_name"],
            "verse_refs": verse_refs,
            "initial_question": user_question,
            "created_at": timestamp,
            "last_updated": timestamp,
            "turn_count": 0
        })
        self._save_index()
        
        return session_id
    
    def save_turn(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        context_package: Optional[Dict] = None
    ):
        """Save a conversation turn"""
        session_file = self.storage_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise ValueError(f"Session {session_id} not found")
        
        # Load session
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        # Add turn
        timestamp = datetime.now().isoformat()
        turn = {
            "role": role,
            "content": content,
            "timestamp": timestamp
        }
        session_data["conversation"].append(turn)
        session_data["last_updated"] = timestamp
        
        # Save context package if provided (for assistant messages)
        if context_package and role == "assistant":
            session_data["context_package"] = context_package
        
        # Save session
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # Update index
        for sess in self.index["sessions"]:
            if sess["session_id"] == session_id:
                sess["last_updated"] = timestamp
                sess["turn_count"] = len(session_data["conversation"])
                break
        self._save_index()
    
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load a complete session"""
        session_file = self.storage_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise ValueError(f"Session {session_id} not found")
        
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        return {
            "session_id": session_id,
            "metadata": {
                "user_name": session_data["user_name"],
                "verse_refs": session_data["verse_refs"],
                "initial_question": session_data["initial_question"],
                "created_at": session_data["created_at"],
                "last_updated": session_data["last_updated"]
            },
            "conversation": session_data["conversation"],
            "context_package": session_data["context_package"]
        }
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List all saved sessions"""
        sessions = sorted(
            self.index["sessions"],
            key=lambda x: x["last_updated"],
            reverse=True
        )
        return sessions[offset:offset + limit]
    
    def rename_session(self, session_id: str, new_name: str):
        """Rename a session"""
        session_file = self.storage_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise ValueError(f"Session {session_id} not found")
        
        # Update session file
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        session_data["user_name"] = new_name
        session_data["last_updated"] = datetime.now().isoformat()
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        # Update index
        for sess in self.index["sessions"]:
            if sess["session_id"] == session_id:
                sess["user_name"] = new_name
                sess["last_updated"] = session_data["last_updated"]
                break
        self._save_index()
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        session_file = self.storage_dir / f"{session_id}.json"
        
        if session_file.exists():
            session_file.unlink()
        
        # Remove from index
        self.index["sessions"] = [
            s for s in self.index["sessions"]
            if s["session_id"] != session_id
        ]
        self._save_index()
    
    def search_sessions(self, query: str, limit: int = 20) -> List[Dict]:
        """Search sessions by content"""
        results = []
        query_lower = query.lower()
        
        for sess in self.index["sessions"]:
            if (query_lower in sess["user_name"].lower() or
                query_lower in sess["initial_question"].lower() or
                query_lower in sess["verse_refs"].lower()):
                results.append(sess)
        
        # Sort by last_updated
        results.sort(key=lambda x: x["last_updated"], reverse=True)
        return results[:limit]
    
    def close(self):
        """No cleanup needed for local storage"""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
