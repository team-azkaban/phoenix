# 🔥 Phoenix — AI-Powered Geospatial Thermal Intelligence

**Built for SIH 2026 PS 26162 by Team Azkaban**

> From thermal signals to actionable intelligence.

Phoenix is a geospatial intelligence platform that converts raw satellite thermal detections into classified, validated, and contextualised events. Instead of stopping at "a hotspot was detected", it determines what the event most likely is, whether it is abnormal for the facility involved, and who may be affected downwind.

The current deployment targets the **Dahej Industrial Region, Gujarat, India**, a dense cluster of chemical, petrochemical, and power facilities where thermal anomalies carry real environmental and disaster-management consequences.

---

## 🎯 Problem Context

Satellite active-fire products such as NASA FIRMS report thermal anomalies, but they do not say what caused the heat. Analysts must manually correlate each detection with maps, facility records, imagery, and weather, which is slow and does not scale.

- A single detection cannot distinguish an industrial fire from a routine gas flare or a crop burn.
- Correlating detections with facility, land-cover, and weather data by hand delays response during real incidents.
- Phoenix automates this correlation as one pipeline and exposes the result through a map-based interface.

---

## 🚀 Core Capabilities

Phoenix goes beyond hotspot display and builds an event-level understanding of each thermal anomaly.

- **Event construction:** Individual detections are clustered in space and time into discrete events, so downstream analysis works on events rather than isolated pixels.
- **ML classification:** An XGBoost model classifies each event from thermal, temporal, and geospatial features and outputs class probabilities instead of a single hard label.
- **Contextual validation:** Every event is cross-checked against facility locations, land cover, and Sentinel-2 imagery to support or challenge the model's prediction.
- **Facility baselining:** Historical thermal behaviour is stored per facility, so an event is judged against what is normal for that site.
- **Environmental estimation:** Thermal activity is translated into event-level and cumulative emission estimates and trends.
- **Impact assessment:** Wind data drives a downwind impact corridor that is intersected with population rasters to estimate potential exposure.
- **Alerting:** Events are scored and surfaced as incident alerts carrying classification, confidence, anomaly level, and exposure context.
- **Conversational access:** Ask Phoenix lets analysts query the platform in natural language, such as "Which alerts need attention?".

---
## 🖥️ Prototype Screenshots

### Landing Page
Overview of Phoenix and its thermal intelligence workflow.

![Phoenix Landing Page](screenshots/01-landing-page.png)

### Regional Thermal Intelligence
Regional view of thermal events and industrial activity.

![Regional Thermal Intelligence](screenshots/02-regional-overview.png)

### AI Thermal Classification
ML-based classification using thermal, temporal, and geospatial features.

![AI Thermal Classification](screenshots/03-ai-classification.png)

### Event Investigation
Classification results supported by satellite and geospatial evidence.

![Event Investigation](screenshots/04-event-investigation.png)

### Facility Monitoring
Historical thermal baselines and facility-level anomaly analysis.

![Facility Monitoring](screenshots/05-facility-monitoring.png)
![Facility Monitoring](screenshots/08-facility-1.png)

### Environmental Intelligence
Facility emissions and long-term thermal activity trends.

![Environmental Intelligence](screenshots/06-environmental-monitoring.png)

### Incident Alerts & Impact
Risk alerts, impact corridors, and population exposure.
![Incident Alerts and Impact Assessment](screenshots/09-alerts.png)
![Incident Alerts and Impact Assessment](screenshots/07-impact-assessment.png)
![Incident Alerts and Impact Assessment](screenshots/10-downwind.png)

### Ask Phoenix
Natural-language interaction with Phoenix intelligence.

![Ask Phoenix](screenshots/08-ask-phoenix.png)

---
## 🧩 System Pipeline

The pipeline runs from raw detections to analyst-facing alerts, with each stage enriching the event record produced by the previous one.

```text
NASA FIRMS (MODIS / VIIRS detections)
        │
        ▼
Spatial-temporal clustering  ──►  Thermal events
        │
        ▼
Feature engineering (thermal + temporal + geospatial)
        │
        ▼
XGBoost classifier  ──►  Class probabilities
        │
        ▼
Validation: Sentinel-2 imagery, land cover, facility proximity
        │
        ▼
Facility baseline comparison  ──►  Anomaly score
        │
        ▼
Risk scoring + emission estimation
        │
        ▼
ERA5 wind  ──►  Impact corridor  ──►  WorldPop exposure estimate
        │
        ▼
Incident alerts, evidence reports, Ask Phoenix
```

---

## 🧠 Machine Learning

Phoenix uses **XGBoost** because the problem is tabular, the features are heterogeneous, and gradient-boosted trees handle mixed-scale inputs and non-linear interactions well while staying reasonably interpretable through feature importance.

### 📐 Features

| Group | Description |
|---|---|
| Thermal | Fire radiative power (FRP) and detection confidence describe the intensity and reliability of the signal. |
| Temporal | Duration, observation count, and persistence help separate short burns from sustained industrial heat. |
| Spatial | Event extent and geometry show whether the source is compact, like a flare stack, or spread out, like a field burn. |
| Geospatial | Distance to the nearest known facility and the surrounding land-cover class tie the event to its physical setting. |
| Behavioural | Deviation from the associated facility's historical activity indicates whether the event is unusual for that site. |

### 🏷️ Event Classes

The classifier distinguishes the following event types:

- **Industrial fire:** Sustained, high-FRP heat located at or near a known facility.
- **Gas flare:** Persistent, compact heat that recurs at the same facility location.
- **Agricultural burn:** Short-lived heat over cropland land-cover.
- **Wildfire:** Heat spreading across vegetated land away from infrastructure.
- **Mining activity:** Thermal signals associated with extraction sites.
- **Mixed / uncertain:** Events where no class probability is dominant, flagged for analyst review instead of being forced into a category.

---

## 🗺️ Geospatial Layer

**PostgreSQL with PostGIS** is the central spatial store. Spatial operations run in-database, which keeps them fast and consistent across the pipeline.

- Events are matched to the nearest facility within a distance threshold.
- Each event location is assigned a land-cover class.
- Impact corridors are clipped and population raster values are aggregated inside them.
- Spatial filters power the map views and alert queries.

---

## 🏭 Facility Baselines and Anomaly Analysis

For each monitored facility, Phoenix stores the historical distribution of thermal behaviour and compares every new event against it.

- Baselines cover typical FRP, event frequency, and persistence.
- The deviation from baseline becomes an anomaly indicator that feeds risk scoring.
- This separates routine operational heat, such as regular flaring, from behaviour that warrants investigation.

---

## 🌱 Environmental Intelligence

Thermal activity is converted into emission estimates so the platform can support environmental monitoring, not just incident detection.

- Emissions are estimated per event and aggregated into facility-level cumulative totals.
- Trends can be compared against earlier periods to highlight sustained increases.
- Outputs are intended to support investigation and compliance-oriented analysis.

---

## 🌬️ Impact Assessment

For high-risk events, Phoenix estimates who may be affected downwind of the source.

- ERA5 wind direction is used to model a downwind corridor originating at the event location.
- The corridor is overlaid on WorldPop data to estimate the potentially exposed population.
- These figures are modelled geographic exposure, not confirmed real-world exposure.

---

## 🔍 Explainability and Alerts

Each classified event carries an evidence profile so the analyst sees why a class was predicted, not only the prediction.

- The profile summarises thermal signal, temporal behaviour, facility relationship, land cover, historical deviation, and satellite imagery.
- Incident alerts combine classification, confidence, FRP anomaly, baseline deviation, and exposure information into one investigation record.

---

## 💬 Ask Phoenix

Ask Phoenix is a natural-language interface, backed by the Gemini API, that retrieves structured intelligence from the platform and explains it.

- "Which events are highest risk?"
- "Why was this event classified as an industrial fire?"
- "Which facilities show anomalous activity?"
- "How many people are potentially exposed?"

---

## 🛰️ Data Sources

Each source contributes a distinct layer of context around a detected event.

| Source | Role in Phoenix |
|---|---|
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | Primary MODIS and VIIRS active-fire detections with location, time, FRP, and confidence. |
| Sentinel-2 | Optical imagery for visual validation around detected events. |
| ESA WorldCover | Land-cover classes used as a classification feature and validation signal. |
| OpenStreetMap | Roads, industrial infrastructure, and facility geometry. |
| Global Energy Monitor | Structured energy and industrial facility records for facility association. |
| ERA5 | Reanalysis wind data for downwind direction and corridor modelling. |
| WorldPop | Gridded population data for exposure estimation. |

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| ML | Python, XGBoost, feature engineering, statistical baseline analysis |
| Geospatial | PostgreSQL, PostGIS, OpenStreetMap |
| Backend | Python, FastAPI, REST APIs |
| Frontend | React, Leaflet |
| Conversational layer | Gemini API |

---

## 📁 Repository Structure

```text
phoenix/
├── frontend/        # React app, map views, alert and event pages
├── backend/         # FastAPI routes, services, schemas
├── ml/              # Preprocessing, features, training, evaluation
├── geospatial/      # Clustering, spatial queries, facility matching, impact analysis
├── data/            # raw/, processed/, samples/
├── notebooks/       # Exploration and experiments
├── scripts/         # Ingestion and utility scripts
├── docs/
├── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Getting Started

Phoenix runs as a FastAPI backend with a React frontend, both backed by a PostGIS-enabled database.

**Prerequisites**

- Python 3.10+
- Node.js 18+
- PostgreSQL with the PostGIS extension enabled

**Setup**

```bash
git clone https://github.com/<your-username>/phoenix.git
cd phoenix

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

**Configuration**

Populate `.env` with your own credentials. Never commit `.env` or any API key, and keep `.env` listed in `.gitignore`.

```env
DATABASE_URL=postgresql://user:password@localhost:5432/phoenix
FIRMS_API_KEY=your_firms_key
GEMINI_API_KEY=your_gemini_key
```

**Run**

```bash
# Backend
uvicorn backend.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## ⚠️ Limitations

Phoenix is a decision-support system, and its outputs should be read with the following constraints in mind.

- A satellite thermal anomaly is not a confirmed fire. It can come from industrial processes, agricultural burning, or other heat sources, which is why Phoenix relies on several independent signals.
- MODIS and VIIRS have coarse spatial resolution, so small or short-lived events may be missed or merged.
- Emission and population-exposure values are model-based estimates that depend on the accuracy of the underlying wind, land-cover, and population data.
- Human verification remains necessary for high-consequence decisions.

---

## 🔭 Future Scope

- **Human-in-the-loop verification:** Analyst corrections fed back into model training.
- **Plume dispersion modelling:** A physically grounded replacement for the simple wind-corridor approximation.
- **Sentinel-5P indicators:** Atmospheric composition as an independent validation signal.
- **Multi-channel alerts:** Delivery beyond the dashboard.
- **Wider coverage:** Expansion to other industrial regions across India.
- **Forecasting:** Event prediction based on facility behaviour.

---

## 👥 Team Azkaban

Built for **Smart India Hackathon 2026, Problem Statement 26162**.
- Ananya Sharma
- Atreyi Prasad
- Avwal Kaur
- Avani Mathur
- Juhi Khanna
- Vania Goel

