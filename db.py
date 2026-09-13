import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "./prognosticos.db")

# Garante que a pasta onde a base de dados vai ficar existe (ex: /app/data)
_pasta = os.path.dirname(DATABASE_PATH)
if _pasta:
    os.makedirs(_pasta, exist_ok=True)


def init_db():
    """Cria as tabelas se ainda não existirem."""
    with get_conn() as conn:
        with open("schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_or_create_utilizador(telegram_id: int, username: str, nome: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM utilizadores WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO utilizadores (telegram_id, username, nome) VALUES (?, ?, ?)",
            (telegram_id, username, nome),
        )
        return cur.lastrowid


def criar_prognostico(data_jogo, liga, equipa_casa, equipa_fora, mercado,
                       odd_betano, conteudo_completo, data_hora_jogo="",
                       tipo_conteudo="texto", preco_desbloqueio=2.00):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO prognosticos
               (data_jogo, liga, equipa_casa, equipa_fora, mercado, odd_betano,
                data_hora_jogo, tipo_conteudo, conteudo_completo, preco_desbloqueio)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data_jogo, liga, equipa_casa, equipa_fora, mercado, odd_betano,
             data_hora_jogo, tipo_conteudo, conteudo_completo, preco_desbloqueio),
        )
        return cur.lastrowid


def get_prognostico(prognostico_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM prognosticos WHERE id = ?", (prognostico_id,)
        ).fetchone()


def criar_desbloqueio(utilizador_id: int, prognostico_id: int, referencia: str, valor: float):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO desbloqueios
               (utilizador_id, prognostico_id, referencia, valor_pago, estado)
               VALUES (?, ?, ?, ?, 'pendente')""",
            (utilizador_id, prognostico_id, referencia, valor),
        )
        return cur.lastrowid


def get_desbloqueio(desbloqueio_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM desbloqueios WHERE id = ?", (desbloqueio_id,)
        ).fetchone()


def marcar_pago(desbloqueio_id: int):
    with get_conn() as conn:
        conn.execute(
            """UPDATE desbloqueios SET estado = 'pago', pago_em = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (desbloqueio_id,),
        )


def marcar_rejeitado(desbloqueio_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE desbloqueios SET estado = 'rejeitado' WHERE id = ?",
            (desbloqueio_id,),
        )


def ja_desbloqueado(utilizador_id: int, prognostico_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT 1 FROM desbloqueios
               WHERE utilizador_id = ? AND prognostico_id = ? AND estado = 'pago'""",
            (utilizador_id, prognostico_id),
        ).fetchone()
        return row is not None


def marcar_resultado(prognostico_id: int, resultado: str):
    """resultado: 'green', 'red' ou 'anulado'"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE prognosticos SET resultado = ? WHERE id = ?",
            (resultado, prognostico_id),
        )


def get_estatisticas():
    with get_conn() as conn:
        return dict(conn.execute("SELECT * FROM vw_estatisticas").fetchone())


def get_config(chave: str):
    with get_conn() as conn:
        row = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
        return row["valor"] if row else None


def set_config(chave: str, valor: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (chave, valor),
        )


def get_sequencia_atual():
    """Devolve (tipo, contagem) da sequência atual: tipo é 'green' ou 'red'."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT resultado FROM prognosticos
               WHERE resultado IN ('green', 'red')
               ORDER BY id DESC"""
        ).fetchall()
    if not rows:
        return None, 0
    tipo = rows[0]["resultado"]
    contagem = 0
    for r in rows:
        if r["resultado"] == tipo:
            contagem += 1
        else:
            break
    return tipo, contagem


def get_data_inicio_historico():
    with get_conn() as conn:
        row = conn.execute(
            """SELECT MIN(data_jogo) AS inicio FROM prognosticos
               WHERE resultado IN ('green', 'red')"""
        ).fetchone()
    return row["inicio"] if row else None


def get_pendentes():
    with get_conn() as conn:
        return conn.execute(
            """SELECT id, liga, odd_betano, data_hora_jogo, criado_em
               FROM prognosticos WHERE resultado = 'pendente'
               ORDER BY id DESC"""
        ).fetchall()
