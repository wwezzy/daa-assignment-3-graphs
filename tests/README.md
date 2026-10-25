# Tests

I keep the inputs, expected answers and actual outputs in this folder. The full test run is:

```text
python tests/run_all.py
```

It needs Python 3.12+ and JDK 17+. The script uses Java from `PATH` or `JAVA_HOME` and keeps temporary files in `.build/test-tmp/`.

## What I checked

- 36 public cases and their repeated batch.
- 44 named boundary cases and 720 random cases with seed `20261020`.
- All 512 directed graphs on three vertices, including loops, for both SCC and topo: 1,024 cases.
- The same 1,788 own requests twice in one process, with a ping between them: 3,577 answers.
- 13 examples that accept a different valid answer or reject an invalid one.
- 13 large requests, each with 100,000 vertices and 250,000 edges or union operations.
- Route reconstruction for the source, a reachable target, an unreachable target, tied/parallel edges and a 100,000-vertex chain.

The saved run passed these checks. The supplied tool tests also passed; four optional C++/C# transport tests skipped because those runtimes were unavailable locally. The solution itself uses Java.

## Expected answers

I calculate the small-case answers separately from the Java algorithms:

- For DSU, I rebuild the graph after each connection and count groups by traversal.
- For minimum forests, I enumerate the subsets with `n-c` edges and check connectivity and cost.
- For SCC and cycle checks, I use all-pairs reachability.
- For DAG distances, I use Bellman-Ford after checking the whole graph for cycles.

Then I use the template's validator to check the returned edges, labels, ordering and parent paths. This allows different correct answers when the result is not unique. The invalid examples include repeated forest IDs, a selected loop, merged SCCs, duplicate condensation edges, reversed prerequisites and wrong parent-edge IDs.

## Large cases

The large tests include chains, cycles, stars, parallel edges, balanced DSU merges and a graph with 250,000 distinct condensation edges. One DAG case has an isolated source and a cycle in another component.

The expected values follow from these graph shapes. A chain of equal-weight edges needs `n-1` edges in its spanning tree. In a directed negative chain, vertex `v` has distance `-v*10^9`. Adding a back edge closes the chain into one SCC. A graph whose edges always point to larger vertex IDs has only singleton SCCs.

The three `.gz` files contain matching input, expected and actual lines. Python's standard `gzip` module can read them. `verify.py` regenerates the files.

## Files

| File | Contents |
|---|---|
| `cases.jsonl` | Small input requests |
| `expected.jsonl` | Expected values |
| `actual.jsonl` | Actual Java answers |
| `case_reasons.json` | Case names and reasons for the expected answers |
| `witness_checks.json` | Alternative valid and invalid answers |
| `scale_inputs.jsonl.gz` | Full-limit inputs |
| `scale_expected.jsonl.gz` | Full-limit expected values |
| `scale_actual.jsonl.gz` | Full-limit actual answers |
| `verification.json` | Test counts and large-case results |
| `setup_results.txt`, `public_results.txt`, `tool_tests_results.txt`, `own_results.txt` | Saved command output |
| `route_results.json` | Route-helper results and selected edge IDs |
| `benchmark_results.json` | Raw timings, medians, seeds and machine details |
| `run_manifest.json` | Commands, run date and source checksums |

`expected.jsonl` stores the quantities needed to check a result. For example, the forest reference gives the optimum cost and component count; it does not choose one particular set of edges. The actual returned edges are in `actual.jsonl`.

## Run individual checks

```text
python tests/verify.py
javac --release 17 -encoding UTF-8 -cp .build/Java -d .build/Java tests/AlgorithmChecks.java
java -Xmx384m -cp .build/Java AlgorithmChecks
java -Xmx384m -cp .build/Java AlgorithmChecks benchmark
```

The Java commands need the compiled solution, which `tools/run.py --setup` creates.

## Kruskal and Prim

I use the same graph for both methods at `n=1000,10000,50000`, with `m=4n` and Java seeds `1406,10406,50406`. A chain with weight 1 guarantees a connected graph and a known optimum of `n-1`. Extra edges have weight at least 2.

For each size I run ten warm-ups and seven timed calls per method, alternating which method goes first. I check the selected edges and total cost outside the timed part. Timing includes the core algorithm and result construction, but excludes compilation, input generation, parsing and I/O. The timing table and discussion are in [ANALYSIS.md](../ANALYSIS.md).
