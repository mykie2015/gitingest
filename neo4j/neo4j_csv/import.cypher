// Run this in cypher-shell or Browser (adjust user/password as needed)
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS row
MERGE (n:Entity {id: row.id}) SET n += row;

LOAD CSV WITH HEADERS FROM 'file:///contains.csv' AS row
MATCH (a:Entity {id: row.start_id})
MATCH (b:Entity {id: row.end_id})
MERGE (a)-[:CONTAINS]->(b);

LOAD CSV WITH HEADERS FROM 'file:///inherits.csv' AS row
MATCH (a:Entity {id: row.start_id})
MATCH (b:Entity {id: row.end_id})
MERGE (a)-[:INHERITS]->(b);

LOAD CSV WITH HEADERS FROM 'file:///calls.csv' AS row
MATCH (a:Entity {id: row.start_id})
MATCH (b:Entity {id: row.end_id})
MERGE (a)-[:CALLS]->(b);

