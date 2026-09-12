import sqlite3
import os
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "./prognosticos.db")


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
                       odd_betano, conteudo_completo, preco_desbloqueio=2.00):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO prognosticos
               (data_jogo, liga, equipa_casa, equipa_fora, mercado, odd_betano,
                conteudo_completo, preco_desbloqueio)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data_jogo, liga, equipa_casa, equipa_fora, mercado, odd_betano,
             conteudo_completo, preco_desbloqueio),
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
