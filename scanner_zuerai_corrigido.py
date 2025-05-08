
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
from datetime import datetime

TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YX5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "6142033408"
API_KEY = "Ur51ZGEGGYPYZBLlen"
API_SECRET = "QqcTJwHyT5FQWwC53CtRDJ577D5CmIxRUnTa"

EXCHANGE = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET
})

SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'MKR/USDT', 'HYPE/USDT',
    'PLUME/USDT', 'PENDLE/USDT', 'ONDO/USDT', 'NEAR/USDT',
    'CFG/USDT', 'PABLO/USDT'
]

TIMEFRAMES = ['15m', '1h']
VOLUME_MEDIA_PERIOD = 20
alertas_enviados = set()

def enviar_alerta(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar alerta:", e)

def detectar_padrao(df):
    open_, close, high, low = df['open'].iloc[-1], df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    corpo = abs(close - open_)
    sombra_inferior = open_ - low if close > open_ else close - low
    sombra_superior = high - close if close > open_ else high - open_

    if corpo < sombra_inferior and sombra_inferior > 2 * corpo:
        return "Martelo"
    elif corpo < sombra_superior and sombra_superior > 2 * corpo:
        return "Shooting Star"
    elif df['close'].iloc[-2] < df['open'].iloc[-2] and close > open_ and open_ < df['close'].iloc[-2] and close > df['open'].iloc[-2]:
        return "Engolfo de Alta"
    elif df['close'].iloc[-2] > df['open'].iloc[-2] and close < open_ and open_ > df['close'].iloc[-2] and close < df['open'].iloc[-2]:
        return "Engolfo de Baixa"
    return None

def analisar_ativo(symbol):
    try:
        dados = {}
        for tf in TIMEFRAMES:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, tf, limit=250)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
            df['ema200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
            macd = MACD(close=df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['volume_ma'] = df['volume'].rolling(VOLUME_MEDIA_PERIOD).mean()
            dados[tf] = df

        rsi_15m = dados['15m']['rsi'].iloc[-1]
        rsi_1h = dados['1h']['rsi'].iloc[-1]
        preco = dados['15m']['close'].iloc[-1]
        volume = dados['15m']['volume'].iloc[-1]
        volume_ma = dados['15m']['volume_ma'].iloc[-1]
        ema200 = dados['15m']['ema200'].iloc[-1]
        macd_val = dados['15m']['macd'].iloc[-1]
        macd_sig = dados['15m']['macd_signal'].iloc[-1]
        padrao = detectar_padrao(dados['15m'])

        divergencia = ""
        if rsi_1h > dados['1h']['rsi'].iloc[-2] and rsi_15m < dados['15m']['rsi'].iloc[-2]:
            divergencia = "⚠️ *Divergência: RSI 1h subindo, 15m caindo*"

        timestamp = dados['15m']['timestamp'].iloc[-1]
        chave = f"{symbol}-{timestamp}"

        if chave in alertas_enviados:
            return

        alerta = ""
        if rsi_15m < 25:
            alerta += f"🟢 *RSI abaixo de 25*\n🪙 {symbol} | ⏱ 15m\n📉 RSI: {rsi_15m:.2f}"
        elif rsi_15m > 75:
            alerta += f"🔴 *RSI acima de 75*\n🪙 {symbol} | ⏱ 15m\n📈 RSI: {rsi_15m:.2f}"

        if alerta:
            if padrao:
                alerta += f"\n🕯 *Padrão: {padrao}*"
            if divergencia:
                alerta += f"\n{divergencia}"
            if volume < volume_ma:
                alerta += f"\n📦 Volume abaixo da média: {volume:.2f} < {volume_ma:.2f}"
            if preco > ema200:
                alerta += f"\n📈 Acima da EMA200: {preco:.2f} > {ema200:.2f}"
            if macd_val > macd_sig:
                alerta += f"\n📊 MACD cruzando pra cima: {macd_val:.2f} > {macd_sig:.2f}"

            enviar_alerta(alerta)
            alertas_enviados.add(chave)

    except Exception as e:
        print(f"Erro ao analisar {symbol}:", e)

print("🤖 Scanner ZUERAI v2 iniciado...")
while True:
    for symbol in SYMBOLS:
        analisar_ativo(symbol)
    print(f"✅ Análise completa às {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(900)
