import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()


class DatabaseUtil:

    def __init__(self, db_config):
        self.db_config = db_config

        try:
            self.connection = psycopg2.connect(**db_config)
            print("✅ Connected to PostgreSQL")

        except Exception as e:
            print(f"❌ Error connecting to the database: {e}")
            self.connection = None

    def schema_details(self, schema_name):

        if self.connection is None:
            return "Database connection not established."

        schema_info_context = ""

        try:
            with self.connection.cursor() as cursor:

                schema_info_context += f"Database Schema: {schema_name}\n"

                cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name;
                    """,
                    (schema_name,),
                )

                tables_list = cursor.fetchall()

                for (table_name,) in tables_list:

                    schema_info_context += f"\n{'=' * 60}\n"
                    schema_info_context += f"Table: {table_name}\n"
                    schema_info_context += f"{'-' * 60}\n"

                    # Fetch columns
                    cursor.execute(
                        """
                        SELECT column_name, data_type
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = %s
                        ORDER BY ordinal_position;
                        """,
                        (schema_name, table_name),
                    )

                    columns = cursor.fetchall()

                    schema_info_context += "Columns:\n"

                    for column_name, data_type in columns:
                        schema_info_context += (
                            f"  • {column_name} ({data_type})\n"
                        )

                    # Fetch sample rows safely
                    cursor.execute(
                        sql.SQL("SELECT * FROM {}.{} LIMIT 5").format(
                            sql.Identifier(schema_name),
                            sql.Identifier(table_name),
                        )
                    )

                    rows = cursor.fetchall()

                    schema_info_context += "\nSample Data:\n"

                    if rows:
                        for row in rows:
                            schema_info_context += f"  {row}\n"
                    else:
                        schema_info_context += "  No rows found.\n"

        except Exception as e:
            schema_info_context = f"Error fetching schema details: {e}"

        return schema_info_context

    def execute_sql(self, query):

        if self.connection is None:
            return None

        try:
            with self.connection.cursor() as cursor:

                cursor.execute(query)

                if cursor.description:
                    result = cursor.fetchall()
                else:
                    result = []

                self.connection.commit()

                return str(result)

        except Exception as e:
            self.connection.rollback()
            print(f"Error executing query: {e}")
            return None

    def close(self):
        if self.connection:
            self.connection.close()
            print("🔒 PostgreSQL connection closed.")


db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_NAME"),
}

obj = DatabaseUtil(db_config)

result = obj.schema_details("public")

with open("test_schema_details.txt", "w", encoding="utf-8") as f:
    f.write(result)

obj.close()