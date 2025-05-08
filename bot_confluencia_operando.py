
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime

# =================== CONFIG ======================
API_KEY = "Ur51ZGEGGYPYZBLlen"
API_SECRET = "Ur51ZGEGGYPYZBLlen"
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YX5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002515365072"
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
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Erro Telegram: {response.text}")
    except Exception as e:
        print(f"Erro ao enviar mensagem Telegram: {e}")

def obter_dados(symbol, timeframe='15m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calcular_valor_entrada():
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    return round(usdt * PERCENT_CAPITAL, 2)

def detectar_padrao_reversao(df):
    ultimo = df.iloc[-1]
    anterior = df.iloc[-2]
    corpo = abs(ultimo['close'] - ultimo['open'])
    sombra_inferior = ultimo['open'] - ultimo['low'] if ultimo['open'] > ultimo['close'] else ultimo['close'] - ultimo['low']
    return sombra_inferior > corpo * 2

def detectar_volume(df):
    volumes = df['volume'][-6:-1]
    return df['volume'].iloc[-1] > volumes.mean()

def detectar_ema(df):
    ema = EMAIndicator(close=df['close'], window=200).ema_indicator()
    return df['close'].iloc[-1] > ema.iloc[-1]

def detectar_rsi(df):
    rsi = RSIIndicator(close=df['close'], window=14).rsi()
    rsi_valor = rsi.iloc[-1]
    if rsi_valor < 25:
        return 'long', rsi_valor
    elif rsi_valor > 75:
        return 'short', rsi_valor
    return None, rsi_valor

def esta_proximo_zona(df, percentual=0.01):
    suporte = min(df['low'])
    resistencia = max(df['high'])
    preco_atual = df['close'].iloc[-1]
    if abs(preco_atual - suporte) / suporte < percentual:
        return 'suporte'
    elif abs(preco_atual - resistencia) / resistencia < percentual:
        return 'resistencia'
    return None

def executar_trade(symbol, direcao, amount):
    order = exchange.create_market_order(symbol, 'buy' if direcao == 'long' else 'sell', amount)
    return order

def monitorar_trade(symbol, entry_price, direcao):
    global stop_count
    while True:
        preco_atual = exchange.fetch_ticker(symbol)['last']
        if direcao == 'long':
            if preco_atual >= entry_price * (1 + TAKE_PROFIT):
                enviar_telegram(f"✅ *TAKE PROFIT* em {symbol}\n💰 Preço: {preco_atual:.4f}")
                return
            elif preco_atual <= entry_price * (1 - STOP_LOSS):
                enviar_telegram(f"❌ *STOP LOSS* em {symbol}\n💸 Preço: {preco_atual:.4f}")
                stop_count += 1
                return
        else:
            if preco_atual <= entry_price * (1 - TAKE_PROFIT):
                enviar_telegram(f"✅ *TAKE PROFIT* em {symbol} (SHORT)\n💰 Preço: {preco_atual:.4f}")
                return
            elif preco_atual >= entry_price * (1 + STOP_LOSS):
                enviar_telegram(f"❌ *STOP LOSS* em {symbol} (SHORT)\n💸 Preço: {preco_atual:.4f}")
                stop_count += 1
                return
        time.sleep(10)

# =================== LOOP PRINCIPAL ======================
markets = exchange.load_markets()
top_symbols = [s for s in markets if '/USDT' in s and markets[s]['active'] and markets[s]['info']['quoteCurrency'] == 'USDT']
top_symbols = top_symbols[:50]  # analisa as 50 primeiras

for symbol in top_symbols:
    if stop_count >= STOP_LIMIT:
        enviar_telegram("🚫 *STOP diário atingido.* Pausando operações.")
        break
    try:
        df = obter_dados(symbol)
        direcao_rsi, rsi_valor = detectar_rsi(df)
        if not direcao_rsi:
            continue

        score = 0
        criterios = []

        if direcao_rsi:
            score += 1
            criterios.append(f"RSI: {rsi_valor:.2f}")

        if detectar_padrao_reversao(df):
            score += 1
            criterios.append("Candle de reversão")

        if detectar_volume(df):
            score += 1
            criterios.append("Volume alto")

        if detectar_ema(df) and direcao_rsi == 'long':
            score += 1
            criterios.append("Acima da EMA200")
        elif not detectar_ema(df) and direcao_rsi == 'short':
            score += 1
            criterios.append("Abaixo da EMA200")

        zona = esta_proximo_zona(df)
        if zona:
            score += 1
            criterios.append(f"Perto de {zona}")

        if score >= 3:
            valor = calcular_valor_entrada()
            if valor < 5:
                continue
            executar_trade(symbol, direcao_rsi, valor)
            enviar_telegram(f"🚀 *ORDEM EXECUTADA*
📈 {symbol} | {direcao_rsi.upper()} | Valor: ${valor}
📊 Critérios: {', '.join(criterios)}")
            monitorar_trade(symbol, df['close'].iloc[-1], direcao_rsi)
    except Exception as e:
        enviar_telegram(f"⚠️ Erro em {symbol}: {str(e)}")
        time.sleep(5)
