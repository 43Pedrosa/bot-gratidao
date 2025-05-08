
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# ========== CONFIG ==========
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YX5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002513565072"
API_KEY = "Ur51ZGEGGYPYZBLlen"
API_SECRET = "QqcTJwHyT5FQWwC53CtRDJ577D5CmIxRUnTa"

EXCHANGE = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

TIMEFRAMES = ['15m', '1h']
alertas_enviados = set()

def enviar_alerta(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except:
        print("Erro ao enviar alerta")

def detectar_padrao(df):
    if len(df) < 3:
        return None
    corpo = df['close'] - df['open']
    sombra_sup = df['high'] - df[['close', 'open']].max(axis=1)
    sombra_inf = df[['close', 'open']].min(axis=1) - df['low']
    if corpo.iloc[-1] > 0 and corpo.iloc[-2] < 0 and df['open'].iloc[-1] < df['close'].iloc[-2]:
        return "ENGOLFO DE ALTA"
    elif corpo.iloc[-1] < 0 and corpo.iloc[-2] > 0 and df['open'].iloc[-1] > df['close'].iloc[-2]:
        return "ENGOLFO DE BAIXA"
    elif sombra_inf.iloc[-1] > abs(corpo.iloc[-1]) * 2 and corpo.iloc[-1] > 0:
        return "MARTELINHO"
    return None

def obter_top_50_usdt():
    mercados = EXCHANGE.load_markets()
    lista = []
    for symbol, info in mercados.items():
        if symbol.endswith('/USDT') and info.get('active', False):
            vol = float(info['info'].get('volume24h', 0))
            lista.append((symbol, vol))
    lista.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in lista[:50]]

def analisar(symbol):
    try:
        df15 = pd.DataFrame(EXCHANGE.fetch_ohlcv(symbol, '15m', limit=250),
                            columns=['timestamp','open','high','low','close','volume'])
        df1h = pd.DataFrame(EXCHANGE.fetch_ohlcv(symbol, '1h', limit=250),
                            columns=['timestamp','open','high','low','close','volume'])

        df15['rsi'] = RSIIndicator(close=df15['close'], window=14).rsi()
        df15['ema200'] = EMAIndicator(close=df15['close'], window=200).ema_indicator()
        df1h['rsi'] = RSIIndicator(close=df1h['close'], window=14).rsi()

        rsi_15m = df15['rsi'].iloc[-1]
        rsi_1h = df1h['rsi'].iloc[-1]
        preco = df15['close'].iloc[-1]
        ema200 = df15['ema200'].iloc[-1]
        padrao = detectar_padrao(df15)
        chave = f"{symbol}-{rsi_15m:.2f}"

        mensagem = ""

        if rsi_15m < 25 or rsi_15m > 75:
            nivel = "🔥" if rsi_15m < 20 or rsi_15m > 80 else "⚠️"
            direcao = "SOBREVENDA" if rsi_15m < 25 else "SOBRECOMPRA"
            mensagem += f"{nivel} *{direcao}*
{symbol} | 15m
RSI: {rsi_15m:.2f}
"

            if preco > ema200:
                mensagem += f"📈 Acima da EMA200
"
            else:
                mensagem += f"📉 Abaixo da EMA200
"

            if rsi_1h > rsi_15m:
                mensagem += f"🔁 Divergência RSI: 1h > 15m
"

            if padrao:
                mensagem += f"🕯️ Padrão detectado: {padrao}
"

        if mensagem and chave not in alertas_enviados:
            enviar_alerta(mensagem)
            alertas_enviados.add(chave)
        elif rsi_15m >= 25 and rsi_15m <= 75:
            alertas_enviados.discard(chave)

    except Exception as e:
        print(f"Erro ao analisar {symbol}: {e}")

# ========= INÍCIO =========
enviar_alerta("🤖 Bot ZUERAI iniciado. Monitorando RSI + EMA + Candle Patterns...")

SYMBOLS = obter_top_50_usdt()

while True:
    for symbol in SYMBOLS:
        analisar(symbol)
    print("🔄 Aguardando 15 minutos...")
    time.sleep(900)
