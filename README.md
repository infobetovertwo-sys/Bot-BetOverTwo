# Bot de Prognósticos — Desbloqueio via MB Way (confirmação manual)

Bot de Telegram que publica prognósticos "bloqueados" num canal (mostrando
só a odd da Betano) e permite a cada utilizador desbloquear individualmente
pagando 2€ via MB Way. O pagamento é confirmado manualmente por ti (um
toque num botão), e o bot trata do resto automaticamente.

## Instruções completas

Segue o ficheiro **GUIA_PASSO_A_PASSO.md** — é um guia detalhado para
quem nunca fez nada disto, com todos os passos por ordem.

## Estrutura dos ficheiros

- `bot.py` — lógica principal do bot (comandos, botões, fluxo de desbloqueio)
- `db.py` — acesso à base de dados (SQLite)
- `schema.sql` — estrutura das tabelas
- `run.py` — ficheiro que arranca o bot (é o que o Railway executa)
- `Procfile` — diz ao Railway como correr o projeto
- `requirements.txt` — dependências Python
