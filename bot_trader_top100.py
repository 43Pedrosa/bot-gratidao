import ccxt
import pandas as pd
import time
import requests
from datetime import datetime

# =================== CONFIGURAÇÕES ======================
API_KEY = "Ur51ZGEGGYPYZBLlen"
API_SECRET = "Ur51ZGEGGYPYZBLlen"
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YK5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002513565072"
STOP_LIMIT = 2
PERCENT_CAPITAL = 0.3
TAKE_PROFIT = 0.03
STOP_LOSS = 0.02

# =================== CONEXÃO BYBIT ======================
exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

stop_count = 0

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except:
        print("Erro ao enviar mensagem Telegram")

def obter_dados(symbol, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calcular_valor_entrada():
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    return round(usdt * PERCENT_CAPITAL, 2)

def executar_trade(symbol, direcao, amount):
    return exchange.create_market_order(symbol, 'buy' if direcao == 'long' else 'sell', amount)

def monitorar_trade(symbol, entry_price, direcao):
    global stop_count
    while True:
        preco_atual = exchange.fetch_ticker(symbol)['last']
        if direcao == 'long':
            if preco_atual >= entry_price * (1 + TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT* ({symbol})\nPreço: {preco_atual}")
                return
            elif preco_atual <= entry_price * (1 - STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT* ({symbol})\nPreço: {preco_atual}")
                stop_count += 1
                return
        else:
            if preco_atual <= entry_price * (1 - TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT* ({symbol})\nPreço: {preco_atual}")
                return
            elif preco_atual >= entry_price * (1 + STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT* ({symbol})\nPreço: {preco_atual}")
                stop_count += 1
                return
        time.sleep(10)

# =================== LOOP PRINCIPAL ======================
markets = exchange.load_markets()
sorted_markets = sorted(
    [m for m in markets.values() if m['active'] and m['quote'] == 'USDT'],
    key=lambda x: float(x['info'].get('quoteVolume24h', 0)),
    reverse=True
)
top_100_symbols = [m['symbol'] for m in sorted_markets[:100]]

for symbol in top_100_symbols:
    if stop_count >= STOP_LIMIT:
        enviar_telegram("🚫 *STOP diário atingido. Pausando operações.*")
        break
    try:
        df = obter_dados(symbol)
        entry_price = df['close'].iloc[-1]
        direcao = 'long' if df['close'].iloc[-1] > df['close'].mean() else 'short'
        valor = calcular_valor_entrada()
        if valor < 5:
            enviar_telegram(f"⚠️ Capital insuficiente para operar {symbol}")
            continue
        enviar_telegram(f"🚀 *Nova operação {direcao.upper()} iniciada em {symbol}*\nPreço: {entry_price}")
        executar_trade(symbol, direcao, valor)
        monitorar_trade(symbol, entry_price, direcao)
    except Exception as e:
        enviar_telegram(f"⚠️ Erro ao operar {symbol}: {str(e)}")
        time.sleep(5)