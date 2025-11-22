
from ConstructiveHeuristic import generate_solution

def select_best_start_solution(input_data, methods=None, seed=None, rnd=None):
    """
    Generiert mehrere Startlösungen (z. B. greedy, best_insertion) #shortest_path, efficiency)
    und wählt die beste basierend auf dem Score für best mögliche Startlösung
    
    Parameter:
        input_data: Die Instanzdaten
        methods: Liste von Methoden-Namen als Strings. Wenn None → Standardmethoden.
        seed: Der Seed für die Zufallszahlengenerierung.
        rnd: Ein bereits initialisiertes random.Random Objekt / festgelegt meist im Notebook 

    Rückgabe:
        (beste_Lösung, gewählte_Methode)
    """
    if methods is None:
        methods = ["greedy", "best_insertion"] #["greedy", "best_insertion", "shortest_path", "efficiency"]

    candidates = []
    for method in methods:
        try:
            sol = generate_solution(input_data, method=method, seed=seed, rnd=rnd)
            candidates.append((sol, method))
        except Exception as e:
            print(f"⚠ Fehler bei Methode '{method}': {e}")

    if not candidates:
        raise RuntimeError("Keine gültige Startlösung generiert.")

    best = max(candidates, key=lambda x: x[0].score)
    return best