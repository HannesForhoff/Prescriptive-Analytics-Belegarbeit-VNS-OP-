import json
import math


# Klasse für einen Knoten im Graphen
class Node:
    def __init__(self, node_id, x, y, score):
        self.id = node_id      # Eindeutige ID des Knotens
        self.x = x             # X-Koordinate
        self.y = y             # Y-Koordinate
        self.score = score     # Punktewert des Knotens


# Klasse zum Einlesen und Verwalten von Eingabedaten
class InputData:
    def __init__(self, file_path):
        self.file_path = file_path              # Pfad zur JSON-Instanz
        self.name = ""                          # Instanzname
        self.time_limit = 0                     # Maximale erlaubte Reisedauer
        self.node_count = 0                     # Anzahl der Knoten
        self.nodes = []                         # Liste von Node-Objekten
        self.distance_matrix = []               # Matrix der paarweisen Distanzen

        self.load_data()                        # Daten aus JSON laden
        self.compute_distance_matrix()          # Distanzmatrix berechnen

    
    # JSON-Datei einlesen und Knoten speichern
    def load_data(self):
        with open(self.file_path, 'r') as file:
            data = json.load(file)

        self.name = data.get("Name", "")
        self.time_limit = data.get("TimeLimit", 0)
        self.node_count = data.get("NodeCount", 0)

        for node in data.get("Nodes", []):
            node_obj = Node(
                node_id=node["Id"],
                x=node["X"],
                y=node["Y"],
                score=node["Score"]
            )
            self.nodes.append(node_obj)

        self.nodes.sort(key=lambda n: n.id)


    
    # Distanzmatrix berechnen / (euklidische Distanzen /laut Chat GPT)
    def compute_distance_matrix(self):
        self.distance_matrix = [[0.0 for _ in range(self.node_count)] for _ in range(self.node_count)]

        for i in range(self.node_count):
            for j in range(self.node_count):
                if i != j:
                    dx = self.nodes[i].x - self.nodes[j].x
                    dy = self.nodes[i].y - self.nodes[j].y
                    distance = math.hypot(dx, dy)  # Euklidische Distanz # distance = √((-4)² + (-3)²) = √(16 + 9) = √25 = 5
                    self.distance_matrix[i][j] = distance
                else:
                    self.distance_matrix[i][j] = 0.0  # Distanz zu sich selbst ist 0

    
    # Zugriff auf Distanz zweier Knoten
    def get_distance(self, node_id_1, node_id_2):
        return self.distance_matrix[node_id_1 - 1][node_id_2 - 1]  # Achtung: Node-IDs starten bei 1


# Beispielnutzung / Test
# if __name__ == '__main__':
#   data = InputData("Instanzen/Instance_1.json")
#   print(f"Instanz: {data.name}, Knoten: {data.node_count}, Zeitlimit: {data.time_limit}")
#   print("Distanz zwischen Knoten 1 und 2:", data.get_distance(1, 2))

# Für Später wenn alle 5 nacheinander eingelesen werden 
# for i in range(1, 6):
#     path = f"instances/Instance_{i}.json"
#     data = InputData(path)
#     print(f"Instanz: {data.name}, Score-Limit: {data.time_limit}, Knoten: {data.node_count}")
