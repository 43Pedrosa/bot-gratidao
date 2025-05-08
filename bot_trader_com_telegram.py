import ccxt
import time
import requests
from datetime import datetime

# CONFIGURAÇÕES
API_KEY = "iDhcgx3LvPqkUl6ByN"
API_SECRET = "Arg9ldCHqZ6lXmMYmBVEIEskTKnF2MCaxOlf"
TELEGRAM_BOT_TOKEN = "7038936636:AAHTXNhrmBKa-vccp_YK5nK4oDYKDWeVwpw"
TELEGRAM_CHAT_ID = "-1002513565072"

PERCENT_CAPITAL = 0.3
TAKE_PROFIT = 0.03
STOP_LOSS = 0.02
STOP_LIMIT = 2

def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Erro ao enviar para Telegram:", e)

def gerar_alerta_telegram(tipo, symbol, quantidade, preco):
    if tipo == "compra":
        return f"📈 *[COMPRA]* `{symbol}`\n💰 *Quantidade:* `{quantidade}`\n🎯 *Preço de entrada:* `${preco}`\n✅ *Ordem executada com sucesso!*\n🕒 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    if tipo == "tp":
        return f"✅ *[TAKE PROFIT]* `{symbol}`\n💰 *Preço:* `${preco}`\n📈 Lucro realizado.\n🕒 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    if tipo == "sl":
        return f"❌ *[STOP LOSS]* `{symbol}`\n💰 *Preço:* `${preco}`\n📉 Prejuízo registrado.\n🕒 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    return f"🔔 *Alerta:* {symbol} - {tipo}"

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
    "options": {"defaultType": "future"}
})

def obter_pares_abaixo_5usdt():
    exchange.load_markets()
    valid = []
    for symbol in exchange.symbols:
        try:
            market = exchange.market(symbol)
            if market.get("linear") and market.get("quote") == "USDT":
                price = exchange.fetch_ticker(symbol)["last"]
                if price < 5:
                    valid.append((symbol, price))
        except:
            continue
    return valid

def calcular_valor_operacao(price):
    balance = exchange.fetch_balance()
    usdt = balance["total"]["USDT"]
    valor_total = usdt * PERCENT_CAPITAL
    amount = valor_total / price
    return round(amount, 3)

def definir_alavancagem(symbol):
    try:
        exchange.set_leverage(3, symbol)
    except:
        pass

def executar_ordem(symbol, direction, amount, preco_entrada):
    side = "buy" if direction == "long" else "sell"
    try:
        definir_alavancagem(symbol)
        exchange.create_market_order(symbol, side, amount)
        msg = gerar_alerta_telegram("compra", symbol, amount, preco_entrada)
        enviar_telegram(msg)
    except Exception as e:
        enviar_telegram(f"⚠️ Erro na ordem para {symbol}: {str(e)}")

def monitorar_operacao(symbol, preco_entrada, direction):
    global stop_count
    while True:
        preco = exchange.fetch_ticker(symbol)["last"]
        if direction == "long":
            if preco >= preco_entrada * (1 + TAKE_PROFIT):
                enviar_telegram(gerar_alerta_telegram("tp", symbol, 0, preco))
                return
            elif preco <= preco_entrada * (1 - STOP_LOSS):
                enviar_telegram(gerar_alerta_telegram("sl", symbol, 0, preco))
                stop_count += 1
                return
        time.sleep(5)

# EXECUÇÃO
stop_count = 0
pares_validos = obter_pares_abaixo_5usdt()

for symbol, preco in pares_validos:
    if stop_count >= STOP_LIMIT:
        enviar_telegram("🚫 Limite de STOP atingido. Encerrando operações por hoje.")
        break
    try:
        amount = calcular_valor_operacao(preco)
        executar_ordem(symbol, "long", amount, preco)
        monitorar_operacao(symbol, preco, "long")
    except Exception as e:
        enviar_telegram(f"Erro com {symbol}: {str(e)}")
        continue