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
Because the PV cells are behind glass, not all light reaching the window surface reaches the cells. We use a **Physical Incident Angle Modifier (IAM)** to model Fresnel reflection:

$$
F(\theta) = \frac{T(\theta)}{T(0)}
$$

As $\theta$ increases beyond $60^\circ$, the reflection coefficient increases sharply, reducing the effective energy reaching the PV cell.

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
E_{harvest} = (PSH \times 1000) \cdot A_{PV} \cdot \eta_{cell} \cdot F(\theta) \cdot (1 - L_{IR})
$$

**Where:**
* $PSH$: Peak Sun Hours (derived from NREL monthly averages).
* $A_{PV}$: Total active cell area ($m^2$).
* $\eta_{cell}$: Rated cell efficiency (e.g., $0.22$).
* $L_{IR}$: Spectral loss from the Low-E / IR-cut window coating.

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