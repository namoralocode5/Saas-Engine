import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timezone, timedelta
from arbitrage_scanner import scan_cross_exchange_arbitrage, fetch_exchange_data, EXCHANGES

# 1. Page Configuration
st.set_page_config(
    page_title="Arbitrage Pulse PRO | Namoralo Code",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Verify Gumroad License
def verify_gumroad_license(product_permalink, license_key):
    if not license_key:
        return False
    if license_key.strip() == "TEST-PRO-1234":
        return True
    
    url = "https://api.gumroad.com/v2/licenses/verify"
    payload = {
        "product_permalink": product_permalink,
        "license_key": license_key.strip()
    }
    try:
        res = requests.post(url, data=payload, timeout=5)
        data = res.json()
        return data.get("success", False) and not data.get("purchase", {}).get("refunded", False)
    except Exception:
        return False

# Calculate time left to next funding rate settlement (00:00, 08:00, 16:00 UTC)
def get_next_funding_time():
    now = datetime.now(timezone.utc)
    target_hours = [0, 8, 16]
    for h in target_hours:
        target = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if target > now:
            diff = target - now
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours:02d}h {minutes:02d}m"
    target = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    diff = target - now
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m"

# Cached exchange data fetching
@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_exchange_data(ex, min_volume_usd):
    return fetch_exchange_data(ex, min_volume_usd=min_volume_usd)

# Generate direct links to futures markets on exchanges
def get_exchange_trade_url(exchange_name, asset):
    ex = exchange_name.lower()
    if 'binance' in ex:
        return f"https://www.binance.com/en/futures/{asset}USDT"
    elif 'bybit' in ex:
        return f"https://www.bybit.com/trade/usdt/{asset}USDT"
    elif 'okx' in ex:
        return f"https://www.okx.com/trade-swap/{asset}-usdt-swap"
    elif 'kraken' in ex:
        return f"https://futures.kraken.com/derivatives/market/{asset}usd"
    return "https://www.tradingview.com"

# Determine risk level based on asset type and funding spread stability
def calculate_risk_level(asset, spread_pct):
    top_tier_assets = {'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'BNB', 'AVAX', 'LINK', 'SUI'}
    if asset in top_tier_assets:
        return ("🟢 LOW RISK", "badge-stable")
    elif spread_pct <= 0.20:
        return ("🟡 MEDIUM RISK", "badge-stable")
    else:
        return ("⚠️ HIGH VOLATILITY", "badge-spike")

# Initialize session state
if "capital" not in st.session_state:
    st.session_state.capital = 1000
if "leverage" not in st.session_state:
    st.session_state.leverage = 1
if "min_vol" not in st.session_state:
    st.session_state.min_vol = 100000
if "fee_pct" not in st.session_state:
    st.session_state.fee_pct = 0.04
if "selected_exchanges" not in st.session_state:
    st.session_state.selected_exchanges = ['binance', 'bybit', 'okx', 'kraken']

# 2. CSS Styling - Complete FinTech Dark Mode & Mobile Bar Fix
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0e14 !important;
        color: #f1f3f6 !important;
    }
    
    header, [data-testid="stHeader"] {
        background-color: #0b0e14 !important;
        visibility: hidden;
    }
    
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem !important;
        background-color: #0b0e14 !important;
    }
    
    div[data-testid="stMetricLabel"] p, label, .stTextInput label, span, p {
        color: #f1f3f6 !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
        background-color: #151a24 !important;
        color: #ffffff !important;
        border: 1px solid #2a354d !important;
        border-radius: 8px !important;
    }

    div[data-testid="stExpander"] {
        background-color: #151a24 !important;
        border: 1px solid #232a3b !important;
        border-radius: 12px !important;
    }
    div[data-testid="stExpander"] summary {
        background-color: #151a24 !important;
        color: #f1f3f6 !important;
    }
    
    .timer-banner {
        background: linear-gradient(90deg, #1e2638 0%, #111622 100%);
        border: 1px solid #2962ff;
        border-radius: 10px;
        padding: 8px 12px;
        text-align: center;
        font-size: 13px;
        color: #82b1ff !important;
        margin-bottom: 12px;
    }
    
    .crypto-card {
        background-color: #151a24 !important;
        border: 1px solid #232a3b !important;
        border-radius: 12px !important;
        padding: 14px !important;
        margin-bottom: 14px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }
    
    .badge-apy {
        background: rgba(0, 230, 118, 0.15) !important;
        color: #00e676 !important;
        padding: 4px 8px !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        border: 1px solid rgba(0, 230, 118, 0.3) !important;
    }

    .badge-stable {
        background: rgba(41, 98, 255, 0.15) !important;
        color: #82b1ff !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        border: 1px solid rgba(41, 98, 255, 0.3) !important;
    }

    .badge-spike {
        background: rgba(255, 179, 0, 0.15) !important;
        color: #ffb300 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 10px !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255, 179, 0, 0.3) !important;
    }
    
    .strategy-box {
        background-color: #1c2333 !important;
        padding: 10px !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        font-size: 13px !important;
        color: #f1f3f6 !important;
    }
    
    .roi-box {
        background-color: #121929 !important;
        border: 1px dashed #2962ff !important;
        padding: 8px 12px !important;
        border-radius: 6px !important;
        margin-bottom: 10px !important;
        font-size: 12px !important;
        color: #82b1ff !important;
    }

    .stButton>button {
        width: 100% !important;
        border-radius: 10px !important;
        height: 50px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #2962ff 0%, #00b0ff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(41, 98, 255, 0.4) !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 20px !important;
        color: #00b0ff !important;
    }
    
    .buy-btn {
        display: inline-block;
        width: 100%;
        text-align: center;
        background: #ff9100 !important;
        color: #000000 !important;
        font-weight: 800;
        padding: 12px;
        border-radius: 8px;
        text-decoration: none;
        margin-top: 8px;
    }

    .card-buy-btn {
        display: block;
        width: 100%;
        text-align: center;
        background: linear-gradient(135deg, #ff9100 0%, #ff6d00 100%) !important;
        color: #000000 !important;
        font-weight: 800;
        padding: 6px 10px;
        border-radius: 6px;
        text-decoration: none;
        font-size: 12px;
        margin-top: 6px;
    }

    .pro-features {
        font-size: 12px;
        color: #a0aec0 !important;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# 3. Main Brand Header
st.markdown("""
<div style="
    display: flex; 
    align-items: center; 
    justify-content: space-between;
    background: #0f131a; 
    border: 1px solid #d4af37; 
    border-radius: 10px; 
    padding: 10px 14px; 
    margin-bottom: 16px;
    box-shadow: 0 4px 15px rgba(212, 175, 55, 0.15);
">
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="font-size: 18px; color: #f5c518;">⚡ <b>NC</b></span>
        <span style="color: #4a5568;">|</span>
        <span style="font-size: 13px; font-weight: 800; letter-spacing: 1px; color: #e2e8f0;">NAMORALO CODE</span>
    </div>
    <span style="font-size: 10px; font-weight: 700; background: #d4af37; color: #000; padding: 2px 6px; border-radius: 4px;">OFFICIAL</span>
</div>
""", unsafe_allow_html=True)

st.markdown("### Arbitrage Pulse PRO")
st.caption("Real-Time Funding Rate Arbitrage Scanner")

time_left = get_next_funding_time()
st.markdown(f"""
<div class="timer-banner">
    ⏳ Next Funding Rate Settlement in: <b>{time_left}</b>
</div>
""", unsafe_allow_html=True)

# License state check
user_key_input = st.session_state.get("user_key_input", "")
GUMROAD_PERMALINK = "arbitrage-pulse-pro"
is_pro_init = verify_gumroad_license(GUMROAD_PERMALINK, user_key_input)

# License activation section
with st.expander("🔑 PRO License Activation / Gumroad Key", expanded=not is_pro_init):
    user_key = st.text_input("Enter your Gumroad License Key:", type="password", key="user_key_input")
    is_pro = verify_gumroad_license(GUMROAD_PERMALINK, user_key)
    
    if is_pro:
        st.success("✅ PRO License Active! Full access unlocked.")
    elif user_key:
        st.error("❌ Invalid or expired license key.")
    else:
        st.markdown("""
        <div class="pro-features">
            🔓 <b>Unlock PRO Features:</b><br>
            • Unmask Exact Long & Short Exchanges<br>
            • 1-Click Direct Trade Execution Links<br>
            • Real-Time Arbitrage Spreads & Multi-Exchange Data
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://namoralocode.gumroad.com/l/arbitrage-pulse-pro" target="_blank" class="buy-btn">💳 Get PRO License on Gumroad</a>', unsafe_allow_html=True)
        st.caption("Test License Key: `TEST-PRO-1234`")

# 4. Parameters and Sliders
with st.expander("⚙️ Portfolio, Fees & Exchange Settings", expanded=False):
    st.session_state.capital = st.number_input("Capital ($)", min_value=100, value=st.session_state.capital, step=500)
    st.session_state.leverage = st.slider("Leverage", min_value=1, max_value=5, value=st.session_state.leverage)
    st.session_state.min_vol = st.number_input("Min. 24h Volume ($)", value=st.session_state.min_vol, step=50000)
    st.session_state.fee_pct = st.number_input("Est. Total Trading Fee (%) per round-trip", min_value=0.0, max_value=0.2, value=st.session_state.fee_pct, step=0.01, format="%.2f")
    
    st.markdown("---")
    st.session_state.selected_exchanges = st.multiselect(
        "Active Exchanges:",
        options=['binance', 'bybit', 'okx', 'kraken'],
        default=st.session_state.selected_exchanges
    )
    st.caption("🟢 Exchange Status: API ready for scanning")

st.write("")

# 5. Action Button & Market Scan
if st.button("🔎 SCAN MARKET NOW"):
    with st.spinner("Fetching funding rates from exchanges..."):
        all_ex_data = {}
        for ex in st.session_state.selected_exchanges:
            data = cached_fetch_exchange_data(ex, min_volume_usd=st.session_state.min_vol)
            if data:
                all_ex_data[ex] = data

        all_assets = set()
        for ex_data in all_ex_data.values():
            all_assets.update(ex_data.keys())

        results = []
        EXCLUDED_SYMBOLS = {'GBP', 'EUR', 'USD', 'USDT', 'USDC', 'CAD', 'HFT', 'BERA', 'ZIG', 'DEGEN'}

        for asset in all_assets:
            if asset in EXCLUDED_SYMBOLS:
                continue
            available_exchanges = [ex for ex in all_ex_data if asset in all_ex_data[ex]]
            if len(available_exchanges) < 2:
                continue

            min_ex = min(available_exchanges, key=lambda x: all_ex_data[x][asset]['rate_pct'])
            max_ex = max(available_exchanges, key=lambda x: all_ex_data[x][asset]['rate_pct'])

            min_rate = all_ex_data[min_ex][asset]['rate_pct']
            max_rate = all_ex_data[max_ex][asset]['rate_pct']
            spread_pct = max_rate - min_rate

            if spread_pct <= 0:
                continue

            payments_per_day = 3
            gross_annual_apy = spread_pct * payments_per_day * 365 * st.session_state.leverage
            fee_drag = st.session_state.fee_pct * st.session_state.leverage
            net_annual_apy = max(0.0, gross_annual_apy - fee_drag)

            risk_label, risk_class = calculate_risk_level(asset, spread_pct)

            if net_annual_apy >= 0.0:
                est_profit_year = round((st.session_state.capital * net_annual_apy) / 100, 2)
                results.append({
                    'asset': asset,
                    'long_ex': min_ex.upper(),
                    'short_ex': max_ex.upper(),
                    'spread': round(spread_pct, 4),
                    'net_apy': round(net_annual_apy, 2),
                    'profit_usd': est_profit_year,
                    'risk_label': risk_label,
                    'risk_class': risk_class,
                    'tv_url': f"https://www.tradingview.com/symbols/{asset}USDT",
                    'long_url': get_exchange_trade_url(min_ex, asset),
                    'short_url': get_exchange_trade_url(max_ex, asset)
                })

        results = sorted(results, key=lambda x: x['net_apy'], reverse=True)
        st.session_state.scan_results = results

# Wyświetlanie wyników z pamięci
if "scan_results" in st.session_state and st.session_state.scan_results:
    results = st.session_state.scan_results
    
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.caption(f"⏱️ Last Update: **{now_str}**")
    
    m1, m2 = st.columns(2)
    m1.metric("Pairs Found", f"{len(results)}")
    if results:
        m2.metric("Max Net APY", f"+{results[0]['net_apy']}%")
    st.write("")

    # Filter & Search Controls
    col_search, col_apy, col_filter = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("🔍 Search Asset:", "").strip().upper()
    with col_apy:
        min_apy_filter = st.number_input("📉 Min. Net APY (%)", min_value=0.0, value=0.0, step=5.0)
    with col_filter:
        only_my_exchanges = st.checkbox("🎯 My Exchanges Only", value=False)

    filtered_results = results.copy()
    if search_query:
        filtered_results = [item for item in filtered_results if search_query in item['asset']]

    if min_apy_filter > 0:
        filtered_results = [item for item in filtered_results if item['net_apy'] >= min_apy_filter]

    if only_my_exchanges:
        active_set = {ex.upper() for ex in st.session_state.selected_exchanges}
        filtered_results = [item for item in filtered_results if item['long_ex'] in active_set and item['short_ex'] in active_set]

    if filtered_results:
        for item in filtered_results:
            if is_pro:
                long_display = f'<a href="{item["long_url"]}" target="_blank" style="color: #00e676; text-decoration: none; font-weight: bold;">{item["long_ex"]} ↗</a>'
                short_display = f'<a href="{item["short_url"]}" target="_blank" style="color: #ff5252; text-decoration: none; font-weight: bold;">{item["short_ex"]} ↗</a>'
                pro_button_html = ""
                strategy_line = f'<div style="margin-top: 4px; font-size: 11px; color: #00e676; font-family: monospace;">📋 Copy Plan: LONG {item["long_ex"]} | SHORT {item["short_ex"]} | {item["asset"]}/USDT</div>'
            else:
                long_display = '<span style="color: #ffb300; font-weight: bold;">🔒 PRO</span>'
                short_display = '<span style="color: #ffb300; font-weight: bold;">🔒 PRO</span>'
                pro_button_html = '<a href="https://namoralocode.gumroad.com/l/arbitrage-pulse-pro" target="_blank" class="card-buy-btn">💳 Unlock Exchanges on Gumroad</a>'
                strategy_line = ""
            
            card_html = f"""<div class="crypto-card">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
    <div>
        <div style="font-size: 18px; font-weight: 800; color: #ffffff;">{item['asset']}/USDT</div>
        <span class="{item['risk_class']}" style="margin-top: 4px; display: inline-block;">{item['risk_label']}</span>
    </div>
    <div class="badge-apy" style="text-align: right;">
        +{item['net_apy']}% APY <span style="font-size: 10px; opacity: 0.8;">({st.session_state.leverage}x)</span>
    </div>
</div>
<div class="strategy-box">
    🟢 LONG: {long_display}<br>
    🔴 SHORT: {short_display}
    {pro_button_html}
</div>
<div class="roi-box">
    💵 Est. Profit (${st.session_state.capital} @ {st.session_state.leverage}x): <b style="color: #82b1ff;">+${item['profit_usd']} / yr</b>
    {strategy_line}
</div>
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: #8f9cae;">
    <span>Spread/8h: +{item['spread']}% (Fees: {st.session_state.fee_pct}%)</span>
    <a href="{item['tv_url']}" target="_blank" style="color: #00b0ff; text-decoration: none; font-weight: bold;">TradingView 📈</a>
</div>
</div>"""
            st.markdown(card_html, unsafe_allow_html=True)

        if not is_pro:
            st.warning("🔒 Activate PRO license to unlock exchanges and direct links.")
            st.markdown('<a href="https://namoralocode.gumroad.com/l/arbitrage-pulse-pro" target="_blank" class="buy-btn">💳 Get PRO License & Unlock Exchanges</a>', unsafe_allow_html=True)
    else:
        st.info("No arbitrage opportunities matching current filter criteria.")
else:
    st.info("Click 'SCAN MARKET NOW' to fetch current arbitrage spreads.")
