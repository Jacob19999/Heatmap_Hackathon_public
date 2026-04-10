# HeatMap Hackathon

## About the Competition

The **HeatMap Hackathon** is a data-driven healthcare competition organized by the **American Burn Association (ABA)** and **BData**, in partnership with **HealthcareMN**, **MinneAnalytics**, and the **University of Minnesota Institute for Research in Statistics and its Applications**. Teams work with real-world hospital infrastructure data to develop actionable insights that advance burn care delivery across the United States.

Participants are provided the **National Injury Resource Database (NIRD)** — a comprehensive, hospital-level dataset of all U.S. burn centers and trauma centers — and are challenged to analyze how hospital capabilities, trauma designations, burn center availability, and geography shape care access and outcomes. Each team selects one of three primary use cases and delivers a presentation evaluated on clinical relevance, analytic rigor, and communication quality (scored out of 45 points).

---

## Executive Summary: The Burn & Trauma Landscape in the U.S.

### Scale of the Problem

Burn injuries represent a significant and under-resourced public health burden in the United States:

- **~600,000 individuals** annually suffer burn injuries requiring emergent care (Ivanko et al., 2024)
- **~30,135 burn admissions** were reported in 2022 through the ABA Burn Injury Summary Report, down from 32,857 in 2021
- The **cost of medical burn care** is estimated at **$4.1 billion** annually, with an additional **$721 million in lost work productivity** (CDC WISQARS, 2020)
- The U.S. burn care market was valued at **$5.9 billion in 2021** and is projected to grow at a 3.6% CAGR through 2030

### Infrastructure Gaps

Despite the scale of burn injuries, the care infrastructure is highly concentrated and unevenly distributed:

- Of approximately **6,200 U.S. hospitals**, only **135 have burn centers** — and only **76 are ABA-verified**
- **8 states have no burn centers at all** (Alaska, Delaware, Mississippi, Montana, North Dakota, New Hampshire, South Dakota, Wyoming)
- **11 additional states** lack any ABA-verified burn center
- Only **~250 dedicated burn surgeons** practice in the U.S., with many centers operating at or over capacity
- More than **two-thirds of burn care** occurs at non-verified, non-burn-center facilities
- **66% of patients** treated in non-burn facilities meet ABA referral criteria but are never transferred to a burn center

### Disparities in Access

Published research consistently identifies systemic inequities in burn care access:

- **Geographic distance** is a strong predictor of non-referral — patients living farther from burn centers are significantly less likely to receive specialized care
- **Older patients** and those with **multiple comorbidities** are less likely to be transferred, even when meeting referral criteria
- **Delayed referral** (average 7.6 days vs. 0.45 days for timely referral) leads to significantly longer hospital stays, higher surgical intervention rates, and more complications
- **Rural populations** face compounding barriers from distance, limited local capabilities, and lower provider density

### Evidence for Improvement

The research base also highlights clear, data-driven pathways to better outcomes:

- **Standardized referral criteria** can achieve 96% sensitivity and 90% specificity in identifying patients who need specialized care
- **Telemedicine** has been shown to accurately assess surgical need in 94.4% of cases, safely diverting 65% of patients from unnecessary transfers
- **Virtual visits** save an average of 130 miles, 164 minutes, and $185 per encounter while maintaining equivalent clinical outcomes
- **Regionalized, tiered care systems** can deliver equitable outcomes in rural populations without requiring universal transfer to high-volume centers

---

## Competition Goals & Challenge Areas

Teams select **one primary use case** to focus their analysis. Insights that extend to additional use cases are encouraged but not required.

### Challenge Area 1: Advancing Burn Care Referral Networks

> **Core Question:** How can data be used to improve referral criteria and reduce delays in access to specialized burn care?

- Identify hospitals that meet burn referral criteria but lack burn center designation
- Map non-burn trauma centers that may experience delayed or missed referrals
- Analyze distance to the nearest burn center by hospital type
- Model referral network tiers (local hospital → trauma center → burn center)
- Build decision-support frameworks to prompt earlier burn center involvement

### Challenge Area 2: Expanding Telemedicine in Burn Care

> **Core Question:** Where can telemedicine most effectively support burn triage and decision-making?

- Identify hospitals without burn centers but with existing trauma capability (candidate tele-burn spoke sites)
- Rank structural gaps between trauma centers and burn centers
- Model hub-and-spoke tele-burn configurations based on designation patterns and geography
- Estimate travel-time savings and patient impact from telemedicine deployment

### Challenge Area 3: Advancing Equitable Access to Burn Care

> **Core Question:** Where do structural inequities limit access to timely burn care?

- Analyze burn center distribution per capita by state or region
- Compare average distance to burn care for rural vs. urban counties
- Evaluate pediatric burn access relative to child population
- Assess burn bed capacity in high-injury vs. low-injury regions

---

## Dataset: National Injury Resource Database (NIRD)

The NIRD is a **hospital-level** (not patient-level) structured dataset capturing:

| Variable Group | Key Fields | Description |
|---|---|---|
| **Geographic** | `STATE`, `COUNTY`, `ZIP_CODE`, `ADDRESS` | Hospital location for spatial analysis and distance modeling |
| **Identification** | `AHA_ID`, `HOSPITAL_NAME`, `PHONE` | Hospital identifiers for deduplication and linkage |
| **Capacity** | `TOTAL_BEDS`, `BURN_BEDS` | Staffed beds and burn-dedicated beds |
| **Trauma Designation** | `TRAUMA_ADULT`, `TRAUMA_PEDS`, `ADULT_TRAUMA_L1/L2`, `PEDS_TRAUMA_L1/L2` | Trauma capability and level |
| **Burn Designation** | `BURN_ADULT`, `BURN_PEDS`, `ABA_VERIFIED`, `BC_STATE_DESIGNATED` | Burn center capability and verification status |
| **Verification** | `ACS_VERIFIED`, `TC_STATE_DESIGNATED` | ACS and state-level verification |

The database includes **135 burn centers** and **617 trauma centers** across **635 institutions**. Teams are encouraged to augment NIRD with external data (U.S. Census, RUCA codes, travel-time estimates, EMS datasets).

---

## Data Security

The `NIRD` dataset is governed by the hackathon data use terms summarized in `Research/BData_HeatMapHackathon_DUA_Summary.pdf`. In line with those requirements:

- Full `NIRD` data must be accessed and analyzed only within a secure local environment controlled by authorized team members.
- `NIRD` files, extracts, or derived outputs should **not** be uploaded to public or third-party AI tools, hosted LLMs, or cloud AI platforms that may retain submitted content or use it for model training.
- When AI assistance is needed for coding, documentation, or workflow support, only the `Data_Mapping_Document.pdf` and a carefully prepared **sample subset** may be shared with those tools.
- Any sample subset shared with AI tools should be the minimum necessary for the task, limited to non-sensitive illustrative records, and must not expose the full dataset or reconstructable derivatives.
- All `NIRD` data, extracts, and derivatives must remain restricted to the hackathon, must not be shared outside the team, and must be deleted at the end of the event if required by the data use agreement.

This repository should therefore treat AI-enabled work as **mapping-document plus sample-subset only**, while all full-dataset analysis stays local and access-controlled.

---

## Judging Criteria (45 Points Total)

| Category | Weight | What Judges Evaluate |
|---|---|---|
| **Clinical / Business Use Case** | 15 pts | Problem framing, use-case alignment, evidence-backed insights, stakeholder impact |
| **Analytic / Methodologic Quality** | 15 pts | Methodological soundness, innovation & creativity, data integration |
| **Presentation & Communication** | 15 pts | Clarity & storytelling, visual/verbal quality, actionability & feasibility |

---

## Repository Structure

```
Heatmap_Hackathon/
├── Dataset/                  # NIRD dataset files
├── Reference/                # Supporting documents
│   ├── Burden_of_Burn_2024.pdf       # Burden of burn injuries analysis (Ivanko et al.)
│   ├── Burn_NIRD_2023_Burns.pdf      # NIRD development paper (Lovick et al.)
│   ├── Data_Mapping_Document.pdf     # NIRD data dictionary & variable guide
│   ├── Use_Case_Publications.pdf     # 10 published studies across 3 use cases
│   └── Judge_Evaluation_Form.pdf     # Scoring rubric for team presentations
└── README.md
```

---

## Key References

1. Ivanko, A. et al. (2024). "The Burden of Burns: An Analysis of Public Health Measures." *Journal of Burn Care & Research*.
2. Lovick, E.A. et al. (2023). "Development of the National Injury Resource Database (NIRD)." *Burns*.
3. Huang, Z. et al. (2021). "Burn Center Referral Practice Evaluation and Treatment Outcomes." Statewide study of 96,000+ cases.
4. Murray, D.O. et al. (2019). "A Case-Controlled Retrospective Review of Burn Patients Meeting ABA Referral Criteria."
5. Head, W.T. et al. (2022). "Virtual Visits for Outpatient Burn Care During the COVID-19 Pandemic."
6. Boccara, D. et al. (2018). "Telemedicine: Burn Care Management With a Smartphone." 94.4% accuracy in surgical determination.
7. Grossoehme, D.H. et al. (2023). "Palliative Care and Burn Care: Empirically Derived Referral Criteria."
8. Conlon, K.M. et al. (2019). "Determining Immediate Burn Bed Availability to Support Regional Disaster Response."
9. Blaisdell, L.L. et al. (2012). "A Half-Century of Burn Epidemiology and Burn Care in a Rural State."
