"""Independent small-case oracles, semantic witness tests, and full-limit batches."""
import gzip
from datetime import datetime, timezone
import itertools
import json
import pathlib
import platform
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from public_validate import check
from run import build, execute


def reachable(n, edges):
    reach = [[i == j for j in range(n)] for i in range(n)]
    for u, v, *_ in edges:
        reach[u][v] = True
    for k in range(n):
        for i in range(n):
            for j in range(n):
                reach[i][j] = reach[i][j] or (reach[i][k] and reach[k][j])
    return reach


def groups(n, edges):
    graph = [[] for _ in range(n)]
    for u, v, *_ in edges:
        graph[u].append(v)
        graph[v].append(u)
    label = [-1] * n
    count, largest = 0, 0
    for start in range(n):
        if label[start] >= 0:
            continue
        stack = [start]
        label[start] = count
        size = 0
        while stack:
            u = stack.pop()
            size += 1
            for v in graph[u]:
                if label[v] < 0:
                    label[v] = count
                    stack.append(v)
        count += 1
        largest = max(largest, size)
    return label, count, largest


def oracle(x):
    n, task = x['n'], x['task']
    if task == 'dsu':
        edges, states = [], []
        for pair in x['operations']:
            edges.append(pair)
            _, count, largest = groups(n, edges)
            states.append([count, largest])
        return {'states': states}
    edges = x['edges']
    if task in ('kruskal', 'prim'):
        _, count, _ = groups(n, edges)
        best = None
        # Exhaust all n-c edge subsets. Only used for tiny random graphs.
        for ids in itertools.combinations(range(len(edges)), n - count):
            chosen = [edges[i] for i in ids]
            if groups(n, chosen)[1] == count:
                cost = sum(e[2] for e in chosen)
                best = cost if best is None else min(best, cost)
        return {'cost': best, 'components': count}
    reach = reachable(n, edges)
    if task == 'scc':
        labels = [min(j for j in range(n) if reach[i][j] and reach[j][i]) for i in range(n)]
        return {'component': labels}
    cyclic = any(u == v or reach[v][u] for u, v, *_ in edges)
    if task == 'topo':
        return {'acyclic': not cyclic}
    if cyclic:
        return {'acyclic': False}
    # Bellman-Ford relaxation, independent of the implementation's topo order.
    distance = [None] * n
    distance[x['source']] = 0
    for _ in range(n - 1):
        for u, v, w in edges:
            if distance[u] is not None:
                value = distance[u] + w
                if distance[v] is None or value < distance[v]:
                    distance[v] = value
    return {'acyclic': True, 'distance': distance}


def small_cases():
    rng = random.Random(20261020)
    cases = []
    for task in ('dsu', 'kruskal', 'prim', 'scc', 'topo', 'dag'):
        for index in range(120):
            n = rng.randrange(1 if task == 'dag' else 0, 7)
            x = {'task': task, 'n': n}
            edges = [] if not n else [[rng.randrange(n), rng.randrange(n)]
                                       for _ in range(rng.randrange(10))]
            if task == 'dsu':
                x['operations'] = edges
            else:
                if task in ('kruskal', 'prim', 'dag'):
                    edges = [e + [rng.randrange(-7, 8)] for e in edges]
                x['edges'] = edges
            if task == 'dag':
                x['source'] = rng.randrange(n)
                # Half the random graphs are guaranteed DAGs; others may cycle.
                if index % 2 == 0:
                    x['edges'] = [e for e in edges if e[0] < e[1]]
            cases.append({'name': f'{task}_random_{index}', 'input': x,
                          'expected': oracle(x), 'reason': 'Independent exhaustive/reachability oracle; seed 20261020.'})
    return cases


def boundary_cases():
    """Named cases make each contract boundary explicit, beyond random coverage."""
    cases = []

    def add(name, request, reason):
        cases.append({'name': name, 'input': request, 'expected': oracle(request), 'reason': reason})

    for n, operations, name in [
        (0, [], 'empty'), (1, [[0, 0], [0, 0]], 'self_repeated'),
        (7, [[0, 1], [2, 3], [1, 3], [4, 5], [0, 3], [3, 5]], 'balanced_isolate'),
        (4, [], 'no_operations')
    ]:
        add('dsu_' + name, {'task': 'dsu', 'n': n, 'operations': operations},
            'Rebuild undirected connected groups by traversal after every operation.')

    forests = [
        ('empty', 0, []), ('isolates', 5, []),
        ('negative_loop_only', 1, [[0, 0, -1000000000]]),
        ('negative_disconnected_parallel', 6, [[0, 0, -1000000000], [0, 1, -7],
            [0, 1, -7], [1, 2, 0], [0, 2, 9], [3, 4, -2]]),
        ('long_positive_sum', 6, [[i, i + 1, 1000000000] for i in range(5)]),
        ('long_negative_sum', 6, [[i, i + 1, -1000000000] for i in range(5)]),
        ('original_unsorted_ids', 4, [[0, 2, 99], [2, 3, 3], [0, 1, 1], [1, 2, 2]]),
        ('equal_weight_cycles', 4, [[0, 1, 0], [1, 2, 0], [2, 0, 0], [1, 3, 0], [2, 3, 0]])
    ]
    for task in ('kruskal', 'prim'):
        for name, n, edges in forests:
            add(task + '_' + name, {'task': task, 'n': n, 'edges': edges},
                'Enumerate all n-c edge subsets and independently check spanning connectivity.')

    directed = [
        ('empty', 0, []), ('isolates', 5, []), ('self_loop', 1, [[0, 0]]),
        ('two_cycles_and_isolate', 6, [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3],
                                     [3, 2], [3, 4], [3, 4]]),
        ('edge_to_finished_is_not_cycle', 4, [[0, 1], [0, 2], [2, 1], [2, 3]]),
        ('cycle_in_later_component', 5, [[0, 1], [2, 3], [3, 4], [4, 2]]),
        ('reverse_vertex_order', 5, [[4, 3], [3, 2], [4, 1], [1, 0], [2, 0]])
    ]
    for task in ('scc', 'topo'):
        for name, n, edges in directed:
            add(task + '_' + name, {'task': task, 'n': n, 'edges': edges},
                'All-pairs reachability proves mutual reachability and detects directed cycles.')

    dags = [
        ('one_source', 1, 0, []), ('unreachable', 5, 2, [[0, 1, -1], [2, 3, -1]]),
        ('valid_minus_one', 3, 0, [[0, 1, -1], [1, 2, 0]]),
        ('negative_long_sum', 6, 0, [[i, i + 1, -1000000000] for i in range(5)]),
        ('positive_long_sum', 6, 0, [[i, i + 1, 1000000000] for i in range(5)]),
        ('parallel_ties', 4, 0, [[0, 1, 2], [0, 1, 2], [0, 2, 1], [2, 1, 1],
                               [1, 3, -1], [2, 3, 0]]),
        ('nonzero_source_reverse_labels', 5, 4, [[4, 3, 2], [3, 1, -5], [4, 1, 9],
                                               [1, 0, 1], [2, 0, -8]]),
        ('reachable_cycle', 3, 0, [[0, 1, 1], [1, 2, -2], [2, 1, 2]]),
        ('unreachable_cycle', 4, 0, [[0, 1, 1], [2, 3, -2], [3, 2, 1]]),
        ('unreachable_self_loop', 3, 0, [[0, 1, 4], [2, 2, -1]])
    ]
    for name, n, source, edges in dags:
        add('dag_' + name, {'task': 'dag', 'n': n, 'source': source, 'edges': edges},
            'Check cycles in all components by reachability, then compute distances by Bellman-Ford.')
    return cases


def exhaustive_directed_cases():
    """Every directed graph on three vertices, including loops: 2^9 graphs."""
    possible = list(itertools.product(range(3), repeat=2))
    cases = []
    for mask in range(1 << len(possible)):
        edges = [list(edge) for bit, edge in enumerate(possible) if mask & (1 << bit)]
        for task in ('scc', 'topo'):
            request = {'task': task, 'n': 3, 'edges': edges}
            cases.append({'name': f'{task}_exhaustive_3_vertices_{mask}', 'input': request,
                          'expected': oracle(request),
                          'reason': 'Every subset of the nine possible directed edges; all-pairs reachability oracle.'})
    return cases


def witness_cases():
    cases = []
    for task in ('kruskal', 'prim'):
        x = {'task': task, 'n': 3, 'edges': [[0,1,1],[1,2,1],[0,2,1],[0,0,-100]]}
        e = {'cost': 2, 'components': 1}
        cases.extend([
            (x, e, {'cost': 2, 'components': 1, 'edge_ids': [0,2]}, True, task + ' alternative optimum'),
            (x, e, {'cost': 2, 'components': 1, 'edge_ids': [0,0]}, False, task + ' duplicate ID'),
            (x, e, {'cost': 2, 'components': 1, 'edge_ids': [0,3]}, False, task + ' loop witness')])
    x = {'task': 'scc', 'n': 3, 'edges': [[0,1],[1,0],[1,2],[0,2]]}
    e = {'component': [0,0,1]}
    cases.extend([
        (x, e, {'component': [7,7,42], 'condensation': [[7,42]]}, True, 'alternative SCC labels'),
        (x, e, {'component': [7,7,7], 'condensation': []}, False, 'incorrect SCC merge'),
        (x, e, {'component': [7,7,42], 'condensation': [[7,42],[7,42]]}, False, 'duplicate condensation')])
    x = {'task': 'topo', 'n': 3, 'edges': [[0,2],[1,2]]}
    e = {'acyclic': True}
    cases.extend([
        (x, e, {'acyclic': True, 'order': [1,0,2]}, True, 'alternative topological order'),
        (x, e, {'acyclic': True, 'order': [2,0,1]}, False, 'reversed prerequisite')])
    x = {'task': 'dag', 'n': 3, 'source': 0, 'edges': [[0,1,2],[0,1,2],[1,2,-1],[0,2,1]]}
    e = {'acyclic': True, 'distance': [0,2,1]}
    cases.extend([
        (x, e, {'acyclic': True, 'distance': [0,2,1], 'parent_edge': [-1,1,3]}, True, 'alternative parallel/tied path'),
        (x, e, {'acyclic': True, 'distance': [0,2,1], 'parent_edge': [-1,2,0]}, False, 'wrong incoming edge IDs')])
    records = []
    for x, e, answer, expected, name in cases:
        actual = check(x, answer, e)
        assert actual == expected, name
        records.append({'name': name, 'input': x, 'expected': e,
                        'candidate': answer, 'should_accept': expected, 'accepted': actual})
    return records


def scale_cases():
    n, m = 100000, 250000
    chain = [[v, v + 1] for v in range(n - 1)]
    pairs = chain + [chain[i % len(chain)] for i in range(m - len(chain))]
    ops = chain + [[0,0] for _ in range(m - len(chain))]
    yield 'dsu_full_limits', {'task': 'dsu', 'n': n, 'operations': ops}, {
        'states': [[n-i-1, i+2] if i < n-1 else [1,n] for i in range(m)]}
    weighted = [e + [1000000000] for e in pairs]
    for task in ('kruskal', 'prim'):
        yield task + '_full_limits', {'task': task, 'n': n, 'edges': weighted}, {
            'cost': (n-1) * 1000000000, 'components': 1}
    yield 'scc_deep_full_limits', {'task': 'scc', 'n': n, 'edges': pairs}, {'component': list(range(n))}
    yield 'topo_deep_full_limits', {'task': 'topo', 'n': n, 'edges': pairs}, {'acyclic': True}
    yield 'dag_negative_full_limits', {'task': 'dag', 'n': n, 'source': 0,
        'edges': [e + [-1000000000] for e in pairs]}, {
        'acyclic': True, 'distance': [-1000000000 * v for v in range(n)]}
    cycle = pairs.copy()
    cycle[-1] = [n-1,0]
    yield 'scc_deep_cycle_full_limits', {'task': 'scc', 'n': n, 'edges': cycle}, {'component': [0] * n}
    unreachable = [[v,v+1,1] for v in range(1,n-1)] + [[n-1,1,1]]
    unreachable += [[1,2,1] for _ in range(m-len(unreachable))]
    yield 'dag_unreachable_deep_cycle', {'task': 'dag', 'n': n, 'source': 0,
        'edges': unreachable}, {'acyclic': False}
    yield 'topo_deep_cycle_full_limits', {'task': 'topo', 'n': n, 'edges': cycle}, {'acyclic': False}

    # This shape fills Prim's lazy heap with O(m) simultaneous candidates.
    star = [[0, v, -1000000000] for v in range(1, n)]
    star += [[0, 1 + i % (n - 1), 1000000000] for i in range(m - len(star))]
    for task in ('kruskal', 'prim'):
        yield task + '_large_parallel_star', {'task': task, 'n': n, 'edges': star}, {
            'cost': -(n - 1) * 1000000000, 'components': 1}

    # Distinct cross-component pairs exercise condensation, not just duplicates.
    cross = []
    for gap in (1, 2, 3):
        cross.extend([[v, v + gap] for v in range(min(n - gap, m - len(cross)))])
    assert len(cross) == m
    yield 'scc_many_condensation_edges', {'task': 'scc', 'n': n, 'edges': cross}, {
        'component': list(range(n))}

    # Build balanced trees, then revisit vertices to exercise longer find paths.
    balanced, states = [], []
    count, largest = n, 1
    gap = 1
    while gap < n:
        for start in range(0, n, 2 * gap):
            if start + gap < n:
                balanced.append([start, start + gap])
                count -= 1
                largest = max(largest, min(2 * gap, n - start))
                states.append([count, largest])
        gap *= 2
    balanced.extend([[0, v % n] for v in range(m - len(balanced))])
    states.extend([[1, n] for _ in range(m - len(states))])
    yield 'dsu_balanced_full_limits', {'task': 'dsu', 'n': n, 'operations': balanced}, {'states': states}


def write_lines(path, records):
    with path.open('w', encoding='utf-8') as stream:
        for record in records:
            stream.write(json.dumps(record, separators=(',', ':')) + '\n')


def main():
    command = build('Java')
    random_cases = small_cases()
    boundaries = boundary_cases()
    exhaustive = exhaustive_directed_cases()
    cases = boundaries + random_cases + exhaustive
    # Repeat the same mixed batch in one process, with ping between copies.
    requests = [c['input'] for c in cases]
    answers = execute(command, requests + [{'task': 'ping'}] + requests)
    for index, case in enumerate(cases):
        assert check(case['input'], answers[index], case['expected']), case['name']
        assert check(case['input'], answers[len(cases)+1+index], case['expected']), case['name'] + ' reset'
    assert answers[len(cases)] == {'status': 'ready'}
    folder = ROOT / 'tests'
    write_lines(folder / 'cases.jsonl', requests)
    write_lines(folder / 'expected.jsonl', [c['expected'] for c in cases])
    write_lines(folder / 'actual.jsonl', answers[:len(cases)])
    (folder / 'case_reasons.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
    witnesses = witness_cases()
    (folder / 'witness_checks.json').write_text(json.dumps(witnesses, indent=2), encoding='utf-8')
    scale = []
    with gzip.open(folder / 'scale_inputs.jsonl.gz', 'wt', encoding='utf-8') as inputs, \
         gzip.open(folder / 'scale_expected.jsonl.gz', 'wt', encoding='utf-8') as expected, \
         gzip.open(folder / 'scale_actual.jsonl.gz', 'wt', encoding='utf-8') as actual:
        for name, request, reference in scale_cases():
            answer = execute(command, [request])[0]
            assert check(request, answer, reference), name
            for stream, record in ((inputs, request), (expected, reference), (actual, answer)):
                stream.write(json.dumps(record, separators=(',', ':')) + '\n')
            scale.append({'name': name, 'n': request['n'],
                          'm_or_q': len(request.get('edges', request.get('operations', []))), 'passed': True})
            print('PASS', name, flush=True)
    report = {'executed_at_utc': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(), 'platform': platform.platform(),
              'small_cases': len(cases), 'named_boundaries': len(boundaries),
              'random_cases': len(random_cases), 'exhaustive_directed_cases': len(exhaustive),
              'mixed_requests_in_one_process': len(answers),
              'semantic_witness_checks': len(witnesses), 'scale': scale}
    (folder / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
