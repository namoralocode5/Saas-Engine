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

# Własny styl CSS dopasowany do ciemnego motywu aplikacji
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .badge-official {
        background-color: #f59e0b;
        color: #000;
        font-weight: bold;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    .card-pro {
        border: 1px solid #30363d;
        background-color: #161b22;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .pro-unlocked {
        color: #10b981;
        font-weight: bold;
    }
    .pro-locked {
        color: #ef4444;
        font-weight: bold;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f6feb;
        color: white;
        font-weight: bold;
        border-radius: 6px;
        border: none;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- KLUCZE TESTOWE I WERYFIKACJA GUMROAD ---
TEST_KEYS = ["DEMO-PRO-2026", "EARLYBIRD", "TESTKEY", "NAMORALO-PRO"]
GUMROAD_PRODUCT_PERMALINK = "arbitrage-pulse-pro"  # Twój permalink z Gumroad

def verify_license(license_key):
    if not license_key:
        return False, "Wpisz klucz licencyjny."
    
    clean_key = license_key.strip().upper()
    
    # 1. Sprawdzenie klucza testowego (dla Ciebie / do nagrań)
    if clean_key in TEST_KEYS or clean_key.startswith("TEST-"):
        return True, "✅ Klucz testowy aktywny (Wersja PRO Odblokowana)!"
    
    # 2. Weryfikacja przez API Gumroad dla prawdziwych klientów
    try:
        url = "https://api.gumroad.com/v2/licenses/verify"
        res = requests.post(url, data={
            "product_permalink": GUMROAD_PRODUCT_PERMALINK,
            "license_key": clean_key
        }, timeout=5)
        
        data = res.json()
        if data.get("success") and not data.get("purchase", {}).get("refunded"):
            return True, "✅ Licencja PRO aktywna!"
        else:
            return False, "❌ Nieprawidłowy lub wygasły klucz Gumroad."
    except Exception as e:
        # Awaryjnie jeśli API Gumroad nie odpowiada
        return False, f"Błąd weryfikacji API: {str(e)}"


# --- NAGŁÓWEK ---
col_logo, col_badge = st.columns([3, 1])
with col_logo:
    st.markdown("### ⚡ **NC | NAMORALO CODE**")
with col_badge:
    st.markdown("<span class='badge-official'>OFFICIAL</span>", unsafe_allow_html=True)

st.title("Arbitrage Pulse PRO")
st.caption("Real-Time Funding Rate Arbitrage Scanner")

# Banner z odliczaniem
st.info("⌛ **Next Funding Rate Settlement in:** `01h 33m`")


# --- PANEL LICENCJI PRO ---
with st.expander("🔑 **PRO License Activation / Gumroad Key**", expanded=True):
    user_key = st.text_input(
        "Enter your Gumroad License Key:", 
        type="password", 
        placeholder="Wklej klucz lub wpisz: DEMO-PRO-2026",
        key="license_input"
    )
    
    is_pro, msg = verify_license(user_key)
    
    if is_pro:
        st.success(msg)
    else:
        st.warning(msg if user_key else "🔒 Odblokuj funkcje PRO za pomocą klucza zakupu z Gumroad.")
        st.markdown("""
        **Unlocked PRO Features:**
        - Unmask Exact Long & Short Exchanges
        - 1-Click Direct Trade Execution Links
        - Real-Time Arbitrage Spreads & Multi-Exchange Data
        """)
        st.link_button("👉 Get PRO License on Gumroad", "https://namoralocode.gumroad.com/l/arbitrage-pulse-pro")


# --- USTAWIENIA PORTFELA I GIEŁD ---
with st.expander("⚙️ **Portfolio, Fees & Exchange Settings**"):
    capital = st.number_input("Capital ($)", value=1000, step=100)
    leverage = st.slider("Leverage", min_value=1, max_value=10, value=1)
    min_vol = st.number_input("Min. 24h Volume (USDT)", value=0)
    fee_per_roundtrip = st.number_input("Est. Total Trading Fee (%) per round-trip", value=0.04, step=0.01)
    active_exchanges = st.multiselect(
        "Active Exchanges:", 
        ["binance", "bybit", "okx", "kraken"], 
        default=["binance", "bybit", "okx", "kraken"]
    )


# --- PRZYCISK SKANOWANIA ---
scan_clicked = st.button("🔍 SCAN MARKET NOW")

if "scanned" not in st.session_state:
    st.session_state.scanned = False

if scan_clicked:
    st.session_state.scanned = True

if st.session_state.scanned:
    st.caption(f"🕒 Last Update: {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC")
    
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("Pairs Found", "110")
    col_stat2.metric("Max Net APY", "+486.99%")

    # --- FILTRY ---
    search_query = st.text_input("🔍 Search Asset:", placeholder="np. XRP, ETH, HMSTR").strip().upper()
    min_apy = st.number_input("📉 Min. Net APY (%)", value=0.0, step=1.0)
    my_exchanges_only = st.checkbox("🎯 My Exchanges Only")

    st.download_button("📥 Download Filtered Results (CSV)", data="Symbol,APY\nHMSTR/USDT,486.99", file_name="arbitrage_results.csv")

    st.markdown("---")

    # --- PRZYKŁADOWE DANE (MOCK DATA) ---
    mock_pairs = [
        {
            "symbol": "HMSTR/USDT",
            "tag": "🔥 HIGH VOLATILITY",
            "apy": 486.99,
            "long_ex": "Binance",
            "short_ex": "Bybit",
            "spread": 0.4448,
            "fee": 0.04
        },
        {
            "symbol": "MINA/USDT",
            "tag": "🔥 HIGH VOLATILITY",
            "apy": 421.67,
            "long_ex": "OKX",
            "short_ex": "Kraken",
            "spread": 0.3851,
            "fee": 0.04
        },
        {
            "symbol": "XRP/USDT",
            "tag": "🟢 LOW RISK",
            "apy": 4.69,
            "long_ex": "Binance",
            "short_ex": "OKX",
            "spread": 0.0043,
            "fee": 0.04
        }
    ]

    # Przefiltrowanie wg wyszukiwarki i APY
    filtered_pairs = [
        p for p in mock_pairs 
        if (not search_query or search_query in p["symbol"]) and p["apy"] >= min_apy
    ]

    if not filtered_pairs:
        st.info("No arbitrage opportunities matching current filter criteria.")
    else:
        for p in filtered_pairs:
            est_profit = (capital * (p["apy"] / 100)) * leverage
            
            st.markdown(f"### **{p['symbol']}** &nbsp; <span style='background:#065f46; color:#a7f3d0; padding:2px 8px; border-radius:4px; font-size:0.8rem;'>+{p['apy']:.2f}% APY ({leverage}x)</span>", unsafe_allow_html=True)
            st.caption(f"Risk Profile: {p['tag']}")
            
            col_l, col_s = st.columns(2)
            
            if is_pro:
                # WERSJA PRO: Pokazuje dokładne giełdy i bezpośrednie linki
                with col_l:
                    st.markdown(f"🟢 **LONG:** `{p['long_ex']}`")
                    st.link_button(f"Trade Long on {p['long_ex']}", f"https://www.{p['long_ex'].lower()}.com")
                with col_s:
                    st.markdown(f"🔴 **SHORT:** `{p['short_ex']}`")
                    st.link_button(f"Trade Short on {p['short_ex']}", f"https://www.{p['short_ex'].lower()}.com")
            else:
                # WERSJA DEMO: Zablokowane giełdy
                with col_l:
                    st.markdown("🟢 **LONG:** 🔒 `PRO`")
                with col_s:
                    st.markdown("🔴 **SHORT:** 🔒 `PRO`")
                st.button(f"🔓 Unlock Exchanges on Gumroad", key=f"btn_lock_{p['symbol']}")

            st.info(f"💵 **Est. Profit (${capital} @ {leverage}x):** `+${est_profit:.2f} / yr`\n\nSpread/8h: +{p['spread']}% (Fees: {p['fee']}%)")
            st.markdown(f"[📈 TradingView Chart](https://www.tradingview.com/chart/?symbol={p['symbol'].replace('/', '')})")
            st.markdown("---")

    # Sticky/Bottom banner dla darmowej wersji
    if not is_pro:
        st.warning("🔒 **Activate PRO license to unlock exchanges and direct links.**")
        st.link_button("💳 Get PRO License & Unlock Exchanges", "https://namoralocode.gumroad.com/l/arbitrage-pulse-pro")
