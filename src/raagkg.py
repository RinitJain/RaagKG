"""RaagKG: a hand-curated knowledge graph of Hindustani ragas.

Reference implementation of the retrieval rule and the scale check described
in the RaagKG paper. Pure Python, no dependencies.

Command line:
    python src/raagkg.py recommend --prahar 5 --rasa Shringar --prakriti Romantic --ritu spring
    python src/raagkg.py check                  # scale consistency report
    python src/raagkg.py show Yaman             # one raga's attributes

Notation: S R G m P D N are shuddha (natural) notes, r g d n are komal (flat),
M' is teevra (sharp) Ma. An apostrophe before a note ('N) marks the lower
octave and after S, R, G (S') the upper octave.
"""
import argparse
import json
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "raagkg.json"

THAAT_SCALES = {
    "Bilawal":  {"S", "R", "G", "m", "P", "D", "N"},
    "Kalyan":   {"S", "R", "G", "M'", "P", "D", "N"},
    "Khamaj":   {"S", "R", "G", "m", "P", "D", "n"},
    "Kafi":     {"S", "R", "g", "m", "P", "D", "n"},
    "Asavari":  {"S", "R", "g", "m", "P", "d", "n"},
    "Bhairavi": {"S", "r", "g", "m", "P", "d", "n"},
    "Bhairav":  {"S", "r", "G", "m", "P", "d", "N"},
    "Marwa":    {"S", "r", "G", "M'", "P", "D", "N"},
    "Poorvi":   {"S", "r", "G", "M'", "P", "d", "N"},
    "Todi":     {"S", "r", "g", "M'", "P", "d", "N"},
}

# Points per matched request value (Section V of the paper).
WEIGHTS = {"prahar": 1, "rasa": 1, "prakriti": 1, "ritu": 2}


def load(path=DATA):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _has(values, wanted):
    wanted = wanted.strip().lower()
    return any(v.lower() == wanted for v in values)


def recommend(ragas, prahar=None, rasa=None, prakriti=None, ritu=None, k=3):
    """Return the k best-matching ragas with their score and matched edges.

    prahar   : "1".."8" (three-hour watches starting 6 AM)
    rasa     : e.g. "Shringar", "Karuna", "Bhakti"
    prakriti : e.g. "Romantic", "Devotional", "Peaceful"
    ritu     : "spring", "summer", "monsoon", "autumn", "winter"

    Each matched value adds its weight; a season match counts double. Ragas
    that match nothing are dropped. Ties keep a fixed order (by name), so the
    same request always returns the same answer. The score does not use
    popularity or any usage history.
    """
    results = []
    for r in ragas:
        score, why = 0, []
        if prahar and (r["prahar_slot"] == str(prahar) or r["prahar_slot"] == "any"):
            score += WEIGHTS["prahar"]
            why.append(f"performed_in -> Prahar {r['prahar_slot']} ({r['prahar']})")
        if rasa and _has(r["rasa"], rasa):
            score += WEIGHTS["rasa"]
            why.append(f"has_rasa -> {rasa}")
        if prakriti and _has(r["prakriti"], prakriti):
            score += WEIGHTS["prakriti"]
            why.append(f"has_prakriti -> {prakriti}")
        if ritu and r["ritu"] == ritu.strip().lower():
            score += WEIGHTS["ritu"]
            why.append(f"associated_with_season -> {r['ritu'].title()}")
        if score > 0:
            results.append({"raga": r["raga"], "score": score, "matched": why})
    results.sort(key=lambda x: (-x["score"], x["raga"].lower()))
    return results[:k]


def notes(phrase):
    """Set of swaras used in a phrase, ignoring octave marks."""
    found = set()
    phrase = re.sub(r"\b[a-z]{3,}\b", " ", phrase)  # drop words such as "(varies)"
    for m in re.finditer(r"([SRGMPDNrgmdn])('?)", phrase.replace("(", " ").replace(")", " ")):
        letter, mark = m.group(1), m.group(2)
        if letter == "M":
            found.add("M'" if mark else "m")
        else:
            found.add(letter)
    return found


def check(ragas):
    """Flag rows whose notes fall outside their parent scale (thaat).

    A flag is not necessarily an error: many ragas borrow a note from outside
    their thaat. The check narrows the catalogue down to rows a musician
    should look at.
    """
    flags = []
    for r in ragas:
        scale = THAAT_SCALES[r["thaat"]]
        used = notes(r["aroha"]) | notes(r["avaroha"])
        outside = sorted(used - scale)
        if outside:
            flags.append({"raga": r["raga"], "thaat": r["thaat"],
                          "issue": "notes outside thaat", "detail": " ".join(outside)})
        for col in ("vadi", "samvadi"):
            for n in re.split(r"\s+or\s+", r[col]):
                if n and not notes(n) <= used:
                    flags.append({"raga": r["raga"], "thaat": r["thaat"],
                                  "issue": f"{col} not in aroha/avaroha", "detail": n})
    return flags


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("recommend")
    rec.add_argument("--prahar")
    rec.add_argument("--rasa")
    rec.add_argument("--prakriti")
    rec.add_argument("--ritu")
    rec.add_argument("-k", type=int, default=3)
    sub.add_parser("check")
    show = sub.add_parser("show")
    show.add_argument("name")
    a = p.parse_args()
    ragas = load()

    if a.cmd == "recommend":
        for i, r in enumerate(recommend(ragas, a.prahar, a.rasa, a.prakriti, a.ritu, a.k), 1):
            print(f"{i}. {r['raga']}  (score {r['score']})")
            for w in r["matched"]:
                print(f"     {w}")
    elif a.cmd == "check":
        flags = check(ragas)
        for f in flags:
            print(f"{f['raga']:<22} {f['thaat']:<9} {f['issue']}: {f['detail']}")
        print(f"\n{len({f['raga'] for f in flags})} of {len(ragas)} ragas flagged for review")
    elif a.cmd == "show":
        hit = [r for r in ragas if r["raga"].lower() == a.name.lower()]
        print(json.dumps(hit[0], ensure_ascii=False, indent=2) if hit else "not found")


if __name__ == "__main__":
    main()
