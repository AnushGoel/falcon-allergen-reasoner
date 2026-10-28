# Colab run 1 (28 October 2026)

Python 3.13.18, owlready2 0.51, OpenJDK 21.0.12.1, Colab CPU runtime.

* `run1_benchmark_uncapped.json`: the scalability benchmark before per-run time limits were added.
  HermiT took 5.8 s at 45 products, 20.9 s at 90, 103.2 s at 180 and 789.1 s at 360 (fitted exponent 2.36);
  the engine grew linearly (exponent 0.98, 2,880 products in 10.4 s).
* `run1_owl_results.json`: HermiT found the ontology consistent with no unsatisfiable classes. Pellet could not
  start because the Pellet bundled with owlready2 0.51 is compiled for Java 25 (class file 69) and Colab had Java 21.
  This run led to the Java 25 setup step and the HermiT fallback.
