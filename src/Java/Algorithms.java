import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

/**
 * Graph algorithms for independent JSON Lines requests.
 * The supplied adapters handle input conversion and output serialization.
 * Totals use long, and DFS uses explicit stacks for deep graphs.
 */
public final class Algorithms {
    /** Only roots have a meaningful size. A DSU parent is not a graph edge. */
    static final class UnionFind {
        final int[] parent;
        final int[] size;
        int components;
        int largest;

        UnionFind(int n) {
            parent = new int[n];
            size = new int[n];
            components = n;
            largest = n == 0 ? 0 : 1;
            for (int v = 0; v < n; v++) {
                parent[v] = v;
                size[v] = 1;
            }
        }

        int find(int v) {
            int root = v;
            while (parent[root] != root) root = parent[root];
            // Second walk: point every vertex on this path straight to its root.
            while (v != root) {
                int next = parent[v];
                parent[v] = root;
                v = next;
            }
            return root;
        }

        boolean union(int u, int v) {
            int a = find(u), b = find(v);
            if (a == b) return false;
            if (size[a] < size[b]) {
                int temp = a;
                a = b;
                b = temp;
            }
            parent[b] = a;
            size[a] += size[b];
            components--;
            largest = Math.max(largest, size[a]);
            return true;
        }
    }

    /** DSU with path compression and union by size/rank; return states. */
    static Map<String, Object> dsu(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] operations = Input.operations(input);

        UnionFind sets = new UnionFind(n);
        int[][] states = new int[operations.length][2];
        for (int i = 0; i < operations.length; i++) {
            sets.union(operations[i][0], operations[i][1]);
            states[i][0] = sets.components;
            states[i][1] = sets.largest;
        }
        return Map.of("states", states);
    }

    /** Separate Kruskal implementation; return cost, edge_ids, components. */
    static Map<String, Object> kruskal(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        return kruskalCore(n, edges);
    }

    static Map<String, Object> kruskalCore(int n, int[][] edges) {
        Integer[] ids = new Integer[edges.length];
        for (int i = 0; i < ids.length; i++) ids[i] = i;
        // Sort IDs, never the original edges: witnesses must keep input IDs.
        Arrays.sort(ids, Comparator.comparingInt((Integer id) -> edges[id][2])
                .thenComparingInt(id -> id));
        UnionFind sets = new UnionFind(n);
        List<Integer> selected = new ArrayList<>();
        long cost = 0;
        for (int id : ids) {
            int[] edge = edges[id];
            if (sets.union(edge[0], edge[1])) {
                selected.add(id);
                cost += (long) edge[2];
            }
        }
        return Map.of("cost", cost, "edge_ids", selected, "components", sets.components);
    }

    /** Separate Prim implementation; restart for every unvisited component. */
    static Map<String, Object> prim(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        return primCore(n, edges);
    }

    static Map<String, Object> primCore(int n, int[][] edges) {
        int[][] adjacent = adjacency(n, edges, true, false);
        boolean[] visited = new boolean[n];
        PriorityQueue<Integer> heap = new PriorityQueue<>(
                Comparator.comparingInt((Integer id) -> edges[id][2])
                        .thenComparingInt(id -> id));
        List<Integer> selected = new ArrayList<>();
        int components = 0;
        long cost = 0;
        // Each new start is a new component, including an isolated vertex.
        for (int start = 0; start < n; start++) {
            if (visited[start]) continue;
            components++;
            visited[start] = true;
            for (int id : adjacent[start]) heap.offer(id);
            while (!heap.isEmpty()) {
                int id = heap.poll();
                int u = edges[id][0], v = edges[id][1];
                if (visited[u] && visited[v]) continue; // Stale edge or self-loop.
                int next = visited[u] ? v : u;
                visited[next] = true;
                selected.add(id);
                cost += (long) edges[id][2];
                for (int other : adjacent[next]) {
                    int a = edges[other][0], b = edges[other][1];
                    if (!(visited[a] && visited[b])) heap.offer(other);
                }
            }
        }
        return Map.of("cost", cost, "edge_ids", selected, "components", components);
    }

    /** Rows contain original edge IDs; reverse means incoming directed edges. */
    private static int[][] adjacency(int n, int[][] edges, boolean undirected, boolean reverse) {
        int[] degree = new int[n];
        for (int[] e : edges) {
            degree[reverse ? e[1] : e[0]]++;
            if (undirected) degree[e[1]]++;
        }
        int[][] result = new int[n][];
        for (int v = 0; v < n; v++) result[v] = new int[degree[v]];
        Arrays.fill(degree, 0);
        for (int id = 0; id < edges.length; id++) {
            int[] e = edges[id];
            int from = reverse ? e[1] : e[0];
            result[from][degree[from]++] = id;
            if (undirected) result[e[1]][degree[e[1]]++] = id;
        }
        return result;
    }

    /** Simulate recursive DFS frames. Return finish order, or null for a cycle. */
    private static int[] finishOrder(int n, int[][] edges, int[][] adjacent,
                                     boolean detectCycles) {
        byte[] color = new byte[n]; // 0 = unseen, 1 = active, 2 = finished.
        int[] nextIndex = new int[n]; // Where each suspended call must resume.
        int[] stack = new int[n];
        int[] finish = new int[n];
        int count = 0;
        for (int start = 0; start < n; start++) {
            if (color[start] != 0) continue;
            int top = 0;
            stack[top] = start;
            color[start] = 1;
            while (top >= 0) {
                int u = stack[top];
                if (nextIndex[u] == adjacent[u].length) {
                    color[u] = 2;
                    finish[count++] = u;
                    top--;
                    continue;
                }
                int id = adjacent[u][nextIndex[u]++];
                int v = edges[id][1];
                if (color[v] == 1 && detectCycles) return null;
                if (color[v] == 0) {
                    color[v] = 1;
                    stack[++top] = v;
                }
            }
        }
        return finish;
    }

    /** Kosaraju's two DFS passes; return component and exact condensation. */
    static Map<String, Object> scc(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int[][] outgoing = adjacency(n, edges, false, false);
        int[][] incoming = adjacency(n, edges, false, true);
        int[] finish = finishOrder(n, edges, outgoing, false);
        int[] component = new int[n];
        Arrays.fill(component, -1);
        int[] stack = new int[n];
        int label = 0;
        for (int i = n - 1; i >= 0; i--) {
            int start = finish[i];
            if (component[start] != -1) continue;
            int top = 0;
            stack[top] = start;
            component[start] = label;
            while (top >= 0) {
                int u = stack[top--];
                for (int id : incoming[u]) {
                    int v = edges[id][0];
                    if (component[v] == -1) {
                        component[v] = label; // Mark on push, preventing duplicates.
                        stack[++top] = v;
                    }
                }
            }
            label++;
        }
        Set<Long> seen = new HashSet<>();
        List<int[]> condensation = new ArrayList<>();
        for (int[] edge : edges) {
            int a = component[edge[0]], b = component[edge[1]];
            if (a == b) continue;
            long pair = ((long) a << 32) | (b & 0xffffffffL);
            if (seen.add(pair)) condensation.add(new int[]{a, b});
        }
        return Map.of("component", component, "condensation", condensation);
    }

    /** Three-state DFS and reverse finish order; return acyclic and order. */
    static Map<String, Object> topo(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int[] finish = finishOrder(n, edges, adjacency(n, edges, false, false), true);
        if (finish == null) return Map.of("acyclic", false, "order", new int[0]);
        reverse(finish);
        return Map.of("acyclic", true, "order", finish);
    }

    private static void reverse(int[] array) {
        for (int i = 0, j = array.length - 1; i < j; i++, j--) {
            int temp = array[i];
            array[i] = array[j];
            array[j] = temp;
        }
    }

    /** Whole-graph cycle check and DAG relaxation; return acyclic, distance, parent_edge. */
    static Map<String, Object> dag(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int source = Input.source(input);
        int[][] edges = Input.edges(input);

        int[][] outgoing = adjacency(n, edges, false, false);
        int[] finish = finishOrder(n, edges, outgoing, true);
        if (finish == null) {
            return Map.of("acyclic", false, "distance", new Long[0], "parent_edge", new int[0]);
        }
        Long[] distance = new Long[n]; // null means unreachable, even for negative costs.
        int[] parentEdge = new int[n];
        Arrays.fill(parentEdge, -1);
        distance[source] = 0L;
        // Decreasing finish order is topological order.
        for (int i = n - 1; i >= 0; i--) {
            int u = finish[i];
            if (distance[u] == null) continue;
            for (int id : outgoing[u]) {
                int v = edges[id][1];
                long candidate = distance[u] + (long) edges[id][2];
                if (distance[v] == null || candidate < distance[v]) {
                    distance[v] = candidate;
                    parentEdge[v] = id;
                }
            }
        }
        return Map.of("acyclic", true, "distance", distance, "parent_edge", parentEdge);
    }

    /**
     * Return source-to-target vertices, or an empty list when target is unreachable.
     * Precondition: valid vertices and arrays from a successful DAG result for the
     * same edges and source. Edge IDs, rather than predecessor vertices, identify
     * the selected routes even when input edges are parallel.
     */
    static List<Integer> reconstructRoute(int source, int target, int[][] edges,
                                           Long[] distance, int[] parentEdge) {
        if (distance[target] == null) return List.of();
        List<Integer> route = new ArrayList<>();
        int v = target;
        while (v != source) {
            route.add(v);
            int id = parentEdge[v];
            if (id < 0 || id >= edges.length || edges[id][1] != v || route.size() >= distance.length) {
                throw new IllegalArgumentException("Invalid parent-edge witness");
            }
            v = edges[id][0];
        }
        route.add(source);
        Collections.reverse(route);
        return route;
    }
}
