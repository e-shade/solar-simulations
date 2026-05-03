# 📖 User Guide & Technical Reference

### ☀️ Solar Harvesting Logic
This app calculates the daily average energy harvest based on:
* **PSH (Peak Sun Hours):** Monthly averages sourced from NREL/NLR.
* **AOI (Angle of Incidence):** Fresnel reflection and cosine losses for vertical glass.
* **IR Cut Loss:** Spectral attenuation from Low-E window coatings.

### 🔋 Battery Calculations
The battery is assumed to be housed within the **Top and Bottom borders** of the window frame.
$$Volume (L) = \frac{(TopArea + BottomArea) \times Thickness}{1,000,000}$$

### ⚙️ Azimuth Guide
* **0°**: North
* **90°**: East
* **180°**: South (Ideal for Northern Hemisphere)
* **270°**: West