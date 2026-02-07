from neo4j import GraphDatabase
import json
import os
import logging
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =========================================================
# CONFIGURATION
# =========================================================
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")

BATCH_SIZE = 100  # Process topics in batches for better performance

# =========================================================
# VALIDATION
# =========================================================
def validate_config():
    """Validate configuration and environment"""
    if not URI:
        raise ValueError("NEO4J_URI not set in environment")
    if not PASSWORD:
        raise ValueError("NEO4J_PASSWORD not set in environment")
    if not os.path.exists("quran_topics_v2.json"):
        raise FileNotFoundError("quran_topics_v2.json not found")
    
    logger.info("Configuration validated successfully")
    logger.info(f"Neo4j URI: {URI}")
    logger.info(f"Neo4j User: {USER}")

# =========================================================
# NEO4J CONNECTION
# =========================================================
def test_connection(driver):
    """Test Neo4j connection"""
    try:
        driver.verify_connectivity()
        logger.info("✅ Neo4j connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
        return False

# =========================================================
# CLEAR DATABASE (OPTIONAL)
# =========================================================
def clear_database(driver):
    """Clear existing data - USE WITH CAUTION"""
    logger.warning("Clearing existing data...")
    
    try:
        driver.execute_query(
            """
            MATCH (n)
            DETACH DELETE n
            """,
            database_="neo4j"
        )
        logger.info("✅ Database cleared")
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        raise

# =========================================================
# CREATE INDEXES
# =========================================================
def create_indexes(driver):
    """Create indexes for better query performance"""
    logger.info("Creating indexes...")
    
    indexes = [
        ("CREATE INDEX ayah_ref IF NOT EXISTS FOR (a:Ayah) ON (a.ref)", "ayah_ref"),
        ("CREATE INDEX ayah_surah IF NOT EXISTS FOR (a:Ayah) ON (a.surah)", "ayah_surah"),
        ("CREATE INDEX topic_id IF NOT EXISTS FOR (t:Topic) ON (t.id)", "topic_id"),
        ("CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)", "concept_name"),
    ]
    
    for query, name in indexes:
        try:
            driver.execute_query(query, database_="neo4j")
            logger.info(f"✅ Created index: {name}")
        except Exception as e:
            logger.warning(f"Index {name} may already exist: {e}")
    
    logger.info("Indexes created successfully")

# =========================================================
# CREATE CONSTRAINTS
# =========================================================
def create_constraints(driver):
    """Create uniqueness constraints"""
    logger.info("Creating constraints...")
    
    constraints = [
        ("""
        CREATE CONSTRAINT ayah_ref_unique IF NOT EXISTS
        FOR (a:Ayah) REQUIRE a.ref IS UNIQUE
        """, "ayah_ref_unique"),
        ("""
        CREATE CONSTRAINT topic_id_unique IF NOT EXISTS
        FOR (t:Topic) REQUIRE t.id IS UNIQUE
        """, "topic_id_unique"),
    ]
    
    for query, name in constraints:
        try:
            driver.execute_query(query, database_="neo4j")
            logger.info(f"✅ Created constraint: {name}")
        except Exception as e:
            logger.warning(f"Constraint {name} may already exist: {e}")

# =========================================================
# BATCH INGESTION
# =========================================================
def ingest_topics_batch(driver, topics_batch, batch_num, total_batches):
    """Ingest a batch of topics efficiently"""
    try:
        # Prepare batch data
        batch_data = [
            {
                "id": topic["id"],
                "ayahs": topic["ayahs"],
                "size": len(topic["ayahs"])
            }
            for topic in topics_batch
        ]
        
        # Single query for entire batch
        query = """
        UNWIND $batch AS topic
        
        // Create Topic node
        MERGE (t:Topic {id: topic.id})
        SET t.size = topic.size
        
        WITH t, topic
        UNWIND topic.ayahs AS ref
        
        // Create Ayah node with extracted surah/ayah numbers
        MERGE (a:Ayah {ref: ref})
        ON CREATE SET 
            a.surah = toInteger(split(ref, ':')[0]),
            a.ayah = toInteger(split(ref, ':')[1])
        
        // Create relationship
        MERGE (a)-[:PART_OF]->(t)
        """
        
        driver.execute_query(
            query,
            batch=batch_data,
            database_="neo4j"
        )
        
        logger.info(f"✅ Batch {batch_num}/{total_batches} completed "
                   f"({len(topics_batch)} topics)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Batch {batch_num} failed: {e}")
        return False

# =========================================================
# CREATE RELATIONSHIPS (OPTIONAL)
# =========================================================
def create_ayah_relationships(driver):
    """
    Create RELATED_TO relationships between ayahs in the same topic
    WARNING: This can be very expensive for large topics
    """
    logger.info("Creating ayah-to-ayah relationships...")
    logger.warning("This may take a long time for large datasets")
    
    query = """
    MATCH (t:Topic)
    MATCH (a1:Ayah)-[:PART_OF]->(t)<-[:PART_OF]-(a2:Ayah)
    WHERE a1.ref < a2.ref
    MERGE (a1)-[:RELATED_TO]->(a2)
    """
    
    try:
        result = driver.execute_query(query, database_="neo4j")
        logger.info("✅ Ayah relationships created")
    except Exception as e:
        logger.error(f"Failed to create relationships: {e}")

# =========================================================
# STATISTICS
# =========================================================
def print_statistics(driver):
    """Print database statistics"""
    logger.info("=" * 60)
    logger.info("DATABASE STATISTICS")
    logger.info("=" * 60)
    
    queries = [
        ("MATCH (t:Topic) RETURN count(t) as count", "Topics"),
        ("MATCH (a:Ayah) RETURN count(a) as count", "Ayahs"),
        ("MATCH ()-[r:PART_OF]->() RETURN count(r) as count", "PART_OF relationships"),
        ("MATCH ()-[r:RELATED_TO]->() RETURN count(r) as count", "RELATED_TO relationships"),
    ]
    
    for query, label in queries:
        try:
            result = driver.execute_query(query, database_="neo4j")
            count = result.records[0]["count"]
            logger.info(f"{label}: {count:,}")
        except Exception as e:
            logger.warning(f"Could not get {label}: {e}")
    
    logger.info("=" * 60)

# =========================================================
# MAIN INGESTION PIPELINE
# =========================================================
def run_ingestion(clear_first=False, create_relations=False):
    """
    Main ingestion pipeline
    
    Args:
        clear_first: If True, clear existing data before ingestion
        create_relations: If True, create RELATED_TO relationships between ayahs
    """
    start_time = time.time()
    
    try:
        # Validate configuration
        logger.info("=" * 60)
        logger.info("STEP 1: Validating configuration")
        logger.info("=" * 60)
        validate_config()
        
        # Load data
        logger.info("=" * 60)
        logger.info("STEP 2: Loading data")
        logger.info("=" * 60)
        with open("quran_topics_v2.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        topics = data["topics"]
        logger.info(f"Loaded {len(topics)} topics")
        
        # Connect to Neo4j
        logger.info("=" * 60)
        logger.info("STEP 3: Connecting to Neo4j")
        logger.info("=" * 60)
        
        with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
            if not test_connection(driver):
                raise ConnectionError("Failed to connect to Neo4j")
            
            # Optional: Clear database
            if clear_first:
                logger.info("=" * 60)
                logger.info("STEP 4: Clearing existing data")
                logger.info("=" * 60)
                clear_database(driver)
            
            # Create indexes and constraints
            logger.info("=" * 60)
            logger.info("STEP 5: Creating indexes and constraints")
            logger.info("=" * 60)
            create_indexes(driver)
            create_constraints(driver)
            
            # Batch ingestion
            logger.info("=" * 60)
            logger.info("STEP 6: Batch ingestion")
            logger.info("=" * 60)
            
            total_batches = (len(topics) + BATCH_SIZE - 1) // BATCH_SIZE
            failed_batches = []
            
            for i in range(0, len(topics), BATCH_SIZE):
                batch = topics[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                
                success = ingest_topics_batch(driver, batch, batch_num, total_batches)
                
                if not success:
                    failed_batches.append(batch_num)
                    logger.warning(f"Retrying batch {batch_num}...")
                    time.sleep(2)
                    success = ingest_topics_batch(driver, batch, batch_num, total_batches)
                    
                    if not success:
                        logger.error(f"Batch {batch_num} failed after retry")
                
                # Small delay to avoid overwhelming the server
                if batch_num % 10 == 0:
                    time.sleep(0.5)
            
            if failed_batches:
                logger.warning(f"Failed batches: {failed_batches}")
            else:
                logger.info("✅ All batches ingested successfully")
            
            # Optional: Create relationships
            if create_relations:
                logger.info("=" * 60)
                logger.info("STEP 7: Creating ayah relationships")
                logger.info("=" * 60)
                create_ayah_relationships(driver)
            
            # Print statistics
            logger.info("=" * 60)
            logger.info("STEP 8: Final statistics")
            logger.info("=" * 60)
            print_statistics(driver)
        
        # Summary
        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info("✅ INGESTION COMPLETED SUCCESSFULLY")
        logger.info(f"Total time: {elapsed:.2f} seconds")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        raise

# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ingest Quran topics into Neo4j")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before ingestion"
    )
    parser.add_argument(
        "--relations",
        action="store_true",
        help="Create RELATED_TO relationships between ayahs (slow)"
    )
    
    args = parser.parse_args()
    
    if args.clear:
        logger.warning("⚠️  WARNING: This will DELETE all existing data!")
        confirm = input("Are you sure? Type 'yes' to continue: ")
        if confirm.lower() != 'yes':
            logger.info("Aborted by user")
            exit(0)
    
    run_ingestion(clear_first=args.clear, create_relations=args.relations)