import telebot
from telebot import types
import os
import yt_dlp
from dotenv import load_dotenv  

load_dotenv()

CHAVE_API = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(CHAVE_API)

user_states = {} 

print("--- SOUNDWAVE BOT ---")
print("Bot rodando...")

def buscar_por_nome(termo):
    opcoes = {
        'quiet': True,
        'noplaylist': True,
        'extract_flat': True, 
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'} 
    }
    
    resultados = []
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch5:{termo}", download=False)
            if 'entries' in info:
                for video in info['entries']:
                    duracao = video.get('duration', 0)
                    resultados.append({
                        'id': video['id'],
                        'titulo': video['title'],
                        'tempo': duracao
                    })
        except Exception as e:
            print(f"Erro busca: {e}")
    return resultados

def baixar_final(url_ou_id, eh_link_direto=False):
    
    if eh_link_direto:
        link_final = url_ou_id
    else:
        link_final = f"https://www.youtube.com/watch?v={url_ou_id}"
    
    opcoes = {
        'format': 'bestaudio/best',
        'outtmpl': 'musica_temp.%(ext)s', 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128', 
        }],
        'quiet': True,
        'noplaylist': True,
        'writethumbnail': True,
        'max_filesize': None,
        'geo_bypass': True,
        'socket_timeout': 60,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    }

    if os.path.exists('ffmpeg.exe'):
        opcoes['ffmpeg_location'] = './'

    with yt_dlp.YoutubeDL(opcoes) as ydl:
        try:
            info = ydl.extract_info(link_final, download=True)
            
            capa = None
            if os.path.exists("musica_temp.jpg"): capa = "musica_temp.jpg"
            elif os.path.exists("musica_temp.webp"): capa = "musica_temp.webp"

            return "musica_temp.mp3", info['title'], info.get('duration', 0), capa
        except Exception as e:
            print(f"Erro download: {e}")
            return None, None, 0, None

def limpar_arquivos():
    for a in ["musica_temp.mp3", "musica_temp.jpg", "musica_temp.webp"]:
        if os.path.exists(a):
            try: os.remove(a)
            except: pass

# --- MENUS ---

def menu_principal():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔎 Buscar Música", callback_data='btn_escolha_tipo'))
    markup.row(types.InlineKeyboardButton("ℹ️ Sobre", callback_data='btn_sobre'))
    return markup

def menu_tipo_busca():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📝 Por Nome/Artista", callback_data='modo_nome'))
    markup.row(types.InlineKeyboardButton("🔗 Por Link (URL)", callback_data='modo_link'))
    markup.row(types.InlineKeyboardButton("⬅️ Voltar", callback_data='btn_voltar_menu'))
    return markup

def menu_resultados(lista_videos):
    markup = types.InlineKeyboardMarkup()
    for vid in lista_videos:
        segundos_totais = int(vid.get('tempo', 0) or 0)
        minutos = int(segundos_totais // 60)
        segundos = int(segundos_totais % 60)
        tempo_str = f"({minutos}:{segundos:02d})"
        
        titulo_limpo = vid['titulo'][:25] 
        texto_botao = f"🎵 {titulo_limpo}... {tempo_str}"
        markup.add(types.InlineKeyboardButton(texto_botao, callback_data=f"dl_{vid['id']}"))
        
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data='btn_cancelar'))
    return markup

def menu_cancelar():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancelar", callback_data='btn_cancelar'))
    return markup

def menu_nova_busca():
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("🔄 Menu Principal", callback_data='btn_voltar_menu'))
    return markup

def menu_voltar():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Voltar", callback_data='btn_voltar_menu'))
    return markup

# --- LÓGICA ---

@bot.message_handler(commands=['start'])
def start(mensagem):
    chat_id = mensagem.chat.id
    user_states[chat_id] = None 
    try: bot.delete_message(chat_id, mensagem.message_id)
    except: pass 

    texto = (
        "👋 **Bem-vindo ao SoundWave!**\n\n"
        "O seu assistente de música no Telegram.\n"
        "Baixe por nome ou link direto.\n\n"
        "👇 **Comece aqui:**"
    )
    
    if os.path.exists('capa.jpg'):
        with open('capa.jpg', 'rb') as foto:
            bot.send_photo(chat_id, foto, caption=texto, reply_markup=menu_principal(), parse_mode='Markdown')
    else:
        bot.send_message(chat_id, texto, reply_markup=menu_principal(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    # 1 --- MENU DE ESCOLHA DO USUARIO ---
    if call.data == 'btn_escolha_tipo':
        bot.edit_message_caption(
            "🧐 **Como você deseja pesquisar?**\n\nEscolha uma opção abaixo:", 
            chat_id, message_id, reply_markup=menu_tipo_busca(), parse_mode='Markdown'
        )

    # 2 --- QUANDO O USUARIO CLICA POR NOME ---
    elif call.data == 'modo_nome':
        user_states[chat_id] = 'esperando_nome'
        bot.edit_message_caption(
            "📝 **Digite o Nome da Música ou Artista:**", 
            chat_id, message_id, reply_markup=menu_cancelar(), parse_mode='Markdown'
        )

    # 3 --- QUANDO O USUARIO CLICA NO MODO LINK ---
    elif call.data == 'modo_link':
        user_states[chat_id] = 'esperando_link'
        bot.edit_message_caption(
            "🔗 **Cole o Link do YouTube aqui:**\n_(Ex: https://youtu.be/...)_", 
            chat_id, message_id, reply_markup=menu_cancelar(), parse_mode='Markdown'
        )

    # 4 --- MENSAGEM BAIXANDO ---   
        bot.answer_callback_query(call.id, "Baixando...") 
        video_id = call.data.split('_')[1]
        try: bot.delete_message(chat_id, message_id)
        except: pass
        
        executar_download(chat_id, video_id, eh_link=False)

    # 5 --- NAVEGAÇÃO ---
    elif call.data == 'btn_sobre':
        texto = (
            "ℹ️ **Sobre o SoundWave**\n\n"
            "🤖 **O que este bot faz?**\n"
            "O SoundWave é uma ferramenta de automação que permite baixar músicas diretamente do YouTube sem sair do Telegram.\n\n"
            "🛠 **Tecnologias Utilizadas:**\n"
            "• Linguagem: **Python 3**\n"
            "• Conversão: **FFmpeg** (Processamento de Áudio)\n"
            "• Extração: **yt-dlp** (Engenharia Reversa)\n\n"
            "👨‍💻 **Desenvolvedores:**\n"
            "Bruno Fabosa, Carlos Eduardo e Alexandre Junior\n"
            "📚 **Engenharia da Computação** (2º Semestre)"
        )
        
        try: bot.edit_message_caption(texto, chat_id, message_id, reply_markup=menu_voltar(), parse_mode='Markdown')
        except: bot.edit_message_text(texto, chat_id, message_id, reply_markup=menu_voltar(), parse_mode='Markdown')

    elif call.data == 'btn_cancelar' or call.data == 'btn_voltar_menu':
        user_states[chat_id] = None
        try: bot.delete_message(chat_id, message_id)
        except: pass
        texto = "🎧 **Menu Principal**"
        
        if os.path.exists('capa.jpg'):
            with open('capa.jpg', 'rb') as foto:
                bot.send_photo(chat_id, foto, caption=texto, reply_markup=menu_principal(), parse_mode='Markdown')
        else:
            bot.send_message(chat_id, texto, reply_markup=menu_principal(), parse_mode='Markdown')

def executar_download(chat_id, conteudo, eh_link):
    bot.send_chat_action(chat_id, 'record_audio')
    msg_status = bot.send_message(chat_id, "📥 **Baixando...** aguarde.", parse_mode='Markdown')
    
    arquivo, titulo, duracao, capa = baixar_final(conteudo, eh_link_direto=eh_link)
    
    if arquivo and os.path.exists(arquivo):
        try: bot.delete_message(chat_id, msg_status.message_id)
        except: pass
        bot.send_chat_action(chat_id, 'upload_audio')
        
        try:
            with open(arquivo, 'rb') as audio:
                thumb = open(capa, 'rb') if capa else None
                bot.send_audio(
                    chat_id, audio, title=titulo, performer="SoundWave", 
                    thumbnail=thumb, duration=duracao, 
                    caption=f"✅ **{titulo}**", parse_mode='Markdown',
                    timeout=120
                )
                if thumb: thumb.close()
            bot.send_message(chat_id, "🔄 **Deseja baixar outra?**", reply_markup=menu_nova_busca(), parse_mode='Markdown')
        except Exception as e:
            if "Entity Too Large" in str(e):
                bot.send_message(chat_id, "❌ **Arquivo muito grande (>50MB).** O Telegram não aceitou.", reply_markup=menu_nova_busca())
            else:
                bot.send_message(chat_id, "❌ Erro no envio.", reply_markup=menu_nova_busca())
    else:
        bot.edit_message_text("❌ Erro ao baixar (Link inválido ou privado).", chat_id, msg_status.message_id, reply_markup=menu_nova_busca())
    
    limpar_arquivos()

@bot.message_handler(func=lambda m: True)
def receber_texto(mensagem):
    chat_id = mensagem.chat.id
    estado_atual = user_states.get(chat_id)
    

    if not estado_atual:
        try:
            bot.delete_message(chat_id, mensagem.message_id)
            aviso = bot.send_message(chat_id, "⚠️ **Use o Menu para escolher: Por Nome ou Link!**", parse_mode='Markdown')
            import time, threading
            threading.Thread(target=lambda: (time.sleep(3), bot.delete_message(chat_id, aviso.message_id))).start()
        except: pass
        return

    if estado_atual == 'esperando_nome':
        bot.send_chat_action(chat_id, 'typing')
        msg_buscando = bot.send_message(chat_id, f"🔎 Pesquisando: `{mensagem.text}`...", parse_mode='Markdown')
        try:
            lista = buscar_por_nome(mensagem.text)
            if lista:
                bot.delete_message(chat_id, msg_buscando.message_id)
                bot.send_message(chat_id, "👇 **Resultados encontrados:**", reply_markup=menu_resultados(lista))
                user_states[chat_id] = None 
            else:
                bot.edit_message_text("❌ Nada encontrado.", chat_id, msg_buscando.message_id, reply_markup=menu_cancelar())
        except:
            bot.send_message(chat_id, "Erro na busca.")

    elif estado_atual == 'esperando_link':
        if "http" not in mensagem.text:
            bot.reply_to(mensagem, "⚠️ Isso não parece um link. Tente novamente ou clique em Cancelar.")
            return

        try: bot.delete_message(chat_id, mensagem.message_id)
        except: pass
        
        executar_download(chat_id, mensagem.text, eh_link=True)
        user_states[chat_id] = None 

bot.infinity_polling(timeout=20, long_polling_timeout=10)

# Integrantes do grupo: Bruno Fabosa dos Santos - Carlos Eduardo da Silva Oliveira - Alexandre dos Santos Junior #
