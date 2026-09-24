import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Theatre Suite - Deal Calculator", page_icon="🎭", layout="wide")

# --- STATE MANAGEMENT ---
if 'calls' not in st.session_state:
    st.session_state.calls = [
        {"label": "First Call", "amount": 1230000.0, "recipient": "Producer"},
        {"label": "Our Call", "amount": 120000.0, "recipient": "Venue"},
        {"label": "Next Prod", "amount": 100000.0, "recipient": "Producer"}
    ]

def add_call():
    st.session_state.calls.append({"label": f"Call {len(st.session_state.calls) + 1}", "amount": 0.0, "recipient": "Producer"})

def remove_call(index):
    st.session_state.calls.pop(index)

# --- SIDEBAR INPUTS ---
st.sidebar.title("🎭 Deal Setup")

st.sidebar.subheader("Show Details")
show_name = st.sidebar.text_input("Show Name", "Hamilton — Tour 2025")
gross = st.sidebar.number_input("Gross Ticket Income (£)", min_value=0.0, value=1735000.0, step=1000.0)
st.sidebar.slider("Gross Scenario Adjuster", min_value=0.0, max_value=max(5000000.0, gross * 1.5), value=gross, step=5000.0, key="gross_slider", on_change=lambda: st.session_state.update(gross=st.session_state.gross_slider))

st.sidebar.subheader("Levies (Off gross)")
col1, col2 = st.sidebar.columns(2)
levy_per = col1.number_input("Levy per ticket (£)", min_value=0.0, value=1.0, step=0.1)
levy_tix = col2.number_input("Paid tickets sold", min_value=0.0, value=49940.0, step=100.0)

st.sidebar.subheader("Supporter Seats (Off gross)")
col1, col2, col3 = st.sidebar.columns(3)
supp_seats = col1.number_input("Seats/wk", min_value=0.0, value=50.0)
supp_price = col2.number_input("Price (£)", min_value=0.0, value=85.30)
supp_weeks = col3.number_input("Weeks", min_value=0.0, value=2.0)

st.sidebar.subheader("Standard Deductions")
col1, col2 = st.sidebar.columns(2)
vat_rate = col1.number_input("VAT Rate (%)", min_value=0.0, value=20.0, step=1.0)
cc_rate = col2.number_input("CC Commission (%)", min_value=0.0, value=2.5, step=0.1, help="Calculated on gross")

st.sidebar.subheader("PRS (Optional)")
prs_enabled = st.sidebar.checkbox("Enable PRS Deduction")
prs_rate = st.sidebar.number_input("PRS Rate (%)", min_value=0.0, value=3.0, step=0.1) if prs_enabled else 0.0

st.sidebar.subheader("Deal Structure")
royalty_rate = st.sidebar.number_input("Royalties to Producer (%)", min_value=0.0, value=0.0, step=0.5)

st.sidebar.markdown("**Calls (in order)**")
calls_to_remove = []
for i, call in enumerate(st.session_state.calls):
    with st.sidebar.container():
        c1, c2, c3, c4 = st.columns([3, 3, 3, 1])
        call['label'] = c1.text_input("Label", value=call['label'], key=f"label_{i}")
        call['amount'] = c2.number_input("Amount (£)", min_value=0.0, value=float(call['amount']), step=1000.0, key=f"amt_{i}")
        call['recipient'] = c3.selectbox("To", ["Venue", "Producer"], index=["Venue", "Producer"].index(call['recipient']), key=f"rec_{i}")
        if c4.button("✕", key=f"del_{i}"):
            calls_to_remove.append(i)

for i in sorted(calls_to_remove, reverse=True):
    remove_call(i)

st.sidebar.button("+ Add Call", on_click=add_call)

st.sidebar.markdown("**Final Split**")
venue_split = st.sidebar.number_input("Venue / Theatre (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
prod_split = 100.0 - venue_split
st.sidebar.progress(venue_split / 100.0, text=f"Venue: {venue_split}% | Producer: {prod_split}%")

# --- CORE CALCULATIONS ---
# 1. Pre-Deal Values
levy_total = levy_per * levy_tix
supp_total = supp_seats * supp_price * supp_weeks
vat_mul = 1 + (vat_rate / 100)

running = gross
running -= levy_total
running -= supp_total

# 2. Tax & Charges
vat_amount = running - (running / vat_mul)
running = running / vat_mul

prs_amount = running * (prs_rate / 100) if prs_enabled else 0
running -= prs_amount

cc_amount = gross * (cc_rate / 100)
running -= cc_amount
net_receipts = running

# 3. The Deal
royalty_amount = running * (royalty_rate / 100)
running -= royalty_amount

venue_calls = 0.0
producer_calls = royalty_amount
waterfall_data = [
    {"Item": "Gross Ticket Income", "Deduction": "", "Running Total": gross, "Type": "Gross"},
    {"Item": "Less Levies", "Deduction": -levy_total, "Running Total": gross - levy_total, "Type": "Venue"},
    {"Item": "Less Supporter Seats", "Deduction": -supp_total, "Running Total": gross - levy_total - supp_total, "Type": "Venue"},
    {"Item": "Less VAT", "Deduction": -vat_amount, "Running Total": gross - levy_total - supp_total - vat_amount, "Type": "Cost"},
    {"Item": "Less CC Commission", "Deduction": -cc_amount, "Running Total": net_receipts + prs_amount, "Type": "Cost"}
]
if prs_enabled:
    waterfall_data.insert(-1, {"Item": "Less PRS", "Deduction": -prs_amount, "Running Total": net_receipts + prs_amount + cc_amount, "Type": "Cost"})

waterfall_data.append({"Item": "Net Receipts for Deal", "Deduction": "", "Running Total": net_receipts, "Type": "Net"})

if royalty_rate > 0:
    waterfall_data.append({"Item": f"Royalties ({royalty_rate}%)", "Deduction": -royalty_amount, "Running Total": running, "Type": "Producer"})

for call in st.session_state.calls:
    if call['amount'] <= 0: continue
    available = max(0.0, running)
    actual_paid = min(call['amount'], available)
    shortfall = call['amount'] - actual_paid
    running -= actual_paid
    
    if call['recipient'] == "Venue":
        venue_calls += actual_paid
    else:
        producer_calls += actual_paid
        
    label = call['label'] + (f" (Shortfall: £{shortfall:,.2f})" if shortfall > 0.005 else "")
    waterfall_data.append({"Item": label, "Deduction": -actual_paid, "Running Total": max(0.0, running), "Type": call['recipient']})

remaining = max(0.0, running)
venue_from_split = remaining * (venue_split / 100)
prod_from_split = remaining * (prod_split / 100)
waterfall_data.append({"Item": f"Split (V: {venue_split}% / P: {prod_split}%)", "Deduction": f"V: £{venue_from_split:,.2f} / P: £{prod_from_split:,.2f}", "Running Total": 0.0, "Type": "Split"})

# 4. Grand Totals
levy_net = levy_total / vat_mul
supp_net = supp_total / vat_mul
venue_grand = levy_net + supp_net + venue_calls + venue_from_split
producer_grand = producer_calls + prod_from_split
total_costs = vat_amount + prs_amount + cc_amount

# --- MAIN UI ---
st.title(show_name if show_name else "Deal Calculation Result")

# Summary Metrics
m1, m2, m3 = st.columns(3)
m1.metric("Theatre / Venue Receives", f"£{venue_grand:,.2f}")
m2.metric("Producer / Company Receives", f"£{producer_grand:,.2f}")
m3.metric("Total Tax & Charges", f"£{total_costs:,.2f}")

st.markdown("---")
col_chart, col_waterfall = st.columns([1, 2])

with col_chart:
    st.subheader("Gross Distribution")
    fig = go.Figure(data=[go.Pie(
        labels=['Venue', 'Producer', 'Costs (VAT/CC/PRS)'],
        values=[venue_grand, producer_grand, total_costs],
        hole=.5,
        marker_colors=['#2d6645', '#3d5a78', '#2c2820']
    )])
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True)

with col_waterfall:
    st.subheader("Deal Waterfall")
    df = pd.DataFrame(waterfall_data)
    
    # Format currency for display
    def format_deduction(val):
        if isinstance(val, (int, float)):
            return f"-£{abs(val):,.2f}" if val != 0 else "£0.00"
        return val
    
    df['Deduction'] = df['Deduction'].apply(format_deduction)
    df['Running Total'] = df['Running Total'].apply(lambda x: f"£{x:,.2f}")
    
    st.dataframe(df, use_container_width=True, hide_index=True)

# Break-Even Calculator Section
with st.expander("🎯 Break-Even Calculator (Reverse Logic)", expanded=False):
    st.markdown("Enter a target income to estimate the gross required based on the current deal structure.")
    c1, c2 = st.columns(2)
    target_venue = c1.number_input("Target Venue Income (£)", min_value=0.0, step=1000.0)
    target_prod = c2.number_input("Target Producer Income (£)", min_value=0.0, step=1000.0)
    
    # Binary search simulation function to find required gross
    def simulate_gross_for_target(target, entity="venue"):
        if target == 0: return 0.0
        lo, hi = 0.0, 50000000.0
        for _ in range(60):
            mid = (lo + hi) / 2
            # Run miniature simulation
            r = mid - levy_total - supp_total
            r /= vat_mul
            r -= prs_amount if prs_enabled else 0 # Simplified: PRS amount would scale, assuming static for basic BE
            r -= mid * (cc_rate / 100)
            
            p_calls = r * (royalty_rate / 100)
            r -= p_calls
            
            v_calls = 0
            for call in st.session_state.calls:
                paid = min(call['amount'], max(0.0, r))
                r -= paid
                if call['recipient'] == "Venue": v_calls += paid
                else: p_calls += paid
                
            rem = max(0.0, r)
            v_grand = levy_net + supp_net + v_calls + (rem * (venue_split / 100))
            p_grand = p_calls + (rem * (prod_split / 100))
            
            result = v_grand if entity == "venue" else p_grand
            if result < target: lo = mid
            else: hi = mid
        return (lo + hi) / 2

    c1_res, c2_res = st.columns(2)
    if target_venue > 0:
        req_gross_v = simulate_gross_for_target(target_venue, "venue")
        c1_res.success(f"**Required Gross:** £{req_gross_v:,.2f}")
    if target_prod > 0:
        req_gross_p = simulate_gross_for_target(target_prod, "producer")
        c2_res.info(f"**Required Gross:** £{req_gross_p:,.2f}")
