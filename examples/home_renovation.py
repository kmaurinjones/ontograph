"""Example: Home renovation project with file references.

Demonstrates how ontograph tracks a home renovation project where entities
reference external files — contractor quotes (PDFs), progress photos (JPGs),
and permit documents. The knowledge graph stores the structured information
while file_refs point to the actual files on disk.

Usage:
    # Create some placeholder files first (or use your own)
    mkdir -p /tmp/reno_files
    touch /tmp/reno_files/kitchen_quote.pdf
    touch /tmp/reno_files/bathroom_quote.pdf
    touch /tmp/reno_files/kitchen_before.jpg
    touch /tmp/reno_files/kitchen_after.jpg
    touch /tmp/reno_files/permit_2026.pdf

    # Run the example
    uv run python examples/home_renovation.py
"""

from ontograph import OntoDB, Schema

DB_PATH = "/tmp/reno_example.db"


def main():
    db = OntoDB(DB_PATH)

    # 1. Define a schema for home renovation
    db.register_schema(Schema(
        name="renovation",
        entity_types=[
            "project", "contractor", "room", "material",
            "document", "milestone",
        ],
        relationship_types=[
            {"name": "works_on", "directed": True},
            {"name": "quoted_for", "directed": True},
            {"name": "part_of", "directed": True},
            {"name": "used_in", "directed": True},
            {"name": "completed", "directed": True},
            {"name": "approved_by", "directed": True},
        ],
    ))

    # 2. Ingest project notes
    result = db.ingest(
        "Started the kitchen renovation in January. Hired Rivera & Sons "
        "Construction for the demolition and framing. They quoted $12,000 for "
        "the full kitchen gut. Also got a quote from Apex Builders for the "
        "bathroom remodel at $8,500. Ordered quartz countertops from Stone "
        "Depot — 40 sq ft of Calacatta Gold. City permit was approved on "
        "Feb 3rd. Kitchen demo completed Feb 15th, framing done by March 1st.",
        source_type="project_notes",
        schema_name="renovation",
    )
    print(f"Ingested: {result['entities_created']} entities, "
          f"{result['relationships_created']} relationships")

    # 3. Attach file references to relevant entities
    # Contractor quotes
    db.attach_files(
        "Rivera & Sons Construction",
        ["/tmp/reno_files/kitchen_quote.pdf"],
    )
    db.attach_files(
        "Apex Builders",
        ["/tmp/reno_files/bathroom_quote.pdf"],
    )

    # Progress photos on the kitchen
    kitchen = db.get_entity("kitchen renovation") or db.get_entity("kitchen")
    if kitchen:
        db.attach_files(
            kitchen.name,
            ["/tmp/reno_files/kitchen_before.jpg", "/tmp/reno_files/kitchen_after.jpg"],
        )

    # Permit document
    permit = db.get_entity("City permit") or db.get_entity("permit")
    if permit:
        db.attach_files(permit.name, ["/tmp/reno_files/permit_2026.pdf"])

    # 4. Query the graph
    print("\n--- Entities with file references ---")
    for entity in db.list_entities():
        if entity.file_refs:
            print(f"  {entity.name} ({entity.entity_type})")
            for ref in entity.file_refs:
                print(f"    -> {ref}")

    # 5. Ask questions — the LLM sees file references in context
    print("\n--- Q&A ---")
    answer = db.ask("What contractor quotes do we have and where are they?")
    print(f"Q: What contractor quotes do we have?\nA: {answer}\n")

    answer2 = db.ask("What photos do we have of the kitchen?")
    print(f"Q: What photos do we have of the kitchen?\nA: {answer2}\n")

    # 6. Show stats
    stats = db.stats()
    print("--- Stats ---")
    print(f"  Entities: {stats['entities']}")
    print(f"  Relationships: {stats['relationships']}")
    print(f"  Documents: {stats['documents']}")

    db.close()


if __name__ == "__main__":
    main()
