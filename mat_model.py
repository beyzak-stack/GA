#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 27 00:48:27 2026

@author: beyzakeskin
"""
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
from docplex.mp.model import Model

# 1. VERİYİ OKU
file_path = "CARP MODEL- Kurucesme Mahallesi- Edges.csv"

df = pd.read_csv(file_path)

# Kolon isimlerini temizle
df.columns = df.columns.str.strip().str.lower()

# Sayısal kolonlar
df["from_node"] = df["from_node"].astype(int)
df["to_node"] = df["to_node"].astype(int)

df["uzunluk"] = df["uzunluk"].astype(float)

df["tip1_talep"] = df["tip1_talep"].fillna(0).astype(int)
df["tip2_talep"] = df["tip2_talep"].fillna(0).astype(int)

df["avg_gecis"] = df["avg_gecis"].fillna(1).astype(int)
df["azu_gecis"] = df["azu_gecis"].fillna(0).astype(int)
df["ayt_gecis"] = df["ayt_gecis"].fillna(0).astype(int)

# yön bilgisi
df["yon"] = (
    df["yon"]
    .fillna("cift")
    .astype(str)
    .str.strip()
    .str.lower()
)

# mahalle bilgisi
df["mahalle"] = (
    df["mahalle"]
    .fillna("atatürk")
    .astype(str)
    .str.strip()
    .str.lower()
)

# edge id oluşturma
df["arc_id"] = range(1, len(df) + 1)

# Kontroller
for _, row in df.iterrows():

    if row["tip1_talep"] < 0 or row["tip2_talep"] < 0:
        raise ValueError(
            f"Arc {row['arc_id']} için negatif talep var!"
        )

    if row["yon"] not in ["cift", "tek"]:
        raise ValueError(
            f"Arc {row['arc_id']} için yön değeri hatalı: {row['yon']}"
        )

print("Veri başarıyla okundu.")
print("Toplam edge:", len(df))

print(
    "Tip1 talep olan edge:",
    len(df[df["tip1_talep"] > 0])
)

print(
    "Tip2 talep olan edge:",
    len(df[df["tip2_talep"] > 0])
)

print(
    "Depo bağlantı edge:",
    len(df[df["mahalle"] == "depo_baglanti"])
)

# 1.1 EDGE SINIFLANDIRMA

df["edge_turu"] = "travel"

df.loc[
    (df["tip1_talep"] > 0) | (df["tip2_talep"] > 0),
    "edge_turu"
] = "servis"

df.loc[
    df["mahalle"] == "depo_baglanti",
    "edge_turu"
] = "depo_baglanti"

print("\nEdge türü:")
print(df["edge_turu"].value_counts())

print("\nKontrol:")
print("Servis edge:", len(df[df["edge_turu"] == "servis"]))
print("Travel edge:", len(df[df["edge_turu"] == "travel"]))
print("Depo bağlantı edge:", len(df[df["edge_turu"] == "depo_baglanti"]))

# 2. KÜMELER VE PARAMETRELER

depot = 0

V = sorted(
    set(df["from_node"]).union(set(df["to_node"]))
)

E = set()       # yönsüz edge seti
A = set()       # yönlü arc seti
ER = set()      # required edge seti: (i, j, tip)

distance = {}
q = {}
edge_type = {}
edge_access = {}

for _, row in df.iterrows():

    i = int(row["from_node"])
    j = int(row["to_node"])
    d = float(row["uzunluk"])
    yon = row["yon"]

    tip1_demand = int(row["tip1_talep"])
    tip2_demand = int(row["tip2_talep"])

    e = tuple(sorted((i, j)))

    E.add(e)

    edge_type[e] = row["edge_turu"]

    edge_access[e] = {
    1: int(row["avg_gecis"]),   # AVG
    2: int(row["ayt_gecis"]),   # AYT
    3: int(row["azu_gecis"])    # AZU
}

    if yon == "cift":

        A.add((i, j))
        A.add((j, i))

        distance[i, j] = d
        distance[j, i] = d

    elif yon == "tek":

        A.add((i, j))
        distance[i, j] = d

    # Tip 1 required edge
    if tip1_demand > 0:

        ER.add((e[0], e[1], 1))

        q[e[0], e[1], 1] = (
            q.get((e[0], e[1], 1), 0)
            +
            tip1_demand
        )

    # Tip 2 required edge
    if tip2_demand > 0:

        ER.add((e[0], e[1], 2))

        q[e[0], e[1], 2] = (
            q.get((e[0], e[1], 2), 0)
            +
            tip2_demand
        )


# Her required edge için servis edilebilecek yönleri belirle
service_dirs = {}

for (i, j, tip) in ER:

    dirs = []

    if (i, j) in A:
        dirs.append((i, j))

    if (j, i) in A:
        dirs.append((j, i))

    if len(dirs) == 0:
        raise ValueError(
            f"Required edge ({i},{j}) tip {tip} için izinli yön yok!"
        )

    service_dirs[i, j, tip] = dirs


print("\nKümeler oluşturuldu.")
print("Node sayısı:", len(V))
print("Yönsüz edge sayısı:", len(E))
print("Yönlü arc sayısı:", len(A))
print("Required edge sayısı:", len(ER))

print(
    "Toplam Tip1 talep:",
    sum(q[u, v, tip] for (u, v, tip) in ER if tip == 1)
)

print(
    "Toplam Tip2 talep:",
    sum(q[u, v, tip] for (u, v, tip) in ER if tip == 2)
)

# 3. ARAÇLAR

C = [1, 2, 3]

vehicle_name = {
    1: "AVG",
    2: "AYT",
    3: "AZU"
}

# tip 1: standart konteyner
# tip 2: yerüstü konteyner
vehicle_allowed_tip = {
    1: [1],   # AVG tip1 toplar
    2: [1],   # AYT tip1 toplar (dar sokaklar)
    3: [2]    # AZU tip2 toplar
}

Q = {
    1: 73500,     # AVG kapasite
    2: 38500,     # AYT kapasite
    3: 165000     # AZU kapasite
}

# 4. MODEL

mdl = Model("CARP_Ataturk_heterojen_filo")

# 5. KARAR DEĞİŞKENLERİ

x = {}

for (u, v, tip) in ER:
    for (i, j) in service_dirs[u, v, tip]:
        for p in C:
            x[i, j, tip, p] = mdl.binary_var(
                name=f"x_{i}_{j}_tip{tip}_{vehicle_name[p]}"
            )

y = {}

for (i, j) in A:
    for p in C:
        y[i, j, p] = mdl.integer_var(
            lb=0,
            name=f"y_{i}_{j}_{vehicle_name[p]}"
        )

f = {}

for (i, j) in A:
    for p in C:
        f[i, j, p] = mdl.continuous_var(
            lb=0,
            name=f"f_{i}_{j}_{vehicle_name[p]}"
        )

print("\nKarar değişkenleri oluşturuldu.")
print("x değişkeni sayısı:", len(x))
print("y değişkeni sayısı:", len(y))
print("f değişkeni sayısı:", len(f))

# Gerçek depo ↔ sanal depo mesafesi (metre)
REAL_DEPOT_DISTANCE = 5600

# 6. AMAÇ FONKSİYONU

service_cost = mdl.sum(
    distance[i, j] * x[i, j, tip, p]
    for (i, j, tip, p) in x
)

travel_cost = mdl.sum(
    distance[i, j] * y[i, j, p]
    for (i, j) in A
    for p in C
)

# Depodan çıkış maliyeti
depot_access_cost = mdl.sum(

    2 * REAL_DEPOT_DISTANCE *

    (
        mdl.sum(
            y[depot, j, p]
            for j in V
            if (depot, j) in A
        )

        +

        mdl.sum(
            x[depot, j, tip, p]
            for (depot2, j, tip, p2) in x
            if depot2 == depot and p2 == p
        )

    )

    for p in C
)

mdl.minimize(
    service_cost
    +
    travel_cost
    +
    depot_access_cost
)

print("\nAmaç fonksiyonu oluşturuldu.")

# 7. KISITLAR

# M1-2: Her node için giren-çıkan derece dengesi
for node in V:
    for p in C:

        outgoing_y = mdl.sum(
            y[node, j, p]
            for j in V
            if (node, j) in A
        )

        incoming_y = mdl.sum(
            y[j, node, p]
            for j in V
            if (j, node) in A
        )

        outgoing_x = mdl.sum(
            var
            for (i, j, tip, pp), var in x.items()
            if pp == p and i == node
        )

        incoming_x = mdl.sum(
            var
            for (i, j, tip, pp), var in x.items()
            if pp == p and j == node
        )

        mdl.add_constraint(
            outgoing_y + outgoing_x == incoming_y + incoming_x,
            ctname=f"balance_{node}_{vehicle_name[p]}"
        )

# M1-4: Her required edge'in tam 1 kez servis edilmesi
for (u, v, tip) in ER:

    mdl.add_constraint(
        mdl.sum(
            x[i, j, tip, p]
            for (i, j) in service_dirs[u, v, tip]
            for p in C
        ) == 1,
        ctname=f"service_{u}_{v}_tip{tip}"
    )

# M1-9 / M1-12: Araç-konteyner tipi uygunluğu
for (i, j, tip, p), var in x.items():

    if tip not in vehicle_allowed_tip[p]:

        mdl.add_constraint(
            var == 0,
            ctname=f"type_{i}_{j}_tip{tip}_{vehicle_name[p]}"
        )

# M1-12 ek: Araç-edge erişim uygunluğu

for (i, j) in A:

    e = tuple(sorted((i, j)))

    for p in C:

        if edge_access[e].get(p, 1) == 0:

            mdl.add_constraint(
                y[i, j, p] == 0,
                ctname=f"access_y_{i}_{j}_{p}"
            )

            for (ii, jj, tip, pp), var in x.items():

                if pp == p and ii == i and jj == j:

                    mdl.add_constraint(
                        var == 0,
                        ctname=f"access_x_{i}_{j}_tip{tip}_{p}"
                    )

# M1-5: Her aracın sanal depodan en fazla 1 kez çıkması
for p in C:

    depot_out_y = mdl.sum(
        y[depot, j, p]
        for j in V
        if (depot, j) in A
    )

    depot_out_x = mdl.sum(
        var
        for (i, j, tip, pp), var in x.items()
        if pp == p and i == depot
    )

    mdl.add_constraint(
        depot_out_y + depot_out_x <= 1,
        ctname=f"depot_depart_{vehicle_name[p]}"
    )

# M1-6: Depo dışındaki node'larda yük/akış dengesi
for node in V:
    if node != depot:
        for p in C:

            collected_at_node = mdl.sum(
                q[u, v, tip] * x[i, j, tip, p]
                for (u, v, tip) in ER
                for (i, j) in service_dirs[u, v, tip]
                if j == node
            )

            mdl.add_constraint(
                mdl.sum(f[j, node, p] for j in V if (j, node) in A)
                -
                mdl.sum(f[node, j, p] for j in V if (node, j) in A)
                ==
                collected_at_node,
                ctname=f"flow_balance_{node}_{vehicle_name[p]}"
            )


# M1-7: Depodan çıkan akış = aracın topladığı toplam talep
for p in C:

    total_demand_p = mdl.sum(
        q[u, v, tip] * x[i, j, tip, p]
        for (u, v, tip) in ER
        for (i, j) in service_dirs[u, v, tip]
    )

    mdl.add_constraint(
        mdl.sum(f[depot, j, p] for j in V if (depot, j) in A)
        ==
        total_demand_p,
        ctname=f"flow_out_depot_{vehicle_name[p]}"
    )


# M1-8: Depoya giren akış = depoya doğru servis edilen edge talebi
for p in C:

    depot_collected = mdl.sum(
        q[u, v, tip] * x[i, j, tip, p]
        for (u, v, tip) in ER
        for (i, j) in service_dirs[u, v, tip]
        if j == depot
    )

    mdl.add_constraint(
        mdl.sum(f[i, depot, p] for i in V if (i, depot) in A)
        ==
        depot_collected,
        ctname=f"flow_into_depot_{vehicle_name[p]}"
    )

# M1-13 / M1-14 / M1-15: Kapasite ve bağlantı kısıtı
for (i, j) in A:
    for p in C:

        service_on_arc = mdl.sum(
            var
            for (ii, jj, tip, pp), var in x.items()
            if pp == p and ii == i and jj == j
        )

        mdl.add_constraint(
            f[i, j, p] <= Q[p] * (y[i, j, p] + service_on_arc),
            ctname=f"capacity_flow_{i}_{j}_{vehicle_name[p]}"
        )

mdl.export_as_lp("model_kontrol_ataturk.lp")
print(
    df[
        (df["from_node"] == 333) &
        (df["to_node"] == 435)
    ][
        [
            "arc_id",
            "from_node",
            "to_node",
            "tip1_talep",
            "tip2_talep",
            "avg_gecis",
            "ayt_gecis",
            "azu_gecis",
            "yon",
            "mahalle"
        ]
    ]
)

print("\nTip2 talep olup AZU giremeyen edge sayısı:")

print(
    df[
        (df["tip2_talep"] > 0) &
        (df["azu_gecis"] == 0)
    ][
        [
            "arc_id",
            "from_node",
            "to_node",
            "tip2_talep",
            "azu_gecis"
        ]
    ]
)
e_test = tuple(sorted((333, 435)))
sol = mdl.solve(log_output=True)

