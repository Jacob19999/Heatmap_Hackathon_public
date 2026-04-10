# Burn Equity Index — Printable Script
_Generated from `Presentation/BEI_Presentation.pptx`. Presenter and timing are taken from the first line of speaker notes._

---

## Slide 1

**Presenter:** Madeline
**Timing (from notes):** 0:00 – 0:25 (25s)

### On-slide text

- Burn Equity Index
- Measuring Structural Burn-Care Access Inequity Across America
- Challenge Area 3: Equitable Access
- Team 15  |  Jacob Tang  ·  Madeline Rose Johnson  ·  Yisihaq Yemiru  ·  Mashfika
- HeatMap Hackathon  |  American Burn Association  ·  BData

### Speaker notes

Good morning everyone. Picture this -- a child reaches for a pot on the stove. In that split second, everything changes. The question that matters most is: how quickly can that child reach specialized burn care? Today we'll show you that the answer depends almost entirely on where you live. I'm Madeline, and together with Jacob, we're presenting the Burn Equity Index.

---

## Slide 2

**Presenter:** Madeline
**Timing (from notes):** 0:25 – 1:10 (45s)

### On-slide text

- The Problem: Access Is Not Equal
- Burn care is one of the most regionalized specialties in medicine
- Burn Centers (US)
- 136
- Total Burn Beds
- 2,080
- US Population
- 331M
```
States with No
Burn Center
```

- 8
- Hennepin County, MN
- Pop: 1.27 million  |  BEI: 0
```
10 min to a verified burn center
Direct access, full pediatric capability
Multiple facilities within 30 min
```

- Kittson County, MN
- Pop: 4,191  |  BEI: 99.6
```
8+ hours to nearest burn center
No stabilization within 30 min
Zero pediatric burn access
```


### Speaker notes

There are only 136 verified burn centers and about 2,000 burn beds for 331 million Americans. Eight states have no burn center at all.

But the numbers only tell part of the story. In Hennepin County -- that's Minneapolis -- a burn patient reaches world-class care in 10 minutes. BEI score: zero. Perfect access. Now jump to Kittson County in the far northwest corner of the same state. Same Minnesota. But here, a burn patient faces an 8-hour journey, and the BEI is 99.6 -- nearly the worst score possible. That's the gap we set out to measure. Jacob, take us through how we did it.

---

## Slide 3

**Presenter:** Jacob
**Timing (from notes):** 1:10 – 1:45 (35s)

### On-slide text

- Our Use Case: Equitable Access
- Given where people live and where burn-care resources sit, how equitably is the system structured?
- 1
- Quantify
```
Build a composite equity index at
census-tract resolution across
the entire United States.
```

- 2
- Visualize
```
Create an interactive dashboard
for stakeholders to explore access
from national to neighborhood level.
```

- 3
- Act
```
Identify high-burden communities
and provide actionable, evidence-
based recommendations.
```


### Speaker notes

Thanks, Madeline. I'm Jacob, and I led the technical build. Our primary use case is Equitable Access -- we're not predicting who gets burned or rating hospital quality. We're mapping structural inequity.

Three goals. First, quantify access with a rigorous index at census-tract resolution. Second, visualize it through an interactive dashboard anyone can use. Third, turn those findings into specific, actionable recommendations. Let me show you how the index works.

---

## Slide 4

**Presenter:** Jacob
**Timing (from notes):** 1:45 – 2:25 (40s)

### On-slide text

- The Burn Equity Index
- BEI  =  100  ×  ( 0.25·S  +  0.30·T  +  0.20·P  +  0.25·C )
- Four pillars -- each captures a distinct dimension of structural access.
- S
```
Supply
Scarcity
```

- Weight: 25%
```
How scarce is specialized
burn-care supply nearby?
```

- T
```
Timely
Access
```

- Weight: 30%
```
How long to reach
definitive burn care?
```

- P
```
Pediatric
Access
```

- Weight: 20%
```
Can children reach
pediatric burn care?
```

- C
```
Capacity
Gap
```

```
Are there enough
burn beds nearby?
```

- 0 = Best Access
- 100 = Worst Access

### Speaker notes

The BEI scores every census tract in the country from zero to a hundred. Zero means excellent structural access; a hundred means severe barriers.

It blends four pillars. S captures how scarce specialized supply is near a community. T -- our heaviest weight at 30 percent -- measures how long it takes to reach definitive care, including transfer pathways. P isolates pediatric access, because children need different facilities. And C looks at whether there are enough burn beds for the surrounding population. Each one is a distinct lens on the same system. Let me walk through the key ones.

---

## Slide 5

**Presenter:** Jacob
**Timing (from notes):** 2:25 – 2:55 (30s)

### On-slide text

- S
- Specialized Supply Scarcity  (25%)
- How scarce is specialized burn-care supply around each community?
- Facility Capability Weights
- ABA-Verified Burn Center
- 1.00
- State-Designated Burn Center
- 0.85
- Burn-Capable (Non-Verified)
- 0.50
- Trauma-Only Stabilization
- 0.20
- How It Works (E2SFCA)
```
1. Compute each facility's supply-to-
    demand ratio (capability weight
    divided by nearby population).
```

```
2. For each tract, sum ratios of
    all reachable facilities.
```

```
3. Normalize nationally, then flip:
    high value = scarce supply.
```

- Distance Decay Function
- ≤ 30 min
- 1.00  Full access
- 31–60 min
- 0.60  Reduced
- 61–90 min
- 0.30  Marginal
- > 90 min
- 0.00  Out of reach

### Speaker notes

Supply uses a two-step floating catchment area method. It's a well-established spatial accessibility framework, and here's how it works in plain terms.

Each facility gets a capability weight -- a verified burn center is 1.0, a trauma-only site is 0.20. We then look at how many people live within driving range, using a step-decay function: full weight within 30 minutes, partial out to 90, and zero beyond. For each tract, we add up the ratios of all hospitals it can reach. Then we normalize and flip, so a high score means scarce supply.

---

## Slide 6

**Presenter:** Jacob
**Timing (from notes):** 2:55 – 3:45 (50s)

### On-slide text

- T
- Timely Access Burden  (30% -- Highest Weight)
- Models the real-world tiered burn care system, not just distance to the nearest center.
- A
- Direct Path
- T(dir)
```
Drive from the tract to the
nearest definitive burn center.
```

- B
- Transfer Path
- T(trans)
```
Drive to stabilization hospital,
add 45-min transfer penalty,
then transfer to burn center.
```

- C
- System Time
- T(sys)
```
Whichever is faster -- direct
or stabilize-then-transfer.
```

- Tier Penalty:  Δ = max(0, T_stab − 30 min)
- We also penalize tracts where even first-line stabilization is more than 30 minutes away. Final score: 75% system time + 25% tier penalty. This captures both the journey and the safety net.

### Speaker notes

This is our heaviest-weighted pillar, because in burn care, minutes matter. And what sets our approach apart is that we model how the system actually works.

We compute three pathways. Path A is direct -- just the drive time to the nearest burn center. Path B is the transfer route -- go to the nearest stabilization hospital, add a 45-minute structural transfer penalty, then continue to a definitive center. Path C picks whichever is faster.

On top of that, we add a tier penalty. If even your nearest emergency room is more than 30 minutes away, that compounds the problem. So the final score blends 75 percent system travel time with 25 percent tier penalty -- capturing both the journey and the safety net.

---

## Slide 7

**Presenter:** Jacob
**Timing (from notes):** 3:45 – 4:20 (35s)

### On-slide text

- P
- Pediatric Access Gap  (20%)
```
Same method as Supply, but using
pediatric-capable facilities and
child population.
```

- Pediatric ABA-Verified
- 1.00
- Pediatric State-Designated
- 0.85
- Peds Trauma + Burn Capable
- 0.60
- Pediatric Stabilization Only
- 0.25
- Why a separate pillar?
```
Pediatric burns need different expertise
and equipment. A community can have
adult access but zero pediatric capability.
```

- C
- Structural Capacity Gap  (25%)
```
Measures burn-bed adequacy relative
to surrounding population, weighted
by distance.
```

- Effective Beds = BURN_BEDS × u
```
u = capacity utilization factor
Baseline: u = 1.0 (structural)
Sensitivity: u = 0.75 (conservative)
```

- The national picture
```
2,080 total US burn beds
= 0.63 beds per 100,000 people
Concentrated in urban corridors
```


### Speaker notes

The Pediatric pillar uses the same framework but calibrated for children -- weighting facilities by pediatric burn capability and using child population as the denominator. We gave it its own pillar because a community might have decent adult access but nothing for kids.

Capacity measures bed adequacy. Across the whole US, there are just 2,080 burn beds -- that's 0.63 per hundred thousand people. And those beds cluster in urban centers, so rural communities are doubly disadvantaged: they're both far away and under-bedded.

---

## Slide 8

**Presenter:** Jacob
**Timing (from notes):** 4:20 – 4:45 (25s)

### On-slide text

- Data Sources & Integration
- Every source is public or challenge-provided -- fully reproducible
- NIRD
```
635 facilities with burn
designation and bed counts
```

- US Census (ACS)
```
84,000+ tract boundaries
and population data
```

```
OpenStreetMap
+ Valhalla
```

```
Real road-network travel
times, not estimates
```

- RUCA Codes
```
Rural-urban classification
for every census tract
```

- CDC SVI
```
Social vulnerability overlay
(kept outside core BEI)
```

- FAA Airport Data
```
Heliport locations for air-
transport sensitivity
```


### Speaker notes

Every data source is either provided by the challenge or freely available. NIRD gives us 635 hospitals. Census provides tract-level population. We compute actual drive times using OpenStreetMap and a local Valhalla routing engine -- these are real road-network times, not straight-line guesses. We also layer in rural-urban classifications, social vulnerability data, and FAA airport records for our air-transport scenario. The entire pipeline is reproducible.

---

## Slide 9

**Presenter:** Madeline
**Timing (from notes):** 4:45 – 5:05 (20s)

### On-slide text

- What Does the Data Reveal?
- From method to map -- let's explore what the data shows
- MN Tracts
- 1,505
- MN Median BEI
- 23.0
```
High-Burden
(BEI ≥ 80)
```

- 155 tracts
- US Counties
- 3,144

### Speaker notes

That's the method. Now let's see what it finds. We scored 1,505 tracts across Minnesota and 3,144 counties nationwide. Minnesota's median BEI is 23 -- that sounds good. But 155 tracts score above 80. Those are communities where reaching burn care takes hours, not minutes. Let me show you on the map.

---

## Slide 10

**Presenter:** Madeline
**Timing (from notes):** 5:05 – 5:40 (35s)

### On-slide text

- Minnesota: Burn Equity Index Map
- Tract-level BEI scores  |  Interactive Dashboard
```
[ DASHBOARD SCREENSHOT ]
MN Map Page -- BEI choropleth with facility markers
```

- Twin Cities Metro
```
BEI: 0 -- 2
Multiple burn centers
within 15 minutes
50%+ of MN population
```

- Northwest MN
```
BEI: 90 -- 100
No burn center for
hundreds of miles
8+ hour travel time
```


### Speaker notes

[USE LIVE DASHBOARD OR SCREENSHOT]

Here's Minnesota, colored by BEI. The Twin Cities metro shows green -- near-zero scores. Half the state's population lives within minutes of a burn center. Now look at the northwest corner. Deep red. Scores above 90. Kittson, Roseau, Marshall counties. No burn center for hundreds of miles. The transition isn't gradual. It drops off like a cliff.

---

## Slide 11

**Presenter:** Madeline
**Timing (from notes):** 5:40 – 6:25 (45s)

### On-slide text

- Minnesota County Stories
- Same state, vastly different realities
- Best Access
- Hennepin County
- Minneapolis
- BEI: 0.0
```
10.6 min to burn center
Direct access pathway
All 4 pillars score 0.00
Pop: 1.27 million
```

- Moderate Burden
- Blue Earth County
- Mankato
- BEI: 58.5
```
88 min to burn center
S: 1.00  T: 0.14  C: 1.00
Supply & capacity gaps
Pop: 69,022
```

- Severe Burden
- Beltrami County
- Bemidji
- BEI: 90.4
```
8+ hrs to burn center
Transfer pathway only
S, T, and C all maxed
Pop: 46,274
```


### Speaker notes

Three counties, one state.

Hennepin -- Minneapolis. BEI: zero. You're 10 minutes from definitive care. Every pillar scores zero. That's what good access looks like.

Blue Earth -- Mankato. A university town, about 69,000 people. BEI: 58.5. You're an hour and a half from a burn center by road. The supply and capacity pillars are both maxed out -- there's simply nothing nearby. But the timely-access score is low because the drive is technically still feasible. A community like this can look fine on a map but is structurally underserved.

Beltrami -- Bemidji. BEI: 90.4. Eight hours to a burn center. Transfer pathway only. Supply, time, and capacity all maxed out. That is structural isolation.

---

## Slide 12

**Presenter:** Madeline
**Timing (from notes):** 6:25 – 6:55 (30s)

### On-slide text

- The Rural–Urban Divide
```
[ DASHBOARD SCREENSHOT ]
MN rural vs urban box plot
(mn_03_rural_urban_gap.png)
```

- Median Travel Time
- Urban:
- 19 min
- Rural:
- 124 min
- 6.5x Longer
```
Rural residents travel 6.5 times
farther to reach burn care.
```

```
30.5% of MN tracts are rural
Only 50.1% of Minnesotans
can reach care in 30 min
```


### Speaker notes

This chart puts the disparity in sharp relief. Urban Minnesotans: 19-minute median. Rural Minnesotans: 124 minutes -- over two hours, and that's the median, so half face even longer trips. A 6.5x gap within one state. And nearly a third of the state's tracts are classified as rural. For burns, where that first hour can determine whether a patient needs grafts or makes a full recovery, two hours is not just inconvenient. It changes outcomes.

---

## Slide 13

**Presenter:** Madeline
**Timing (from notes):** 6:55 – 7:30 (35s)

### On-slide text

- National: County-Level BEI Map
- 3,144 counties  |  331 million Americans  |  Interactive Dashboard
```
[ DASHBOARD SCREENSHOT ]
USA County Map Page -- Full national BEI choropleth
```

- Worst States (Avg BEI)
```
AK: 99.7   ND: 99.0
MT: 96.5   SD: 96.4
WY: 83.4   NV: 83.3
```

- Best States (Avg BEI)
```
NJ: 10.0   RI: 29.5
MD: 29.8   MA: 31.0
```

```
8 States -- Zero Burn
Centers
```

```
AK, DE, MS, MT,
ND, NH, SD, WY
```


### Speaker notes

[SWITCH TO NATIONAL DASHBOARD VIEW IF POSSIBLE]

Now the full country. The coasts light up green -- New Jersey, Maryland, Massachusetts, all below 31. The interior is a different story. Great Plains, Mountain West, rural Deep South -- all high-burden. Alaska and North Dakota average above 99. Eight states have no burn center at all. If you're burned in Montana, you have to leave the state. These aren't empty places -- Flathead County, Montana: 106,000 residents, BEI of 100.

---

## Slide 14

**Presenter:** Jacob
**Timing (from notes):** 7:30 – 8:00 (30s)

### On-slide text

- State Rankings & Coverage Gaps
```
[ DASHBOARD SCREENSHOT ]
State Rankings bar chart
(usa_02_state_rankings.png)
```

```
[ DASHBOARD SCREENSHOT ]
National Coverage Gap chart
(usa_03_coverage_gap.png)
```


### Speaker notes

The state rankings confirm the geographic pattern. States with vast rural areas and few burn centers sit at the bottom. But population-weighted BEI also reveals inequity in states that seem well-resourced on paper. The coverage gap chart on the right shows millions of Americans -- disproportionately in rural and tribal communities -- living more than 60 minutes from verified care. That matters clinically. The ABA's own referral guidelines stress timely transfer for major burns.

---

## Slide 15

**Presenter:** Jacob
**Timing (from notes):** 8:00 – 8:35 (35s)

### On-slide text

- What Makes BEI Different
- 1
- Tiered System Modeling
```
Models the real-world stabilize-then-
transfer pathway with explicit transfer
penalties and tier gap detection.
```

- 2
- Multi-Scenario Transport
```
Ground-only baseline plus ground-
plus-air sensitivity using FAA data.
Published as scenario analysis.
```

- 3
- Four-Pillar Composite
```
Supply, timeliness, pediatrics, and
capacity each address a distinct
clinical dimension. Fully transparent.
```

- 4
- Interactive Dashboard
```
Any stakeholder can explore access
patterns from national overview down
to individual tracts. No coding needed.
```


### Speaker notes

Four things set the BEI apart. First, we model the real tiered care system -- not just nearest-facility distance, but the full stabilize-and-transfer pathway with explicit penalties.

Second, we run multi-scenario transport. Ground-only as the reproducible baseline, plus a ground-plus-air sensitivity scenario built on real FAA infrastructure data.

Third, four pillars that each address a different clinical dimension. And fourth, an interactive dashboard that makes all of this accessible to anyone -- clinicians, planners, or the public. No technical expertise needed.

---

## Slide 16

**Presenter:** Madeline
**Timing (from notes):** 8:35 – 9:20 (45s)

### On-slide text

- Impact & Recommendations
- From data to decisions
- Telemedicine Triage
- Referral
```
Deploy tele-burn consultation in
high-BEI regions. Research shows
94% accuracy in remote surgical
determination.
```

```
Strategic Facility
Placement
```

- Equitable Access
```
Use hotspot clusters to identify
where new burn-capable facilities
would have the greatest impact.
NW Minnesota is a clear candidate.
```

```
Air Transport
Investment
```

```
Target air-ambulance resources
where ground BEI exceeds 80 but
air scenario shows 5+ point gain.
Existing heliports are underused.
```

- Policy Planning Tool
```
Integrate BEI into state health
department planning and ABA
verification processes. Open-source
and fully reproducible.
```


### Speaker notes

So what do we do with this data? Four things.

Telemedicine. In places like Beltrami County, a tele-burn consult can guide treatment while the patient is in transit. Research shows 94 percent accuracy in remote surgical assessment.

Facility placement. Our hotspot analysis shows exactly where a new burn-capable site would close the biggest gaps. Northwest Minnesota is the clear candidate.

Air transport. Our analysis finds corridors where adding air access drops the BEI significantly. Existing heliports in those areas are underused.

And the BEI itself becomes the planning tool. Open-source, reproducible, and ready for state health departments and the ABA to adopt.

---

## Slide 17

**Presenter:** Jacob
**Timing (from notes):** 9:20 – 9:50 (30s)

### On-slide text

- Limitations & Future Directions
- National routing at county level
- Masks variation within large rural counties. MN uses ideal tract-level routing. Full US tract-level needs a high-memory server.
- Florida data gap
- 67 FL counties absent due to a routing batch error. Pipeline issue, not methodological -- the formula applies identically.
- Air scenario is structural
- An accessibility estimate, not an operational prediction. Real-time weather and dispatch are out of scope.
- Static capacity model
- Uses structural bed counts, not real-time occupancy. Live bed-census integration is a clear next step.
- Next:  Tract-level national routing  |  Real-time bed feeds  |  Temporal BEI  |  State health planning integration

### Speaker notes

We want to be upfront about limitations. National analysis is at county level, which can mask variation in large rural counties -- Minnesota uses full tract-level routing. Florida's counties are absent due to a routing error in our pipeline, not a methodology gap. Our air scenario is a structural estimate, not an operational forecast. And bed capacity is structural, not real-time.

Going forward: tract-level national routing, live bed census feeds, temporal BEI that captures seasonal patterns, and direct integration with state planning systems.

---

## Slide 18

**Presenter:** Madeline
**Timing (from notes):** 9:50 – 10:45 (55s)

### On-slide text

- Every Minute Matters
```
The Burn Equity Index gives us a shared language
to see, measure, and act on the structural gaps
that separate 10 minutes from 10 hours.
```

- Hennepin County
- BEI: 0
- Same State
- 10m vs 8h
- Kittson County
- BEI: 99.6
- The gap is structural. What's structural can be changed. Change starts with data.

### Speaker notes

Remember that child at the stove. In Hennepin County, they're in a burn unit in 10 minutes. In Kittson County -- same state -- eight hours.

We've scored every county in America and every census tract in Minnesota. The Burn Equity Index gives clinicians, planners, and policymakers one number that captures what used to take months to assess.

The gap is structural. But structural means it can be changed. A new facility, a telemedicine link, an air corridor -- each one shifts the score. And every score represents real families. That's what the BEI does.

---

## Slide 19

**Presenter:** Both
**Timing (from notes):** 10:45 – 10:59 (14s)

### On-slide text

- Thank You
- Team 15  —  Burn Equity Index  —  Challenge Area 3
- JT
- Jacob Tang
```
Technical Lead
Pipeline & Methodology
```

- MR
- Madeline Rose Johnson
```
Analytics & Presentation
MS Data Science
```

- YY
- Yisihaq Yemiru
```
Research &
Data Integration
```

- M
- Mashfika
```
Analysis &
Visualization
```

- American Burn Association  ·  BData  ·  HealthcareMN  ·  MinneAnalytics  ·  University of Minnesota
- Data: NIRD  ·  US Census  ·  OpenStreetMap  ·  Valhalla  ·  RUCA  ·  CDC SVI  ·  FAA
- Interactive Dashboard Available

### Speaker notes

MADELINE: Thank you for your time. We'd love to take questions, and the interactive dashboard is available for you to explore.

JACOB: The full pipeline, methodology, and dashboard are open and reproducible. Thank you.

[END -- TOTAL: 10:59]

=== SCRIPT SUMMARY ===
~1,600 words | 10:59

JACOB: Slides 3-8, 14-15, 17 (~5:10)
MADELINE: Slides 1-2, 9-13, 16, 18-19 (~5:49)

=== RUBRIC COVERAGE ===
I. Clinical/Business Use Case (15 pts)
   1. Use Case ID: Equitable Access (Slide 3)
   2. Insights: County stories, rural-urban gap (Slides 10-14)
   3. Impact: Recommendations with stakeholder relevance (Slide 16)

II. Analytic/Methodologic Quality (15 pts)
   4. Methods: E2SFCA, tiered routing, normalization (Slides 4-7)
   5. Innovation: Tiered system, multi-scenario, dashboard (Slide 15)
   6. Data Integration: 6 public/challenge sources (Slide 8)

III. Presentation & Communication (15 pts)
   7. Storytelling: Human hook, county stories, bookend close
   8. Visual Quality: Dashboard, CVD-safe colors, dual presenters
   9. Actionability: 4 concrete, feasible recommendations (Slide 16)
