# DAA Assignment 3

**Kuat Allazhar**

Design and Analysis of Algorithms

I used Java 17 for this assignment. The project covers connectivity, minimum spanning forests, strongly connected components, topological sorting and shortest paths in a DAG.

## Algorithms

| Task | Implementation |
|---|---|
| `dsu` | Path compression and union by size |
| `kruskal` | Sorting edges by weight and merging components with DSU |
| `prim` | Adjacency lists and a priority queue, with a new start for each component |
| `scc` | Kosaraju with two DFS passes and a transposed graph |
| `topo` | Three-state DFS and reversed finish order |
| `dag` | Relaxing edges in topological order and reconstructing a route |

The code is in [Algorithms.java](src/Java/Algorithms.java). I use `long` for costs and distances, and explicit stacks for DFS. Edge IDs keep their original positions in the input.

## Run

The project needs JDK 17+ and Python 3.12+. Java should be on `PATH`, or `JAVA_HOME` should point to the JDK.

```text
python tools/run.py --setup
python tools/run.py --check
```

To run my own tests, route checks and timing comparison:

```text
python tests/run_all.py
```

To run the program on a saved input file:

```text
python tools/run.py --input tests/cases.jsonl
```

## Example

The program reads one JSON request per line and returns one JSON result per line.

Input:

```json
{"task":"dsu","n":4,"operations":[[0,1],[1,2],[0,2],[3,3]]}
```

Output:

```json
{"states":[[3,2],[2,3],[2,3],[2,3]]}
```

## Tests and analysis

The saved run passed all 36 public cases, 1,788 own test cases and 13 large cases with 100,000 vertices. I also compared Kruskal and Prim at three graph sizes.

- [ANALYSIS.md](ANALYSIS.md): explanations, correctness, complexity and timings.
- [tests/README.md](tests/README.md): test commands, expected answers and saved results.
- [README_RU.md](README_RU.md): Russian version.
