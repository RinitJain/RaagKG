# Changelog

## 1.0.0 (2026-10-30)

First public release: 101 ragas, 12 attributes each.

Corrections made to the source sheet when building `data/` (the sheet is kept
unchanged in `data/raw/`, and `scripts/build_release.py` applies these steps):

- **Miyan Ki Malhar**: values from the Jaati column onwards had shifted one
  column to the right. They are realigned: prahar "Mid Night (Rainy Season)",
  jaati Sampurna-Sampurna, rasa Gambhir and Shanti. The temperament value was
  lost in the shift and is left empty.
- **Lankadahan Sarang**: parent scale recorded as "Sarang", which is not one of
  the ten thaats; set to Kafi.
- **Basant, Paraj**: sharp Ma written `m'` in aroha, avaroha and pakad,
  changed to `M'` to match the rest of the catalogue.
- **Related ragas**: four names written differently from their catalogue
  entries are linked to them: Sohni to Sohani, Hameer to Hamir, Suha to Suha
  Kanada, Shahana to Shahana Kanada. Matching ignores letter case
  (Miyan ki Malhar = Miyan Ki Malhar).
