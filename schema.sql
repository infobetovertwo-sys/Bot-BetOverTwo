-- Base de dados: prognosticos_bot
-- SQLite (podes migrar para Postgres depois sem grandes alterações)

CREATE TABLE IF NOT EXISTS utilizadores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    nome TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prognosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_jogo DATE NOT NULL,
    liga TEXT,
    equipa_casa TEXT,
    equipa_fora TEXT,
    mercado TEXT,              -- ex: "Over 2.5", "Vitória Casa", "Ambas Marcam"
    odd_betano REAL NOT NULL,  -- odd visível publicamente (antes de desbloquear)
    data_hora_jogo TEXT,       -- ex: "13/09" — visível publicamente (só data)
    hora_corte TEXT,           -- ISO datetime exato do início do jogo — uso interno, nunca mostrado publicamente
    tipo_conteudo TEXT DEFAULT 'texto',  -- 'texto' ou 'foto'
    conteudo_completo TEXT,    -- texto livre, OU file_id da foto (se tipo_conteudo='foto')
    preco_desbloqueio REAL DEFAULT 2.00,
    resultado TEXT DEFAULT 'pendente',  -- 'green', 'red', 'pendente', 'anulado'
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    publicado_em TIMESTAMP,
    mensagem_id_grupo INTEGER  -- id da mensagem no grupo, para editar depois (ex: marcar resultado)
);

CREATE TABLE IF NOT EXISTS desbloqueios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utilizador_id INTEGER NOT NULL,
    prognostico_id INTEGER NOT NULL,
    referencia TEXT UNIQUE,         -- código curto que o utilizador põe na descrição do MB Way
    estado TEXT DEFAULT 'pendente', -- 'pendente', 'pago', 'rejeitado'
    valor_pago REAL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pago_em TIMESTAMP,
    FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id),
    FOREIGN KEY (prognostico_id) REFERENCES prognosticos(id),
    UNIQUE(utilizador_id, prognostico_id)  -- não pode desbloquear o mesmo prognóstico 2x
);

CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT
);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_desbloqueios_estado ON desbloqueios(estado);
CREATE INDEX IF NOT EXISTS idx_prognosticos_resultado ON prognosticos(resultado);

-- View para estatísticas rápidas (taxa de acerto e ROI)
-- ROI assume stake unitário de 1u por prognóstico e odd decimal
CREATE VIEW IF NOT EXISTS vw_estatisticas AS
SELECT
    COUNT(*) AS total_prognosticos,
    SUM(CASE WHEN resultado = 'green' THEN 1 ELSE 0 END) AS total_greens,
    SUM(CASE WHEN resultado = 'red' THEN 1 ELSE 0 END) AS total_reds,
    ROUND(
        100.0 * SUM(CASE WHEN resultado = 'green' THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN resultado IN ('green','red') THEN 1 ELSE 0 END), 0), 2
    ) AS taxa_acerto_pct,
    ROUND(
        100.0 * (
            SUM(CASE WHEN resultado = 'green' THEN (odd_betano - 1) ELSE 0 END)
            - SUM(CASE WHEN resultado = 'red' THEN 1 ELSE 0 END)
        ) / NULLIF(SUM(CASE WHEN resultado IN ('green','red') THEN 1 ELSE 0 END), 0), 2
    ) AS roi_pct
FROM prognosticos;
