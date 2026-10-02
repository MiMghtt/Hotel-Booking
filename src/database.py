import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env"
)


def get_engine():
    """
    Cria e retorna a conexão com o Amazon Redshift.
    """

    db_user = os.getenv("REDSHIFT_USER")
    db_pass = os.getenv("REDSHIFT_PASSWORD")
    db_host = os.getenv("REDSHIFT_HOST")
    db_port = os.getenv("REDSHIFT_PORT", "5439")
    db_name = os.getenv("REDSHIFT_DB")

    if not db_user:
        raise ValueError(
            "REDSHIFT_USER não encontrado no .env."
        )

    if not db_pass:
        raise ValueError(
            "REDSHIFT_PASSWORD não encontrado no .env."
        )

    if not db_host:
        raise ValueError(
            "REDSHIFT_HOST não encontrado no .env."
        )

    if not db_name:
        raise ValueError(
            "REDSHIFT_DB não encontrado no .env."
        )

    encoded_pass = quote_plus(db_pass)

    connection_string = (
        f"redshift+psycopg2://"
        f"{db_user}:{encoded_pass}"
        f"@{db_host}:{db_port}"
        f"/{db_name}"
    )

    return create_engine(connection_string)