from pathlib import Path

from sqlalchemy import text

from database import get_engine


BASE_DIR = Path(__file__).resolve().parent.parent

VIEWS_PATH = BASE_DIR / "sql" / "views"


def execute_sql_file(connection, file_path):
    """
    Lê e executa um arquivo SQL no Redshift.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        sql = file.read()

    connection.execute(text(sql))


def create_views(connection):
    """
    Cria ou atualiza todas as Business Views
    definidas no diretório sql/views.
    """

    sql_files = sorted(VIEWS_PATH.glob("*.sql"))

    if not sql_files:
        raise FileNotFoundError(
            f"Nenhum arquivo SQL encontrado em: {VIEWS_PATH}"
        )

    print("\nCriando Business Views...")

    for sql_file in sql_files:

        print(f"  → {sql_file.name}")

        execute_sql_file(
            connection,
            sql_file
        )

        print(f"  ✓ {sql_file.name} criada/atualizada.")

    print("✓ Business Views criadas com sucesso.")


def run_views():

    engine = get_engine()

    print(
        "\n=============================================="
    )
    print(
        "Iniciando criação das BUSINESS VIEWS"
    )
    print(
        "=============================================="
    )

    with engine.begin() as connection:

        create_views(connection)

    print(
        "\n=============================================="
    )
    print(
        "BUSINESS VIEWS criadas com sucesso!"
    )
    print(
        "=============================================="
    )


if __name__ == "__main__":
    run_views()