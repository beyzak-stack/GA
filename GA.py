import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

# =========================
# 1. VERİYİ OKU
# =========================

file_path ="Ataturk Mahallesi- Ataturk Mah.- Edges.csv"
df = pd.read_csv(file_path)

# Kolon adlarını temizle
df.columns = df.columns.str.strip().str.lower()

# Gerekli kolonları al
df = df[
    [
        "wkt",
        "ad",
        "from_node",
        "to_node",
        "uzunluk",
        "tip1_talep",
        "tip2_talep",
        "yon",
        "avgataturk_sefer1_service",
        "avgataturk_sefer1_sira",
        "avgataturk_sefer2_service",
        "avgataturk_sefer2_sira",
        "avg_gecis",
        "azu_gecis",
        "mahalle"
    ]
].copy()

# Veri tiplerini düzelt
df["from_node"] = df["from_node"].astype(int)
df["to_node"] = df["to_node"].astype(int)
df["uzunluk"] = df["uzunluk"].astype(float)

df["tip1_talep"] = df["tip1_talep"].fillna(0).astype(int)
df["tip2_talep"] = df["tip2_talep"].fillna(0).astype(int)

df["avg_gecis"] = df["avg_gecis"].fillna(1).astype(int)
df["azu_gecis"] = df["azu_gecis"].fillna(0).astype(int)

df["yon"] = (
    df["yon"]
    .fillna("cift")
    .astype(str)
    .str.strip()
    .str.lower()
)

df["mahalle"] = (
    df["mahalle"]
    .fillna("atatürk")
    .astype(str)
    .str.strip()
    .str.lower()
)

# arc_id oluştur
df["arc_id"] = range(1, len(df) + 1)

# Edge türü oluştur
df["edge_turu"] = "travel"

df.loc[
    (df["tip1_talep"] > 0) | (df["tip2_talep"] > 0),
    "edge_turu"
] = "servis"

df.loc[
    df["mahalle"] == "depo_baglanti",
    "edge_turu"
] = "depo_baglanti"

# Veri kontrolü
for _, row in df.iterrows():

    if row["tip1_talep"] < 0 or row["tip2_talep"] < 0:
        raise ValueError(f"Arc {row['arc_id']} için negatif talep var!")

    if row["yon"] not in ["cift", "tek"]:
        raise ValueError(f"Arc {row['arc_id']} için yön değeri hatalı: {row['yon']}")

    if row["avg_gecis"] not in [0, 1]:
        raise ValueError(f"Arc {row['arc_id']} için avg_gecis 0/1 olmalı!")

    if row["azu_gecis"] not in [0, 1]:
        raise ValueError(f"Arc {row['arc_id']} için azu_gecis 0/1 olmalı!")

print("Toplam edge sayısı:", len(df))
print("Node sayısı:", len(set(df["from_node"]).union(set(df["to_node"]))))

print("\nTalep özeti:")
print("Tip1 talep olan edge:", len(df[df["tip1_talep"] > 0]))
print("Tip2 talep olan edge:", len(df[df["tip2_talep"] > 0]))
print("Toplam Tip1 talep:", df["tip1_talep"].sum())
print("Toplam Tip2 talep:", df["tip2_talep"].sum())

print("\nAraç geçiş uygunluğu:")
print("AVG geçebilir edge:", df["avg_gecis"].sum())
print("AZU geçebilir edge:", df["azu_gecis"].sum())

# =========================
# 2. GRAPH OLUŞTUR
# =========================

G = nx.DiGraph()

for _, row in df.iterrows():

    from_node = int(row["from_node"])
    to_node = int(row["to_node"])
    weight = float(row["uzunluk"])

    edge_data = {
        "weight": weight,
        "arc_id": int(row["arc_id"]),
        "edge_turu": row["edge_turu"],
        "mahalle": row["mahalle"],
        "tip1_talep": int(row["tip1_talep"]),
        "tip2_talep": int(row["tip2_talep"]),
        "avg_gecis": int(row["avg_gecis"]),
        "azu_gecis": int(row["azu_gecis"])
    }

    if row["yon"] == "cift":

        G.add_edge(from_node, to_node, **edge_data)
        G.add_edge(to_node, from_node, **edge_data)

    elif row["yon"] == "tek":

        G.add_edge(from_node, to_node, **edge_data)


print("\nGraph oluşturuldu.")
print("Graph node sayısı:", G.number_of_nodes())
print("Graph arc sayısı:", G.number_of_edges())

# Bağlantı kontrolü
if 0 in G.nodes:
    reachable_from_depot = nx.descendants(G, 0)
    print("Depodan ulaşılabilen node sayısı:", len(reachable_from_depot))
else:
    print("UYARI: Depot node 0 graph içinde yok.")
    
# =========================
# EN KISA YOLLARI HESAPLA
# =========================

shortest = dict(
    nx.all_pairs_dijkstra_path_length(
        G,
        weight="weight"
    )
)

print("En kısa yollar hesaplandı.")

# =========================
# 3. GERÇEK KOORDİNATLI GRAPH GÖRSELLEŞTİRME
# =========================

nodes_df = pd.read_csv("Ataturk Mahallesi- Ataturk Mah.- dugum_noktalari.csv")

nodes_df.columns = nodes_df.columns.str.strip().str.lower()

# WKT içinden koordinatları çıkar
nodes_df["x"] = nodes_df["wkt"].str.extract(r'POINT \(([\d\.]+)')
nodes_df["y"] = nodes_df["wkt"].str.extract(r'POINT \([\d\.]+ ([\d\.]+)\)')

nodes_df["x"] = nodes_df["x"].astype(float)
nodes_df["y"] = nodes_df["y"].astype(float)

nodes_df["id"] = nodes_df["id"].astype(int)

pos = {
    row["id"]: (row["x"], row["y"])
    for _, row in nodes_df.iterrows()
}

# Edge türlerine göre ayır
service_edges_df = df[df["edge_turu"] == "servis"]
travel_edges_df = df[df["edge_turu"] == "travel"]
depot_edges_df = df[df["edge_turu"] == "depo_baglanti"]

plt.figure(figsize=(20, 16))

# Travel yollar
nx.draw_networkx_edges(
    G,
    pos,
    edgelist=[
        (row["from_node"], row["to_node"])
        for _, row in travel_edges_df.iterrows()
    ],
    edge_color="lightgray",
    width=1,
    arrows=True,
    arrowsize=6,
    alpha=0.7
)

# Depo bağlantı yolları
nx.draw_networkx_edges(
    G,
    pos,
    edgelist=[
        (row["from_node"], row["to_node"])
        for _, row in depot_edges_df.iterrows()
    ],
    edge_color="orange",
    width=1.5,
    arrows=True,
    arrowsize=6,
    alpha=0.8
)

# Servis yolları
nx.draw_networkx_edges(
    G,
    pos,
    edgelist=[
        (row["from_node"], row["to_node"])
        for _, row in service_edges_df.iterrows()
    ],
    edge_color="red",
    width=2,
    arrows=True,
    arrowsize=8,
    alpha=0.9
)

# Node'lar
nx.draw_networkx_nodes(
    G,
    pos,
    node_size=60,
    node_color="lightblue"
)

# Depo node
if 0 in pos:
    nx.draw_networkx_nodes(
        G,
        pos,
        nodelist=[0],
        node_size=260,
        node_color="green"
    )

# Node etiketleri
nx.draw_networkx_labels(
    G,
    pos,
    font_size=5
)

plt.title(
    "Atatürk Mahallesi Yol Ağı\n"
    "Kırmızı: Servis | Gri: Travel | Turuncu: Depo Bağlantı | Yeşil: Sanal Depo",
    fontsize=16
)

plt.axis("off")
plt.tight_layout()
plt.show()    

# =========================
# 4. REQUIRED EDGE LİSTESİ
# =========================

required_edges = []

# =========================
# SEÇİLİ MAHALLELER / KDS SENARYOSU
# =========================

selected_neighborhoods = [
    "ataturk"
]
service_df = df[
    df["mahalle"].isin(selected_neighborhoods)
].copy()

for _, row in service_df.iterrows():

    # Tip 1 talebi varsa ayrı required edge oluştur
    if int(row["tip1_talep"]) > 0:

        edge = {
            "id": int(row["arc_id"]),
            "from": int(row["from_node"]),
            "to": int(row["to_node"]),
            "length": float(row["uzunluk"]),
            "demand": int(row["tip1_talep"]),
            "tip": 1,
            "yon": row["yon"],
            "avg_gecis": int(row["avg_gecis"]),
            "azu_gecis": int(row["azu_gecis"]),
            "edge_turu": row["edge_turu"]
        }

        required_edges.append(edge)

    # Tip 2 talebi varsa ayrı required edge oluştur
    if int(row["tip2_talep"]) > 0:

        edge = {
            "id": int(row["arc_id"]),
            "from": int(row["from_node"]),
            "to": int(row["to_node"]),
            "length": float(row["uzunluk"]),
            "demand": int(row["tip2_talep"]),
            "tip": 2,
            "yon": row["yon"],
            "avg_gecis": int(row["avg_gecis"]),
            "azu_gecis": int(row["azu_gecis"]),
            "edge_turu": row["edge_turu"]
        }

        required_edges.append(edge)


required_tip1 = [
    e for e in required_edges
    if e["tip"] == 1
]

required_tip2 = [
    e for e in required_edges
    if e["tip"] == 2
]


print("\nRequired edge listesi oluşturuldu.")
print("Toplam required iş:", len(required_edges))
print("Tip 1 required iş:", len(required_tip1))
print("Tip 2 required iş:", len(required_tip2))

print("Tip 1 toplam talep:", sum(e["demand"] for e in required_tip1))
print("Tip 2 toplam talep:", sum(e["demand"] for e in required_tip2))


print("\nAZU'nun erişemediği Tip2 yollar:")

problemli_tip2 = service_df[
    (df["tip2_talep"] > 0) &
    (df["azu_gecis"] == 0)
]

print(problemli_tip2[[
    "from_node",
    "to_node",
    "tip2_talep",
    "azu_gecis",
    "mahalle"
]])

# =========================
# 5. FITNESS FONKSİYONU
# =========================

depot = 0

# Gerçek depo ↔ sanal depo mesafesi
REAL_DEPOT_DISTANCE = 5600  # metre

# Atatürk için aktif araçlar
active_vehicles = [1, 3]   # AVG ve AZU

Q = {
    1: 73500,      # AVG
    2: 38500,      # AYT
    3: 165000      # AZU
}

vehicle_name = {
    1: "AVG",
    2: "AYT",
    3: "AZU"
}

vehicle_allowed_tip = {
    1: [1],   # AVG tip1
    2: [1],   # AYT tip1
    3: [2]    # AZU tip2
}

vehicle_access_col = {
    1: "avg_gecis",
    2: "avg_gecis",   # şimdilik AYT aktif değil; ileride ayt_gecis eklenebilir
    3: "azu_gecis"
}


def build_vehicle_graph(vehicle_id):
    """
    Her araç için geçebileceği edge'lerden ayrı graph oluşturur.
    Örn: AZU sadece azu_gecis = 1 olan yollardan geçebilir.
    """

    access_col = vehicle_access_col[vehicle_id]

    Gv = nx.DiGraph()

    for _, row in df.iterrows():

        if int(row[access_col]) != 1:
            continue

        from_node = int(row["from_node"])
        to_node = int(row["to_node"])
        weight = float(row["uzunluk"])

        edge_data = {
            "weight": weight,
            "arc_id": int(row["arc_id"]),
            "edge_turu": row["edge_turu"],
            "mahalle": row["mahalle"]
        }

        if row["yon"] == "cift":
            Gv.add_edge(from_node, to_node, **edge_data)
            Gv.add_edge(to_node, from_node, **edge_data)

        elif row["yon"] == "tek":
            Gv.add_edge(from_node, to_node, **edge_data)

    return Gv


vehicle_graph = {}
vehicle_shortest = {}

for vehicle_id in active_vehicles:

    vehicle_graph[vehicle_id] = build_vehicle_graph(vehicle_id)

    vehicle_shortest[vehicle_id] = dict(
        nx.all_pairs_dijkstra_path_length(
            vehicle_graph[vehicle_id],
            weight="weight"
        )
    )

    print(
        f"{vehicle_name[vehicle_id]} graph oluşturuldu:",
        vehicle_graph[vehicle_id].number_of_nodes(),
        "node,",
        vehicle_graph[vehicle_id].number_of_edges(),
        "arc"
    )


def calculate_fitness(edge_list, vehicle_id):

    total_cost = 0
    current_node = depot
    current_load = 0
    routes = []
    current_route = []

    shortest_v = vehicle_shortest[vehicle_id]

    for edge in edge_list:

        # Araç konteyner tipi uygunluğu
        if edge["tip"] not in vehicle_allowed_tip[vehicle_id]:
            raise ValueError(
                f"{vehicle_name[vehicle_id]} aracı "
                f"tip {edge['tip']} edge'ini servis edemez!"
            )

        # Araç bu servis edge'ine girebiliyor mu?
        access_col = vehicle_access_col[vehicle_id]

        edge_row = df[df["arc_id"] == edge["id"]].iloc[0]

        if int(edge_row[access_col]) != 1:
            raise ValueError(
                f"{vehicle_name[vehicle_id]} aracı "
                f"{edge['id']} numaralı edge'e erişemez!"
            )

        demand = edge["demand"]

        # Kapasite dolarsa sanal depoya dön
        if current_load + demand > Q[vehicle_id]:

            if current_route:

                if current_node not in shortest_v or depot not in shortest_v[current_node]:
                    return float("inf"), 0, []

                total_cost += shortest_v[current_node][depot]
                total_cost += REAL_DEPOT_DISTANCE   # sanal depo → gerçek depo

                routes.append(current_route)

            current_route = []
            current_load = 0
            current_node = depot

            total_cost += REAL_DEPOT_DISTANCE       # gerçek depo → sanal depo

        u = edge["from"]
        v = edge["to"]

        possible_dirs = [(u, v)]

        if edge["yon"] == "cift":
            possible_dirs.append((v, u))

        best_cost = float("inf")
        best_dir = None

        for start, end in possible_dirs:

            # Araç current_node'dan servis başlangıcına ulaşabiliyor mu?
            if current_node not in shortest_v:
                continue

            if start not in shortest_v[current_node]:
                continue

            cost = shortest_v[current_node][start] + edge["length"]

            if cost < best_cost:
                best_cost = cost
                best_dir = (start, end)

        if best_dir is None:
            return float("inf"), 0, []

        total_cost += best_cost
        current_load += demand
        current_node = best_dir[1]

        current_route.append({
            "edge_id": edge["id"],
            "direction": best_dir
        })

    # Son rota sanal depoya dönsün
    if current_route:

        if current_node not in shortest_v or depot not in shortest_v[current_node]:
            return float("inf"), 0, []

        total_cost += shortest_v[current_node][depot]

        # son dönüş: sanal depo → gerçek depo
        total_cost += REAL_DEPOT_DISTANCE

        routes.append(current_route)

    # ilk çıkış: gerçek depo → sanal depo
    if routes:
        total_cost += REAL_DEPOT_DISTANCE

    fitness_score = 1 / (total_cost + 1)

    return total_cost, fitness_score, routes

print("\nAZU erişim kontrolü:")

G_azu = vehicle_graph[3]
shortest_azu = vehicle_shortest[3]

for edge in required_tip2:

    u = edge["from"]
    v = edge["to"]

    depot_to_u = depot in shortest_azu and u in shortest_azu[depot]
    depot_to_v = depot in shortest_azu and v in shortest_azu[depot]

    u_to_depot = u in shortest_azu and depot in shortest_azu[u]
    v_to_depot = v in shortest_azu and depot in shortest_azu[v]

    if not ((depot_to_u or depot_to_v) and (u_to_depot or v_to_depot)):

        print(
            "Ulaşılamayan Tip2 edge:",
            "edge_id:", edge["id"],
            "from:", u,
            "to:", v,
            "demand:", edge["demand"]
        )
# =========================
# 6. FITNESS TESTİ
# =========================

# Tip 1 standart konteynerler için AVG aracı
test_cost_avg, test_fitness_avg, test_routes_avg = calculate_fitness(
    required_tip1,
    vehicle_id=1
)

# Tip 2 yerüstü konteynerler için AZU aracı
test_cost_azu, test_fitness_azu, test_routes_azu = calculate_fitness(
    required_tip2,
    vehicle_id=3
)

print("\n===== FITNESS TEST SONUÇLARI =====")

print("\nAVG - Tip 1:")
print("Toplam maliyet:", test_cost_avg)
print("Fitness skoru:", test_fitness_avg)
print("Rota sayısı:", len(test_routes_avg))

print("\nAZU - Tip 2:")
print("Toplam maliyet:", test_cost_azu)
print("Fitness skoru:", test_fitness_azu)
print("Rota sayısı:", len(test_routes_azu))


# =========================
# 6.1 ROTA DETAY ANALİZİ
# =========================

def analyze_routes(routes, required_edges, vehicle_id):

    edge_dict = {
        e["id"]: e
        for e in required_edges
    }

    detailed_rows = []

    Gv = vehicle_graph[vehicle_id]
    shortest_v = vehicle_shortest[vehicle_id]

    for route_num, route in enumerate(routes, start=1):

        current_node = depot
        route_load = 0

        # Gerçek depo -> sanal depo başlangıç hareketi
        detailed_rows.append({
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "route_no": route_num,
            "step_no": "START",
            "from_node": "REAL_DEPOT",
            "to_service_start": depot,
            "travel_path": "REAL_DEPOT_TO_VIRTUAL_DEPOT",
            "travel_distance": REAL_DEPOT_DISTANCE,
            "serviced_edge": None,
            "service_direction": "REAL_DEPOT_TO_VIRTUAL_DEPOT",
            "service_distance": 0,
            "demand": 0,
            "cumulative_load": 0
        })

        for step_num, step in enumerate(route, start=1):

            edge_id = step["edge_id"]
            start_node, end_node = step["direction"]

            edge = edge_dict[edge_id]

            travel_path = nx.shortest_path(
                Gv,
                source=current_node,
                target=start_node,
                weight="weight"
            )

            travel_distance = shortest_v[current_node][start_node]

            route_load += edge["demand"]

            detailed_rows.append({
                "vehicle_id": vehicle_id,
                "vehicle_name": vehicle_name[vehicle_id],
                "route_no": route_num,
                "step_no": step_num,
                "from_node": current_node,
                "to_service_start": start_node,
                "travel_path": travel_path,
                "travel_distance": travel_distance,
                "serviced_edge": edge_id,
                "service_direction": f"{start_node}->{end_node}",
                "service_distance": edge["length"],
                "demand": edge["demand"],
                "cumulative_load": route_load
            })

            current_node = end_node

        return_path = nx.shortest_path(
            Gv,
            source=current_node,
            target=depot,
            weight="weight"
        )

        return_distance = shortest_v[current_node][depot]

        detailed_rows.append({
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "route_no": route_num,
            "step_no": "RETURN",
            "from_node": current_node,
            "to_service_start": depot,
            "travel_path": return_path,
            "travel_distance": return_distance,
            "serviced_edge": None,
            "service_direction": "RETURN_TO_VIRTUAL_DEPOT",
            "service_distance": 0,
            "demand": 0,
            "cumulative_load": route_load
        })

        # Sanal depo -> gerçek depo dönüş hareketi
        detailed_rows.append({
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "route_no": route_num,
            "step_no": "END",
            "from_node": depot,
            "to_service_start": "REAL_DEPOT",
            "travel_path": "VIRTUAL_DEPOT_TO_REAL_DEPOT",
            "travel_distance": REAL_DEPOT_DISTANCE,
            "serviced_edge": None,
            "service_direction": "VIRTUAL_DEPOT_TO_REAL_DEPOT",
            "service_distance": 0,
            "demand": 0,
            "cumulative_load": route_load
        })

    return pd.DataFrame(detailed_rows)


# =========================
# 6.2 TEST ROTALARINI ANALİZ ET
# =========================

avg_df = analyze_routes(
    test_routes_avg,
    required_tip1,
    vehicle_id=1
)

azu_df = analyze_routes(
    test_routes_azu,
    required_tip2,
    vehicle_id=3
)

print("\nAVG rota detay ilk satırlar:")
print(avg_df.head())

print("\nAZU rota detay ilk satırlar:")
print(azu_df.head())


# =========================
# 6.3 ROTA GÖRSELLEŞTİRME
# =========================

def plot_vehicle_routes(route_df, vehicle_label, vehicle_id):

    Gv = vehicle_graph[vehicle_id]

    for route_no in sorted(route_df["route_no"].unique()):

        selected_route_df = route_df[
            route_df["route_no"] == route_no
        ]

        plt.figure(figsize=(20, 16))

        nx.draw_networkx_edges(
            Gv,
            pos,
            edge_color="lightgray",
            width=1,
            arrows=True,
            arrowsize=8
        )

        nx.draw_networkx_nodes(
            Gv,
            pos,
            node_size=80,
            node_color="lightblue"
        )

        if depot in pos:
            nx.draw_networkx_nodes(
                Gv,
                pos,
                nodelist=[depot],
                node_size=260,
                node_color="green"
            )

        nx.draw_networkx_labels(
            Gv,
            pos,
            font_size=6
        )

        for _, row in selected_route_df.iterrows():

            path = row["travel_path"]

            if isinstance(path, list) and len(path) >= 2:

                path_edges = list(zip(path[:-1], path[1:]))

                nx.draw_networkx_edges(
                    Gv,
                    pos,
                    edgelist=path_edges,
                    edge_color="blue",
                    width=2,
                    arrows=True,
                    arrowsize=8
                )

        for _, row in selected_route_df.iterrows():

            if isinstance(row["service_direction"], str) and "->" in row["service_direction"]:

                if row["service_direction"] in [
                    "REAL_DEPOT_TO_VIRTUAL_DEPOT",
                    "VIRTUAL_DEPOT_TO_REAL_DEPOT",
                    "RETURN_TO_VIRTUAL_DEPOT"
                ]:
                    continue

                start_node, end_node = map(
                    int,
                    row["service_direction"].split("->")
                )

                nx.draw_networkx_edges(
                    Gv,
                    pos,
                    edgelist=[(start_node, end_node)],
                    edge_color="red",
                    width=3,
                    arrows=True,
                    arrowsize=10
                )

        plt.title(
            f"{vehicle_label} - Rota {route_no}",
            fontsize=18
        )

        plt.axis("off")
        plt.tight_layout()
        plt.show()

if not avg_df.empty and "route_no" in avg_df.columns:
    plot_vehicle_routes(avg_df, vehicle_label="AVG", vehicle_id=1)
else:
    print("AVG için çizilecek rota bulunamadı.")

if not azu_df.empty and "route_no" in azu_df.columns:
    plot_vehicle_routes(azu_df, vehicle_label="AZU", vehicle_id=3)
else:
    print("AZU için çizilecek rota bulunamadı.")

# =========================
# 7. GA - BİREY VE POPÜLASYON OLUŞTURMA
# =========================

import random

def create_individual(edge_list):
    individual = edge_list[:]
    random.shuffle(individual)
    return individual


def create_population(
    edge_list,
    population_size,
    seed_individual=None
):

    population = []

    # Başlangıç çözümünü popülasyona ekle
    if seed_individual is not None:
        population.append(seed_individual[:])

    # Kalan bireyleri random oluştur
    while len(population) < population_size:

        individual = create_individual(edge_list)
        population.append(individual)

    return population


# =========================
# 7.1 POPÜLASYON TESTİ
# =========================

population_avg = create_population(
    required_tip1,
    population_size=50
)

population_azu = create_population(
    required_tip2,
    population_size=30
)

print("\nAVG popülasyon:")
print("Birey sayısı:", len(population_avg))
print("Bir bireydeki edge sayısı:", len(population_avg[0]))

print("\nAZU popülasyon:")
print("Birey sayısı:", len(population_azu))
print("Bir bireydeki edge sayısı:", len(population_azu[0]))


# =========================
# 7.2 POPÜLASYON FITNESS DEĞERLERİNİ HESAPLA
# =========================

fitness_avg = []
fitness_azu = []

costs_avg = []
costs_azu = []

routes_avg_population = []
routes_azu_population = []

# AVG
for individual in population_avg:
    cost, fitness, routes = calculate_fitness(
        individual,
        vehicle_id=1
    )
    fitness_avg.append(fitness)
    costs_avg.append(cost)
    routes_avg_population.append(routes)

# AZU
for individual in population_azu:
    cost, fitness, routes = calculate_fitness(
        individual,
        vehicle_id=3
    )
    fitness_azu.append(fitness)
    costs_azu.append(cost)
    routes_azu_population.append(routes)


print("\n===== POPÜLASYON FITNESS SONUÇLARI =====")

print("\nAVG:")
print("En iyi maliyet:", min(costs_avg))
print("En kötü maliyet:", max(costs_avg))
print("Ortalama maliyet:", sum(costs_avg) / len(costs_avg))

print("\nAZU:")
print("En iyi maliyet:", min(costs_azu))
print("En kötü maliyet:", max(costs_azu))
print("Ortalama maliyet:", sum(costs_azu) / len(costs_azu))


# AVG
print("\nAVG:")
best_avg_fitness = max(fitness_avg)
worst_avg_fitness = min(fitness_avg)

print("En iyi fitness:", best_avg_fitness)
print("En kötü fitness:", worst_avg_fitness)
print("En iyi maliyet:", round((1 / best_avg_fitness) - 1, 2))
print("En kötü maliyet:", round((1 / worst_avg_fitness) - 1, 2))


# AZU
print("\nAZU:")
best_azu_fitness = max(fitness_azu)
worst_azu_fitness = min(fitness_azu)

print("En iyi fitness:", best_azu_fitness)
print("En kötü fitness:", worst_azu_fitness)
print("En iyi maliyet:", round((1 / best_azu_fitness) - 1, 2))
print("En kötü maliyet:", round((1 / worst_azu_fitness) - 1, 2))


# =========================
# 7.3 CONSTRAINT CHECK
# =========================

def check_solution_constraints(routes, required_edges, vehicle_id):

    required_ids = set(e["id"] for e in required_edges)
    served_ids = []

    capacity_ok = True
    depot_ok = True
    type_ok = True
    route_loads = []

    for route in routes:

        route_load = 0

        for step in route:

            edge_id = step["edge_id"]
            served_ids.append(edge_id)

            edge = next(
                e for e in required_edges
                if e["id"] == edge_id
            )

            route_load += edge["demand"]

            if edge["tip"] not in vehicle_allowed_tip[vehicle_id]:
                type_ok = False

        if route_load > Q[vehicle_id]:
            capacity_ok = False

        route_loads.append(route_load)

    served_ids_set = set(served_ids)

    all_required_served = served_ids_set == required_ids
    no_duplicate_service = len(served_ids) == len(served_ids_set)

    feasible = (
        all_required_served
        and no_duplicate_service
        and capacity_ok
        and depot_ok
        and type_ok
    )

    return {
        "vehicle_id": vehicle_id,
        "vehicle_name": vehicle_name[vehicle_id],
        "feasible": feasible,
        "all_required_served": all_required_served,
        "no_duplicate_service": no_duplicate_service,
        "capacity_ok": capacity_ok,
        "depot_ok": depot_ok,
        "type_ok": type_ok,
        "served_count": len(served_ids),
        "required_count": len(required_ids),
        "route_count": len(routes),
        "route_loads": route_loads
    }


check_avg = check_solution_constraints(
    test_routes_avg,
    required_tip1,
    vehicle_id=1
)

check_azu = check_solution_constraints(
    test_routes_azu,
    required_tip2,
    vehicle_id=3
)

print("\nAVG feasibility:")
print(check_avg)

print("\nAZU feasibility:")
print(check_azu)

# =========================
# 8. GA - SELECTION
# =========================

def roulette_wheel_selection_index(fitness_values):

    total_fitness = sum(fitness_values)

    if total_fitness == 0:

        selected_index = random.choice(
            range(len(fitness_values))
        )

    else:

        selected_index = random.choices(
            range(len(fitness_values)),
            weights=fitness_values,
            k=1
        )[0]

    return selected_index


# =========================
# ROULETTE WHEEL PARENT SELECTION TESTİ
# =========================

# AVG
parent1_idx_avg = roulette_wheel_selection_index(fitness_avg)
parent2_idx_avg = roulette_wheel_selection_index(fitness_avg)

# AZU
parent1_idx_azu = roulette_wheel_selection_index(fitness_azu)
parent2_idx_azu = roulette_wheel_selection_index(fitness_azu)

print("\nAVG seçilen parent indexleri:")
print(parent1_idx_avg, parent2_idx_avg)

print("\nAZU seçilen parent indexleri:")
print(parent1_idx_azu, parent2_idx_azu)


# =========================
# 9. GA - ORDERED CROSSOVER (OX)
# =========================

def ordered_crossover(parent1, parent2):

    size = len(parent1)

    child = [None] * size

    start, end = sorted(
        random.sample(range(size), 2)
    )

    child[start:end+1] = parent1[start:end+1]

    parent2_remaining = [
        edge for edge in parent2
        if edge not in child
    ]

    current_pos = 0

    for i in range(size):

        if child[i] is None:

            child[i] = parent2_remaining[current_pos]
            current_pos += 1

    return child


# =========================
# TEST - AVG CROSSOVER
# =========================

parent1_avg = population_avg[parent1_idx_avg]
parent2_avg = population_avg[parent2_idx_avg]

child_avg = ordered_crossover(
    parent1_avg,
    parent2_avg
)

child_cost_avg, child_fitness_avg, _ = calculate_fitness(
    child_avg,
    vehicle_id=1
)


# =========================
# TEST - AZU CROSSOVER
# =========================

parent1_azu = population_azu[parent1_idx_azu]
parent2_azu = population_azu[parent2_idx_azu]

child_azu = ordered_crossover(
    parent1_azu,
    parent2_azu
)

child_cost_azu, child_fitness_azu, _ = calculate_fitness(
    child_azu,
    vehicle_id=3
)


# =========================
# SONUÇLAR
# =========================

print("\n===== CROSSOVER SONUÇLARI =====")

print("\nAVG:")
print("Child cost:", child_cost_avg)
print("Child fitness:", child_fitness_avg)
print("Child edge sayısı:", len(child_avg))

print("\nAZU:")
print("Child cost:", child_cost_azu)
print("Child fitness:", child_fitness_azu)
print("Child edge sayısı:", len(child_azu))

# =========================
# 10. GA - SWAP MUTATION
# =========================

def swap_mutation(individual, mutation_rate=0.15):

    mutated = individual[:]

    if random.random() < mutation_rate:

        i, j = random.sample(
            range(len(mutated)),
            2
        )

        mutated[i], mutated[j] = (
            mutated[j],
            mutated[i]
        )

    return mutated


# =========================
# TEST - SWAP MUTATION
# =========================

# AVG
mutated_child_avg = swap_mutation(
    child_avg,
    mutation_rate=1.00
)

# AZU
mutated_child_azu = swap_mutation(
    child_azu,
    mutation_rate=1.00
)


mutated_cost_avg, mutated_fitness_avg, _ = calculate_fitness(
    mutated_child_avg,
    vehicle_id=1
)

mutated_cost_azu, mutated_fitness_azu, _ = calculate_fitness(
    mutated_child_azu,
    vehicle_id=3
)


print("\n===== SWAP MUTATION SONUÇLARI =====")

# AVG
print("\nAVG:")
print("Crossover child cost:", child_cost_avg)
print("Swap sonrası cost:", mutated_cost_avg)
print("Swap sonrası fitness:", mutated_fitness_avg)
print("Edge sayısı:", len(mutated_child_avg))

# AZU
print("\nAZU:")
print("Crossover child cost:", child_cost_azu)
print("Swap sonrası cost:", mutated_cost_azu)
print("Swap sonrası fitness:", mutated_fitness_azu)
print("Edge sayısı:", len(mutated_child_azu))


print("\nAVG test fitness:", test_fitness_avg)
print("AZU test fitness:", test_fitness_azu)

# =========================
# LOCAL SEARCH - INSERTION IMPROVEMENT
# =========================

def insertion_local_search(
    individual,
    vehicle_id,
    max_trials=30
):

    best_individual = individual[:]

    best_cost, _, _ = calculate_fitness(
        best_individual,
        vehicle_id
    )

    for _ in range(max_trials):

        candidate = best_individual[:]

        i, j = random.sample(
            range(len(candidate)),
            2
        )

        selected_edge = candidate.pop(i)
        candidate.insert(j, selected_edge)

        candidate_cost, _, _ = calculate_fitness(
            candidate,
            vehicle_id
        )

        if candidate_cost < best_cost:
            best_individual = candidate[:]
            best_cost = candidate_cost

    return best_individual

# =========================
# 11. FULL GA DÖNGÜSÜ
# =========================
def run_genetic_algorithm(
    required_edge_list,
    vehicle_id,
    population_size=100,
    generations=100,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=30
):

    population = create_population(
    required_edge_list,
    population_size,
    seed_individual=required_edge_list
)

    best_individual = None
    best_cost = float("inf")
    best_fitness = 0
    best_routes = None

    history = []

    no_improvement_counter = 0

    for generation in range(1, generations + 1):

        results = []

        improved_this_generation = False

        for individual in population:

            cost, fitness, routes = calculate_fitness(
                individual,
                vehicle_id
            )

            results.append({
                "individual": individual,
                "cost": cost,
                "fitness": fitness,
                "routes": routes
            })

            if cost < best_cost:

                best_cost = cost
                best_fitness = fitness
                best_individual = individual[:]
                best_routes = routes

                improved_this_generation = True

        if improved_this_generation:
            no_improvement_counter = 0
        else:
            no_improvement_counter += 1

        avg_cost = (
            sum(r["cost"] for r in results)
            / len(results)
        )

        results = sorted(
            results,
            key=lambda x: x["fitness"],
            reverse=True
        )

        new_population = []

        # =========================
        # ELITISM
        # =========================

        elites = results[:elite_size]

        for elite in elites:
            new_population.append(
                elite["individual"][:]
            )

        fitness_values = [
            r["fitness"]
            for r in results
        ]

        sorted_population = [
            r["individual"]
            for r in results
        ]

        # =========================
        # YENİ NESİL ÜRET
        # =========================

        while len(new_population) < population_size:

            parent1_index = roulette_wheel_selection_index(
                fitness_values
            )

            parent2_index = roulette_wheel_selection_index(
                fitness_values
            )

            while parent2_index == parent1_index:

                parent2_index = roulette_wheel_selection_index(
                    fitness_values
                )

            parent1 = sorted_population[parent1_index]
            parent2 = sorted_population[parent2_index]

            # CROSSOVER
            if random.random() < crossover_rate:

                child = ordered_crossover(
                    parent1,
                    parent2
                )

            else:
                child = parent1[:]

            # MUTATION
            child = swap_mutation(
                child,
                mutation_rate=mutation_rate
            )

            # LOCAL SEARCH
            child = insertion_local_search(
                child,
                vehicle_id,
                max_trials=3
            )

            new_population.append(child)

        population = new_population

        history.append({
            "generation": generation,
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "best_cost": best_cost,
            "avg_cost": avg_cost,
            "best_fitness": best_fitness,
            "no_improvement": no_improvement_counter
        })

        if generation % 10 == 0:

            print(
                f"Generation {generation} | "
                f"{vehicle_name[vehicle_id]} | "
                f"Best cost: {best_cost} | "
                f"Best fitness: {best_fitness} | "
                f"No improvement: {no_improvement_counter}"
            )

        # =========================
        # EARLY STOPPING
        # =========================

        if no_improvement_counter >= patience:

            print(
                f"Early stopping: "
                f"{vehicle_name[vehicle_id]} için "
                f"{patience} nesildir iyileşme yok. "
                f"Generation {generation}'da durdu."
            )

            break

    history_df = pd.DataFrame(history)

    return (
        best_cost,
        best_fitness,
        best_routes,
        best_individual,
        history_df
    )

# =========================
# 12. FULL GA ÇALIŞTIR
# =========================

best_cost_avg, best_fitness_avg, best_routes_avg, best_individual_avg, history_avg = run_genetic_algorithm(
    required_tip1,
    vehicle_id=1,
    population_size=20,
    generations=50,
    crossover_rate=0.70,
    mutation_rate=0.20,
    elite_size=2,
    patience=8
)

best_cost_azu, best_fitness_azu, best_routes_azu, best_individual_azu, history_azu = run_genetic_algorithm(
    required_tip2,
    vehicle_id=3,
    population_size=15,
    generations=40,
    crossover_rate=0.70,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)


print("\n===== FULL GA SONUÇLARI =====")

print("\nAVG:")
print("En iyi maliyet:", best_cost_avg)
print("En iyi fitness:", best_fitness_avg)
print("Rota sayısı:", len(best_routes_avg))

print("\nAZU:")
print("En iyi maliyet:", best_cost_azu)
print("En iyi fitness:", best_fitness_azu)
print("Rota sayısı:", len(best_routes_azu))

# =========================
# 13. EN İYİ GA ROTALARINI DETAYLI ANALİZ ET
# =========================

best_avg_df = analyze_routes(
    best_routes_avg,
    required_tip1,
    vehicle_id=1
)

best_azu_df = analyze_routes(
    best_routes_azu,
    required_tip2,
    vehicle_id=3
)

best_avg_df["total_cost"] = best_cost_avg
best_avg_df["fitness_score"] = best_fitness_avg

best_azu_df["total_cost"] = best_cost_azu
best_azu_df["fitness_score"] = best_fitness_azu

# =========================
# 14. ROTA BAZLI KAPASİTE ANALİZİ
# =========================

def route_capacity_summary(route_detail_df, vehicle_id):

    summary = (
        route_detail_df
        .groupby("route_no")
        .agg(
            route_load=("demand", "sum"),
            service_distance=("service_distance", "sum"),
            travel_distance=("travel_distance", "sum")
        )
        .reset_index()
    )

    summary["vehicle_id"] = vehicle_id

    summary["vehicle_name"] = vehicle_name[vehicle_id]

    summary["vehicle_capacity"] = Q[vehicle_id]

    summary["unused_capacity"] = (
        summary["vehicle_capacity"]
        - summary["route_load"]
    )

    summary["capacity_utilization"] = (
        summary["route_load"]
        / summary["vehicle_capacity"]
    )

    summary["capacity_utilization_percent"] = (
        summary["capacity_utilization"] * 100
    ).round(2)

    summary["capacity_ok"] = (
        summary["route_load"]
        <= summary["vehicle_capacity"]
    )

    summary["route_total_distance"] = (
        summary["service_distance"]
        + summary["travel_distance"]
    )

    return summary


capacity_avg_df = route_capacity_summary(
    best_avg_df,
    vehicle_id=1
)

capacity_azu_df = route_capacity_summary(
    best_azu_df,
    vehicle_id=3
)


# =========================
# 15. GA YAKINSAMA GRAFİĞİ
# =========================

plt.figure(figsize=(10, 6))

plt.plot(
    history_avg["generation"],
    history_avg["best_cost"],
    label="Best Cost"
)

plt.plot(
    history_avg["generation"],
    history_avg["avg_cost"],
    label="Average Cost"
)

plt.xlabel("Generation")
plt.ylabel("Cost")

plt.title("AVG GA Yakınsama Grafiği")

plt.legend()
plt.grid(True)
plt.show()


plt.figure(figsize=(10, 6))

plt.plot(
    history_azu["generation"],
    history_azu["best_cost"],
    label="Best Cost"
)

plt.plot(
    history_azu["generation"],
    history_azu["avg_cost"],
    label="Average Cost"
)

plt.xlabel("Generation")
plt.ylabel("Cost")

plt.title("AZU GA Yakınsama Grafiği")

plt.legend()
plt.grid(True)
plt.show()

# =========================
# 16. MULTI RUN ANALYSIS
# =========================

def multi_run_ga(
    required_edge_list,
    vehicle_id,
    run_count=20,
    population_size=100,
    generations=300,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=30
):

    multi_run_results = []

    best_overall_cost = float("inf")
    best_overall_fitness = 0
    best_overall_routes = None
    best_overall_individual = None
    best_overall_run = None

    for run in range(1, run_count + 1):

        print(
            f"\n===== RUN {run} | "
            f"{vehicle_name[vehicle_id]} ====="
        )

        (
            best_cost,
            best_fitness,
            best_routes,
            best_individual,
            history_df

        ) = run_genetic_algorithm(

            required_edge_list=required_edge_list,
            vehicle_id=vehicle_id,
            population_size=population_size,
            generations=generations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            elite_size=elite_size,
            patience=patience
        )

        multi_run_results.append({
            "run_no": run,
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "best_cost": best_cost,
            "best_fitness": best_fitness,
            "route_count": len(best_routes),
            "last_generation": history_df["generation"].max(),
            "best_sequence": [
                edge["id"]
                for edge in best_individual
            ]
        })

        if best_cost < best_overall_cost:

            best_overall_cost = best_cost
            best_overall_fitness = best_fitness
            best_overall_routes = best_routes
            best_overall_individual = best_individual
            best_overall_run = run

    multi_run_df = pd.DataFrame(
        multi_run_results
    )

    summary_df = pd.DataFrame([{
        "vehicle_id": vehicle_id,
        "vehicle_name": vehicle_name[vehicle_id],
        "run_count": run_count,
        "best_cost": multi_run_df["best_cost"].min(),
        "worst_cost": multi_run_df["best_cost"].max(),
        "average_cost": multi_run_df["best_cost"].mean(),
        "std_cost": multi_run_df["best_cost"].std(),
        "best_run": best_overall_run
    }])

    return (
        multi_run_df,
        summary_df,
        best_overall_cost,
        best_overall_fitness,
        best_overall_routes,
        best_overall_individual
    )

# =========================
# 17. MULTI RUN ÇALIŞTIR
# =========================

avg_multi_df, avg_summary_df, final_best_cost_avg, final_best_fitness_avg, final_best_routes_avg, final_best_individual_avg = multi_run_ga(
    required_edge_list=required_tip1,
    vehicle_id=1,
    run_count=3,
    population_size=20,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=8
)

azu_multi_df, azu_summary_df, final_best_cost_azu, final_best_fitness_azu, final_best_routes_azu, final_best_individual_azu = multi_run_ga(
    required_edge_list=required_tip2,
    vehicle_id=3,
    run_count=3,
    population_size=15,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)

print("\n===== AVG MULTI RUN SONUÇLARI =====")
print(avg_multi_df)

print("\n===== AVG ÖZET =====")
print(avg_summary_df)

print("\n===== AZU MULTI RUN SONUÇLARI =====")
print(azu_multi_df)

print("\n===== AZU ÖZET =====")
print(azu_summary_df)

print("\n===== GENEL EN İYİ SONUÇ =====")
print("AVG en iyi maliyet:", final_best_cost_avg)
print("AZU en iyi maliyet:", final_best_cost_azu)
print("Toplam en iyi maliyet:", final_best_cost_avg + final_best_cost_azu)

final_best_avg_df = analyze_routes(
    final_best_routes_avg,
    required_tip1,
    vehicle_id=1
)

final_best_azu_df = analyze_routes(
    final_best_routes_azu,
    required_tip2,
    vehicle_id=3
)

final_best_avg_df["total_cost"] = final_best_cost_avg
final_best_avg_df["fitness_score"] = final_best_fitness_avg

final_best_azu_df["total_cost"] = final_best_cost_azu
final_best_azu_df["fitness_score"] = final_best_fitness_azu

final_capacity_avg_df = route_capacity_summary(
    final_best_avg_df,
    vehicle_id=1
)

final_capacity_azu_df = route_capacity_summary(
    final_best_azu_df,
    vehicle_id=3
)

print("\nAVG en iyi edge sıralaması:")
print([edge["id"] for edge in final_best_individual_avg])

print("\nAZU en iyi edge sıralaması:")
print([edge["id"] for edge in final_best_individual_azu])

# =========================
# 18. GA SONUÇLARINI KML'YE AKTAR
# =========================

import os

kml_folder = "kml_outputs"

os.makedirs(
    kml_folder,
    exist_ok=True
)


def parse_linestring(wkt):

    wkt = (
        wkt
        .replace("LINESTRING (", "")
        .replace(")", "")
    )

    coords = []

    for pair in wkt.split(","):

        lon, lat = pair.strip().split(" ")

        coords.append((
            float(lon),
            float(lat)
        ))

    return coords


def create_line_geometry_dict(edge_csv_path):

    edge_geo_df = pd.read_csv(edge_csv_path)

    edge_geo_df.columns = (
        edge_geo_df.columns
        .str.strip()
        .str.lower()
    )

    if "yön" in edge_geo_df.columns:
        edge_geo_df = edge_geo_df.rename(
            columns={"yön": "yon"}
        )

    line_geometry_by_arc = {}
    line_geometry_by_nodes = {}

    for idx, row in edge_geo_df.iterrows():

        arc_id = idx + 1

        i = int(row["from_node"])
        j = int(row["to_node"])

        coords = parse_linestring(
            row["wkt"]
        )

        line_geometry_by_arc[arc_id] = coords
        line_geometry_by_nodes[(i, j)] = coords

        if str(row["yon"]).strip().lower() == "cift":

            line_geometry_by_nodes[(j, i)] = list(
                reversed(coords)
            )

    return (
        line_geometry_by_arc,
        line_geometry_by_nodes
    )


line_geometry_by_arc, line_geometry_by_nodes = create_line_geometry_dict(
    file_path
)


def build_kml_header(kml_name):

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>{kml_name}</name>

<Style id="service">
<LineStyle>
<color>ff0000ff</color>
<width>5</width>
</LineStyle>
</Style>

<Style id="travel">
<LineStyle>
<color>ffff0000</color>
<width>4</width>
</LineStyle>
</Style>
"""


def build_kml_footer():

    return """
</Document>
</kml>
"""


def add_linestring_placemark(
    kml,
    name,
    style_id,
    coords
):

    coord_text = "\n".join(
        f"{lon},{lat},0"
        for lon, lat in coords
    )

    kml += f"""
<Placemark>
<name>{name}</name>
<styleUrl>#{style_id}</styleUrl>
<LineString>
<tessellate>1</tessellate>
<coordinates>
{coord_text}
</coordinates>
</LineString>
</Placemark>
"""

    return kml


def write_ga_kml(
    route_df,
    vehicle_label,
    output_path
):

    kml = build_kml_header(
        f"{vehicle_label} GA Rota Sonucu"
    )

    for _, row in route_df.iterrows():

        route_no = row["route_no"]
        step_no = row["step_no"]

        # =========================
        # TRAVEL PATH
        # =========================

        path = row["travel_path"]

        if isinstance(path, list):

            for a, b in zip(path[:-1], path[1:]):

                if (a, b) not in line_geometry_by_nodes:

                    print(
                        f"UYARI: travel path için geometri yok: {a}->{b}"
                    )

                    continue

                coords = line_geometry_by_nodes[(a, b)]

                kml = add_linestring_placemark(
                    kml=kml,
                    name=(
                        f"{vehicle_label} | "
                        f"Rota {route_no} | "
                        f"Adım {step_no} | "
                        f"Travel {a}->{b}"
                    ),
                    style_id="travel",
                    coords=coords
                )

        # =========================
        # SERVİS EDGE
        # =========================

        service_direction = row["service_direction"]

        if not isinstance(service_direction, str):
            continue

        if service_direction in [
            "REAL_DEPOT_TO_VIRTUAL_DEPOT",
            "VIRTUAL_DEPOT_TO_REAL_DEPOT",
            "RETURN_TO_VIRTUAL_DEPOT"
        ]:
            continue

        if "->" not in service_direction:
            continue

        if pd.isna(row["serviced_edge"]):
            continue

        edge_id = int(row["serviced_edge"])

        if edge_id not in line_geometry_by_arc:

            print(
                f"UYARI: servis edge geometrisi yok: edge_id {edge_id}"
            )

            continue

        coords = line_geometry_by_arc[edge_id]

        start_node, end_node = map(
            int,
            service_direction.split("->")
        )

        edge_row = df[
            df["arc_id"] == edge_id
        ].iloc[0]

        csv_from = int(edge_row["from_node"])
        csv_to = int(edge_row["to_node"])

        if (start_node, end_node) == (csv_to, csv_from):

            coords = list(
                reversed(coords)
            )

        kml = add_linestring_placemark(
            kml=kml,
            name=(
                f"{vehicle_label} | "
                f"Rota {route_no} | "
                f"Adım {step_no} | "
                f"Servis Edge {edge_id} "
                f"({start_node}->{end_node})"
            ),
            style_id="service",
            coords=coords
        )

    kml += build_kml_footer()

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(kml)

    print(
        f"KML oluşturuldu: {output_path}"
    )


def write_ga_kml_by_route(
    route_df,
    vehicle_label
):

    output_paths = []

    for route_no in sorted(
        route_df["route_no"].unique()
    ):

        selected_route_df = route_df[
            route_df["route_no"] == route_no
        ].copy()

        output_path = os.path.join(
            kml_folder,
            f"{vehicle_label}_route_{route_no}.kml"
        )

        write_ga_kml(
            selected_route_df,
            vehicle_label=f"{vehicle_label}_route_{route_no}",
            output_path=output_path
        )

        output_paths.append(output_path)

    return output_paths


# =========================
# 18.1 KML DOSYALARINI OLUŞTUR
# =========================

# Her rota için ayrı KML
avg_kml_paths = write_ga_kml_by_route(
    final_best_avg_df,
    vehicle_label="AVG"
)

azu_kml_paths = write_ga_kml_by_route(
    final_best_azu_df,
    vehicle_label="AZU"
)

# İstersen araç bazlı birleşik KML de kalsın
write_ga_kml(
    final_best_avg_df,
    vehicle_label="AVG_FINAL_GA",
    output_path=os.path.join(
        kml_folder,
        "AVG_FINAL_GA_Rota.kml"
    )
)

write_ga_kml(
    final_best_azu_df,
    vehicle_label="AZU_FINAL_GA",
    output_path=os.path.join(
        kml_folder,
        "AZU_FINAL_GA_Rota.kml"
    )
)
# =========================
# 19. BELEDİYE GERÇEK ROTA VERİSİ
# =========================

df["avgataturk_sefer1_service"] = df["avgataturk_sefer1_service"].fillna(0).astype(int)
df["avgataturk_sefer2_service"] = df["avgataturk_sefer2_service"].fillna(0).astype(int)

df["avgataturk_sefer1_sira"] = df["avgataturk_sefer1_sira"].fillna(9999).astype(int)
df["avgataturk_sefer2_sira"] = df["avgataturk_sefer2_sira"].fillna(9999).astype(int)

municipality_sefer1 = df[
    df["avgataturk_sefer1_service"] == 1
].copy()

municipality_sefer2 = df[
    df["avgataturk_sefer2_service"] == 1
].copy()

municipality_sefer1 = municipality_sefer1.sort_values(
    by="avgataturk_sefer1_sira"
)

municipality_sefer2 = municipality_sefer2.sort_values(
    by="avgataturk_sefer2_sira"
)

print("\nBelediye seferleri oluşturuldu.")
print("Sefer 1 servis edge sayısı:", len(municipality_sefer1))
print("Sefer 2 servis edge sayısı:", len(municipality_sefer2))


# =========================
# 20. BELEDİYE ROTA MALİYETİ HESAPLAMA
# =========================

def calculate_municipality_route_cost(sefer_df, vehicle_id=1):

    total_cost = 0
    current_node = depot
    route_load = 0
    detailed_rows = []

    Gv = vehicle_graph[vehicle_id]
    shortest_v = vehicle_shortest[vehicle_id]

    # gerçek depo -> sanal depo
    total_cost += REAL_DEPOT_DISTANCE

    for step_no, (_, row) in enumerate(sefer_df.iterrows(), start=1):

        u = int(row["from_node"])
        v = int(row["to_node"])
        edge_length = float(row["uzunluk"])
        demand = int(row["tip1_talep"])

        possible_dirs = [(u, v)]

        if row["yon"] == "cift":
            possible_dirs.append((v, u))

        best_cost = float("inf")
        best_dir = None
        best_path = None

        for start, end in possible_dirs:

            if current_node in shortest_v and start in shortest_v[current_node]:

                travel_cost = shortest_v[current_node][start]

                if travel_cost < best_cost:
                    best_cost = travel_cost
                    best_dir = (start, end)

                    best_path = nx.shortest_path(
                        Gv,
                        source=current_node,
                        target=start,
                        weight="weight"
                    )

        if best_dir is None:
            print(f"UYARI: Belediye rotasında ulaşılamayan edge: {u}->{v}")
            continue

        total_cost += best_cost + edge_length
        route_load += demand

        detailed_rows.append({
            "route_no": 1,
            "step_no": step_no,
            "from_node": current_node,
            "to_service_start": best_dir[0],
            "travel_path": best_path,
            "travel_distance": best_cost,
            "serviced_edge": int(row["arc_id"]),
            "service_direction": f"{best_dir[0]}->{best_dir[1]}",
            "service_distance": edge_length,
            "demand": demand,
            "cumulative_load": route_load,
            "mahalle": row["mahalle"]
        })

        current_node = best_dir[1]

    # son servis -> sanal depo
    if current_node in shortest_v and depot in shortest_v[current_node]:

        return_path = nx.shortest_path(
            Gv,
            source=current_node,
            target=depot,
            weight="weight"
        )

        return_distance = shortest_v[current_node][depot]
        total_cost += return_distance

        detailed_rows.append({
            "route_no": 1,
            "step_no": "RETURN",
            "from_node": current_node,
            "to_service_start": depot,
            "travel_path": return_path,
            "travel_distance": return_distance,
            "serviced_edge": None,
            "service_direction": "RETURN_TO_VIRTUAL_DEPOT",
            "service_distance": 0,
            "demand": 0,
            "cumulative_load": route_load,
            "mahalle": None
        })

    else:
        print("UYARI: Belediye rotası sanal depoya dönemedi.")

    # sanal depo -> gerçek depo
    total_cost += REAL_DEPOT_DISTANCE

    return total_cost, route_load, pd.DataFrame(detailed_rows)


municipality_cost_1, municipality_load_1, municipality_df_1 = calculate_municipality_route_cost(
    municipality_sefer1,
    vehicle_id=1
)

municipality_cost_2, municipality_load_2, municipality_df_2 = calculate_municipality_route_cost(
    municipality_sefer2,
    vehicle_id=1
)

municipality_total_cost = municipality_cost_1 + municipality_cost_2
municipality_total_load = municipality_load_1 + municipality_load_2

print("\n===== BELEDİYE ROTA MALİYETLERİ =====")
print("Sefer 1 maliyet:", municipality_cost_1)
print("Sefer 1 yük:", municipality_load_1)
print("Sefer 2 maliyet:", municipality_cost_2)
print("Sefer 2 yük:", municipality_load_2)
print("Belediye toplam maliyet:", municipality_total_cost)
print("Belediye toplam yük:", municipality_total_load)

# =========================
# 21. KDS KARŞILAŞTIRMA TABLOSU
# =========================

ga_total_cost = final_best_cost_avg + final_best_cost_azu

kds_comparison_df = pd.DataFrame([
    {
        "Senaryo": "GA Tabanlı Optimizasyon",
        "Kapsam": ", ".join(selected_neighborhoods),
        "Araçlar": "AVG + AZU",
        "Toplam Maliyet": ga_total_cost,
        "Toplam Yük": sum(e["demand"] for e in required_edges),
        "Açıklama": "Model tarafından üretilen optimize rota"
    },
    {
        "Senaryo": "Belediye Referans Rotası",
        "Kapsam": "Saha gözlemindeki AVG seferleri",
        "Araçlar": "AVG",
        "Toplam Maliyet": municipality_total_cost,
        "Toplam Yük": municipality_total_load,
        "Açıklama": "Belediye servis sırasına göre hesaplanan referans rota"
    }
])

print("\n===== KDS KARŞILAŞTIRMA TABLOSU =====")
print(kds_comparison_df)

# =========================
# 22. MINI KDS MENÜSÜ
# =========================

print("\n==============================")
print("BUCA ÇÖP TOPLAMA KARAR DESTEK SİSTEMİ")
print("==============================")

print("\nAktif çalışma alanı:")
print(", ".join(selected_neighborhoods))

print("\n1 -> Belediye Referans Rotası")
print("2 -> GA Optimize Rota")
print("3 -> KDS Karşılaştırma Tablosu")

secim = input("\nBir seçim giriniz: ")

if secim == "1":

    print("\n===== BELEDİYE REFERANS ROTASI =====")
    print("Sefer 1 maliyet:", municipality_cost_1)
    print("Sefer 1 yük:", municipality_load_1)
    print("Sefer 2 maliyet:", municipality_cost_2)
    print("Sefer 2 yük:", municipality_load_2)
    print("Toplam belediye maliyeti:", municipality_total_cost)
    print("Toplam belediye yük:", municipality_total_load)

elif secim == "2":

    print("\n===== GA OPTİMİZE ROTA =====")
    print("AVG maliyet:", final_best_cost_avg)
    print("AZU maliyet:", final_best_cost_azu)
    print("Toplam GA maliyeti:", final_best_cost_avg + final_best_cost_azu)
    print("Toplam rota sayısı:", len(final_best_routes_avg) + len(final_best_routes_azu))

elif secim == "3":

    print("\n===== KDS KARŞILAŞTIRMA TABLOSU =====")
    print(kds_comparison_df)

else:

    print("\nGeçersiz seçim yapıldı.")
    

    