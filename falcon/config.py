"""Paths, IRIs and regulatory constants used across the project."""
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT = PACKAGE_DIR.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

ONTOLOGY_IRI = "http://www.semanticweb.org/anushgoel/ontologies/2026/falcon.owl"
INFERRED_IRI = "http://www.semanticweb.org/anushgoel/ontologies/2026/falcon-inferred.owl"
NAMESPACE = ONTOLOGY_IRI + "#"
SPARQL_PREFIX = "PREFIX falcon: <%s>\n" % NAMESPACE

PROJECT = "FALCON: Food Allergen and Label Compliance Ontology"

GLUTEN_FREE_LIMIT_PPM = 20.0      # FDA 21 CFR 101.91, EU Reg. 828/2014, Health Canada
SULPHITE_LIMIT_PPM = 10.0         # US/Canada: >= 10 ppm; EU Annex II: > 10 mg/kg

JAVA_MEMORY_MB = 4000             # heap given to HermiT/Pellet
