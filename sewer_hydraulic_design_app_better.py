
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import griddata

st.set_page_config(page_title="Sewer Hydraulic Design Software", layout="wide")

DEFAULT_N = 0.013
MIN_V = 0.8
MAX_V = 4.0


def velocity_color(v: float) -> str:
    return "green" if MIN_V <= v <= MAX_V else "red"


def calculate_velocity(diameter: float, gradient: float, n: float, equation: str) -> float:
    if equation == "Manning":
        return (1 / n) * ((diameter / 4) ** (2 / 3)) * (gradient ** 0.5)

    elif equation == "Colebrook-White":
        return 5.74 * np.sqrt(diameter * gradient)

    elif equation == "Hazen-Williams":
        c = 130
        return 0.849 * c * ((diameter / 4) ** 0.63) * (gradient ** 0.54)

    return (1 / n) * ((diameter / 4) ** (2 / 3)) * (gradient ** 0.5)


def recalculate(df: pd.DataFrame, diameter: float, gradient: float, flow_per_pe: float, n: float = DEFAULT_N, equation: str = "Manning") -> pd.DataFrame:
    new_df = df.copy()
    new_df["Index"] = range(1, len(new_df) + 1)
    new_df["Design_Flow_m3s"] = new_df["PE_on_Line"] * flow_per_pe * new_df["Peak_Factor"]
    velocity = calculate_velocity(diameter, gradient, n, equation)
    new_df["Velocity_ms"] = velocity
    new_df["Velocity_Color"] = new_df["Velocity_ms"].apply(velocity_color)
    return new_df


def get_status_text(df: pd.DataFrame):
    min_v = float(df["Velocity_ms"].min())
    max_v = float(df["Velocity_ms"].max())

    if min_v < MIN_V:
        status = "⚠ Velocity below 0.8 m/s (sedimentation risk)"
    elif max_v > MAX_V:
        status = "⚠ Velocity above 4.0 m/s (scouring risk)"
    else:
        status = "✅ Velocity within SPAN / MSIG Vol III sewer design guideline"

    return status, min_v, max_v


def make_velocity_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Manhole"],
        y=df["Velocity_ms"],
        mode="lines+markers",
        name="Velocity",
        marker=dict(size=10, color=df["Velocity_Color"]),
        line=dict(width=2),
        hovertemplate="Manhole: %{x}<br>Velocity: %{y:.3f} m/s<extra></extra>"
    ))
    fig.add_hline(y=MIN_V, line_dash="dash", annotation_text="Min 0.8 m/s")
    fig.add_hline(y=MAX_V, line_dash="dash", annotation_text="Max 4.0 m/s")
    fig.update_layout(
        title="Sewer Velocity Along Network",
        xaxis_title="Manhole",
        yaxis_title="Velocity (m/s)",
        height=380,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def make_flow_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Manhole"],
        y=df["Design_Flow_m3s"],
        mode="lines+markers",
        name="Design Flow",
        hovertemplate="Manhole: %{x}<br>Flow: %{y:.6f} m³/s<extra></extra>"
    ))
    fig.update_layout(
        title="Design Flow Along Sewer Network",
        xaxis_title="Manhole",
        yaxis_title="Flow (m³/s)",
        height=380,
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def make_3d_chart(df: pd.DataFrame, view_name: str) -> go.Figure:
    x = df["PE_on_Line"].to_numpy(dtype=float)
    y = df["Index"].to_numpy(dtype=float)
    z = df["Design_Flow_m3s"].to_numpy(dtype=float)

    xi = np.linspace(x.min(), x.max(), 60)
    yi = np.linspace(y.min(), y.max(), 60)
    xi_grid, yi_grid = np.meshgrid(xi, yi)

    zi = griddata((x, y), z, (xi_grid, yi_grid), method="linear")
    if np.isnan(zi).any():
        zi = griddata((x, y), z, (xi_grid, yi_grid), method="nearest")

    fig = go.Figure()
    fig.add_trace(go.Surface(
        x=xi_grid,
        y=yi_grid,
        z=zi,
        colorscale="Viridis",
        colorbar=dict(title="Flow (m³/s)"),
        opacity=0.9,
        showscale=True,
        hovertemplate="PE: %{x:.0f}<br>Seq: %{y:.0f}<br>Flow: %{z:.6f} m³/s<extra></extra>"
    ))
    fig.add_trace(go.Scatter3d(
        x=x,
        y=y,
        z=z,
        mode="markers+text",
        text=df["Manhole"],
        textposition="top center",
        marker=dict(size=4),
        name="Manholes",
        hovertemplate="Manhole: %{text}<br>PE: %{x:.0f}<br>Seq: %{y:.0f}<br>Flow: %{z:.6f} m³/s<extra></extra>"
    ))

    cameras = {
        "Reset": dict(eye=dict(x=1.6, y=-1.6, z=0.8)),
        "Top": dict(eye=dict(x=0.01, y=0.01, z=2.4)),
        "Side": dict(eye=dict(x=0.01, y=-2.4, z=0.01)),
    }

    fig.update_layout(
        title="3D Sewer Flow Terrain",
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
        scene=dict(
            xaxis_title="Population Equivalent",
            yaxis_title="Manhole Sequence",
            zaxis_title="Design Flow (m³/s)",
            camera=cameras.get(view_name, cameras["Reset"]),
        ),
    )
    return fig


def validate_columns(df: pd.DataFrame):
    required = ["Manhole", "PE_on_Line", "Peak_Factor"]
    return [col for col in required if col not in df.columns]


st.title("Sewer Hydraulic Design Software")
st.caption("Interactive sewer flow and velocity checking tool")

with st.sidebar:
    st.header("Input Controls")
    uploaded_file = st.file_uploader("Upload sewer Excel file", type=["xlsx", "xls"])
    diameter = st.slider("Diameter (m)", min_value=0.15, max_value=0.45, value=0.225, step=0.005)
    gradient = st.slider("Gradient", min_value=0.001, max_value=0.01, value=0.005, step=0.0005, format="%.4f")
    flow_per_pe = st.slider("Flow per PE (m³/s)", min_value=0.0000010, max_value=0.0000100, value=0.0000027, step=0.0000001, format="%.7f")
    equation = st.selectbox("Hydraulic Equation", ["Manning", "Colebrook-White", "Hazen-Williams"])
    view_name = st.radio("3D View", ["Reset", "Top", "Side"], horizontal=True)
    st.markdown("---")
    st.write(f"Manning roughness n = **{DEFAULT_N}**")
    st.write(f"Selected equation = **{equation}**")

if uploaded_file is None:
    st.info("Upload your Excel file to start using the software.")
    st.markdown(
        "Required columns: **Manhole**, **PE_on_Line**, **Peak_Factor**.\nOptional existing columns such as **Velocity_ms** and **Design_Flow_m3s** will be recalculated."
    )
else:
    try:
        raw_df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as exc:
        st.error(f"Unable to read the uploaded Excel file: {exc}")
        st.stop()

    missing_cols = validate_columns(raw_df)
    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
        st.stop()

    result_df = recalculate(raw_df, diameter, gradient, flow_per_pe, equation=equation)
    status, min_v, max_v = get_status_text(result_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Minimum Velocity", f"{min_v:.3f} m/s")
    c2.metric("Maximum Velocity", f"{max_v:.3f} m/s")
    c3.metric("Total Design Flow", f"{result_df['Design_Flow_m3s'].sum():.6f} m³/s")

    if status.startswith("✅"):
        st.success(status)
    else:
        st.warning(status)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_velocity_chart(result_df), use_container_width=True)
    with col2:
        st.plotly_chart(make_flow_chart(result_df), use_container_width=True)

    st.plotly_chart(make_3d_chart(result_df, view_name), use_container_width=True)

    display_df = result_df.copy()
    display_df["Design_Flow_m3s"] = display_df["Design_Flow_m3s"].round(6)
    display_df["Velocity_ms"] = display_df["Velocity_ms"].round(3)

    st.subheader("Calculated Sewer Table")
    st.dataframe(display_df, use_container_width=True)

    csv_data = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download recalculated results (CSV)",
        data=csv_data,
        file_name="sewer_design_results.csv",
        mime="text/csv",
    )
