import sqlite3, os, sys

DB_PATH = r".\instance\pneumark.db"

DDL = """
CREATE TABLE IF NOT EXISTS gp_bench_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  serial TEXT NOT NULL,
  modelo TEXT NOT NULL,
  bench TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'waiting',
  source TEXT NOT NULL DEFAULT 'montagem',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_queue_serial_bench
ON gp_bench_queue(serial, bench);
"""

def main():
    if not os.path.exists(DB_PATH):
        print(f"Banco não encontrado: {DB_PATH}")
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    try:
        con.executescript(DDL)
        con.commit()
        # Verificações rápidas
        t = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gp_bench_queue'").fetchone()
        idx = con.execute("PRAGMA index_list('gp_bench_queue')").fetchall()
        print("Tabela criada/verificada:", t is not None)
        print("Índices:", idx)
        print("OK: gp_bench_queue pronta.")
    finally:
        con.close()

if __name__ == "__main__":
    main()
