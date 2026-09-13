"""
Bot de prognósticos com desbloqueio pago via MB Way (confirmação manual).

Comandos de admin (só funcionam para TELEGRAM_ADMIN_ID):
  /novo -> inicia o fluxo de criação de um prognóstico (conversa passo a passo)
  /resultado <id> green|red|anulado -> marca o resultado
  /stats -> mostra taxa de acerto e ROI atuais

Fluxo do utilizador comum:
  1. Vê o prognóstico bloqueado no grupo (odd da Betano visível, resto escondido)
  2. Clica em "🔓 Desbloquear por 2€"
  3. Bot manda-lhe o número de MB Way + uma referência única, em privado
  4. O utilizador paga por fora (app do banco/MB Way)
  5. O admin recebe uma notificação com botões para confirmar o pagamento na Revolut
  6. Assim que o admin confirma, o bot envia automaticamente o conteúdo completo
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import db

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID", "0"))
GRUPO_ID = int(os.getenv("TELEGRAM_GRUPO_ID", "0"))
MBWAY_NUMERO = os.getenv("MBWAY_NUMERO", "9XX XXX XXX")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ---------- Mensagem fixada no canal com estatísticas sempre atualizadas ----------

async def atualizar_mensagem_fixada():
    stats = db.get_estatisticas()
    if not stats["total_prognosticos"] or not (stats["total_greens"] or stats["total_reds"]):
        return  # ainda sem histórico, não há o que mostrar

    tipo_seq, contagem_seq = db.get_sequencia_atual()
    emoji_seq = "✅" if tipo_seq == "green" else "❌"
    linha_sequencia = f"🔥 Sequência atual: {contagem_seq} {emoji_seq}\n" if contagem_seq > 0 else ""

    data_inicio = db.get_data_inicio_historico()
    linha_data = f"📅 Desde: {data_inicio}\n" if data_inicio else ""

    texto = (
        f"📊 <b>Estatísticas do canal</b>\n\n"
        f"✅ Taxa de acerto: <b>{stats['taxa_acerto_pct']}%</b> "
        f"({stats['total_greens']}✅-{stats['total_reds']}❌)\n"
        f"📈 ROI: <b>{stats['roi_pct']}%</b>\n"
        f"{linha_sequencia}"
        f"{linha_data}"
    )

    message_id = db.get_config("stats_message_id")
    if message_id:
        try:
            await bot.edit_message_text(chat_id=GRUPO_ID, message_id=int(message_id), text=texto, parse_mode="HTML")
            return
        except Exception:
            pass  # mensagem pode ter sido apagada — cria uma nova abaixo

    sent = await bot.send_message(GRUPO_ID, texto, parse_mode="HTML")
    db.set_config("stats_message_id", str(sent.message_id))
    try:
        await bot.pin_chat_message(GRUPO_ID, sent.message_id, disable_notification=True)
    except Exception:
        await bot.send_message(
            ADMIN_ID,
            "⚠️ Não consegui fixar a mensagem de estatísticas no canal — "
            "confirma que o bot tem a permissão 'Fixar Mensagens' como administrador do canal.",
        )


# ---------- Comando /start (confirmação de que o bot está ativo) ----------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "✅ Bot ativo!\n\n"
            "Comandos disponíveis:\n"
            "/novo — publicar um prognóstico novo\n"
            "/pendentes — ver prognósticos ainda sem resultado marcado\n"
            "/stats — ver taxa de acerto e ROI\n"
            "/resultado <id> green|red|anulado — marcar resultado"
        )
    else:
        await message.answer(
            "👋 Bem-vindo ao BetOverTwo!\n\n"
            "📋 <b>Como funciona:</b>\n"
            "• Prognósticos de jogos de futebol de todas as ligas do mundo\n"
            "• Jogos com muitos golos — odds a partir de 1.75\n"
            "• Mercados: <b>Ambas Marcam + 2.5 Golos</b> ou <b>Ambas Marcam + 3.5 Golos</b>\n"
            "• Cada prognóstico custa <b>2€</b>\n"
            "• Publicados com <b>24h de antecedência</b> em relação ao jogo\n"
            "• O prognóstico só é enviado em <b>mensagem privada</b>, e só depois "
            "do pagamento confirmado\n\n"
            "Os prognósticos são publicados no canal, bloqueados. "
            "Quando quiseres desbloquear um, clica no botão da mensagem — "
            "envio-te aqui as instruções de pagamento.",
            parse_mode="HTML",
        )


# ---------- Criação de prognóstico (fluxo de admin) ----------

class NovoPrognostico(StatesGroup):
    liga = State()
    odd = State()
    data = State()
    mercado = State()
    foto = State()
    preco = State()


@dp.message(Command("novo"))
async def novo_prognostico_inicio(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.set_state(NovoPrognostico.liga)
    await message.answer("Qual a liga? (ex: La Liga)")


@dp.message(NovoPrognostico.liga)
async def novo_liga(message: Message, state: FSMContext):
    await state.update_data(liga=message.text.strip())
    await state.set_state(NovoPrognostico.odd)
    await message.answer("Odd na Betano? (ex: 1.85)")


@dp.message(NovoPrognostico.odd)
async def novo_odd(message: Message, state: FSMContext):
    try:
        odd = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Odd inválida, tenta outra vez (ex: 1.85)")
        return
    await state.update_data(odd_betano=odd)
    await state.set_state(NovoPrognostico.data)
    await message.answer("Data do jogo? (ex: 13/09)")


@dp.message(NovoPrognostico.data)
async def novo_data(message: Message, state: FSMContext):
    await state.update_data(data_hora_jogo=message.text.strip())
    await state.set_state(NovoPrognostico.mercado)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ambas Marcam + 2.5 Golos", callback_data="mercado:AM+2.5")],
        [InlineKeyboardButton(text="Ambas Marcam + 3.5 Golos", callback_data="mercado:AM+3.5")],
    ])
    await message.answer("Qual o mercado?", reply_markup=kb)


@dp.callback_query(NovoPrognostico.mercado, F.data.startswith("mercado:"))
async def novo_mercado_callback(callback: CallbackQuery, state: FSMContext):
    mercado = callback.data.split(":", 1)[1]
    await state.update_data(mercado=mercado)
    await state.set_state(NovoPrognostico.foto)
    await callback.message.edit_text(f"Mercado escolhido: {mercado} ✅")
    await callback.message.answer("Agora envia a imagem do prognóstico 📸")
    await callback.answer()


@dp.message(NovoPrognostico.foto, F.photo)
async def novo_foto(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id  # maior resolução disponível
    await state.update_data(conteudo_completo=file_id)
    await state.set_state(NovoPrognostico.preco)
    await message.answer("Imagem recebida ✅\nPreço de desbloqueio em € (Enter para usar 2.00):")


@dp.message(NovoPrognostico.foto)
async def novo_foto_invalida(message: Message, state: FSMContext):
    await message.answer("Preciso mesmo de uma imagem — usa o clip 📎 e envia uma foto.")


@dp.message(NovoPrognostico.preco)
async def novo_preco(message: Message, state: FSMContext):
    texto = message.text.strip().replace("€", "").replace(",", ".").strip()
    if texto == "":
        preco = 2.00
    else:
        try:
            preco = float(texto)
        except ValueError:
            await message.answer("Não percebi esse valor. Escreve só o número, ex: 2 ou 2.50 (sem símbolo de euro).")
            return
    dados = await state.get_data()
    await state.clear()

    from datetime import date
    prog_id = db.criar_prognostico(
        data_jogo=date.today().isoformat(),
        liga=dados.get("liga", ""), equipa_casa="", equipa_fora="",
        mercado=dados.get("mercado", ""),
        odd_betano=dados["odd_betano"],
        conteudo_completo=dados["conteudo_completo"],
        data_hora_jogo=dados.get("data_hora_jogo", ""),
        tipo_conteudo="foto",
        preco_desbloqueio=preco,
    )

    stats = db.get_estatisticas()
    linha_stats = ""
    if stats["total_prognosticos"] and stats["total_prognosticos"] > 0 and (stats["total_greens"] or stats["total_reds"]):
        linha_stats = (
            f"📈 Taxa de acerto: {stats['taxa_acerto_pct']}% | ROI: {stats['roi_pct']}%\n\n"
        )

    texto_grupo = (
        f"🔒 <b>Prognóstico</b>\n"
        f"🏆 {dados.get('liga', '')}\n"
        f"📅 {dados.get('data_hora_jogo', '')}\n"
        f"🎯 Mercado: {dados.get('mercado', '')}\n"
        f"📊 Odd (Betano): <b>{dados['odd_betano']}</b>\n\n"
        f"{linha_stats}"
        f"Desbloqueia por {preco:.2f}€ 👇"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"🔓 Desbloquear por {preco:.2f}€",
            callback_data=f"desbloquear:{prog_id}",
        )
    ]])
    sent = await bot.send_message(GRUPO_ID, texto_grupo, reply_markup=kb, parse_mode="HTML")

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE prognosticos SET mensagem_id_grupo = ?, publicado_em = CURRENT_TIMESTAMP WHERE id = ?",
            (sent.message_id, prog_id),
        )

    await message.answer(f"✅ Prognóstico #{prog_id} publicado no grupo.")


# ---------- Função auxiliar: envia o conteúdo, seja texto ou foto ----------

async def enviar_conteudo(chat_id: int, prog, prefixo: str = ""):
    if prog["tipo_conteudo"] == "foto":
        await bot.send_photo(chat_id, prog["conteudo_completo"], caption=prefixo or None)
    else:
        texto = f"{prefixo}\n\n{prog['conteudo_completo']}" if prefixo else prog["conteudo_completo"]
        await bot.send_message(chat_id, texto)


# ---------- Botão de desbloqueio ----------

@dp.callback_query(F.data.startswith("desbloquear:"))
async def callback_desbloquear(callback: CallbackQuery):
    prognostico_id = int(callback.data.split(":")[1])
    prog = db.get_prognostico(prognostico_id)
    if not prog:
        await callback.answer("Prognóstico não encontrado.", show_alert=True)
        return

    utilizador_id = db.get_or_create_utilizador(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )

    # Já pagou antes? reenvia o conteúdo sem pedir pagamento outra vez
    with db.get_conn() as conn:
        ja_pago = conn.execute(
            """SELECT 1 FROM desbloqueios
               WHERE utilizador_id = ? AND prognostico_id = ? AND estado = 'pago'""",
            (utilizador_id, prognostico_id),
        ).fetchone()
    if ja_pago:
        await enviar_conteudo(callback.from_user.id, prog)
        await callback.answer("Já tinhas desbloqueado — reenviado em privado.")
        return

    # Referência curta, aleatória (não revela quantos prognósticos já existem)
    import secrets
    referencia = f"REF{secrets.token_hex(3).upper()}"

    try:
        desbloqueio_id = db.criar_desbloqueio(
            utilizador_id, prognostico_id, referencia, prog["preco_desbloqueio"]
        )
    except Exception:
        # já existe um pedido pendente para este utilizador+prognóstico
        await callback.answer("Já tens um pedido de desbloqueio pendente para este prognóstico.", show_alert=True)
        return

    try:
        await bot.send_message(
            callback.from_user.id,
            f"Para desbloquear este prognóstico, envia "
            f"<b>{prog['preco_desbloqueio']:.2f}€</b> via MB Way para:\n\n"
            f"📱 <b>{MBWAY_NUMERO}</b>\n\n"
            f"Na descrição/nota do MB Way, coloca esta referência:\n"
            f"<code>{referencia}</code>\n\n"
            f"Assim que eu confirmar o pagamento, recebes o prognóstico aqui automaticamente. "
            f"Isto costuma demorar só alguns minutos.",
            parse_mode="HTML",
        )
    except Exception:
        await callback.answer(
            "Preciso que me inicies uma conversa privada primeiro (clica em Start no bot).",
            show_alert=True,
        )
        return

    await callback.answer("Enviei-te as instruções de pagamento em privado 👍")

    # Notifica o admin com botões para confirmar/rejeitar
    kb_admin = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Confirmar pagamento", callback_data=f"confirmar:{desbloqueio_id}"),
        InlineKeyboardButton(text="❌ Ainda não recebi", callback_data=f"rejeitar:{desbloqueio_id}"),
    ]])
    await bot.send_message(
        ADMIN_ID,
        f"💰 <b>Pedido de desbloqueio</b>\n"
        f"Utilizador: {callback.from_user.full_name} (@{callback.from_user.username or 'sem username'})\n"
        f"Prognóstico: #{prognostico_id} — {prog['liga']}\n"
        f"Valor: {prog['preco_desbloqueio']:.2f}€\n"
        f"Referência a procurar na Revolut: <code>{referencia}</code>",
        reply_markup=kb_admin,
        parse_mode="HTML",
    )


# ---------- Confirmação manual do admin ----------

@dp.callback_query(F.data.startswith("confirmar:"))
async def callback_confirmar(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Só o admin pode confirmar pagamentos.", show_alert=True)
        return

    desbloqueio_id = int(callback.data.split(":")[1])
    desbloqueio = db.get_desbloqueio(desbloqueio_id)
    if not desbloqueio or desbloqueio["estado"] != "pendente":
        await callback.answer("Este pedido já foi tratado.", show_alert=True)
        return

    db.marcar_pago(desbloqueio_id)
    prog = db.get_prognostico(desbloqueio["prognostico_id"])
    with db.get_conn() as conn:
        utilizador = conn.execute(
            "SELECT telegram_id FROM utilizadores WHERE id = ?",
            (desbloqueio["utilizador_id"],),
        ).fetchone()

    await enviar_conteudo(utilizador["telegram_id"], prog, prefixo="✅ Pagamento confirmado!")
    await callback.message.edit_text(callback.message.text + "\n\n✅ CONFIRMADO")
    await callback.answer("Confirmado! Conteúdo enviado ao utilizador.")


@dp.callback_query(F.data.startswith("rejeitar:"))
async def callback_rejeitar(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Só o admin pode fazer isto.", show_alert=True)
        return

    desbloqueio_id = int(callback.data.split(":")[1])
    db.marcar_rejeitado(desbloqueio_id)
    await callback.message.edit_text(callback.message.text + "\n\n❌ REJEITADO (pagamento não confirmado)")
    await callback.answer("Marcado como não pago.")


# ---------- Stats e resultado (admin) ----------

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    s = db.get_estatisticas()
    await message.answer(
        f"📊 <b>Estatísticas</b>\n"
        f"Total: {s['total_prognosticos']}\n"
        f"Greens: {s['total_greens']} | Reds: {s['total_reds']}\n"
        f"Taxa de acerto: {s['taxa_acerto_pct']}%\n"
        f"ROI: {s['roi_pct']}%",
        parse_mode="HTML",
    )


@dp.message(Command("pendentes"))
async def cmd_pendentes(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    pendentes = db.get_pendentes()
    if not pendentes:
        await message.answer("Não há prognósticos pendentes de resultado.")
        return
    linhas = ["📋 <b>Prognósticos por marcar:</b>\n"]
    for p in pendentes:
        linhas.append(
            f"#{p['id']} — {p['liga'] or 'sem liga'} | Odd: {p['odd_betano']} | {p['data_hora_jogo'] or 'sem data'}"
        )
    linhas.append("\nUsa: /resultado <id> green|red|anulado")
    await message.answer("\n".join(linhas), parse_mode="HTML")


@dp.message(Command("resultado"))
async def cmd_resultado(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    partes = message.text.split()
    if len(partes) != 3:
        await message.answer("Uso: /resultado <id> green|red|anulado")
        return
    _, prog_id, resultado = partes
    if resultado not in ("green", "red", "anulado"):
        await message.answer("Resultado inválido.")
        return
    db.marcar_resultado(int(prog_id), resultado)
    await atualizar_mensagem_fixada()
    await message.answer(f"Prognóstico #{prog_id} marcado como {resultado}.")


async def main():
    db.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
