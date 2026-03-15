"""Tests for the ontograph CLI.

Tests cover argument parsing, subcommand dispatch, JSON output, and error
handling for all commands that don't require OPENAI_API_KEY (stats, entities,
entity, relationships, neighbors, schema list/get/register, add-alias).
Commands requiring the LLM (ingest, search, ask, resolve, add-entity) are
tested for argument parsing only.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ontograph.cli import build_parser, main


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    """Return a path to a temporary database file."""
    return str(tmp_path / "test.db")


@pytest.fixture
def populated_db(tmp_db: str) -> str:
    """Create a database with some entities, relationships, aliases, and schemas."""
    from ontograph.db import GraphDB
    from ontograph.models import Alias, Entity, Relationship, Schema

    db = GraphDB(tmp_db)
    db.insert_entity(Entity(name="Lena", entity_type="person", id="aaa111bbb222"))
    db.insert_entity(Entity(name="Dev", entity_type="person", id="ccc333ddd444"))
    db.insert_entity(Entity(name="Project Neptune", entity_type="project", id="eee555fff666"))

    db.insert_relationship(
        Relationship(
            source_id="aaa111bbb222",
            target_id="eee555fff666",
            relationship_type="works_on",
            directed=True,
        )
    )
    db.insert_relationship(
        Relationship(
            source_id="aaa111bbb222",
            target_id="ccc333ddd444",
            relationship_type="colleague",
            directed=False,
        )
    )

    db.insert_alias(Alias(entity_id="aaa111bbb222", alias="Al", alias_type="nickname"))

    db.insert_schema(
        Schema(
            name="workplace",
            entity_types=["person", "project", "team"],
            relationship_types=[
                {"name": "works_on", "directed": True},
                {"name": "colleague", "directed": False},
            ],
        )
    )

    db.close()
    return tmp_db


# ── Parser tests ──


class TestParserConstruction:
    def test_build_parser_returns_parser(self) -> None:
        parser = build_parser()
        assert parser.prog == "ontograph"

    def test_version_flag(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_db_flag_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.db == "ontograph.db"

    def test_db_flag_custom(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--db", "custom.db", "stats"])
        assert args.db == "custom.db"

    def test_no_command_exits_cleanly(self) -> None:
        with patch("sys.argv", ["ontograph"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0


# ── Stats ──


class TestStatsCommand:
    def test_stats_empty_db(self, tmp_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", tmp_db, "stats"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["entities"] == 0
        assert output["relationships"] == 0

    def test_stats_populated_db(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "stats"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["entities"] == 3
        assert output["relationships"] == 2
        assert output["aliases"] == 1


# ── Entities ──


class TestEntitiesCommand:
    def test_list_all(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "entities"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 3

    def test_filter_by_type(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "entities", "--type", "person"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 2
        assert all(e["entity_type"] == "person" for e in output)

    def test_filter_by_nonexistent_type(
        self, populated_db: str, capsys: pytest.CaptureFixture
    ) -> None:
        with patch(
            "sys.argv", ["ontograph", "--db", populated_db, "entities", "--type", "animal"]
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == []


# ── Entity (single) ──


class TestEntityCommand:
    def test_get_by_id(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "entity", "aaa111bbb222"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["name"] == "Lena"

    def test_get_by_name(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "entity", "Dev"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["name"] == "Dev"
        assert output["entity_type"] == "person"

    def test_not_found(self, populated_db: str) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "entity", "Nobody"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


# ── Relationships ──


class TestRelationshipsCommand:
    def test_list_all_for_entity(
        self, populated_db: str, capsys: pytest.CaptureFixture
    ) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "relationships", "Lena"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 2

    def test_filter_by_type(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch(
            "sys.argv",
            ["ontograph", "--db", populated_db, "relationships", "Lena", "--type", "works_on"],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["relationship_type"] == "works_on"

    def test_no_relationships(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch(
            "sys.argv",
            [
                "ontograph",
                "--db",
                populated_db,
                "relationships",
                "Project Neptune",
                "--direction",
                "outgoing",
            ],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == []


# ── Neighbors ──


class TestNeighborsCommand:
    def test_direct_neighbors(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "neighbors", "Lena"]):
            main()
        output = json.loads(capsys.readouterr().out)
        names = {e["name"] for e in output}
        assert "Dev" in names
        assert "Project Neptune" in names

    def test_depth_2(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch(
            "sys.argv",
            ["ontograph", "--db", populated_db, "neighbors", "Project Neptune", "--depth", "2"],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        names = {e["name"] for e in output}
        # Project Neptune -> Lena -> Dev (depth 2)
        assert "Lena" in names
        assert "Dev" in names


# ── Schema ──


class TestSchemaCommands:
    def test_list_schemas(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch("sys.argv", ["ontograph", "--db", populated_db, "schema", "list"]):
            main()
        output = json.loads(capsys.readouterr().out)
        assert len(output) == 1
        assert output[0]["name"] == "workplace"

    def test_get_schema(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch(
            "sys.argv", ["ontograph", "--db", populated_db, "schema", "get", "workplace"]
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["name"] == "workplace"
        assert "person" in output["entity_types"]

    def test_get_schema_not_found(self, populated_db: str) -> None:
        with patch(
            "sys.argv", ["ontograph", "--db", populated_db, "schema", "get", "nonexistent"]
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_register_schema_inline(
        self, tmp_db: str, capsys: pytest.CaptureFixture
    ) -> None:
        schema_json = json.dumps({
            "name": "test_schema",
            "entity_types": ["thing"],
            "relationship_types": [{"name": "related_to", "directed": False}],
        })
        with patch(
            "sys.argv",
            ["ontograph", "--db", tmp_db, "schema", "register", "--json", schema_json],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["name"] == "test_schema"

    def test_register_schema_from_file(
        self, tmp_db: str, capsys: pytest.CaptureFixture, tmp_path: Path
    ) -> None:
        schema_data = {
            "name": "file_schema",
            "entity_types": ["widget"],
            "relationship_types": [{"name": "connects_to", "directed": True}],
        }
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema_data))

        with patch(
            "sys.argv",
            ["ontograph", "--db", tmp_db, "schema", "register", "--file", str(schema_file)],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["name"] == "file_schema"


# ── Add-alias ──


class TestAddAliasCommand:
    def test_add_alias_by_name(self, populated_db: str, capsys: pytest.CaptureFixture) -> None:
        with patch(
            "sys.argv",
            [
                "ontograph",
                "--db",
                populated_db,
                "add-alias",
                "Lena",
                "Len",
                "--alias-type",
                "nickname",
            ],
        ):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output["alias"] == "Len"
        assert output["alias_type"] == "nickname"
        assert output["entity_id"] == "aaa111bbb222"

    def test_add_alias_entity_not_found(self, populated_db: str) -> None:
        with patch(
            "sys.argv",
            ["ontograph", "--db", populated_db, "add-alias", "Nobody", "Nick"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


# ── Ingest input validation ──


class TestIngestInputValidation:
    def test_no_input_shows_error(self, tmp_db: str) -> None:
        with patch("sys.argv", ["ontograph", "--db", tmp_db, "ingest"]):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = True
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_file_not_found(self, tmp_db: str) -> None:
        with patch(
            "sys.argv",
            ["ontograph", "--db", tmp_db, "ingest", "--file", "/nonexistent/file.txt"],
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_empty_text_shows_error(self, tmp_db: str) -> None:
        with patch("sys.argv", ["ontograph", "--db", tmp_db, "ingest", "--text", "   "]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
