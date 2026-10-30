"""Run with:  python tests/test_raagkg.py   (or: pytest)"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import raagkg  # noqa: E402

RAGAS = raagkg.load()


def test_counts_match_paper_table():
    assert len(RAGAS) == 101
    assert {r["thaat"] for r in RAGAS} == set(raagkg.THAAT_SCALES)
    assert sum(1 for r in RAGAS if r["ritu"]) == 73
    assert sum(1 for r in RAGAS if r["samaprakritic"] or r["samaprakritic_unresolved"]) == 44


def test_names_unique():
    names = [r["raga"].lower() for r in RAGAS]
    assert len(names) == len(set(names))


def test_every_raga_has_core_attributes():
    for r in RAGAS:
        for col in ("thaat", "aroha", "avaroha", "vadi", "samvadi", "pakad",
                    "jaati", "prahar", "prahar_slot"):
            assert r[col], (r["raga"], col)
        assert r["rasa"], r["raga"]


def test_recommend_is_deterministic_and_explained():
    q = dict(prahar="4", rasa="Karuna", prakriti="Longing", ritu="summer")
    first = raagkg.recommend(RAGAS, **q)
    assert first == raagkg.recommend(RAGAS, **q)
    assert first[0]["raga"] == "Multani"
    for hit in first:
        assert len(hit["matched"]) >= 1
        assert hit["score"] == sum(2 if m.startswith("associated_with_season") else 1
                                   for m in hit["matched"])


def test_graph_edges_point_to_existing_nodes():
    nodes = {row["id"] for row in csv.DictReader(open(ROOT / "graph" / "nodes.csv", encoding="utf-8"))}
    for e in csv.DictReader(open(ROOT / "graph" / "edges.csv", encoding="utf-8")):
        assert e["source"] in nodes and e["target"] in nodes, e


def test_notes_parser():
    assert raagkg.notes("N' R G M' D N S'") == {"N", "R", "G", "M'", "D", "S"}
    assert raagkg.notes("S r g m P d n S'") == {"S", "r", "g", "m", "P", "d", "n"}
    assert raagkg.notes("S R G P D S' (varies)") == {"S", "R", "G", "P", "D"}


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for t in tests:
        t()
        print("ok ", t.__name__)
    print(f"{len(tests)} tests passed")
