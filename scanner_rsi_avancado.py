
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD

# ========== CONFIGURAÇÕES ==========
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
    'CFG/USDT', 'PABLO/USDT'  # Arctic Pablo Coin como exemplo
]

TIMEFRAMES = ['15m', '1h', '4h', '1d', '1w']
VOLUME_MEDIA_PERIOD = 20

def enviar_alerta(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except:
        pass

def analisar_ativo(symbol, timeframe):
    try:
        ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=50)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
        df['ema200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
        macd = MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['volume_ma'] = df['volume'].rolling(VOLUME_MEDIA_PERIOD).mean()

        rsi_atual = df['rsi'].iloc[-1]
        volume_atual = df['volume'].iloc[-1]
        volume_ma = df['volume_ma'].iloc[-1]
        preco_atual = df['close'].iloc[-1]
        ema200 = df['ema200'].iloc[-1]
        macd_val = df['macd'].iloc[-1]
        macd_sig = df['macd_signal'].iloc[-1]

        alerta = None

        if rsi_atual < 25:
            if volume_atual < volume_ma:
                alerta = f"🟢 *RSI < 25 + Volume Baixo*
🪙 {symbol} | ⏱ {timeframe}
📉 RSI: {rsi_atual:.2f} | 📦 Volume: {volume_atual:.2f} < Média: {volume_ma:.2f}"
            elif preco_atual > ema200:
                alerta = f"🟢 *RSI < 25 + Acima da EMA200*
🪙 {symbol} | ⏱ {timeframe}
📉 RSI: {rsi_atual:.2f} | 📈 EMA200: {ema200:.2f}"
            elif macd_val > macd_sig:
                alerta = f"🟢 *RSI < 25 + MACD Cruzando pra Cima*
🪙 {symbol} | ⏱ {timeframe}
📉 RSI: {rsi_atual:.2f} | 📊 MACD: {macd_val:.2f} > Sinal: {macd_sig:.2f}"
            else:
                alerta = f"🟢 *RSI abaixo de 25*
🪙 {symbol} | ⏱ {timeframe}
📉 RSI: {rsi_atual:.2f}"

        elif rsi_atual > 75:
            alerta = f"🔴 *RSI acima de 75*
🪙 {symbol} | ⏱ {timeframe}
📈 RSI: {rsi_atual:.2f}"

        if alerta:
            enviar_alerta(alerta)

    except Exception as e:
        print(f"Erro ao analisar {symbol} ({timeframe}):", e)

# ========== LOOP PRINCIPAL ==========
while True:
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            analisar_ativo(symbol, tf)
    print("✅ Análise concluída. Aguardando próximo ciclo...")
    time.sleep(900)  # 15 minutos
