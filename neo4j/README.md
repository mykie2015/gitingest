# Gitingest → Neo4j Workflow

This folder contains everything you need to visualise a repository's **file/function call graph** inside a local Neo4j database.

## Folder Contents

| Item | Purpose |
|------|---------|
| `digest_to_neo4j.py` | Converts a *Gitingest* digest into CSV files understood by Neo4j's [`LOAD CSV`](https://neo4j.com/docs/cypher-manual/current/clauses/load-csv/) command. |
| `neo4j_csv/` | Auto-generated CSVs (`nodes.csv`, `contains.csv`, `calls.csv`, `inherits.csv`) plus `import.cypher` (Cypher script that loads them). |
| `neo4j-docker-compose.yml` | Spins up a Neo4j **5.x** Community Edition instance with the CSV folder mounted at `/import`. |
| `load_to_neo4j.sh` | Helper script that **empties** the DB, copies fresh CSVs into the container and runs `import.cypher`. |
| `check_neo4j.sh` | Sanity-check script – prints node / relationship counts (optionally in *strict* mode). |
| `query.cypher` | A collection of handy Cypher snippets for exploring the graph. |

---

## Quick-start

### 1. Generate a digest
If you haven't already:

```bash
# From the repo root
poetry install            # or use your existing venv

gitingest . -o - > neo4j/my_repo_digest.txt
```

### 2. Convert the digest to CSV

```bash
python neo4j/digest_to_neo4j.py neo4j/my_repo_digest.txt
```
This populates **`neo4j/neo4j_csv/*`** and overwrites any existing CSVs.

### 3. Start Neo4j

```bash
# Detached mode; exposes :7474 (HTTP) and :7687 (Bolt)
docker compose -f neo4j/neo4j-docker-compose.yml up -d
```
Default credentials (defined in the compose file):

* **User**: `neo4j`
* **Password**: `graph1234`

> Change the password by editing the compose file or exporting `NEO4J_AUTH=neo4j/<new-pw>` before `docker compose up`.

### 4. Load the CSVs

```bash
bash neo4j/load_to_neo4j.sh
```
The script will:
1. **Clear** all existing data (`MATCH (n) DETACH DELETE n`).
2. Copy the CSVs into the container's `/import` folder.
3. Run `neo4j_csv/import.cypher` to create indexes & load nodes / relationships.

### 5. Sanity check

```bash
# basic counts
bash neo4j/check_neo4j.sh

# strict mode + schema validation
STRICT=1 bash neo4j/check_neo4j.sh
```

### 6. Explore!

Open <http://localhost:7474> in your browser, log in with the credentials above and start running Cypher.  For convenience you can paste queries from `neo4j/query.cypher` or run the whole file via:

```bash
docker exec -i neo4j cypher-shell -u neo4j -p graph1234 < neo4j/query.cypher
```

---

## Scripts in Detail

### `load_to_neo4j.sh`

```text
USAGE: load_to_neo4j.sh [--strict]

--strict   aborts if the expected node / relationship counts do **not** match
```
The script honours two optional environment variables:

* `NEO4J_CONTAINER` – container name (default `neo4j`)
* `NEO4J_PASSWORD`  – password (default `graph1234`)

### `check_neo4j.sh`
Same flags & env vars as above.  When you set `STRICT=1` it now also validates the graph **schema** in addition to counts.

Schema-related environment variables:

* `EXPECTED_LABELS` – space-separated list of node labels that must exist (default: `Entity`)
* `EXPECTED_REL_TYPES` – space-separated list of relationship types that must exist (default: `CONTAINS CALLS INHERITS`)

Example strict run:

```bash
STRICT=1 EXPECTED_LABELS="Entity" EXPECTED_REL_TYPES="CONTAINS CALLS" bash neo4j/check_neo4j.sh
```

If any expectation fails, the script exits with status 1 – perfect for CI pipelines.

---

## Cleaning Up

```bash
docker compose -f neo4j/neo4j-docker-compose.yml down -v
```
This stops Neo4j **and** removes the volume so the next import starts fresh.

---

## Troubleshooting

| Symptom | Possible Cause / Fix |
|---------|----------------------|
| `Could not find the file /import` when copying CSVs | Container not running or has a different name.  Check `docker ps` and the `NEO4J_CONTAINER` env var. |
| Cypher script runs but *nothing* appears in Browser | Your current DB is empty.  Make sure you ran `digest_to_neo4j.py` *and* `load_to_neo4j.sh` after restarting the container. |
| "password must be at least 8 characters" | Neo4j 5 enforces a min-length; update `neo4j-docker-compose.yml` accordingly. |
| Want to inspect raw CSVs | They're in `neo4j/neo4j_csv/` – open with any spreadsheet or text editor. |

---

Happy graphing! 🎉 