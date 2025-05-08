
import openai
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

OPENAI_KEY = os.getenv("OPENAI_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def gerar_frase():
    openai.api_key = OPENAI_KEY
    prompt = "Crie uma frase curta, poética e profunda sobre gratidão e espiritualidade. Estilo @GratidãoDiária. No máximo 30 palavras."
    resposta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um escritor espiritual profundo."},
            {"role": "user", "content": prompt}
        ]
    )
    return resposta.choices[0].message["content"].strip()

def gerar_imagem_base():
    url = "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert("RGBA")

def escrever_frase_na_imagem(img, frase):
    largura, altura = img.size
    draw = ImageDraw.Draw(img)
    try:
        fonte = ImageFont.truetype("arial.ttf", 48)
    except:
        fonte = ImageFont.load_default()
    texto_largura, texto_altura = draw.textsize(frase, font=fonte)
    posicao = ((largura - texto_largura) / 2, altura * 0.7)
    draw.text((posicao[0] + 2, posicao[1] + 2), frase, font=fonte, fill="black")
    draw.text(posicao, frase, font=fonte, fill="white")
    return img

def enviar_para_telegram(img):
    bio = BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {"photo": bio}
    data = {"chat_id": TELEGRAM_CHAT_ID, "caption": ""}
    response = requests.post(url, files=files, data=data)
    return response.json()

def bot_conteudo_gratidao():
    frase = gerar_frase()
    print("Frase gerada:", frase)
    imagem_base = gerar_imagem_base()
    imagem_final = escrever_frase_na_imagem(imagem_base, frase)
    resultado = enviar_para_telegram(imagem_final)
    print("Enviado para Telegram:", resultado)

bot_conteudo_gratidao()
