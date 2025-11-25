import streamlit as st
import math
import numpy as np
import pandas as pd

st.title("Steel Pipe Stress Calculator")
st.markdown("""
This tool calculates actual and allowable stresses for a steel pipe under axial load, bending, and external/internal pressure, and performs unity checks.
""")

# ---- INPUTS ----
st.header("Pipe Properties")
D = st.number_input("Outer Diameter D (in)", min_value=0.01)
t = st.number_input("Wall Thickness t (in)", min_value=0.001)
E = st.number_input("Elastic Modulus E (psi)", value=29000000)
SMYS = st.number_input("Specified Minimum Yield Strength (SMYS) (psi)", min_value=1.0)
poisson = st.number_input("Poisson's Ratio", value=0.3)

st.header("Axial Force")
P = st.number_input("Axial Force P (lbf)")
force_type = st.radio("Is the force tensile or compressive?", ["Tensile", "Compressive"])

st.header("Curved Section")
R = st.number_input("Bending Radius R (in)", min_value=0.01)

st.header("Pressure Conditions")
slurry_weight_lbft3 = st.number_input("Slurry Weight (lb/ft³)", min_value=0.01)
depth = st.number_input("Depth at point of interest (ft)", min_value=0.01)
internal_pressure = st.number_input("Internal Pressure (psi)", min_value=0.0)

# ---- DERIVED VALUES ----
A = math.pi / 4 * (D**2 - (D - 2*t)**2)  # in^2
r2 = D / 2
r1 = r2 - t
I = math.pi / 4 * (r2**4 - r1**4)  # in^4

# ---- ACTUAL STRESSES ----
f_axial = abs(P) / A if A else 0
f_bending = (E * D) / (24 * R) if R else 0
ppg = slurry_weight_lbft3 / 8.34
external_pressure = (ppg * depth) / 19.25
delta_p = external_pressure - internal_pressure
f_hoop = (delta_p * D) / (2 * t) if t else 0

# ---- ALLOWABLE STRESSES ----
F_t = 0.9 * SMYS

D_over_t = D / t if t else float('inf')
Fb = 0
if D_over_t <= (1500000 / SMYS):
    Fb = 0.75 * SMYS
elif (1500000 / SMYS) < D_over_t <= (3000000 / SMYS):
    Fb = (0.84 - (1.74 * SMYS * D) / (E * t)) * SMYS
elif (3000000 / SMYS) < D_over_t <= 300000:
    Fb = (0.72 - (0.58 * SMYS * D) / (E * t)) * SMYS

Fhe = 0.88 * E * (t / D)**2 if D else 0
if Fhe <= 0.55 * SMYS:
    Fhc = Fhe
elif Fhe <= 1.6 * SMYS:
    Fhc = 0.45 * SMYS + 0.18 * Fhe
elif Fhe <= 6.2 * SMYS:
    Fhc = (1.31 * SMYS) / (1.15 + (SMYS / Fhe))
else:
    Fhc = SMYS

# ---- ALLOWABLE COMPRESSION STRESS ----
K = 1
l = 39.37  # 1 meter in inches
r = math.sqrt(I / A) if A else 0
Kl_over_r = (K * l) / r if r else float('inf')
Cc = math.sqrt((2 * math.pi**2 * E) / SMYS) if SMYS else 0
Fe_prime = (12 * math.pi**2 * E) / (23 * (Kl_over_r**2)) if Kl_over_r else 0

if Kl_over_r < Cc:
    Fa = ((1 - (Kl_over_r**2) / (2 * Cc**2)) * SMYS) / (5/3 + 3 * Kl_over_r / (8 * Cc) - (Kl_over_r**3) / (8 * Cc**3))
else:
    Fa = Fe_prime

# ---- ADDITIONAL SAFETY FACTORS AND TERMS ----
C = 0.3
Fxe = (2 * C * E * t) / D if D else 0
Faa = Fxe / 2  # SFx = 2
Fha = Fhe / 2  # SFh = 2
SFx = 2.0
SFb = SMYS / Fb if Fb else float('inf')
SFh = 2.0
fx = f_axial + f_bending + 0.5 * f_hoop

if D_over_t <= 60:
    Fxc = SMYS
else:
    Fxc_calc = SMYS * (1.64 - 23 * (D_over_t)**0.25)
    Fxc = min(Fxc_calc, Fxe)

# ---- UNITY CHECKS ----
unity1 = unity2 = unity_compression1 = unity_compression2 = unity_compression3 = None
unity_compression4 = unity_compression5 = unity_compression6 = None

if force_type == "Tensile":
    unity1 = (f_axial / (0.6 * SMYS)) + (f_bending / Fb) if Fb else float('inf')
    A_term = ((f_axial + f_bending - 0.5 * f_hoop) * 1.25) / SMYS
    B_term = (1.5 * f_hoop) / Fhc if Fhc else float('inf')
    unity2 = A_term**2 + B_term**2 + 2 * poisson * abs(A_term) * B_term

if force_type == "Compressive":
    Cm = 0.85
    unity_compression1 = (f_axial / Fa) + (Cm * f_bending) / (1 - (f_axial / Fe_prime)) / Fb if Fb and Fe_prime else float('inf')
    unity_compression2 = (f_axial / (0.6 * SMYS)) + (f_bending / Fb) if Fb else float('inf')
    if Fa and Fb:
        unity_compression3 = (f_axial / Fa) + (f_bending / Fb)
    unity_compression4 = ((f_axial + 0.5 * f_hoop) * SFx / Fxc) + (f_bending * SFb / SMYS)
    unity_compression5 = SFh * f_hoop / Fhc if Fhc else float('inf')
    if fx > 0.5 * Fha:
        unity_compression6 = ((fx - 0.5 * Fha) / (Faa - 0.5 * Fha)) + (f_hoop / Fha)**2 if (Faa - 0.5 * Fha) != 0 else float('inf')

# ---- OUTPUT TABLES ----
actual_stress_data = {
    "Stress Type": ["Axial Stress", "Bending Stress", "Hoop Stress"],
    "Value (psi)": [round(f_axial, 2), round(f_bending, 2), round(f_hoop, 2)]
}
st.subheader("Actual Stresses")
st.table(pd.DataFrame(actual_stress_data))

allowable_types = ["Tensile (Ft)", "Bending (Fb)", "Hoop Buckling (Fhc)"]
allowable_values = [round(F_t, 2), round(Fb, 2), round(Fhc, 2)]
if force_type == "Compressive":
    allowable_types.append("Compressive (Fa)")
    allowable_values.append(round(Fa, 2))

st.subheader("Allowable Stresses")
st.table(pd.DataFrame({
    "Allowable Stress Type": allowable_types,
    "Value (psi)": allowable_values
}))

safety_factors = {
    "Stress Type": [],
    "Allowable (psi)": [],
    "Actual (psi)": [],
    "Safety Factor": []
}
if f_axial > 0:
    safety_factors["Stress Type"].append("Axial")
    val = F_t if force_type == "Tensile" else Fa
    safety_factors["Allowable (psi)"].append(round(val, 2))
    safety_factors["Actual (psi)"].append(round(f_axial, 2))
    safety_factors["Safety Factor"].append(round(val / f_axial, 2))

if f_bending > 0:
    safety_factors["Stress Type"].append("Bending")
    safety_factors["Allowable (psi)"].append(round(Fb, 2))
    safety_factors["Actual (psi)"].append(round(f_bending, 2))
    safety_factors["Safety Factor"].append(round(Fb / f_bending, 2))

if f_hoop > 0:
    safety_factors["Stress Type"].append("Hoop")
    safety_factors["Allowable (psi)"].append(round(Fhc, 2))
    safety_factors["Actual (psi)"].append(round(f_hoop, 2))
    safety_factors["Safety Factor"].append(round(Fhc / f_hoop, 2))

st.subheader("Safety Factors (Allowable / Actual)")
st.table(pd.DataFrame(safety_factors))

if force_type == "Tensile":
    tensile_table1 = []
    if unity1 is not None:
        tensile_table1.append(("Unity Check 1 (fa/(0.6*Fy) + fb/Fb)", round(unity1, 2)))
    df_t1 = pd.DataFrame(tensile_table1, columns=["Unity Check", "Value"])
    df_t1["Status"] = df_t1["Value"].apply(lambda x: "✅ PASS" if x <= 1 else "❌ FAIL")
    st.subheader("Combined Tensile and Bending Stress")
    st.table(df_t1)

    tensile_table2 = []
    if unity2 is not None:
        tensile_table2.append(("Unity Check 2 (JD Hair: full unity with hoop)", round(unity2, 2)))
    df_t2 = pd.DataFrame(tensile_table2, columns=["Unity Check", "Value"])
    df_t2["Status"] = df_t2["Value"].apply(lambda x: "✅ PASS" if x <= 1 else "❌ FAIL")
    st.subheader("Full Unity Check of Tensile, Bending and External Hoop")
    st.table(df_t2)

if force_type == "Compressive":
    uc_combined_cb = []
    if unity_compression1 is not None:
        uc_combined_cb.append(("Unity Check 1 (fa/Fa + Cm*fb / ((1 - fa/Fe’)*Fb))", round(unity_compression1, 2)))
    if unity_compression2 is not None:
        uc_combined_cb.append(("Unity Check 2 (fa/(0.6*Fy) + fb/Fb)", round(unity_compression2, 2)))
    if unity_compression3 is not None:
        uc_combined_cb.append(("Unity Check 3 (fa/Fa + fb/Fb)", round(unity_compression3, 2)))

    df_cb = pd.DataFrame(uc_combined_cb, columns=["Unity Check", "Value"])
    df_cb["Status"] = df_cb["Value"].apply(lambda x: "✅ PASS" if x <= 1 else "❌ FAIL")
    st.subheader("Combined Compression and Bending Stress")
    st.table(df_cb)

    uc_combined_hoop = []
    if unity_compression4 is not None:
        uc_combined_hoop.append(("Unity Check 4 ((fa + 0.5fh)*SFx/Fxc + fb*SFb/Fy)", round(unity_compression4, 2)))
    if unity_compression5 is not None:
        uc_combined_hoop.append(("Unity Check 5 (SFh*fh / Fhc)", round(unity_compression5, 2)))
    if unity_compression6 is not None:
        uc_combined_hoop.append(("Unity Check 6 (fx & hoop interaction)", round(unity_compression6, 2)))

    df_hoop = pd.DataFrame(uc_combined_hoop, columns=["Unity Check", "Value"])
    df_hoop["Status"] = df_hoop["Value"].apply(lambda x: "✅ PASS" if x <= 1 else "❌ FAIL")
    st.subheader("Combined Compression and External Hoop Stress")
    st.table(df_hoop)
