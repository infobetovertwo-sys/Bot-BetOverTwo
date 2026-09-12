# Guia Passo a Passo — Bot de Prognósticos (confirmação manual via MB Way)

Este guia assume que nunca fizeste nada disto. Segue as partes por ordem.

**Como funciona o negócio:** publicas um prognóstico bloqueado no canal
(só a odd da Betano fica visível). Quem quiser desbloquear clica num botão,
recebe o teu número de MB Way + uma referência única, paga por fora, e tu
confirmas manualmente no bot (um toque num botão) assim que vires o
dinheiro entrar na Revolut. O bot trata do resto sozinho: enviar as
instruções, avisar-te do pedido, e mandar o conteúdo completo assim que
confirmares.

---

## Checklist geral (as 3 contas que vais precisar de criar)

- [ ] Conta no **Telegram** (já deves ter)
- [ ] Conta no **GitHub** (onde o código vai ficar guardado)
- [ ] Conta no **Railway** (o servidor que vai correr o bot 24h/dia)
- [ ] Conta **Revolut pessoal** (já deves ter, para receberes os MB Way)

Já não precisas de Revolut Business nem de abrir atividade para começar a
testar — o dinheiro entra via MB Way normal na tua conta pessoal. (A
questão fiscal continua a aplicar-se conforme já falámos — isto só muda a
parte técnica do pagamento, não a obrigação de declarares o rendimento.)

---

## PARTE 1 — Criar o bot no Telegram

1. Abre o Telegram e procura por **@BotFather**.
2. Escreve `/newbot` e envia.
3. Dá um **nome** ao bot (ex: "Prognósticos Pro").
4. Dá um **username** que acabe em `bot` (ex: `prognosticospro_bot`).
5. O BotFather devolve um **token** — copia e guarda num sítio seguro.

### Criar o canal
6. Cria um **canal** no Telegram (Novo → Novo Canal).
7. Adiciona o teu bot como **Administrador** (nome do canal → Administradores → Adicionar Administrador → procura o username do bot → marca "Publicar mensagens" e "Editar mensagens de outros" → guardar).

### IDs que já tens
Já descobriste estes dois valores nas mensagens anteriores — confirma que os tens guardados:
- `TELEGRAM_ADMIN_ID` → o teu ID pessoal (ex: `7198139962`)
- `TELEGRAM_GRUPO_ID` → o ID do canal (começa por `-100...`)

---

## PARTE 2 — Colocar o código no GitHub

1. Vai a [github.com](https://github.com) e cria conta gratuita.
2. Clica **"New"** → dá um nome ao repositório (ex: `bot-prognosticos`) → deixa como **Private** → **Create repository**.
3. Clica **"uploading an existing file"** (ou "Add file" → "Upload files").
4. Arrasta **todos os ficheiros** do projeto que te enviei (bot.py, db.py, schema.sql, requirements.txt, Procfile, run.py, README.md). **Não incluas o `.env.example`** com dados reais — esse fica só de referência.
5. Clica **"Commit changes"**.

---

## PARTE 3 — Pôr o bot a correr 24h/dia (Railway)

1. Vai a [railway.app](https://railway.app) e entra com a tua conta GitHub.
2. **"New Project"** → **"Deploy from GitHub repo"** → escolhe `bot-prognosticos`.
3. O Railway vai tentar correr o projeto e falhar por agora (falta configurar) — normal, não te preocupes.

### Configurar as variáveis
4. No serviço criado, vai a **"Variables"** → **"New Variable"** e adiciona, uma a uma:

   | Nome da variável | Valor |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | o token do BotFather |
   | `TELEGRAM_ADMIN_ID` | o teu ID pessoal |
   | `TELEGRAM_GRUPO_ID` | o ID do canal |
   | `MBWAY_NUMERO` | o teu número de telemóvel associado ao MB Way |
   | `DATABASE_PATH` | `./prognosticos.db` |

5. O Railway reinicia sozinho depois de guardares as variáveis.

Não precisas de gerar domínio público nem configurar webhooks — este fluxo é mais simples que o anterior, o bot só precisa de estar "ligado" e a falar com o Telegram.

---

## PARTE 4 — Testar tudo

1. No Telegram, em privado com o bot, escreve `/novo` e segue as perguntas (liga, equipas, mercado, odd, conteúdo, preço).
2. Confirma que a mensagem aparece bloqueada no canal, com o botão "🔓 Desbloquear".
3. Usando outra conta de Telegram (ou pede a alguém), clica no botão.
4. Essa pessoa deve receber, em privado, o teu número de MB Way + uma referência (ex: `PG1U4321`).
5. **Tu**, como admin, deves receber uma notificação com os botões "✅ Confirmar pagamento" / "❌ Ainda não recebi".
6. Faz um pagamento de teste real (tu próprio a mandar 2€ via MB Way, com essa referência na nota) e confirma que aparece na tua Revolut.
7. Toca em "✅ Confirmar pagamento" no bot.
8. Confirma que a pessoa que desbloqueou recebe automaticamente o conteúdo completo em privado.

Se isto funcionar de ponta a ponta, o sistema está pronto para uso real.

---

## Fluxo do dia a dia (depois de tudo montado)

1. Escreves `/novo` no privado com o bot → publicas o prognóstico bloqueado.
2. Vais recebendo notificações sempre que alguém pede para desbloquear.
3. Abres a Revolut, procuras a referência indicada, confirmas que o valor bateu certo.
4. Tocas em "✅ Confirmar pagamento" — o bot trata do resto.
5. Depois do jogo, usas `/resultado <id> green` ou `/resultado <id> red`.
6. `/stats` a qualquer momento para veres a taxa de acerto e ROI atualizados.

---

## Se algo falhar

- **O bot não responde** → Railway → "Deployments" → clica no mais recente → vê os "Logs". A mensagem de erro normalmente diz o que falta.
- **O botão de desbloquear não funciona** → confirma que o bot é administrador do canal e que o `TELEGRAM_GRUPO_ID` está certo (começa por `-100`).
- **Não recebo a notificação de novo pedido** → confirma que o `TELEGRAM_ADMIN_ID` no Railway é exatamente o teu ID pessoal.
- **Dúvida nalgum passo** → diz-me exatamente onde travaste (ex: "Parte 3, passo 4, não aparece Variables") e resolvemos juntos.

---

## O que fazer depois (opcional, mais à frente)

- Comando `/historico` para os utilizadores verem resultados passados.
- Aviso automático de "jogo responsável" nas mensagens públicas.
- Se o volume crescer bastante, aí sim vale a pena reconsiderar automação total com Revolut Business + faturação automática (já montámos essa versão antes, fica disponível para quando fizer sentido).
