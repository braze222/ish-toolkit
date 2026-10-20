import json
import pytest
from lib.elmatrix.catalog import CATALOG, get_niche, render_catalog, render_opportunity
from lib.elmatrix import cli


def test_catalog_has_unique_ids_and_required_fields():
    ids = [item["id"] for item in CATALOG]
    assert len(ids) >= 20
    assert len(ids) == len(set(ids))
    for item in CATALOG:
        assert item["category"] and item["name"] and item["buyer"]
        assert item["offer"] and item["query"] and item["test"] and item["risks"]


def test_catalog_is_explicitly_hypothetical():
    rendered = render_catalog()
    assert "hypotheses only" in rendered
    assert "no demand, profit" in rendered
    assert len([line for line in rendered.splitlines() if line.startswith("| ")]) >= 20


def test_category_filter_and_json():
    result = json.loads(render_catalog("education", "json"))
    assert result["evidence_status"] == "hypotheses_not_validated"
    assert result["niches"]
    assert all(item["category"] == "education" for item in result["niches"])


def test_opportunity_brief_contains_validation_and_risks():
    brief = render_opportunity("local-cleaning", "ZA")
    assert "unvalidated hypothesis" in brief
    assert "Evidence ledger" in brief
    assert "elmatrix scan --query" in brief
    assert "Main risks" in brief or "Risks to investigate" in brief
    assert "do not call this niche profitable" in brief


def test_unknown_niche_rejected():
    with pytest.raises(ValueError, match="unknown niche ID"):
        render_opportunity("made-up-niche")


def test_cli_niches_and_opportunity(capsys):
    assert cli.main(["niches", "--category", "education"]) == 0
    assert "children-learning" in capsys.readouterr().out
    assert cli.main(["opportunity", "--niche", "digital-templates", "--region", "ZA"]) == 0
    out = capsys.readouterr().out
    assert "digital-templates" not in out  # title uses human-readable name
    assert "Small-business document templates" in out
    assert cli.main(["opportunity", "--niche", "not-real"]) == 2
