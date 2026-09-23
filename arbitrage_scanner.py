# -*- coding: utf-8 -*-
"""
Automated Multi-Exchange Arbitrage & Funding Rate Scanner (PRO SaaS Engine V3.0)
-------------------------------------------------------------------
Scans perpetual futures funding rates across Binance, Bybit, OKX, and Kraken via CCXT,
finds cross-exchange spread opportunities, calculates NET APY after fees,
enforces volume filters, and dispatches Telegram alerts with TradingView links.
"""

import os
import requests
import ccxt
import pandas as pd

EXCHANGES = ['binance', 'bybit', 'okx', 'kraken']

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    token = TELEGRAM_BOT_TOKEN.strip() if TELEGRAM_BOT_TOKEN else None
    chat_id = TELEGRAM_CHAT_ID.strip() if TELEGRAM_CHAT_ID else None

    if not token or not chat_id:
        print("⚠️ Telegram BOT_TOKEN or CHAT_ID missing in environment variables. Notification skipped.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 400:
            print("⚠️ HTML formatting rejected by Telegram (HTTP 400). Retrying as plain text...")
            payload.pop("parse_mode", None)
            clean_text = message.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace("<a>", "").replace("</a>", "")
            payload["text"] = clean_text
            response = requests.post(url, json=payload, timeout=10)
            
        if response.status_code == 200:
            print("🚀 Telegram alert delivered successfully!")
        else:
            print(f"❌ Telegram API Error ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"❌ Network/Telegram Error: {e}")

def fetch_exchange_data(exchange_id, min_volume_usd=100000.0):
    print(f"🔄 Fetching data from exchange: {exchange_id.upper()}...")
    try:
        ex_class = getattr(ccxt, exchange_id)
        if exchange_id == 'kraken':
            exchange = ccxt.krakenfutures({'enableRateLimit': True})
        else:
            exchange = ex_class({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
            
        markets = exchange.load_markets()
        rates = exchange.fetch_funding_rates()
        
        try:
            tickers = exchange.fetch_tickers()
        except Exception:
            tickers = {}
            
        parsed_data = {}
        for symbol, rate_info in rates.items():
            market_info = markets.get(symbol, {})
            base_currency = market_info.get('base')
            
            if not base_currency:
                continue
                
            rate = rate_info.get('fundingRate')
            if rate is None:
                continue
                
            ticker_info = tickers.get(symbol, {})
            volume_usd = ticker_info.get('quoteVolume', 0) or ticker_info.get('baseVolume', 0) or 0
            
            if volume_usd < min_volume_usd:
                continue

            parsed_data[base_currency.upper()] = {
                'rate': rate,
                'rate_pct': rate * 100,
                'volume_usd': volume_usd,
                'symbol': symbol
            }
            
        return parsed_data
        
    except Exception as e:
        print(f"⚠️ Error fetching data from {exchange_id.upper()}: {e}")
        return {}

def scan_cross_exchange_arbitrage():
    min_net_apy = 15.0       
    total_fee_pct = 0.20      
    min_vol = 100000.0        
    
    EXCLUDED_SYMBOLS = {'GBP', 'EUR', 'USD', 'USDT', 'USDC', 'CAD', 'HFT', 'BERA', 'ZIG', 'DEGEN'}

    print("🔎 Running Multi-Exchange Arbitrage Scanner...")

    all_ex_data = {}
    for ex in EXCHANGES:
        data = fetch_exchange_data(ex, min_volume_usd=min_vol)
        if data:
            all_ex_data[ex] = data

    if len(all_ex_data) < 2:
        print("❌ Too few exchanges returned valid data for arbitrage.")
        return

    all_assets = set()
    for ex_data in all_ex_data.values():
        all_assets.update(ex_data.keys())

    results = []

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
        gross_annual_apy = spread_pct * payments_per_day * 365

        annual_fee_drag = (total_fee_pct / 30.0) * 365.0
        net_annual_apy = max(0.0, gross_annual_apy - annual_fee_drag)

        if net_annual_apy < min_net_apy:
            continue

        payback_days = round(total_fee_pct / (spread_pct * payments_per_day), 1) if spread_pct > 0 else 'N/A'
        tv_url = f"https://www.tradingview.com/symbols/{asset}USDT"

        results.append({
            'Asset': asset,
            'Long Exchange': min_ex.upper(),
            'Short Exchange': max_ex.upper(),
            'Long Rate (%)': round(min_rate, 4),
            'Short Rate (%)': round(max_rate, 4),
            'Spread (%)': round(spread_pct, 4),
            'Gross APY (%)': round(gross_annual_apy, 2),
            'Net APY (%)': round(net_annual_apy, 2),
            'Fee Payback (days)': payback_days,
            'TradingView URL': tv_url
        })

    df = pd.DataFrame(results)
    if df.empty:
        print(f"No arbitrage opportunities found with Net APY >= {min_net_apy}%.")
        return

    df = df.sort_values(by='Net APY (%)', ascending=False)

    msg = f"🔥 <b>MULTI-EXCHANGE ARBITRAGE ALERTS</b>\n"
    msg += f"<i>(Cross-Exchange Futures Spread)</i>\n\n"

    for _, row in df.head(5).iterrows():
        clickable_symbol = f'<a href="{row["TradingView URL"]}"><b>{row["Asset"]}/USDT</b></a>'
        
        msg += f"🪙 {clickable_symbol}\n"
        msg += f"├ Strategy: <b>LONG on {row['Long Exchange']} | SHORT on {row['Short Exchange']}</b>\n"
        msg += f"├ Funding Rates: {row['Long Exchange']} ({row['Long Rate (%)']}%) vs {row['Short Exchange']} ({row['Short Rate (%)']}%)\n"
        msg += f"├ Spread / 8h: <b>+{row['Spread (%)']}%</b>\n"
        msg += f"├ Gross APY: <b>+{row['Gross APY (%)']}%</b>\n"
        msg += f"├ <b>NET APY (after fees): +{row['Net APY (%)']}%</b>\n"
        msg += f"└ Fee Payback: <b>{row['Fee Payback (days)']} days</b>\n\n"

    send_telegram_message(msg)

if __name__ == "__main__":
    scan_cross_exchange_arbitrage()
