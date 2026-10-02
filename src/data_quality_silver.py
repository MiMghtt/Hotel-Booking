import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env"
)


REDSHIFT_SCHEMA = os.getenv(
    "REDSHIFT_SCHEMA",
    "hotel_bookings"
)

TABLE_NAME = "silver"


# =========================
# DATABASE
# =========================

def get_engine():
    """
    Gera a engine do SQLAlchemy utilizando
    as credenciais do Redshift no .env.
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

    return create_engine(
        connection_string
    )


# =========================
# DATA QUALITY
# =========================

def run_data_quality_checks():

    engine = get_engine()

    table = (
        f"{REDSHIFT_SCHEMA}.{TABLE_NAME}"
    )

    print(
        f"Iniciando Data Quality na tabela "
        f"{table}\n"
    )

    errors = []

    # =========================
    # 1. VOLUME
    # =========================

    df_count = pd.read_sql(
        f"""
        SELECT COUNT(*) AS total
        FROM {table};
        """,
        engine
    )

    total_rows = int(
        df_count["total"].iloc[0]
    )

    print(
        f"📊 1. Volume Total de Registros: "
        f"{total_rows}"
    )

    if total_rows == 0:

        errors.append(
            "❌ ERRO DE VOLUME: "
            f"A tabela {table} está vazia."
        )

    elif total_rows < 80000:

        print(
            f"⚠️ AVISO DE VOLUME: "
            f"Esperava-se > 80.000 linhas, "
            f"encontrado {total_rows}."
        )

    else:

        print(
            "   ✓ Volume dentro do esperado"
        )


    # =========================
    # 2. NULOS
    # =========================

    critical_columns = [
        "hotel",
        "is_canceled",
        "arrival_date_year",
        "arrival_date_month",
        "adr",
    ]

    null_checks_query = ", ".join(
        [
            f"""
            SUM(
                CASE
                    WHEN {column} IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_{column}
            """
            for column in critical_columns
        ]
    )

    df_nulls = pd.read_sql(
        f"""
        SELECT
            {null_checks_query}
        FROM {table};
        """,
        engine
    )

    print(
        "\n❓ 2. Checagem de Valores Nulos:"
    )

    for column in critical_columns:

        null_count = int(
            df_nulls[
                f"null_{column}"
            ].iloc[0]
        )

        if null_count > 0:

            errors.append(
                f"❌ ERRO DE NULLS: "
                f"A coluna '{column}' possui "
                f"{null_count} valores nulos."
            )

        else:

            print(
                f"   ✓ {column}: 0 nulos"
            )


    # =========================
    # 3. DUPLICIDADES
    # =========================

    query_dupes = f"""
        SELECT
            COUNT(*) -
            COUNT(
                DISTINCT
                MD5(
                    COALESCE(hotel, '') ||
                    COALESCE(is_canceled::VARCHAR, '') ||
                    COALESCE(arrival_date_year::VARCHAR, '') ||
                    COALESCE(arrival_date_month, '') ||
                    COALESCE(arrival_date_day_of_month::VARCHAR, '') ||
                    COALESCE(adults::VARCHAR, '') ||
                    COALESCE(children::VARCHAR, '') ||
                    COALESCE(babies::VARCHAR, '') ||
                    COALESCE(adr::VARCHAR, '')
                )
            ) AS dupes
        FROM {table};
    """

    df_dupes = pd.read_sql(
        query_dupes,
        engine
    )

    dupes_count = int(
        df_dupes["dupes"].iloc[0]
    )

    print(
        f"\n🔄 3. Duplicidades Identificadas: "
        f"{dupes_count}"
    )

    if dupes_count > 0:

        print(
            f"   ⚠️ AVISO: {dupes_count} "
            "possíveis registros duplicados."
        )

    else:

        print(
            "   ✓ Nenhuma duplicidade identificada"
        )


    # =========================
    # 4. RANGES / REGRAS
    # =========================

    query_ranges = f"""
        SELECT

            SUM(
                CASE
                    WHEN adr < 0 THEN 1
                    ELSE 0
                END
            ) AS adr_invalido,

            SUM(
                CASE
                    WHEN is_canceled NOT IN (0, 1) THEN 1
                    ELSE 0
                END
            ) AS is_canceled_invalido,

            SUM(
                CASE
                    WHEN adults < 0 THEN 1
                    ELSE 0
                END
            ) AS adults_invalido,

            SUM(
                CASE
                    WHEN children < 0 THEN 1
                    ELSE 0
                END
            ) AS children_invalido,

            SUM(
                CASE
                    WHEN babies < 0 THEN 1
                    ELSE 0
                END
            ) AS babies_invalido,

            SUM(
                CASE
                    WHEN total_nights < 0 THEN 1
                    ELSE 0
                END
            ) AS total_nights_invalido,

            SUM(
                CASE
                    WHEN total_guests < 0 THEN 1
                    ELSE 0
                END
            ) AS total_guests_invalido

        FROM {table};
    """

    df_ranges = pd.read_sql(
        query_ranges,
        engine
    )

    print(
        "\n📏 4. Checagem de Ranges "
        "e Regras de Negócio:"
    )

    range_checks = {
        "adr_invalido":
            "ADR possui valores negativos",

        "is_canceled_invalido":
            "is_canceled possui valores diferentes de 0 ou 1",

        "adults_invalido":
            "adults possui valores negativos",

        "children_invalido":
            "children possui valores negativos",

        "babies_invalido":
            "babies possui valores negativos",

        "total_nights_invalido":
            "total_nights possui valores negativos",

        "total_guests_invalido":
            "total_guests possui valores negativos",
    }

    for column, message in range_checks.items():

        invalid_count = int(
            df_ranges[column].iloc[0]
        )

        if invalid_count > 0:

            errors.append(
                f"❌ ERRO DE RANGE: "
                f"{message}. "
                f"Registros: {invalid_count}."
            )

        else:

            print(
                f"   ✓ {message}: OK"
            )


    # =========================
    # 5. CONSISTÊNCIA
    # =========================

    query_consistency = f"""
        SELECT

            SUM(
                CASE
                    WHEN total_nights !=
                        (
                            stays_in_weekend_nights +
                            stays_in_week_nights
                        )
                    THEN 1
                    ELSE 0
                END
            ) AS nights_inconsistentes,

            SUM(
                CASE
                    WHEN total_guests !=
                        (
                            adults +
                            children +
                            babies
                        )
                    THEN 1
                    ELSE 0
                END
            ) AS guests_inconsistentes,

            SUM(
                CASE
                    WHEN ABS(
                        estimated_revenue -
                        (
                            adr * total_nights
                        )
                    ) > 0.01
                    THEN 1
                    ELSE 0
                END
            ) AS revenue_inconsistente

        FROM {table};
    """

    df_consistency = pd.read_sql(
        query_consistency,
        engine
    )

    print(
        "\n🔗 5. Checagem de Consistência:"
    )

    consistency_checks = {
        "nights_inconsistentes":
            "total_nights",

        "guests_inconsistentes":
            "total_guests",

        "revenue_inconsistente":
            "estimated_revenue",
    }

    for column, label in consistency_checks.items():

        invalid_count = int(
            df_consistency[column].iloc[0]
        )

        if invalid_count > 0:

            errors.append(
                f"❌ ERRO DE CONSISTÊNCIA: "
                f"{label} possui "
                f"{invalid_count} registros inconsistentes."
            )

        else:

            print(
                f"   ✓ {label}: consistente"
            )


    # =========================
    # RESULTADO
    # =========================

    print(
        "\n" + "=" * 60
    )

    if errors:

        print(
            "❌ FALHAS DETECTADAS "
            "NO DATA QUALITY:"
        )

        for error in errors:

            print(
                f"  - {error}"
            )

        print(
            "=" * 60
        )

        sys.exit(1)

    else:

        print(
            "✅ DATA QUALITY CONCLUÍDO "
            "COM SUCESSO!"
        )

        print(
            f"   Tabela validada: {table}"
        )

        print(
            f"   Registros: {total_rows}"
        )

        print(
            "=" * 60
        )


if __name__ == "__main__":
    run_data_quality_checks()