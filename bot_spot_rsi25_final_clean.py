
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from datetime import datetime

# === CONFIGURAÇÕES ===
API_KEY = 'SUA_API_KEY'
API_SECRET = 'SEU_API_SECRET'
TELEGRAM_TOKEN = 'SEU_TOKEN_TELEGRAM'
TELEGRAM_CHAT_ID = 'SEU_CHAT_ID'
VOLUME_MINIMO_USDT = 20000
INTERVALO_CHECAGEM = 60  # segundos
LUCRO_MINIMO_PCT = 7
PORCENTAGEM_CAPITAL = 0.9

exchange = ccxt.bybit({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

par_em_operacao = None
preco_entrada = 0
quantidade_comprada = 0

def enviar_telegram(mensagem):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': mensagem, 'parse_mode': 'Markdown'}
    requests.post(url, data=data)

def calcular_rsi(dados, periodo=14):
    fechamento = dados['close']
    rsi = RSIIndicator(close=fechamento, window=periodo).rsi()
    return rsi.iloc[-1]

def candle_reversao(df):
    ultimo = df.iloc[-2]
    corpo = abs(ultimo['close'] - ultimo['open'])
    sombra = ultimo['high'] - ultimo['low']
    return corpo < (sombra * 0.3)

def obter_resistencia(df):
    return df['high'][-5:].max()

def buscar_pares():
    tickers = exchange.fetch_tickers()
    return [par for par, info in tickers.items() if par.endswith('/USDT') and info['quoteVolume'] and info['quoteVolume'] > VOLUME_MINIMO_USDT]

def obter_dados(par):
    ohlcv = exchange.fetch_ohlcv(par, timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def main():
    global par_em_operacao, preco_entrada, quantidade_comprada

    while True:
        try:
            if par_em_operacao:
                df = obter_dados(par_em_operacao)
                preco_atual = df['close'].iloc[-1]
                resistencia = obter_resistencia(df)
                lucro_pct = ((preco_atual - preco_entrada) / preco_entrada) * 100

                if lucro_pct >= LUCRO_MINIMO_PCT or candle_reversao(df) or preco_atual >= resistencia:
                    exchange.create_market_sell_order(par_em_operacao, quantidade_comprada)
                    mensagem = f"✅ *SAÍDA EXECUTADA*
*Par:* `{par_em_operacao}`
*Lucro:* `{lucro_pct:.2f}%`
*Preço:* `${preco_atual:.4f}`"
                    enviar_telegram(mensagem)
                    par_em_operacao = None
            else:
                pares = buscar_pares()
                for par in pares:
                    df = obter_dados(par)
                    rsi = calcular_rsi(df)

                    if rsi < 25:
                        saldo = exchange.fetch_balance()
                        usdt = saldo['total'].get('USDT', 0) * PORCENTAGEM_CAPITAL
                        if usdt > 5:
                            preco = df['close'].iloc[-1]
                            quantidade = round(usdt / preco, 4)
                            exchange.create_market_buy_order(par, quantidade)

                            par_em_operacao = par
                            preco_entrada = preco
                            quantidade_comprada = quantidade

                            mensagem = f"🚨 *ENTRADA EXECUTADA*
*Par:* `{par}`
*RSI:* `{rsi:.2f}`
*Preço:* `${preco:.4f}`
*Quantidade:* `{quantidade}`"
                            enviar_telegram(mensagem)
                            break
            time.sleep(INTERVALO_CHECAGEM)
        except Exception as e:
            print(f"[Erro] {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
