// === Neo4j handy queries for the Gitingest graph ===
// Copy-paste the ones you need into Browser, or run via cypher-shell with: -f query.cypher
// Lines starting with // are ignored by Cypher.

///////////////////////////////////////////////////////////////////////////
// 1. Global counts
///////////////////////////////////////////////////////////////////////////
// Total nodes
MATCH (n) RETURN count(n) AS total_nodes;

// Total relationships
MATCH ()-[r]->() RETURN count(r) AS total_relationships;

// Counts by label
MATCH (n) RETURN n.label AS label, count(*) AS nodes ORDER BY nodes DESC;

// Counts by relationship type
MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS total ORDER BY total DESC;

///////////////////////////////////////////////////////////////////////////
// 2. Show the whole graph (use with care if graph is large)
///////////////////////////////////////////////////////////////////////////
// A. Visual graph of every relationship
// (nodes + relationships returned separately – Neo4j Browser still shows full graph)
MATCH (n)-[r]->(m) RETURN n, r, m;
//   Tip: In Browser, press the eye icon to adjust node sizes or apply the "hierarchical" style.

// B. Smaller sample if the graph grows in the future
// MATCH p=(n)-[r]->(m) RETURN p LIMIT 250;

///////////////////////////////////////////////////////////////////////////
// 3. Explore a particular file's members
///////////////////////////////////////////////////////////////////////////
// Replace 'cli.py' with any file name
MATCH (f:Entity {label:'File', name:'cli.py'})-[:CONTAINS]->(m)
RETURN m.id AS id, m.label AS label, m.name AS name
ORDER BY label;

///////////////////////////////////////////////////////////////////////////
// 4. Fan-in/fan-out of a function (call graph excerpt)
///////////////////////////////////////////////////////////////////////////
// Who calls run_command?
MATCH (caller)-[:CALLS]->(callee:Entity {label:'Function', name:'run_command'})
RETURN caller.id;

// What does clone_repo call?
MATCH (src:Entity {name:'clone_repo'})-[:CALLS]->(target)
RETURN target.id;

///////////////////////////////////////////////////////////////////////////
// 5. Inheritance chains
///////////////////////////////////////////////////////////////////////////
// Direct subclasses of TimeoutError
MATCH (child)-[:INHERITS]->(parent {name:'TimeoutError'}) RETURN child.id;

// Full inheritance hierarchy
MATCH path = (root:Entity {label:'Class'})<-[:INHERITS*]-(descendant)
RETURN path;

///////////////////////////////////////////////////////////////////////////
// 6. Orphans – functions with no callers
///////////////////////////////////////////////////////////////////////////
MATCH (f:Entity {label:'Function'})
WHERE NOT ()-[:CALLS]->(f)
RETURN f.id LIMIT 25; 