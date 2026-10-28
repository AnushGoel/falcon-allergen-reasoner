"""
Check that Python, owlready2 and Java are ready for FALCON.

    python check_environment.py
"""
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    print("FALCON environment check")
    print("-" * 40)
    print("Python      %s on %s" % (platform.python_version(), platform.system()))
    if sys.version_info < (3, 8):
        print("FAIL  Python 3.8 or newer is required.")
        return 1
    try:
        import owlready2
    except ImportError:
        print("FAIL  owlready2 is missing. Run:  pip install -r requirements.txt")
        return 1
    print("owlready2   %s" % getattr(owlready2, "VERSION", "installed"))

    from falcon.owl_reasoning import MIN_JAVA_FOR_PELLET, configure_java, explain_java_error
    info = configure_java()
    if not info["java"]:
        print("FAIL  Java not found. Install Java 25 with:  winget install EclipseAdoptium.Temurin.25.JDK")
        print("      then open a new terminal, or set FALCON_JAVA to the full path of java.exe.")
        return 1
    print("Java        %s  (%s, found via %s)" % (info["version"], info["java"], info["source"]))
    if info["major"] and info["major"] < MIN_JAVA_FOR_PELLET:
        print("NOTE  Pellet in owlready2 0.51+ needs Java %d; HermiT works with this Java. Install Java %d with:"
              % (MIN_JAVA_FOR_PELLET, MIN_JAVA_FOR_PELLET))
        print("      winget install EclipseAdoptium.Temurin.25.JDK   (FALCON picks the newest Java automatically)")

    world = owlready2.World()
    onto = world.get_ontology("http://example.org/falcon-check.owl")
    with onto:
        class Product(owlready2.Thing):
            pass

        class Ingredient(owlready2.Thing):
            pass

        class Allergen(owlready2.Thing):
            pass

        class hasIngredient(owlready2.ObjectProperty):
            pass

        class triggersAllergen(owlready2.ObjectProperty):
            pass

        class containsAllergen(owlready2.ObjectProperty):
            pass

        owlready2.Imp().set_as_rule(
            "Product(?p), hasIngredient(?p, ?i), triggersAllergen(?i, ?a) -> containsAllergen(?p, ?a)")
        milk = Allergen("milk")
        whey = Ingredient("whey", triggersAllergen=[milk])
        bar = Product("bar", hasIngredient=[whey])
    try:
        owlready2.sync_reasoner_pellet(world, infer_property_values=True, debug=0)
        passed = milk in bar.containsAllergen
    except Exception as exc:
        print("FAIL  Pellet could not run: %s" % explain_java_error(str(exc))[:600])
        return 1
    print("Pellet+SWRL %s" % ("PASS" if passed else "FAIL (rule did not fire)"))
    print("-" * 40)
    print("Ready. Next:  python run_all.py" if passed else "Something is wrong; see README troubleshooting.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
