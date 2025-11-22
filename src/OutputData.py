

class TourSolution:
    """
    Ein Datenobjekt, das eine Tour repräsentiert.
    Es speichert nicht nur die Tour selbst sondern auch ihre Kenngrößen wie Score und Gesamtdistanz
    """
    def __init__(self, tour, time_limit):
        # SELBSTREPARATUR-LOGIK 
        # Diese Logik im Konstruktor stellt sicher, dass jede Tour, die erzeugt wird, eine syntaktisch korrekte, geschlossene Schleife ist. #
        # Das verhindert Bewertungsfehler im gesamten Algorithmus.

        # 1. Entferne Duplikate (z.B. [1, 5, 5, 1] -> [1, 5, 1])
        processed_tour = []
        visited_nodes = set()
        for node_id in tour:
            if node_id not in visited_nodes:
                processed_tour.append(node_id)
                visited_nodes.add(node_id)
        
        # 2. Erzwingt Start bei Depot (1)
        if not processed_tour or processed_tour[0] != 1:
            processed_tour.insert(0, 1)

        # 3. Stellz sicher, dass die Tour mit 1 endet (wenn sie mehr als nur das Depot enthält)
        if len(processed_tour) > 1 and processed_tour[-1] != 1:
            processed_tour.append(1)
        
        #  Sonderfall: Eine leere oder nur-Depot-Tour wird zu [1, 1].
        if len(processed_tour) == 1 and processed_tour[0] == 1:
            self.tour = [1, 1]
        else:
            self.tour = processed_tour
        

        self.time_limit = time_limit
        self.score = 0
        self.total_distance = 0.0
        self.used_time = 0.0
        self.is_valid = False

    def evaluate(self, input_data):
        """
        Berechnet Score, Distanz und Gültigkeit der Tour.
        Diese Methode wird nach jeder Änderung an einer Tour aufgerufen.
        """
        self.score = 0
        self.total_distance = 0.0
        visited = set()

        # Iteriert über alle Kanten der Tour und summiert die Distanzen.
        for i in range(len(self.tour) - 1):
            from_id = self.tour[i]
            to_id = self.tour[i + 1]
            self.total_distance += input_data.get_distance(from_id, to_id)

            # Summiert den Score für jeden einzigartigen Knoten
            if from_id not in visited:
                node = next((n for n in input_data.nodes if n.id == from_id), None)
                if node:
                    self.score += node.score
                visited.add(from_id)

        # Der Score des letzten Knotens (Depot) wird nicht gezählt da er Score 0 hat.
        
        
        self.used_time = self.total_distance
        self.is_valid = self.total_distance <= self.time_limit

    def __str__(self):
        """String-Darstellung für einfache Ausgabe im .py Notebook."""
        valid_str = "✅" if self.is_valid else "❌"
        return (f"Tour: {self.tour}\n"
                f"Score: {self.score}\n"
                f"Gesamtdistanz: {self.total_distance:.2f}\n"
                f"Verwendete Zeit: {self.used_time:.2f}\n"
                f"Gültig (<= {self.time_limit}): {valid_str}")
