import random
from OutputData import TourSolution

class NeighborhoodGenerator:
    """
    Diese Klasse bündelt alle Operatoren zur Veränderung einer Tour.
    Sie enthält Methoden für Shaking und die local search sowie die Reparatur von Touren/Nach Starkem Shaking
    """
    def __init__(self, input_data, seed=None, rnd = None, shaking_intensity_divisor=15, remove_var_min_pct=10, remove_var_max_pct=30):
        self.input_data = input_data
        # gesetzter Seed aus dem Notebook oder wenn keiner vorhanden = random Seed
        self.random = rnd or random.Random(seed)
        # Zählt, wie viele VNS-Iterationen in Folge keine Verbesserung brachten / # Wird zur Steuerung der Shaking-Intensität verwendet
        self.no_improvement_counter = 0
        self.shaking_intensity_divisor = shaking_intensity_divisor 
        self.remove_var_min_pct = remove_var_min_pct
        self.remove_var_max_pct = remove_var_max_pct 

    # SHAKING OPERATOREN 
    # Diese Methoden dienen dazu, eine Lösung stark zu verändern(zu shaken), um aus einem lokalen Optimum zu entkommen
    def remove_k_random_nodes(self, tour, k=2):
        """Entfernt eine feste Anzahl (k) zufälliger Knoten aus der Tour."""
        if len(tour) <= 2: return tour
        # Wähle zufällige Indizes zum Entfernen (außer Start/End-Depot 1)
        indices = list(range(1, len(tour) - 1))
        self.random.shuffle(indices)
        to_remove = sorted(indices[:min(k, len(indices))])
        # Von hinten nach vorne entfernen, um Indexverschiebungen zu vermeiden
        for i in reversed(to_remove):
            del tour[i]
        return tour

    def shuffle_segment(self, tour):
        """Nimmt ein zufälliges Segment der Tour und mischt die Reihenfolge der Knoten darin"""
        if len(tour) <= 4: return tour
        start = self.random.randint(1, len(tour) - 3)
        end = self.random.randint(start + 1, min(start + 4, len(tour) - 1))
        if start >= end: return tour
        segment = tour[start:end]
        self.random.shuffle(segment)
        return tour[:start] + segment + tour[end:]
    

    def remove_worst_nodes(self, tour, k=3):
        """ Entfernt die 'schlechtesten' Knoten basierend auf ihrem Score. """
        if len(tour) <= k + 2: return tour
        
        # Finde die IDs der Knoten in der Tour (ohne Depot)
        tour_node_ids = tour[1:-1]
        
        # Sortiere sie nach ihrem Score (aufsteigend)
        sorted_nodes = sorted(tour_node_ids, key=lambda node_id: self.input_data.nodes[node_id-1].score)
        
        # Wähle die k schlechtesten aus
        ids_to_remove = set(sorted_nodes[:k])
        
        # Erstelle eine neue Tour ohne diese Knoten
        new_tour = [node_id for node_id in tour if node_id not in ids_to_remove]
        return new_tour

    def swap_large_segments(self, tour):
        """ Tauscht zwei größere, nicht überlappende Segmente in der Tour. """
        if len(tour) < 10: return tour
        
        size = len(tour) - 2 # Ohne Depots
        
        # Wähle zwei zufällige Schnittpunkte
        i = self.random.randint(1, size // 2)
        j = self.random.randint(i + 2, size - 2)
        
        segment1 = tour[1:i]
        segment2 = tour[i:j]
        segment3 = tour[j:-1]
        
        # Mische die Segmente neu
        shuffled_segments = [segment1, segment2, segment3]
        self.random.shuffle(shuffled_segments)
        
        # Baue die Tour neu zusammen
        new_tour_middle = []
        for seg in shuffled_segments:
            new_tour_middle.extend(seg)
            
        return [1] + new_tour_middle + [1]

    def remove_variable(self, tour):
        """Entfernt einen zufälligen prozentualen Anteil der Knoten."""
        if len(tour) <= 4: return tour
        percent = self.random.randint(self.remove_var_min_pct, self.remove_var_max_pct)
        num_remove = max(1, int((len(tour) - 2) * percent / 100))
        indices = list(range(1, len(tour) - 1))
        self.random.shuffle(indices)
        to_remove = sorted(indices[:num_remove])
        for i in reversed(to_remove):
            del tour[i]
        return tour

    def greedy_repair(self, tour, max_add=None):
        """
        Repariert eine "kaputte" (durch Shaking verkürzte) Tour.
        Fügt iterativ die besten noch nicht besuchten Knoten (höchster Score)
        an einer zufälligen, aber gültigen Position wieder ein.
        """
        rnd = self.random
        added = 0
        existing_ids = set(tour)
        candidates = sorted(
            [n for n in self.input_data.nodes if n.id not in existing_ids],
            key=lambda n: n.score, reverse=True
        )
        for node in candidates:
            insert_positions = list(range(1, len(tour)))
            rnd.shuffle(insert_positions)
            for i in insert_positions:
                new_tour = tour[:i] + [node.id] + tour[i:]
                sol = TourSolution(new_tour, self.input_data.time_limit)
                sol.evaluate(self.input_data)
                if sol.is_valid:
                    tour = new_tour
                    added += 1
                    break
            if max_add is not None and added >= max_add:
                break
        return tour

    def random_modify(self, solution, repair=False):
        """
        Haupt-Shaking-Funktion, die adaptiv mehrere Operatoren kombiniert.
        Je länger keine Verbesserung gefunden wurde (`no_improvement_counter`),
        desto mehr Operatoren werden angewendet, um die Störung zu erhöhen.
        """
        tour = solution.tour.copy()
        k = self.no_improvement_counter
        # Die Intensität (Anzahl der Operationen) steigt mit der Stagnation.
        num_ops = 1 + k // self.shaking_intensity_divisor #15 
        if num_ops > 5: num_ops = 5

        
        # Verwendete aggressive Operatoren 
        ops = [
            "remove", "shuffle", "remove_variable",
            "remove_worst", "swap_segments" 
        ]
       

        self.random.shuffle(ops)
        chosen_ops = ops[:min(num_ops, len(ops))]

        for op in chosen_ops:
            if op == "remove":
                tour = self.remove_k_random_nodes(tour, k=self.random.randint(1, 3))
            elif op == "shuffle":
                tour = self.shuffle_segment(tour)
            elif op == "remove_variable":
                tour = self.remove_variable(tour)
                # Nach starker Zerstörung wird eine begrenzte Reparatur durchgeführt / Sonst würde die Zerstörte Tour durch die kürze niemals im Pool aufgenommen werden/ an bestehende Lösunge ran kommen
                added_limit = int(0.3 * len(self.input_data.nodes))
                tour = self.greedy_repair(tour, max_add=added_limit)
            elif op == "remove_worst": 
                tour = self.remove_worst_nodes(tour, k=self.random.randint(2, 4))
            elif op == "swap_segments": 
                tour = self.swap_large_segments(tour)
            
        # max 20 Knoten bei Repair / nicht mehr weil sonst dauert das zu lang (20 ist da schon ein ziemlich hoher wert der sich aber durch testen bewährt hat)
        if repair:
            tour = self.greedy_repair(tour, max_add=20)

        # Erzeugt ein neues, valides Solution-Objekt aus der gestörten Tour    
        neighbor = TourSolution(tour, self.input_data.time_limit)
        neighbor.evaluate(self.input_data)
        return neighbor if neighbor.is_valid else solution
    
    def shaking(self, solution, k, repair=False):
        """Wrapper für die Shaking-Logik."""
        return self.random_modify(solution, repair=repair)

    # === LOKALE SUCHOPERATOREN (Best Improvement) ===
    # Diese Methoden durchsuchen die Nachbarschaft und geben die beste gefundene Verbesserung zurück.

    def add_best_node(self, solution):
        """Sucht den besten Knoten der an der besten Position eingefügt werden kann."""
        candidates = sorted([node.id for node in self.input_data.nodes if node.id not in solution.tour])
        best_solution = solution
        for node_id in candidates:
            for i in range(1, len(solution.tour)):
                new_tour = solution.tour[:i] + [node_id] + solution.tour[i:]
                neighbor = TourSolution(new_tour, self.input_data.time_limit)
                neighbor.evaluate(self.input_data)
                if neighbor.is_valid and (neighbor.score > best_solution.score or 
                   (neighbor.score == best_solution.score and neighbor.total_distance < best_solution.total_distance)):
                    best_solution = neighbor
        return best_solution

    def replace_node(self, solution):
        """Sucht den besten Austausch eines Tour-Knotens gegen einen externen Knoten."""
        candidates = sorted([node.id for node in self.input_data.nodes if node.id not in solution.tour])
        best_solution = solution
        for i in range(1, len(solution.tour) - 1):
            for new_id in candidates:
                new_tour = solution.tour[:i] + [new_id] + solution.tour[i + 1:]
                neighbor = TourSolution(new_tour, self.input_data.time_limit)
                neighbor.evaluate(self.input_data)
                if neighbor.is_valid and (neighbor.score > best_solution.score or 
                   (neighbor.score == best_solution.score and neighbor.total_distance < best_solution.total_distance)):
                    best_solution = neighbor
        return best_solution

    def segment_move(self, solution):
        """Testet das Verschieben von kleinen Tour-Segmenten an andere Positionen."""
        best_solution = solution
        tour = solution.tour
        for i in range(1, len(tour) - 2):
            for j in range(i + 1, min(i + 4, len(tour) - 1)):
                segment = tour[i:j]
                if not segment: continue
                reduced = tour[:i] + tour[j:]
                for k in range(1, len(reduced) + 1):
                    new_tour = reduced[:k] + segment + reduced[k:]
                    neighbor = TourSolution(new_tour, self.input_data.time_limit)
                    neighbor.evaluate(self.input_data)
                    if neighbor.is_valid and (neighbor.score > best_solution.score or 
                       (neighbor.score == best_solution.score and neighbor.total_distance < best_solution.total_distance)):
                        best_solution = neighbor
        return best_solution

    def insert_best_node_at_best_position(self, solution):
        """Dopplung von `add_best_node`, aber mit anderer Kandidatensortierung. Dient der Diversität in der VND."""
        best_solution = solution
        candidates = sorted([n for n in self.input_data.nodes if n.id not in solution.tour], key=lambda n: n.id)
        for node in candidates:
            for i in range(1, len(solution.tour)):
                new_tour = solution.tour[:i] + [node.id] + solution.tour[i:]
                neighbor = TourSolution(new_tour, self.input_data.time_limit)
                neighbor.evaluate(self.input_data)
                if neighbor.is_valid and (neighbor.score > best_solution.score or 
                   (neighbor.score == best_solution.score and neighbor.total_distance < best_solution.total_distance)):
                    best_solution = neighbor
        return best_solution


# Alte Test

# import random
# from OutputData import TourSolution

# class NeighborhoodGenerator:
#     def __init__(self, input_data, seed=None):
#         self.input_data = input_data
#         self.random = random.Random(seed)
#         self.no_improvement_counter = 0

#     # =============================
#     # SHAKING: Entferne k zufällige Knoten
#     # =============================
#     def remove_k_random_nodes(self, tour, k=2):
#         indices = list(range(1, len(tour) - 1))
#         self.random.shuffle(indices)
#         to_remove = sorted(indices[:min(k, len(indices))])
#         for i in reversed(to_remove):
#             del tour[i]
#         return tour

#     # # =============================
#     # # SHAKING: Füge k zufällige Top-Knoten ein
#     # # =============================
#     # def insert_k_top_nodes(self, tour, k=2):
#     #     existing_ids = set(tour)
#     #     candidates = sorted(
#     #         [node for node in self.input_data.nodes if node.id not in existing_ids],
#     #         key=lambda n: n.score,
#     #         reverse=True
#     #     )[:10]
#     #     for _ in range(k):
#     #         if not candidates:
#     #             break
#     #         chosen = self.random.choice(candidates)
#     #         pos = self.random.randint(1, len(tour) - 1)
#     #         tour = tour[:pos] + [chosen.id] + tour[pos:]
#     #         candidates.remove(chosen)
#     #     return tour



#     # =============================
#     # SHAKING: Entferne variablen Anteil der Tour (z. B. 10–40 %)
#     # =============================
#     def remove_variable_portion(self, tour, min_pct=0.1, max_pct=0.4):
#         if len(tour) <= 4:
#             return tour

#         n = len(tour) - 2  # ohne Start/Ende
#         pct = self.random.uniform(min_pct, max_pct)
#         k = max(1, int(n * pct))
#         indices = list(range(1, len(tour) - 1))
#         self.random.shuffle(indices)
#         to_remove = sorted(indices[:k])
#         for i in reversed(to_remove):
#             del tour[i]
#         return tour

#     # =============================
#     # SHAKING: Mische zufälliges Tour-Segment
#     # =============================
#     def shuffle_segment(self, tour):
#         if len(tour) <= 4:
#             return tour
#         start = self.random.randint(1, len(tour) - 4)
#         end = self.random.randint(start + 1, min(start + 4, len(tour) - 1))
#         segment = tour[start:end]
#         self.random.shuffle(segment)
#         return tour[:start] + segment + tour[end:]

#     # =============================
#     # SHAKING: Adaptive zufällige Veränderung
#     # =============================
#     def random_modify(self, solution):
#         tour = solution.tour.copy()
#         k = self.no_improvement_counter

#         # Adaptive Intensität: Mehr Änderungen bei mehr Fehlversuchen
#         num_ops = 1
#         if k >= 90: num_ops = 5
#         elif k >= 60: num_ops = 4
#         elif k >= 30: num_ops = 3
#         elif k >= 10: num_ops = 2

#         for _ in range(num_ops):
#             op = self.random.choice(["remove", "shuffle", "remove_variable"]) #(["remove", "insert", "shuffle"])
#             if op == "remove":
#                 tour = self.remove_k_random_nodes(tour, k=self.random.randint(1, 3))
#             elif op == "insert":
#                 tour = self.insert_k_top_nodes(tour, k=self.random.randint(1, 3))
#             elif op == "shuffle":
#                 tour = self.shuffle_segment(tour)
#             elif op == "remove_variable":
#                 tour = self.remove_variable_portion(tour)

#         neighbor = TourSolution(tour, self.input_data.time_limit)
#         neighbor.evaluate(self.input_data)
#         return neighbor if neighbor.is_valid else solution

#     # =============================
#     # SHAKING-WRAPPER
#     # =============================
#     def shaking(self, solution, k):
#         return self.random_modify(solution)

#     # =============================
#     # LOCAL SEARCH-WRAPPER
#     # =============================
#     def local_search(self, solution, k):
#         methods = [
#             self.add_best_node,
#             self.remove_worst_node,
#             #self.insert_best_node_at_best_position,  # ⬅️ Neue Methode eingefügt
#             self.replace_node,
#             self.segment_move
#         ]
#         method = methods[k % len(methods)]
#         new_solution = method(solution)

#         if new_solution.is_valid and new_solution.score > solution.score:
#             self.no_improvement_counter = 0
#             return new_solution

#         self.no_improvement_counter += 1
#         return solution

#     # =============================
#     # LOCAL SEARCH: Add best possible node
#     # =============================
#     def add_best_node(self, solution):
#         candidates = [node.id for node in self.input_data.nodes if node.id not in solution.tour]
#         best_score = -1
#         best_solution = None

#         for node_id in candidates:
#             for i in range(1, len(solution.tour)):
#                 new_tour = solution.tour[:i] + [node_id] + solution.tour[i:]
#                 neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                 neighbor.evaluate(self.input_data)
#                 if neighbor.is_valid and neighbor.score > best_score:
#                     best_score = neighbor.score
#                     best_solution = neighbor

#         return best_solution if best_solution else solution

#     # =============================
#     # LOCAL SEARCH: Remove worst node (Score vs Zeit-Verhältnis)
#     # =============================
#     def remove_worst_node(self, solution):
#         worst_ratio = float('inf')
#         worst_index = -1

#         for i in range(1, len(solution.tour) - 1):
#             node_id = solution.tour[i]
#             prev_id = solution.tour[i - 1]
#             next_id = solution.tour[i + 1]
#             node = self.input_data.nodes[node_id - 1]
#             time_cost = self.input_data.get_distance(prev_id, node_id) + self.input_data.get_distance(node_id, next_id)
#             ratio = time_cost / (node.score + 1e-6)
#             if ratio < worst_ratio:
#                 worst_ratio = ratio
#                 worst_index = i

#         if worst_index == -1:
#             return solution

#         new_tour = solution.tour[:worst_index] + solution.tour[worst_index + 1:]
#         neighbor = TourSolution(new_tour, self.input_data.time_limit)
#         neighbor.evaluate(self.input_data)
#         return neighbor if neighbor.is_valid else solution

#     # =============================
#     # LOCAL SEARCH: Replace a node with a better one
#     # =============================
#     def replace_node(self, solution):
#         candidates = [node.id for node in self.input_data.nodes if node.id not in solution.tour]
#         best_solution = None
#         best_score = solution.score

#         for i in range(1, len(solution.tour) - 1):
#             for new_id in candidates:
#                 new_tour = solution.tour[:i] + [new_id] + solution.tour[i + 1:]
#                 neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                 neighbor.evaluate(self.input_data)
#                 if neighbor.is_valid and neighbor.score > best_score:
#                     best_solution = neighbor
#                     best_score = neighbor.score

#         return best_solution if best_solution else solution

#     # =============================
#     # LOCAL SEARCH: Move a segment to a new position
#     # =============================
#     def segment_move(self, solution):
#         best_solution = solution
#         best_score = solution.score
#         tour = solution.tour

#         for i in range(1, len(tour) - 3):
#             for j in range(i + 1, min(i + 3, len(tour) - 1)):
#                 segment = tour[i:j + 1]
#                 reduced_tour = tour[:i] + tour[j + 1:]
#                 for k in range(1, len(reduced_tour)):
#                     new_tour = reduced_tour[:k] + segment + reduced_tour[k:]
#                     neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                     neighbor.evaluate(self.input_data)
#                     if neighbor.is_valid and neighbor.score > best_score:
#                         best_solution = neighbor
#                         best_score = neighbor.score

#         return best_solution

    # # =============================
    # # LOCAL SEARCH: Insert best node at best position
    # # =============================
    # def insert_best_node_at_best_position(self, solution):
    #     best_solution = solution
    #     best_score = solution.score
    #     time_limit = self.input_data.time_limit

    #     # Alle Knoten, die noch nicht enthalten sind
    #     candidates = [node for node in self.input_data.nodes if node.id not in solution.tour]

    #     for candidate in candidates:
    #         for i in range(1, len(solution.tour)):  # Einfügeposition zwischen Start und Ziel
    #             new_tour = solution.tour[:i] + [candidate.id] + solution.tour[i:]
    #             neighbor = TourSolution(new_tour, time_limit)
    #             neighbor.evaluate(self.input_data)

    #             if neighbor.is_valid and neighbor.score > best_score:
    #                 best_score = neighbor.score
    #                 best_solution = neighbor

    #     return best_solution

# import random
# from OutputData import TourSolution

# class NeighborhoodGenerator:
#     def __init__(self, input_data, seed=None):
#         self.input_data = input_data
#         self.random = random.Random(seed)
#         self.no_improvement_counter = 0

#     # =============================
#     # LOCAL SEARCH: Add best possible node
#     # =============================
#     def add_best_node(self, solution):
#         candidates = [node.id for node in self.input_data.nodes if node.id not in solution.tour]
#         best_score = -1
#         best_solution = None

#         for node_id in candidates:
#             for i in range(1, len(solution.tour)):
#                 new_tour = solution.tour[:i] + [node_id] + solution.tour[i:]
#                 neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                 neighbor.evaluate(self.input_data)
#                 if neighbor.is_valid and neighbor.score > best_score:
#                     best_score = neighbor.score
#                     best_solution = neighbor

#         return best_solution if best_solution else solution

#     # =============================
#     # LOCAL SEARCH: Remove worst node (low score per time)
#     # =============================
#     def remove_worst_node(self, solution):
#         worst_ratio = float('inf')
#         worst_index = -1

#         for i in range(1, len(solution.tour) - 1):
#             node_id = solution.tour[i]
#             prev_id = solution.tour[i - 1]
#             next_id = solution.tour[i + 1]
#             node = self.input_data.nodes[node_id - 1]
#             time_cost = self.input_data.get_distance(prev_id, node_id) + self.input_data.get_distance(node_id, next_id)
#             ratio = time_cost / (node.score + 1e-6)
#             if ratio < worst_ratio:
#                 worst_ratio = ratio
#                 worst_index = i

#         if worst_index == -1:
#             return solution

#         new_tour = solution.tour[:worst_index] + solution.tour[worst_index + 1:]
#         neighbor = TourSolution(new_tour, self.input_data.time_limit)
#         neighbor.evaluate(self.input_data)
#         return neighbor if neighbor.is_valid else solution

#     # =============================
#     # LOCAL SEARCH: Replace a node with a better one
#     # =============================
#     def replace_node(self, solution):
#         candidates = [node.id for node in self.input_data.nodes if node.id not in solution.tour]
#         best_solution = None
#         best_score = solution.score

#         for i in range(1, len(solution.tour) - 1):
#             for new_id in candidates:
#                 new_tour = solution.tour[:i] + [new_id] + solution.tour[i + 1:]
#                 neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                 neighbor.evaluate(self.input_data)
#                 if neighbor.is_valid and neighbor.score > best_score:
#                     best_solution = neighbor
#                     best_score = neighbor.score

#         return best_solution if best_solution else solution

#     # =============================
#     # LOCAL SEARCH: Move a segment to a new position
#     # =============================
#     def segment_move(self, solution):
#         best_solution = solution
#         best_score = solution.score
#         tour = solution.tour

#         for i in range(1, len(tour) - 3):
#             for j in range(i + 1, min(i + 3, len(tour) - 1)):
#                 segment = tour[i:j + 1]
#                 reduced_tour = tour[:i] + tour[j + 1:]
#                 for k in range(1, len(reduced_tour)):
#                     new_tour = reduced_tour[:k] + segment + reduced_tour[k:]
#                     neighbor = TourSolution(new_tour, self.input_data.time_limit)
#                     neighbor.evaluate(self.input_data)
#                     if neighbor.is_valid and neighbor.score > best_score:
#                         best_solution = neighbor
#                         best_score = neighbor.score

#         return best_solution

#     # =============================
#     # SHAKING: Random modification with weights and adaptive intensity
#     # =============================
#     def random_modify(self, solution):
#         tour = solution.tour.copy()
#         actions = ["remove"] * 5 + ["replace"] * 3 + ["add"] * 2

#         # Adaptive Shaking: intensiver bei mehr Fehlversuchen
#         if self.no_improvement_counter >= 90:
#             num_actions = 5
#         elif self.no_improvement_counter >= 60:
#             num_actions = 4
#         elif self.no_improvement_counter >= 30:
#             num_actions = 3
#         else:
#             num_actions = 1

#         for _ in range(num_actions):
#             action = self.random.choice(actions)

#             if action == "add":
#                 top_candidates = sorted(
#                     [node for node in self.input_data.nodes if node.id not in tour],
#                     key=lambda n: n.score,
#                     reverse=True
#                 )[:5]
#                 if top_candidates:
#                     new_id = self.random.choice([n.id for n in top_candidates])
#                     pos = self.random.randint(1, len(tour) - 1)
#                     tour = tour[:pos] + [new_id] + tour[pos:]

#             elif action == "remove" and len(tour) > 3:
#                 scores = [(i, self.input_data.nodes[tour[i] - 1].score) for i in range(1, len(tour) - 1)]
#                 if scores:
#                     lowest = sorted(scores, key=lambda x: x[1])[:2]
#                     index_to_remove = self.random.choice([idx for idx, _ in lowest])
#                     tour = tour[:index_to_remove] + tour[index_to_remove + 1:]

#             elif action == "replace" and len(tour) > 3:
#                 candidates = [node.id for node in self.input_data.nodes if node.id not in tour]
#                 if candidates:
#                     pos = self.random.randint(1, len(tour) - 2)
#                     new_id = self.random.choice(candidates)
#                     tour = tour[:pos] + [new_id] + tour[pos + 1:]

#         neighbor = TourSolution(tour, self.input_data.time_limit)
#         neighbor.evaluate(self.input_data)
#         return neighbor if neighbor.is_valid else solution

#     # =============================
#     # SHAKING wrapper
#     # =============================
#     def shaking(self, solution, k):
#         return self.random_modify(solution)

#     # =============================
#     # Local Search wrapper
#     # =============================
#     def local_search(self, solution, k):
#         methods = [self.add_best_node, self.remove_worst_node, self.replace_node, self.segment_move]
#         method = methods[k % len(methods)]
#         new_solution = method(solution)

#         if new_solution.is_valid and (
#             new_solution.score > solution.score or
#             (new_solution.score == solution.score and new_solution.total_distance < solution.total_distance)
#         ):
#             self.no_improvement_counter = 0
#             return new_solution

#         self.no_improvement_counter += 1
#         return solution
