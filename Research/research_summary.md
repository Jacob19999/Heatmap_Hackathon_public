# Research Summary

## Paper 1: The Burden of Burns: An Analysis of Public Health Measures

**Authors:** Ivanko, A., Garbuzov, A.E., Schoen, J.E., Kearns, R., Phillips, B., Murata, E., Danos, D., Phelan, H.A., & Carter, J.E.

**Published:** 2024, *Journal of Burn Care & Research* (Oxford University Press / American Burn Association)

**Funding:** Spirit of Charity Foundation

### Objective

To compare national references reporting the incidence of burn injuries in the United States and estimate the true burden of burns.



### Background

- Burn mortality has improved over recent decades, but the societal burden remains ambiguous to the public.
- Scarcity of investigational funding for burn survivors has led to gaps in understanding lifelong sequelae.
- NIH funding levels are highly associated with burden of disease, making accurate incidence reporting critical for resource allocation.
- Only 135 of ~6,200 US hospitals have a burn center, and only 50-60% of those are ABA-verified.
- The majority of burn care occurs at rural, non-trauma, non-burn centers, making it difficult to quantify the patient population.

### Methods

Seven national data sources were queried for 2020 (or most recent available data):

1. ABA Burn Injury Summary Report (BISR)
2. ABA Fact Sheet
3. CDC WISQARS database
4. CDC NHAMCS (National Hospital Ambulatory Medical Care Survey)
5. National Inpatient Sample (NIS)
6. National Emergency Department Sample (NEDS)
7. Commercially available claims databases (ICD-10 burn codes)

### Key Findings


| Source         | Patient Population     | Burn Injury Estimate           | Year |
| -------------- | ---------------------- | ------------------------------ | ---- |
| ABA BISR       | Admissions             | 30,135                         | 2022 |
| ABA Fact Sheet | ED & Admissions        | 486,000                        | 2011 |
| CDC NHAMCS     | ED                     | 359,000                        | 2020 |
| NIS            | Inpatients             | 118,720                        | 2020 |
| NEDS           | ED                     | 438,185                        | 2020 |
| CDC WISQARS    | Unintentional injuries | 287,926 non-fatal; 3,529 fatal | 2020 |
| Claims data    | Claims                 | 698,555                        | 2020 |


- **Large variability** exists across all reporting sources.
- The ABA BISR only captures data from 109 burn centers, severely undercounting total admissions.
- The NHAMCS surveys only ~400 EDs over a 4-week window and generalizes to a full year.
- CDC WISQARS reported medical costs of **$4.1 billion** and **$721 million** in lost work for 2020.
- Claims data (698,555) likely still underreports self-pay/uninsured, military facilities, and community-based hospitals.

### Long-Term Sequelae (Underreported)

- Burn patients face elevated risk of cancer, cardiovascular disease, neurological disorders, diabetes, musculoskeletal disorders, GI disease, and infections.
- Psychiatric conditions, hypertrophic scarring, and range-of-motion disabilities require extended follow-up.
- Burn hypermetabolism persists for years post-injury.
- No DRG codes exist to associate long-term complications with the original burn injury ICD-10 code.

### Conclusion

- The authors estimate **~600,000 individuals annually** suffer a burn injury meriting emergent care in the US.
- The true incidence is likely much higher than reported by any single source.
- Underreporting leads to a scarcity of NIH research funding (for comparison, Alzheimer's with ~500,000 cases receives $2.9B in funding).
- Further analysis of claims databases is needed to better determine treatment patterns.

---

## Paper 2: Development of the National Injury Resource Database (NIRD)

**Authors:** Lovick, E.A., Phelan, H.A., Phillips, B.D., Hickerson, W.L., Kearns, R.D., & Carter, J.E.

**Published:** 2023, *Burns* (Elsevier)

**Presented:** Poster at the 2023 American Burn Association Annual Meeting

### Objective

To develop a comprehensive, publicly available database of all US burn centers (BC) and trauma centers (TC) and their capabilities, addressing the lack of an accurate resource for burn/trauma care routing and planning.

### Background

- More than two-thirds of severely burned patients are treated at non-verified burn centers.
- Only a small number of states have formal burn center designation requirements.
- The lack of an accurate, publicly available database creates challenges in patient routing and disaster preparedness.
- Only 2% of US hospitals have designated burn centers.

### Methods

- Each state was queried for the presence of burn and trauma centers.
- Data sources: American Burn Association (ABA), American College of Surgeons (ACS/COT), all 51 state departments of health (SDH).
- Centers were linked with 7-digit AHA identification numbers.
- Resources and verification status validated via electronic/telephonic communications.
- Combined with commercially available claims databases to create an IRB-approved centralized database.

### Key Findings

#### Database Composition

- **635 total institutions**: 135 burn centers + 617 trauma centers
  - 18 burn-center-only facilities
  - 500 trauma-center-only facilities
  - 117 co-located burn and trauma centers

#### Burn Center Verification & Designation

- **76 ABA-verified burn centers** found in 31 states + Washington DC
- 11 states had no ABA-verified burn centers (Alabama, Arkansas, Hawaii, Idaho, Kentucky, Maine, New Mexico, Oklahoma, South Carolina, Vermont, West Virginia)
- **8 states had no burn centers at all** (Alaska, Delaware, Mississippi, Montana, North Dakota, New Hampshire, South Dakota, Wyoming)
- Only 8 states had formal burn center designation requirements
- 6 additional states recognized (licensed/certified/approved) burn centers without formal designation

#### Burn Center Capabilities

- 48 (35.6%) adult-only burn centers
- 17 (12.6%) pediatric-only burn centers
- 70 (51.9%) combined adult and pediatric burn centers

#### 10-Year Trends (2012-2022)

- 12 burn centers removed (10 closed, 2 lost ABA recognition)
- 18 burn centers added
- **Net increase of 7 burn centers** over the decade
- 14 burn centers gained ABA verification; 1 lost it

#### Verified vs. Designated Burn Centers

- No significant differences in hospital size, ER volume, hospital beds, or burn ICU beds
- Significant differences found in discharge rates and all revenue categories:
  - Verified median total revenue: **$994M** vs. designated: **$652M**
  - Verified median inpatient revenue: **$2.1B** vs. designated: **$1.3B**

#### ABA Data Inconsistencies

- Variability found in 18 burn centers across 15 states between ABA's own Burn Center Directory and Regional Map
- ABA sources reported different totals: 76 (online), 74 (email), and 72 (podium presentation) verified burn centers

### Conclusion

- NIRD is the first comprehensive database of all US burn and level I/II trauma centers.
- The ABA's online burn center directory is outdated and inconsistent.
- Non-verified burn centers show similar capacity to verified ones and may already meet verification requirements.
- States should support regional burn care development and seek national-level ABA verification.
- Only ~250 dedicated burn surgeons exist in the US, and burn centers operate at or over capacity daily.
- NIRD can serve as a foundation for real-time patient routing tools and improved transfer operations.

---

## Cross-Paper Themes & Relevance to Heatmap Project

1. **Geographic gaps in burn care access**: 8 states have no burn centers at all, and 11 states lack ABA-verified centers. This presents a clear use case for geographic/heatmap visualization of burn care deserts.
2. **Underreporting and data fragmentation**: Burn injury incidence ranges from 30,135 (ABA BISR) to 698,555 (claims data) depending on the source. A unified visualization could highlight where data gaps are most severe.
3. **Resource allocation inequality**: The significant revenue differences between verified and non-verified centers, combined with the uneven geographic distribution, suggest opportunities for heatmap-based analysis of resource allocation.
4. **Disaster preparedness**: With burn centers operating at or over capacity and limited to ~5 large admissions during disasters, mapping real-time capacity could be critical for emergency response planning.
5. **Economic burden**: Annual burn care costs exceed $4.1B in medical costs alone (2020), with an estimated 600,000 emergent care cases per year. Visualizing cost and incidence by region could support advocacy for increased NIH funding.

