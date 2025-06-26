#!/usr/bin/env bash
# Quick health-check script for the Neo4j graph produced by digest_to_neo4j.py.
# It connects to the running container and prints summary stats. Optionally it
# can fail (non-zero exit) if the graph looks empty.
#
# Environment overrides:
#   NEO4J_CONTAINER – Docker container name (default: neo4j)
#   NEO4J_USER      – Username (default: neo4j)
#   NEO4J_PASSWORD  – Password (default: graph1234)
#   STRICT          – If set to 1, exit 1 when node or rel count == 0
#
set -euo pipefail

NEO4J_CONTAINER="${NEO4J_CONTAINER:-neo4j}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-graph1234}"
STRICT="${STRICT:-0}"

if ! docker ps --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"; then
  echo "Container '${NEO4J_CONTAINER}' not running." >&2
  exit 1
fi

echo "Checking graph in container '${NEO4J_CONTAINER}'..."

NODE_COUNT=$(docker exec -i "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n) AS c" | tail -n1)
REL_COUNT=$(docker exec -i "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "MATCH ()-[r]->() RETURN count(r) AS c" | tail -n1)

LABELS=$(docker exec -i "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "CALL db.labels()" | tail -n +2)
RELS=$(docker exec -i "$NEO4J_CONTAINER" cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" "CALL db.relationshipTypes()" | tail -n +2)

echo "Nodes : $NODE_COUNT"
echo "Rels  : $REL_COUNT"
echo "Labels: $LABELS"
echo "RelTypes: $RELS"

if [[ "$STRICT" == "1" ]]; then
  if [[ "$NODE_COUNT" == "0" || "$REL_COUNT" == "0" ]]; then
    echo "Graph appears empty – failing (STRICT=1)" >&2
    exit 1
  fi
fi

echo "Graph check completed successfully." 