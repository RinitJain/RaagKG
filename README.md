# RaagKG

[![DOI](https://zenodo.org/badge/1439996614.svg)](https://doi.org/10.5281/zenodo.23813360)

A hand-curated knowledge graph of 101 Hindustani ragas. For each raga it
records twelve attributes, covering both the musical rules (parent scale,
ascent, descent, principal notes, signature phrase, note count) and the
context a raga belongs to (time of day, mood, temperament, season, related
ragas). It comes with a small, transparent rule that suggests ragas for a
time of day, mood, temperament and season, and explains every suggestion by
the attributes it matched.

This repository accompanies the paper *RaagKG: Grounding Music Generation in a
Knowledge Graph of Ragas* (Jain, Joshi, Mahajan, Sonawane and Joshi).

## What is here

| Path | Contents |
|---|---|
| `data/raagkg.csv` | The catalogue, one row per raga (spreadsheet friendly) |
| `data/raagkg.json` | The same data with list fields as JSON arrays |
| `data/raw/raagkg_source_sheet.tsv` | The curated source sheet, unchanged |
| `graph/nodes.csv`, `graph/edges.csv` | The graph as node and edge tables |
| `graph/import_neo4j.cypher` | Builds the graph in Neo4j 5 |
| `graph/raagkg.graphml` | The graph for Gephi, yEd or networkx |
| `src/raagkg.py` | Retrieval rule, explanations and scale check (no dependencies) |
| `scripts/build_release.py` | Rebuilds every file above from the source sheet |
| `reports/scale_check.csv` | Rows whose notes fall outside their parent scale |
| `reports/related_raga_links.csv` | How each related-raga name was resolved |
| `DATA_CARD.md` | Field definitions, sources, known gaps and intended use |
| `CHANGELOG.md` | Every correction made to the source sheet |

## Quick start

Python 3.8 or later, nothing to install.

```bash
python src/raagkg.py recommend --prahar 4 --rasa Karuna --prakriti Longing --ritu summer
```

```
1. Multani  (score 5)
     performed_in -> Prahar 4 (Late Afternoon (3PM-5PM))
     has_rasa -> Karuna
     has_prakriti -> Longing
     associated_with_season -> Summer
2. Palasi  (score 3)
     ...
```

```bash
python src/raagkg.py show Yaman     # one raga's attributes
python src/raagkg.py check          # scale consistency report
python tests/test_raagkg.py         # tests
python scripts/build_release.py     # rebuild data and graph from the sheet
```

To load the graph into Neo4j 5, open an empty database and run
`cypher-shell -f graph/import_neo4j.cypher`, or paste the file into Neo4j Browser.

## How a suggestion is made

A request gives up to four values: a prahar (one of eight three-hour watches,
1 = 6 AM to 9 AM through 8 = 3 AM to 6 AM), a rasa (mood), a prakriti
(temperament) and a ritu (season). Each raga earns one point for a matching
prahar, rasa and prakriti, and two points for a matching season. Ragas that
match nothing are dropped and the three highest are returned; ties keep a
fixed order, so the same request always gives the same answer. Ragas marked
"any time" match every prahar. Nothing in the score depends on how well known
a raga is.

The paper's experiments ran on the authors' Neo4j build of this catalogue.
This release rebuilds the graph from the curated sheet, so small differences
in derived fields, such as the prahar slot, are possible.

## Notation

`S R G m P D N` are the natural (shuddha) notes, `r g d n` the flat (komal)
notes and `M'` the sharp (teevra) Ma. An apostrophe before a note (`'N`) marks
the lower octave; `S'` is the upper Sa. See `DATA_CARD.md` for the remaining
notation details.

## Sources

Attributes were compiled by the authors from V. N. Bhatkhande's *Kramik
Pustak Malika* and V. D. Paluskar's *Sangeet Bal Prakash*, and checked
against SwarGanga, Raga Junglism and Artium Academy. No attribute was written
by a language model.

## Licence

Data (`data/`, `graph/`, `reports/`): [CC BY 4.0](LICENSE-DATA.md).
Code (`src/`, `scripts/`, `tests/`): [MIT](LICENSE).

## Citation

See `CITATION.cff`, or use GitHub's "Cite this repository" button.
Corrections from musicians are welcome as issues or pull requests.

Example outputs of RaagAI, which builds on RaagKG: https://github.com/RinitJain/RaagAI-Outputs
