import time
import random
from Neighborhood import NeighborhoodGenerator
from ConstructiveHeuristic import generate_solution
from OutputData import TourSolution

def similarity(tour_a, tour_b):
    """
    Berechnet die (Jaccard) Ähnlichkeit zwischen zwei Touren.
    Die Ähnlichkeit ist definiert als der Anteil der gemeinsamen Knoten (ohne Depot) im Verhältnis zur Gesamtmenge der besuchten Knoten.
    Ein Wert von 1.0 bedeutet identische Knotensets / 0.0 bedeutet keine gemeinsamen Knoten.
    Wird verwendet für den ListenAbgleich (Solution Pool)
    """
    set_a = set(tour_a[1:-1])
    set_b = set(tour_b[1:-1])
    union_size = len(set_a | set_b)
    if union_size == 0: return 1.0
    return len(set_a & set_b) / union_size

def run_vns(input_data, start_solution, seed=None, rnd=None, global_start_time=None, verbose=True):
    """
    Wrapper für die VNS.
    Diese Funktion ist der Einstiegspunkt.
    Sie ruft die eigentliche, parametrisierbare VNS-Funktion mit bewährten Standardparametern auf (Gewählt aus Parameteranalyse / die meisten zumimindest).
    """
    if rnd is None:
        rnd = random.Random(seed)
    if global_start_time is None:
        global_start_time = time.time()

    default_params = {
        'max_pool_size': 12,
        'similarity_threshold': 0.85,
        'pool_score_ratio': 0.85,
        'restart_stagnation': 60,
        'vns_stagnation_limit': 120,
        'max_time': 180,
        'shaking_intensity_divisor': 5,
        'remove_var_min_pct': 25,
        'remove_var_max_pct': 35,
    }
    return run_vns_parametrized(input_data, start_solution, rnd, default_params, global_start_time, verbose)

def run_vns_parametrized(input_data, start_solution, rnd, params, global_start_time, verbose=True):
    """
    Führt die Kernlogik der Variable Neighborhood Search (VNS) aus.
    Diese Funktion ist hochgradig parametrisierbar, um Analysen zu ermöglichen. / Wurde sehr häufig umstrukturiert für die ParameterAnalyse / Für ältere Versionen siehe weiter unten
    """
    # === 1. Parameter und Initialisierung ===
    # Die Parameter werden aus dem übergebenen Dictionary ausgelesen.
    # Falls ein Parameter nicht vorhanden ist, wird ein  Standardwert verwendet. / Bei normalen Durchläufen ohne ParameterAnalyse wird immer der Standart Wert verwendet der durch die ParameterAnalyse gefunden wurde
    max_pool_size = params.get('max_pool_size', 12)
    similarity_threshold = params.get('similarity_threshold', 0.85)
    pool_score_ratio = params.get('pool_score_ratio', 0.85)
    restart_stagnation = params.get('restart_stagnation', 50)
    vns_stagnation_limit = params.get('vns_stagnation_limit', 100)
    max_time = params.get('max_time', 180)
    shaking_intensity_divisor = params.get('shaking_intensity_divisor', 15)
    remove_var_min_pct = params.get('remove_var_min_pct', 10)
    remove_var_max_pct = params.get('remove_var_max_pct', 30)
    repair_shaking = params.get('repair_shaking', False)

    # current ist die Lösung, von der aus gesucht wird. 
    current = start_solution
    #best ist die beste jemals gefundene Lösung.
    best = current
    
    # der pool speichert eine Sammlung guter und diverser Lösungen, / ca 60 % der besten Lösungen / 40 % diverse / Jedoch nur selten benutzt wurden. Vor allem bei den größeren Instancen spielt der Pool kaum noch relevanz. 
    # leider auch nicht herausgefunden wie man das am besten noch implementieren kann.
    
    # um bei Restarts auf vielversprechende, aber andere Startpunkte zurückgreifen zu können. / So die Theorie / Restarts gibt es bei Instance 4 und 5 aber leider kaum noch.
    pool = [start_solution]
    
    # der NeighborhoodGenerator wird einmal erstellt. Sein interner Zustand 
    # (z.B. der no_improvement_counter für das Shaking) bleibt über den gesamten VNS-Lauf erhalten.
    # Dies ist entscheidend für adaptive Strategien. / Siehe Neighborhood.py  def random_modify ) 
    # Auch hier habe ich wegen der Parameteranalyse alles variable machen müssen / in älteren Versionen standen hier feste Werte
    ng = NeighborhoodGenerator(
        input_data, 
        rnd=rnd, 
        shaking_intensity_divisor=shaking_intensity_divisor,
        remove_var_min_pct=remove_var_min_pct,
        remove_var_max_pct=remove_var_max_pct
    )

    # Liste von local_search für das VND (Intensivierung).
    local_search_methods = [
        ng.add_best_node,
        ng.insert_best_node_at_best_position,
        ng.replace_node,
        ng.segment_move
    ]

    k_shake = 0  # Index für die Shaking-Struktur (hier nicht direkt genutzt, aber Teil des VNS-Konzepts)
    stagnation_counter = 0 # Zählt Iterationen ohne Verbesserung der *global besten* Lösung. / Wird auch für Abbruch verwendet
    restarts = 0 # Wie häufig restartet wurde. Hab ich auch oft mit geloggt weil ich zwischen durch große Probleme hatte bei der reproduzierung und schauen wollte wieso das ganze 
    
    #  Hilfsfunktionen für den Pool 
    def add_to_pool(candidate):
        """Fügt eine Kandidatenlösung zum Pool hinzu, wenn sie gut und divers genug ist."""
        # Ignoriere Lösungen die deutlich schlechter sind als die bisher beste
        if best.score > 0 and candidate.score < pool_score_ratio * best.score: return
        
        # Ignoriere Lösungen, die zu ähnlich zu bereits im Pool vorhandenen sind / Hier greift wieder def similarity von oben
        is_too_similar = False
        for sol in pool:
            if similarity(sol.tour, candidate.tour) > similarity_threshold:
                is_too_similar = True
                break
        
        if not is_too_similar:
            pool.append(candidate)
            # Deterministisches Sortieren, um Reproduzierbarkeit zu gewährleisten. (Hat mir Chat GPT nach einer Weile als mögliches Problem der fehlenden Reproduzierbarkeit vorgeschlagen)
            # Kriterien: 1. Score (hoch), 2. Distanz (niedrig), 3. Tour-Inhalt (eindeutig). / Danach wird Sotiert um jedes mal deterministische Listen = Lösungen/Scores zu erhalten 
            pool.sort(key=lambda s: (s.score, -s.total_distance, tuple(s.tour)), reverse=True)
            if len(pool) > max_pool_size:
                pool.pop() # Entferne die schlechteste Lösung, wenn der Pool voll ist. / Pool wird begrenz da sonst die random auswahl an Lösungen bei Neustart zu ineffizient wäre und auch schlechtere Lösunge wählen kann/ oder welche die schonmal genutzt worden sind

    def select_from_pool():
        """Wählt eine Lösung aus dem Pool. Bevorzugt Lösungen, die unähnlicher zur besten Lösung sind um diversität zu erzeugen"""
        if not pool: return best
        if len(pool) == 1: return pool[0]
        
        max_score = max(sol.score for sol in pool) if pool else 1
        if max_score == 0: max_score = 1
        
        # Gewichtung kombiniert Diversität (Unähnlichkeit zu `best`) und Qualität (Score).
        weights = [(1 - similarity(sol.tour, best.tour)) * 0.5 + (sol.score / max_score) * 0.5 for sol in pool]
        return rnd.choices(pool, weights=weights, k=1)[0]
        
    # === 2. VNS-Hauptschleife ===
    # Läuft, solange das Zeitlimit und das Stagnationslimit nicht erreicht sind / Sonst abbruch 
    while time.time() - global_start_time < max_time and stagnation_counter < vns_stagnation_limit:
        
        # Schritt 1: Shaking (Störung)
        # Stört die *aktuelle* Lösung (`current`), um aus lokalen Optimum zu entkommen und mögliche Nachbarschaften/globale Optima zu erkunden
        # Die Intensität des Shakings wird durch `ng.no_improvement_counter` gesteuert in def random_modify in Neighborhood.py
        shaken = ng.shaking(current, k_shake, repair=repair_shaking)
        
        # Zusätzliche Zeitchecks an rechenintensiven Stellen für das einhalten Zeitlimit (3 min pro Instance)
        if time.time() - global_start_time >= max_time: break
        
        # Schritt 2: Lokale Suche (Variable Neighborhood Descent - VND) (In Aufgaben Stellung Empfohlen gewesen)
        # Eine intensive lokale Suche die versucht die gestörte Lösung so gut wie möglich zu verbessern
        local_best = shaken
        k_vnd = 0
        while k_vnd < len(local_search_methods):
            if k_vnd % 2 == 0 and time.time() - global_start_time >= max_time: break
            
            method = local_search_methods[k_vnd]
            improved = method(local_best)

            # Wenn eine Verbesserung gefunden wurde, beginne die VND von vorne mit der ersten Nachbarschaft
            # Dies ist eine "First Improvement"-Strategie auf Ebene der Nachbarschaftsstrukturen
            if improved.score > local_best.score or \
              (improved.score == local_best.score and improved.total_distance < local_best.total_distance):
                local_best = improved
                k_vnd = 0
            else:
                k_vnd += 1
        
        # Schritt 3 Entscheidung (Move or Not)
        # Vergleiche das Ergebnis der lokalen Suche `local_best` mit der Lösung *vor* dem Shaking `current`
        if local_best.score > current.score or \
           (local_best.score == current.score and local_best.total_distance < local_best.total_distance):
            # Akzeptiere die neue Lösung
            current = local_best
            stagnation_counter = 0 # Reset da eine bessere Lösung gefunden wurde

            # Prüfe, ob sie auch die global beste Lösung ist
            if current.score > best.score or \
               (current.score == best.score and current.total_distance < best.total_distance):
                best = current
                if verbose:
                    print(f"Neue beste Lösung gefunden: Score={best.score}, Distanz={best.total_distance:.2f}")
                    print(f"   Tour: {best.tour}")
            
            add_to_pool(current)
            ng.no_improvement_counter = 0 # Reset des Shaking-Zählers
            k_shake = 0
        else:
            # Keine Verbesserung = erhöhe die Zähler
            stagnation_counter += 1
            ng.no_improvement_counter += 1
            k_shake = (k_shake + 1) % 4 # (hier nicht direkt genutzt, aber VNS-"Standard")

        # Schritt 4: Restart-Strategie
        # Wenn der Algorithmus zu lange keine Verbesserung für `current` findet wird ein Restart ausgelöst, um Stagnation zu durchbrechen/ diverstiät zu ermöglichen
        if ng.no_improvement_counter > restart_stagnation:
            restarts += 1
            if verbose:
                print(f"Restart nach : {ng.no_improvement_counter} Iterationen ohne Verbesserung.")
            
            # Wähle eine diverse Lösung aus dem Pool und störe sie stark
            current = ng.shaking(select_from_pool(), k=3, repair=True) 
            add_to_pool(current)
            ng.no_improvement_counter = 0
            
    if verbose:
        print(f"VNS ist abgeschlossen | Bester gefundener Score: {best.score} | Restarts: {restarts}")

    return best















# import time
# import random
# from Neighborhood import NeighborhoodGenerator
# from ConstructiveHeuristic import generate_solution
# from OutputData import TourSolution

# def similarity(tour_a, tour_b):
#     set_a = set(tour_a[1:-1])
#     set_b = set(tour_b[1:-1])
#     union_size = len(set_a | set_b)
#     if union_size == 0: return 1.0
#     return len(set_a & set_b) / union_size

# def run_vns(input_data, start_solution, seed=None, rnd=None):
#     if rnd is None:
#         rnd = random.Random(seed)

#     # 1. Initialisierung
#     current = start_solution
#     best = current
#     pool = [start_solution]
#     max_pool_size = 12
    
#     ng = NeighborhoodGenerator(input_data, rnd=rnd)
#     local_search_methods = [
#         ng.add_best_node,
#         ng.insert_best_node_at_best_position,
#         ng.replace_node,
#         ng.segment_move
#     ]

#     k_shake = 0
#     max_time = 180
#     max_stagnation = 200
#     stagnation_counter = 0
#     restarts = 0
#     start_time = time.time()

#     def add_to_pool(candidate):
#         if best.score > 0 and candidate.score < 0.85 * best.score: return
        
#         is_too_similar = False
#         for sol in pool:
#             if similarity(sol.tour, candidate.tour) > 0.85:
#                 is_too_similar = True
#                 break
        
#         if not is_too_similar:
#             pool.append(candidate)
#             # ========================================================
#             # FINALE, ENTSCHEIDENDE KORREKTUR: DETERMINISTISCHES SORTIEREN
#             # 1. Nach Score (höher ist besser)
#             # 2. Nach Distanz (niedriger ist besser, daher -s.total_distance)
#             # 3. Nach Tour-Inhalt (garantierter Tie-Breaker)
#             pool.sort(key=lambda s: (s.score, -s.total_distance, tuple(s.tour)), reverse=True)
#             # ========================================================
#             if len(pool) > max_pool_size:
#                 pool.pop()

#     def select_from_pool():
#         if not pool: return best
#         if len(pool) == 1: return pool[0]
        
#         max_score_in_pool = max(sol.score for sol in pool) if pool else 1
#         if max_score_in_pool == 0: max_score_in_pool = 1
        
#         weights = [(1 - similarity(sol.tour, best.tour)) * 0.5 + (sol.score / max_score_in_pool) * 0.5 for sol in pool]
#         return rnd.choices(pool, weights=weights, k=1)[0]

#     # 2. VNS-Hauptschleife
#     while time.time() - start_time < max_time and stagnation_counter < max_stagnation:
        
#         shaken = ng.shaking(current, k_shake)
        
#         local_best = shaken
#         k_vnd = 0
#         while k_vnd < len(local_search_methods):
#             method = local_search_methods[k_vnd]
#             improved = method(local_best)

#             if improved.score > local_best.score or \
#               (improved.score == local_best.score and improved.total_distance < local_best.total_distance):
#                 local_best = improved
#                 k_vnd = 0
#             else:
#                 k_vnd += 1
        
#         if local_best.score > current.score or \
#            (local_best.score == current.score and local_best.total_distance < current.total_distance):
#             current = local_best

#             if current.score > best.score or \
#                (current.score == best.score and current.total_distance < best.total_distance):
#                 best = current
#                 stagnation_counter = 0
#                 print(f"Neue beste Lösung: Score={best.score}, Distanz={best.total_distance:.2f}")
            
#             add_to_pool(current)
#             ng.no_improvement_counter = 0
#             k_shake = 0
#         else:
#             stagnation_counter += 1
#             ng.no_improvement_counter += 1
#             k_shake = (k_shake + 1) % 4

#         if ng.no_improvement_counter > 40:
#             restarts += 1
#             print(f"🔄 Restart nach {ng.no_improvement_counter} Iterationen ohne Verbesserung.")
#             current = ng.shaking(select_from_pool(), k=3, repair=True) 
#             add_to_pool(current)
#             ng.no_improvement_counter = 0

#     print(f"✅ VNS abgeschlossen | Bester Score: {best.score} | Restarts: {restarts}")
#     return best

















































































##### Alte Test 

# import time
# import random
# from Neighborhood import NeighborhoodGenerator
# from OutputData import TourSolution
# from ConstructiveHeuristic import generate_solution

# # =============================
# # Haupt-VNS mit Solution-Pool und explorativem Restart
# # =============================

# def run_vns(input_data, start_solution, seed=None):
#     rnd = random.Random(seed)
#     current = start_solution
#     best = current
#     solution_pool = [start_solution]
#     max_pool_size = 12

#     exploration_index = 0

#     # =============================
#     # Optimale Scores als Abbruchkriterium
#     # =============================
#     optimal_scores = {
#         "Instance_1": 155,
#         "Instance_2": 205,
#         "Instance_3": 510,
#         "Instance_4": 3138,
#         "Instance_5": 4591,
#     }
#     instance_name = input_data.name
#     optimal_target = optimal_scores.get(instance_name, None)

#     ng = NeighborhoodGenerator(input_data, seed=seed)
#     k = 0
#     max_time = 180  # 3 Minuten
#     max_no_improvement = 200
#     no_improvement = 0
#     restarts = 0
#     start_time = time.time()
#     last_restart_time = time.time()

#     while (time.time() - start_time < max_time) and (no_improvement < max_no_improvement):
#         shaken = ng.shaking(current, k)
#         improved = ng.local_search(shaken, k)

#         if improved.score > current.score:
#             current = improved
#             if improved.score > best.score:
#                 best = improved

#             # =============================
#             # Lösung in Pool speichern, wenn stark genug
#             # =============================
#             if improved.score >= 0.85 * best.score:
#                 solution_pool.append(improved)
#                 if len(solution_pool) > max_pool_size:
#                     solution_pool = sorted(solution_pool, key=lambda s: s.score, reverse=True)[:max_pool_size]

#             k = 0
#             no_improvement = 0

#         else:
#             k = (k + 1) % 4
#             no_improvement += 1

#         # =============================
#         # Stagnation → Restart
#         # =============================
#         if no_improvement > 70 :
#             if restarts % 4 == 0:
#                 # Erst deterministische Methoden (3x), dann alternierend randomisierte
#                 if exploration_index < 1:
#                     method = ["greedy_shuffle"][exploration_index] #["shortest_path", "greedy_shuffle"]
#                 else:
#                     method = ["randomized_greedy", "randomized_best_insertion"][(exploration_index - 1) % 2]

#                 exploration_index += 1



#                 current = generate_solution(input_data, method=method, seed=seed)
#                 print(f"⚠️ Restart mit neuer explorativer Lösung ({method})")
#             else:
#                 # 🔁 Score-gewichtete Auswahl aus dem Pool
#                 scores = [sol.score for sol in solution_pool]
#                 current = ng.shaking(rnd.choices(solution_pool, weights=scores, k=1)[0], 0)


#             no_improvement = 0
#             restarts += 1

#         # =============================
#         # Zeitbasierter Restart
#         # =============================
#         if time.time() - last_restart_time > 60 and solution_pool:
#             # 🔁 Score-gewichtete Auswahl aus dem Pool
#             scores = [sol.score for sol in solution_pool]
#             current = ng.shaking(rnd.choices(solution_pool, weights=scores, k=1)[0], 0)

#             last_restart_time = time.time()
#             restarts += 1

#         # =============================
#         # Früher Abbruch bei optimaler Lösung
#         # =============================
#         if optimal_target and improved.score >= optimal_target:
#             print(f"🎯 Optimale Lösung erreicht ({improved.score}) – VNS wird abgebrochen.")
#             return improved

#     # =============================
#     # Ergebnis-Log
#     # =============================
#     print(f"✅ VNS abgeschlossen | Poolgröße: {len(solution_pool)} | Restarts: {restarts}")
#     return best


# def run_vns(input_data, start_solution, seed=None):
#     current = start_solution
#     best = current
#     solution_pool = [start_solution]
#     max_pool_size = 10

#     ng = NeighborhoodGenerator(input_data, seed=seed)
#     k = 0
#     max_time = 180
#     max_no_improvement = 200
#     no_improvement = 0
#     restarts = 0  # NEU: Restart-Zähler
#     start_time = time.time()

#     while (time.time() - start_time < max_time) and (no_improvement < max_no_improvement):
#         shaken = ng.shaking(current, k)
#         improved = ng.local_search(shaken, k)

#         if improved.score > current.score:
#             current = improved
#             if improved.score > best.score:
#                 best = improved

#             # Nur gute Lösungen in den Pool
#             if improved.score >= 0.9 * best.score:
#                 solution_pool.append(improved)
#                 # Begrenzung des Pools
#                 if len(solution_pool) > max_pool_size:
#                     solution_pool = sorted(solution_pool, key=lambda s: s.score, reverse=True)[:max_pool_size]

#             k = 0
#             no_improvement = 0
#         else:
#             k = (k + 1) % 4
#             no_improvement += 1

#         if no_improvement > 50 and solution_pool:
#             base = random.choice(solution_pool)
#             current = ng.shaking(base, 0)
#             restarts += 1  # NEU: Restart mitgezählt
#             no_improvement = 0

#     # ✅ Logging am Ende
#     print(f"✅ VNS abgeschlossen | Poolgröße: {len(solution_pool)} | Restarts: {restarts}")
#     return best



# import time
# import random
# from Neighborhood import NeighborhoodGenerator
# from OutputData import TourSolution

# # =============================
# # Haupt-VNS mit Solution-Pool und adaptivem Restart
# # =============================
# def run_vns(input_data, start_solution, seed=None):
#     current = start_solution
#     best = current
#     solution_pool = [start_solution]

#     ng = NeighborhoodGenerator(input_data, seed=seed)
#     k = 0
#     max_time = 180  # 3 Minuten
#     max_no_improvement = 300
#     no_improvement = 0
#     start_time = time.time()

#     while (time.time() - start_time < max_time) and (no_improvement < max_no_improvement):
#         shaken = ng.shaking(current, k)
#         improved = ng.local_search(shaken, k)

#         if improved.score > current.score:
#             current = improved
#             if improved.score > best.score:
#                 best = improved
#             solution_pool.append(current)
#             k = 0
#             no_improvement = 0
#         else:
#             k = (k + 1) % 4
#             no_improvement += 1

#         # =============================
#         # Adaptive Restart nach 200 Fehlversuchen
#         # =============================
#         if no_improvement > 200 and solution_pool:
#             base = random.choice(solution_pool)
#             current = ng.shaking(base, 0)
#             no_improvement = 0

#     return best


# import time
# from OutputData import TourSolution
# from Neighborhood import NeighborhoodGenerator


# def run_vns(input_data, start_solution, seed=None):
#     """
#     Fuehrt die Variable Neighborhood Search (VNS) aus
#     unter Einhaltung eines Zeitlimits von 3 Minuten und
#     maximal 100 erfolglosen Verbesserungsversuchen.
#     """
    
#     # Parameter
#     max_time = 180  # Sekunden
#     max_no_improvement = 300

#     # Initialisierung
#     start_time = time.time()
#     ng = NeighborhoodGenerator(input_data, seed=seed)

#     current = start_solution
#     best = current
#     k = 0
#     no_improvement = 0

#     # Haupt-VNS-Schleife
#     while (time.time() - start_time < max_time) and (no_improvement < max_no_improvement):
#         # 1. Struktur brechen
#         shaken = ng.shaking(current, k)

#         # 2. Lokal optimieren
#         improved = ng.local_search(shaken, k)

#         # 3. Entscheidung
#         if improved.is_valid and improved.score > best.score:
#             best = improved
#             current = improved
#             k = 0
#             no_improvement = 0
#         else:
#             k = (k + 1) % 3  # Drei Nachbarschaftsoperatoren
#             no_improvement += 1

#     return best
