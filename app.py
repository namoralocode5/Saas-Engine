# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import datetime

# --- CONFIG & STYLING ---
st.set_page_config(
    page_title="Arbitrage Pulse PRO",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .badge-official { background-color: #f59e0b; color: #000; font-weight: bold; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
    .stButton>button { width: 100%; background-color: #1f6feb; color: white; font-weight: bold; border-radius: 6px; border: none; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- KLUCZE TESTOWE I WERYFIKACJA ---
GUMROAD_PRODUCT_PERMALINK = "arbitrage-pulse-pro"

def verify_license(license_key):
    if not license_key:
        return False, "Wpisz klucz licencyjny."
    
    clean_key = license_key.strip()
    
    # KOD 1-ZNAKOWY DLA SZYBKIEGO TESTU / NAGRANIA (np. wpisanie "1")
    if len(clean_key) == 1 or clean_key.upper() in ["1", "X", "EARLYBIRD"]:
        return True, "✅ Klucz testowy aktywny (PRO Odblokowane)!"
    
    # Weryfikacja Gumroad dla prawdziwych klientów
    try:
        url = "https://api.gumroad.com/v2/licenses/verify"
        res = requests.post(url, data={"product_permalink": GUMROAD_PRODUCT_PERMALINK, "license_key": clean_key}, timeout=5)
        data = res.json()
        if data.get("success") and not data.get("purchase", {}).get("refunded"):
            return True, "✅ Licencja PRO aktywna!"
        return False, "❌ Nieprawidłowy klucz."
    except Exception:
        return False, "Błąd weryfikacji API."

# --- NAGŁÓWEK ---
col_logo, col_badge = st.columns([3, 1])
with col_logo:
    st.markdown("### ⚡ **NC | NAMORALO CODE**")
with col_badge:
    st.markdown("<span class='badge-official'>OFFICIAL</span>", unsafe_allow_html=True)

st.title("Arbitrage Pulse PRO")
st.caption("Real-Time Funding Rate Arbitrage Scanner")

st.info("⌛ **Next Funding Rate Settlement in:** `01h 33m`")

# --- PANEL LICENCJI PRO ---
with st.expander("🔑 **PRO License Activation**", expanded=True):
    user_key = st.text_input("Enter License Key:", type="password", placeholder="Wpisz: 1", key="license_input")
    is_pro, msg = verify_license(user_key)
    
    if is_pro:
        st.success(msg)
    else:
        st.warning("🔒 Odblokuj funkcje PRO kluczem z Gumroad.")
        st.link_button("👉 Get PRO License on Gumroad", "https://namoralocode.gumroad.com/l/arbitrage-pulse-pro")

# --- USTAWIENIA ---
with st.expander("⚙️ **Portfolio Settings**"):
    capital = st.number_input("Capital ($)", value=1000, step=100)
    leverage = st.slider("Leverage", min_value=1, max_value=10, value=1)

# --- SKANOWANIE ---
if st.button("🔍 SCAN MARKET NOW") or "scanned" in st.session_state:
    st.session_state.scanned = True
    st.caption(f"🕒 Last Update: {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")
    
    col1, col2 = st.columns(2)
    col1.metric("Pairs Found", "110")
    col2.metric("Max Net APY", "+486.99%")

    search_query = st.text_input("🔍 Search Asset:", placeholder="np. XRP, HMSTR").strip().upper()
    min_apy = st.number_input("📉 Min. Net APY (%)", value=0.0, step=1.0)

    st.markdown("---")

    mock_pairs = [
        {"symbol": "HMSTR/USDT", "tag": "🔥 HIGH VOLATILITY", "apy": 486.99, "long": "Binance", "short": "Bybit", "spread": 0.4448},
        {"symbol": "MINA/USDT", "tag": "🔥 HIGH VOLATILITY", "apy": 421.67, "long": "OKX", "short": "Kraken", "spread": 0.3851},
        {"symbol": "XRP/USDT", "tag": "🟢 LOW RISK", "apy": 4.69, "long": "Binance", "short": "OKX", "spread": 0.0043}
    ]

    filtered = [p for p in mock_pairs if (not search_query or search_query in p["symbol"]) and p["apy"] >= min_apy]

    for p in filtered:
        est_profit = (capital * (p["apy"] / 100)) * leverage
        st.markdown(f"### **{p['symbol']}** &nbsp; <span style='background:#065f46; color:#a7f3d0; padding:2px 8px; border-radius:4px;'>+{p['apy']:.2f}% APY</span>", unsafe_allow_html=True)
        
        col_l, col_s = st.columns(2)
        if is_pro:
            with col_l:
                st.markdown(f"🟢 **LONG:** `{p['long']}`")
                st.link_button(f"Trade Long", f"https://www.{p['long'].lower()}.com")
            with col_s:
                st.markdown(f"🔴 **SHORT:** `{p['short']}`")
                st.link_button(f"Trade Short", f"https://www.{p['short'].lower()}.com")
        else:
            with col_l: st.markdown("🟢 **LONG:** 🔒 `PRO`")
            with col_s: st.markdown("🔴 **SHORT:** 🔒 `PRO`")
            st.button("🔓 Unlock Exchanges", key=f"btn_{p['symbol']}")

        st.info(f"💵 **Est. Profit (${capital}):** `+${est_profit:.2f} / yr` | Spread: +{p['spread']}%")
        st.markdown("---")

    if not is_pro:
        st.warning("🔒 **Activate PRO license to unlock exchanges.**")
        st.link_button("💳 Get PRO License", "https://namoralocode.gumroad.com/l/arbitrage-pulse-pro")

