import random
from OutputData import TourSolution
from math import atan2


def generate_solution(input_data, method, top_k=3, cluster_size=35, seed=None , rnd = None):
    """
    Eine Factory-Funktion, die basierend auf dem 'method'-String die passende konstruktive Heuristik aufruft, um eine Startlösung zu erzeugen.
    Stellt sicher, dass ein gültiges `random.Random`-Objekt an alle stochastischen Methoden weitergereicht wird (Reproduzierbarkeit)
    """

    if rnd is None:
        rnd = random.Random(seed)

    if method == "greedy":
        return greedy_solution(input_data)
    elif method == "random":
        return random_solution(input_data, rnd=rnd)
    elif method == "randomized_greedy":
        return randomized_greedy_solution(input_data, top_k, rnd=rnd)
    elif method == "best_insertion":
        return best_insertion_solution(input_data)
    elif method == "clustered_greedy":
        return clustered_greedy_solution(input_data, cluster_size)
    elif method == "shortest_path":
        return shortest_path_solution(input_data)
    elif method == "efficiency":
        return efficiency_direct_solution(input_data)
    elif method == "randomized_best_insertion":
        return randomized_best_insertion_solution(input_data, top_k, rnd=rnd)
    elif method == "greedy_shuffle":
        return greedy_shuffle_start_solution(input_data, rnd=rnd)
    else:
        raise ValueError(f"Unbekannte Methode: {method}")



# Greedy: Nächsten Knoten mit bestem Score/Distanz-Verhältnis
def greedy_solution(input_data):
    """
    Erzeugt eine Tour nach einem greedy Kriterium. 
    In jedem Schritt wird der unbesuchte Knoten mit dem besten Verhältnis von Score zu Reisekosten
    (Hinfahrt vom letzten Knoten + Rückfahrt zum Depot) ausgewählt.
    Dies führt schnell zu guten aber oft leider nur lokal optimalen Lösungen.
    """
    current_id = 1
    tour = [current_id]
    remaining = set(n.id for n in input_data.nodes if n.id != 1)
    time = 0.0

    while remaining:
        best = None
        best_value = -1
        # KORREKTUR: Iteriere über eine sortierte Liste für deterministisches Verhalten.
        for node_id in sorted(list(remaining)):
            dist = input_data.get_distance(current_id, node_id) + input_data.get_distance(node_id, 1)
            if time + dist > input_data.time_limit:
                continue
            score = next(n.score for n in input_data.nodes if n.id == node_id)
            value = score / dist if dist > 0 else float('inf')
            if value > best_value:
                best = node_id
                best_value = value

        if best is None:
            break

        time += input_data.get_distance(current_id, best)
        current_id = best
        tour.append(best)
        remaining.remove(best)

    tour.append(1)
    solution = TourSolution(tour, input_data.time_limit)
    solution.evaluate(input_data)
    return solution

# Random: wähle zufällig Knoten, solange gültig
def random_solution(input_data, rnd):
    current_id = 1
    tour = [current_id]
    remaining = list(n.id for n in input_data.nodes if n.id != 1)
    rnd.shuffle(remaining)
    time = 0.0

    for node_id in remaining:
        dist = input_data.get_distance(current_id, node_id) + input_data.get_distance(node_id, 1)
        if time + dist > input_data.time_limit:
            continue
        time += input_data.get_distance(current_id, node_id)
        tour.append(node_id)
        current_id = node_id

    tour.append(1)
    solution = TourSolution(tour, input_data.time_limit)
    solution.evaluate(input_data)
    return solution



# Randomized Greedy: zufällige Auswahl aus Top-k besten Knoten
def randomized_greedy_solution(input_data, k, rnd):
    """
    Statt immer den absolut besten nächsten Knoten zu wählen, wird eine
    Kandidatenliste der 'k' besten nächsten Knoten erstellt. Aus dieser Liste
    wird dann zufällig einer ausgewählt. Dies erhöht die Diversität der
    erzeugten Startlösungen. / Wird bei manchen Restarts verwendet 
    """
    current_id = 1
    tour = [current_id]
    remaining = set(n.id for n in input_data.nodes if n.id != 1)
    time = 0.0

    while remaining:
        candidates = []
        # KORREKTUR: Iteriere über eine sortierte Liste für deterministisches Verhalten.
        for node_id in sorted(list(remaining)):
            dist = input_data.get_distance(current_id, node_id) + input_data.get_distance(node_id, 1)
            if time + dist > input_data.time_limit:
                continue
            score = next(n.score for n in input_data.nodes if n.id == node_id)
            value = score / dist if dist > 0 else float('inf')
            candidates.append((value, node_id))

        if not candidates:
            break

        candidates.sort(key=lambda x: x[0], reverse=True)
        chosen = rnd.choice(candidates[:min(k, len(candidates))])[1]

        time += input_data.get_distance(current_id, chosen)
        current_id = chosen
        tour.append(chosen)
        remaining.remove(chosen)

    tour.append(1)
    solution = TourSolution(tour, input_data.time_limit)
    solution.evaluate(input_data)
    return solution


# Best Insertion: füge Knoten an beste Stelle der Tour ein
def best_insertion_solution(input_data):
    """
    Baut eine Tour iterativ auf. Beginnt mit einer minimalen Tour (Depot -> Depot).
    In jedem Schritt wird derjenige unbesuchte Knoten gesucht, der an der
    bestmöglichen Position in die bestehende Tour eingefügt werden kann,
    sodass der Anstieg der Gesamtdistanz minimal ist. Diese Heuristik ist
    rechenintensiver, erzeugt aber oft strukturell sehr gute Touren/Startlösungen.
    """
    tour = [1, 1]
    remaining = set(n.id for n in input_data.nodes if n.id != 1)

    while remaining:
        best_node = None
        best_pos = None
        best_increase = float('inf')

        #Iterierung über eine sortierte Liste für deterministisches Verhalten.
        for node_id in sorted(list(remaining)):
            for i in range(1, len(tour)):
                before = tour[i - 1]
                after = tour[i]
                added = (
                    input_data.get_distance(before, node_id) +
                    input_data.get_distance(node_id, after) -
                    input_data.get_distance(before, after)
                )
                
                temp_tour = tour[:i] + [node_id] + tour[i:]
                temp_time = compute_total_distance(temp_tour, input_data)
                
                if temp_time <= input_data.time_limit and added < best_increase:
                    best_increase = added
                    best_node = node_id
                    best_pos = i

        if best_node is None:
            break

        tour.insert(best_pos, best_node)
        remaining.remove(best_node)

    solution = TourSolution(tour, input_data.time_limit)
    solution.evaluate(input_data)
    return solution



# Clustering + Greedy: teile in Cluster, löse lokal greedy / Verworfen / War schon als Idee hat aber gar nicht geklappt
def clustered_greedy_solution(input_data, cluster_size):
    depot = next(n for n in input_data.nodes if n.id == 1)
    nodes = [n for n in input_data.nodes if n.id != 1]
    nodes.sort(key=lambda n: atan2(n.y - depot.y, n.x - depot.x))

    clusters = [nodes[i:i + cluster_size] for i in range(0, len(nodes), cluster_size)]
    tour = [1]
    time = 0.0
    current_id = 1

    for cluster in clusters:
        local_nodes = set(n.id for n in cluster)
        while local_nodes:
            best = None
            best_value = -1
            for node_id in sorted(list(local_nodes)):
                dist = input_data.get_distance(current_id, node_id) + input_data.get_distance(node_id, 1)
                if time + dist > input_data.time_limit:
                    continue
                score = next(n.score for n in input_data.nodes if n.id == node_id)
                value = score / dist if dist > 0 else float('inf')
                if value > best_value:
                    best = node_id
                    best_value = value
            if best is None:
                break
            time += input_data.get_distance(current_id, best)
            tour.append(best)
            current_id = best
            local_nodes.remove(best)

    tour.append(1)
    solution = TourSolution(tour, input_data.time_limit)
    solution.evaluate(input_data)
    return solution

#Verworfen / Lange Touren aber sehr schlechte 
def shortest_path_solution(input_data):
    tour = [1]
    remaining = set(node.id for node in input_data.nodes if node.id != 1)

    while remaining:
        last = tour[-1]
        
        
        sorted_remaining = sorted(list(remaining), key=lambda nid: (input_data.get_distance(last, nid), nid))
        
        found_next = False
        for next_node in sorted_remaining:
            new_tour = tour + [next_node, 1]
            solution = TourSolution(new_tour, input_data.time_limit)
            solution.evaluate(input_data)

            if solution.is_valid:
                tour.append(next_node)
                remaining.remove(next_node)
                found_next = True
                break
        
        if not found_next:
            break

    tour.append(1)
    final_solution = TourSolution(tour, input_data.time_limit)
    final_solution.evaluate(input_data)
    return final_solution

# Verworfen / Hat leider schlechte Startlösungen gebracht 
def efficiency_direct_solution(input_data):
    tour = [1]
    remaining = set(node.id for node in input_data.nodes if node.id != 1)

    while remaining:
        best_ratio = -1
        best_node = None

        # KORREKTUR: Iteriere über eine sortierte Liste für deterministisches Verhalten.
        for nid in sorted(list(remaining)):
            dist = input_data.get_distance(tour[-1], nid)
            score = input_data.nodes[nid - 1].score
            if dist > 0:
                ratio = score / dist
                if ratio > best_ratio:
                    new_tour = tour + [nid, 1]
                    temp_sol = TourSolution(new_tour, input_data.time_limit)
                    temp_sol.evaluate(input_data)
                    if temp_sol.is_valid:
                        best_ratio = ratio
                        best_node = nid

        if best_node is None:
            break

        tour.append(best_node)
        remaining.remove(best_node)

    tour.append(1)
    final_solution = TourSolution(tour, input_data.time_limit)
    final_solution.evaluate(input_data)
    return final_solution


# Randomized Best Insertion: Wähle zufällig aus Top-K Einfügeoptionen / Wird noch manchmal aus mögliche Restart Lösung für Diversität verwendet
def randomized_best_insertion_solution(input_data, top_k, rnd):
    nodes = input_data.nodes.copy()
    unvisited = set(node.id for node in nodes if node.id != 1)
    tour = [1, 1]

    while unvisited:
        candidates = []
        for node_id in sorted(list(unvisited)):
            for i in range(1, len(tour)):
                new_tour = tour[:i] + [node_id] + tour[i:]
                sol = TourSolution(new_tour, input_data.time_limit)
                sol.evaluate(input_data)
                if sol.is_valid:
                    delta = sol.score
                    candidates.append((delta, new_tour))

        if not candidates:
            break

        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:min(top_k, len(candidates))]
        if not top_candidates:
            break
            
        _, selected_tour = rnd.choice(top_candidates)
        tour = selected_tour
        unvisited = set(node.id for node in input_data.nodes if node.id not in tour)

    final_solution = TourSolution(tour, input_data.time_limit)
    final_solution.evaluate(input_data)
    return final_solution



# Greedy mit zufälligem Startknoten  / Wollte ich als restart Lösung verwenden um neue Pool Solutions zu ermöglichen die anders augebraut sind. Hat aber nicht funktioniert und wurde verworfen
def greedy_shuffle_start_solution(input_data, rnd):
    nodes = input_data.nodes.copy()
    start_candidates = [node for node in nodes if node.id != 1]
    start_node = rnd.choice(start_candidates)

    tour = [1, start_node.id]
    time_limit = input_data.time_limit
    remaining = set(node.id for node in nodes if node.id not in tour)

    while remaining:
        best_ratio = -1
        best_node = None
        
        
        for node_id in sorted(list(remaining)):
            full_tour = tour + [node_id, 1]
            total = compute_total_distance(full_tour, input_data)
            
            if total <= time_limit:
                dist_to = input_data.get_distance(tour[-1], node_id)
                dist_back = input_data.get_distance(node_id, 1)
                node = input_data.nodes[node_id - 1]
                ratio = node.score / (dist_to + dist_back + 1e-6)

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_node = node_id

        if best_node is None:
            break

        tour.append(best_node)
        remaining.remove(best_node)

    tour.append(1)
    sol = TourSolution(tour, input_data.time_limit)
    sol.evaluate(input_data)
    return sol


# Hilfsfunktion: berechne Tourdistanz
def compute_total_distance(tour, input_data):
    return sum(input_data.get_distance(tour[i], tour[i+1]) for i in range(len(tour)-1))