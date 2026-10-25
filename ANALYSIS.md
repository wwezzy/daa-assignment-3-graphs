# DAA Assignment 3: Analysis

**Kuat Allazhar**

I use Java 17 for all six algorithms. My solution keeps the supplied JSON Lines adapters and has no external dependencies. I use `long` for costs and finite distances, `Long[]` for nullable distances, and original zero-based input positions for edge IDs.

## Running the project

Run these commands from the repository root with Python 3.12+ and JDK 17+ on `PATH`:

```text
python tools/run.py --setup
python tools/run.py --check
python tests/run_all.py
```

The first command verifies launch and `ping`. The second runs the 36 public cases and repeats their complete batch in one process. My `run_all.py` also checks the supplied tools, runs the independent tests, calls the route helper directly and records the benchmark. It accepts a JDK through `JAVA_HOME` if Java is not on `PATH`. Temporary test files stay under the ignored `.build/test-tmp/` directory.

To run my saved requests without automatic comparison:

```text
python tools/run.py --input tests/cases.jsonl
```

Individual commands for my own checks are:

```text
python tests/verify.py
javac --release 17 -encoding UTF-8 -cp .build/Java -d .build/Java tests/AlgorithmChecks.java
java -Xmx384m -cp .build/Java AlgorithmChecks
java -Xmx384m -cp .build/Java AlgorithmChecks benchmark
```

For a direct build and launch without the Python launcher:

```text
javac --release 17 -encoding UTF-8 -d .build/Java src/Java/Algorithms.java src/Java/Input.java src/Java/Json.java src/Java/Main.java
java -Xmx384m -cp .build/Java Main
```

`Main` reads one UTF-8 JSON object per line and writes exactly one result object per line. It prints no prompts, timing output or debugging messages. The direct test and benchmark program is a separate class outside `src/Java/`.

## Implementation notes

I keep `Input.java`, `Json.java` and `Main.java` unchanged. All algorithm fields belong to a new request. I do not retain a DSU, heap, graph, color array or distance array in mutable static state. The input edge array is not sorted or modified. The mixed test sends 1,788 cases, a `ping`, and the same 1,788 cases again in one process.

Adjacency rows contain original edge IDs. I count degrees, allocate each row once and fill it. Directed edges occupy one adjacency entry, while an undirected graph uses two. This takes `O(n+m)` time and memory, including loops and parallel edges.

My iterative DFS stores the current path in `stack` and the next unexplored adjacency position in `nextIndex[u]`. I mark a vertex active when I push it and finished after its last outgoing edge. Thus every suspended DFS call retains its progress, every edge cursor advances once, and finish order matches recursive DFS. I do not rescan all neighbors on each return. DFS and DSU `find` never use the Java call stack. The full-limit tests include chains and cycles of 100,000 vertices.

## 1. Disjoint-set union

**Steps.** I initialize `parent[v]=v`, `size[v]=1`, `components=n`, and `largest=1` for `n>0`, or zero otherwise. `find(v)` first finds the root, then follows the old path again and redirects every visited vertex to that root. I save the old parent before overwriting it. `union` attaches the smaller root to the larger root, adds the sizes, decreases `components` and updates `largest`. Equal roots cause no merge. I record `[components, largest]` after each operation, without an initial output state.

**Invariant.** Parent pointers form rooted trees. Two vertices have the same root exactly when the processed connections put them in the same component. Only a root's `size` is meaningful. `components` counts the roots, and `largest` is the maximum component size.

**Correctness.** Initially, each singleton component is correct. Path compression changes the route to a root without changing group membership. A connection between different roots merges exactly those two components. A connection within one component leaves the partition unchanged. The size and counter updates preserve the invariant, so induction over the operations proves every reported state. Each parent walk reaches a root, and the finite operation loop terminates.

**Boundaries.** Empty input returns `states=[]`. Self-unions and repeated unions keep the same partition and statistics. Union by size uses actual component sizes, rather than ranks. A parent pointer is an internal DSU link and need not be an input graph edge.

**Complexity.** For `q` operations, time is `O(n+q*alpha(n))` amortized. Memory is `O(n+q)`, including all output states. The amortized bound describes a sequence of operations, rather than a worst-case constant time for each individual call.

## 2. Kruskal minimum spanning forest

**Steps.** I sort an array of original edge IDs by weight, with the ID as a deterministic tie-breaker. I start an empty forest and a singleton DSU. I accept an edge when `union(u,v)` returns true, add its weight to a `long` total and save its original ID. I scan all edges, so the final DSU count also includes isolated vertices.

**Invariant.** Selected edges form a forest whose components are exactly the DSU components. Some minimum spanning forest contains all edges selected so far.

**Correctness.** An edge within one DSU component would create a cycle, so I reject it. For an accepted edge, consider the cut separating one current DSU component from the rest of its original connected component. No strictly lighter edge across this cut can remain unprocessed. Any earlier edge across it would already have merged two current components. The current edge is therefore a minimum crossing edge. The cut exchange argument permits adding it to an optimum forest, including equal and negative weights. At the end, every input edge has both endpoints connected in the selected forest, so it spans each original component. The invariant then proves minimum total cost. The sorted scan is finite.

**Boundaries.** I reject all self-loops, even negative ones. Parallel edges keep distinct original IDs. Empty input returns cost zero, no edge IDs and zero components. A graph with `c` components produces exactly `n-c` selected edges. Negative totals and sums beyond 32 bits are valid.

**Complexity.** Time is `O(n+m log(m+1))`. Memory is `O(n+m)`, including sorting storage, DSU and selected IDs.

## 3. Prim minimum spanning forest

**Steps.** I build undirected adjacency lists and use a priority queue ordered by weight and then original ID. I start at each unvisited vertex in turn and count a new component. I add its incident edges to the queue. After removing an edge, I skip it if both endpoints are already visited. Otherwise I accept it, visit its unvisited endpoint and enqueue its outgoing edges that still reach an unvisited endpoint. An empty queue finishes that component, and the outer loop restarts elsewhere.

**Invariant.** In the current original component, the selected edges connect the visited vertices as a tree. Every edge crossing from visited to unvisited vertices is represented in the heap. Some heap entries may have become stale because both endpoints are now visited.

**Correctness.** Every inserted edge has a visited endpoint, and visited status never reverses. A nonstale removed edge therefore has exactly one unvisited endpoint and cannot create a cycle. Once I skip stale entries, the minimum heap edge is a minimum crossing edge, which is safe by the cut exchange argument. Queue exhaustion means no input edge leaves the visited set, so this original component is complete. Restarting handles every component and each isolate. Each vertex becomes visited once, and only finitely many edges enter the queue. This proves termination and an optimum spanning forest.

**Boundaries.** Loops are stale immediately and never enter the forest. Parallel edges, tied weights and negative weights are valid. An isolated start contributes one component without selecting an edge. Empty input starts none. The selected IDs may differ from Kruskal's while the cost and component count agree.

**Complexity.** I use a lazy heap containing up to `O(m)` entries, rather than an indexed heap with decrease-key. Time is `O(n+m log(m+1))`, and memory is `O(n+m)` including the output.

## 4. Kosaraju strongly connected components

**Steps.** I build the original adjacency and its transpose. The first DFS pass records vertices on exit. In decreasing finish order, I traverse the transpose from each still-unassigned vertex and give that traversal one new label. Finally I scan all original edges and emit every distinct ordered pair of different component labels. I pack the two labels into a `long` and use a hash set to deduplicate pairs.

**Invariant.** The first stack records genuine DFS finish order. During the second pass, completed labels identify whole SCCs, and each new traversal assigns exactly one previously unassigned SCC.

**Correctness.** The condensation is acyclic: a directed cycle among distinct SCCs would make them mutually reachable. For an edge from SCC C to a different SCC D, C has the greater maximum first-pass finish time. Consequently, the highest-finish remaining SCC has no incoming edge from a remaining SCC in the original graph. A transpose search from it cannot leave to another unassigned SCC. Reversing edges preserves mutual reachability within an SCC, so that search reaches all and only its vertices. Repeating proves the labels. The final scan includes every cross-component pair, omits internal edges and removes duplicates. Both traversals and the edge scan terminate.

**Boundaries.** Isolates receive separate labels. Loops and duplicate edges do not change membership. Empty input returns empty `component` and `condensation` arrays. Labels need not match the reference numerically, so my tests compare partitions and exact condensation under the returned labels.

**Complexity.** Expected time is `O(n+m)` with hash-based deduplication. Memory is `O(n+m)`, including the transpose, explicit stacks, labels and condensation.

## 5. DFS topological ordering

**Steps.** I visit every component using three colors: unvisited, active and finished. An edge to an active vertex reports a cycle immediately. If no cycle exists, I reverse DFS finish order and return every vertex once.

**Invariant.** Active vertices form the current DFS path. A finished vertex has no unexplored outgoing edges. The finish array contains each completed vertex once.

**Correctness.** An edge to an active ancestor closes a directed cycle. Conversely, DFS must encounter an active edge while exploring a directed cycle, so the cycle test is complete. In an acyclic graph, every edge `u->v` finishes `v` before `u`, whether DFS discovers `v` through that edge or `v` was already finished. Reversing finish order therefore places `u` before `v`. The outer loop includes isolates and disconnected components. Every cursor and color advances finitely, proving termination.

**Boundaries.** An edge to a finished vertex alone is not a cycle. A self-loop is a cycle. Any cycle, including in a later component, returns `acyclic=false` and `order=[]`. For `n=0`, I return `acyclic=true` and an empty order. Duplicate edges are harmless.

**Complexity.** Time and memory are `O(n+m)`, including adjacency, traversal progress and the returned order.

## 6. Shortest paths in a DAG

**Steps.** I first check the whole graph for cycles with the same three-state DFS. A cycle returns `acyclic=false` and two empty arrays. Otherwise I initialize every distance to `null`, every parent edge to `-1`, and the source distance to zero. I process vertices in topological order and relax outgoing edges only from reachable vertices. A strictly shorter route updates both the distance and the original incoming edge ID.

**Invariant.** Before processing a vertex, every predecessor has been processed and every recorded finite distance is the weight of a valid source path. The vertex's distance is final when I relax its outgoing edges.

**Correctness.** The source's empty path has cost zero. By topological induction, all possible last edges of a path into a vertex come from already processed predecessors. Relaxing those edges selects the minimum source-path cost before the vertex is processed. Unreachable vertices receive no candidate and remain `null`. An updated parent edge ends at its vertex and connects it to an already reachable predecessor, so following parents reaches the source. Negative weights do not invalidate this argument because a DAG has no cycles. DFS and each relaxation scan are finite.

**Boundaries.** I reject cycles even when they are unreachable from the source. A source or unreachable vertex has parent `-1`. Finite distance `-1` is valid and differs from `null`. Parallel and tied edges can produce several valid parent arrays. I preserve edge IDs through adjacency construction. With at most 99,999 edges on a path and absolute edge weight at most `10^9`, finite path magnitudes stay below `10^14`, safely within `long`.

**Complexity.** Time and memory are `O(n+m)`, including cycle detection, adjacency and output arrays.

### Route reconstruction

`reconstructRoute(source,target,edges,distance,parentEdge)` uses arrays from a successful DAG result for the same graph and source. It returns vertices from source to target, `[source]` for the source, and an empty list for an unreachable target. It follows original parent-edge IDs backward, checks their direction, then reverses the vertex list. Each predecessor lies earlier in the DAG order, so the process reaches the source. A route with `L` vertices takes `O(L)` time and output space.

These are the actual direct calls recorded in `tests/route_results.json`. For the example edges `[[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]`, the source is 0 and `n=5`:

| Target | Returned vertices | Selected original edge IDs | Cost |
|---:|---|---|---|
| 3 | `[0,1,2,3]` | `[0,2,3]` | `3-7+4=0` |
| 0 | `[0]` | `[]` | `0` |
| 4 | `[]` | `[]` | unreachable |

For tied/parallel edges `[[0,1,2],[0,1,2],[0,2,1],[2,1,1],[1,3,-1],[2,3,0]]`, the call for target 3 returned `[0,2,3]`, selected IDs `[2,5]`, and cost `1+0=1`. Routes through either parallel `0->1` edge and then `1->3` also have cost 1. My assertions check actual edge directions and the sum rather than assuming one tie winner. A separate 100,000-vertex negative chain reconstructs all 100,000 vertices and verifies every selected edge and total `-99,999,000,000,000`.

## Tests

The recorded run completed on 25 October 2026 using Python 3.12.10 and Microsoft OpenJDK 17.0.20.1. `tests/run_manifest.json` records exact commands, times and SHA-256 hashes of the executed algorithm, adapter and test sources.

| Check | Recorded result |
|---|---|
| Setup and preserved ping | passed |
| Public algorithm cases | 36 passed |
| Two complete public batches in one process | passed |
| Supplied tool/transport unit tests | 16 tests, no failures, 4 optional-runtime skips |
| Named independent boundary cases | 44 passed |
| Seeded random cases | 720 passed |
| Exhaustive directed cases | 1,024 passed: SCC and topo on all 512 directed three-vertex graphs |
| Mixed persistent-process requests | 3,577 results checked |
| Alternative/invalid witness demonstrations | 13 passed |
| Full-limit cases | 13 passed, each at `n=100000` and `m` or `q=250000` |
| Direct route-helper checks | reachable, source, unreachable, tied/parallel and deep route passed |

My tiny-case expected answers use methods independent of the submitted algorithms. Connectivity is recomputed by graph traversal, forest costs come from exhaustive enumeration of all `n-c` edge subsets, and SCCs and cycle detection use all-pairs reachability. DAG distances use Bellman-Ford relaxation. Random seed is `20261020`. I reuse the supplied semantic validator to check witnesses against these independently justified reference values.

The 44 named cases explicitly cover empty inputs, isolates, repeated/self unions, negative loops, parallel/tied edges, unsorted original IDs, large positive and negative totals, edges to finished DFS vertices, nonzero sources, unreachable vertices and unreachable cycles. The exhaustive suite includes every subset of the nine possible directed edges on three vertices, including loops.

For full limits, chains justify the expected distances and component memberships directly. Equal-weight undirected chains cost `(n-1)*10^9`. Negative DAG chains give distance `-v*10^9`. A back edge closes a deep cycle; a separate cycle still invalidates a DAG request with isolated source 0. Negative stars with expensive parallel edges exercise Prim's large lazy heap. A forward-only graph with 250,000 distinct edges exercises large condensation output. Balanced unions exercise longer DSU parent paths before repeated searches. Inputs, expected values and actual answers for all large cases are saved in gzip-compressed JSON Lines.

For non-unique answers, I demonstrate acceptance of a different optimum forest, different SCC labels, a different valid topological order and tied/parallel parent edges. I also demonstrate rejection of duplicate forest IDs, a loop witness, incorrect SCC merging, duplicate condensation pairs, reversed precedence and wrong incoming edge IDs. These checks compare validity, rather than an exact serialized answer.

The tests establish the recorded results. The correctness arguments and operation counts above establish the algorithmic claims; timing measurements alone do not prove them.

## Kruskal and Prim timings

I compare both methods on the same graph at each of three sizes. `tests/AlgorithmChecks.java` contains the exact generator. With Java `Random(406+n)`, I first add the chain `[v-1,v,1]` for `v=1..n-1`, then random endpoint edges of weight `2+nextInt(999)` until `m=4n`. The seeds are 1406, 10406 and 50406. Loops and parallel edges may occur. Every connecting edge has weight at least 1, and the chain attains `n-1`, so the optimum is independently known.

Before timing, I validate both results. At each size I perform ten untimed warm-up calls per method, followed by seven measurements per method. I alternate which method runs first. Outside every measured interval, I verify original ID uniqueness, edge count, total cost and connectivity of the selected graph by traversal. Connectedness plus exactly `n-1` edges proves the returned subgraph is a tree.

**Environment.** Windows 11, amd64, CPU identifier `Intel64 Family 6 Model 186 Stepping 2, GenuineIntel`, 20 available logical processors, Microsoft OpenJDK `17.0.20.1+1-LTS`, OpenJDK 64-Bit Server VM, maximum Java heap 384 MiB. The benchmark uses one process and one algorithm thread.

**Timing boundary.** I use `System.nanoTime()`. The interval starts immediately before `kruskalCore(n,edges)` or `primCore(n,edges)` and ends when its complete result returns. Sorting/DSU or adjacency/heap work, allocation and result construction are included. Compilation, graph generation, parsing, input conversion, console I/O and validation are excluded for both methods. Any GC pause inside an interval remains included. Raw nanosecond trials and runtime metadata are in `tests/benchmark_results.json`.

| n | m | Kruskal trials, ms | Median, ms | Prim trials, ms | Median, ms |
|---:|---:|---|---:|---|---:|
| 1000 | 4000 | 0.9946, 1.3867, 1.4699, 1.0517, 1.0731, 1.1261, 1.1143 | 1.1143 | 0.9797, 0.8615, 0.8981, 0.8781, 0.8982, 0.8718, 0.8524 | 0.8781 |
| 10000 | 40000 | 7.8997, 7.8573, 7.6919, 7.3159, 7.2557, 7.9728, 7.9507 | 7.8573 | 13.2254, 14.1095, 12.1161, 12.2575, 12.5899, 14.0595, 13.4315 | 13.2254 |
| 50000 | 200000 | 55.9329, 48.6008, 48.6799, 43.9331, 42.6319, 53.1699, 45.6303 | 48.6008 | 108.1126, 99.4530, 106.5390, 95.4284, 100.9110, 96.9559, 102.9170 | 100.9110 |

**Observations.** Prim has the lower median at the smallest size. Kruskal has the lower median at the two larger sizes. Both methods return the same known optimum and component count. The work in this lazy Prim implementation includes heap entries that can later become stale, while Kruskal sorts all edge IDs before its DSU scan.

**Limits of the experiment.** These measurements describe this graph family, runtime and machine. The fixed `m/n` ratio and cheap chain do not represent all sparse or dense graphs. JIT compilation, allocation, GC and system load affect the constants, and ten warm-ups do not guarantee complete stabilization. I do not infer a universal winner or an asymptotic bound from three measurements of input size.

## Sources

- I used the official [assignment template and contracts](https://github.com/RZhaniya/daa-assignment-3-graphs) at commit `76c1d91daa90ceadcb225f5408d54d4bfcf397f9`. The JSON adapters, launcher, public cases and semantic validator come from that template and remain unchanged.
- I used the supplied Lecture 6 on DSU and minimum spanning trees and Lecture 7 on SCCs, topological ordering and DAG shortest paths for the course definitions and algorithm explanations.
- I used OpenAI Codex to help me understand the main ideas behind the algorithms.
