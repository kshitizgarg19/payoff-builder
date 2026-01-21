# app.py
# ---------------------------------------------------------
# Commodity & Stock Options Payoff Chart Builder (Enhanced UI)
# Opstra-like Manual Strategy Simulator
# Author: Kshitiz Garg
# Tech: Python, Streamlit, Plotly, Pandas, NumPy
# ---------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Payoff Builder - Options & Futures", layout="wide")

# ---------------------- SIDEBAR ----------------------
st.sidebar.title("⚙ Strategy Controls")

market_type = st.sidebar.selectbox(
    "Select Market",
    ["Stock / Index", "Commodity"]
)

underlying_name = st.sidebar.text_input("Underlying Name (e.g. BANKNIFTY / GOLD / RELIANCE)")

spot_price = st.sidebar.number_input("Current Spot / Cash Price", value=100.0, step=1.0)

expiry_date = st.sidebar.date_input("Expiry Date")

# Today price for P&L comparison
live_price = st.sidebar.number_input("Today's / Live Price", value=spot_price, step=1.0)

st.sidebar.markdown("---")

# ---------------------- SESSION STATE ----------------------
if "legs" not in st.session_state:
    st.session_state.legs = []

# ---------------------- ADD LEG ----------------------
st.sidebar.subheader("➕ Add Position")

instrument_type = st.sidebar.selectbox(
    "Instrument",
    ["Call Option", "Put Option", "Future"]
)

position_type = st.sidebar.radio("Position", ["Buy (Long)", "Sell (Short)"])

strike = None
premium = None

if instrument_type != "Future":
    strike = st.sidebar.number_input("Strike Price", value=100.0, step=1.0)
    premium = st.sidebar.number_input("Premium", value=5.0, step=0.5)

lot_size = st.sidebar.number_input("Lot Size / Quantity", value=1, step=1)

add_leg = st.sidebar.button("Add to Strategy")

if add_leg:
    leg = {
        "Instrument": instrument_type,
        "Position": position_type,
        "Strike": strike,
        "Premium": premium,
        "Lot": lot_size
    }
    st.session_state.legs.append(leg)

# ---------------------- MAIN UI ----------------------
st.title("📈 Payoff Chart Builder (Stocks & Commodities)")

col1, col2 = st.columns([1.2, 2])

# ---------------------- PAYOFF LOGIC ----------------------

def call_payoff(price, strike, premium, lot, position):
    intrinsic = np.maximum(price - strike, 0)
    payoff = intrinsic - premium
    if position == "Sell (Short)":
        payoff = -payoff
    return payoff * lot


def put_payoff(price, strike, premium, lot, position):
    intrinsic = np.maximum(strike - price, 0)
    payoff = intrinsic - premium
    if position == "Sell (Short)":
        payoff = -payoff
    return payoff * lot


def future_payoff(price, spot, lot, position):
    payoff = price - spot
    if position == "Sell (Short)":
        payoff = -payoff
    return payoff * lot


def leg_pnl(price, leg):
    if leg["Instrument"] == "Call Option":
        return call_payoff(price, leg["Strike"], leg["Premium"], leg["Lot"], leg["Position"])
    elif leg["Instrument"] == "Put Option":
        return put_payoff(price, leg["Strike"], leg["Premium"], leg["Lot"], leg["Position"])
    else:
        return future_payoff(price, spot_price, leg["Lot"], leg["Position"])


# ---------------------- LEFT PANEL ----------------------
with col1:
    st.subheader("🧾 Strategy Legs (Editable)")

    if len(st.session_state.legs) == 0:
        st.info("No positions added yet")
    else:
        for i, leg in enumerate(st.session_state.legs):
            with st.expander(f"Leg {i + 1}: {leg['Instrument']} | {leg['Position']}", expanded=True):
                leg["Instrument"] = st.selectbox(
                    "Instrument",
                    ["Call Option", "Put Option", "Future"],
                    index=["Call Option", "Put Option", "Future"].index(leg["Instrument"]),
                    key=f"inst_{i}"
                )

                leg["Position"] = st.radio(
                    "Position",
                    ["Buy (Long)", "Sell (Short)"],
                    index=["Buy (Long)", "Sell (Short)"].index(leg["Position"]),
                    key=f"pos_{i}"
                )

                if leg["Instrument"] != "Future":
                    leg["Strike"] = st.slider(
                        "Strike",
                        min_value=max(0.0, spot_price * 0.5),
                        max_value=spot_price * 1.5,
                        value=float(leg["Strike"]),
                        step=1.0,
                        key=f"strike_{i}"
                    )

                    leg["Premium"] = st.slider(
                        "Premium",
                        min_value=0.0,
                        max_value=spot_price * 0.5,
                        value=float(leg["Premium"]),
                        step=0.5,
                        key=f"prem_{i}"
                    )

                leg["Lot"] = st.slider(
                    "Lot Size",
                    min_value=1,
                    max_value=1000,
                    value=int(leg["Lot"]),
                    step=1,
                    key=f"lot_{i}"
                )

                if st.button(f"❌ Remove Leg {i + 1}", key=f"del_{i}"):
                    st.session_state.legs.pop(i)
                    st.experimental_rerun()

    if st.button("🧹 Clear Strategy"):
        st.session_state.legs = []
        st.experimental_rerun()

# ---------------------- RIGHT PANEL ----------------------
with col2:
    st.subheader("📊 Payoff Curve")

    if len(st.session_state.legs) == 0:
        st.warning("Add at least one position to see payoff")
    else:
        price_range = np.linspace(spot_price * 0.5, spot_price * 1.5, 300)
        total_pnl = np.zeros_like(price_range)

        for leg in st.session_state.legs:
            total_pnl += leg_pnl(price_range, leg)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=price_range,
            y=total_pnl,
            mode='lines',
            name='Total P&L'
        ))

        fig.add_hline(y=0, line_dash="dash")
        fig.add_vline(x=spot_price, line_dash="dot", annotation_text="Spot", annotation_position="top")
        fig.add_vline(x=live_price, line_dash="dot", line_color="green", annotation_text="Today", annotation_position="top")

        fig.update_layout(
            title=f"Payoff Chart - {underlying_name}",
            xaxis_title="Underlying Price",
            yaxis_title="Profit / Loss",
            template="plotly_white",
            height=500
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---------------------- METRICS ----------------------
        max_profit = round(np.max(total_pnl), 2)
        max_loss = round(np.min(total_pnl), 2)

        breakevens = price_range[np.isclose(total_pnl, 0, atol=5)]

        m1, m2, m3 = st.columns(3)
        m1.metric("Max Profit", f"₹ {max_profit}")
        m2.metric("Max Loss", f"₹ {max_loss}")

        if len(breakevens) > 0:
            m3.metric("Breakeven(s)", ", ".join([str(round(x, 2)) for x in breakevens[:4]]))
        else:
            m3.metric("Breakeven(s)", "None")

        # ---------------------- PNL TABLE ----------------------
        st.subheader("📋 P&L Summary Table")

        table_data = []
        total_today = 0
        total_expiry = 0

        for i, leg in enumerate(st.session_state.legs):
            pnl_today = leg_pnl(live_price, leg)
            pnl_expiry = leg_pnl(spot_price, leg)

            total_today += pnl_today
            total_expiry += pnl_expiry

            table_data.append({
                "Leg": i + 1,
                "Instrument": leg["Instrument"],
                "Position": leg["Position"],
                "Strike": leg["Strike"],
                "Premium": leg["Premium"],
                "Lot": leg["Lot"],
                "P&L Today": round(float(pnl_today), 2),
                "P&L at Spot": round(float(pnl_expiry), 2)
            })

        df = pd.DataFrame(table_data)

        st.dataframe(df, use_container_width=True)

        t1, t2 = st.columns(2)
        t1.metric("Total P&L Today", f"₹ {round(float(total_today), 2)}")
        t2.metric("Total P&L at Spot", f"₹ {round(float(total_expiry), 2)}")

# ---------------------- FOOTER ----------------------
st.markdown("---")
st.markdown(
    "Maintained and developed by **Kshitiz Garg** | [LinkedIn](https://www.linkedin.com/in/kshitiz-garg-898403207/) | [GitHub](https://github.com/kshitizgarg19)")

# ---------------------- RUN INFO ----------------------
st.caption("Advanced strategy builder with editable legs, breakevens, payoff curve and P&L table for stocks, indices & commodities. Inspired by Opstra.")
