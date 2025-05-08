
import ccxt
import pandas as pd
import time
import requests
from datetime import datetime
from estrategias import verificar_confluencias

# =================== CONFIGURAÇÕES ======================
API_KEY = 'Ur51ZGEGGYPYZBLlen'
API_SECRET = 'QqcTJwHyT5FQWwC53CtRDJ577D5CmIxRUnTa'
TELEGRAM_BOT_TOKEN = '7038936636:AAHTXNhrmBKa-vccp_YX5nK4oDYKDWeVwpw'
TELEGRAM_CHAT_ID = '-1002515356072'
PAIR = 'BTC/USDT'
STOP_LIMIT = 2
PERCENT_CAPITAL = 0.3
TAKE_PROFIT = 0.03
STOP_LOSS = 0.02

exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

stop_count = 0

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

def obter_dados(par=PAIR, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(par, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calcular_valor_entrada():
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    return round(usdt * PERCENT_CAPITAL, 2)

def executar_trade(direcao, amount):
    return exchange.create_market_order(PAIR, 'buy' if direcao == 'long' else 'sell', amount)

def monitorar_trade(entry_price, direcao):
    global stop_count
    while True:
        preco_atual = exchange.fetch_ticker(PAIR)['last']
        if direcao == 'long':
            if preco_atual >= entry_price * (1 + TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT*
Preço: {preco_atual}")
                return
            elif preco_atual <= entry_price * (1 - STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT*
Preço: {preco_atual}")
                stop_count += 1
                return
        else:
            if preco_atual <= entry_price * (1 - TAKE_PROFIT):
                enviar_telegram(f"✅ *Take Profit HIT*
Preço: {preco_atual}")
                return
            elif preco_atual >= entry_price * (1 + STOP_LOSS):
                enviar_telegram(f"❌ *Stop Loss HIT*
Preço: {preco_atual}")
                stop_count += 1
                return
        time.sleep(10)
