import csv
import sqlite3
from pathlib import Path

COMPOSERS = {
    'John Adams': 'adams',
    'Johann Sebastian Bach': 'bach',
    'Ludwig van Beethoven': 'beethoven',
    'Anton Bruckner': 'bruckner',
    'Antonín Dvořák': 'dvorak',
    'Philip Glass': 'glass',
    'George Frideric Handel': 'handel',
    'Joseph Haydn': 'haydn',
    'Gustav Mahler': 'mahler',
    'Wolfgang Amadeus Mozart': 'mozart',
    'Steve Reich': 'reich',
    'Pyotr Ilyich Tchaikovsky': 'tchaikovsky',
    'Antonio Vivaldi': 'vivaldi',
    'Richard Wagner': 'wagner',
}
CSV_PATH = 'source_files/{composer}_clean_min10.csv'
DB_PATH = Path('symphonies.db')


def create_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            composer TEXT NOT NULL,
            work TEXT NOT NULL,
            duration_ms INTEGER NOT NULL,
            UNIQUE(composer, work)
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_duration ON works(duration_ms)
    """)

def insert_data(conn: sqlite3.Connection, csv_path: Path, composer: str) -> None:
    cur = conn.cursor()

    with csv_path.open(newline="", encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)

        rows = []
        for row in reader:
            try:
                rows.append((
                    composer,
                    row['work'],
                    int(row['duration_ms'])
                ))
            except (ValueError, KeyError) as e:
                print(f'skipping row {row}')
                print(f'error {e}')
                continue
        cur.executemany("""
            INSERT INTO works (composer, work, duration_ms)
            VALUES (?, ?, ?)
        """, rows)

def main():
    with sqlite3.connect(DB_PATH) as conn:
        create_schema(conn)
        for composer, nickname in COMPOSERS.items():
            csv_path = Path(CSV_PATH.format(composer=nickname))
            if not csv_path.exists():
                print(f'Missing file: {csv_path}')
                continue
            insert_data(conn=conn, csv_path=csv_path, composer=composer)

        print('Data inserted successfully.')


if __name__ == '__main__':
    main()

## The old way of main() function:
# conn = sqlite3.connect(DB_PATH)
# try:
#     create_schema(conn)
#     conn.execute("BEGIN")
#     for composer, nickname in COMPOSERS.items():
#         csv_path = Path(CSV_PATH.format(composer=nickname))
#         if not csv_path.exists():
#             print(f"Missing file: {csv_path}")
#             continue
#         insert_data(conn=conn, csv_path=csv_path, composer=composer)
#     conn.commit()
#     print("Data inserted successfully.")
# except Exception:
#     conn.rollback()
#     raise
# finally:
#     conn.close()