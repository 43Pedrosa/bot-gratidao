
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD

# ========== CONFIGURAÇÕES ==========
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YK5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002513565072"
API_KEY = "Ur51ZGEGGYPYZBLlen"
API_SECRET = "QqcTJwHyT5FQWwC53CtRDJ577D5CmIxRUnTa"

EXCHANGE = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET
})

def obter_top_100_pares(exchange):
    mercados = exchange.load_markets()
    lista = []
    for symbol, market in mercados.items():
        if symbol.endswith('/USDT') and market.get('active', False):
            volume = float(market['info'].get('volume24h', 0)) if 'volume24h' in market['info'] else 0
            lista.append((symbol, volume))
    lista.sort(key=lambda x: x[1], reverse=True)
    return [par[0] for par in lista[:100]]

SYMBOLS = obter_top_100_pares(EXCHANGE)
TIMEFRAMES = ['15m', '1h']
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
    except Exception as e:
        print("Erro ao enviar alerta:", e)

def detectar_padrao_candle(df):
    if len(df) < 3:
        return None
    corpo = df['close'] - df['open']
    sombra_superior = df['high'] - df[['close', 'open']].max(axis=1)
    sombra_inferior = df[['close', 'open']].min(axis=1) - df['low']

    if corpo.iloc[-1] > 0 and corpo.iloc[-2] < 0 and df['open'].iloc[-1] < df['close'].iloc[-2]:
        return "ENGOLFO de alta"
    elif corpo.iloc[-1] < 0 and corpo.iloc[-2] > 0 and df['open'].iloc[-1] > df['close'].iloc[-2]:
        return "ENGOLFO de baixa"
    elif sombra_inferior.iloc[-1] > corpo.iloc[-1]*2 and corpo.iloc[-1] > 0:
        return "MARTELINHO (reversão de alta)"
    elif sombra_superior.iloc[-1] > corpo.iloc[-1]*2 and corpo.iloc[-1] < 0:
        return "SHOOTING STAR (reversão de baixa)"
    return None

def analisar_ativo(symbol):
    dados_rsi = {}
    for tf in TIMEFRAMES:
        try:
            ohlcv = EXCHANGE.fetch_ohlcv(symbol, tf, limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
            df['ema200'] = EMAIndicator(close=df['close'], window=200).ema_indicator()
            macd = MACD(close=df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['volume_ma'] = df['volume'].rolling(VOLUME_MEDIA_PERIOD).mean()

            rsi = df['rsi'].iloc[-1]
            volume = df['volume'].iloc[-1]
            volume_ma = df['volume_ma'].iloc[-1]
            preco = df['close'].iloc[-1]
            ema200 = df['ema200'].iloc[-1]
            macd_val = df['macd'].iloc[-1]
            macd_sig = df['macd_signal'].iloc[-1]

            dados_rsi[tf] = rsi

            # 🔁 Confirmação RSI multi-timeframe
            if tf == '1h' and dados_rsi.get('15m', 100) < 25 and rsi < 25:
                msg = f"🔁 *Confirmação RSI*\n{symbol} com RSI < 25 em 15m e 1h\n15m: {dados_rsi['15m']:.2f} | 1h: {rsi:.2f}"
                enviar_alerta(msg)

            # ⚠️ Score baseado em múltiplos indicadores
            score = 0
            motivos = []
            if rsi < 25:
                score += 3
                motivos.append("RSI < 25")
            if volume < volume_ma:
                score += 2
                motivos.append("Volume abaixo da média")
            if macd_val > macd_sig:
                score += 2
                motivos.append("MACD cruzando pra cima")
            if preco > ema200:
                score += 1
                motivos.append("Acima da EMA200")
            padrao = detectar_padrao_candle(df)
            if padrao:
                score += 2
                motivos.append(f"Padrão: {padrao}")

            if score >= 6:
                msg = f"⚠️ *ALERTA DE CONFLUÊNCIA*\n{symbol} | Score: {score}/10\n" + "\n".join(f"• {m}" for m in motivos)
                enviar_alerta(msg)

            # 🕯️ Alerta apenas de padrão de candle
            if padrao:
                msg = f"🕯️ *Padrão detectado*\n{symbol} | {tf}\n🔍 {padrao}"
                enviar_alerta(msg)

        except Exception as e:
            print(f"Erro ao analisar {symbol} ({tf}):", e)

# ========== LOOP PRINCIPAL ==========
while True:
    for symbol in SYMBOLS:
        analisar_ativo(symbol)
    print("✅ Análise concluída. Aguardando próximo ciclo...")
    time.sleep(900)
