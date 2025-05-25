# inspect_db.py

import duckdb

def main():
    # Connect to the existing database
    conn = duckdb.connect('squads.db')
    # Read the entire players table into a DuckDB result
    df = conn.execute("SELECT * FROM players").fetchdf()
    conn.close()

    # Print it nicely
    print(df.to_string(index=False))

if __name__ == '__main__':
    main()
