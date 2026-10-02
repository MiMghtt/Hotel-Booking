import os
import boto3
import pandas as pd

from io import BytesIO
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from urllib.parse import quote_plus


load_dotenv()


# =========================
# CONFIG
# =========================

BUCKET = "hotel-booking-mmarighetti"
RAW_KEY = "raw/hotel_bookings.csv"

PROCESSED_KEY = "processed/hotel_bookings.csv"

REDSHIFT_HOST = os.getenv("REDSHIFT_HOST")
REDSHIFT_PORT = os.getenv("REDSHIFT_PORT", "5439")
REDSHIFT_DB = os.getenv("REDSHIFT_DB")
REDSHIFT_USER = os.getenv("REDSHIFT_USER")
REDSHIFT_PASSWORD = os.getenv("REDSHIFT_PASSWORD")

REDSHIFT_SCHEMA = os.getenv("REDSHIFT_SCHEMA", "public")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


TABLE_NAME = "silver"


MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12
}


# =========================
# EXTRACT
# =========================

def read_from_s3(bucket: str, key: str) -> pd.DataFrame:

    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=bucket,
        Key=key
    )

    return pd.read_csv(
        BytesIO(response["Body"].read())
    )


# =========================
# TRANSFORM
# =========================

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def handle_nulls(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["children"] = df["children"].fillna(0)
    df["country"] = df["country"].fillna("UNKNOWN")

    return df


def convert_types(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    integer_columns = [
        "is_canceled",
        "lead_time",
        "arrival_date_year",
        "arrival_date_week_number",
        "arrival_date_day_of_month",
        "stays_in_weekend_nights",
        "stays_in_week_nights",
        "adults",
        "children",
        "babies",
        "is_repeated_guest",
        "previous_cancellations",
        "previous_bookings_not_canceled",
        "booking_changes",
        "agent",
        "company",
        "days_in_waiting_list",
        "required_car_parking_spaces",
        "total_of_special_requests"
    ]

    decimal_columns = [
        "adr"
    ]

    for column in integer_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        ).astype("Int64")

    for column in decimal_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df

def create_arrival_date(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["arrival_month_num"] = (
        df["arrival_date_month"].map(MONTHS)
    )

    df["arrival_date"] = pd.to_datetime(
        {
            "year": df["arrival_date_year"],
            "month": df["arrival_month_num"],
            "day": df["arrival_date_day_of_month"]
        },
        errors="coerce"
    )

    return df


def create_total_nights(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["total_nights"] = (
        df["stays_in_weekend_nights"]
        + df["stays_in_week_nights"]
    )

    return df


def create_total_guests(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["total_guests"] = (
        df["adults"]
        + df["children"]
        + df["babies"]
    )

    return df


def create_estimated_revenue(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["estimated_revenue"] = (
        df["adr"]
        * df["total_nights"]
    )

    return df

def apply_data_quality_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classifica registros de acordo com regras de qualidade de dados.

    Os registros não são removidos nesta etapa.
    Apenas recebem um status de qualidade para posterior uso
    na camada Gold.
    """

    df = df.copy()

    # Status padrão
    df["data_quality_status"] = "VALID"

    # =========================================================
    # ADR NEGATIVO
    # =========================================================

    df.loc[
        df["adr"] < 0,
        "data_quality_status"
    ] = "INVALID_ADR"

    # =========================================================
    # ADR EXTREMAMENTE ALTO E INCONSISTENTE
    # =========================================================

    df.loc[
        (df["adr"] > 5000) &
        (df["reservation_status"] == "Canceled"),
        "data_quality_status"
    ] = "INVALID_EXTREME_ADR"

    # =========================================================
    # OCUPAÇÃO EXTREMA E INCONSISTENTE
    # =========================================================

    df.loc[
        (df["adults"] > 20) &
        (df["adr"] == 0) &
        (df["reservation_status"] == "Canceled"),
        "data_quality_status"
    ] = "INVALID_EXTREME_OCCUPANCY"

    return df

def filter_invalid_data(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    return df[
        (df["adults"] >= 0) &
        (df["children"] >= 0) &
        (df["babies"] >= 0) &
        (df["total_nights"] >= 0) &
        (df["total_guests"] >= 0)
    ]


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:

    return df.drop_duplicates()


# =========================
# VALIDATION
# =========================

def validate_data(df: pd.DataFrame) -> None:

    assert df["adults"].ge(0).all(), \
        "Existem adultos com valor negativo"

    assert df["children"].ge(0).all(), \
        "Existem crianças com valor negativo"

    assert df["babies"].ge(0).all(), \
        "Existem bebês com valor negativo"

    assert df["total_nights"].ge(0).all(), \
        "Existem reservas com noites negativas"

    assert df["total_guests"].ge(0).all(), \
        "Existem reservas com hóspedes negativos"


# =========================
# LOAD - S3 PROCESSED
# =========================

def upload_processed_to_s3(df: pd.DataFrame) -> None:

    s3 = boto3.client("s3")

    csv_buffer = BytesIO()

    df.to_csv(
        csv_buffer,
        index=False
    )

    csv_buffer.seek(0)

    s3.put_object(
        Bucket=BUCKET,
        Key=PROCESSED_KEY,
        Body=csv_buffer.getvalue()
    )

    print(
        f"Arquivo tratado enviado para "
        f"s3://{BUCKET}/{PROCESSED_KEY}"
    )


# =========================
# LOAD - REDSHIFT
# =========================

def get_redshift_engine():

    password = quote_plus(REDSHIFT_PASSWORD)

    database_url = (
        f"redshift+psycopg2://"
        f"{REDSHIFT_USER}:{password}"
        f"@{REDSHIFT_HOST}:{REDSHIFT_PORT}"
        f"/{REDSHIFT_DB}"
    )

    return create_engine(database_url)

def load_to_redshift() -> None:

    engine = get_redshift_engine()

    s3_path = (
        f"s3://{BUCKET}/{PROCESSED_KEY}"
    )

    copy_sql = f"""
        COPY {REDSHIFT_SCHEMA}.{TABLE_NAME}
        FROM '{s3_path}'
        IAM_ROLE default
        FORMAT AS CSV
        IGNOREHEADER 1
        EMPTYASNULL
        BLANKSASNULL
        DATEFORMAT 'auto'
        TIMEFORMAT 'auto'
        REGION '{AWS_REGION}';
    """

    with engine.begin() as connection:

        connection.execute(
            text(
                f"""
                TRUNCATE TABLE
                {REDSHIFT_SCHEMA}.{TABLE_NAME};
                """
            )
        )

        connection.execute(
            text(copy_sql)
        )

    print("Carga no Redshift concluída com sucesso!")



# =========================
# MAIN
# =========================

def main():

    # Extract

    df = read_from_s3(
        BUCKET,
        RAW_KEY
    )

    print(
        f"Linhas iniciais: {len(df)}"
    )


    # Clean

    df = clean_column_names(df)


    # Null treatment

    df = handle_nulls(df)


    # Types

    df = convert_types(df)


    # Business rules

    df = create_arrival_date(df)

    df = create_total_nights(df)

    df = create_total_guests(df)

    df = create_estimated_revenue(df)


    # Data quality

    df = apply_data_quality_rules(df)


    # Invalid structural data

    df = filter_invalid_data(df)


    # Duplicates

    df = remove_duplicates(df)


    print(
        f"Linhas após tratamento: {len(df)}"
    )


    # Validation

    validate_data(df)


    # Upload processed file to S3

    upload_processed_to_s3(df)


    # Load into Redshift

    load_to_redshift()


    print(
        "ETL completo executado com sucesso!"
    )


if __name__ == "__main__":
    main()