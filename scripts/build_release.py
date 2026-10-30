"""Build the RaagKG release files from the source sheet.

    python scripts/build_release.py

Reads  data/raw/raagkg_source_sheet.tsv  (the curated sheet, kept unchanged)
Writes data/raagkg.csv, data/raagkg.json,
       graph/nodes.csv, graph/edges.csv, graph/raagkg.graphml,
       graph/import_neo4j.cypher, reports/related_raga_links.csv

Every correction applied to the sheet is listed in CORRECTIONS below and in
CHANGELOG.md, so the cleaned files can always be traced back to the source.
"""
import csv
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "raagkg_source_sheet.tsv"

THAATS = {"Bilawal", "Kalyan", "Khamaj", "Kafi", "Asavari",
          "Bhairavi", "Bhairav", "Marwa", "Poorvi", "Todi"}

# Prahar slots: the day is split into eight three-hour watches.
PRAHAR_SLOTS = {
    "1": "6 AM - 9 AM", "2": "9 AM - 12 PM", "3": "12 PM - 3 PM",
    "4": "3 PM - 6 PM", "5": "6 PM - 9 PM", "6": "9 PM - 12 AM",
    "7": "12 AM - 3 AM", "8": "3 AM - 6 AM", "any": "Any time",
}

# Each free-text time in the sheet mapped to the slot that its clock range
# covers most. Ranges that straddle two slots go to the slot holding the
# larger share (e.g. 11 PM - 2 AM -> slot 7).
PRAHAR_MAP = {
    "Early Morning (6AM-9AM)": "1",
    "First Quarter of Morning (6AM-9AM)": "1",
    "Late Morning (9AM-12PM)": "2",
    "Late Morning (9-12am)": "2",
    "Mid-day (12PM-3PM)": "3",
    "Mid-day (12-3pm)": "3",
    "Late Afternoon (3PM-6PM)": "4",
    "Late Afternoon (3-6pm)": "4",
    "Late Afternoon (3PM-5PM)": "4",
    "Late Afternoon / Sunset (4PM-6PM)": "4",
    "Late Afternoon (4PM-7PM)": "4",
    "First Quarter of Night (6PM-9PM)": "5",
    "First Quarter of Night (6-9pm)": "5",
    "First quarter of night (6-9pm)": "5",
    "First Quarter of Night (7PM-9PM)": "5",
    "Sunset (6PM-9PM)": "5",
    "First Quarter of Night (9PM-12AM)": "6",
    "Second Quarter of Night (9PM-12AM)": "6",
    "Second Quarter of Night (9PM-12PM)": "6",
    "Second Quarter of Night (10PM-1AM)": "6",
    "Mid Night (9PM-12AM)": "6",
    "Mid Night (Rainy Season)": "6",
    "Late Night (9PM-12AM)": "6",
    "Late Night (10pm-1am)": "6",
    "Late Night (12AM-3AM)": "7",
    "Late Night (11PM-2AM)": "7",
    "Mid Night (12AM-3AM)": "7",
    "Late Night / Spring Season": "7",
    "Last Quarter of Night (3AM-6AM)": "8",
    "Dawn (3AM-6AM)": "8",
    "Rainy Season (any time)": "any",
    "Any time (Sarvakalik)": "any",
}

# Names in the related-raga column that refer to a catalogue raga under a
# different spelling. "Bilawal" is left unresolved on purpose: it may mean
# either Shuddha Bilawal or Alhaiya Bilawal.
ALIASES = {
    "sohni": "Sohani",
    "hameer": "Hamir",
    "suha": "Suha Kanada",
    "shahana": "Shahana Kanada",
}


def fix_row(r):
    """Apply the documented corrections. Returns the list of changes made."""
    changes = []
    name = r["Raga_Name"]
    if name == "Miyan Ki Malhar" and r["Jaati"] == "Rainy Season":
        # Values from Jaati onwards had slid one column to the right.
        r["Prahar"] = "Mid Night (Rainy Season)"
        r["Jaati"] = "Sampurna-Sampurna"
        r["Rasa"] = "Gambhir, Shanti"
        r["Nature_Character"] = ""
        changes.append("realigned columns that had shifted by one; "
                       "temperament left blank (value lost in the shift)")
    if name == "Lankadahan Sarang" and r["Thaat"] == "Sarang":
        r["Thaat"] = "Kafi"
        changes.append("thaat 'Sarang' is not a standard thaat; set to Kafi")
    if name in ("Basant", "Paraj"):
        for col in ("Aroha", "Avaroha", "Pakad"):
            new = r[col].replace("m'", "M'")
            if new != r[col]:
                r[col] = new
                changes.append(f"{col}: teevra Ma written m' changed to M'")
    return changes


def split_list(text):
    return [t.strip() for t in re.split(r",", text or "") if t.strip()]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def swar_id(note):
    """Swar node id: keep komal/shuddha case, drop octave marks."""
    return note.replace("'", "").strip()


def main():
    rows = list(csv.DictReader(open(RAW, encoding="utf-8"), delimiter="\t"))
    catalogue = {r["Raga_Name"].strip().lower(): r["Raga_Name"].strip()
                 for r in rows}
    corrections, records, link_rows = [], [], []

    for r in rows:
        r = {k: (v or "").strip() for k, v in r.items()}
        for c in fix_row(r):
            corrections.append((r["Raga_Name"], c))
        if r["Thaat"] not in THAATS:
            raise SystemExit(f"unknown thaat for {r['Raga_Name']}: {r['Thaat']}")
        if r["Prahar"] not in PRAHAR_MAP:
            raise SystemExit(f"unmapped prahar for {r['Raga_Name']}: {r['Prahar']}")

        related, related_unresolved = [], []
        for s in split_list(r["Samaprakritic_Raags"]):
            key = s.lower()
            target = catalogue.get(key) or ALIASES.get(key)
            if target:
                related.append(target)
            else:
                related_unresolved.append(s)
            link_rows.append({"raga": r["Raga_Name"], "listed_as": s,
                              "resolved_to": target or "",
                              "status": "resolved" if target else "not in catalogue"})

        season = r["Season"]
        records.append({
            "raga": r["Raga_Name"],
            "thaat": r["Thaat"],
            "aroha": r["Aroha"],
            "avaroha": r["Avaroha"],
            "vadi": r["Vadi_Swar"],
            "samvadi": r["Samvadi_Swar"],
            "pakad": r["Pakad"],
            "jaati": r["Jaati"],
            "prahar": r["Prahar"],
            "prahar_slot": PRAHAR_MAP[r["Prahar"]],
            "rasa": split_list(r["Rasa"]),
            "prakriti": split_list(r["Nature_Character"]),
            "ritu": ("all" if season.startswith("All") else season.lower()),
            "samaprakritic": related,
            "samaprakritic_unresolved": related_unresolved,
        })

    records.sort(key=lambda x: x["raga"].lower())

    # ---- tabular release -------------------------------------------------
    cols = ["raga", "thaat", "aroha", "avaroha", "vadi", "samvadi", "pakad",
            "jaati", "prahar", "prahar_slot", "rasa", "prakriti", "ritu",
            "samaprakritic", "samaprakritic_unresolved"]
    with open(ROOT / "data" / "raagkg.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rec in records:
            w.writerow({k: "; ".join(v) if isinstance(v, list) else v
                        for k, v in rec.items()})
    with open(ROOT / "data" / "raagkg.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    with open(ROOT / "reports" / "related_raga_links.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["raga", "listed_as", "resolved_to", "status"])
        w.writeheader()
        w.writerows(link_rows)

    # ---- graph -----------------------------------------------------------
    nodes, edges = {}, []

    def node(nid, label, name, **props):
        nodes.setdefault(nid, {"id": nid, "label": label, "name": name, **props})
        return nid

    for rec in records:
        rid = node("raga:" + slug(rec["raga"]), "Raga", rec["raga"],
                   aroha=rec["aroha"], avaroha=rec["avaroha"],
                   pakad=rec["pakad"], prahar_text=rec["prahar"])

        def link(target, rel):
            edges.append({"source": rid, "target": target, "type": rel})

        link(node("thaat:" + slug(rec["thaat"]), "Thaat", rec["thaat"]),
             "belongs_to_thaat")
        s = rec["prahar_slot"]
        link(node("prahar:" + s, "Prahar",
                  PRAHAR_SLOTS[s] if s == "any" else f"Prahar {s} ({PRAHAR_SLOTS[s]})"),
             "performed_in")
        if rec["jaati"]:
            link(node("jaati:" + slug(rec["jaati"]), "Jaati", rec["jaati"]), "has_jaati")
        for v in rec["rasa"]:
            link(node("rasa:" + slug(v), "Rasa", v), "has_rasa")
        for v in rec["prakriti"]:
            link(node("prakriti:" + slug(v), "Prakriti", v), "has_prakriti")
        if rec["ritu"]:
            label = "All seasons (Sarvakalik)" if rec["ritu"] == "all" else rec["ritu"].title()
            link(node("ritu:" + rec["ritu"], "Ritu", label), "associated_with_season")
        for col, rel in (("vadi", "vadi_swar"), ("samvadi", "samvadi_swar")):
            for note in re.split(r"\s+or\s+", rec[col]):
                if note:
                    link(node("swar:" + swar_id(note), "Swar", swar_id(note)), rel)
        for other in rec["samaprakritic"]:
            link("raga:" + slug(other), "samaprakritic")

    node_cols = ["id", "label", "name", "aroha", "avaroha", "pakad", "prahar_text"]
    nlist = sorted(nodes.values(), key=lambda n: (n["label"], n["id"]))
    with open(ROOT / "graph" / "nodes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=node_cols)
        w.writeheader()
        for n in nlist:
            w.writerow({c: n.get(c, "") for c in node_cols})
    with open(ROOT / "graph" / "edges.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source", "target", "type"])
        w.writeheader()
        w.writerows(edges)

    # GraphML (Gephi, networkx, yEd)
    keys = ["label", "name", "aroha", "avaroha", "pakad", "prahar_text"]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    out += [f'  <key id="{k}" for="node" attr.name="{k}" attr.type="string"/>' for k in keys]
    out.append('  <key id="type" for="edge" attr.name="type" attr.type="string"/>')
    out.append('  <graph id="RaagKG" edgedefault="directed">')
    for n in nlist:
        out.append(f'    <node id="{escape(n["id"])}">')
        for k in keys:
            if n.get(k):
                out.append(f'      <data key="{k}">{escape(n[k])}</data>')
        out.append("    </node>")
    for i, e in enumerate(edges):
        out.append(f'    <edge id="e{i}" source="{escape(e["source"])}" '
                   f'target="{escape(e["target"])}"><data key="type">{e["type"]}</data></edge>')
    out += ["  </graph>", "</graphml>"]
    (ROOT / "graph" / "raagkg.graphml").write_text("\n".join(out), encoding="utf-8")

    # Cypher script: paste into Neo4j Browser or run with cypher-shell.
    def lit(v):
        return json.dumps(v, ensure_ascii=False)

    cy = ["// RaagKG import script, generated by scripts/build_release.py",
          "// Run on an empty database: cypher-shell -f graph/import_neo4j.cypher", ""]
    for label in sorted({n["label"] for n in nlist}):
        cy.append(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                  f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;")
    cy.append("")
    for label in sorted({n["label"] for n in nlist}):
        items = []
        for n in nlist:
            if n["label"] != label:
                continue
            props = {k: n[k] for k in node_cols if k != "label" and n.get(k)}
            items.append("{" + ", ".join(f"{k}: {lit(v)}" for k, v in props.items()) + "}")
        cy.append(f"UNWIND [\n  " + ",\n  ".join(items) +
                  f"\n] AS p\nMERGE (n:{label} {{id: p.id}}) SET n += p;\n")
    labels = {n["id"]: n["label"] for n in nlist}
    for rel in sorted({e["type"] for e in edges}):
        es = [e for e in edges if e["type"] == rel]
        tl = labels[es[0]["target"]]
        items = [f"[{lit(e['source'])}, {lit(e['target'])}]" for e in es]
        cy.append(f"UNWIND [\n  " + ",\n  ".join(items) +
                  f"\n] AS e\nMATCH (a:Raga {{id: e[0]}}), (b:{tl} {{id: e[1]}})\n"
                  f"MERGE (a)-[:{rel}]->(b);\n")
    (ROOT / "graph" / "import_neo4j.cypher").write_text("\n".join(cy), encoding="utf-8")

    print(f"ragas: {len(records)}  nodes: {len(nodes)}  edges: {len(edges)}")
    print("corrections applied:")
    for name, c in corrections:
        print(f"  {name}: {c}")


if __name__ == "__main__":
    main()
