
import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# =================== CONFIGURAÇÕES ======================
API_KEY = "iDhcgx3LvPqkUl6ByN"
API_SECRET = "Arg9ldCHqZ6lXmMYmBVEIEskTKnF2MCaxOlf"
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YK5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002513565072"
STOP_LIMIT = 2
PERCENT_CAPITAL = 0.3
TAKE_PROFIT = 0.03
STOP_LOSS = 0.02

exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'
    }
})

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensagem,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except:
        print("Erro ao enviar mensagem Telegram")

def obter_dados(par, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(par, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calcular_valor_entrada():
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    return round(usdt * PERCENT_CAPITAL, 2)

def executar_trade(direcao, par, amount):
    return exchange.create_market_order(par, 'buy' if direcao == 'long' else 'sell', amount)

def monitorar_trade(entry_price, direcao, par):
    stop_count = 0
    while True:
        preco_atual = exchange.fetch_ticker(par)['last']
        if direcao == 'long':
            if preco_atual >= entry_price * (1 + TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT*\nPar: {par}\n💰Preço: {preco_atual}")
                return
            elif preco_atual <= entry_price * (1 - STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT*\nPar: {par}\n📉Preço: {preco_atual}")
                return
        else:
            if preco_atual <= entry_price * (1 - TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT*\nPar: {par}\n💰Preço: {preco_atual}")
                return
            elif preco_atual >= entry_price * (1 + STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT*\nPar: {par}\n📉Preço: {preco_atual}")
                return
        time.sleep(10)

def main():
    enviar_telegram("🤖 Bot Iniciado com os Top 100 Pares da Bybit")
    markets = exchange.load_markets()
    top_symbols = sorted(
        [s for s in markets if "/USDT" in s and markets[s]['active']],
        key=lambda s: float(markets[s].get('info', {}).get('turnover24h', 0)),
        reverse=True
    )[:100]

    for symbol in top_symbols:
        try:
            df = obter_dados(symbol)
            if df.empty:
                continue
            preco_entrada = df['close'].iloc[-1]
            direcao = 'long'
            valor = calcular_valor_entrada()
            enviar_telegram(f"🚨 Operação iniciada em {symbol}\n🎯 Entrada: {preco_entrada}")
            executar_trade(direcao, symbol, valor)
            monitorar_trade(preco_entrada, direcao, symbol)
        except Exception as e:
            print(f"Erro com {symbol}: {e}")
        time.sleep(2)

if __name__ == "__main__":
    main()
