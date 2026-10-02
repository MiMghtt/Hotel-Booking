import os

from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    dotenv_path=BASE_DIR / ".env"
)


REDSHIFT_SCHEMA = os.getenv(
    "REDSHIFT_SCHEMA",
    "hotel_bookings"
)

SILVER_TABLE = "silver"

DIM_DATE = "dim_date"
DIM_HOTEL = "dim_hotel"
DIM_CUSTOMER = "dim_customer"
DIM_ROOM = "dim_room"
DIM_CHANNEL = "dim_channel"
FACT_BOOKING = "fact_booking"


# =========================================================
# DATABASE
# =========================================================

def get_engine():
    """
    Cria a conexão com o Redshift.
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


# =========================================================
# GOLD
# =========================================================

def load_dimensions(connection):
    """
    Carrega as dimensões a partir dos registros válidos
    da tabela Silver.

    Apenas registros com data_quality_status = 'VALID'
    participam da camada Gold.
    """

    print("Carregando dimensões...")

    # =====================================================
    # DIM DATE
    # =====================================================

    print("  → dim_date")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{DIM_DATE} (
                date_key,
                full_date,
                year,
                month_number,
                month_name,
                week_number,
                day_of_month,
                quarter
            )

            SELECT DISTINCT

                CAST(
                    TO_CHAR(
                        arrival_date,
                        'YYYYMMDD'
                    )
                    AS INTEGER
                ) AS date_key,

                arrival_date AS full_date,

                arrival_date_year AS year,

                arrival_month_num AS month_number,

                arrival_date_month AS month_name,

                arrival_date_week_number AS week_number,

                arrival_date_day_of_month AS day_of_month,

                CASE
                    WHEN arrival_month_num BETWEEN 1 AND 3
                        THEN 1

                    WHEN arrival_month_num BETWEEN 4 AND 6
                        THEN 2

                    WHEN arrival_month_num BETWEEN 7 AND 9
                        THEN 3

                    WHEN arrival_month_num BETWEEN 10 AND 12
                        THEN 4
                END AS quarter

            FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE}

            WHERE arrival_date IS NOT NULL
              AND data_quality_status = 'VALID';
        """)
    )

    # =====================================================
    # DIM HOTEL
    # =====================================================

    print("  → dim_hotel")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{DIM_HOTEL} (
                hotel_key,
                hotel
            )

            SELECT
                ROW_NUMBER() OVER (
                    ORDER BY hotel
                ) AS hotel_key,

                hotel

            FROM (
                SELECT DISTINCT
                    hotel

                FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE}

                WHERE hotel IS NOT NULL
                  AND data_quality_status = 'VALID'
            ) source;
        """)
    )

    # =====================================================
    # DIM CUSTOMER
    # =====================================================

    print("  → dim_customer")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{DIM_CUSTOMER} (
                customer_key,
                country,
                customer_type,
                is_repeated_guest
            )

            SELECT

                ROW_NUMBER() OVER (
                    ORDER BY
                        country,
                        customer_type,
                        is_repeated_guest
                ) AS customer_key,

                country,

                customer_type,

                is_repeated_guest

            FROM (
                SELECT DISTINCT

                    country,

                    customer_type,

                    is_repeated_guest

                FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE}

                WHERE data_quality_status = 'VALID'

            ) source;
        """)
    )

    # =====================================================
    # DIM ROOM
    # =====================================================

    print("  → dim_room")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{DIM_ROOM} (
                room_key,
                reserved_room_type,
                assigned_room_type
            )

            SELECT

                ROW_NUMBER() OVER (
                    ORDER BY
                        reserved_room_type,
                        assigned_room_type
                ) AS room_key,

                reserved_room_type,

                assigned_room_type

            FROM (
                SELECT DISTINCT

                    reserved_room_type,

                    assigned_room_type

                FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE}

                WHERE data_quality_status = 'VALID'

            ) source;
        """)
    )

    # =====================================================
    # DIM CHANNEL
    # =====================================================

    print("  → dim_channel")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{DIM_CHANNEL} (
                channel_key,
                market_segment,
                distribution_channel
            )

            SELECT

                ROW_NUMBER() OVER (
                    ORDER BY
                        market_segment,
                        distribution_channel
                ) AS channel_key,

                market_segment,

                distribution_channel

            FROM (
                SELECT DISTINCT

                    market_segment,

                    distribution_channel

                FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE}

                WHERE data_quality_status = 'VALID'

            ) source;
        """)
    )

    print("  ✓ Dimensões carregadas.")


# =========================================================
# FACT
# =========================================================

def load_fact(connection):
    """
    Carrega a fact_booking relacionando
    somente registros válidos da Silver
    com as dimensões.
    """

    print("Carregando fact_booking...")

    connection.execute(
        text(f"""
            INSERT INTO {REDSHIFT_SCHEMA}.{FACT_BOOKING} (

                booking_key,

                date_key,
                hotel_key,
                customer_key,
                room_key,
                channel_key,

                lead_time,
                stays_in_weekend_nights,
                stays_in_week_nights,
                total_nights,

                adults,
                children,
                babies,
                total_guests,

                adr,
                estimated_revenue,

                is_canceled,
                is_repeated_guest,

                previous_cancellations,
                previous_bookings_not_canceled,
                booking_changes,
                days_in_waiting_list,

                required_car_parking_spaces,
                total_of_special_requests,

                meal,
                deposit_type,

                reservation_status,
                reservation_status_date,

                agent,
                company
            )

            SELECT

                ROW_NUMBER() OVER (
                    ORDER BY
                        s.arrival_date,
                        s.hotel,
                        s.lead_time,
                        s.adr,
                        s.reservation_status_date
                ) AS booking_key,

                d.date_key,

                h.hotel_key,

                c.customer_key,

                r.room_key,

                ch.channel_key,

                s.lead_time,

                s.stays_in_weekend_nights,

                s.stays_in_week_nights,

                s.total_nights,

                s.adults,

                s.children,

                s.babies,

                s.total_guests,

                s.adr,

                s.estimated_revenue,

                s.is_canceled,

                s.is_repeated_guest,

                s.previous_cancellations,

                s.previous_bookings_not_canceled,

                s.booking_changes,

                s.days_in_waiting_list,

                s.required_car_parking_spaces,

                s.total_of_special_requests,

                s.meal,

                s.deposit_type,

                s.reservation_status,

                s.reservation_status_date,

                s.agent,

                s.company

            FROM {REDSHIFT_SCHEMA}.{SILVER_TABLE} s

            -- =================================================
            -- DATE
            -- =================================================

            INNER JOIN {REDSHIFT_SCHEMA}.{DIM_DATE} d

                ON d.full_date = s.arrival_date

            -- =================================================
            -- HOTEL
            -- =================================================

            INNER JOIN {REDSHIFT_SCHEMA}.{DIM_HOTEL} h

                ON h.hotel = s.hotel

            -- =================================================
            -- CUSTOMER
            -- =================================================

            INNER JOIN {REDSHIFT_SCHEMA}.{DIM_CUSTOMER} c

                ON COALESCE(c.country, '')
                    = COALESCE(s.country, '')

                AND COALESCE(c.customer_type, '')
                    = COALESCE(s.customer_type, '')

                AND COALESCE(c.is_repeated_guest, -1)
                    = COALESCE(s.is_repeated_guest, -1)

            -- =================================================
            -- ROOM
            -- =================================================

            INNER JOIN {REDSHIFT_SCHEMA}.{DIM_ROOM} r

                ON COALESCE(r.reserved_room_type, '')
                    = COALESCE(s.reserved_room_type, '')

                AND COALESCE(r.assigned_room_type, '')
                    = COALESCE(s.assigned_room_type, '')

            -- =================================================
            -- CHANNEL
            -- =================================================

            INNER JOIN {REDSHIFT_SCHEMA}.{DIM_CHANNEL} ch

                ON COALESCE(ch.market_segment, '')
                    = COALESCE(s.market_segment, '')

                AND COALESCE(ch.distribution_channel, '')
                    = COALESCE(s.distribution_channel, '')

            -- =================================================
            -- DATA QUALITY
            -- =================================================

            WHERE s.data_quality_status = 'VALID';
        """)
    )

    print("  ✓ Fact_booking carregada.")


# =========================================================
# EXECUÇÃO
# =========================================================

def run_gold():

    engine = get_engine()

    print(
        "=============================================="
    )

    print(
        "Iniciando carga da camada GOLD"
    )

    print(
        "=============================================="
    )

    with engine.begin() as connection:

        # =====================================================
        # LIMPA A GOLD
        # =====================================================

        print("\nLimpando tabelas Gold...")

        connection.execute(
            text(
                f"""
                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{FACT_BOOKING};

                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{DIM_DATE};

                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{DIM_HOTEL};

                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{DIM_CUSTOMER};

                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{DIM_ROOM};

                TRUNCATE TABLE
                    {REDSHIFT_SCHEMA}.{DIM_CHANNEL};
                """
            )
        )

        print("  ✓ Gold limpa.")

        # =====================================================
        # DIMENSÕES
        # =====================================================

        load_dimensions(connection)

        # =====================================================
        # FACT
        # =====================================================

        load_fact(connection)

    print(
        "\n=============================================="
    )

    print(
        "GOLD carregada com sucesso!"
    )

    print(
        "=============================================="
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    run_gold()