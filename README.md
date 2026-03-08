# African EPA-AfCFTA Overlap Integrity Platform

**Modular Multi-Country Rules-of-Origin Circumvention Simulator with Behavioral Forecasting**

An interactive Streamlit application that models the overlap between EU Economic Partnership Agreements (EPAs) and the African Continental Free Trade Area (AfCFTA) as a dynamic strategic arbitrage game. It identifies circumvention risks (rerouting, misclassification, false origin claims) across 20 African countries, forecasts adaptive behaviors, and supports comparative enforcement and negotiating strategies.

---

## What It Does

1. **Country selection**: Choose one or more of 20 African EPA-implementing countries via sidebar controls (individual, by EPA group, by region, or all).
2. **Anomaly detection**: Runs four statistical detectors on synthetic trade-flow data calibrated to real UN Comtrade patterns:
   - Z-score export spike detection (configurable threshold)
   - Production capacity mismatch analysis
   - Origin shift correlation (China imports vs. EU exports)
   - Import-export ratio anomaly flagging (transshipment indicator)
3. **Monte Carlo simulation**: Models firm-level circumvention decisions and state-level enforcement responses as interacting agents over a 5-year horizon under 6 predefined scenarios + custom scenario builder.
4. **Composite risk scoring**: Weighted combination -- Structural vulnerability (30%), Anomaly signals (30%), MC leakage estimate (25%), Governance trajectory (15%).
5. **Interactive dashboards** across 6 tabs: Overview, Country Deep-Dive, Comparative Analysis, Simulation Lab, Policy Menu, Data Explorer.
6. **CSV downloads** for all key outputs (risk scores, anomaly data, simulation results, policy recommendations, executive summary).

---

## Data Sources

All data is embedded directly in the code (no external API calls required at runtime). Baseline values are calibrated to these public sources:

| Data | Source | Notes |
|------|--------|-------|
| Trade flow patterns | [UN Comtrade](https://comtrade.un.org) | Synthetic data calibrated to 2016-2025 reporter/partner/HS6 patterns |
| Governance indicators | [World Bank WGI 2024](https://www.worldbank.org/en/publication/worldwide-governance-indicators) | Government Effectiveness percentile rank |
| GDP, manufacturing share | [World Bank WDI 2023](https://databank.worldbank.org/source/world-development-indicators) | Current USD GDP, MVA % of GDP |
| EPA tariff schedules | [EU Access2Markets](https://trade.ec.europa.eu/access-to-markets/) | Duty-free/quota-free access, RoO protocols |
| AfCFTA concessions | [AfCFTA e-Tariff Book](https://etariff.au-afcfta.org) | Tariff liberalization schedules |
| Enforcement calibration | [EPPO Annual Report 2025](https://www.eppo.europa.eu/) | 3,602 cases, EUR 67.27bn estimated damage |
| Customs fraud patterns | [OLAF Annual Report](https://anti-fraud.ec.europa.eu/) | Origin fraud typologies |
| Trade facilitation | [UNCTAD Trade Facilitation](https://unctad.org/topic/trade-facilitation) | Customs automation indicators |

---

## Model Specification

### Anomaly Detection Pipeline

| Method | Weight | Description |
|--------|--------|-------------|
| Export spike | 30% | Rolling Z-score; flags values > threshold SD above expanding-window mean |
| Capacity mismatch | 25% | Export-to-production-capacity ratio vs. baseline median (first 3 years) |
| Origin shift | 25% | Pearson correlation between China import growth and EU export growth |
| Import/export ratio | 20% | China imports / EU exports ratio as transshipment indicator |

### Monte Carlo Behavioral Simulation

**Firm agent**: Maximizes E[gain from circumvention] = tariff_saving - rerouting_cost, subject to E[loss if caught] = detection_probability x penalty_multiplier x tariff_saving. Decision via logistic function modulated by risk aversion and compliance baseline. Parameters drawn from lognormal distributions per simulation.

**State agent**: Adjusts audit intensity bounded by governance capacity, customs technology, enforcement budget, and political will. Responds to observed circumvention with lag.

**Interaction**: Multi-period adaptive dynamics -- firms learn from previous enforcement intensity; states respond to observed circumvention. External shocks (rerouting pressure, AfCFTA liberalization) shift equilibrium.

**Calibration**: Firm detection probability baseline (10-25%) and penalty multipliers (2-4x) anchored to EPPO 2025 statistics on EU customs fraud cases.

### Risk Score Composition

| Component | Weight | Range |
|-----------|--------|-------|
| Structural vulnerability | 30% | Port exposure, governance gap, customs weakness, EPA access value, manufacturing cover, HS exposure |
| Anomaly signals | 30% | Latest-year mean composite anomaly score (EU27 partner) |
| MC leakage estimate | 25% | Final-period mean leakage rate x 400 (scales 0-25% to 0-100) |
| Governance trajectory | 15% | WGI customs effectiveness level + trend adjustment |

---

## Countries Covered (20)

- **West Africa**: Ghana, Cote d'Ivoire, Nigeria, Senegal, Togo
- **Central Africa**: Cameroon, Gabon
- **East Africa (EAC)**: Kenya, Tanzania, Uganda, Rwanda
- **ESA**: Mauritius, Madagascar, Zimbabwe, Seychelles, Comoros
- **SADC**: South Africa, Botswana, Mozambique, Namibia

## Monitored HS Categories (16)

Fish (03), Vegetables & Fruit (07-08), Fats & Oils (15), Sugar (17), Cocoa (18), Tobacco (24), Minerals & Fuels (26-27), Plastics (39), Wood (44), Cotton (52), Apparel (61-62), Precious Metals (71), Iron & Steel (72-73), Aluminium (76), Machinery & Electronics (84-85), Vehicles (87)

---

## Deployment

### Streamlit Community Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set main file to `app.py`
5. **Set Python version to 3.12** in Advanced Settings (Streamlit Cloud defaults to 3.13, and some pinned packages may lack 3.13 wheels)
6. Deploy -- no secrets required

### Local Development

```bash
# Requires Python 3.10-3.12
pip install -r requirements.txt
streamlit run app.py
```

### Hugging Face Spaces

1. Create a new Space (Streamlit SDK)
2. Upload all files (`app.py`, `requirements.txt`, `.streamlit/config.toml`, `README.md`)
3. Auto-deploys

---

## Project Structure

```
epa-afcfta-simulator/
  app.py                  # Single-file application (all data, logic, UI)
  requirements.txt        # 5 packages, exact-pinned versions
  README.md               # This file
  .streamlit/
    config.toml           # Theme + browser config
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.41.1 | Web application framework |
| pandas | 2.2.3 | Data manipulation |
| numpy | 2.0.2 | Numerical computation |
| scipy | 1.13.1 | Statistical methods (Pearson correlation) |
| plotly | 5.24.1 | Interactive charts (heatmaps, fan charts, bar charts) |

No other packages are required. The app uses only Python standard library beyond these five.

---

## Limitations

- **Synthetic data**: Trade flows are generated, not live. Calibrated to real patterns but not identical to actual Comtrade data. Data lags (3-6 months) are inherent in the real sources too.
- **Model simplification**: The Monte Carlo model uses representative-firm and representative-state agents rather than heterogeneous agent-based modeling.
- **Country comparisons**: Risk scores should be interpreted as relative capacity diagnostics, not absolute judgments. Framed neutrally to support capacity-building.
- **HS granularity**: Analysis uses HS 2-digit chapters rather than 6/8-digit tariff lines. Real enforcement requires tariff-line granularity.
- **No real-time alerting**: Forward-looking scenarios substitute for real-time monitoring, which would require live data feeds.

---

## License

MIT
