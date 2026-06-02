#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun May 31 08:16:45 2026

@author: beyzakeskin
"""

import streamlit as st
import pandas as pd
import os
import json
import re
import xml.etree.ElementTree as ET
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Buca Atık Toplama KDS",
    layout="wide"
)

st.markdown("""
<style>

/* Ana içerik alanı */
.block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* Streamlit üst barını gizle */
header {
    visibility: hidden;
}

/* Sağ üst araç çubuğunu kaldır */
[data-testid="stToolbar"] {
    display: none;
}

/* Kırmızı çizgiyi kaldır */
[data-testid="stDecoration"] {
    display: none;
}

/* Deploy menüsünü kaldır */
[data-testid="stStatusWidget"] {
    display: none;
}

/* Footer kaldır */
footer {
    visibility: hidden;
}

/* Sayfa üst boşluğunu azalt */
[data-testid="stAppViewContainer"] {
    margin-top: 0rem;
}

</style>
""", unsafe_allow_html=True)
# =====================================================
# DOSYA YOLLARI
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KDS_DIR = os.path.join(BASE_DIR, "kds_outputs")
KML_DIR = os.path.join(BASE_DIR, "kml_outputs")

CONTAINER_FILES = {
    "Atatürk": os.path.join(
        BASE_DIR,
        "Ataturk Mah.- konteyner_noktalari.csv"
    ),
    "Kuruçeşme": os.path.join(
        BASE_DIR,
        "Kurucesme Mah.- konteyner_noktalari.csv"
    )
}

GOOGLE_MAPS_API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
# =====================================================
# YARDIMCI FONKSİYONLAR
# =====================================================

def load_csv(file_name):
    path = os.path.join(KDS_DIR, file_name)

    if not os.path.exists(path):
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as e:
        st.warning(f"Dosya okunamadı: {path} | {e}")
        return pd.DataFrame()


def normalize_text(text):
    return (
        str(text)
        .lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def filter_kml_files(all_files, selected_neighborhood, selected_vehicle, selected_operation_plan):
    filtered = all_files.copy()

    # Operasyon planı filtresi
    if selected_operation_plan == "Mevcut Belediye Operasyonu":
        filtered = [
            f for f in filtered
            if "belediye" in normalize_text(f)
        ]
    elif selected_operation_plan == "Optimum Toplama Planı":
        filtered = [
            f for f in filtered
            if "belediye" not in normalize_text(f)
        ]

    # Mahalle filtresi
    if selected_neighborhood == "Atatürk":
        filtered = [
            f for f in filtered
            if "ataturk" in normalize_text(f)
        ]

    elif selected_neighborhood == "Kuruçeşme":
        filtered = [
            f for f in filtered
            if "kurucesme" in normalize_text(f)
        ]

    # Araç filtresi
    if selected_vehicle != "Tümü":
        filtered = [
            f for f in filtered
            if f.upper().startswith(selected_vehicle.upper())
        ]

    return sorted(filtered)


def kml_to_paths(kml_file):
    paths = []

    try:
        tree = ET.parse(kml_file)
        root = tree.getroot()
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        for placemark in root.findall(".//kml:Placemark", ns):

            name_el = placemark.find("kml:name", ns)
            coord_el = placemark.find(".//kml:coordinates", ns)

            if coord_el is None or coord_el.text is None:
                continue

            name = name_el.text if name_el is not None else "Rota"
            coords = []

            for item in coord_el.text.strip().split():
                parts = item.split(",")

                if len(parts) < 2:
                    continue

                lon = float(parts[0])
                lat = float(parts[1])

                coords.append({
                    "lat": lat,
                    "lng": lon
                })

            if len(coords) >= 2:
                paths.append({
                    "name": name,
                    "coords": coords
                })

    except Exception as e:
        st.warning(f"KML okunamadı: {kml_file} | {e}")

    return paths

def container_csv_to_markers(csv_file, allowed_mahalleler=None):

    if not os.path.exists(csv_file):
        st.warning(f"Konteyner dosyası bulunamadı: {csv_file}")
        return []

    try:
        container_df = pd.read_csv(csv_file)
    except TimeoutError:
        st.warning(f"Konteyner dosyası zaman aşımına uğradı: {csv_file}")
        return []
    except Exception as e:
        st.warning(f"Konteyner dosyası okunamadı: {csv_file} | {e}")
        return []

    container_df.columns = (
        container_df.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
        .str.lower()
    )

    if "mahalle" in container_df.columns:

        container_df["mahalle"] = (
            container_df["mahalle"]
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

        if allowed_mahalleler is not None:
            allowed_mahalleler = [
                str(m).strip().lower()
                .replace("ü", "u")
                .replace("ç", "c")
                .replace("ş", "s")
                .replace("ı", "i")
                .replace("ö", "o")
                .replace("ğ", "g")
                for m in allowed_mahalleler
            ]

            container_df = container_df[
                container_df["mahalle"].isin(allowed_mahalleler)
            ].copy()

    if "wkt" not in container_df.columns:
        st.error("Konteyner CSV dosyasında 'wkt' kolonu bulunamadı.")
        return []

    markers = []

    for _, row in container_df.iterrows():

        wkt = str(row["wkt"]).strip()

        match = re.search(
            r"POINT\s*\(\s*([0-9\.\-]+)\s+([0-9\.\-]+)\s*\)",
            wkt,
            re.IGNORECASE
        )

        if not match:
            continue

        try:
            lon = float(match.group(1))
            lat = float(match.group(2))
        except ValueError:
            continue

        raw_tip = str(row.get("tip", "")).strip().lower()

        if raw_tip in ["2", "2.0", "tip2", "yerüstü", "yerustu"]:
            container_type = "2"
        else:
            container_type = "1"

        markers.append({
            "lat": lat,
            "lng": lon,
            "adres": str(row.get("ad", row.get("name", ""))),
            "adet": str(row.get("adet", "")),
            "tip": container_type,
            "mahalle": str(row.get("mahalle", ""))
        })

    return markers


def get_vehicle_type_from_file(file_name):
    file_name = str(file_name).upper()

    if file_name.startswith("AVG"):
        return "AVG"

    if file_name.startswith("AYT"):
        return "AYT"

    if file_name.startswith("AZU"):
        return "AZU"

    if "BELEDIYE" in file_name:
        return "BELEDIYE"

    return "DIGER"


def generate_kds_recommendation(selected_scenario):

    if selected_scenario == "Tek AZU Birleşik Toplama":
        return (
            "Tek AZU birleşik toplama senaryosu, iki mahalledeki Tip2 taleplerinin "
            "tek AZU aracıyla birlikte değerlendirilmesini sağlar."
        )

    if selected_scenario == "Atatürk Trafik Senaryosu":
        return (
            "Atatürk Mahallesi için saat bazlı trafik etkisi incelenmektedir. "
            "17:00-20:00 aralığı operasyon maliyetini artırabilir."
        )

    if selected_scenario == "Belediye Mevcut Rota Maliyeti":
        return (
            "Belediye servis sırası sabit kabul edilmiştir. "
            "Servisler arası travel path maliyeti shortest path yöntemiyle hesaplanmıştır."
        )

    return (
        "Mevcut GA sonuçları referans durum olarak kullanılmaktadır."
    )


def prepare_summary_data(summary_df, capacity_df, selected_neighborhood, selected_vehicle):
    summary_df = summary_df.copy()
    capacity_df = capacity_df.copy()

    # Mahalle filtresi
    if selected_neighborhood != "Tümü":

        mahalle_key = normalize_text(selected_neighborhood)

        if "label" in summary_df.columns:
            summary_df = summary_df[
                summary_df["label"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(mahalle_key, na=False)
            ]

        if "mahalle" in summary_df.columns:
            summary_df = summary_df[
                summary_df["mahalle"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(mahalle_key, na=False)
            ]

        if "mahalle" in capacity_df.columns:
            capacity_df = capacity_df[
                capacity_df["mahalle"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(mahalle_key, na=False)
            ]

        if "label" in capacity_df.columns:
            capacity_df = capacity_df[
                capacity_df["label"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(mahalle_key, na=False)
            ]

    # Araç filtresi
    if selected_vehicle != "Tümü":

        if "vehicle_name" in summary_df.columns:
            summary_df = summary_df[
                summary_df["vehicle_name"].astype(str).str.upper() == selected_vehicle
            ]

        if "vehicle_name" in capacity_df.columns:
            capacity_df = capacity_df[
                capacity_df["vehicle_name"].astype(str).str.upper() == selected_vehicle
            ]

    return summary_df, capacity_df


def prepare_operation_summary_data(operation_summary_df, selected_operation_plan, selected_neighborhood, selected_vehicle):
    filtered_df = operation_summary_df.copy()

    if filtered_df.empty:
        return filtered_df

    if "Operasyon Planı" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Operasyon Planı"].astype(str) == selected_operation_plan
        ]

    if selected_neighborhood != "Tümü" and "Mahalle" in filtered_df.columns:
        mahalle_key = normalize_text(selected_neighborhood)
        filtered_df = filtered_df[
            filtered_df["Mahalle"]
            .astype(str)
            .apply(normalize_text)
            .str.contains(mahalle_key, na=False)
        ]

    if selected_vehicle != "Tümü" and "Araç" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Araç"].astype(str).str.upper() == selected_vehicle
        ]

    return filtered_df


def safe_sum(df, column_name):
    if df.empty or column_name not in df.columns:
        return "-"
    return round(pd.to_numeric(df[column_name], errors="coerce").fillna(0).sum(), 2)


def safe_nunique(df, column_name):
    if df.empty or column_name not in df.columns:
        return "-"
    return df[column_name].nunique()


# =====================================================
# DATAFRAME OKUMA
# =====================================================

operation_summary_df = load_csv("operation_summary.csv")
multi_run_summary_df = load_csv("multi_run_summary.csv")
final_route_details_df = load_csv("final_route_details.csv")
capacity_summary_df = load_csv("capacity_summary.csv")
azu_scenario_comparison_df = load_csv("azu_scenario_comparison.csv")
traffic_scenario_comparison_df = load_csv("traffic_scenario_comparison.csv")
municipality_route_summary_df = load_csv("municipality_route_summary.csv")
municipality_route_details_df = load_csv("municipality_route_details.csv")
neighborhood_info_df = load_csv("neighborhood_info.csv")

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.header("Kontrol Paneli")

selected_operation_plan = st.sidebar.selectbox(
    "Operasyon Planı",
    [
        "Optimum Toplama Planı",
        "Mevcut Belediye Operasyonu",
        "Alternatif Operasyonlar"
    ]
)

selected_alternative_plan = None

if selected_operation_plan == "Alternatif Operasyonlar":

    selected_alternative_plan = st.sidebar.selectbox(
        "Alternatif Plan",
        [
            "Yoğun Trafik Durumu",
            "Tek AZU Operasyonu"
        ]
    )

selected_neighborhood = st.sidebar.selectbox(
    "Mahalle",
    ["Tümü", "Atatürk", "Kuruçeşme"]
)

if selected_neighborhood == "Atatürk":
    vehicle_options = ["Tümü", "AVG", "AZU"]

elif selected_neighborhood == "Kuruçeşme":
    vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

else:
    vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

selected_vehicle = st.sidebar.selectbox(
    "Araç",
    vehicle_options
)

st.sidebar.divider()

show_containers = st.sidebar.checkbox(
    "Konteynerleri Göster",
    value=False
)

show_routes = st.sidebar.checkbox(
    "Rotaları Göster",
    value=True
)

st.sidebar.divider()

st.sidebar.markdown("### Rota Katmanları")

all_kml_files = []

if os.path.exists(KML_DIR):
    all_kml_files = [
        f for f in os.listdir(KML_DIR)
        if f.lower().endswith(".kml")
    ]

filtered_kml_files = filter_kml_files(
    all_files=all_kml_files,
    selected_neighborhood=selected_neighborhood,
    selected_vehicle=selected_vehicle,
    selected_operation_plan=selected_operation_plan
)

selected_kml_files = st.sidebar.multiselect(
    "Rota Seçiniz",
    filtered_kml_files,
    default=[]
)

# =====================================================
# BAŞLIK
# =====================================================

st.title("Buca Atık Toplama Karar Destek Sistemi")
st.caption("Operasyon planı, mahalle ve araç bazlı rota görselleştirme ekranı")

# =====================================================
# HARİTA VERİLERİ
# =====================================================

container_markers = []

if show_containers:

    if selected_neighborhood == "Atatürk":

        if selected_operation_plan == "Mevcut Belediye Operasyonu":
            allowed_container_mahalleler = [
                "ataturk",
                "adatepe",
                "camlikule"
            ]
        else:
            allowed_container_mahalleler = [
                "ataturk"
            ]

        container_markers = container_csv_to_markers(
            CONTAINER_FILES["Atatürk"],
            allowed_mahalleler=allowed_container_mahalleler
        )

    elif selected_neighborhood == "Kuruçeşme":

        container_markers = container_csv_to_markers(
            CONTAINER_FILES["Kuruçeşme"],
            allowed_mahalleler=["kurucesme"]
        )

    else:

        container_markers.extend(
            container_csv_to_markers(
                CONTAINER_FILES["Atatürk"],
                allowed_mahalleler=None
            )
        )

        container_markers.extend(
            container_csv_to_markers(
                CONTAINER_FILES["Kuruçeşme"],
                allowed_mahalleler=None
            )
        )

route_paths = []

if show_routes:

    for selected_kml in selected_kml_files:

        selected_kml_path = os.path.join(
            KML_DIR,
            selected_kml
        )

        loaded_paths = kml_to_paths(
            selected_kml_path
        )

        vehicle_type = get_vehicle_type_from_file(
            selected_kml
        )

        for item in loaded_paths:
            item["vehicle_type"] = vehicle_type
            item["file_name"] = selected_kml

        route_paths.extend(loaded_paths)

route_paths_js = json.dumps(route_paths)
container_markers_js = json.dumps(container_markers)

# Harita merkezi
if selected_neighborhood == "Atatürk":
    map_center = {"lat": 38.3712, "lng": 27.1855}
    map_zoom = 15

elif selected_neighborhood == "Kuruçeşme":
    map_center = {"lat": 38.3655, "lng": 27.1700}
    map_zoom = 15

else:
    map_center = {"lat": 38.3685, "lng": 27.1780}
    map_zoom = 14

# =====================================================
# GOOGLE MAPS HTML
# =====================================================

html_template = """
<!DOCTYPE html>
<html>
<head>
<script src="https://maps.googleapis.com/maps/api/js?key={api_key}"></script>

<script>
function initMap() {{

    var map = new google.maps.Map(document.getElementById("map"), {{
        zoom: {map_zoom},
        center: {map_center},
        mapTypeId: "roadmap"
    }});

    var routePaths = {route_paths_js};
    var containerMarkers = {container_markers_js};
    function addLegend(routePaths, containerMarkers) {{

    var hasAVG = routePaths.some(item => item.vehicle_type === "AVG");
    var hasAYT = routePaths.some(item => item.vehicle_type === "AYT");
    var hasAZU = routePaths.some(item => item.vehicle_type === "AZU");
    var hasBelediye = routePaths.some(item => item.vehicle_type === "BELEDIYE");

    var hasContainers = containerMarkers.length > 0;

    var legendRows = "";

    if (hasAVG) {{
        legendRows +=
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #E11D48;margin-right:8px;"></span>AVG Toplama</div>' +
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #1D4ED8;margin-right:8px;"></span>AVG Geçiş</div>';
    }}

    if (hasAYT) {{
        legendRows +=
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #F97316;margin-right:8px;"></span>AYT Toplama</div>' +
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #FDBA74;margin-right:8px;"></span>AYT Geçiş</div>';
    }}

    if (hasAZU) {{
        legendRows +=
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #7E22CE;margin-right:8px;"></span>AZU Toplama</div>' +
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #16A34A;margin-right:8px;"></span>AZU Geçiş</div>';
    }}

    if (hasBelediye) {{
        legendRows +=
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #111827;margin-right:8px;"></span>Belediye Toplama</div>' +
            '<div><span style="display:inline-block;width:34px;border-top:4px solid #64748B;margin-right:8px;"></span>Belediye Geçiş</div>';
    }}

    if (hasContainers) {{
        if (legendRows !== "") {{
            legendRows += '<div style="height:6px;"></div>';
        }}

        legendRows +=
            '<div><span style="display:inline-block;width:12px;height:12px;background:#0EA5E9;border-radius:50%;margin-right:8px;"></span>Normal Konteyner</div>' +
            '<div><span style="display:inline-block;width:12px;height:12px;background:#A855F7;border-radius:50%;margin-right:8px;"></span>Yerüstü Konteyner</div>';
    }}

    if (legendRows === "") {{
        return;
    }}

    var legend = document.createElement("div");

    legend.innerHTML =
        '<div style="' +
        'background:white;' +
        'padding:12px 14px;' +
        'margin:10px;' +
        'border-radius:10px;' +
        'box-shadow:0 2px 8px rgba(0,0,0,0.25);' +
        'font-family:Arial;' +
        'font-size:13px;' +
        'color:#111827;' +
        'min-width:170px;' +
        '">' +
        '<div style="font-weight:bold; margin-bottom:8px;">Lejant</div>' +
        legendRows +
        '</div>';

    map.controls[google.maps.ControlPosition.LEFT_BOTTOM].push(legend);
}}

function getLineType(name) {{
    if (name.includes("Servis") || name.includes("service")) {{
        return "Servis yolu";
    }}
    return "Travel yolu";
}}

function drawRouteLines(paths) {{

    paths.forEach(function(item) {{

        var vehicleType = item.vehicle_type;
        var lowerName = String(item.name).toLowerCase();
        var isService = item.name.includes("Servis") || lowerName.includes("service");
        var lineType = getLineType(item.name);

        var color = "#2563EB";

        if (vehicleType === "AVG" && isService) {{
            color = "#E11D48";
        }}
        else if (vehicleType === "AVG" && !isService) {{
            color = "#1D4ED8";
        }}
        else if (vehicleType === "AYT" && isService) {{
            color = "#F97316";
        }}
        else if (vehicleType === "AYT" && !isService) {{
            color = "#FDBA74";
        }}
        else if (vehicleType === "AZU" && isService) {{
            color = "#7E22CE";
        }}
        else if (vehicleType === "AZU" && !isService) {{
            color = "#16A34A";
        }}
        else if (vehicleType === "BELEDIYE" && isService) {{
            color = "#111827";
        }}
        else if (vehicleType === "BELEDIYE" && !isService) {{
            color = "#64748B";
        }}

        var line = new google.maps.Polyline({{
            path: item.coords,
            geodesic: true,
            strokeColor: color,
            strokeOpacity: isService ? 1.0 : 0.80,
            strokeWeight: isService ? 6 : 4,
            zIndex: isService ? 30 : 20
        }});

        line.setMap(map);

        var infoWindow = new google.maps.InfoWindow({{
            content:
                '<div style="font-family:Arial; min-width:280px;">' +
                '<h3 style="margin:0 0 8px 0;">' + vehicleType + '</h3>' +
                '<b>Dosya:</b><br>' + item.file_name + '<br><br>' +
                '<b>Rota bilgisi:</b><br>' + item.name + '<br><br>' +
                '<b>Çizgi tipi:</b> ' + lineType +
                '</div>'
        }});

        line.addListener("click", function(event) {{
            infoWindow.setPosition(event.latLng);
            infoWindow.open(map);
        }});

    }});
}}

drawRouteLines(routePaths);
addLegend(routePaths, containerMarkers);
    containerMarkers.forEach(function(item) {{

        var point = {{
            lat: Number(item.lat),
            lng: Number(item.lng)
        }};

        var infoWindow = new google.maps.InfoWindow({{
            content:
                '<div style="font-family:Arial; min-width:220px;">' +
                '<h3 style="margin:0 0 8px 0;">Konteyner</h3>' +
                '<b>Adres:</b> ' + item.adres + '<br>' +
                '<b>Adet:</b> ' + item.adet + '<br>' +
                '<b>Tip:</b> ' + item.tip + '<br>' +
                '<b>Mahalle:</b> ' + item.mahalle +
                '</div>',
            position: point
        }});
        var containerType = String(item.tip).trim();

var containerColor = "#0EA5E9";

if (containerType === "2") {{
    containerColor = "#A855F7";
}}
        var containerType = String(item.tip).trim();

var containerColor = "#0EA5E9";

if (
    containerType === "2" ||
    containerType.toLowerCase().includes("tip2") ||
    containerType.toLowerCase().includes("yer")
) {{
    containerColor = "#A855F7";
}}

var circle = new google.maps.Circle({{
    strokeColor: "#FFFFFF",
    strokeOpacity: 1,
    strokeWeight: 2,
    fillColor: containerColor,
    fillOpacity: 0.95,
    map: map,
    center: point,
    radius: 9,
    zIndex: 9999
}});
        circle.addListener("click", function() {{
            infoWindow.open(map);
        }});

    }});

}}
</script>
</head>

<body onload="initMap()" style="margin:0;">
<div id="map" style="
    width:100%;
    height:720px;
    border-radius:18px;
"></div>
</body>
</html>
"""

html_code = html_template.format(
    api_key=GOOGLE_MAPS_API_KEY,
    map_center=json.dumps(map_center),
    map_zoom=map_zoom,
    route_paths_js=route_paths_js,
    container_markers_js=container_markers_js
)

# =====================================================
# HARİTA EN ÜSTTE
# =====================================================

st.subheader("Operasyon Haritası")

components.html(
    html_code,
    height=750
)

# =====================================================
# MAHALLE ÖZETİ
# =====================================================

def format_number(value, suffix=""):
    if value == "-":
        return "-"
    try:
        value = float(value)
        if value.is_integer():
            return f"{int(value):,}".replace(",", ".") + suffix
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + suffix
    except:
        return str(value)
    
st.subheader("📍 Seçilen Mahalle Bilgileri")

if selected_neighborhood == "Tümü":
    st.info(
        "Mahalle özeti seçilen mahalleye göre gösterilmektedir. "
        "Lütfen Atatürk veya Kuruçeşme mahallesini seçiniz."
    )

elif neighborhood_info_df.empty:
    st.info(
        "Mahalle özeti verisi bulunamadı. "
        "GA kodunu çalıştırıp kds_outputs/neighborhood_info.csv dosyasını oluşturmalısın."
    )

else:
    neighborhood_filtered_df = neighborhood_info_df[
        neighborhood_info_df["Mahalle"].astype(str) == selected_neighborhood
    ].copy()

    if neighborhood_filtered_df.empty:
        st.warning("Seçilen mahalle için mahalle özeti bulunamadı.")

    else:
        mahalle_row = neighborhood_filtered_df.iloc[0]

        normal_container_count = mahalle_row.get("Normal Konteyner Sayısı", "-")
        aboveground_container_count = mahalle_row.get("Yerüstü Konteyner Sayısı", "-")
        container_point_count = mahalle_row.get("Konteyner Noktası Sayısı", "-")
        service_street_count = mahalle_row.get("Toplama Yapılacak Sokak Sayısı", "-")
        daily_collection_amount = mahalle_row.get("Günlük Toplama Miktarı (L)", "-")
        service_required_ratio = mahalle_row.get("Servis Gerektiren Yol Oranı (%)", "-")

        st.markdown("""
<style>
.kpi-card {
    background-color: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 12px 16px;
    min-height: 85px;
}

.kpi-title {
    font-size: 11px;
    color: #A1A1AA;
    margin-bottom: 4px;
}

.kpi-value {
    font-size: 18px;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1;
}

.kpi-icon {
    font-size: 14px;
    margin-bottom: 4px;
}
</style>
""", unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">🗑️</div>
                    <div class="kpi-title">Normal Konteyner Adedi</div>
                    <div class="kpi-value">{format_number(normal_container_count)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">🗑️</div>
                    <div class="kpi-title">Yerüstü Konteyner Adedi</div>
                    <div class="kpi-value">{format_number(aboveground_container_count)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">📍</div>
                    <div class="kpi-title">Konteyner Noktası Sayısı</div>
                    <div class="kpi-value">{format_number(container_point_count)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        col4, col5, col6 = st.columns(3)

        with col4:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">🛣️</div>
                    <div class="kpi-title">Toplama Yapılacak Sokak Sayısı</div>
                    <div class="kpi-value">{format_number(service_street_count)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col5:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">📦</div>
                    <div class="kpi-title">Günlük Toplama Miktarı</div>
                    <div class="kpi-value">{format_number(daily_collection_amount, " L")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col6:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">📊</div>
                    <div class="kpi-title">Servis Gerektiren Yol Oranı</div>
                    <div class="kpi-value">{format_number(service_required_ratio, "%")}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
operation_filtered_df = prepare_operation_summary_data(
    operation_summary_df=operation_summary_df,
    selected_operation_plan=selected_operation_plan,
    selected_neighborhood=selected_neighborhood,
    selected_vehicle=selected_vehicle
)           
# =====================================================
# TABLOLAR
# =====================================================

st.subheader("Operasyon Sonuçları")

if selected_operation_plan == "Mevcut Belediye Operasyonu":

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Operasyon Özeti",
            "Araç / Rota Performansı",
            "Belediye Rota Verisi",
            "Rota Detayları"
        ]
    )

elif selected_operation_plan == "Alternatif Operasyonlar":

    tab1, tab_alt = st.tabs(
        [
            "Operasyon Özeti",
            "Alternatif Plan Karşılaştırması"
        ]
    )

else:

    tab1, tab2, tab4 = st.tabs(
        [
            "Operasyon Özeti",
            "Araç / Rota Performansı",
            "Rota Detayları"
        ]
    )

with tab1:

    st.write("Seçilen operasyon planına göre mahalle ve araç bazlı özet")

    if not operation_filtered_df.empty:

        if selected_neighborhood == "Tümü":

            st.info(
                "Operasyon özeti mahalle bazlı değerlendirme için gösterilmektedir. "
                "Lütfen Atatürk veya Kuruçeşme mahallesini seçiniz."
            )

        else:

            st.markdown("### 📊 Operasyon Değerlendirmesi")

            total_waste_tab1 = operation_filtered_df["Toplanan Atık (L)"].sum()

            total_distance_tab1 = operation_filtered_df["Toplam Mesafe (km)"].sum()

            vehicle_count_tab1 = (
                operation_filtered_df["Araç"]
                .astype(str)
                .nunique()
            )

            route_count_tab1 = (
                operation_filtered_df["Tamamlanan Rota Sayısı"]
                .sum()
            )

            best_vehicle_row = operation_filtered_df.loc[
                operation_filtered_df["Toplanan Atık (L)"].idxmax()
            ]

            best_vehicle = best_vehicle_row["Araç"]

            best_vehicle_waste = best_vehicle_row["Toplanan Atık (L)"]

            c1, c2, c3, c4, c5 = st.columns(5)

            with c1:
                st.metric(
                    "♻️ Toplanan Atık",
                    f"{total_waste_tab1:,.0f} L"
                )

            with c2:
                st.metric(
                    "🛣️ Toplam Mesafe",
                    f"{total_distance_tab1:,.2f} km"
                )

            with c3:
                st.metric(
                    "🚛 Kullanılan Araç",
                    f"{vehicle_count_tab1}"
                )

            with c4:
                st.metric(
                    "🏆 En Fazla Toplayan Araç",
                    f"{best_vehicle}",
                    f"{best_vehicle_waste:,.0f} L"
                )

            with c5:
                st.metric(
                    "📍 Tamamlanan Rota",
                    f"{route_count_tab1:,.0f}"
                )

        st.markdown("### 📋 Operasyon Özeti Tablosu")

        st.dataframe(
            operation_filtered_df,
            use_container_width=True
        )

    else:

        st.warning(
            "operation_summary.csv bulunamadı veya seçili filtreye uygun kayıt yok."
        )
        
if selected_operation_plan == "Alternatif Operasyonlar":

    with tab_alt:

        if selected_alternative_plan == "Tek AZU Operasyonu":

            st.subheader("🚛 Tek AZU Operasyonu")

            if not azu_scenario_comparison_df.empty:

                st.dataframe(
                    azu_scenario_comparison_df,
                    use_container_width=True
                )

                st.markdown("### 📊 Tek AZU Plan Karşılaştırması")

                chart_df = azu_scenario_comparison_df.copy()

                numeric_cols = chart_df.select_dtypes(
                    include=["int64", "float64"]
                ).columns.tolist()

                if len(numeric_cols) > 0:
                    st.bar_chart(
                        chart_df[numeric_cols],
                        use_container_width=True
                    )

            else:
                st.warning("azu_scenario_comparison.csv bulunamadı.")

        elif selected_alternative_plan == "Yoğun Trafik Durumu":

            st.subheader("🚦 Yoğun Trafik Durumu")

            if not traffic_scenario_comparison_df.empty:

                st.dataframe(
                    traffic_scenario_comparison_df,
                    use_container_width=True
                )

                st.markdown("### 📊 Trafik Etkisi Karşılaştırması")

                chart_df = traffic_scenario_comparison_df.copy()

                numeric_cols = chart_df.select_dtypes(
                    include=["int64", "float64"]
                ).columns.tolist()

                if len(numeric_cols) > 0:
                    st.bar_chart(
                        chart_df[numeric_cols],
                        use_container_width=True
                    )

            else:
                st.warning("traffic_scenario_comparison.csv bulunamadı.")
                
with tab2:

    st.write("Araç ve rota bazlı operasyon performansı")

    summary_df, capacity_df = prepare_summary_data(
        summary_df=multi_run_summary_df,
        capacity_df=capacity_summary_df,
        selected_neighborhood=selected_neighborhood,
        selected_vehicle=selected_vehicle
    )

    if not capacity_df.empty:

        capacity_display_df = capacity_df.rename(columns={
            "mahalle": "Mahalle",
            "vehicle_name": "Araç",
            "route_no": "Rota No",
            "route_load": "Toplanan Atık (L)",
            "service_distance": "Toplama Yapılan Mesafe (m)",
            "travel_distance": "Geçiş Mesafesi (m)",
            "vehicle_capacity": "Araç Kapasitesi (L)",
            "unused_capacity": "Kalan Kapasite (L)",
            "capacity_utilization_percent": "Araç Doluluk Oranı (%)",
            "capacity_ok": "Kapasite Uygun",
            "route_total_distance": "Toplam Mesafe (m)"
        })

        display_columns = [
            "Mahalle",
            "Araç",
            "Rota No",
            "Toplanan Atık (L)",
            "Araç Kapasitesi (L)",
            "Kalan Kapasite (L)",
            "Araç Doluluk Oranı (%)",
            "Toplama Yapılan Mesafe (m)",
            "Geçiş Mesafesi (m)",
            "Toplam Mesafe (m)",
            "Kapasite Uygun"
        ]

        capacity_display_df = capacity_display_df[
            [col for col in display_columns if col in capacity_display_df.columns]
        ]

        if selected_neighborhood == "Tümü":

            st.info(
                "Araç performans grafikleri mahalle bazlı değerlendirme için gösterilmektedir. "
                "Lütfen Atatürk veya Kuruçeşme mahallesini seçiniz."
            )

        else:

            st.markdown("### Araç Performans Analizi")

            chart_df = capacity_display_df.copy()

            numeric_columns = [
                "Toplanan Atık (L)",
                "Araç Kapasitesi (L)",
                "Kalan Kapasite (L)",
                "Araç Doluluk Oranı (%)",
                "Toplama Yapılan Mesafe (m)",
                "Geçiş Mesafesi (m)",
                "Toplam Mesafe (m)"
            ]

            for col in numeric_columns:
                if col in chart_df.columns:
                    chart_df[col] = pd.to_numeric(
                        chart_df[col],
                        errors="coerce"
                    ).fillna(0)

            if not chart_df.empty:

                st.markdown("**Rota Bazlı Doluluk Oranı (%)**")

                route_fill_df = chart_df.copy()

                route_fill_df["Rota Etiketi"] = (
                    route_fill_df["Araç"].astype(str)
                    + " - Rota "
                    + route_fill_df["Rota No"].astype(str)
                )

                st.bar_chart(
                    route_fill_df.set_index("Rota Etiketi")["Araç Doluluk Oranı (%)"],
                    use_container_width=True
                )

                col_g1, col_g2, col_g3 = st.columns(3)

                with col_g1:
                    st.markdown("**Toplama / Geçiş Mesafesi**")

                    distance_compare_df = chart_df.copy()
                    distance_compare_df["Toplama (m)"] = distance_compare_df["Toplama Yapılan Mesafe (m)"]
                    distance_compare_df["Geçiş (m)"] = distance_compare_df["Geçiş Mesafesi (m)"]

                    st.bar_chart(
                        distance_compare_df.set_index("Araç")[["Toplama (m)", "Geçiş (m)"]],
                        use_container_width=True
                    )

                with col_g2:
                    st.markdown("**Kapasite Kullanımı (L)**")

                    capacity_compare_df = chart_df.copy()
                    capacity_compare_df["Kullanılan Kapasite"] = capacity_compare_df["Toplanan Atık (L)"]
                    capacity_compare_df["Boş Kapasite"] = capacity_compare_df["Kalan Kapasite (L)"]

                    st.bar_chart(
                        capacity_compare_df.set_index("Araç")[["Kullanılan Kapasite", "Boş Kapasite"]],
                        use_container_width=True
                    )

                with col_g3:
                    st.markdown("**Verimlilik (L/km)**")

                    efficiency_df = chart_df.copy()

                    efficiency_df["Verimlilik (L/km)"] = (
                        efficiency_df["Toplanan Atık (L)"] /
                        (efficiency_df["Toplam Mesafe (m)"] / 1000)
                    )

                    efficiency_df["Verimlilik (L/km)"] = (
                        efficiency_df["Verimlilik (L/km)"]
                        .replace([float("inf"), -float("inf")], 0)
                        .fillna(0)
                    )

                    st.bar_chart(
                        efficiency_df.set_index("Araç")["Verimlilik (L/km)"],
                        use_container_width=True
                    )

                comparison_count = chart_df[["Araç", "Rota No"]].drop_duplicates().shape[0]

                if comparison_count > 1:

                    st.markdown("### Operasyon Değerlendirmesi")

                    best_fill = chart_df.loc[
                        chart_df["Araç Doluluk Oranı (%)"].idxmax()
                    ]

                    best_efficiency = efficiency_df.loc[
                        efficiency_df["Verimlilik (L/km)"].idxmax()
                    ]

                    best_collection = chart_df.loc[
                        chart_df["Toplanan Atık (L)"].idxmax()
                    ]

                    c1, c2, c3 = st.columns(3)

                    with c1:
                        st.success(
                            f"🏆 En Yüksek Doluluk\n\n"
                            f"{best_fill['Araç']} - "
                            f"%{best_fill['Araç Doluluk Oranı (%)']:.1f}"
                        )

                    with c2:
                        st.info(
                            f"🚛 En Verimli Araç\n\n"
                            f"{best_efficiency['Araç']} - "
                            f"{best_efficiency['Verimlilik (L/km)']:.0f} L/km"
                        )

                    with c3:
                        st.warning(
                            f"📦 En Fazla Toplama\n\n"
                            f"{best_collection['Araç']} - "
                            f"{best_collection['Toplanan Atık (L)']:,.0f} L".replace(",", ".")
                        )

                else:
                    st.info(
                        "Operasyon değerlendirmesi için en az iki rota veya araç gereklidir. "
                        "Seçili filtrede yalnızca tek rota bulunduğu için karşılaştırma yapılmadı."
                    )

        st.markdown("### 📋 Araç / Rota Performans Tablosu")

        st.dataframe(
            capacity_display_df,
            use_container_width=True
        )

    else:
        st.warning("capacity_summary.csv bulunamadı veya seçili filtreye uygun kayıt yok.")
        
if selected_operation_plan == "Mevcut Belediye Operasyonu":
    with tab3:

        st.write("Belediyeden alınan rota verilerine göre hesaplanan mevcut operasyon bilgileri")

        if not municipality_route_summary_df.empty:
            st.dataframe(
                municipality_route_summary_df,
                use_container_width=True
            )
        else:
            st.warning("municipality_route_summary.csv bulunamadı.")

        if not municipality_route_details_df.empty:
            with st.expander("Belediye rota detayları"):
                st.dataframe(
                    municipality_route_details_df,
                    use_container_width=True
                )

with tab4:

    st.write("Seçilen filtrelere göre oluşturulan toplama rotası adımları")

    route_df = final_route_details_df.copy()

    if not route_df.empty:

        if selected_neighborhood != "Tümü" and "mahalle" in route_df.columns:

            key = normalize_text(selected_neighborhood)

            route_df = route_df[
                route_df["mahalle"]
                .astype(str)
                .apply(normalize_text)
                .str.contains(key, na=False)
            ]

        if selected_vehicle != "Tümü" and "vehicle_name" in route_df.columns:

            route_df = route_df[
                route_df["vehicle_name"].astype(str).str.upper() == selected_vehicle
            ]

        # Sadece gerçek servis adımlarını göster
        if "step_no" in route_df.columns:
            route_df = route_df[
                ~route_df["step_no"]
                .astype(str)
                .isin(["START", "RETURN", "END"])
            ].copy()

        route_display_df = route_df.rename(columns={
            "mahalle": "Mahalle",
            "vehicle_name": "Araç",
            "route_no": "Rota No",
            "step_no": "Sıra",
            "yol_adi": "Yol Adı",
            "serviced_edge": "Servis No",
            "service_direction": "Servis Yönü",
            "service_distance": "Toplama Mesafesi (m)",
            "travel_distance": "Geçiş Mesafesi (m)",
            "demand": "Toplanacak Miktar (L)",
            "cumulative_load": "Araçtaki Toplam Yük (L)"
        })

        display_columns = [
            "Mahalle",
            "Araç",
            "Rota No",
            "Sıra",
            "Yol Adı",
            "Toplanacak Miktar (L)",
            "Araçtaki Toplam Yük (L)",
            "Toplama Mesafesi (m)",
            "Geçiş Mesafesi (m)"
        ]

        route_display_df = route_display_df[
            [col for col in display_columns if col in route_display_df.columns]
        ]

        if not route_display_df.empty:

            numeric_cols = [
                "Toplanacak Miktar (L)",
                "Araçtaki Toplam Yük (L)",
                "Toplama Mesafesi (m)",
                "Geçiş Mesafesi (m)"
            ]

            for col in numeric_cols:
                if col in route_display_df.columns:
                    route_display_df[col] = pd.to_numeric(
                        route_display_df[col],
                        errors="coerce"
                    ).fillna(0)

            if selected_neighborhood == "Tümü":

                st.info(
                    "Rota karşılaştırma analizi mahalle bazlı değerlendirme için gösterilmektedir. "
                    "Lütfen Atatürk veya Kuruçeşme mahallesini seçiniz."
                )

            else:

                st.markdown("### 📊 Rota Karşılaştırma Analizi")

                route_summary_chart = (
                    route_display_df
                    .groupby(["Araç", "Rota No"])
                    .agg({
                        "Toplanacak Miktar (L)": "sum",
                        "Toplama Mesafesi (m)": "sum",
                        "Geçiş Mesafesi (m)": "sum"
                    })
                    .reset_index()
                )

                route_summary_chart["Rota"] = (
                    route_summary_chart["Araç"].astype(str)
                    + " - Rota "
                    + route_summary_chart["Rota No"].astype(str)
                )

                route_summary_chart["Toplam Mesafe (m)"] = (
                    route_summary_chart["Toplama Mesafesi (m)"]
                    + route_summary_chart["Geçiş Mesafesi (m)"]
                )

                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    st.markdown("**Rota Bazlı Toplanacak Miktar (L)**")
                    st.bar_chart(
                        route_summary_chart.set_index("Rota")["Toplanacak Miktar (L)"],
                        use_container_width=True
                    )

                with col_r2:
                    st.markdown("**Rota Bazlı Toplam Mesafe (m)**")
                    st.bar_chart(
                        route_summary_chart.set_index("Rota")["Toplam Mesafe (m)"],
                        use_container_width=True
                    )

                if "Yol Adı" in route_display_df.columns:

                    st.markdown("### 🏆 En Yoğun Sokaklar")

                    top_streets_df = (
                        route_display_df
                        .groupby("Yol Adı")["Toplanacak Miktar (L)"]
                        .sum()
                        .sort_values(ascending=False)
                        .head(10)
                    )

                    st.bar_chart(
                        top_streets_df,
                        use_container_width=True
                    )

            st.markdown("### 📋 Rota Detay Tablosu")

            st.dataframe(
                route_display_df,
                use_container_width=True
            )

        else:
            st.warning("Seçili filtrelere uygun rota detayı bulunamadı.")

    else:
        st.warning("final_route_details.csv bulunamadı.")