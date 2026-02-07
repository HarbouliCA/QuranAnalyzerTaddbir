from neo4j import GraphDatabase

class QuranGraphSearch:

    def __init__(self, driver: GraphDatabase.driver):
        self.driver = driver

    def search_by_concept(self, query: str):
        cypher = """
        MATCH (c:Concept)
        WHERE toLower(c.name) CONTAINS toLower($q)
        MATCH (a:Ayah)-[:MENTIONS]->(c)
        OPTIONAL MATCH (c)-[:PART_OF]->(l:Law)
        RETURN 
            c.name AS concept,
            l.name AS law,
            a.ref AS ref,
            a.text AS text
        ORDER BY a.surah, a.ayah
        """
        with self.driver.session() as s:
            return s.run(cypher, q=query).data()

    def expand_from_ayah(self, ref: str):
        cypher = """
        MATCH (a:Ayah {ref:$ref})-[:MENTIONS]->(c:Concept)<-[:MENTIONS]-(other:Ayah)
        WHERE a <> other
        RETURN DISTINCT
            c.name AS concept,
            other.ref AS ref,
            other.text AS text
        """
        with self.driver.session() as s:
            return s.run(cypher, ref=ref).data()
