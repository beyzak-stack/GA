#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 31 02:44:59 2026

@author: beyzakeskin
"""
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import random
# =====================================================
# 1. VERİYİ OKU - İKİ MAHALLELİ YAPI
# =====================================================

edge_files = {
    "atatürk": "Ataturk Mahallesi- Ataturk Mah.- Edges.csv",
    "kurucesme": "Kurucesme Mahallesi- Edges.csv"
}

container_files = {
    "atatürk": "Ataturk Mah.- konteyner_noktalari.csv",
    "kurucesme": "Kurucesme Mah.- konteyner_noktalari.csv"
}

dfs = []

for mahalle_adi, file_path in edge_files.items():

    temp = pd.read_csv(file_path)
    temp.columns = temp.columns.str.strip().str.lower()

    temp["source_mahalle"] = mahalle_adi

    # Atatürk dosyasında ayt_gecis yoksa sıfır veriyoruz
    if "ayt_gecis" not in temp.columns:
        temp["ayt_gecis"] = 0

    # Trafik seviyesi sadece Atatürk dosyasında var.
    # Kuruçeşme'de yoksa varsayılan olarak normal veriyoruz.
    if "trafik_seviyesi" not in temp.columns:
        temp["trafik_seviyesi"] = "normal"

    # Eksik servis/sıra kolonları varsa hata vermemesi için
    service_cols = [
        "avgataturk_sefer1_service",
        "avgataturk_sefer1_sira",
        "avgataturk_sefer2_service",
        "avgataturk_sefer2_sira",
        "avg297_sefer1_service",
        "avg297_sefer1_sira",
        "ayt275_sefer1_service",
        "ayt275_sefer1_sira"
    ]

    for col in service_cols:
        if col not in temp.columns:
            temp[col] = 0

    dfs.append(temp)

df = pd.concat(dfs, ignore_index=True)

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
        "avg_gecis",
        "ayt_gecis",
        "azu_gecis",
        "mahalle",
        "source_mahalle",
        "trafik_seviyesi",
        "yol_adi",
        # Belediye gerçek rota servis/sıra kolonları
        "avgataturk_sefer1_service",
        "avgataturk_sefer1_sira",
        "avgataturk_sefer2_service",
        "avgataturk_sefer2_sira",
        "avg297_sefer1_service",
        "avg297_sefer1_sira",
        "ayt275_sefer1_service",
        "ayt275_sefer1_sira"
        
    ]
].copy()

# Veri tiplerini düzelt
df["from_node"] = df["from_node"].astype(int)
df["to_node"] = df["to_node"].astype(int)
df["uzunluk"] = df["uzunluk"].astype(float)

df["tip1_talep"] = df["tip1_talep"].fillna(0).astype(int)
df["tip2_talep"] = df["tip2_talep"].fillna(0).astype(int)

df["avg_gecis"] = df["avg_gecis"].fillna(0).astype(int)
df["ayt_gecis"] = df["ayt_gecis"].fillna(0).astype(int)
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
    .fillna(df["source_mahalle"])
    .astype(str)
    .str.strip()
    .str.lower()
)

df["source_mahalle"] = (
    df["source_mahalle"]
    .astype(str)
    .str.strip()
    .str.lower()
)

df["trafik_seviyesi"] = (
    df["trafik_seviyesi"]
    .fillna("normal")
    .astype(str)
    .str.strip()
    .str.lower()
)

if "yol_adi" not in df.columns:
    df["yol_adi"] = df["ad"]

df["yol_adi"] = (
    df["yol_adi"]
    .fillna(df["ad"])
    .astype(str)
    .str.strip()
)

df.loc[
    df["yol_adi"].isin(["", "nan", "None"]),
    "yol_adi"
] = "Yol adı belirtilmemiş"

# Trafik seviyesi isimlerini standartlaştır
traffic_replace = {
    "düşük": "dusuk",
    "düsük": "dusuk",
    "dusuk": "dusuk",
    "orta": "orta",
    "normal": "normal",
    "yüksek": "yogun",
    "yuksek": "yogun",
    "yoğun": "yogun",
    "yogun": "yogun"
}

df["trafik_seviyesi"] = (
    df["trafik_seviyesi"]
    .replace(traffic_replace)
)

# İki dosyada arc_id çakışmasın diye birleşik veri üzerinden yeniden veriyoruz
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

# Trafik seviyesi kontrolü
allowed_traffic_levels = [
    "dusuk",
    "orta",
    "normal",
    "yogun"
]

wrong_traffic_levels = df[
    ~df["trafik_seviyesi"].isin(allowed_traffic_levels)
]

if len(wrong_traffic_levels) > 0:
    print("\nUYARI: Hatalı trafik seviyesi değerleri var:")
    print(
        wrong_traffic_levels[
            [
                "arc_id",
                "source_mahalle",
                "from_node",
                "to_node",
                "trafik_seviyesi"
            ]
        ]
    )

# Kontrol çıktıları
print("Toplam edge sayısı:", len(df))
print("Node sayısı:", len(set(df["from_node"]).union(set(df["to_node"]))))

print("\nMahallelere göre edge sayısı:")
print(df["source_mahalle"].value_counts())

print("\nTalep özeti:")
print("Tip1 talep olan edge:", len(df[df["tip1_talep"] > 0]))
print("Tip2 talep olan edge:", len(df[df["tip2_talep"] > 0]))
print("Toplam Tip1 talep:", df["tip1_talep"].sum())
print("Toplam Tip2 talep:", df["tip2_talep"].sum())

print("\nAraç geçiş uygunluğu:")
print("AVG geçebilir edge:", df["avg_gecis"].sum())
print("AYT geçebilir edge:", df["ayt_gecis"].sum())
print("AZU geçebilir edge:", df["azu_gecis"].sum())

print("\nTrafik seviyesi dağılımı:")
print(df.groupby("source_mahalle")["trafik_seviyesi"].value_counts())

print("\n===== ATATÜRK NORMAL OLARAK İŞARETLENEN EDGELER =====")

normal_edges = df[
    (df["source_mahalle"] == "atatürk") &
    (df["trafik_seviyesi"] == "normal")
]

print(
    normal_edges[
        [
            "arc_id",
            "ad",
            "from_node",
            "to_node",
            "trafik_seviyesi"
        ]
    ]
)

# =====================================================
# 2. GRAPH OLUŞTUR
# =====================================================

depot = 0

G = nx.DiGraph()

for _, row in df.iterrows():

    from_node = int(row["from_node"])
    to_node = int(row["to_node"])
    weight = float(row["uzunluk"])

    edge_data = {
        "weight": weight,
        "arc_id": int(row["arc_id"]),
        "edge_turu": row["edge_turu"],
        "yol_adi": row["yol_adi"],
        "mahalle": row["source_mahalle"],
        "tip1_talep": int(row["tip1_talep"]),
        "tip2_talep": int(row["tip2_talep"]),
        "avg_gecis": int(row["avg_gecis"]),
        "ayt_gecis": int(row["ayt_gecis"]),
        "azu_gecis": int(row["azu_gecis"])
    }

    if row["yon"] == "cift":
        G.add_edge(from_node, to_node, **edge_data)
        G.add_edge(to_node, from_node, **edge_data)

    elif row["yon"] == "tek":
        G.add_edge(from_node, to_node, **edge_data)

print("\nGraph node sayısı:", G.number_of_nodes())
print("Graph arc sayısı:", G.number_of_edges())

if depot in G.nodes:
    reachable_from_depot = nx.descendants(G, depot)
    print("Depodan ulaşılabilen node sayısı:", len(reachable_from_depot))
else:
    print("UYARI: Depot node 0 graph içinde yok.")
    
# =====================================================
# 2.1 EN KISA YOLLARI HESAPLA
# =====================================================

shortest = dict(
    nx.all_pairs_dijkstra_path_length(
        G,
        weight="weight"
    )
)

print("En kısa yollar hesaplandı.")

# =====================================================
# 3. GERÇEK KOORDİNATLI GRAPH GÖRSELLEŞTİRME
# =====================================================

node_files = {
    "atatürk": "Ataturk Mahallesi- Ataturk Mah.- dugum_noktalari.csv",
    "kurucesme": "Kurucesme Mahallesi- Kurucesme Mah-dugum_noktaları.csv.csv"
}

node_dfs = []

for mahalle_adi, node_path in node_files.items():

    nodes_temp = pd.read_csv(node_path)
    nodes_temp.columns = nodes_temp.columns.str.strip().str.lower()

    nodes_temp["source_mahalle"] = mahalle_adi

    nodes_temp["x"] = nodes_temp["wkt"].str.extract(
        r'POINT \(([\d\.]+)'
    )

    nodes_temp["y"] = nodes_temp["wkt"].str.extract(
        r'POINT \([\d\.]+ ([\d\.]+)\)'
    )

    nodes_temp["x"] = nodes_temp["x"].astype(float)
    nodes_temp["y"] = nodes_temp["y"].astype(float)
    nodes_temp["id"] = nodes_temp["id"].astype(int)

    node_dfs.append(nodes_temp)

nodes_df = pd.concat(node_dfs, ignore_index=True)

pos = {
    row["id"]: (row["x"], row["y"])
    for _, row in nodes_df.iterrows()
}

print("\nNode koordinatları oluşturuldu.")
print("Koordinatı olan node sayısı:", len(pos))


# =====================================================
# 3.1 MAHALLE BAZLI GÖRSELLEŞTİRME FONKSİYONU
# =====================================================

def plot_neighborhood_network(mahalle_adi):

    mahalle_df = df[
        df["source_mahalle"] == mahalle_adi
    ].copy()

    Gm = nx.DiGraph()

    for _, row in mahalle_df.iterrows():

        u = int(row["from_node"])
        v = int(row["to_node"])

        edge_data = {
            "weight": float(row["uzunluk"]),
            "edge_turu": row["edge_turu"]
        }

        if row["yon"] == "cift":
            Gm.add_edge(u, v, **edge_data)
            Gm.add_edge(v, u, **edge_data)
        else:
            Gm.add_edge(u, v, **edge_data)

    mahalle_nodes = [
        node for node in Gm.nodes()
        if node in pos
    ]

    travel_edges = [
        (u, v) for u, v, data in Gm.edges(data=True)
        if data["edge_turu"] == "travel"
        and u in pos and v in pos
    ]

    service_edges = [
        (u, v) for u, v, data in Gm.edges(data=True)
        if data["edge_turu"] == "servis"
        and u in pos and v in pos
    ]

    depot_edges = [
        (u, v) for u, v, data in Gm.edges(data=True)
        if data["edge_turu"] == "depo_baglanti"
        and u in pos and v in pos
    ]

    plt.figure(figsize=(20, 16))

    nx.draw_networkx_edges(
        Gm,
        pos,
        edgelist=travel_edges,
        edge_color="lightgray",
        width=1,
        arrows=True,
        arrowsize=6,
        alpha=0.7
    )

    nx.draw_networkx_edges(
        Gm,
        pos,
        edgelist=depot_edges,
        edge_color="orange",
        width=1.5,
        arrows=True,
        arrowsize=6,
        alpha=0.8
    )

    nx.draw_networkx_edges(
        Gm,
        pos,
        edgelist=service_edges,
        edge_color="red",
        width=2,
        arrows=True,
        arrowsize=8,
        alpha=0.9
    )

    nx.draw_networkx_nodes(
        Gm,
        pos,
        nodelist=mahalle_nodes,
        node_size=60,
        node_color="lightblue"
    )

    if depot in Gm.nodes() and depot in pos:
        nx.draw_networkx_nodes(
            Gm,
            pos,
            nodelist=[depot],
            node_size=260,
            node_color="green"
        )

    nx.draw_networkx_labels(
        Gm,
        pos,
        labels={
            node: node
            for node in mahalle_nodes
        },
        font_size=5
    )

    plt.title(
        f"{mahalle_adi.capitalize()} Mahallesi Yol Ağı\n"
        "Kırmızı: Servis | Gri: Travel | Turuncu: Depo Bağlantı | Yeşil: Sanal Depo",
        fontsize=16
    )

    plt.axis("off")
    plt.tight_layout()

    plot_folder = "plots"
    os.makedirs(plot_folder, exist_ok=True)

    plot_path = os.path.join(
        plot_folder,
        f"network_plot_{mahalle_adi}.png"
    )

    plt.savefig(
        plot_path,
        dpi=120,
        bbox_inches="tight"
    )

    print(f"{mahalle_adi} görseli kaydedildi: {plot_path}")

    plt.show()
    plt.close()

# =====================================================
# 3.2 MAHALLE GÖRSELLERİNİ OLUŞTUR
# =====================================================

plot_neighborhood_network("atatürk")
plot_neighborhood_network("kurucesme")

# =====================================================
# 4. REQUIRED EDGE LİSTESİ - MAHALLE + ARAÇ BAZLI
# =====================================================

selected_neighborhoods = [
    "atatürk",
    "kurucesme"
]

service_df = df[
    df["source_mahalle"].isin(selected_neighborhoods)
].copy()


def create_required_edge(row, demand_col, tip_no):
    return {
        "id": int(row["arc_id"]),
        "from": int(row["from_node"]),
        "to": int(row["to_node"]),
        "length": float(row["uzunluk"]),
        "demand": int(row[demand_col]),
        "yol_adi": row["yol_adi"],
        "tip": tip_no,
        "yon": row["yon"],
        "mahalle": row["source_mahalle"],
        "avg_gecis": int(row["avg_gecis"]),
        "ayt_gecis": int(row["ayt_gecis"]),
        "azu_gecis": int(row["azu_gecis"]),
        "edge_turu": row["edge_turu"]
    }


required_ataturk_avg = []
required_ataturk_azu = []

required_kurucesme_avg = []
required_kurucesme_ayt = []
required_kurucesme_azu = []


for _, row in service_df.iterrows():

    mahalle = row["source_mahalle"]

    # =============================
    # ATATÜRK
    # =============================

    if mahalle == "atatürk" and row["mahalle"] == "ataturk":

        # Atatürk Tip1 → AVG
        if (
            int(row["tip1_talep"]) > 0
            and int(row["avg_gecis"]) == 1
        ):

            required_ataturk_avg.append(
                create_required_edge(
                    row=row,
                    demand_col="tip1_talep",
                    tip_no=1
                )
            )

        # Atatürk Tip2 → AZU
        if (
            int(row["tip2_talep"]) > 0
            and int(row["azu_gecis"]) == 1
        ):

            required_ataturk_azu.append(
                create_required_edge(
                    row=row,
                    demand_col="tip2_talep",
                    tip_no=2
                )
            )

    # =============================
    # KURUÇEŞME
    # =============================

    elif mahalle == "kurucesme" and row["mahalle"] == "kurucesme":

        # Kuruçeşme Tip1 → AVG
        if (
            int(row["tip1_talep"]) > 0
            and int(row["avg_gecis"]) == 1
        ):

            required_kurucesme_avg.append(
                create_required_edge(
                    row=row,
                    demand_col="tip1_talep",
                    tip_no=1
                )
            )

        # Kuruçeşme Tip1 → AYT
        # AYT sadece AVG'nin giremediği ama AYT'nin girebildiği Tip1 yolları toplar.
        if (
            int(row["tip1_talep"]) > 0
            and int(row["avg_gecis"]) == 0
            and int(row["ayt_gecis"]) == 1
        ):

            required_kurucesme_ayt.append(
                create_required_edge(
                    row=row,
                    demand_col="tip1_talep",
                    tip_no=1
                )
            )

        # Kuruçeşme Tip2 → AZU
        if (
            int(row["tip2_talep"]) > 0
            and int(row["azu_gecis"]) == 1
        ):

            required_kurucesme_azu.append(
                create_required_edge(
                    row=row,
                    demand_col="tip2_talep",
                    tip_no=2
                )
            )


required_edges = (
    required_ataturk_avg
    + required_ataturk_azu
    + required_kurucesme_avg
    + required_kurucesme_ayt
    + required_kurucesme_azu
)

print("\nRequired edge listesi oluşturuldu.")
print("Toplam required edge:", len(required_edges))

print("\nAtatürk required edge:")
print("Atatürk AVG required edge:", len(required_ataturk_avg))
print("Atatürk AZU required edge:", len(required_ataturk_azu))

print("\nKuruçeşme required edge:")
print("Kuruçeşme AVG required edge:", len(required_kurucesme_avg))
print("Kuruçeşme AYT required edge:", len(required_kurucesme_ayt))
print("Kuruçeşme AZU required edge:", len(required_kurucesme_azu))

print("\nAraç-mahalle bazlı toplam talep:")
print("Atatürk AVG toplam talep:", sum(e["demand"] for e in required_ataturk_avg))
print("Atatürk AZU toplam talep:", sum(e["demand"] for e in required_ataturk_azu))
print("Kuruçeşme AVG toplam talep:", sum(e["demand"] for e in required_kurucesme_avg))
print("Kuruçeşme AYT toplam talep:", sum(e["demand"] for e in required_kurucesme_ayt))
print("Kuruçeşme AZU toplam talep:", sum(e["demand"] for e in required_kurucesme_azu))

# =====================================================
# 5. FITNESS FONKSİYONU - MAHALLE + ARAÇ BAZLI
# =====================================================

depot = 0

REAL_DEPOT_DISTANCE = 5600  # metre

active_vehicles = [1, 2, 3]   # AVG, AYT, AZU

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
    2: "ayt_gecis",
    3: "azu_gecis"
}

def build_vehicle_graph(vehicle_id, neighborhood_filter=None):
    """
    Vehicle graph oluşturur.
    neighborhood_filter: ['atatürk'], ['kurucesme'] vb.
    """

    Gv = nx.DiGraph()

    for _, row in df.iterrows():
        # Mahalle filtresi
        if neighborhood_filter is not None:
            if row["source_mahalle"] not in neighborhood_filter:
                continue

        # Araç geçiş kontrolü
        if vehicle_id == "AVG" and row["avg_gecis"] != 1:
            continue
        if vehicle_id == "AYT" and row["ayt_gecis"] != 1:
            continue
        if vehicle_id == "AZU" and row["azu_gecis"] != 1:
            continue

        u = int(row["from_node"])
        v = int(row["to_node"])
        w = float(row["uzunluk"])

        if row["yon"] == "tek":
            Gv.add_edge(u, v, weight=w)
        else:
            Gv.add_edge(u, v, weight=w)
            Gv.add_edge(v, u, weight=w)

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

        # Araç erişim uygunluğu
        access_col = vehicle_access_col[vehicle_id]

        edge_row = df[
            df["arc_id"] == edge["id"]
        ].iloc[0]

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
                total_cost += REAL_DEPOT_DISTANCE

                routes.append(current_route)

            current_route = []
            current_load = 0
            current_node = depot

            total_cost += REAL_DEPOT_DISTANCE

        u = edge["from"]
        v = edge["to"]

        possible_dirs = [(u, v)]

        if edge["yon"] == "cift":
            possible_dirs.append((v, u))

        best_cost = float("inf")
        best_dir = None

        for start, end in possible_dirs:

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
        total_cost += REAL_DEPOT_DISTANCE

        routes.append(current_route)

    # İlk çıkış: gerçek depo → sanal depo
    if routes:
        total_cost += REAL_DEPOT_DISTANCE

    fitness_score = 1 / (total_cost + 1)

    return total_cost, fitness_score, routes


# =====================================================
# 5.1 FITNESS TESTİ
# =====================================================

test_cost_ataturk_avg, test_fitness_ataturk_avg, test_routes_ataturk_avg = calculate_fitness(
    required_ataturk_avg,
    vehicle_id=1
)

test_cost_ataturk_azu, test_fitness_ataturk_azu, test_routes_ataturk_azu = calculate_fitness(
    required_ataturk_azu,
    vehicle_id=3
)

test_cost_kurucesme_avg, test_fitness_kurucesme_avg, test_routes_kurucesme_avg = calculate_fitness(
    required_kurucesme_avg,
    vehicle_id=1
)

test_cost_kurucesme_ayt, test_fitness_kurucesme_ayt, test_routes_kurucesme_ayt = calculate_fitness(
    required_kurucesme_ayt,
    vehicle_id=2
)

test_cost_kurucesme_azu, test_fitness_kurucesme_azu, test_routes_kurucesme_azu = calculate_fitness(
    required_kurucesme_azu,
    vehicle_id=3
)


print("\n===== FITNESS TEST SONUÇLARI =====")

print("\nATATÜRK - AVG:")
print("Toplam maliyet:", test_cost_ataturk_avg)
print("Fitness skoru:", test_fitness_ataturk_avg)
print("Rota sayısı:", len(test_routes_ataturk_avg))

print("\nATATÜRK - AZU:")
print("Toplam maliyet:", test_cost_ataturk_azu)
print("Fitness skoru:", test_fitness_ataturk_azu)
print("Rota sayısı:", len(test_routes_ataturk_azu))

print("\nKURUÇEŞME - AVG:")
print("Toplam maliyet:", test_cost_kurucesme_avg)
print("Fitness skoru:", test_fitness_kurucesme_avg)
print("Rota sayısı:", len(test_routes_kurucesme_avg))

print("\nKURUÇEŞME - AYT:")
print("Toplam maliyet:", test_cost_kurucesme_ayt)
print("Fitness skoru:", test_fitness_kurucesme_ayt)
print("Rota sayısı:", len(test_routes_kurucesme_ayt))

print("\nKURUÇEŞME - AZU:")
print("Toplam maliyet:", test_cost_kurucesme_azu)
print("Fitness skoru:", test_fitness_kurucesme_azu)
print("Rota sayısı:", len(test_routes_kurucesme_azu))

# =====================================================
# 6. ROTA DETAY ANALİZİ
# =====================================================

def analyze_routes(routes, required_edges, vehicle_id, mahalle_adi):

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

        detailed_rows.append({
            "mahalle": mahalle_adi,
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
            "yol_adi": "-",
            "demand": 0,
            "cumulative_load": 0,
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
                "mahalle": mahalle_adi,
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
                "yol_adi": edge["yol_adi"],
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
            "mahalle": mahalle_adi,
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
            "yol_adi": "-",
            "demand": 0,
            "cumulative_load": route_load
        })

        detailed_rows.append({
            "mahalle": mahalle_adi,
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
            "yol_adi": "-",
            "demand": 0,
            "cumulative_load": route_load
        })

    return pd.DataFrame(detailed_rows)


# =====================================================
# 6.1 TEST ROTALARINI ANALİZ ET
# =====================================================

ataturk_avg_df = analyze_routes(
    test_routes_ataturk_avg,
    required_ataturk_avg,
    vehicle_id=1,
    mahalle_adi="atatürk"
)

ataturk_azu_df = analyze_routes(
    test_routes_ataturk_azu,
    required_ataturk_azu,
    vehicle_id=3,
    mahalle_adi="atatürk"
)

kurucesme_avg_df = analyze_routes(
    test_routes_kurucesme_avg,
    required_kurucesme_avg,
    vehicle_id=1,
    mahalle_adi="kurucesme"
)

kurucesme_ayt_df = analyze_routes(
    test_routes_kurucesme_ayt,
    required_kurucesme_ayt,
    vehicle_id=2,
    mahalle_adi="kurucesme"
)

kurucesme_azu_df = analyze_routes(
    test_routes_kurucesme_azu,
    required_kurucesme_azu,
    vehicle_id=3,
    mahalle_adi="kurucesme"
)


test_route_details_df = pd.concat(
    [
        ataturk_avg_df,
        ataturk_azu_df,
        kurucesme_avg_df,
        kurucesme_ayt_df,
        kurucesme_azu_df
    ],
    ignore_index=True
)

print("\nTest rota detayları oluşturuldu.")
print(test_route_details_df.head())

# =====================================================
# 7. GA - BİREY VE POPÜLASYON OLUŞTURMA
# =====================================================

import random

def create_individual(edge_list):
    individual = edge_list[:]
    random.shuffle(individual)
    return individual

def create_population(edge_list, population_size, seed_individual=None):

    population = []

    if seed_individual is not None:
        population.append(seed_individual[:])

    while len(population) < population_size:
        individual = create_individual(edge_list)
        population.append(individual)

    return population

# =====================================================
# 7.1 POPÜLASYON TESTİ - MAHALLE + ARAÇ BAZLI
# =====================================================

population_ataturk_avg = create_population(
    required_ataturk_avg,
    population_size=30
)

population_ataturk_azu = create_population(
    required_ataturk_azu,
    population_size=20
)

population_kurucesme_avg = create_population(
    required_kurucesme_avg,
    population_size=30
)

population_kurucesme_ayt = create_population(
    required_kurucesme_ayt,
    population_size=30
)

population_kurucesme_azu = create_population(
    required_kurucesme_azu,
    population_size=20
)


print("\n===== POPÜLASYON BİLGİLERİ =====")

print("\nAtatürk AVG:")
print("Birey sayısı:", len(population_ataturk_avg))
print("Bir bireydeki edge sayısı:", len(population_ataturk_avg[0]))

print("\nAtatürk AZU:")
print("Birey sayısı:", len(population_ataturk_azu))
print("Bir bireydeki edge sayısı:", len(population_ataturk_azu[0]))

print("\nKuruçeşme AVG:")
print("Birey sayısı:", len(population_kurucesme_avg))
print("Bir bireydeki edge sayısı:", len(population_kurucesme_avg[0]))

print("\nKuruçeşme AYT:")
print("Birey sayısı:", len(population_kurucesme_ayt))
print("Bir bireydeki edge sayısı:", len(population_kurucesme_ayt[0]))

print("\nKuruçeşme AZU:")
print("Birey sayısı:", len(population_kurucesme_azu))
print("Bir bireydeki edge sayısı:", len(population_kurucesme_azu[0]))


# =====================================================
# 7.2 POPÜLASYON FITNESS DEĞERLERİNİ HESAPLA
# =====================================================

def evaluate_population(population, vehicle_id, label):

    fitness_values = []
    cost_values = []
    route_values = []

    for individual in population:

        cost, fitness, routes = calculate_fitness(
            individual,
            vehicle_id=vehicle_id
        )

        cost_values.append(cost)
        fitness_values.append(fitness)
        route_values.append(routes)

    print(f"\n{label} başlangıç popülasyonu:")
    print("En iyi maliyet:", min(cost_values))
    print("En kötü maliyet:", max(cost_values))
    print("Ortalama maliyet:", sum(cost_values) / len(cost_values))
    print("En iyi fitness:", max(fitness_values))
    print("En kötü fitness:", min(fitness_values))

    return cost_values, fitness_values, route_values


costs_ataturk_avg, fitness_ataturk_avg, routes_ataturk_avg_population = evaluate_population(
    population_ataturk_avg,
    vehicle_id=1,
    label="Atatürk AVG"
)

costs_ataturk_azu, fitness_ataturk_azu, routes_ataturk_azu_population = evaluate_population(
    population_ataturk_azu,
    vehicle_id=3,
    label="Atatürk AZU"
)

costs_kurucesme_avg, fitness_kurucesme_avg, routes_kurucesme_avg_population = evaluate_population(
    population_kurucesme_avg,
    vehicle_id=1,
    label="Kuruçeşme AVG"
)

costs_kurucesme_ayt, fitness_kurucesme_ayt, routes_kurucesme_ayt_population = evaluate_population(
    population_kurucesme_ayt,
    vehicle_id=2,
    label="Kuruçeşme AYT"
)

costs_kurucesme_azu, fitness_kurucesme_azu, routes_kurucesme_azu_population = evaluate_population(
    population_kurucesme_azu,
    vehicle_id=3,
    label="Kuruçeşme AZU"
)

# =====================================================
# 7.3 CONSTRAINT CHECK
# =====================================================

def check_solution_constraints(routes, required_edges, vehicle_id, label):

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
        "label": label,
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


check_ataturk_avg = check_solution_constraints(
    test_routes_ataturk_avg,
    required_ataturk_avg,
    vehicle_id=1,
    label="Atatürk AVG"
)

check_ataturk_azu = check_solution_constraints(
    test_routes_ataturk_azu,
    required_ataturk_azu,
    vehicle_id=3,
    label="Atatürk AZU"
)

check_kurucesme_avg = check_solution_constraints(
    test_routes_kurucesme_avg,
    required_kurucesme_avg,
    vehicle_id=1,
    label="Kuruçeşme AVG"
)

check_kurucesme_ayt = check_solution_constraints(
    test_routes_kurucesme_ayt,
    required_kurucesme_ayt,
    vehicle_id=2,
    label="Kuruçeşme AYT"
)

check_kurucesme_azu = check_solution_constraints(
    test_routes_kurucesme_azu,
    required_kurucesme_azu,
    vehicle_id=3,
    label="Kuruçeşme AZU"
)


constraint_check_df = pd.DataFrame([
    check_ataturk_avg,
    check_ataturk_azu,
    check_kurucesme_avg,
    check_kurucesme_ayt,
    check_kurucesme_azu
])

print("\n===== CONSTRAINT CHECK SONUÇLARI =====")
print(constraint_check_df)

# =====================================================
# 8. GA - SELECTION
# =====================================================

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


# =====================================================
# 9. GA - ORDERED CROSSOVER
# =====================================================

def ordered_crossover(parent1, parent2):

    size = len(parent1)

    if size < 2:
        return parent1[:]

    child = [None] * size

    start, end = sorted(
        random.sample(range(size), 2)
    )

    child[start:end + 1] = parent1[start:end + 1]

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


# =====================================================
# 10. GA - SWAP MUTATION
# =====================================================

def swap_mutation(individual, mutation_rate=0.15):

    mutated = individual[:]

    if len(mutated) < 2:
        return mutated

    if random.random() < mutation_rate:

        i, j = random.sample(
            range(len(mutated)),
            2
        )

        mutated[i], mutated[j] = mutated[j], mutated[i]

    return mutated


# =====================================================
# 10.1 LOCAL SEARCH - INSERTION IMPROVEMENT
# =====================================================

def insertion_local_search(
    individual,
    vehicle_id,
    max_trials=30
):

    if len(individual) < 2:
        return individual[:]

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

# =====================================================
# 11. FULL GA DÖNGÜSÜ
# =====================================================

def run_genetic_algorithm(
    required_edge_list,
    vehicle_id,
    label,
    population_size=100,
    generations=100,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=30
):

    if len(required_edge_list) == 0:
        print(f"\nUYARI: {label} için required edge yok.")
        return (
            0,
            0,
            [],
            [],
            pd.DataFrame()
        )

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

        while len(new_population) < population_size:

            parent1_index = roulette_wheel_selection_index(
                fitness_values
            )

            parent2_index = roulette_wheel_selection_index(
                fitness_values
            )

            while parent2_index == parent1_index and len(sorted_population) > 1:
                parent2_index = roulette_wheel_selection_index(
                    fitness_values
                )

            parent1 = sorted_population[parent1_index]
            parent2 = sorted_population[parent2_index]

            if random.random() < crossover_rate:
                child = ordered_crossover(
                    parent1,
                    parent2
                )
            else:
                child = parent1[:]

            child = swap_mutation(
                child,
                mutation_rate=mutation_rate
            )

            child = insertion_local_search(
                child,
                vehicle_id,
                max_trials=3
            )

            new_population.append(child)

        population = new_population

        history.append({
            "generation": generation,
            "label": label,
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
                f"{label} | "
                f"Best cost: {best_cost} | "
                f"Best fitness: {best_fitness} | "
                f"No improvement: {no_improvement_counter}"
            )

        if no_improvement_counter >= patience:

            print(
                f"Early stopping: "
                f"{label} için "
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

# =====================================================
# 12. FULL GA ÇALIŞTIR - MAHALLE + ARAÇ BAZLI
# =====================================================

best_cost_ataturk_avg, best_fitness_ataturk_avg, best_routes_ataturk_avg, best_individual_ataturk_avg, history_ataturk_avg = run_genetic_algorithm(
    required_edge_list=required_ataturk_avg,
    vehicle_id=1,
    label="Atatürk AVG",
    population_size=20,
    generations=50,
    crossover_rate=0.70,
    mutation_rate=0.20,
    elite_size=2,
    patience=8
)

best_cost_ataturk_azu, best_fitness_ataturk_azu, best_routes_ataturk_azu, best_individual_ataturk_azu, history_ataturk_azu = run_genetic_algorithm(
    required_edge_list=required_ataturk_azu,
    vehicle_id=3,
    label="Atatürk AZU",
    population_size=15,
    generations=40,
    crossover_rate=0.70,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)

best_cost_kurucesme_avg, best_fitness_kurucesme_avg, best_routes_kurucesme_avg, best_individual_kurucesme_avg, history_kurucesme_avg = run_genetic_algorithm(
    required_edge_list=required_kurucesme_avg,
    vehicle_id=1,
    label="Kuruçeşme AVG",
    population_size=20,
    generations=50,
    crossover_rate=0.70,
    mutation_rate=0.20,
    elite_size=2,
    patience=8
)

best_cost_kurucesme_ayt, best_fitness_kurucesme_ayt, best_routes_kurucesme_ayt, best_individual_kurucesme_ayt, history_kurucesme_ayt = run_genetic_algorithm(
    required_edge_list=required_kurucesme_ayt,
    vehicle_id=2,
    label="Kuruçeşme AYT",
    population_size=20,
    generations=50,
    crossover_rate=0.70,
    mutation_rate=0.20,
    elite_size=2,
    patience=8
)

best_cost_kurucesme_azu, best_fitness_kurucesme_azu, best_routes_kurucesme_azu, best_individual_kurucesme_azu, history_kurucesme_azu = run_genetic_algorithm(
    required_edge_list=required_kurucesme_azu,
    vehicle_id=3,
    label="Kuruçeşme AZU",
    population_size=15,
    generations=40,
    crossover_rate=0.70,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)


print("\n===== FULL GA SONUÇLARI =====")

print("\nAtatürk AVG:")
print("En iyi maliyet:", best_cost_ataturk_avg)
print("En iyi fitness:", best_fitness_ataturk_avg)
print("Rota sayısı:", len(best_routes_ataturk_avg))

print("\nAtatürk AZU:")
print("En iyi maliyet:", best_cost_ataturk_azu)
print("En iyi fitness:", best_fitness_ataturk_azu)
print("Rota sayısı:", len(best_routes_ataturk_azu))

print("\nKuruçeşme AVG:")
print("En iyi maliyet:", best_cost_kurucesme_avg)
print("En iyi fitness:", best_fitness_kurucesme_avg)
print("Rota sayısı:", len(best_routes_kurucesme_avg))

print("\nKuruçeşme AYT:")
print("En iyi maliyet:", best_cost_kurucesme_ayt)
print("En iyi fitness:", best_fitness_kurucesme_ayt)
print("Rota sayısı:", len(best_routes_kurucesme_ayt))

print("\nKuruçeşme AZU:")
print("En iyi maliyet:", best_cost_kurucesme_azu)
print("En iyi fitness:", best_fitness_kurucesme_azu)
print("Rota sayısı:", len(best_routes_kurucesme_azu))


total_best_cost = (
    best_cost_ataturk_avg
    + best_cost_ataturk_azu
    + best_cost_kurucesme_avg
    + best_cost_kurucesme_ayt
    + best_cost_kurucesme_azu
)

print("\nToplam GA maliyeti:", total_best_cost)

# =====================================================
# 13. EN İYİ GA ROTALARINI DETAYLI ANALİZ ET
# =====================================================

best_ataturk_avg_df = analyze_routes(
    best_routes_ataturk_avg,
    required_ataturk_avg,
    vehicle_id=1,
    mahalle_adi="atatürk"
)

best_ataturk_azu_df = analyze_routes(
    best_routes_ataturk_azu,
    required_ataturk_azu,
    vehicle_id=3,
    mahalle_adi="atatürk"
)

best_kurucesme_avg_df = analyze_routes(
    best_routes_kurucesme_avg,
    required_kurucesme_avg,
    vehicle_id=1,
    mahalle_adi="kurucesme"
)

best_kurucesme_ayt_df = analyze_routes(
    best_routes_kurucesme_ayt,
    required_kurucesme_ayt,
    vehicle_id=2,
    mahalle_adi="kurucesme"
)

best_kurucesme_azu_df = analyze_routes(
    best_routes_kurucesme_azu,
    required_kurucesme_azu,
    vehicle_id=3,
    mahalle_adi="kurucesme"
)


best_ataturk_avg_df["total_cost"] = best_cost_ataturk_avg
best_ataturk_avg_df["fitness_score"] = best_fitness_ataturk_avg

best_ataturk_azu_df["total_cost"] = best_cost_ataturk_azu
best_ataturk_azu_df["fitness_score"] = best_fitness_ataturk_azu

best_kurucesme_avg_df["total_cost"] = best_cost_kurucesme_avg
best_kurucesme_avg_df["fitness_score"] = best_fitness_kurucesme_avg

best_kurucesme_ayt_df["total_cost"] = best_cost_kurucesme_ayt
best_kurucesme_ayt_df["fitness_score"] = best_fitness_kurucesme_ayt

best_kurucesme_azu_df["total_cost"] = best_cost_kurucesme_azu
best_kurucesme_azu_df["fitness_score"] = best_fitness_kurucesme_azu


best_route_details_df = pd.concat(
    [
        best_ataturk_avg_df,
        best_ataturk_azu_df,
        best_kurucesme_avg_df,
        best_kurucesme_ayt_df,
        best_kurucesme_azu_df
    ],
    ignore_index=True
)

print("\nEn iyi GA rota detayları oluşturuldu.")
print(best_route_details_df.head())

# =====================================================
# 14. ROTA BAZLI KAPASİTE ANALİZİ
# =====================================================

def route_capacity_summary(route_detail_df, vehicle_id, label):

    if route_detail_df.empty:
        return pd.DataFrame()

    summary = (
        route_detail_df
        .groupby(["mahalle", "vehicle_name", "route_no"])
        .agg(
            route_load=("demand", "sum"),
            service_distance=("service_distance", "sum"),
            travel_distance=("travel_distance", "sum")
        )
        .reset_index()
    )

    summary["label"] = label
    summary["vehicle_id"] = vehicle_id
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


capacity_ataturk_avg_df = route_capacity_summary(
    best_ataturk_avg_df,
    vehicle_id=1,
    label="Atatürk AVG"
)

capacity_ataturk_azu_df = route_capacity_summary(
    best_ataturk_azu_df,
    vehicle_id=3,
    label="Atatürk AZU"
)

capacity_kurucesme_avg_df = route_capacity_summary(
    best_kurucesme_avg_df,
    vehicle_id=1,
    label="Kuruçeşme AVG"
)

capacity_kurucesme_ayt_df = route_capacity_summary(
    best_kurucesme_ayt_df,
    vehicle_id=2,
    label="Kuruçeşme AYT"
)

capacity_kurucesme_azu_df = route_capacity_summary(
    best_kurucesme_azu_df,
    vehicle_id=3,
    label="Kuruçeşme AZU"
)


capacity_summary_df = pd.concat(
    [
        capacity_ataturk_avg_df,
        capacity_ataturk_azu_df,
        capacity_kurucesme_avg_df,
        capacity_kurucesme_ayt_df,
        capacity_kurucesme_azu_df
    ],
    ignore_index=True
)

print("\n===== ROTA BAZLI KAPASİTE ANALİZİ =====")
print(capacity_summary_df)

# =====================================================
# 15. GA YAKINSAMA GRAFİĞİ
# =====================================================

def plot_ga_convergence(history_df, label):

    if history_df.empty:
        print(f"UYARI: {label} için history boş, grafik çizilmedi.")
        return

    plt.figure(figsize=(10, 6))

    plt.plot(
        history_df["generation"],
        history_df["best_cost"],
        label="Best Cost"
    )

    plt.plot(
        history_df["generation"],
        history_df["avg_cost"],
        label="Average Cost"
    )

    plt.xlabel("Generation")
    plt.ylabel("Cost")
    plt.title(f"{label} GA Yakınsama Grafiği")
    plt.legend()
    plt.grid(True)

    plot_folder = "plots"
    os.makedirs(plot_folder, exist_ok=True)

    safe_label = (
        label.lower()
        .replace(" ", "_")
        .replace("ü", "u")
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )

    plot_path = os.path.join(
        plot_folder,
        f"ga_convergence_{safe_label}.png"
    )

    plt.savefig(
        plot_path,
        dpi=120,
        bbox_inches="tight"
    )

    print(f"{label} yakınsama grafiği kaydedildi: {plot_path}")

    plt.show()
    plt.close()


plot_ga_convergence(
    history_ataturk_avg,
    "Atatürk AVG"
)

plot_ga_convergence(
    history_ataturk_azu,
    "Atatürk AZU"
)

plot_ga_convergence(
    history_kurucesme_avg,
    "Kuruçeşme AVG"
)

plot_ga_convergence(
    history_kurucesme_ayt,
    "Kuruçeşme AYT"
)

plot_ga_convergence(
    history_kurucesme_azu,
    "Kuruçeşme AZU"
)

# =====================================================
# 16. MULTI RUN ANALYSIS
# =====================================================

def multi_run_ga(
    required_edge_list,
    vehicle_id,
    label,
    run_count=20,
    population_size=100,
    generations=300,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=30
):

    if len(required_edge_list) == 0:
        print(f"UYARI: {label} için required edge yok.")
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            0,
            0,
            [],
            []
        )

    multi_run_results = []

    best_overall_cost = float("inf")
    best_overall_fitness = 0
    best_overall_routes = None
    best_overall_individual = None
    best_overall_run = None

    for run in range(1, run_count + 1):

        print(
            f"\n===== RUN {run} | {label} ====="
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
            label=label,
            population_size=population_size,
            generations=generations,
            crossover_rate=crossover_rate,
            mutation_rate=mutation_rate,
            elite_size=elite_size,
            patience=patience
        )

        multi_run_results.append({
            "run_no": run,
            "label": label,
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "best_cost": best_cost,
            "best_fitness": best_fitness,
            "route_count": len(best_routes),
            "last_generation": history_df["generation"].max()
            if not history_df.empty else 0,
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
        "label": label,
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

# =====================================================
# 17. MULTI RUN ÇALIŞTIR
# =====================================================

ataturk_avg_multi_df, ataturk_avg_summary_df, final_best_cost_ataturk_avg, final_best_fitness_ataturk_avg, final_best_routes_ataturk_avg, final_best_individual_ataturk_avg = multi_run_ga(
    required_edge_list=required_ataturk_avg,
    vehicle_id=1,
    label="Atatürk AVG",
    run_count=3,
    population_size=20,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=8
)

ataturk_azu_multi_df, ataturk_azu_summary_df, final_best_cost_ataturk_azu, final_best_fitness_ataturk_azu, final_best_routes_ataturk_azu, final_best_individual_ataturk_azu = multi_run_ga(
    required_edge_list=required_ataturk_azu,
    vehicle_id=3,
    label="Atatürk AZU",
    run_count=3,
    population_size=15,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)

kurucesme_avg_multi_df, kurucesme_avg_summary_df, final_best_cost_kurucesme_avg, final_best_fitness_kurucesme_avg, final_best_routes_kurucesme_avg, final_best_individual_kurucesme_avg = multi_run_ga(
    required_edge_list=required_kurucesme_avg,
    vehicle_id=1,
    label="Kuruçeşme AVG",
    run_count=3,
    population_size=20,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=8
)

kurucesme_ayt_multi_df, kurucesme_ayt_summary_df, final_best_cost_kurucesme_ayt, final_best_fitness_kurucesme_ayt, final_best_routes_kurucesme_ayt, final_best_individual_kurucesme_ayt = multi_run_ga(
    required_edge_list=required_kurucesme_ayt,
    vehicle_id=2,
    label="Kuruçeşme AYT",
    run_count=3,
    population_size=20,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.15,
    elite_size=2,
    patience=8
)

kurucesme_azu_multi_df, kurucesme_azu_summary_df, final_best_cost_kurucesme_azu, final_best_fitness_kurucesme_azu, final_best_routes_kurucesme_azu, final_best_individual_kurucesme_azu = multi_run_ga(
    required_edge_list=required_kurucesme_azu,
    vehicle_id=3,
    label="Kuruçeşme AZU",
    run_count=3,
    population_size=15,
    generations=20,
    crossover_rate=0.80,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)


multi_run_results_df = pd.concat(
    [
        ataturk_avg_multi_df,
        ataturk_azu_multi_df,
        kurucesme_avg_multi_df,
        kurucesme_ayt_multi_df,
        kurucesme_azu_multi_df
    ],
    ignore_index=True
)

multi_run_summary_df = pd.concat(
    [
        ataturk_avg_summary_df,
        ataturk_azu_summary_df,
        kurucesme_avg_summary_df,
        kurucesme_ayt_summary_df,
        kurucesme_azu_summary_df
    ],
    ignore_index=True
)


print("\n===== MULTI RUN SONUÇLARI =====")
print(multi_run_results_df)

print("\n===== MULTI RUN ÖZET =====")
print(multi_run_summary_df)


final_total_best_cost = (
    final_best_cost_ataturk_avg
    + final_best_cost_ataturk_azu
    + final_best_cost_kurucesme_avg
    + final_best_cost_kurucesme_ayt
    + final_best_cost_kurucesme_azu
)

print("\n===== GENEL EN İYİ SONUÇ =====")
print("Atatürk AVG en iyi maliyet:", final_best_cost_ataturk_avg)
print("Atatürk AZU en iyi maliyet:", final_best_cost_ataturk_azu)
print("Kuruçeşme AVG en iyi maliyet:", final_best_cost_kurucesme_avg)
print("Kuruçeşme AYT en iyi maliyet:", final_best_cost_kurucesme_ayt)
print("Kuruçeşme AZU en iyi maliyet:", final_best_cost_kurucesme_azu)
print("Toplam en iyi maliyet:", final_total_best_cost)

# =====================================================
# 17.1 FINAL BEST ROTALARI DETAYLI ANALİZ ET
# =====================================================

final_best_ataturk_avg_df = analyze_routes(
    final_best_routes_ataturk_avg,
    required_ataturk_avg,
    vehicle_id=1,
    mahalle_adi="atatürk"
)

final_best_ataturk_azu_df = analyze_routes(
    final_best_routes_ataturk_azu,
    required_ataturk_azu,
    vehicle_id=3,
    mahalle_adi="atatürk"
)

final_best_kurucesme_avg_df = analyze_routes(
    final_best_routes_kurucesme_avg,
    required_kurucesme_avg,
    vehicle_id=1,
    mahalle_adi="kurucesme"
)

final_best_kurucesme_ayt_df = analyze_routes(
    final_best_routes_kurucesme_ayt,
    required_kurucesme_ayt,
    vehicle_id=2,
    mahalle_adi="kurucesme"
)

final_best_kurucesme_azu_df = analyze_routes(
    final_best_routes_kurucesme_azu,
    required_kurucesme_azu,
    vehicle_id=3,
    mahalle_adi="kurucesme"
)

final_route_details_df = pd.concat(
    [
        final_best_ataturk_avg_df,
        final_best_ataturk_azu_df,
        final_best_kurucesme_avg_df,
        final_best_kurucesme_ayt_df,
        final_best_kurucesme_azu_df
    ],
    ignore_index=True
)

print("\nFinal rota detayları oluşturuldu.")
print(final_route_details_df.head())

# =====================================================
# 18. GA SONUÇLARINI KML'YE AKTAR
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

kml_folder = os.path.join(
    BASE_DIR,
    "kml_outputs"
)

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

        coords.append(
            (
                float(lon),
                float(lat)
            )
        )

    return coords


def create_line_geometry_dict():

    line_geometry_by_arc = {}
    line_geometry_by_nodes = {}

    for _, row in df.iterrows():

        arc_id = int(row["arc_id"])

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


line_geometry_by_arc, line_geometry_by_nodes = create_line_geometry_dict()


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

    if os.path.exists(output_path):
        os.remove(output_path)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(kml)

    print(f"KML oluşturuldu: {output_path}")


def write_ga_kml_by_route(
    route_df,
    vehicle_label
):

    output_paths = []

    for route_no in sorted(route_df["route_no"].unique()):

        selected_route_df = route_df[
            route_df["route_no"] == route_no
        ].copy()

        safe_label = (
            vehicle_label
            .replace(" ", "_")
            .replace("ü", "u")
            .replace("ı", "i")
            .replace("ğ", "g")
            .replace("ş", "s")
            .replace("ö", "o")
            .replace("ç", "c")
        )

        output_path = os.path.join(
            kml_folder,
            f"{safe_label}_route_{route_no}.kml"
        )

        write_ga_kml(
            selected_route_df,
            vehicle_label=f"{vehicle_label}_route_{route_no}",
            output_path=output_path
        )

        output_paths.append(output_path)

    return output_paths


# =====================================================
# 18.1 ARAÇ + MAHALLE BAZLI KML DOSYALARI
# =====================================================

ataturk_avg_kml_paths = write_ga_kml_by_route(
    final_best_ataturk_avg_df,
    vehicle_label="AVG_Ataturk"
)

ataturk_azu_kml_paths = write_ga_kml_by_route(
    final_best_ataturk_azu_df,
    vehicle_label="AZU_Ataturk"
)

kurucesme_avg_kml_paths = write_ga_kml_by_route(
    final_best_kurucesme_avg_df,
    vehicle_label="AVG_Kurucesme"
)

kurucesme_ayt_kml_paths = write_ga_kml_by_route(
    final_best_kurucesme_ayt_df,
    vehicle_label="AYT_Kurucesme"
)

kurucesme_azu_kml_paths = write_ga_kml_by_route(
    final_best_kurucesme_azu_df,
    vehicle_label="AZU_Kurucesme"
)


print("\nKML dosyaları oluşturuldu.")
print("Atatürk AVG:", ataturk_avg_kml_paths)
print("Atatürk AZU:", ataturk_azu_kml_paths)
print("Kuruçeşme AVG:", kurucesme_avg_kml_paths)
print("Kuruçeşme AYT:", kurucesme_ayt_kml_paths)
print("Kuruçeşme AZU:", kurucesme_azu_kml_paths)
print(os.listdir(kml_folder))

# =====================================================
# 19. SENARYO ANALİZİ - TEK AZU İLE BİRLEŞİK TİP2 TOPLAMA
# =====================================================

# Mevcut durumda AZU iki mahalle için ayrı ayrı çözülmüştü:
# Atatürk AZU + Kuruçeşme AZU

current_separate_azu_cost = (
    best_cost_ataturk_azu
    + best_cost_kurucesme_azu
)

current_separate_azu_route_count = (
    len(best_routes_ataturk_azu)
    + len(best_routes_kurucesme_azu)
)

current_separate_azu_demand = (
    sum(e["demand"] for e in required_ataturk_azu)
    + sum(e["demand"] for e in required_kurucesme_azu)
)

current_separate_azu_edge_count = (
    len(required_ataturk_azu)
    + len(required_kurucesme_azu)
)


# Senaryo: Atatürk ve Kuruçeşme Tip2 talepleri tek AZU aracıyla birlikte çözülür.

required_combined_azu = (
    required_ataturk_azu
    + required_kurucesme_azu
)

combined_azu_cost, combined_azu_fitness, combined_azu_routes, combined_azu_individual, combined_azu_history = run_genetic_algorithm(
    required_edge_list=required_combined_azu,
    vehicle_id=3,
    label="Tek AZU - Atatürk + Kuruçeşme",
    population_size=20,
    generations=50,
    crossover_rate=0.70,
    mutation_rate=0.10,
    elite_size=2,
    patience=8
)

combined_azu_df = analyze_routes(
    combined_azu_routes,
    required_combined_azu,
    vehicle_id=3,
    mahalle_adi="atatürk+kurucesme"
)

combined_azu_df["total_cost"] = combined_azu_cost
combined_azu_df["fitness_score"] = combined_azu_fitness

combined_azu_demand = sum(
    e["demand"] for e in required_combined_azu
)

combined_azu_edge_count = len(
    required_combined_azu
)

combined_azu_route_count = len(
    combined_azu_routes
)


# =====================================================
# 19.1 SENARYO PERFORMANS GÖSTERGELERİ
# =====================================================

AZU_CAPACITY = Q[3]

current_capacity_utilization = round(
    current_separate_azu_demand / AZU_CAPACITY * 100,
    2
)

combined_capacity_utilization = round(
    combined_azu_demand / AZU_CAPACITY * 100,
    2
)

current_cost_per_demand = round(
    current_separate_azu_cost / current_separate_azu_demand,
    4
)

combined_cost_per_demand = round(
    combined_azu_cost / combined_azu_demand,
    4
)

current_cost_per_edge = round(
    current_separate_azu_cost / current_separate_azu_edge_count,
    2
)

combined_cost_per_edge = round(
    combined_azu_cost / combined_azu_edge_count,
    2
)


# =====================================================
# 19.2 SENARYO KARŞILAŞTIRMA TABLOSU
# =====================================================

azu_scenario_comparison_df = pd.DataFrame([

    {
        "Senaryo": "Mevcut Durum - AZU ayrı çözüm",
        "Açıklama": "Atatürk AZU ve Kuruçeşme AZU ayrı ayrı optimize edilmiştir.",
        "Toplam Talep": current_separate_azu_demand,
        "Servis Edge Sayısı": current_separate_azu_edge_count,
        "Toplam Maliyet": current_separate_azu_cost,
        "Rota Sayısı": current_separate_azu_route_count,
        "Kapasite Kullanımı (%)": current_capacity_utilization,
        "Birim Talep Maliyeti": current_cost_per_demand,
        "Edge Başına Maliyet": current_cost_per_edge,
        "Karar": "Referans"
    },

    {
        "Senaryo": "Tek AZU - Birleşik çözüm",
        "Açıklama": "Atatürk ve Kuruçeşme Tip2 talepleri tek AZU aracıyla birlikte optimize edilmiştir.",
        "Toplam Talep": combined_azu_demand,
        "Servis Edge Sayısı": combined_azu_edge_count,
        "Toplam Maliyet": combined_azu_cost,
        "Rota Sayısı": combined_azu_route_count,
        "Kapasite Kullanımı (%)": combined_capacity_utilization,
        "Birim Talep Maliyeti": combined_cost_per_demand,
        "Edge Başına Maliyet": combined_cost_per_edge,
        "Karar": "Önerilir"
    }

])

azu_scenario_comparison_df["Maliyet Farkı"] = (
    azu_scenario_comparison_df["Toplam Maliyet"]
    - current_separate_azu_cost
)

azu_scenario_comparison_df["Tasarruf"] = (
    current_separate_azu_cost
    - azu_scenario_comparison_df["Toplam Maliyet"]
)

azu_scenario_comparison_df["Tasarruf (%)"] = (
    (
        current_separate_azu_cost
        - azu_scenario_comparison_df["Toplam Maliyet"]
    )
    / current_separate_azu_cost
    * 100
).round(2)


print("\n===== SENARYO ANALİZİ: TEK AZU İLE BİRLEŞİK TİP2 TOPLAMA =====")
print(azu_scenario_comparison_df)

print("\nTek AZU birleşik rota maliyeti:", combined_azu_cost)
print("Tek AZU birleşik fitness:", combined_azu_fitness)
print("Tek AZU birleşik rota sayısı:", combined_azu_route_count)


# =====================================================
# 19.3 SENARYO KML ÇIKTISI - TEK AZU BİRLEŞİK ROTA
# =====================================================

combined_azu_kml_paths = write_ga_kml_by_route(
    combined_azu_df,
    vehicle_label="TEK_AZU_Ataturk_Kurucesme"
)

print("\nTek AZU birleşik rota KML dosyaları oluşturuldu:")
print(combined_azu_kml_paths)

# =====================================================
# 19.1 SENARYO KML ÇIKTISI - TEK AZU BİRLEŞİK ROTA
# =====================================================

combined_azu_kml_paths = write_ga_kml_by_route(
    combined_azu_df,
    vehicle_label="TEK_AZU_Ataturk_Kurucesme"
)

print("\nTek AZU birleşik rota KML dosyaları oluşturuldu:")
print(combined_azu_kml_paths)

# =====================================================
# 20. SENARYO ANALİZİ - ATATÜRK MAHALLESİ SAAT BAZLI TRAFİK ETKİSİ
# =====================================================

traffic_time_scenarios = {
    "15:00-17:00": {
        "dusuk": 1.00,
        "orta": 1.10,
        "yogun": 1.20,
        "normal": 1.00
    },
    "17:00-20:00": {
        "dusuk": 1.00,
        "orta": 1.25,
        "yogun": 1.50,
        "normal": 1.00
    },
    "20:00-23:00": {
        "dusuk": 1.00,
        "orta": 1.05,
        "yogun": 1.15,
        "normal": 1.00
    }
}


def get_traffic_factor(row, factor_dict):

    if row["source_mahalle"] != "atatürk":
        return 1.00

    traffic_level = row["trafik_seviyesi"]

    return factor_dict.get(traffic_level, 1.00)


def build_vehicle_graph_with_traffic(vehicle_id, factor_dict):

    access_col = vehicle_access_col[vehicle_id]

    Gv = nx.DiGraph()

    for _, row in df.iterrows():

        if int(row[access_col]) != 1:
            continue

        from_node = int(row["from_node"])
        to_node = int(row["to_node"])

        traffic_factor = get_traffic_factor(row, factor_dict)

        weight = float(row["uzunluk"]) * traffic_factor

        edge_data = {
            "weight": weight,
            "arc_id": int(row["arc_id"]),
            "edge_turu": row["edge_turu"],
            "mahalle": row["source_mahalle"],
            "trafik_seviyesi": row["trafik_seviyesi"],
            "trafik_katsayi": traffic_factor
        }

        if row["yon"] == "cift":
            Gv.add_edge(from_node, to_node, **edge_data)
            Gv.add_edge(to_node, from_node, **edge_data)

        elif row["yon"] == "tek":
            Gv.add_edge(from_node, to_node, **edge_data)

    return Gv


def create_traffic_required_edges(required_edges, factor_dict):

    traffic_required_edges = []

    for edge in required_edges:

        edge_row = df[
            df["arc_id"] == edge["id"]
        ].iloc[0]

        traffic_factor = get_traffic_factor(edge_row, factor_dict)

        new_edge = edge.copy()

        new_edge["original_length"] = edge["length"]
        new_edge["traffic_factor"] = traffic_factor
        new_edge["traffic_level"] = edge_row["trafik_seviyesi"]
        new_edge["length"] = edge["length"] * traffic_factor

        traffic_required_edges.append(new_edge)

    return traffic_required_edges


traffic_scenario_results = []

original_vehicle_graph = vehicle_graph.copy()
original_vehicle_shortest = vehicle_shortest.copy()

for time_period, factor_dict in traffic_time_scenarios.items():

    print(f"\n===== TRAFİK SENARYOSU: {time_period} =====")

    vehicle_graph[1] = build_vehicle_graph_with_traffic(
        vehicle_id=1,
        factor_dict=factor_dict
    )

    vehicle_graph[3] = build_vehicle_graph_with_traffic(
        vehicle_id=3,
        factor_dict=factor_dict
    )

    vehicle_shortest[1] = dict(
        nx.all_pairs_dijkstra_path_length(
            vehicle_graph[1],
            weight="weight"
        )
    )

    vehicle_shortest[3] = dict(
        nx.all_pairs_dijkstra_path_length(
            vehicle_graph[3],
            weight="weight"
        )
    )

    traffic_required_ataturk_avg = create_traffic_required_edges(
        required_ataturk_avg,
        factor_dict
    )

    traffic_required_ataturk_azu = create_traffic_required_edges(
        required_ataturk_azu,
        factor_dict
    )

    traffic_cost_ataturk_avg, traffic_fitness_ataturk_avg, traffic_routes_ataturk_avg, traffic_individual_ataturk_avg, traffic_history_ataturk_avg = run_genetic_algorithm(
        required_edge_list=traffic_required_ataturk_avg,
        vehicle_id=1,
        label=f"Atatürk AVG Trafik {time_period}",
        population_size=20,
        generations=30,
        crossover_rate=0.80,
        mutation_rate=0.15,
        elite_size=2,
        patience=8
    )

    traffic_cost_ataturk_azu, traffic_fitness_ataturk_azu, traffic_routes_ataturk_azu, traffic_individual_ataturk_azu, traffic_history_ataturk_azu = run_genetic_algorithm(
        required_edge_list=traffic_required_ataturk_azu,
        vehicle_id=3,
        label=f"Atatürk AZU Trafik {time_period}",
        population_size=15,
        generations=30,
        crossover_rate=0.80,
        mutation_rate=0.10,
        elite_size=2,
        patience=8
    )

    traffic_total_cost = (
        traffic_cost_ataturk_avg
        + traffic_cost_ataturk_azu
    )

    current_total_cost = (
        final_best_cost_ataturk_avg
        + final_best_cost_ataturk_azu
    )

    traffic_scenario_results.append({
        "Zaman Aralığı": time_period,
        "Senaryo": "Atatürk Trafik Etkisi",
        "AVG Mevcut Maliyet": final_best_cost_ataturk_avg,
        "AVG Trafikli Maliyet": traffic_cost_ataturk_avg,
        "AVG Rota Sayısı": len(traffic_routes_ataturk_avg),
        "AZU Mevcut Maliyet": final_best_cost_ataturk_azu,
        "AZU Trafikli Maliyet": traffic_cost_ataturk_azu,
        "AZU Rota Sayısı": len(traffic_routes_ataturk_azu),
        "Mevcut Toplam Maliyet": current_total_cost,
        "Trafikli Toplam Maliyet": traffic_total_cost,
        "Maliyet Farkı": traffic_total_cost - current_total_cost,
        "Maliyet Artışı (%)": round(
            (traffic_total_cost - current_total_cost)
            / current_total_cost
            * 100,
            2
        )
    })


vehicle_graph = original_vehicle_graph
vehicle_shortest = original_vehicle_shortest


traffic_scenario_comparison_df = pd.DataFrame(
    traffic_scenario_results
)

print("\n===== SENARYO ANALİZİ: ATATÜRK SAAT BAZLI TRAFİK ETKİSİ =====")
print(traffic_scenario_comparison_df)

# =====================================================
# 21. BELEDİYE MEVCUT ROTA MALİYETİ SENARYOSU - BAŞTAN SONA
# =====================================================

# Mahalle filtreleri
municipality_ataturk_service_area = [
    "ataturk",
    "adatepe",
    "camlikule"
]

municipality_kurucesme_service_area = [
    "kurucesme"
]


# =====================================================
# 21.1 BELEDİYE SERVİS SIRASINI HAZIRLA
# =====================================================

def prepare_municipality_service_df(
    service_col,
    order_col,
    mahalle_filter=None
):

    temp_df = df.copy()

    if service_col not in temp_df.columns:
        raise KeyError(f"{service_col} kolonu df içinde yok.")

    if order_col not in temp_df.columns:
        raise KeyError(f"{order_col} kolonu df içinde yok.")

    temp_df[service_col] = (
        temp_df[service_col]
        .fillna(0)
        .astype(int)
    )

    temp_df[order_col] = (
        temp_df[order_col]
        .fillna(9999)
        .astype(int)
    )

    route_df = temp_df[
        temp_df[service_col] == 1
    ].copy()

    if mahalle_filter is not None:
        route_df = route_df[
            route_df["mahalle"].isin(mahalle_filter)
        ].copy()

    route_df = route_df.sort_values(
        by=order_col
    )

    return route_df


# =====================================================
# 21.2 BELEDİYE ROTA MALİYETİ HESAPLA
# =====================================================

def calculate_municipality_route_cost(
    route_df,
    vehicle_id,
    route_label
):

    total_cost = 0
    current_node = depot
    route_load = 0
    detailed_rows = []

    Gv = vehicle_graph[vehicle_id]
    shortest_v = vehicle_shortest[vehicle_id]

    # Gerçek depo -> sanal depo
    total_cost += REAL_DEPOT_DISTANCE

    detailed_rows.append({
        "route_label": route_label,
        "vehicle_id": vehicle_id,
        "vehicle_name": vehicle_name[vehicle_id],
        "step_no": "START",
        "from_node": "REAL_DEPOT",
        "to_service_start": depot,
        "travel_path": "REAL_DEPOT_TO_VIRTUAL_DEPOT",
        "travel_distance": REAL_DEPOT_DISTANCE,
        "serviced_edge": None,
        "service_direction": "REAL_DEPOT_TO_VIRTUAL_DEPOT",
        "service_distance": 0,
        "demand": 0,
        "cumulative_load": 0,
        "mahalle": None
    })

    for step_no, (_, row) in enumerate(
        route_df.iterrows(),
        start=1
    ):

        u = int(row["from_node"])
        v = int(row["to_node"])

        edge_length = float(row["uzunluk"])
        demand = int(row["tip1_talep"])

        possible_dirs = [
            (u, v)
        ]

        if row["yon"] == "cift":
            possible_dirs.append(
                (v, u)
            )

        best_travel_cost = float("inf")
        best_dir = None
        best_path = None

        for start_node, end_node in possible_dirs:

            if (
                current_node in shortest_v
                and start_node in shortest_v[current_node]
            ):

                travel_cost = shortest_v[current_node][start_node]

                if travel_cost < best_travel_cost:

                    best_travel_cost = travel_cost
                    best_dir = (
                        start_node,
                        end_node
                    )

                    best_path = nx.shortest_path(
                        Gv,
                        source=current_node,
                        target=start_node,
                        weight="weight"
                    )

        if best_dir is None:

            print(
                f"UYARI: {route_label} için ulaşılamayan edge:",
                row["arc_id"]
            )

            continue

        service_cost = edge_length

        total_cost += (
            best_travel_cost
            + service_cost
        )

        route_load += demand

        detailed_rows.append({
            "route_label": route_label,
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
            "step_no": step_no,
            "from_node": current_node,
            "to_service_start": best_dir[0],
            "travel_path": best_path,
            "travel_distance": best_travel_cost,
            "serviced_edge": int(row["arc_id"]),
            "service_direction": f"{best_dir[0]}->{best_dir[1]}",
            "service_distance": service_cost,
            "yol_adi": row.get("yol_adi", row.get("ad", "Yol adı bilgisi yok")),
            "demand": demand,
            "cumulative_load": route_load,
            "mahalle": row["mahalle"]
        })

        current_node = best_dir[1]

    # Son servis -> sanal depo
    if (
        current_node in shortest_v
        and depot in shortest_v[current_node]
    ):

        return_path = nx.shortest_path(
            Gv,
            source=current_node,
            target=depot,
            weight="weight"
        )

        return_distance = shortest_v[current_node][depot]

        total_cost += return_distance

        detailed_rows.append({
            "route_label": route_label,
            "vehicle_id": vehicle_id,
            "vehicle_name": vehicle_name[vehicle_id],
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

        print(
            f"UYARI: {route_label} sanal depoya dönemedi."
        )

    # Sanal depo -> gerçek depo
    total_cost += REAL_DEPOT_DISTANCE

    detailed_rows.append({
        "route_label": route_label,
        "vehicle_id": vehicle_id,
        "vehicle_name": vehicle_name[vehicle_id],
        "step_no": "END",
        "from_node": depot,
        "to_service_start": "REAL_DEPOT",
        "travel_path": "VIRTUAL_DEPOT_TO_REAL_DEPOT",
        "travel_distance": REAL_DEPOT_DISTANCE,
        "serviced_edge": None,
        "service_direction": "VIRTUAL_DEPOT_TO_REAL_DEPOT",
        "service_distance": 0,
        "demand": 0,
        "cumulative_load": route_load,
        "mahalle": None
    })

    municipality_detail_df = pd.DataFrame(
        detailed_rows
    )

    return (
        total_cost,
        route_load,
        municipality_detail_df
    )


# =====================================================
# 21.3 BELEDİYE SERVİS SIRALARINI HAZIRLA
# =====================================================

municipality_ataturk_sefer1 = prepare_municipality_service_df(
    service_col="avgataturk_sefer1_service",
    order_col="avgataturk_sefer1_sira",
    mahalle_filter=municipality_ataturk_service_area
)

municipality_ataturk_sefer2 = prepare_municipality_service_df(
    service_col="avgataturk_sefer2_service",
    order_col="avgataturk_sefer2_sira",
    mahalle_filter=municipality_ataturk_service_area
)

municipality_kurucesme_avg = prepare_municipality_service_df(
    service_col="avg297_sefer1_service",
    order_col="avg297_sefer1_sira",
    mahalle_filter=municipality_kurucesme_service_area
)


# =====================================================
# 21.4 BELEDİYE ROTA MALİYETLERİNİ HESAPLA
# =====================================================

municipality_cost_ataturk_1, municipality_load_ataturk_1, municipality_df_ataturk_1 = calculate_municipality_route_cost(
    municipality_ataturk_sefer1,
    vehicle_id=1,
    route_label="Belediye Ataturk AVG Sefer 1"
)

municipality_cost_ataturk_2, municipality_load_ataturk_2, municipality_df_ataturk_2 = calculate_municipality_route_cost(
    municipality_ataturk_sefer2,
    vehicle_id=1,
    route_label="Belediye Ataturk AVG Sefer 2"
)

municipality_cost_kurucesme_avg, municipality_load_kurucesme_avg, municipality_df_kurucesme_avg = calculate_municipality_route_cost(
    municipality_kurucesme_avg,
    vehicle_id=1,
    route_label="Belediye Kurucesme AVG297"
)


# =====================================================
# 21.5 BELEDİYE ROTA DETAYLARINI BİRLEŞTİR
# =====================================================

municipality_route_details_df = pd.concat(
    [
        municipality_df_ataturk_1,
        municipality_df_ataturk_2,
        municipality_df_kurucesme_avg
    ],
    ignore_index=True
)


# =====================================================
# 21.6 BELEDİYE ROTA ÖZETİ
# =====================================================

municipality_route_summary_df = pd.DataFrame([
    {
        "Rota": "Atatürk AVG Sefer 1",
        "Araç": "AVG",
        "Servis Edge Sayısı": len(municipality_ataturk_sefer1),
        "Toplam Talep": municipality_load_ataturk_1,
        "Toplam Maliyet": municipality_cost_ataturk_1
    },
    {
        "Rota": "Atatürk AVG Sefer 2",
        "Araç": "AVG",
        "Servis Edge Sayısı": len(municipality_ataturk_sefer2),
        "Toplam Talep": municipality_load_ataturk_2,
        "Toplam Maliyet": municipality_cost_ataturk_2
    },
    {
        "Rota": "Kuruçeşme AVG297",
        "Araç": "AVG",
        "Servis Edge Sayısı": len(municipality_kurucesme_avg),
        "Toplam Talep": municipality_load_kurucesme_avg,
        "Toplam Maliyet": municipality_cost_kurucesme_avg
    }
])

print("\n===== BELEDİYE MEVCUT ROTA MALİYETİ SENARYOSU =====")
print(municipality_route_summary_df)

# =====================================================
# 21.7 BELEDİYE ROTALARINI KML'YE AKTAR
# =====================================================

belediye_kml_routes = [
    (
        municipality_df_ataturk_1,
        "BELEDIYE_ATATURK_AVG_ROTA_1",
        "BELEDIYE_Ataturk_Adatepe_Camlikule_AVG_Rota_1.kml"
    ),
    (
        municipality_df_ataturk_2,
        "BELEDIYE_ATATURK_AVG_ROTA_2",
        "BELEDIYE_Ataturk_Adatepe_Camlikule_AVG_Rota_2.kml"
    )
]

for route_df, route_label, file_name in belediye_kml_routes:

    if route_df is not None and not route_df.empty:

        route_df = route_df.copy()

        # Belediye rota dataframe'inde route_no yoksa ekle
        if "route_no" not in route_df.columns:
            route_df["route_no"] = 1

        write_ga_kml(
            route_df=route_df,
            vehicle_label=route_label,
            output_path=os.path.join(kml_folder, file_name)
        )

        print("Belediye KML oluşturuldu:", file_name)

    else:
        print("UYARI: Belediye rota dataframe boş:", route_label)
# =====================================================
# 22. KDS EXPORT TABLOLARI - OPTİMUM TOPLAMA PLANI
# =====================================================

kds_output_folder = "kds_outputs"
os.makedirs(kds_output_folder, exist_ok=True)


def create_operation_summary_from_capacity(capacity_df, plan_name):
    """
    KDS için belediye dilinde operasyon özeti oluşturur.
    CARP/GA teknik terimleri kullanıcıya yansıtılmaz.
    """

    if capacity_df.empty:
        return pd.DataFrame()

    summary = (
        capacity_df
        .groupby(["mahalle", "vehicle_name"])
        .agg(
            toplam_atik_l=("route_load", "sum"),
            toplam_mesafe_m=("route_total_distance", "sum"),
            tamamlanan_rota_sayisi=("route_no", "nunique"),
            ortalama_doluluk=("capacity_utilization_percent", "mean")
        )
        .reset_index()
    )

    summary["Operasyon Planı"] = plan_name

    summary["Mahalle"] = summary["mahalle"].replace({
        "atatürk": "Atatürk",
        "ataturk": "Atatürk",
        "kurucesme": "Kuruçeşme"
    })

    summary["Araç"] = summary["vehicle_name"]

    summary["Toplanan Atık (L)"] = summary["toplam_atik_l"].astype(int)

    summary["Toplam Mesafe (km)"] = (
        summary["toplam_mesafe_m"] / 1000
    ).round(2)

    summary["Tamamlanan Rota Sayısı"] = (
        summary["tamamlanan_rota_sayisi"].astype(int)
    )

    summary["Ortalama Araç Doluluğu (%)"] = (
        summary["ortalama_doluluk"].round(2)
    )

    # Maliyet bilgisi multi_run_summary_df'den gelecek
    cost_map = {
        "Atatürk AVG": final_best_cost_ataturk_avg,
        "Atatürk AZU": final_best_cost_ataturk_azu,
        "Kuruçeşme AVG": final_best_cost_kurucesme_avg,
        "Kuruçeşme AYT": final_best_cost_kurucesme_ayt,
        "Kuruçeşme AZU": final_best_cost_kurucesme_azu
    }

    summary["label_for_cost"] = (
        summary["Mahalle"] + " " + summary["Araç"]
    )

    summary["Tahmini Operasyon Maliyeti"] = (
        summary["label_for_cost"]
        .map(cost_map)
        .fillna(0)
        .round(2)
    )

    summary = summary[
        [
            "Operasyon Planı",
            "Mahalle",
            "Araç",
            "Toplanan Atık (L)",
            "Toplam Mesafe (km)",
            "Tamamlanan Rota Sayısı",
            "Tahmini Operasyon Maliyeti",
            "Ortalama Araç Doluluğu (%)"
        ]
    ]

    return summary


operation_summary_df = create_operation_summary_from_capacity(
    capacity_summary_df,
    plan_name="Optimum Toplama Planı"
)


# =====================================================
# 22.1 KDS CSV KAYITLARI
# =====================================================

operation_summary_df.to_csv(
    os.path.join(kds_output_folder, "operation_summary.csv"),
    index=False
)

capacity_summary_df.to_csv(
    os.path.join(kds_output_folder, "capacity_summary.csv"),
    index=False
)

final_route_details_df.to_csv(
    os.path.join(kds_output_folder, "final_route_details.csv"),
    index=False
)

multi_run_summary_df.to_csv(
    os.path.join(kds_output_folder, "multi_run_summary.csv"),
    index=False
)

municipality_route_summary_df.to_csv(
    os.path.join(kds_output_folder, "municipality_route_summary.csv"),
    index=False
)

# Belediye operasyonu için adım bazlı detay kaydı
# KDS'de Toplam Mesafe = travel_distance + service_distance olarak buradan okunur.
municipality_route_details_df.to_csv(
    os.path.join(kds_output_folder, "municipality_route_details.csv"),
    index=False
)

print("\nBelediye rota detayları kaydedildi:")
print(os.path.join(kds_output_folder, "municipality_route_details.csv"))

print("\n===== KDS OPERASYON ÖZETİ - OPTİMUM TOPLAMA PLANI =====")
print(operation_summary_df)

print("\nKDS çıktıları kaydedildi.")
print("Klasör:", kds_output_folder)

# =====================================================
# KDS EXPORT - MAHALLE ÖZETİ
# =====================================================

container_summary_rows = []

mahalle_gosterim_map = {
    "atatürk": "Atatürk",
    "ataturk": "Atatürk",
    "kuruçeşme": "Kuruçeşme",
    "kurucesme": "Kuruçeşme"
}

mahalle_filter_map = {
    "atatürk": "ataturk",
    "ataturk": "ataturk",
    "kuruçeşme": "kurucesme",
    "kurucesme": "kurucesme"
}

for mahalle_adi, container_path in container_files.items():

    if not os.path.exists(container_path):
        print(f"UYARI: Konteyner dosyası bulunamadı: {container_path}")
        continue

    cdf = pd.read_csv(container_path)

    cdf.columns = (
        cdf.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.lower()
    )

    # Mahalle adını normalize et
    mahalle_key = mahalle_filter_map.get(mahalle_adi, mahalle_adi)

    if "mahalle" in cdf.columns:
        cdf["mahalle"] = (
            cdf["mahalle"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({
                "atatürk": "ataturk",
                "ataturk": "ataturk",
                "kuruçeşme": "kurucesme",
                "kurucesme": "kurucesme",
                "çamlıkule": "camlikule",
                "camlikule": "camlikule",
                "adatepe": "adatepe"
            })
        )

        # ASIL DÜZELTME BURADA
        cdf = cdf[cdf["mahalle"] == mahalle_key].copy()

    cdf["adet"] = pd.to_numeric(
        cdf.get("adet", 0),
        errors="coerce"
    ).fillna(0).astype(int)

    cdf["tip"] = pd.to_numeric(
        cdf.get("tip", 0),
        errors="coerce"
    ).fillna(0).astype(int)

    mahalle_edges = df[
        df["source_mahalle"] == mahalle_adi
    ].copy()

    toplam_yol_sayisi = len(mahalle_edges)

    toplama_yapilacak_sokak = len(
        mahalle_edges[
            (mahalle_edges["tip1_talep"] > 0) |
            (mahalle_edges["tip2_talep"] > 0)
        ]
    )

    servis_orani = (
        (toplama_yapilacak_sokak / toplam_yol_sayisi) * 100
        if toplam_yol_sayisi > 0
        else 0
    )

    gunluk_toplama_miktari = (
        mahalle_edges["tip1_talep"].sum()
        + mahalle_edges["tip2_talep"].sum()
    )

    normal_konteyner_sayisi = cdf.loc[
        cdf["tip"] == 1,
        "adet"
    ].sum()

    yerustu_konteyner_sayisi = cdf.loc[
        cdf["tip"] == 2,
        "adet"
    ].sum()

    konteyner_noktasi_sayisi = len(cdf)

    container_summary_rows.append({
        "Mahalle": mahalle_gosterim_map.get(mahalle_adi, mahalle_adi),
        "Normal Konteyner Sayısı": int(normal_konteyner_sayisi),
        "Yerüstü Konteyner Sayısı": int(yerustu_konteyner_sayisi),
        "Konteyner Noktası Sayısı": int(konteyner_noktasi_sayisi),
        "Toplama Yapılacak Sokak Sayısı": int(toplama_yapilacak_sokak),
        "Günlük Toplama Miktarı (L)": int(gunluk_toplama_miktari),
        "Servis Gerektiren Yol Oranı (%)": round(servis_orani, 2)
    })

neighborhood_info_df = pd.DataFrame(container_summary_rows)

neighborhood_info_df.to_csv(
    os.path.join(kds_output_folder, "neighborhood_info.csv"),
    index=False
)

print("\n===== KDS MAHALLE ÖZETİ =====")
print(neighborhood_info_df)
# =====================================================
# BELEDİYE AVG OPERASYONU - MAHALLE BAZLI BİLGİ
# =====================================================

municipality_service_df = df[
    (df["avgataturk_sefer1_service"] == 1) |
    (df["avgataturk_sefer2_service"] == 1)
].copy()

# Sefer sayısı
municipality_service_df["sefer_sayisi"] = 0
municipality_service_df.loc[
    municipality_service_df["avgataturk_sefer1_service"] == 1,
    "sefer_sayisi"
] += 1

municipality_service_df.loc[
    municipality_service_df["avgataturk_sefer2_service"] == 1,
    "sefer_sayisi"
] += 1

# Mahalle bazlı servis özeti
municipality_neighborhood_info_df = (
    municipality_service_df
    .groupby("mahalle")
    .agg(
        toplama_yapilacak_sokak_sayisi=("ad", "count"),
        gunluk_toplama_miktari_litre=("tip1_talep", "sum"),
        servis_mesafesi_metre=("uzunluk", "sum")
    )
    .reset_index()
)

municipality_neighborhood_info_df["servis_mesafesi_km"] = (
    municipality_neighborhood_info_df["servis_mesafesi_metre"] / 1000
).round(2)

sefer_ozet_df = (
    municipality_service_df
    .groupby("mahalle")
    .agg(
        sefer1_var=("avgataturk_sefer1_service", "max"),
        sefer2_var=("avgataturk_sefer2_service", "max")
    )
    .reset_index()
)

sefer_ozet_df["sefer_sayisi"] = (
    sefer_ozet_df["sefer1_var"] + sefer_ozet_df["sefer2_var"]
)

municipality_neighborhood_info_df = municipality_neighborhood_info_df.merge(
    sefer_ozet_df[["mahalle", "sefer_sayisi"]],
    on="mahalle",
    how="left"
)

# Mahalle isimlerini düzgün göster
municipality_neighborhood_info_df["mahalle_gosterim"] = (
    municipality_neighborhood_info_df["mahalle"]
    .replace({
        "ataturk": "Atatürk",
        "adatepe": "Adatepe",
        "camlikule": "Çamlıkule"
    })
)

# Kolon sırası
municipality_neighborhood_info_df = municipality_neighborhood_info_df[
    [
        "mahalle_gosterim",
        "toplama_yapilacak_sokak_sayisi",
        "gunluk_toplama_miktari_litre",
        "servis_mesafesi_km",
        "sefer_sayisi"
    ]
]

municipality_neighborhood_info_df.to_csv(
    os.path.join("kds_outputs", "municipality_neighborhood_info.csv"),
    index=False
)

print("\nBelediye mahalle bazlı operasyon bilgisi kaydedildi:")
print(municipality_neighborhood_info_df)


