
import ccxt
import pandas as pd
import time
import requests
from ta.momentum import RSIIndicator
from datetime import datetime

# === CONFIGURAÇÕES ===
API_KEY = 'iDhcgx3LvPqkUl6ByN'
API_SECRET = 'Arg9ldCHqZ6lXmMYmBVEIEskTKnF2MCaxOlf'
TELEGRAM_TOKEN = '7038936636:AAHTXNhrmBKa-vccp_YK5nK4oDYKDWeVwpw'
TELEGRAM_CHAT_ID = '-1002513565072'
VOLUME_MINIMO_USDT = 20000
INTERVALO_CHECAGEM = 60  # segundos
LUCRO_ALVO_PCT = 7
PERCENTUAL_CAPITAL = 0.9

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
    candle = df.iloc[-2]
    corpo = abs(candle['close'] - candle['open'])
    sombra_superior = candle['high'] - max(candle['close'], candle['open'])
    sombra_inferior = min(candle['close'], candle['open']) - candle['low']
    return sombra_inferior > corpo * 2 and sombra_superior < corpo

def verificar_resistencia(df):
    ultimos = df['high'].tail(10)
    resistencia = ultimos.max()
    return df['close'].iloc[-1] >= resistencia

def buscar_pares():
    tickers = exchange.fetch_tickers()
    pares_filtrados = []
    for par, info in tickers.items():
        if not par.endswith('/USDT'):
            continue
        if info['quoteVolume'] and info['quoteVolume'] > VOLUME_MINIMO_USDT:
            pares_filtrados.append(par)
    return pares_filtrados

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
                lucro_pct = ((preco_atual - preco_entrada) / preco_entrada) * 100

                if lucro_pct >= LUCRO_ALVO_PCT or candle_reversao(df) or verificar_resistencia(df):
                    exchange.create_market_sell_order(par_em_operacao, quantidade_comprada)
                    mensagem = (
                        f"*SAÍDA*\n"
                        f"Par: `{par_em_operacao}`\n"
                        f"Lucro: `{lucro_pct:.2f}%`\n"
                        f"Preço de Saída: `${preco_atual:.4f}`"
                    )
                    enviar_telegram(mensagem)
                    par_em_operacao = None

            else:
                pares = buscar_pares()
                for par in pares:
                    df = obter_dados(par)
                    rsi = calcular_rsi(df)
                    if rsi < 25:
                        saldo = exchange.fetch_balance()
                        usdt_disp = saldo['total']['USDT'] * PERCENTUAL_CAPITAL
                        if usdt_disp > 5:
                            preco = df['close'].iloc[-1]
                            quantidade = round(usdt_disp / preco, 4)
                            exchange.create_market_buy_order(par, quantidade)

                            par_em_operacao = par
                            preco_entrada = preco
                            quantidade_comprada = quantidade

                            mensagem = (
                                f"*ENTRADA EXECUTADA*\n"
                                f"Par: `{par}`\n"
                                f"RSI: `{rsi:.2f}`\n"
                                f"Preço de Entrada: `${preco:.4f}`\n"
                                f"Quantidade: `{quantidade}`"
                            )
                            enviar_telegram(mensagem)
                            break

            time.sleep(INTERVALO_CHECAGEM)

        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
