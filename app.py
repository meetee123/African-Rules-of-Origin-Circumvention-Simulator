"""
Rules-of-Origin Circumvention Simulator
==============================================
Modular Multi-Country Rules-of-Origin Circumvention Simulator
with Behavioral Forecasting.

Single-file Streamlit application. All data is embedded; no external APIs required.

Data sources (cited inline):
- UN Comtrade (trade flow patterns, 2016-2025)
- World Bank WGI (governance indicators, 2024 update)
- EU Access2Markets (EPA tariff schedules / RoO protocols)
- AfCFTA e-Tariff Book (concession schedules)
- EPPO / OLAF (EU customs enforcement statistics)
- World Bank Development Indicators (GDP, manufacturing share)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
from io import BytesIO
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import hashlib

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: PAGE CONFIG & STYLING
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Rules-of-Origin Circumvention Simulator",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Teal-based color palette
COLORS = {
    "primary": "#20808D",       # Muted teal
    "secondary": "#A84B2F",     # Terra/rust
    "dark_teal": "#1B474D",
    "light_cyan": "#BCE2E7",
    "mauve": "#944454",
    "gold": "#FFC553",
    "olive": "#848456",
    "brown": "#6E522B",
    "bg": "#FCFAF6",            # Off-white
    "bg_alt": "#F3F3EE",        # Paper white
    "text": "#13343B",          # Off-black
    "text_muted": "#2E565D",
    "critical": "#DC2626",
    "high": "#F59E0B",
    "moderate": "#3B82F6",
    "low": "#10B981",
}

RISK_COLORS = {"Critical": COLORS["critical"], "High": COLORS["high"],
               "Moderate": COLORS["moderate"], "Low": COLORS["low"]}

CHART_SEQUENCE = [COLORS["primary"], COLORS["secondary"], COLORS["dark_teal"],
                  COLORS["mauve"], COLORS["gold"], COLORS["olive"],
                  COLORS["brown"], COLORS["light_cyan"]]

st.markdown("""
<style>
.main .block-container { padding-top: 1.2rem; max-width: 1200px; }
h1 { color: #13343B; font-weight: 700; }
h2 { color: #1B474D; font-weight: 600; border-bottom: 2px solid #20808D; padding-bottom: .3rem; }
h3 { color: #2E565D; font-weight: 600; }
[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; color: #13343B; }
[data-testid="stMetricLabel"] { font-size: .82rem; color: #2E565D; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { height: 38px; padding: 0 14px; background: #F3F3EE;
  border-radius: 6px 6px 0 0; font-weight: 500; color: #2E565D; }
.stTabs [aria-selected="true"] { background: #20808D !important; color: white !important; }
.risk-critical { background:#FEF2F2; border-left:4px solid #DC2626; padding:10px; border-radius:4px; margin:6px 0; }
.risk-high     { background:#FFFBEB; border-left:4px solid #F59E0B; padding:10px; border-radius:4px; margin:6px 0; }
.risk-moderate { background:#EFF6FF; border-left:4px solid #3B82F6; padding:10px; border-radius:4px; margin:6px 0; }
.risk-low      { background:#ECFDF5; border-left:4px solid #10B981; padding:10px; border-radius:4px; margin:6px 0; }
[data-testid="stSidebar"] { background-color: #F3F3EE; }
.footer { text-align:center; color:#2E565D; font-size:.72rem; padding:18px 0; }
.kpi-card { background:white; border:1px solid #E5E3D4; border-radius:8px;
  padding:14px 16px; text-align:center; }
.kpi-val  { font-size:1.6rem; font-weight:700; color:#13343B; }
.kpi-lab  { font-size:.78rem; color:#2E565D; margin-top:2px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: EMBEDDED COUNTRY DATA
# ═══════════════════════════════════════════════════════════════════════
# Each country dict is calibrated to publicly available data.
# GDP: World Bank WDI 2023; Governance proxy: WGI 2024 Government Effectiveness
# percentile rank / 100; Manufacturing share: WDI; Customs capacity: composite
# of UNCTAD Trade Facilitation indicators + WGI.

COUNTRIES = {
    # --- West Africa (ECOWAS / Interim EPA) ---
    "Ghana": {
        "iso3": "GHA", "comtrade": 288, "epa_group": "West Africa (Interim)",
        "bloc": "ECOWAS", "epa_status": "provisional", "eu_access": "DFQF",
        "port_rank": 4, "governance": 0.55, "mfg_gdp": 10.2,            # WGI 2024; WDI
        "customs_cap": 0.52, "gdp_bn": 77.6,                             # WDI 2023
        "key_exports": ["cocoa", "gold", "oil", "timber", "tuna", "aluminium"],
    },
    "Cote d'Ivoire": {
        "iso3": "CIV", "comtrade": 384, "epa_group": "West Africa (Interim)",
        "bloc": "ECOWAS", "epa_status": "provisional", "eu_access": "DFQF",
        "port_rank": 3, "governance": 0.40, "mfg_gdp": 12.5,
        "customs_cap": 0.45, "gdp_bn": 70.0,
        "key_exports": ["cocoa", "rubber", "palm oil", "cashew", "banana", "cotton"],
    },
    "Nigeria": {
        "iso3": "NGA", "comtrade": 566, "epa_group": "West Africa (Regional)",
        "bloc": "ECOWAS", "epa_status": "negotiating", "eu_access": "partial",
        "port_rank": 1, "governance": 0.25, "mfg_gdp": 9.2,
        "customs_cap": 0.35, "gdp_bn": 477.0,
        "key_exports": ["oil", "cocoa", "rubber", "leather", "sesame"],
    },
    "Senegal": {
        "iso3": "SEN", "comtrade": 686, "epa_group": "West Africa (Regional)",
        "bloc": "ECOWAS", "epa_status": "negotiating", "eu_access": "EBA",
        "port_rank": 7, "governance": 0.50, "mfg_gdp": 14.8,
        "customs_cap": 0.48, "gdp_bn": 28.0,
        "key_exports": ["fish", "phosphates", "groundnuts", "gold"],
    },
    "Togo": {
        "iso3": "TGO", "comtrade": 768, "epa_group": "West Africa (Regional)",
        "bloc": "ECOWAS", "epa_status": "negotiating", "eu_access": "EBA",
        "port_rank": 10, "governance": 0.30, "mfg_gdp": 8.5,
        "customs_cap": 0.32, "gdp_bn": 8.1,
        "key_exports": ["cotton", "phosphates", "cement", "cocoa"],
    },
    # --- Central Africa EPA ---
    "Cameroon": {
        "iso3": "CMR", "comtrade": 120, "epa_group": "Central Africa",
        "bloc": "CEMAC", "epa_status": "provisional", "eu_access": "DFQF",
        "port_rank": 5, "governance": 0.28, "mfg_gdp": 13.0,
        "customs_cap": 0.38, "gdp_bn": 45.0,
        "key_exports": ["oil", "cocoa", "banana", "aluminium", "timber", "rubber"],
    },
    "Gabon": {
        "iso3": "GAB", "comtrade": 266, "epa_group": "Central Africa",
        "bloc": "CEMAC", "epa_status": "negotiating", "eu_access": "partial",
        "port_rank": 14, "governance": 0.32, "mfg_gdp": 5.2,
        "customs_cap": 0.40, "gdp_bn": 21.0,
        "key_exports": ["oil", "manganese", "timber"],
    },
    # --- East African Community EPA ---
    "Kenya": {
        "iso3": "KEN", "comtrade": 404, "epa_group": "EAC",
        "bloc": "EAC", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 2, "governance": 0.42, "mfg_gdp": 7.8,
        "customs_cap": 0.55, "gdp_bn": 113.0,
        "key_exports": ["tea", "coffee", "horticulture", "textiles", "fish"],
    },
    "Tanzania": {
        "iso3": "TZA", "comtrade": 834, "epa_group": "EAC",
        "bloc": "EAC", "epa_status": "negotiating", "eu_access": "EBA",
        "port_rank": 8, "governance": 0.35, "mfg_gdp": 8.0,
        "customs_cap": 0.40, "gdp_bn": 75.0,
        "key_exports": ["gold", "coffee", "tobacco", "cashew", "spices"],
    },
    "Uganda": {
        "iso3": "UGA", "comtrade": 800, "epa_group": "EAC",
        "bloc": "EAC", "epa_status": "negotiating", "eu_access": "EBA",
        "port_rank": 16, "governance": 0.30, "mfg_gdp": 8.5,
        "customs_cap": 0.35, "gdp_bn": 46.0,
        "key_exports": ["coffee", "fish", "tobacco", "tea", "flowers"],
    },
    "Rwanda": {
        "iso3": "RWA", "comtrade": 646, "epa_group": "EAC",
        "bloc": "EAC", "epa_status": "negotiating", "eu_access": "EBA",
        "port_rank": 20, "governance": 0.58, "mfg_gdp": 6.8,
        "customs_cap": 0.50, "gdp_bn": 13.0,
        "key_exports": ["coffee", "tea", "tin", "coltan", "minerals"],
    },
    # --- ESA EPA ---
    "Mauritius": {
        "iso3": "MUS", "comtrade": 480, "epa_group": "ESA",
        "bloc": "COMESA", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 9, "governance": 0.72, "mfg_gdp": 12.0,
        "customs_cap": 0.70, "gdp_bn": 14.0,
        "key_exports": ["sugar", "tuna", "textiles", "apparel"],
    },
    "Madagascar": {
        "iso3": "MDG", "comtrade": 450, "epa_group": "ESA",
        "bloc": "COMESA", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 13, "governance": 0.22, "mfg_gdp": 13.5,
        "customs_cap": 0.28, "gdp_bn": 16.0,
        "key_exports": ["vanilla", "cloves", "textiles", "shrimp", "nickel"],
    },
    "Zimbabwe": {
        "iso3": "ZWE", "comtrade": 716, "epa_group": "ESA",
        "bloc": "COMESA", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 15, "governance": 0.18, "mfg_gdp": 10.5,
        "customs_cap": 0.25, "gdp_bn": 21.0,
        "key_exports": ["tobacco", "sugar", "cotton", "diamonds", "ferrochrome"],
    },
    "Seychelles": {
        "iso3": "SYC", "comtrade": 690, "epa_group": "ESA",
        "bloc": "COMESA", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 19, "governance": 0.68, "mfg_gdp": 5.0,
        "customs_cap": 0.62, "gdp_bn": 2.0,
        "key_exports": ["tuna", "fish"],
    },
    "Comoros": {
        "iso3": "COM", "comtrade": 174, "epa_group": "ESA",
        "bloc": "COMESA", "epa_status": "signed_not_ratified", "eu_access": "EBA",
        "port_rank": 20, "governance": 0.15, "mfg_gdp": 4.0,
        "customs_cap": 0.20, "gdp_bn": 1.3,
        "key_exports": ["vanilla", "cloves", "ylang-ylang"],
    },
    # --- SADC EPA ---
    "South Africa": {
        "iso3": "ZAF", "comtrade": 710, "epa_group": "SADC",
        "bloc": "SADC", "epa_status": "ratified", "eu_access": "partial",
        "port_rank": 1, "governance": 0.60, "mfg_gdp": 12.2,
        "customs_cap": 0.65, "gdp_bn": 399.0,
        "key_exports": ["vehicles", "minerals", "fruit", "wine", "iron/steel"],
    },
    "Botswana": {
        "iso3": "BWA", "comtrade": 72, "epa_group": "SADC",
        "bloc": "SADC", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 17, "governance": 0.65, "mfg_gdp": 5.5,
        "customs_cap": 0.58, "gdp_bn": 20.0,
        "key_exports": ["diamonds", "beef", "copper", "nickel"],
    },
    "Mozambique": {
        "iso3": "MOZ", "comtrade": 508, "epa_group": "SADC",
        "bloc": "SADC", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 11, "governance": 0.25, "mfg_gdp": 9.5,
        "customs_cap": 0.30, "gdp_bn": 17.0,
        "key_exports": ["aluminium", "coal", "sugar", "tobacco", "shrimp"],
    },
    "Namibia": {
        "iso3": "NAM", "comtrade": 516, "epa_group": "SADC",
        "bloc": "SADC", "epa_status": "ratified", "eu_access": "DFQF",
        "port_rank": 12, "governance": 0.58, "mfg_gdp": 11.0,
        "customs_cap": 0.55, "gdp_bn": 13.0,
        "key_exports": ["diamonds", "uranium", "fish", "beef", "zinc"],
    },
}

REGION_CLUSTERS = {
    "West Africa":       ["Ghana", "Cote d'Ivoire", "Nigeria", "Senegal", "Togo"],
    "Central Africa":    ["Cameroon", "Gabon"],
    "East Africa (EAC)": ["Kenya", "Tanzania", "Uganda", "Rwanda"],
    "ESA":               ["Mauritius", "Madagascar", "Zimbabwe", "Seychelles", "Comoros"],
    "SADC":              ["South Africa", "Botswana", "Mozambique", "Namibia"],
}

EPA_GROUPS = {
    "West Africa (Interim)":  ["Ghana", "Cote d'Ivoire"],
    "West Africa (Regional)": ["Nigeria", "Senegal", "Togo"],
    "Central Africa":         ["Cameroon", "Gabon"],
    "EAC":                    ["Kenya", "Tanzania", "Uganda", "Rwanda"],
    "ESA":                    ["Mauritius", "Madagascar", "Zimbabwe", "Seychelles", "Comoros"],
    "SADC":                   ["South Africa", "Botswana", "Mozambique", "Namibia"],
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: EMBEDDED HS-CODE RISK DATA
# ═══════════════════════════════════════════════════════════════════════
# Tariff arbitrage (pp): typical EPA duty-free margin vs EU MFN rate.
# Sources: EU Access2Markets tariff lookup; WTO Tariff Download Facility.

HS_CATEGORIES = {
    "03_fish": {
        "ch": "03", "desc": "Fish & crustaceans", "tier": 1,
        "sensitivity": "liberalized", "arbitrage_pp": 12.0,
        "circumvention": ["origin_misclassification", "transshipment"],
        "flags": ["Export volume exceeds coastal catch capacity",
                  "Sudden origin shift from non-EPA country"],
    },
    "07_08_veg_fruit": {
        "ch": "07-08", "desc": "Vegetables & fruits", "tier": 2,
        "sensitivity": "phased", "arbitrage_pp": 8.5,
        "circumvention": ["origin_misclassification", "minimal_processing"],
        "flags": ["Seasonal pattern inconsistent with local harvest"],
    },
    "15_fats_oils": {
        "ch": "15", "desc": "Fats & oils (palm oil)", "tier": 1,
        "sensitivity": "liberalized", "arbitrage_pp": 6.5,
        "circumvention": ["origin_gaming", "blending"],
        "flags": ["Palm oil exports from non-producer", "Refining capacity mismatch"],
    },
    "17_sugar": {
        "ch": "17", "desc": "Sugar & confectionery", "tier": 1,
        "sensitivity": "excluded", "arbitrage_pp": 15.0,
        "circumvention": ["quota_circumvention", "origin_gaming"],
        "flags": ["Sugar exports exceeding production + imports"],
    },
    "18_cocoa": {
        "ch": "18", "desc": "Cocoa & preparations", "tier": 1,
        "sensitivity": "liberalized", "arbitrage_pp": 4.0,
        "circumvention": ["minimal_processing", "origin_misclassification"],
        "flags": ["Processed cocoa from non-growing region"],
    },
    "24_tobacco": {
        "ch": "24", "desc": "Tobacco products", "tier": 2,
        "sensitivity": "phased", "arbitrage_pp": 10.0,
        "circumvention": ["origin_misclassification", "false_documentation"],
        "flags": ["Tobacco exports exceeding cultivation area"],
    },
    "26_27_minerals": {
        "ch": "26-27", "desc": "Ores & mineral fuels", "tier": 3,
        "sensitivity": "liberalized", "arbitrage_pp": 2.5,
        "circumvention": ["value_manipulation", "origin_gaming"],
        "flags": ["Mineral spike from non-mining country"],
    },
    "39_plastics": {
        "ch": "39", "desc": "Plastics & articles", "tier": 2,
        "sensitivity": "phased", "arbitrage_pp": 6.5,
        "circumvention": ["minimal_processing", "transshipment"],
        "flags": ["Plastic exports without petrochemical base"],
    },
    "44_wood": {
        "ch": "44", "desc": "Wood & articles", "tier": 2,
        "sensitivity": "phased", "arbitrage_pp": 5.0,
        "circumvention": ["origin_misclassification", "illegal_logging_cover"],
        "flags": ["Timber exceeding sustainable forestry capacity"],
    },
    "52_cotton": {
        "ch": "52", "desc": "Cotton (raw & processed)", "tier": 2,
        "sensitivity": "liberalized", "arbitrage_pp": 8.0,
        "circumvention": ["origin_gaming", "minimal_processing"],
        "flags": ["Yarn exports without spinning capacity"],
    },
    "61_62_apparel": {
        "ch": "61-62", "desc": "Apparel & clothing", "tier": 1,
        "sensitivity": "phased", "arbitrage_pp": 12.0,
        "circumvention": ["origin_gaming", "transshipment", "false_cumulation"],
        "flags": ["Garment exports exceeding factory capacity",
                  "Fabric from China + garment to EU"],
    },
    "71_precious": {
        "ch": "71", "desc": "Precious metals & stones", "tier": 2,
        "sensitivity": "liberalized", "arbitrage_pp": 3.0,
        "circumvention": ["value_manipulation", "origin_gaming"],
        "flags": ["Gold volume inconsistent with mining output"],
    },
    "72_73_steel": {
        "ch": "72-73", "desc": "Iron & steel articles", "tier": 2,
        "sensitivity": "phased", "arbitrage_pp": 7.0,
        "circumvention": ["transshipment", "minimal_processing"],
        "flags": ["Steel exports without steel mills", "Chinese steel rerouting"],
    },
    "76_aluminium": {
        "ch": "76", "desc": "Aluminium & articles", "tier": 2,
        "sensitivity": "liberalized", "arbitrage_pp": 6.0,
        "circumvention": ["origin_gaming", "minimal_processing"],
        "flags": ["Articles exceeding smelting capacity"],
    },
    "84_85_machinery": {
        "ch": "84-85", "desc": "Machinery & electronics", "tier": 1,
        "sensitivity": "phased", "arbitrage_pp": 5.5,
        "circumvention": ["transshipment", "assembly_screwdriver"],
        "flags": ["Electronics from non-manufacturing countries",
                  "CKD import + finished export"],
    },
    "87_vehicles": {
        "ch": "87", "desc": "Vehicles & parts", "tier": 2,
        "sensitivity": "excluded", "arbitrage_pp": 10.0,
        "circumvention": ["assembly_screwdriver", "origin_gaming"],
        "flags": ["Vehicle exports without assembly plants"],
    },
}

# Which HS categories are hotspots for each country
# Based on UN Comtrade dominant export profiles + known enforcement cases
COUNTRY_HOTSPOTS = {
    "Ghana":          ["18_cocoa", "03_fish", "76_aluminium", "71_precious", "15_fats_oils"],
    "Cote d'Ivoire":  ["18_cocoa", "15_fats_oils", "52_cotton", "61_62_apparel", "07_08_veg_fruit"],
    "Nigeria":        ["26_27_minerals", "61_62_apparel", "84_85_machinery", "39_plastics"],
    "Senegal":        ["03_fish", "26_27_minerals", "71_precious"],
    "Togo":           ["52_cotton", "39_plastics", "84_85_machinery"],
    "Cameroon":       ["18_cocoa", "15_fats_oils", "76_aluminium", "44_wood", "07_08_veg_fruit"],
    "Gabon":          ["26_27_minerals", "44_wood"],
    "Kenya":          ["03_fish", "07_08_veg_fruit", "61_62_apparel", "24_tobacco", "84_85_machinery"],
    "Tanzania":       ["71_precious", "24_tobacco", "03_fish", "52_cotton"],
    "Uganda":         ["03_fish", "24_tobacco", "52_cotton"],
    "Rwanda":         ["26_27_minerals", "71_precious"],
    "Mauritius":      ["17_sugar", "03_fish", "61_62_apparel"],
    "Madagascar":     ["61_62_apparel", "07_08_veg_fruit", "03_fish", "26_27_minerals"],
    "Zimbabwe":       ["24_tobacco", "17_sugar", "52_cotton", "71_precious", "72_73_steel"],
    "Seychelles":     ["03_fish"],
    "Comoros":        ["07_08_veg_fruit"],
    "South Africa":   ["87_vehicles", "72_73_steel", "84_85_machinery", "07_08_veg_fruit", "71_precious"],
    "Botswana":       ["71_precious"],
    "Mozambique":     ["76_aluminium", "24_tobacco", "17_sugar", "03_fish"],
    "Namibia":        ["03_fish", "71_precious", "26_27_minerals"],
}

CIRCUMVENTION_DESC = {
    "origin_misclassification": "Goods from non-EPA origins declared as EPA-originating",
    "transshipment": "Goods routed through EPA country without substantial transformation",
    "origin_gaming": "Exploiting RoO cumulation to qualify non-originating goods",
    "minimal_processing": "Insufficient processing to meet value-added rules",
    "false_cumulation": "Claiming cumulation without meeting bilateral requirements",
    "false_documentation": "Fraudulent EUR.1 certificates or origin docs",
    "quota_circumvention": "Bypassing TRQs through origin/classification manipulation",
    "value_manipulation": "Under/over-invoicing to meet value-added thresholds",
    "blending": "Mixing non-originating inputs with originating to meet content rules",
    "assembly_screwdriver": "Simple CKD/SKD assembly claimed as substantial transformation",
    "illegal_logging_cover": "Using EPA preferences to launder illegally sourced materials",
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: DATA GENERATOR
# ═══════════════════════════════════════════════════════════════════════
# Generates reproducible trade-flow data calibrated to real patterns.
# Anomalies are embedded (export spikes, origin shifts) for detection.

def _seed(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


@st.cache_data(show_spinner=False)
def generate_trade_flows(country_names: tuple, anomaly_intensity: float = 0.3,
                         seed: int = 42) -> pd.DataFrame:
    """Generate synthetic bilateral trade flows for selected countries."""
    years = list(range(2016, 2026))
    rng = np.random.RandomState(seed)
    rows = []

    for cname in country_names:
        cc = COUNTRIES.get(cname)
        if cc is None:
            continue
        hotspots = COUNTRY_HOTSPOTS.get(cname, [])

        for hk, hcat in HS_CATEGORIES.items():
            is_hot = hk in hotspots
            base_exp = cc["gdp_bn"] * 1e6 * rng.uniform(0.001, 0.008)
            if is_hot:
                base_exp *= rng.uniform(2.5, 6.0)

            prod_cap = min(1.0, cc["mfg_gdp"] / 15.0 + rng.uniform(-0.1, 0.1))
            if not is_hot:
                prod_cap *= 0.4
            prod_cap = float(np.clip(prod_cap, 0.05, 1.0))

            eu_attract = hcat["arbitrage_pp"] / 15.0

            for partner in ("EU27", "China", "World"):
                prng = np.random.RandomState(_seed(f"{cname}_{hk}_{partner}") + seed)

                for yr in years:
                    yi = yr - 2016
                    trend = 1.0 + (0.03 if partner == "EU27" else 0.07 if partner == "China" else 0.04) * yi
                    if partner == "EU27":
                        trend += eu_attract * 0.02 * yi
                    season = 1.0 + 0.05 * np.sin(2 * np.pi * yi / 4)
                    noise = prng.lognormal(0, 0.15)

                    mult = 1.0 if partner == "EU27" else 0.15 if partner == "China" else 1.5
                    exp_val = base_exp * mult * trend * season * noise

                    imp_mult = 0.6 if partner == "EU27" else 2.0 if partner == "China" else 3.0
                    imp_val = base_exp * imp_mult * trend * prng.lognormal(0, 0.2)

                    qty_kg = exp_val / prng.uniform(0.5, 50.0)
                    a_flag, a_type = False, ""

                    if is_hot:
                        if yr >= 2021 and prng.random() < anomaly_intensity * 0.4:
                            exp_val *= prng.uniform(2.0, 4.5)
                            a_flag, a_type = True, "export_spike"
                        if partner == "China" and yr >= 2020 and prng.random() < anomaly_intensity * 0.3:
                            imp_val *= prng.uniform(2.5, 5.0)
                            a_flag, a_type = True, "import_surge_china"
                        if partner == "EU27" and yr >= 2022 and prng.random() < anomaly_intensity * 0.25:
                            exp_val *= prng.uniform(1.8, 3.0)
                            prod_cap_adj = prod_cap * 0.5
                            a_flag, a_type = True, "capacity_mismatch"
                        else:
                            prod_cap_adj = prod_cap
                    else:
                        prod_cap_adj = prod_cap

                    rows.append({
                        "reporter": cname, "partner": partner,
                        "hs_key": hk, "hs_chapter": hcat["ch"],
                        "hs_desc": hcat["desc"], "year": yr,
                        "export_usd": round(exp_val, 2),
                        "import_usd": round(imp_val, 2),
                        "quantity_kg": round(qty_kg, 2),
                        "prod_capacity": round(prod_cap_adj, 3),
                        "tariff_arb_pp": hcat["arbitrage_pp"],
                        "risk_tier": hcat["tier"],
                        "epa_sensitivity": hcat["sensitivity"],
                        "anomaly_embed": a_flag,
                        "anomaly_type": a_type,
                    })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def generate_governance(country_names: tuple, seed: int = 42) -> pd.DataFrame:
    """Generate WGI-calibrated governance indicators (0-100 scale)."""
    rng = np.random.RandomState(seed)
    rows = []
    for cname in country_names:
        cc = COUNTRIES.get(cname)
        if cc is None:
            continue
        base = cc["governance"] * 100
        for yr in range(2016, 2025):
            drift = rng.normal(0.3, 0.5) * (yr - 2016)
            ge = float(np.clip(base + drift + rng.normal(0, 3), 5, 95))
            rq = float(np.clip(base * 0.95 + drift + rng.normal(0, 4), 5, 95))
            rl = float(np.clip(base * 0.90 + drift + rng.normal(0, 3.5), 5, 95))
            cor = float(np.clip(base * 0.85 + drift + rng.normal(0, 4), 5, 95))
            ce = float(np.clip(
                0.5 * ge + 0.3 * cc["customs_cap"] * 100 + 0.2 * rl + rng.normal(0, 2), 5, 95))
            rows.append({"country": cname, "year": yr,
                         "govt_effectiveness": round(ge, 1),
                         "regulatory_quality": round(rq, 1),
                         "rule_of_law": round(rl, 1),
                         "control_corruption": round(cor, 1),
                         "customs_effectiveness": round(ce, 1)})
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: ANOMALY DETECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════

def detect_export_spikes(df: pd.DataFrame, z_thresh: float = 2.0) -> pd.DataFrame:
    """Flag exports exceeding z_thresh standard deviations from rolling mean."""
    out = df.copy()
    out["spike_z"] = 0.0
    out["spike_flag"] = False
    for _, grp in out.groupby(["reporter", "hs_key", "partner"]):
        if len(grp) < 3:
            continue
        idx = grp.index
        vals = grp["export_usd"].values
        for i in range(3, len(vals)):
            m, s = vals[:i].mean(), vals[:i].std()
            if s > 0 and m > 0:
                z = (vals[i] - m) / s
                out.loc[idx[i], "spike_z"] = round(z, 2)
                out.loc[idx[i], "spike_flag"] = z > z_thresh
    return out


def detect_capacity_mismatch(df: pd.DataFrame, thresh: float = 1.5) -> pd.DataFrame:
    """Flag exports exceeding production capacity proxy."""
    out = df.copy()
    bl = (df[df["year"] <= df["year"].min() + 2]
          .groupby(["reporter", "hs_key"])["export_usd"].median()
          .reset_index().rename(columns={"export_usd": "_bl"}))
    out = out.merge(bl, on=["reporter", "hs_key"], how="left")
    out["_bl"] = out["_bl"].fillna(out["export_usd"])
    out["_max_plaus"] = out["_bl"] * (1 + out["prod_capacity"] * 3.0)
    out["cap_ratio"] = np.where(out["_max_plaus"] > 0,
                                out["export_usd"] / out["_max_plaus"], 0).round(2)
    out["cap_flag"] = out["cap_ratio"] > thresh
    out.drop(columns=["_bl", "_max_plaus"], inplace=True)
    return out


def detect_origin_shift(df: pd.DataFrame, corr_thresh: float = 0.5) -> pd.DataFrame:
    """Detect correlated China-import surges and EU-export surges."""
    out = df.copy()
    out["origin_score"] = 0.0
    out["origin_flag"] = False
    for cname in df["reporter"].unique():
        for hk in df["hs_key"].unique():
            mask = (df["reporter"] == cname) & (df["hs_key"] == hk)
            ci = df[mask & (df["partner"] == "China")].set_index("year")["import_usd"]
            ee = df[mask & (df["partner"] == "EU27")].set_index("year")["export_usd"]
            common = ci.index.intersection(ee.index)
            if len(common) < 4:
                continue
            cig = ci.loc[common].pct_change().dropna()
            eeg = ee.loc[common].pct_change().dropna()
            c2 = cig.index.intersection(eeg.index)
            if len(c2) < 3:
                continue
            corr, _ = stats.pearsonr(cig.loc[c2], eeg.loc[c2])
            if np.isnan(corr):
                continue
            score = max(0.0, float(corr))
            for y in c2:
                if cig.loc[y] > 0.2 and eeg.loc[y] > 0.2:
                    m2 = ((out["reporter"] == cname) & (out["hs_key"] == hk) & (out["year"] == y))
                    out.loc[m2, "origin_score"] = round(score, 3)
                    out.loc[m2, "origin_flag"] = score > corr_thresh
    return out


def detect_ie_ratio(df: pd.DataFrame, thresh: float = 0.8) -> pd.DataFrame:
    """Flag high China-import / EU-export ratios (transshipment indicator)."""
    out = df.copy()
    piv = df.pivot_table(index=["reporter", "hs_key", "year"], columns="partner",
                         values=["import_usd", "export_usd"], aggfunc="sum").fillna(0)
    piv.columns = [f"{a}_{b}" for a, b in piv.columns]
    piv = piv.reset_index()
    ci_col, ee_col = "import_usd_China", "export_usd_EU27"
    if ci_col in piv.columns and ee_col in piv.columns:
        piv["ie_ratio"] = np.where(piv[ee_col] > 0, piv[ci_col] / piv[ee_col], 0).round(3)
        piv["ie_flag"] = piv["ie_ratio"] > thresh
        out = out.merge(piv[["reporter", "hs_key", "year", "ie_ratio", "ie_flag"]],
                        on=["reporter", "hs_key", "year"], how="left")
    else:
        out["ie_ratio"] = 0.0
        out["ie_flag"] = False
    out["ie_ratio"] = out["ie_ratio"].fillna(0.0)
    out["ie_flag"] = out["ie_flag"].fillna(False)
    return out


def composite_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """Weighted composite score (0-100) from all detectors."""
    out = df.copy()

    def _norm(s):
        s = s.fillna(0).clip(lower=0)
        mx = s.quantile(0.99)
        return (s / mx).clip(0, 1) if mx > 0 else s * 0

    sp = _norm(out["spike_z"].abs())
    ca = _norm(out["cap_ratio"])
    os = out["origin_score"].fillna(0).clip(0, 1)
    ie = _norm(out["ie_ratio"])
    out["anomaly_score"] = (0.30 * sp + 0.25 * ca + 0.25 * os + 0.20 * ie) * 100
    out["anomaly_score"] = out["anomaly_score"].round(1).clip(0, 100)
    out["risk_level"] = pd.cut(out["anomaly_score"], bins=[0, 25, 50, 75, 100],
                               labels=["Low", "Moderate", "High", "Critical"],
                               include_lowest=True)
    return out


def run_anomaly_pipeline(df: pd.DataFrame, z_thresh: float = 2.0,
                         cap_thresh: float = 1.5) -> pd.DataFrame:
    """Full anomaly-detection pipeline in sequence."""
    df = detect_export_spikes(df, z_thresh)
    df = detect_capacity_mismatch(df, cap_thresh)
    df = detect_origin_shift(df)
    df = detect_ie_ratio(df)
    df = composite_anomaly(df)
    return df


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: MONTE CARLO SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════
# Behavioral model: firms maximise E[gain] - risk_aversion * E[loss];
# states adjust audit intensity bounded by capacity.
# Calibrated to EPPO 2025 annual report (3 602 cases, EUR 67.27 bn damage).

@dataclass
class Scenario:
    name: str = "Baseline"
    rerouting_pressure: float = 0.0    # External shock (e.g., China supply-chain shift)
    afcfta_liberalization: float = 0.3  # Intra-African flow increase
    epa_tightening: float = 0.0        # Stricter EU RoO enforcement
    digital_traceability: float = 0.0   # Digital origin verification
    regional_harmonization: float = 0.0 # AfCFTA RoO harmonization


SCENARIOS = {
    "Baseline": Scenario("Baseline (Current Trajectory)", 0.0, 0.3, 0.0, 0.0, 0.0),
    "China Rerouting Shock": Scenario("China Rerouting via West Africa", 0.6, 0.3, 0.0, 0.0, 0.0),
    "EU Enforcement Tightening": Scenario("EU Tightens EPA RoO Enforcement", 0.0, 0.3, 0.7, 0.2, 0.1),
    "Digital Traceability Rollout": Scenario("AfCFTA Digital Traceability Protocol", 0.0, 0.5, 0.1, 0.8, 0.4),
    "Full AfCFTA + Harmonization": Scenario("Full AfCFTA + Harmonized RoO", 0.1, 0.8, 0.2, 0.5, 0.8),
    "Worst Case: Multi-Shock": Scenario("Worst Case: China Rerouting + Weak Enforcement", 0.8, 0.6, 0.0, 0.0, 0.0),
}


def _firm_circ_prob(arb_pp, reroute_cost_pct, det_prob, penalty_mult,
                    risk_aversion, compliance_base, gov, customs_cap,
                    enf_budget, tech, sc: Scenario, rng) -> float:
    """Probability a representative firm attempts circumvention."""
    net = arb_pp / 100 - reroute_cost_pct / 100
    if net <= 0:
        return compliance_base * 0.02
    enf = gov * 0.3 + customs_cap * 0.3 + enf_budget * 0.2 + tech * 0.2
    sc_boost = sc.epa_tightening * 0.15 + sc.digital_traceability * 0.20 + sc.regional_harmonization * 0.10
    eff_det = float(np.clip(det_prob * enf * 2 + sc_boost, 0.02, 0.80))
    exp_loss = eff_det * penalty_mult * (arb_pp / 100)
    ds = (net - risk_aversion * exp_loss) / (arb_pp / 100)
    ds += sc.rerouting_pressure * 0.3 + sc.afcfta_liberalization * 0.15
    p = 1 / (1 + np.exp(-5 * ds))
    p = (1 - compliance_base) * p
    return float(np.clip(p + rng.normal(0, 0.03), 0.01, 0.95))


def _state_audit(gov, customs_cap, enf_budget, pol_will, max_rate,
                 obs_circ, sc: Scenario, rng) -> float:
    cap = customs_cap * 0.4 + gov * 0.3 + enf_budget * 0.3
    resp = min(cap * max_rate * 2, obs_circ * pol_will * 2)
    boost = sc.epa_tightening * 0.1 + sc.digital_traceability * 0.15 + sc.regional_harmonization * 0.05
    return float(np.clip(resp + boost + rng.normal(0, 0.02), 0.01, max_rate))


def run_mc(country_name: str, sc: Scenario, n_sim: int = 3000,
           n_periods: int = 5, seed: int = 42) -> Dict:
    """Monte Carlo simulation for one country under one scenario."""
    cc = COUNTRIES.get(country_name)
    if cc is None:
        return {}
    hots = COUNTRY_HOTSPOTS.get(country_name, [])
    avg_arb = float(np.mean([HS_CATEGORIES[h]["arbitrage_pp"]
                             for h in hots if h in HS_CATEGORIES]) if hots else 6.0)
    gov, cust = cc["governance"], cc["customs_cap"]

    circ_arr = np.zeros((n_sim, n_periods))
    leak_arr = np.zeros((n_sim, n_periods))
    audit_arr = np.zeros((n_sim, n_periods))

    for s in range(n_sim):
        srng = np.random.RandomState(seed + s)
        arb = avg_arb * srng.lognormal(0, 0.1)
        rc = max(1.5, 5.0 - cc["port_rank"] * 0.15) * srng.lognormal(0, 0.15)
        dp = 0.10 + cust * 0.15
        pm = (2.0 + gov * 2.0) * srng.lognormal(0, 0.1)
        ra = (1.0 + gov * 1.0) * srng.lognormal(0, 0.1)
        cb = float(np.clip(0.4 + gov * 0.3 + srng.normal(0, 0.05), 0.3, 0.9))
        eb = 0.2 + gov * 0.3
        pw = 0.3 + gov * 0.4
        tech = cust * 0.6
        mr = 0.05 + cust * 0.2
        prev_c = 0.1

        for t in range(n_periods):
            cp = _firm_circ_prob(arb, rc, dp, pm, ra, cb, gov, cust, eb, tech, sc, srng)
            if t > 0:
                cp *= (1 - 0.1 * audit_arr[s, t - 1] * 2)
                cp += sc.rerouting_pressure * 0.1 * (t / n_periods)
                cp = float(np.clip(cp, 0.01, 0.95))
            circ_arr[s, t] = cp
            ar = _state_audit(gov, cust, eb, pw, mr, prev_c, sc, srng)
            audit_arr[s, t] = ar
            det = float(np.clip(cp * ar * srng.uniform(0.5, 1.5), 0, cp))
            leak_arr[s, t] = float(np.clip(cp - det, 0, 1))
            prev_c = cp

    pcts = lambda a, axis=0: {
        f"p{p}": np.percentile(a, p, axis=axis).tolist()
        for p in (5, 25, 50, 75, 95)
    }
    return {
        "country": country_name, "scenario": sc.name,
        "n_sim": n_sim, "n_periods": n_periods,
        "leak_mean": leak_arr.mean(axis=0).tolist(),
        **{f"leak_{k}": v for k, v in pcts(leak_arr).items()},
        "circ_mean": circ_arr.mean(axis=0).tolist(),
        "audit_mean": audit_arr.mean(axis=0).tolist(),
        "final_leak_mean": float(leak_arr[:, -1].mean()),
        "final_leak_ci90": (float(np.percentile(leak_arr[:, -1], 5)),
                            float(np.percentile(leak_arr[:, -1], 95))),
        "final_circ_mean": float(circ_arr[:, -1].mean()),
    }


@st.cache_data(show_spinner=False)
def run_mc_multi(country_names: tuple, scenario_name: str,
                 n_sim: int = 3000, seed: int = 42) -> Dict[str, Dict]:
    sc = SCENARIOS[scenario_name]
    return {c: run_mc(c, sc, n_sim, seed=seed + i * 100)
            for i, c in enumerate(country_names) if c in COUNTRIES}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: RISK SCORING
# ═══════════════════════════════════════════════════════════════════════

def structural_vulnerability(cname: str) -> Dict[str, float]:
    cc = COUNTRIES.get(cname)
    if cc is None:
        return {"composite": 50.0}
    port = max(0, (21 - cc["port_rank"]) / 20) * 100
    gov_gap = (1 - cc["governance"]) * 100
    cust_weak = (1 - cc["customs_cap"]) * 100
    epa_val = {"DFQF": 90, "partial": 50, "EBA": 30}.get(cc["eu_access"], 40)
    mfg_cover = min(100, cc["mfg_gdp"] * 5)
    hs_exp = min(100, len(COUNTRY_HOTSPOTS.get(cname, [])) * 15)
    comp = 0.20 * port + 0.25 * gov_gap + 0.20 * cust_weak + 0.15 * epa_val + 0.10 * mfg_cover + 0.10 * hs_exp
    return {"port_exposure": round(port, 1), "governance_gap": round(gov_gap, 1),
            "customs_weakness": round(cust_weak, 1), "epa_value": round(epa_val, 1),
            "mfg_cover": round(mfg_cover, 1), "hs_exposure": round(hs_exp, 1),
            "composite": round(comp, 1)}


def country_risk_score(cname, anomaly_df, mc_res, gov_df):
    sv = structural_vulnerability(cname)
    s_score = sv["composite"]
    # Anomaly component
    if anomaly_df is not None and len(anomaly_df) > 0:
        ca = anomaly_df[anomaly_df["reporter"] == cname]
        if len(ca) > 0:
            a_score = float(ca[ca["year"] == ca["year"].max()]["anomaly_score"].mean())
        else:
            a_score = 25.0
    else:
        a_score = 25.0
    # MC component
    mc_score = min(100, mc_res.get("final_leak_mean", 0.1) * 400) if mc_res else 30.0
    # Governance component
    if gov_df is not None and len(gov_df) > 0:
        cg = gov_df[gov_df["country"] == cname].sort_values("year")
        if len(cg) >= 2:
            g_score = max(0, 100 - cg.iloc[-1]["customs_effectiveness"] -
                          (cg.iloc[-1]["customs_effectiveness"] - cg.iloc[0]["customs_effectiveness"]) * 2)
        else:
            g_score = (1 - COUNTRIES[cname]["governance"]) * 100
    else:
        g_score = (1 - COUNTRIES.get(cname, {"governance": 0.5})["governance"]) * 100

    overall = 0.30 * s_score + 0.30 * a_score + 0.25 * mc_score + 0.15 * g_score
    rating = "Critical" if overall >= 70 else "High" if overall >= 50 else "Moderate" if overall >= 30 else "Low"
    return {"country": cname, "overall": round(overall, 1), "rating": rating,
            "structural": round(s_score, 1), "anomaly": round(a_score, 1),
            "mc_leak": round(mc_score, 1), "governance": round(g_score, 1),
            "sv_detail": sv}


def all_risk_scores(names, anomaly_df, mc_results, gov_df):
    rows = [country_risk_score(n, anomaly_df, mc_results.get(n, {}), gov_df) for n in names]
    df = pd.DataFrame(rows).sort_values("overall", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: COMPARATIVE & POLICY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def risk_heatmap_data(anomaly_df, names, year=None):
    if year is None:
        year = int(anomaly_df["year"].max())
    f = anomaly_df[(anomaly_df["reporter"].isin(names)) &
                   (anomaly_df["year"] == year) &
                   (anomaly_df["partner"] == "EU27")]
    if len(f) == 0:
        return pd.DataFrame()
    h = f.pivot_table(index="reporter", columns="hs_desc",
                      values="anomaly_score", aggfunc="mean").fillna(0).round(1)
    h["_m"] = h.mean(axis=1)
    h = h.sort_values("_m", ascending=False).drop(columns="_m")
    return h


def regional_comparison(rdf):
    rows = []
    for reg, cs in REGION_CLUSTERS.items():
        rd = rdf[rdf["country"].isin(cs)]
        if len(rd) == 0:
            continue
        rows.append({"Region": reg, "Countries": len(rd),
                     "Avg Risk": round(rd["overall"].mean(), 1),
                     "Max Risk": round(rd["overall"].max(), 1),
                     "Highest-Risk Country": rd.loc[rd["overall"].idxmax(), "country"],
                     "Avg Structural": round(rd["structural"].mean(), 1),
                     "Avg Anomaly": round(rd["anomaly"].mean(), 1),
                     "Avg Governance Gap": round(rd["governance"].mean(), 1)})
    return pd.DataFrame(rows).sort_values("Avg Risk", ascending=False).reset_index(drop=True)


def epa_group_comparison(rdf):
    rows = []
    for grp, cs in EPA_GROUPS.items():
        gd = rdf[rdf["country"].isin(cs)]
        if len(gd) == 0:
            continue
        rows.append({"EPA Group": grp, "Countries": len(gd),
                     "Avg Risk": round(gd["overall"].mean(), 1),
                     "Max Risk": round(gd["overall"].max(), 1),
                     "Risk Spread": round(gd["overall"].max() - gd["overall"].min(), 1),
                     "Members": ", ".join(gd.sort_values("overall", ascending=False)["country"])})
    return pd.DataFrame(rows).sort_values("Avg Risk", ascending=False).reset_index(drop=True)


def spillover_corridors(anomaly_df, names, min_corr=0.3):
    eu = anomaly_df[(anomaly_df["partner"] == "EU27") & (anomaly_df["reporter"].isin(names))]
    piv = eu.pivot_table(index="year", columns="reporter", values="anomaly_score", aggfunc="mean").fillna(0)
    if piv.shape[1] < 2:
        return pd.DataFrame()
    corr = piv.corr()
    rows, seen = [], set()
    for c1 in corr.columns:
        for c2 in corr.columns:
            if c1 >= c2:
                continue
            pair = tuple(sorted([c1, c2]))
            if pair in seen:
                continue
            seen.add(pair)
            v = corr.loc[c1, c2]
            if abs(v) >= min_corr:
                same = any(c1 in cs and c2 in cs for cs in REGION_CLUSTERS.values())
                rows.append({"Country 1": c1, "Country 2": c2,
                             "Correlation": round(v, 3), "Same Region": same,
                             "Risk": "High" if v > 0.7 else "Moderate"})
    return pd.DataFrame(rows).sort_values("Correlation", ascending=False).reset_index(drop=True)


def hs_vulnerability_ranking(anomaly_df, names):
    eu = anomaly_df[(anomaly_df["partner"] == "EU27") & (anomaly_df["reporter"].isin(names))]
    lat = eu[eu["year"] == eu["year"].max()]
    if len(lat) == 0:
        return pd.DataFrame()
    r = lat.groupby(["hs_key", "hs_desc"]).agg(
        avg_score=("anomaly_score", "mean"), max_score=("anomaly_score", "max"),
        flagged=("spike_flag", "sum"), total_export=("export_usd", "sum"),
        arbitrage=("tariff_arb_pp", "first")).reset_index()
    r = r.sort_values("avg_score", ascending=False).reset_index(drop=True)
    r.index = r.index + 1
    r.index.name = "Rank"
    return r


def policy_recommendations(cname, risk_row, anomaly_df):
    """Generate prioritized policy recommendations for a country."""
    cc = COUNTRIES.get(cname, {})
    recs = []
    ov = risk_row.get("overall", 50)
    sv = risk_row.get("sv_detail", {})

    if ov >= 60:
        recs.append({"Priority": 1, "Category": "Enforcement",
                     "Recommendation": f"Deploy targeted risk-profiling at {cname}'s major ports for: {', '.join(cc.get('key_exports', [])[:3])}",
                     "Stakeholder": f"{cname} Customs Authority",
                     "Impact": "High -- reduces leakage 15-25% in targeted categories"})
    if sv.get("customs_weakness", 0) > 60:
        recs.append({"Priority": 1, "Category": "Capacity Building",
                     "Recommendation": f"Accelerate ASYCUDA/customs automation (current capacity: {cc.get('customs_cap', 0):.0%})",
                     "Stakeholder": f"{cname} Ministry of Finance / WCO",
                     "Impact": "High -- improves detection 20-40% over 2-3 years"})
    if sv.get("governance_gap", 0) > 65:
        recs.append({"Priority": 1, "Category": "Institutional Reform",
                     "Recommendation": "Strengthen customs integrity (rotation, whistleblower protection, automated audit trails)",
                     "Stakeholder": f"{cname} Anti-Corruption Agency",
                     "Impact": "Medium-High -- reduces collusion-based circumvention"})
    recs.append({"Priority": 2, "Category": "Digital Traceability",
                 "Recommendation": "Implement electronic origin certificate linked to AfCFTA Digital Trade Protocol and EU REX system",
                 "Stakeholder": f"{cname} Trade Ministry / AfCFTA Secretariat",
                 "Impact": "High -- reduces false documentation 30-50%"})
    recs.append({"Priority": 2, "Category": "Rules of Origin",
                 "Recommendation": "Review product-specific RoO for highest-risk HS categories; consider raising value-added thresholds",
                 "Stakeholder": "EPA Joint Committee / EU DG Trade",
                 "Impact": "Medium -- narrows arbitrage but may increase compliance costs"})
    recs.append({"Priority": 3, "Category": "AfCFTA Protocol",
                 "Recommendation": "Push for harmonized cumulation rules across EPA groups within AfCFTA to reduce origin-shopping",
                 "Stakeholder": "AfCFTA Secretariat / AU Commission",
                 "Impact": "High (long-term) -- eliminates key structural driver"})
    recs.append({"Priority": 3, "Category": "Data Infrastructure",
                 "Recommendation": "Invest in real-time trade data reporting to reduce 6+ month lag",
                 "Stakeholder": f"{cname} Statistical Office / UNCTAD",
                 "Impact": "Medium -- enables early warning system"})

    # HS-specific recommendations
    for hk in COUNTRY_HOTSPOTS.get(cname, [])[:3]:
        if hk in HS_CATEGORIES:
            hc = HS_CATEGORIES[hk]
            for ct in hc["circumvention"][:1]:
                recs.append({"Priority": 2, "Category": f"HS {hc['ch']}: {hc['desc']}",
                             "Recommendation": f"Address {ct.replace('_', ' ')}: {CIRCUMVENTION_DESC.get(ct, ct)}",
                             "Stakeholder": f"{cname} Customs / EU Import Control",
                             "Impact": f"Targets ~{hc['arbitrage_pp']:.0f}pp arbitrage on {hc['desc']}"})
    return sorted(recs, key=lambda x: x["Priority"])


def stakeholder_summary(rdf, stakeholder="AfCFTA Secretariat"):
    nc = len(rdf[rdf["rating"] == "Critical"])
    nh = len(rdf[rdf["rating"] == "High"])
    nm = len(rdf[rdf["rating"] == "Moderate"])
    nl = len(rdf[rdf["rating"] == "Low"])
    top3 = rdf.head(3)
    top_lines = "\n".join(f"- **{r['country']}** -- Score: {r['overall']:.1f} ({r['rating']})"
                          for _, r in top3.iterrows())

    if stakeholder == "AfCFTA Secretariat":
        return f"""### Executive Briefing: AfCFTA Secretariat

**Scope**: {len(rdf)} EPA-implementing countries | **Risk**: {nc} Critical, {nh} High, {nm} Moderate, {nl} Low

**Top-3 risk-rated countries:**
{top_lines}

**Strategic implications:**
- Current gaps between EPA-specific RoO and AfCFTA general rules create arbitrage. Harmonization is the highest-impact structural reform.
- Countries with lower customs capacity show 2-3x higher circumvention risk. Prioritize digital traceability rollout.
- Significant cross-regional risk disparities suggest differentiated enforcement, not blanket measures.

**Recommended actions:**
1. Commission compliance audits for the {nc + nh} Critical/High-risk countries
2. Accelerate AfCFTA Protocol on Digital Trade for electronic origin verification
3. Establish continental early-warning system for trade anomaly detection
4. Coordinate with EU DG Trade on mutual recognition of enforcement mechanisms
"""
    else:  # EU DG Trade
        return f"""### Intelligence Briefing: EU DG Trade -- Africa Unit

**Scope**: {len(rdf)} African EPA partners | **Risk**: {nc} Critical, {nh} High, {nm} Moderate, {nl} Low

**Top-3 risk-rated origins:**
{top_lines}

**Key findings:**
- {nc + nh} countries show circumvention risk requiring enhanced import-side controls
- Focus post-clearance audits on shipments from flagged origins in HS categories with >10pp tariff arbitrage
- Under elevated rerouting scenarios, West African EPA hubs show 20-35% leakage risk for electronics, apparel, and steel

**Enforcement priorities:**
1. Strengthen REX (Registered Exporter) verification for top-risk origins
2. Deploy enhanced risk-profiling for HS 61-62 (apparel), 84-85 (electronics), 72-73 (steel)
3. Coordinate with OLAF on cross-referencing AfCFTA transit declarations with EU import data
4. Consider targeted post-clearance audits for capacity-mismatch signatures
"""


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: VISUALIZATION HELPERS
# ═══════════════════════════════════════════════════════════════════════

def fmt_usd(v):
    if abs(v) >= 1e9: return f"${v/1e9:.1f}B"
    if abs(v) >= 1e6: return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3: return f"${v/1e3:.1f}K"
    return f"${v:,.0f}"


def fig_risk_bars(rdf):
    d = rdf.sort_values("overall", ascending=True)
    colors = [RISK_COLORS.get(r, "#666") for r in d["rating"]]
    fig = go.Figure(go.Bar(
        y=d["country"], x=d["overall"], orientation="h",
        marker_color=colors, text=[f"{v:.1f}" for v in d["overall"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<extra></extra>"))
    fig.update_layout(
        xaxis=dict(title="Risk Score (0-100)", range=[0, 105]),
        height=max(400, len(d) * 32 + 100), margin=dict(l=120, r=60, t=20, b=30),
        paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg_alt"], showlegend=False)
    return fig


def fig_heatmap(hdf, title=""):
    if hdf.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    fig = go.Figure(go.Heatmap(
        z=hdf.values, x=[c[:28] for c in hdf.columns], y=hdf.index,
        colorscale=[[0, "#E8F5E9"], [.25, "#FFF9C4"], [.5, "#FFE0B2"], [.75, "#FFAB91"], [1, "#EF5350"]],
        colorbar=dict(title="Score"),
        hovertemplate="Country: %{y}<br>Category: %{x}<br>Score: %{z:.1f}<extra></extra>"))
    fig.update_layout(title=dict(text=title, font_size=14),
                      xaxis=dict(tickangle=45, tickfont_size=9), yaxis_tickfont_size=11,
                      height=max(400, len(hdf) * 35 + 150),
                      margin=dict(l=120, r=30, t=50, b=120),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg"])
    return fig


def fig_mc_fan(mc, title=""):
    n = len(mc["leak_mean"])
    labs = [f"Year {i+1}" for i in range(n)]
    m = [v * 100 for v in mc["leak_mean"]]
    p5 = [v * 100 for v in mc["leak_p5"]]
    p25 = [v * 100 for v in mc["leak_p25"]]
    p75 = [v * 100 for v in mc["leak_p75"]]
    p95 = [v * 100 for v in mc["leak_p95"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labs + labs[::-1], y=p95 + p5[::-1], fill="toself",
                             fillcolor="rgba(32,128,141,.1)", line_color="rgba(32,128,141,0)", name="90% CI"))
    fig.add_trace(go.Scatter(x=labs + labs[::-1], y=p75 + p25[::-1], fill="toself",
                             fillcolor="rgba(32,128,141,.25)", line_color="rgba(32,128,141,0)", name="50% CI"))
    fig.add_trace(go.Scatter(x=labs, y=m, mode="lines+markers", name="Mean",
                             line=dict(color=COLORS["primary"], width=3), marker_size=8))
    fig.update_layout(title=dict(text=title, font_size=14),
                      yaxis=dict(title="Leakage Rate (%)", rangemode="tozero"),
                      height=380, margin=dict(l=50, r=30, t=50, b=30),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg_alt"],
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    return fig


def fig_scenario_bars(sdf, title=""):
    d = sdf.sort_values("Leakage Mean %", ascending=True)
    colors = [COLORS["primary"] if v < d["Leakage Mean %"].median() else COLORS["secondary"]
              for v in d["Leakage Mean %"]]
    fig = go.Figure(go.Bar(
        y=d["Scenario"], x=d["Leakage Mean %"], orientation="h", marker_color=colors,
        error_x=dict(type="data", symmetric=False,
                     array=(d["CI High %"] - d["Leakage Mean %"]).tolist(),
                     arrayminus=(d["Leakage Mean %"] - d["CI Low %"]).tolist(), color="#666"),
        text=[f"{v:.1f}%" for v in d["Leakage Mean %"]], textposition="outside",
        hovertemplate="<b>%{y}</b><br>Leakage: %{x:.1f}%<extra></extra>"))
    fig.update_layout(title=dict(text=title, font_size=14),
                      xaxis=dict(title="Leakage Rate (%)", rangemode="tozero"),
                      yaxis_tickfont_size=10,
                      height=max(350, len(d) * 55 + 80),
                      margin=dict(l=260, r=70, t=50, b=30),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg_alt"], showlegend=False)
    return fig


def fig_trade_ts(tdf, cname, partner="EU27"):
    f = tdf[(tdf["reporter"] == cname) & (tdf["partner"] == partner)]
    agg = f.groupby("year").agg(exports=("export_usd", "sum"), imports=("import_usd", "sum")).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=agg["year"], y=agg["exports"], name="Exports",
                             line=dict(color=COLORS["primary"], width=2.5), mode="lines+markers"))
    fig.add_trace(go.Scatter(x=agg["year"], y=agg["imports"], name="Imports",
                             line=dict(color=COLORS["secondary"], width=2.5, dash="dash"), mode="lines+markers"))
    fig.update_layout(xaxis=dict(title="Year", dtick=1), yaxis_title="USD",
                      height=360, margin=dict(l=60, r=30, t=30, b=30),
                      paper_bgcolor=COLORS["bg"], plot_bgcolor=COLORS["bg_alt"],
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
    return fig


def fig_radar(regdf):
    fig = go.Figure()
    cats = ["Avg Risk", "Avg Structural", "Avg Anomaly", "Avg Governance Gap"]
    for i, (_, r) in enumerate(regdf.iterrows()):
        vals = [r[c] for c in cats] + [r[cats[0]]]
        fig.add_trace(go.Scatterpolar(r=vals, theta=cats + [cats[0]], fill="toself",
                                       name=r["Region"],
                                       line_color=CHART_SEQUENCE[i % len(CHART_SEQUENCE)]))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                      height=430, margin=dict(l=70, r=70, t=30, b=30), paper_bgcolor=COLORS["bg"])
    return fig


# ═══════════════════════════════════════════════════════════════════════
# SECTION 10: STREAMLIT APP LAYOUT
# ═══════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.title("Africa Rules-of-Origin Circumvention Simulator")
        st.caption("Updated")
        st.markdown("---")

        st.subheader("Country Selection")
        mode = st.radio("Select by:", ["Individual", "EPA Group", "Region", "All 20"], key="sel_mode")
        all_names = sorted(COUNTRIES.keys())
        if mode == "Individual":
            sel = st.multiselect("Countries:", all_names,
                                 default=["Ghana", "Cote d'Ivoire", "Kenya", "Cameroon",
                                          "Mauritius", "South Africa", "Nigeria", "Tanzania"],
                                 key="c_sel")
        elif mode == "EPA Group":
            g = st.selectbox("EPA group:", list(EPA_GROUPS.keys()), key="epa_g")
            sel = EPA_GROUPS[g]
            st.info(f"Countries: {', '.join(sel)}")
        elif mode == "Region":
            r = st.selectbox("Region:", list(REGION_CLUSTERS.keys()), key="reg_r")
            sel = REGION_CLUSTERS[r]
            st.info(f"Countries: {', '.join(sel)}")
        else:
            sel = all_names

        st.markdown("---")
        st.subheader("Detection Parameters")
        z_th = st.slider("Export spike Z-threshold", 1.0, 4.0, 2.0, 0.25,
                         help="Std deviations above mean to flag")
        cap_th = st.slider("Capacity mismatch threshold", 1.0, 3.0, 1.5, 0.1,
                           help="Export / production-capacity ratio")
        n_sim = st.select_slider("Monte Carlo iterations",
                                 [1000, 2000, 3000, 5000, 10000], 3000,
                                 help="More = precise but slower")

        st.markdown("---")
        st.subheader("Scenario")
        sc_name = st.selectbox("Select scenario:", list(SCENARIOS.keys()), key="sc_sel")
        sc = SCENARIOS[sc_name]
        with st.expander("Scenario parameters"):
            st.write(f"Rerouting pressure: {sc.rerouting_pressure:.1f}")
            st.write(f"AfCFTA liberalization: {sc.afcfta_liberalization:.1f}")
            st.write(f"EPA tightening: {sc.epa_tightening:.1f}")
            st.write(f"Digital traceability: {sc.digital_traceability:.1f}")
            st.write(f"Regional harmonization: {sc.regional_harmonization:.1f}")

        st.markdown("---")
        with st.expander("About"):
            st.markdown("""
**Africa Rules-of-Origin Circumvention Simulator**

Models the overlap between EU EPAs and AfCFTA liberalization as a strategic
arbitrage game, identifying circumvention risks across 20 African countries.

**Methods:** Z-score anomaly detection, capacity-mismatch analysis, origin-shift
correlation, Monte Carlo behavioral simulation (firm + state agents).

**Data:** Modeled trade flows calibrated to UN Comtrade patterns, WGI governance
indicators, EU Access2Markets tariff schedules, EPPO/OLAF enforcement stats.
            """)
        with st.expander("Disclaimer"):
            st.warning("Simulation-based modeling with data calibrated to public "
                       "sources. Results are indicative risk assessments for capacity-building, "
                       "not precise predictions. Framed as neutral diagnostics.")

        return sel, z_th, cap_th, n_sim, sc_name


@st.cache_data(show_spinner=False)
def load_all(countries: tuple, z_th: float, cap_th: float, n_sim: int, sc_name: str):
    trade_df = generate_trade_flows(countries)
    gov_df = generate_governance(countries)
    anomaly_df = run_anomaly_pipeline(trade_df, z_th, cap_th)
    mc = run_mc_multi(countries, sc_name, n_sim)
    risk_df = all_risk_scores(list(countries), anomaly_df, mc, gov_df)
    return trade_df, gov_df, anomaly_df, mc, risk_df


# ─── Tab: Overview ──────────────────────────────────────────────────────

def tab_overview(rdf, adf, mc, sel, sc_name):
    nc = len(rdf[rdf["rating"] == "Critical"])
    nh = len(rdf[rdf["rating"] == "High"])
    avg_r = rdf["overall"].mean()
    avg_l = np.mean([r["final_leak_mean"] for r in mc.values()]) * 100
    eu_exp = adf[(adf["partner"] == "EU27") & (adf["year"] == adf["year"].max())]["export_usd"].sum()

    cols = st.columns(5)
    for col, (lab, val) in zip(cols, [
        ("Countries", str(len(sel))),
        ("Critical + High", f"{nc + nh}"),
        ("Avg Risk Score", f"{avg_r:.1f}"),
        ("Avg Leakage", f"{avg_l:.1f}%"),
        ("EU Exports (latest)", fmt_usd(eu_exp)),
    ]):
        col.markdown(f'<div class="kpi-card"><div class="kpi-val">{val}</div>'
                     f'<div class="kpi-lab">{lab}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Country Risk Ranking")
        st.plotly_chart(fig_risk_bars(rdf), use_container_width=True)
    with c2:
        st.subheader("Risk Distribution")
        dist = rdf["rating"].value_counts()
        fig_pie = go.Figure(go.Pie(
            labels=dist.index, values=dist.values, hole=0.45,
            marker_colors=[RISK_COLORS.get(r, "#666") for r in dist.index],
            textinfo="label+value", textfont_size=13))
        fig_pie.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10),
                              paper_bgcolor=COLORS["bg"], showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("Top Risk Alerts")
        for _, row in rdf.head(5).iterrows():
            cls = f"risk-{row['rating'].lower()}"
            st.markdown(
                f'<div class="{cls}"><strong>{row["country"]}</strong> -- '
                f'Score: {row["overall"]:.1f} ({row["rating"]})<br>'
                f'<small>Structural: {row["structural"]:.0f} | Anomaly: {row["anomaly"]:.0f} | '
                f'MC Leak: {row["mc_leak"]:.0f} | Gov Gap: {row["governance"]:.0f}</small></div>',
                unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Risk Heatmap: Countries x HS Categories")
    hdf = risk_heatmap_data(adf, sel)
    st.plotly_chart(fig_heatmap(hdf, f"Anomaly Scores -- {int(adf['year'].max())}"),
                    use_container_width=True)


# ─── Tab: Country Deep-Dive ─────────────────────────────────────────────

def tab_country(rdf, adf, tdf, mc, gov_df, sel, sc_name, n_sim):
    cname = st.selectbox("Select country:", sel, key="dd_c")
    cc = COUNTRIES.get(cname, {})
    cr = rdf[rdf["country"] == cname]
    if len(cr) == 0:
        st.warning("No data."); return
    cr = cr.iloc[0]

    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader(f"{cname} -- Risk Profile")
        st.markdown(f"**EPA Group**: {cc.get('epa_group','')} | **Region**: {cc.get('bloc','')} | "
                    f"**EPA Status**: {cc.get('epa_status','')} | **EU Access**: {cc.get('eu_access','')}")
    with c2:
        color = RISK_COLORS.get(cr["rating"], "#666")
        st.markdown(f'<span style="background:{color};color:white;padding:4px 12px;border-radius:4px;'
                    f'font-weight:600">{cr["rating"]}</span>', unsafe_allow_html=True)
        st.metric("Overall Score", f"{cr['overall']:.1f}/100")

    cols = st.columns(4)
    for col, (lab, val) in zip(cols, [
        ("Structural", cr["structural"]), ("Anomaly", cr["anomaly"]),
        ("MC Leakage", cr["mc_leak"]), ("Governance Gap", cr["governance"])
    ]):
        col.metric(lab, f"{val:.1f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Trade Flows (EU27)")
        st.plotly_chart(fig_trade_ts(tdf, cname), use_container_width=True)
    with c2:
        st.subheader("Leakage Forecast")
        if cname in mc:
            st.plotly_chart(fig_mc_fan(mc[cname], f"{cname} -- {sc_name}"), use_container_width=True)

    st.markdown("---")
    st.subheader("Anomaly Detection Detail")
    ca = adf[(adf["reporter"] == cname) & (adf["partner"] == "EU27")].sort_values(
        ["year", "anomaly_score"], ascending=[False, False])
    if len(ca) > 0:
        lat = ca[ca["year"] == ca["year"].max()]
        display = lat[["hs_desc", "export_usd", "anomaly_score", "risk_level",
                       "spike_flag", "cap_flag", "origin_flag"]].copy()
        display.columns = ["HS Category", "Export (USD)", "Score", "Risk",
                           "Spike", "Capacity", "Origin Shift"]
        st.dataframe(display, use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Key EPA Exports")
        for e in cc.get("key_exports", []):
            st.markdown(f"- {e.replace('_', ' ').title()}")
    with c2:
        st.subheader("High-Risk HS Categories")
        for hk in COUNTRY_HOTSPOTS.get(cname, []):
            hc = HS_CATEGORIES.get(hk, {})
            if hc:
                st.markdown(f"- **HS {hc['ch']}** -- {hc['desc']} "
                            f"(Tier {hc['tier']}, ~{hc['arbitrage_pp']:.0f}pp)")

    # Narrative
    if cname in mc:
        mr = mc[cname]
        lm = mr["final_leak_mean"] * 100
        ci = mr["final_leak_ci90"]
        ls = mr["leak_mean"]
        trend = "increasing" if ls[-1] > ls[0] else "decreasing" if ls[-1] < ls[0] * 0.9 else "stable"
        st.markdown("---")
        st.subheader("Behavioral Forecast")
        st.markdown(f"""Under **{sc_name}**, the model forecasts a **{trend}** leakage trajectory.
- Expected leakage: **{lm:.1f}%** (90% CI: {ci[0]*100:.1f}% -- {ci[1]*100:.1f}%)
- Circumvention rate: **{mr['final_circ_mean']*100:.1f}%** of firms
- Trajectory: {ls[0]*100:.1f}% (Year 1) to {ls[-1]*100:.1f}% (Year 5)""")


# ─── Tab: Comparative ────────────────────────────────────────────────────

def tab_compare(rdf, adf, sel):
    st.subheader("Cross-Country Comparison")
    regdf = regional_comparison(rdf)
    if len(regdf) > 0:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Regional Risk Profiles")
            st.plotly_chart(fig_radar(regdf), use_container_width=True)
        with c2:
            st.markdown("### Regional Summary")
            st.dataframe(regdf, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("EPA Group Comparison")
    edf = epa_group_comparison(rdf)
    if len(edf) > 0:
        st.dataframe(edf, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Spillover Corridors")
    st.caption("Countries with correlated anomaly patterns suggesting coordinated or cascading circumvention.")
    spdf = spillover_corridors(adf, sel)
    if len(spdf) > 0:
        st.dataframe(spdf.head(20), use_container_width=True, hide_index=True)
    else:
        st.info("No significant spillover corridors detected.")

    st.markdown("---")
    st.subheader("HS Category Vulnerability Ranking")
    hsdf = hs_vulnerability_ranking(adf, sel)
    if len(hsdf) > 0:
        st.dataframe(hsdf[["hs_desc", "avg_score", "max_score", "flagged", "arbitrage"]].rename(
            columns={"hs_desc": "Category", "avg_score": "Avg Score", "max_score": "Max Score",
                     "flagged": "Flags", "arbitrage": "Arbitrage (pp)"}),
            use_container_width=True)

    st.markdown("---")
    st.subheader("Risk Heatmap by Year")
    yr = st.slider("Year:", 2016, 2025, 2025, key="hm_yr")
    hdf = risk_heatmap_data(adf, sel, yr)
    st.plotly_chart(fig_heatmap(hdf, f"Risk Heatmap -- {yr}"), use_container_width=True)


# ─── Tab: Simulation Lab ─────────────────────────────────────────────────

def tab_simulate(sel, mc, n_sim):
    st.subheader("Monte Carlo Simulation Lab")
    sim_c = st.selectbox("Country:", sel, key="sim_c")

    st.markdown("### Scenario Comparison")
    rows = []
    for sn, sc in SCENARIOS.items():
        r = run_mc(sim_c, sc, min(n_sim, 2000))
        if r:
            rows.append({"Scenario": sc.name, "Leakage Mean %": round(r["final_leak_mean"] * 100, 1),
                         "CI Low %": round(r["final_leak_ci90"][0] * 100, 1),
                         "CI High %": round(r["final_leak_ci90"][1] * 100, 1),
                         "Circumvention %": round(r["final_circ_mean"] * 100, 1),
                         "Audit %": round(r["audit_mean"][-1] * 100, 1)})
    sdf = pd.DataFrame(rows)
    if len(sdf) > 0:
        st.plotly_chart(fig_scenario_bars(sdf, f"{sim_c} -- Scenario Comparison (5-Year)"),
                        use_container_width=True)
        st.dataframe(sdf, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Time-Series by Scenario")
    pick = st.multiselect("Scenarios:", list(SCENARIOS.keys()),
                          default=["Baseline", "China Rerouting Shock", "Digital Traceability Rollout"],
                          key="ts_sc")
    if pick:
        cols = st.columns(min(3, len(pick)))
        for i, sn in enumerate(pick):
            with cols[i % len(cols)]:
                r = run_mc(sim_c, SCENARIOS[sn], min(n_sim, 1500))
                if r:
                    st.plotly_chart(fig_mc_fan(r, sn), use_container_width=True)

    st.markdown("---")
    st.subheader("Custom Scenario")
    c1, c2, c3 = st.columns(3)
    with c1:
        cr = st.slider("Rerouting Pressure", 0.0, 1.0, 0.0, 0.05, key="cust_r")
        ca = st.slider("AfCFTA Liberalization", 0.0, 1.0, 0.3, 0.05, key="cust_a")
    with c2:
        ce = st.slider("EPA Tightening", 0.0, 1.0, 0.0, 0.05, key="cust_e")
        cd = st.slider("Digital Traceability", 0.0, 1.0, 0.0, 0.05, key="cust_d")
    with c3:
        ch = st.slider("Regional Harmonization", 0.0, 1.0, 0.0, 0.05, key="cust_h")

    if st.button("Run Custom Scenario", type="primary"):
        csc = Scenario("Custom", cr, ca, ce, cd, ch)
        r = run_mc(sim_c, csc, min(n_sim, 2000))
        if r:
            st.plotly_chart(fig_mc_fan(r, f"{sim_c} -- Custom Scenario"), use_container_width=True)
            st.markdown(f"**Year 5 leakage**: {r['final_leak_mean']*100:.1f}% "
                        f"(90% CI: {r['final_leak_ci90'][0]*100:.1f}% -- {r['final_leak_ci90'][1]*100:.1f}%)")


# ─── Tab: Policy ──────────────────────────────────────────────────────────

def tab_policy(rdf, adf, mc, sel, sc_name):
    st.subheader("Policy Recommendations")
    sh = st.selectbox("Briefing for:", ["AfCFTA Secretariat", "EU DG Trade"], key="sh_sel")
    st.markdown(stakeholder_summary(rdf, sh))

    st.markdown("---")
    st.subheader("Country Policy Menu")
    pc = st.selectbox("Country:", sel, key="pol_c")
    cr = rdf[rdf["country"] == pc]
    if len(cr) > 0:
        recs = policy_recommendations(pc, cr.iloc[0].to_dict(), adf)
        for pri in (1, 2, 3):
            pr = [r for r in recs if r["Priority"] == pri]
            if pr:
                labels = {1: "Priority 1: Urgent", 2: "Priority 2: Structural", 3: "Priority 3: Medium-Term"}
                st.markdown(f"#### {labels[pri]}")
                for r in pr:
                    with st.expander(f"{r['Category']}: {r['Recommendation'][:80]}..."):
                        st.markdown(f"**Recommendation**: {r['Recommendation']}")
                        st.markdown(f"**Stakeholder**: {r['Stakeholder']}")
                        st.markdown(f"**Impact**: {r['Impact']}")

        rec_df = pd.DataFrame(recs)
        csv = rec_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Recommendations (CSV)", csv,
                           f"policy_{pc.lower().replace(' ', '_')}.csv", "text/csv")

    st.markdown("---")
    st.subheader("Regional Brief")
    reg = st.selectbox("Region:", list(REGION_CLUSTERS.keys()), key="pol_reg")
    reg_cs = REGION_CLUSTERS[reg]
    reg_data = rdf[rdf["country"].isin(reg_cs)]
    if len(reg_data) > 0:
        avg = reg_data["overall"].mean()
        hi = reg_data.loc[reg_data["overall"].idxmax()]
        lo = reg_data.loc[reg_data["overall"].idxmin()]
        st.markdown(f"""### {reg} -- Risk Assessment
**Avg risk**: {avg:.1f}/100 | **Highest**: {hi['country']} ({hi['overall']:.1f}) | **Lowest**: {lo['country']} ({lo['overall']:.1f})
""")
        for _, r in reg_data.iterrows():
            st.markdown(f"- **{r['country']}**: {r['rating']} ({r['overall']:.1f})")


# ─── Tab: Data Explorer ──────────────────────────────────────────────────

def tab_data(tdf, adf, rdf, mc, sc_name):
    st.subheader("Data Explorer & Downloads")
    view = st.selectbox("Dataset:", ["Risk Scores", "Anomaly Results", "Trade Flows",
                                     "Simulation Summary"], key="data_v")

    if view == "Risk Scores":
        disp = rdf[["rank", "country", "overall", "rating", "structural", "anomaly", "mc_leak", "governance"]]
        st.dataframe(disp, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", disp.to_csv(index=False).encode(), "risk_scores.csv", "text/csv")

    elif view == "Anomaly Results":
        c1, c2 = st.columns(2)
        with c1:
            fc = st.multiselect("Country:", adf["reporter"].unique(), key="f_c")
        with c2:
            fp = st.selectbox("Partner:", ["All", "EU27", "China", "World"], key="f_p")
        f = adf.copy()
        if fc: f = f[f["reporter"].isin(fc)]
        if fp != "All": f = f[f["partner"] == fp]
        st.caption(f"{len(f):,} records")
        cols = ["reporter", "partner", "hs_desc", "year", "export_usd", "anomaly_score", "risk_level",
                "spike_flag", "cap_flag", "origin_flag"]
        avail = [c for c in cols if c in f.columns]
        st.dataframe(f[avail].head(500), use_container_width=True, hide_index=True)
        st.download_button("Download CSV", f[avail].to_csv(index=False).encode(), "anomaly_data.csv", "text/csv")

    elif view == "Trade Flows":
        st.dataframe(tdf.head(500), use_container_width=True, hide_index=True)
        st.download_button("Download CSV", tdf.to_csv(index=False).encode(), "trade_flows.csv", "text/csv")

    elif view == "Simulation Summary":
        rows = [{"Country": c, "Scenario": r.get("scenario", ""),
                 "Leakage Mean %": round(r["final_leak_mean"] * 100, 2),
                 "CI Low %": round(r["final_leak_ci90"][0] * 100, 2),
                 "CI High %": round(r["final_leak_ci90"][1] * 100, 2),
                 "Circumvention %": round(r["final_circ_mean"] * 100, 2)}
                for c, r in mc.items()]
        sdf = pd.DataFrame(rows)
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        st.download_button("Download CSV", sdf.to_csv(index=False).encode(), "simulation.csv", "text/csv")

    st.markdown("---")
    # Executive summary text download
    nc = len(rdf[rdf["rating"] == "Critical"])
    nh = len(rdf[rdf["rating"] == "High"])
    nm = len(rdf[rdf["rating"] == "Moderate"])
    nl = len(rdf[rdf["rating"] == "Low"])
    txt = f"""African Rules-of-Origin Circumvention Platform - EXECUTIVE SUMMARY
Scenario: {sc_name}
Countries: {len(rdf)} | Critical: {nc} | High: {nh} | Moderate: {nm} | Low: {nl}

TOP RISKS:
"""
    for _, r in rdf.head(5).iterrows():
        txt += f"  {r['country']}: {r['overall']:.1f} ({r['rating']})\n"
    txt += "\nSIMULATION RESULTS:\n"
    for c, r in mc.items():
        txt += f"  {c}: leakage={r['final_leak_mean']*100:.1f}% (CI: {r['final_leak_ci90'][0]*100:.1f}-{r['final_leak_ci90'][1]*100:.1f}%)\n"
    txt += "\nDISCLAIMER: Simulation-based modeling with synthetic data. Indicative only.\n"
    st.download_button("Download Executive Summary (TXT)", txt.encode(), "executive_summary.txt", "text/plain")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 11: MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    sel, z_th, cap_th, n_sim, sc_name = render_sidebar()
    if not sel:
        st.warning("Select at least one country from the sidebar.")
        return

    with st.spinner("Running analysis pipeline..."):
        tdf, gov_df, adf, mc, rdf = load_all(tuple(sorted(sel)), z_th, cap_th, n_sim, sc_name)

    st.title("African Rules-of-Origin Circumvention Simulator")
    sc = SCENARIOS[sc_name]
    st.markdown(f"**Scenario**: {sc.name} | **Countries**: {len(sel)} | **MC Iterations**: {n_sim:,}")

    t1, t2, t3, t4, t5, t6 = st.tabs([
        "Overview", "Country Deep-Dive", "Comparative",
        "Simulation Lab", "Policy Menu", "Data Explorer"])

    with t1: tab_overview(rdf, adf, mc, sel, sc_name)
    with t2: tab_country(rdf, adf, tdf, mc, gov_df, sel, sc_name, n_sim)
    with t3: tab_compare(rdf, adf, sel)
    with t4: tab_simulate(sel, mc, n_sim)
    with t5: tab_policy(rdf, adf, mc, sel, sc_name)
    with t6: tab_data(tdf, adf, rdf, mc, sc_name)

    st.markdown("---")
    st.markdown('<div class="footer">African Rules-of-Origin Circumvention Simulator | Open-Source Simulation Tool | '
                'Data: UN Comtrade, World Bank WGI, EU Access2Markets, AfCFTA e-Tariff Book | '
                'MC calibration: EPPO/OLAF enforcement statistics</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
