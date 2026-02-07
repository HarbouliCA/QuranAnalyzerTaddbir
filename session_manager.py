"""
Session Manager for Quran Analyzer
Handles conversation persistence using Neo4j graph database
"""

from neo4j import GraphDatabase
from datetime import datetime
import uuid
import json
import os
from typing import Optional, List, Dict, Any


class SessionManager:
    """Manage conversation sessions in Neo4j"""
    
    def __init__(self, uri=None, user=None, password=None):
        """Initialize Neo4j connection"""
        self.uri = uri or os.getenv("NEO4J_URI")
        self.user = user or os.getenv("NEO4J_USER")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        
        if not all([self.uri, self.user, self.password]):
            raise ValueError("Neo4j credentials not provided")
        
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                connection_timeout=10
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            self._create_indexes()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {str(e)}")
    
    def _create_indexes(self):
        """Create necessary indexes and constraints"""
        with self.driver.session() as session:
            # Unique constraint on session_id
            session.run("""
                CREATE CONSTRAINT session_id_unique IF NOT EXISTS
                FOR (s:Session) REQUIRE s.session_id IS UNIQUE
            """)
            # Index on created_at for sorting
            session.run("""
                CREATE INDEX session_created_at IF NOT EXISTS
                FOR (s:Session) ON (s.created_at)
            """)
    
    def create_session(self, user_question: str, verse_refs: str) -> str:
        """
        Create a new conversation session
        
        Args:
            user_question: Initial question from user
            verse_refs: Verse references (e.g., "50:15-16")
        
        Returns:
            session_id: UUID of created session
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        with self.driver.session() as session:
            session.run("""
                CREATE (s:Session {
                    session_id: $session_id,
                    created_at: $created_at,
                    last_updated: $last_updated,
                    user_name: $user_name,
                    verse_refs: $verse_refs,
                    initial_question: $initial_question
                })
            """, 
                session_id=session_id,
                created_at=timestamp,
                last_updated=timestamp,
                user_name=f"تدبر {verse_refs}",
                verse_refs=verse_refs,
                initial_question=user_question
            )
        
        return session_id
    
    def save_turn(
        self, 
        session_id: str, 
        role: str, 
        content: str, 
        context_package: Optional[Dict] = None
    ):
        """
        Save a conversation turn
        
        Args:
            session_id: Session UUID
            role: "user" or "assistant"
            content: Message content
            context_package: Optional context data (for assistant messages)
        """
        timestamp = datetime.now().isoformat()
        turn_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            # Create turn node
            session.run("""
                MATCH (s:Session {session_id: $session_id})
                CREATE (t:Turn {
                    turn_id: $turn_id,
                    role: $role,
                    content: $content,
                    timestamp: $timestamp,
                    context_package: $context_package
                })
                CREATE (s)-[:HAS_TURN]->(t)
                SET s.last_updated = $timestamp
            """,
                session_id=session_id,
                turn_id=turn_id,
                role=role,
                content=content,
                timestamp=timestamp,
                context_package=json.dumps(context_package) if context_package else None
            )
    
    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Load a complete session with all turns
        
        Args:
            session_id: Session UUID
        
        Returns:
            Dictionary with chat_history, context_package, metadata
        """
        with self.driver.session() as session:
            # Get session metadata
            result = session.run("""
                MATCH (s:Session {session_id: $session_id})
                RETURN s.user_name as user_name,
                       s.verse_refs as verse_refs,
                       s.initial_question as initial_question,
                       s.created_at as created_at,
                       s.last_updated as last_updated
            """, session_id=session_id)
            
            record = result.single()
            if not record:
                raise ValueError(f"Session {session_id} not found")
            
            metadata = {
                "user_name": record["user_name"],
                "verse_refs": record["verse_refs"],
                "initial_question": record["initial_question"],
                "created_at": record["created_at"],
                "last_updated": record["last_updated"]
            }
            
            # Get all turns in order
            result = session.run("""
                MATCH (s:Session {session_id: $session_id})-[:HAS_TURN]->(t:Turn)
                RETURN t.role as role,
                       t.content as content,
                       t.timestamp as timestamp,
                       t.context_package as context_package
                ORDER BY t.timestamp
            """, session_id=session_id)
            
            conversation = []
            last_context = None
            
            for record in result:
                conversation.append({
                    "role": record["role"],
                    "content": record["content"],
                    "timestamp": record["timestamp"]
                })
                
                # Keep track of last context package (for assistant messages)
                if record["context_package"]:
                    last_context = json.loads(record["context_package"])
            
            return {
                "session_id": session_id,
                "metadata": metadata,
                "conversation": conversation,
                "context_package": last_context
            }
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        List all saved sessions with metadata
        
        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip (for pagination)
        
        Returns:
            List of session summaries
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Session)
                OPTIONAL MATCH (s)-[:HAS_TURN]->(t:Turn)
                WITH s, count(t) as turn_count
                RETURN s.session_id as session_id,
                       s.user_name as user_name,
                       s.verse_refs as verse_refs,
                       s.initial_question as initial_question,
                       s.created_at as created_at,
                       s.last_updated as last_updated,
                       turn_count
                ORDER BY s.last_updated DESC
                SKIP $offset
                LIMIT $limit
            """, limit=limit, offset=offset)
            
            sessions = []
            for record in result:
                sessions.append({
                    "session_id": record["session_id"],
                    "user_name": record["user_name"],
                    "verse_refs": record["verse_refs"],
                    "initial_question": record["initial_question"],
                    "created_at": record["created_at"],
                    "last_updated": record["last_updated"],
                    "turn_count": record["turn_count"]
                })
            
            return sessions
    
    def rename_session(self, session_id: str, new_name: str):
        """
        Rename a session
        
        Args:
            session_id: Session UUID
            new_name: New display name
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (s:Session {session_id: $session_id})
                SET s.user_name = $new_name,
                    s.last_updated = $timestamp
            """, 
                session_id=session_id, 
                new_name=new_name,
                timestamp=datetime.now().isoformat()
            )
    
    def delete_session(self, session_id: str):
        """
        Delete a session and all its turns
        
        Args:
            session_id: Session UUID
        """
        with self.driver.session() as session:
            session.run("""
                MATCH (s:Session {session_id: $session_id})
                OPTIONAL MATCH (s)-[:HAS_TURN]->(t:Turn)
                DETACH DELETE s, t
            """, session_id=session_id)
    
    def search_sessions(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search sessions by content
        
        Args:
            query: Search term
            limit: Maximum results
        
        Returns:
            List of matching sessions
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Session)
                WHERE s.user_name CONTAINS $query 
                   OR s.initial_question CONTAINS $query
                   OR s.verse_refs CONTAINS $query
                OPTIONAL MATCH (s)-[:HAS_TURN]->(t:Turn)
                WITH s, count(t) as turn_count
                RETURN s.session_id as session_id,
                       s.user_name as user_name,
                       s.verse_refs as verse_refs,
                       s.initial_question as initial_question,
                       s.created_at as created_at,
                       s.last_updated as last_updated,
                       turn_count
                ORDER BY s.last_updated DESC
                LIMIT $limit
            """, query=query, limit=limit)
            
            sessions = []
            for record in result:
                sessions.append({
                    "session_id": record["session_id"],
                    "user_name": record["user_name"],
                    "verse_refs": record["verse_refs"],
                    "initial_question": record["initial_question"],
                    "created_at": record["created_at"],
                    "last_updated": record["last_updated"],
                    "turn_count": record["turn_count"]
                })
            
            return sessions
    
    def close(self):
        """Close Neo4j driver"""
        self.driver.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
