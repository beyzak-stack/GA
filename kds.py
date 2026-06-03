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

    elif selected_neighborhood == "Atatürk + Adatepe + Çamlıkule":
        filtered = [
            f for f in filtered
            if "ataturk" in normalize_text(f)
            or "adatepe" in normalize_text(f)
            or "camlikule" in normalize_text(f)
            or "belediye" in normalize_text(f)
        ]

    elif selected_neighborhood == "Kuruçeşme":
        filtered = [
            f for f in filtered
            if "kurucesme" in normalize_text(f)
        ]

    # Araç filtresi
    if selected_vehicle != "Tümü":

        if selected_operation_plan == "Mevcut Belediye Operasyonu":
            # Belediye KML dosyaları genelde BELEDIYE_..._AVG_... şeklinde başlar.
            # Bu nedenle sadece startswith("AVG") kontrolü yapılırsa dosyalar elenir.
            filtered = [
                f for f in filtered
                if selected_vehicle.upper() in f.upper()
                or "BELEDIYE" in f.upper()
            ]
        else:
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


def calculate_municipality_total_distance_km(details_df, summary_df=None, fallback_km=0):
    """
    Belediye mevcut operasyonu için toplam mesafeyi hesaplar.
    Öncelik: municipality_route_details.csv içindeki travel_distance + service_distance.
    Eğer detay dosyası yoksa, uygun özet kolonlarından okumaya çalışır.
    """

    # 1) En doğru kaynak: detay dosyası
    if details_df is not None and not details_df.empty:
        detail_df = details_df.copy()

        if "vehicle_name" in detail_df.columns:
            detail_df = detail_df[
                detail_df["vehicle_name"].astype(str).str.upper() == "AVG"
            ].copy()

        has_travel = "travel_distance" in detail_df.columns
        has_service = "service_distance" in detail_df.columns

        if has_travel or has_service:
            travel_m = (
                pd.to_numeric(detail_df.get("travel_distance", 0), errors="coerce")
                .fillna(0)
                .sum()
            )
            service_m = (
                pd.to_numeric(detail_df.get("service_distance", 0), errors="coerce")
                .fillna(0)
                .sum()
            )
            return round((travel_m + service_m) / 1000, 2), round(travel_m / 1000, 2), round(service_m / 1000, 2), "details"

    # 2) Alternatif kaynak: belediye rota özet dosyası
    if summary_df is not None and not summary_df.empty:
        summary = summary_df.copy()

        if "vehicle_name" in summary.columns:
            summary = summary[
                summary["vehicle_name"].astype(str).str.upper() == "AVG"
            ].copy()

        possible_total_cols = [
            "total_cost",
            "route_total_distance",
            "total_distance",
            "Toplam Mesafe (km)",
            "Toplam Mesafe",
            "toplam_mesafe",
        ]

        for col in possible_total_cols:
            if col in summary.columns:
                value = pd.to_numeric(summary[col], errors="coerce").fillna(0).sum()

                # Büyük değerler metre kabul edilir, küçük değerler km kabul edilir.
                if value > 1000:
                    value = value / 1000

                return round(value, 2), 0, 0, "summary"

    # 3) Son çare: mahalle bazlı servis mesafesi
    return round(float(fallback_km), 2), 0, round(float(fallback_km), 2), "fallback"

def filter_municipality_avg_region_df(input_df):
    """
    Belediye mevcut operasyonunda sadece Atatürk + Adatepe + Çamlıkule
    AVG rotalarını alır. START / RETURN / END satırlarını silmez.
    Böylece toplam mesafe doğru hesaplanır.
    """

    if input_df is None or input_df.empty:
        return pd.DataFrame()

    filtered_df = input_df.copy()

    if "vehicle_name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["vehicle_name"].astype(str).str.upper() == "AVG"
        ].copy()

    # En önemli kısım:
    # Önce route_label ile Atatürk seferlerini seçiyoruz.
    # Böylece START, RETURN, END satırları da korunuyor.
    if "route_label" in filtered_df.columns:
        label_norm = (
            filtered_df["route_label"]
            .astype(str)
            .apply(normalize_text)
        )

        filtered_df = filtered_df[
            label_norm.str.contains("ataturk", na=False)
            & ~label_norm.str.contains("kurucesme", na=False)
        ].copy()

    else:
        allowed_mahalleler = ["ataturk", "adatepe", "camlikule"]

        if "mahalle" in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df["mahalle"]
                .astype(str)
                .apply(normalize_text)
                .isin(allowed_mahalleler)
            ].copy()

    if "route_no" not in filtered_df.columns:
        if "route_label" in filtered_df.columns:
            filtered_df["route_no"] = (
                filtered_df["route_label"]
                .astype(str)
                .str.extract(r"(?:Rota|Sefer)\s*(\d+)")[0]
            )
        else:
            filtered_df["route_no"] = 1

    filtered_df["route_no"] = pd.to_numeric(
        filtered_df["route_no"],
        errors="coerce"
    ).fillna(1).astype(int)

    if "mahalle" not in filtered_df.columns:
        filtered_df["mahalle"] = "Atatürk + Adatepe + Çamlıkule"

    if "yol_adi" not in filtered_df.columns:
        filtered_df["yol_adi"] = "Yol adı bilgisi yok"
    else:
        filtered_df["yol_adi"] = (
            filtered_df["yol_adi"]
            .fillna("Yol adı bilgisi yok")
            .astype(str)
            .replace({"": "Yol adı bilgisi yok", "nan": "Yol adı bilgisi yok"})
        )

    return filtered_df
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
municipality_neighborhood_info_df = load_csv(
    "municipality_neighborhood_info.csv"
)

# =====================================================
# SABİT SOL KONTROL PANELİ
# =====================================================

left_panel, main_panel = st.columns([0.9, 5.1])

with left_panel:

    st.markdown("## Kontrol Paneli")

    selected_operation_plan = st.selectbox(
        "Operasyon Planı",
        [
            "Optimum Toplama Planı",
            "Mevcut Belediye Operasyonu",
            "Alternatif Operasyonlar"
        ]
    )

    selected_alternative_plan = None

    if selected_operation_plan == "Alternatif Operasyonlar":
        selected_alternative_plan = st.selectbox(
            "Alternatif Plan",
            [
                "Yoğun Trafik Durumu",
                "Tek AZU Operasyonu"
            ]
        )

    # -----------------------------
    # Mahalle seçenekleri
    # -----------------------------
    if selected_operation_plan == "Mevcut Belediye Operasyonu":
        neighborhood_options = [
            "Tümü",
            "Atatürk + Adatepe + Çamlıkule",
            "Kuruçeşme"
        ]
    else:
        neighborhood_options = [
            "Tümü",
            "Atatürk",
            "Kuruçeşme"
        ]

    selected_neighborhood = st.selectbox(
        "Mahalle",
        neighborhood_options
    )

    # -----------------------------
    # Araç seçenekleri
    # -----------------------------
    if selected_operation_plan == "Mevcut Belediye Operasyonu":

        if selected_neighborhood == "Atatürk + Adatepe + Çamlıkule":
            vehicle_options = ["Tümü", "AVG", "AZU"]

        elif selected_neighborhood == "Kuruçeşme":
            vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

        else:
            vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

    else:

        if selected_neighborhood == "Atatürk":
            vehicle_options = ["Tümü", "AVG", "AZU"]

        elif selected_neighborhood == "Kuruçeşme":
            vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

        else:
            vehicle_options = ["Tümü", "AVG", "AYT", "AZU"]

    selected_vehicle = st.selectbox(
        "Araç",
        vehicle_options
    )

    st.divider()

    show_containers = st.checkbox(
        "Konteynerleri Göster",
        value=False
    )

    show_routes = st.checkbox(
        "Rotaları Göster",
        value=True
    )

    st.divider()

    st.markdown("### Rota Katmanları")

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

    # Belediye mevcut operasyonunda ilgili KML'ler otomatik seçili gelsin.
    if selected_operation_plan == "Mevcut Belediye Operasyonu":
        default_kml_files = filtered_kml_files
    else:
        default_kml_files = []

    selected_kml_files = st.multiselect(
        "Rota Seçiniz",
        filtered_kml_files,
        default=default_kml_files
    )
# =====================================================
# BAŞLIK
# =====================================================
with main_panel:

    st.title("Buca Atık Toplama Karar Destek Sistemi")
    st.caption("Operasyon planı, mahalle ve araç bazlı rota görselleştirme ekranı")

    # =====================================================
    # HARİTA VERİLERİ
    # =====================================================

    container_markers = []

    if show_containers:

        if selected_neighborhood in ["Atatürk", "Atatürk + Adatepe + Çamlıkule"]:

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
    if selected_neighborhood in ["Atatürk", "Atatürk + Adatepe + Çamlıkule"]:
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
    
    if not (
    selected_operation_plan == "Mevcut Belediye Operasyonu"
    and selected_neighborhood == "Atatürk + Adatepe + Çamlıkule"
    and selected_vehicle == "AVG"
    ):
     st.subheader("📍 Seçilen Mahalle Bilgileri")

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

    .kpi-sub {
        font-size: 11px;
        color: #A1A1AA;
        margin-top: 6px;
        line-height: 1.5;
    }

    .kpi-icon {
        font-size: 14px;
        margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

    if (
        selected_operation_plan == "Mevcut Belediye Operasyonu"
        and selected_neighborhood == "Atatürk + Adatepe + Çamlıkule"
        and selected_vehicle == "AVG"
    ):
        st.subheader("📍 Seçilen Operasyon Bölgesi Bilgileri")

        if municipality_neighborhood_info_df.empty:
            st.info(
                "Belediye mahalle bazlı operasyon verisi bulunamadı. "
                "GA kodunu çalıştırıp kds_outputs/municipality_neighborhood_info.csv dosyasını oluşturmalısın."
            )
        else:
            belediye_bolge_df = municipality_neighborhood_info_df.copy()

            # Belediye operasyon bölgesi için konteyner bilgileri
            belediye_container_markers = container_csv_to_markers(
                CONTAINER_FILES["Atatürk"],
                allowed_mahalleler=[
                    "ataturk",
                    "adatepe",
                    "camlikule"
                ]
            )

            mahalle_gosterim_map = {
                "ataturk": "Atatürk",
                "adatepe": "Adatepe",
                "camlikule": "Çamlıkule"
            }

            container_rows = []

            for marker in belediye_container_markers:
                mahalle_key = normalize_text(marker.get("mahalle", ""))

                try:
                    adet = int(float(marker.get("adet", 1)))
                except:
                    adet = 1

                container_rows.append({
                    "mahalle": mahalle_key,
                    "mahalle_gosterim": mahalle_gosterim_map.get(mahalle_key, marker.get("mahalle", "-")),
                    "adet": adet,
                    "tip": marker.get("tip", "1")
                })

            container_summary_df = pd.DataFrame(container_rows)

            if container_summary_df.empty:
                toplam_normal_konteyner = 0
                toplam_konteyner_noktasi = 0
                normal_detay = "Konteyner verisi bulunamadı"
                nokta_detay = "Konteyner verisi bulunamadı"
            else:
                normal_container_df = container_summary_df[
                    container_summary_df["tip"].astype(str) == "1"
                ].copy()

                toplam_normal_konteyner = normal_container_df["adet"].sum()
                toplam_konteyner_noktasi = len(container_summary_df)

                normal_detay_list = []
                nokta_detay_list = []

                for mahalle_key, mahalle_name in mahalle_gosterim_map.items():
                    mahalle_normal = normal_container_df[
                        normal_container_df["mahalle"] == mahalle_key
                    ]["adet"].sum()

                    mahalle_nokta = container_summary_df[
                        container_summary_df["mahalle"] == mahalle_key
                    ].shape[0]

                    normal_detay_list.append(
                        f"{mahalle_name}: {format_number(mahalle_normal)}"
                    )
                    nokta_detay_list.append(
                        f"{mahalle_name}: {format_number(mahalle_nokta)}"
                    )

                normal_detay = "<br>".join(normal_detay_list)
                nokta_detay = "<br>".join(nokta_detay_list)

            toplam_sokak = pd.to_numeric(
                belediye_bolge_df.get("toplama_yapilacak_sokak_sayisi", 0),
                errors="coerce"
            ).fillna(0).sum()

            toplam_atik = pd.to_numeric(
                belediye_bolge_df.get("gunluk_toplama_miktari_litre", 0),
                errors="coerce"
            ).fillna(0).sum()

            toplam_servis_mesafesi = pd.to_numeric(
                belediye_bolge_df.get("servis_mesafesi_km", 0),
                errors="coerce"
            ).fillna(0).sum()

            sefer_sayisi = pd.to_numeric(
                belediye_bolge_df.get("sefer_sayisi", 0),
                errors="coerce"
            ).fillna(0).max()

            def mahalle_detay_satirlari(deger_kolonu, suffix=""):
                satirlar = []
                if "mahalle_gosterim" not in belediye_bolge_df.columns:
                    return ""

                for _, row in belediye_bolge_df.iterrows():
                    mahalle_adi = row.get("mahalle_gosterim", "-")
                    deger = row.get(deger_kolonu, 0)
                    satirlar.append(
                        f"{mahalle_adi}: {format_number(deger, suffix)}"
                    )

                return "<br>".join(satirlar)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-icon">🗑️</div>
                        <div class="kpi-title">Normal Konteyner Adedi</div>
                        <div class="kpi-value">{format_number(toplam_normal_konteyner)}</div>
                        <div class="kpi-sub">{normal_detay}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-icon">📍</div>
                        <div class="kpi-title">Konteyner Noktası Sayısı</div>
                        <div class="kpi-value">{format_number(toplam_konteyner_noktasi)}</div>
                        <div class="kpi-sub">{nokta_detay}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col3:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                        <div class="kpi-icon">🛣️</div>
                        <div class="kpi-title">Toplama Yapılacak Sokak Sayısı</div>
                        <div class="kpi-value">{format_number(toplam_sokak)}</div>
                        <div class="kpi-sub">{mahalle_detay_satirlari("toplama_yapilacak_sokak_sayisi")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    elif selected_neighborhood == "Tümü":
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

        tab1, tab2, tab4 = st.tabs(
            [
                "Operasyon Özeti",
                "Araç / Rota Performansı",
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

        is_municipality_avg_operation = (
            selected_operation_plan == "Mevcut Belediye Operasyonu"
            and selected_neighborhood == "Atatürk + Adatepe + Çamlıkule"
            and selected_vehicle == "AVG"
        )

        if is_municipality_avg_operation:

            if municipality_neighborhood_info_df.empty:

                st.warning(
                    "municipality_neighborhood_info.csv bulunamadı veya seçili filtreye uygun kayıt yok."
                )

            else:

                belediye_bolge_df_tab = municipality_neighborhood_info_df.copy()

                total_waste_tab1 = pd.to_numeric(
                    belediye_bolge_df_tab.get("gunluk_toplama_miktari_litre", 0),
                    errors="coerce"
                ).fillna(0).sum()

                fallback_service_km = pd.to_numeric(
                    belediye_bolge_df_tab.get("servis_mesafesi_km", 0),
                    errors="coerce"
                ).fillna(0).sum()

                municipality_details_for_region_df = filter_municipality_avg_region_df(
                    municipality_route_details_df
                )

                (
                    total_distance_tab1,
                    total_travel_distance_tab1,
                    total_service_distance_tab1,
                    municipality_distance_source
                ) = calculate_municipality_total_distance_km(
                    details_df=municipality_details_for_region_df,
                    summary_df=municipality_route_summary_df,
                    fallback_km=fallback_service_km
                )

                if municipality_distance_source == "fallback":
                    st.warning(
                        "Toplam mesafe için municipality_route_details.csv bulunamadı/okunamadı. "
                        "Şimdilik yalnızca servis mesafesi gösteriliyor. GA kodunu tekrar çalıştırıp "
                        "kds_outputs/municipality_route_details.csv dosyasını oluşturmalısın."
                    )

                route_count_tab1 = pd.to_numeric(
                    belediye_bolge_df_tab.get("sefer_sayisi", 0),
                    errors="coerce"
                ).fillna(0).max()

                vehicle_count_tab1 = 1
                best_vehicle = "AVG"
                best_vehicle_waste = total_waste_tab1

                st.markdown("### 📊 Operasyon Değerlendirmesi")

                c1, c2, c3, c4 = st.columns(4)

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
                        "📍 Tamamlanan Sefer",
                        f"{route_count_tab1:,.0f}"
                    )

                belediye_ozet_df = pd.DataFrame([
                    {
                        "Operasyon Planı": "Mevcut Belediye Operasyonu",
                        "Operasyon Bölgesi": "Atatürk + Adatepe + Çamlıkule",
                        "Araç": "AVG",
                        "Toplanan Atık (L)": int(total_waste_tab1),
                        "Toplam Mesafe (km)": round(total_distance_tab1, 2),
                        "Tamamlanan Sefer Sayısı": int(route_count_tab1),
                    }
                ])

                st.markdown("### 📋 Operasyon Özeti Tablosu")

                st.dataframe(
                    belediye_ozet_df,
                    use_container_width=True
                )

        elif not operation_filtered_df.empty:

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

        is_municipality_avg_operation = (
            selected_operation_plan == "Mevcut Belediye Operasyonu"
            and selected_neighborhood == "Atatürk + Adatepe + Çamlıkule"
            and selected_vehicle == "AVG"
        )

        if is_municipality_avg_operation:

            st.write("Belediye mevcut operasyonuna ait rota bazlı performans")

            if municipality_route_details_df.empty:

                st.warning(
                    "municipality_route_details.csv bulunamadı. "
                    "GA kodunu çalıştırıp kds_outputs/municipality_route_details.csv dosyasını oluşturmalısın."
                )

            else:

                belediye_perf_df = filter_municipality_avg_region_df(
                    municipality_route_details_df
                )

                if belediye_perf_df.empty:
                    st.warning(
                        "Seçili belediye operasyon bölgesi için rota performans kaydı bulunamadı. "
                        "municipality_route_details.csv içindeki mahalle/route_label alanlarını kontrol etmelisin."
                    )
                    st.stop()

                belediye_perf_df["sefer_no"] = belediye_perf_df["route_no"]

                belediye_perf_df["sefer_no"] = pd.to_numeric(
                    belediye_perf_df["sefer_no"],
                    errors="coerce"
                ).fillna(1).astype(int)

                numeric_cols = [
                    "demand",
                    "travel_distance",
                    "service_distance"
                ]

                for col in numeric_cols:
                    if col in belediye_perf_df.columns:
                        belediye_perf_df[col] = pd.to_numeric(
                            belediye_perf_df[col],
                            errors="coerce"
                        ).fillna(0)
                    else:
                        belediye_perf_df[col] = 0

                if "vehicle_name" not in belediye_perf_df.columns:
                    belediye_perf_df["vehicle_name"] = "AVG"

                belediye_sefer_df = (
                    belediye_perf_df
                    .groupby(["vehicle_name", "sefer_no"], dropna=False)
                    .agg(
                        toplanan_atik_litre=("demand", "sum"),
                        servis_mesafesi_metre=("service_distance", "sum"),
                        travel_mesafesi_metre=("travel_distance", "sum")
                    )
                    .reset_index()
                )

                belediye_sefer_df["toplam_mesafe_metre"] = (
                    belediye_sefer_df["servis_mesafesi_metre"]
                    + belediye_sefer_df["travel_mesafesi_metre"]
                )

                belediye_sefer_df["toplam_mesafe_km"] = (
                    belediye_sefer_df["toplam_mesafe_metre"] / 1000
                ).round(2)

                avg_capacity = 73500

                belediye_sefer_df["arac_kapasitesi_litre"] = avg_capacity

                belediye_sefer_df["kalan_kapasite_litre"] = (
                    belediye_sefer_df["arac_kapasitesi_litre"]
                    - belediye_sefer_df["toplanan_atik_litre"]
                )

                belediye_sefer_df["arac_doluluk_orani"] = (
                    belediye_sefer_df["toplanan_atik_litre"]
                    / belediye_sefer_df["arac_kapasitesi_litre"]
                    * 100
                ).round(2)

                belediye_sefer_df["verimlilik_l_km"] = (
                    belediye_sefer_df["toplanan_atik_litre"]
                    / belediye_sefer_df["toplam_mesafe_km"].replace(0, pd.NA)
                ).fillna(0).round(2)

                st.markdown("### 📊 Belediye Rota Performans Analizi")

                chart_df = belediye_sefer_df.copy()
                chart_df["Rota Etiketi"] = (
                    chart_df["vehicle_name"].astype(str)
                    + " - Rota "
                    + chart_df["sefer_no"].astype(int).astype(str)
                )

                col_g1, col_g2, col_g3 = st.columns(3)

                with col_g1:
                    st.markdown("**Rota Bazlı Toplanan Atık (L)**")
                    st.bar_chart(
                        chart_df.set_index("Rota Etiketi")["toplanan_atik_litre"],
                        use_container_width=True
                    )

                with col_g2:
                    st.markdown("**Toplama / Geçiş Mesafesi (m)**")
                    mesafe_chart_df = chart_df.rename(columns={
                        "servis_mesafesi_metre": "Toplama (m)",
                        "travel_mesafesi_metre": "Geçiş (m)"
                    })
                    st.bar_chart(
                        mesafe_chart_df.set_index("Rota Etiketi")[["Toplama (m)", "Geçiş (m)"]],
                        use_container_width=True
                    )

                with col_g3:
                    st.markdown("**Araç Doluluk Oranı (%)**")
                    st.bar_chart(
                        chart_df.set_index("Rota Etiketi")["arac_doluluk_orani"],
                        use_container_width=True
                    )

                st.markdown("### 📋 Belediye Araç / Rota Performans Tablosu")

                belediye_display_df = belediye_sefer_df.rename(columns={
                    "vehicle_name": "Araç",
                    "sefer_no": "Rota No",
                    "toplanan_atik_litre": "Toplanan Atık (L)",
                    "arac_kapasitesi_litre": "Araç Kapasitesi (L)",
                    "kalan_kapasite_litre": "Kalan Kapasite (L)",
                    "arac_doluluk_orani": "Araç Doluluk Oranı (%)",
                    "servis_mesafesi_metre": "Toplama Yapılan Mesafe (m)",
                    "travel_mesafesi_metre": "Geçiş Mesafesi (m)",
                    "toplam_mesafe_metre": "Toplam Mesafe (m)",
                    "toplam_mesafe_km": "Toplam Mesafe (km)"
                })
                
                belediye_display_df["Kapasite Uygun"] = (
                belediye_display_df["Kalan Kapasite (L)"] >= 0)

                display_columns = [
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

                belediye_display_df = belediye_display_df[
                    [col for col in display_columns if col in belediye_display_df.columns]
                ]

                st.dataframe(
                    belediye_display_df,
                    use_container_width=True
                )

        else:

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

    with tab4:

        st.write("Seçilen filtrelere göre oluşturulan toplama rotası adımları")

        is_municipality_avg_operation = (
            selected_operation_plan == "Mevcut Belediye Operasyonu"
            and selected_neighborhood == "Atatürk + Adatepe + Çamlıkule"
            and selected_vehicle == "AVG"
        )

        if is_municipality_avg_operation:
            route_df = municipality_route_details_df.copy()
        else:
            route_df = final_route_details_df.copy()

        if not route_df.empty:

            if is_municipality_avg_operation:

                # Sadece belediye mevcut operasyonundaki Atatürk + Adatepe + Çamlıkule AVG seferlerini al.
                route_df = filter_municipality_avg_region_df(route_df)

            else:

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
            if selected_operation_plan == "Mevcut Belediye Operasyonu":
                st.warning(
                    "municipality_route_details.csv bulunamadı. GA kodunu çalıştırıp belediye rota detaylarını oluşturmalısın."
                )
            else:
                st.warning("final_route_details.csv bulunamadı.")
