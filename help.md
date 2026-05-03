# Technical Reference & User Guide

### Solar Harvesting Logic
This app calculates the daily average energy harvest based on:
* **PSH (Peak Sun Hours):** Monthly averages sourced from NREL/NLR.
* **AOI (Angle of Incidence):** Fresnel reflection and cosine losses for vertical glass.
* **IR Cut Loss:** Spectral attenuation from Low-E window coatings.
* **Window & PDLC Frame Geometry**

### Azimuth Guide
* **0°**: North
* **90°**: East
* **180°**: South (Ideal for Northern Hemisphere)
* **270°**: West

Note: Only when changing Azimuth (the window's facing direction), the data based on this azimuth is fetched from NREL site. The process takes about 1min

### Window Geometry
* A 2D representation of the window fitted with the PDLC and the borders.
* The combined borders area is assumed to include PV cells flushed with the window's surface.
* The battery, or two, will be part of the bottom border and if selected, also part of the top border.

#### Understanding Glass Extinction ($K$)
The **Extinction Coefficient ($K$)** represents how much solar energy is absorbed by the glass material itself as light passes through it. A higher $K$ value means less light reaches the PV cells.

*   **Low-Iron Glass ($K \approx 4$):** Often called "Solar Glass." It is highly transparent and lacks the green tint seen in standard glass. This is ideal for maximum energy harvest.
*   **Standard Clear Float Glass ($K \approx 32$):** Common window glass. The iron impurities cause a slight green tint and absorb significantly more light than solar glass.
*   **Tinted Glass ($K > 100$):** Specifically designed to reduce solar heat gain, which significantly penalizes PV performance.

### Interactive Map
The map gradient colors represent the daily energy harvesting potential, The gradient transitions from Red (Insufficient) to Green (Sufficient) based on the expected PDLC daily film energy usage. This provides an immediate "at-a-glance" status for every state without needing to hover.

When hovering over the map, A blob will show:
* State name
* Is harvesting sufficient?
* Energy collected per day
* Peak sun hours

## Equations

The mathematical model and physical assumptions used in the solar window harvesting simulation.

---

### 1. Solar Geometry & Angle of Incidence (AOI)
The most critical factor for vertical PV performance is the **Angle of Incidence ($\theta$)**. This is the angle between the sun's rays and the window's surface normal.

The geometric relationship is defined as:

$$
\cos(\theta) = \sin(\alpha_s) \cos(\beta) + \cos(\alpha_s) \sin(\beta) \cos(\psi_s - \psi)
$$

**Where:**
* $\alpha_s$: Solar elevation angle.
* $\beta$: Surface tilt ($90^\circ$ for a vertical window).
* $\psi_s$: Solar azimuth angle.
* $\psi$: Window azimuth (User-defined; $180^\circ$ is South).

---

### 2. Optical Transmission & Fresnel Losses
Because the PV cells are behind glass, not all light reaching the window surface reaches the cells. The **Physical Incident Angle Modifier (IAM)** models the reduction in transmission due to reflection and absorption as the incident angle increases.

The transmission $T(\theta)$ is defined by the combination of Fresnel reflection and the Beer-Lambert law:
$$
T(\theta) = \tau_{refl}(\theta) \cdot \tau_{abs}(\theta)
$$

**Where:**
* **Snell's Law:** $\theta_r = \arcsin\left(\frac{1}{n} \sin \theta\right)$ defines the refraction angle inside the glass ($n \approx 1.526$).
* **Fresnel Reflection:** $\tau_{refl}(\theta) = 1 - \frac{1}{2} \left( \frac{\sin^2(\theta_r - \theta)}{\sin^2(\theta_r + \theta)} + \frac{\tan^2(\theta_r - \theta)}{\tan^2(\theta_r + \theta)} \right)$
* **Beer-Lambert Absorption:** $\tau_{abs}(\theta) = e^{-\frac{K \cdot L}{\cos \theta_r}}$ (governed by extinction coefficient $K$ and thickness $L$).

The final modifier used in calculations is normalized relative to normal incidence ($0^\circ$):
$$
F(\theta) = \frac{T(\theta)}{T(0)}
$$

---

### 3. PV Active Area Geometry
The total active PV area ($A_{PV}$) is the sum of the border regions where the transparent solar cells are integrated:

$$
A_{PV} = A_{top} + A_{bot} + A_{sides}
$$

**Where:**
* $A_{top} = W_{window} \times H_{top\_border}$
* $A_{bot} = W_{window} \times H_{bot\_border}$
* $A_{sides} = (H_{window} - H_{top\_border} - H_{bot\_border}) \times W_{side\_border} \times 2$

---

### 4. Energy Harvesting Equation
The final daily energy harvested ($E_{harvest}$) in Watt-hours ($Wh$) is the product of the available solar resource and the system efficiency chain:

$$
E_{harvest} = (PSH \times STC) \cdot A_{PV} \cdot \eta_{cell} \cdot F(\theta) \cdot (1 - L_{IR}) \cdot (1 - L_{soil}) \cdot (1 - L_{sys})
$$

**Where:**
* $PSH$: Peak Sun Hours (derived from NREL monthly averages).
* $A_{PV}$: Total active cell area ($m^2$).
* $\eta_{cell}$: Rated cell efficiency (e.g., $0.22$).
* $L_{IR}$: Spectral loss from the Low-E / IR-cut window coating.
* $L_{soil}$: Soiling loss (dust, dirt, bird droppings).
* $L_{sys}$: System losses (wiring, mismatch, conversion).
* $STC$: Standard Test Condition solar irradiance (1000 W/m^2)

---

### 5. Battery Storage & Volume Math
The system assumes the battery is integrated into the window's top and bottom frame borders.

**Volume ($V_{batt}$) in Liters:**

$$
V_{batt} = (Area_{top} + Area_{bot}) \times Thickness
$$

**Energy Capacity ($E_{batt}$) in Watt-hours:**

$$
E_{batt} = V_{batt} \times \rho_{density}
$$

**Where:**
* $Area$: Border area in $m^2$.
* $Thickness$: Frame depth in $m$.
* $\rho_{density}$: Battery energy density in $Wh/L$.

---

### 6. Load & Autonomy
To determine if the window is self-sustaining, we calculate the daily load of the PDLC smart film ($E_{load}$):

$$
E_{load} = A_{film} \times P_{film} \times t_{active}
$$

**Autonomy (Days):**

$$
Days = \frac{E_{batt}}{E_{load}}
$$

**Sustainability Constraint:**
The system is considered autonomous if:

$$
E_{harvest(min)} \geq E_{load}
$$