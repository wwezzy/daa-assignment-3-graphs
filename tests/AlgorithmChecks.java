import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/** Direct route-helper calls and a reproducible algorithm-only benchmark. */
public final class AlgorithmChecks {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void routes() {
        int[][] edges = {{0,1,3},{0,2,8},{1,2,-7},{2,3,4}};
        Map<String,Object> input = Map.of("n", 5, "source", 0, "edges", rows(edges));
        Map<String,Object> result = Algorithms.dag(input);
        Long[] d = (Long[]) result.get("distance");
        int[] p = (int[]) result.get("parent_edge");
        List<Map<String,Object>> calls = new ArrayList<>();
        for (int target : new int[]{3, 0, 4}) {
            List<Integer> route = Algorithms.reconstructRoute(0, target, edges, d, p);
            List<Integer> expected = target == 3 ? List.of(0,1,2,3)
                    : target == 0 ? List.of(0) : List.of();
            require(route.equals(expected), "route " + target);
            calls.add(routeRecord("example", target, route, edges, d, p));
        }
        int[][] tied = {{0,1,2},{0,1,2},{0,2,1},{2,1,1},{1,3,-1},{2,3,0}};
        result = Algorithms.dag(Map.of("n", 4, "source", 0, "edges", rows(tied)));
        d = (Long[]) result.get("distance");
        p = (int[]) result.get("parent_edge");
        List<Integer> route = Algorithms.reconstructRoute(0, 3, tied, d, p);
        require(d[3] == 1L, "tied route cost");
        calls.add(routeRecord("tied_parallel", 3, route, tied, d, p));
        System.out.println(Json.write(Map.of("route_calls", calls, "deep_route", deepRoute())));
    }

    private static Map<String, Object> deepRoute() {
        int n = 100000;
        int[][] edges = new int[n - 1][3];
        for (int v = 0; v < n - 1; v++) edges[v] = new int[]{v, v + 1, -1000000000};
        Map<String, Object> result = Algorithms.dag(
                Map.of("n", n, "source", 0, "edges", rows(edges)));
        Long[] distance = (Long[]) result.get("distance");
        int[] parentEdge = (int[]) result.get("parent_edge");
        List<Integer> route = Algorithms.reconstructRoute(0, n - 1, edges, distance, parentEdge);
        require(route.size() == n, "deep route length");
        long total = 0;
        for (int i = 0; i < n; i++) {
            require(route.get(i) == i, "deep route vertex " + i);
            if (i > 0) {
                int id = parentEdge[i];
                require(id == i - 1 && edges[id][0] == i - 1 && edges[id][1] == i, "deep edge direction");
                total += edges[id][2];
            }
        }
        require(total == distance[n - 1], "deep route total");
        return Map.of("n", n, "target", n - 1, "route_length", route.size(),
                "first", route.get(0), "last", route.get(n - 1), "distance", total);
    }

    private static Map<String,Object> routeRecord(String graph, int target, List<Integer> route,
                                                   int[][] edges, Long[] d, int[] p) {
        List<Integer> ids = new ArrayList<>();
        long cost = 0;
        for (int i = 1; i < route.size(); i++) {
            int id = p[route.get(i)];
            require(edges[id][0] == route.get(i - 1) && edges[id][1] == route.get(i), "direction");
            ids.add(id);
            cost += (long) edges[id][2];
        }
        if (!route.isEmpty()) require(cost == d[target], "route weight");
        Map<String,Object> record = new LinkedHashMap<>();
        record.put("graph", graph);
        record.put("target", target);
        record.put("vertices", route);
        record.put("edge_ids", ids);
        record.put("distance", d[target]);
        return record;
    }

    private static List<List<Integer>> rows(int[][] edges) {
        List<List<Integer>> rows = new ArrayList<>();
        for (int[] e : edges) rows.add(List.of(e[0], e[1], e[2]));
        return rows;
    }

    @SuppressWarnings("unchecked")
    private static void validate(int n, int[][] edges, Map<String,Object> result) {
        require(((Number) result.get("cost")).longValue() == n - 1L, "known optimum");
        require(((Number) result.get("components")).intValue() == 1, "component count");
        List<Integer> ids = (List<Integer>) result.get("edge_ids");
        require(ids.size() == n - 1, "forest edge count");
        // Independent witness check by traversing the selected subgraph.
        List<Integer>[] graph = new ArrayList[n];
        for (int i = 0; i < n; i++) graph[i] = new ArrayList<>();
        boolean[] used = new boolean[edges.length];
        long sum = 0;
        for (int id : ids) {
            require(id >= 0 && id < edges.length && !used[id], "edge identity");
            used[id] = true;
            int[] e = edges[id];
            require(e[0] != e[1], "self-loop");
            graph[e[0]].add(e[1]);
            graph[e[1]].add(e[0]);
            sum += e[2];
        }
        boolean[] seen = new boolean[n];
        int[] stack = new int[n];
        int top = 0, count = 1;
        seen[0] = true;
        while (top >= 0) {
            int u = stack[top--];
            for (int v : graph[u]) if (!seen[v]) {
                seen[v] = true;
                stack[++top] = v;
                count++;
            }
        }
        require(count == n && sum == n - 1L, "spanning tree witness");
    }

    private static void benchmark() {
        List<Map<String,Object>> records = new ArrayList<>();
        for (int n : new int[]{1000, 10000, 50000}) {
            long seed = 406L + n;
            Random random = new Random(seed);
            int[][] edges = new int[4 * n][3];
            int index = 0;
            for (int v = 1; v < n; v++) edges[index++] = new int[]{v - 1, v, 1};
            while (index < edges.length) {
                edges[index++] = new int[]{random.nextInt(n), random.nextInt(n), 2 + random.nextInt(999)};
            }
            validate(n, edges, Algorithms.kruskalCore(n, edges));
            validate(n, edges, Algorithms.primCore(n, edges));
            for (int i = 0; i < 10; i++) {
                Algorithms.kruskalCore(n, edges);
                Algorithms.primCore(n, edges);
            }
            long[] kruskal = new long[7], prim = new long[7];
            for (int i = 0; i < 7; i++) {
                // Alternate first method to reduce fixed ordering bias.
                for (int j = 0; j < 2; j++) {
                    boolean useKruskal = (i + j) % 2 == 0;
                    long start = System.nanoTime();
                    Map<String,Object> answer = useKruskal
                            ? Algorithms.kruskalCore(n, edges) : Algorithms.primCore(n, edges);
                    long elapsed = System.nanoTime() - start;
                    (useKruskal ? kruskal : prim)[i] = elapsed;
                    validate(n, edges, answer); // Validation outside timed interval.
                }
            }
            Map<String,Object> r = new LinkedHashMap<>();
            r.put("n", n);
            r.put("m", edges.length);
            r.put("seed", seed);
            r.put("kruskal_ns", kruskal);
            r.put("prim_ns", prim);
            long[] sorted = kruskal.clone();
            Arrays.sort(sorted);
            r.put("kruskal_median_ns", sorted[3]);
            sorted = prim.clone();
            Arrays.sort(sorted);
            r.put("prim_median_ns", sorted[3]);
            records.add(r);
        }
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("benchmark", records);
        metadata.put("java", System.getProperty("java.runtime.version"));
        metadata.put("vendor", System.getProperty("java.vendor"));
        metadata.put("vm", System.getProperty("java.vm.name"));
        metadata.put("os", System.getProperty("os.name"));
        metadata.put("os_version", System.getProperty("os.version"));
        metadata.put("arch", System.getProperty("os.arch"));
        metadata.put("cpu_identifier", System.getenv().getOrDefault("PROCESSOR_IDENTIFIER", "unavailable"));
        metadata.put("processors", Runtime.getRuntime().availableProcessors());
        metadata.put("max_heap_bytes", Runtime.getRuntime().maxMemory());
        metadata.put("timer", "System.nanoTime");
        metadata.put("warmup_calls_per_method_per_size", 10);
        metadata.put("trials_per_method_per_size", 7);
        metadata.put("timing_includes", List.of("sorting or adjacency construction", "algorithm", "result allocation"));
        metadata.put("timing_excludes", List.of("compilation", "graph generation", "JSON parsing", "input/output", "validation"));
        System.out.println(Json.write(metadata));
    }

    public static void main(String[] args) {
        if (args.length > 0 && args[0].equals("benchmark")) benchmark();
        else routes();
    }
}
