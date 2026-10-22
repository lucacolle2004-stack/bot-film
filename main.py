import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import gspread

# Configurazione log
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Connessione al Foglio Google tramite il file credentials.json
gc = gspread.service_account(filename='credentials.json')
sh = gc.open('Classifica Film Giada e Luca')
worksheet = sh.get_worksheet(0)

# Criteri di valutazione aggiornati (con "Coinvolgimento")
CRITERI = [
    ("trama", "1/9 - Trama / Sceneggiatura"),
    ("personaggi", "2/9 - Personaggi / Interpretazioni"),
    ("impatto", "3/9 - Impatto Visivo / Atmosfera"),
    ("coinvolgimento", "4/9 - Coinvolgimento"),
    ("ritmo", "5/9 - Ritmo / Gestione del tempo"),
    ("finale", "6/9 - Finale"),
    ("rewatch", "7/9 - Fattore Re-watch (Lo rivedresti?)"),
    ("cinema", "8/9 - Valore Cinema (Ne valeva la pena?)"),
    ("animazioni", "9/9 - Animazioni / Stile Artistico"),
]

# Dizionario temporaneo per i voti
user_data_temp = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao Luca e Giada! 🍿 Sono pronto per raccogliere le vostre recensioni.\n\n"
        "Usa il comando **/vota** per iniziare a valutare un film o una serie TV!"
    )

async def avvia_voto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data_temp[update.effective_user.id] = {"voti": {}}
    await update.message.reply_text("Inserisci il **Titolo** del film o della serie TV che volete valutare:")
    context.user_data['stato'] = 'ATTESA_TITOLO'

async def gestisci_messaggi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stato = context.user_data.get('stato')

    if stato == 'ATTESA_TITOLO':
        titolo = update.message.text
        user_data_temp[user_id]["titolo"] = titolo
        
        # Scegli se Film o Serie TV/Anime
        keyboard = [
            [InlineKeyboardButton("🎬 Film", callback_data="tipo_Film"),
             InlineKeyboardButton("📺 Serie TV / Anime", callback_data="tipo_Serie")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Hai scelto: **{titolo}**. Di cosa si tratta?", reply_markup=reply_markup, parse_mode="Markdown")
        context.user_data['stato'] = None

async def gestisci_pulsanti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("tipo_"):
        tipo = data.split("_")[1]
        user_data_temp[user_id]["tipo"] = tipo
        await mostra_scelta_voto(query, 0)

    elif data.startswith("voto_"):
        parts = data.split("_")
        criterio_idx = int(parts[1])
        voto = int(parts[2])

        criterio_chiave = CRITERI[criterio_idx][0]
        user_data_temp[user_id]["voti"][criterio_chiave] = voto

        successivo_idx = criterio_idx + 1
        if successivo_idx < len(CRITERI):
            await mostra_scelta_voto(query, successivo_idx)
        else:
            # Finito! Calcoliamo la media e salviamo sul Foglio Google
            dati = user_data_temp[user_id]
            titolo = dati["titolo"]
            tipo = dati["tipo"]
            voti = dati["voti"]

            lista_voti = [voti[c[0]] for c in CRITERI]
            media_totale = round(sum(lista_voti) / len(lista_voti), 2)

            # Scrive i dati sul Foglio Google
            riga = [titolo, tipo] + lista_voti + [media_totale]
            worksheet.append_row(riga)

            await query.edit_message_text(
                f"✅ **Recensione salvata con successo nel Foglio Google!**\n\n"
                f"📌 **Titolo:** {titolo} ({tipo})\n"
                f"⭐ **Media Totale:** {media_totale}/10"
            )

async def mostra_scelta_voto(query, indice_criterio):
    criterio_chiave, criterio_testo = CRITERI[indice_criterio]
    
    # Pulsanti da 1 a 10
    riga1 = [InlineKeyboardButton(str(i), callback_data=f"voto_{indice_criterio}_{i}") for i in range(1, 6)]
    riga2 = [InlineKeyboardButton(str(i), callback_data=f"voto_{indice_criterio}_{i}") for i in range(6, 11)]
    
    keyboard = [riga1, riga2]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"Valuta per:\n🔹 **{criterio_testo}**",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    # INCOLLA QUI IL TOKEN DEL TUO BOT RICEVUTO DA BOTFATHER TRA LE VIRGOLETTE
    TOKEN = "8944828789:AAGp4sBP9ZOtu5N70WiWXj2IVwjhCHKJTHs"
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vota", avvia_voto))
    app.add_handler(CallbackQueryHandler(gestisci_pulsanti))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), gestisci_messaggi))

    print("Bot avviato e pronto per Luca e Giada...")
    app.run_polling()
