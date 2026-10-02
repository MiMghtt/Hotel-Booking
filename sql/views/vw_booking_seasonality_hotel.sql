-- ============================================================================
-- VIEW: vw_booking_seasonality_hotel
-- CAMADA: Gold / Business
-- OBJETIVO:
--     Apresenta a evolução das reservas por hotel ao longo do tempo,
--     permitindo identificar padrões de sazonalidade e variações na demanda,
--     receita e cancelamentos.
--
-- GRANULARIDADE:
--     Uma linha por hotel, ano e mês.
--
-- PRINCIPAIS INDICADORES:
--     - Total de reservas
--     - Reservas canceladas
--     - Taxa de cancelamento
--     - Total de noites e hóspedes
--     - ADR médio
--     - Receita estimada total
-- ============================================================================

CREATE OR REPLACE VIEW hotel_bookings.vw_booking_seasonality_hotel AS

SELECT
    h.hotel,

    d.year,

    d.month_number,

    d.month_name,

    COUNT(*) AS total_bookings,

    SUM(
        CASE
            WHEN f.is_canceled = 1 THEN 1
            ELSE 0
        END
    ) AS canceled_bookings,

    ROUND(
        100.0 *
        SUM(CASE WHEN f.is_canceled = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate,

    SUM(f.total_nights) AS total_nights,

    SUM(f.total_guests) AS total_guests,

    ROUND(AVG(f.adr), 2) AS avg_adr,

    SUM(f.estimated_revenue) AS total_estimated_revenue

FROM hotel_bookings.fact_booking f

JOIN hotel_bookings.dim_date d
    ON f.date_key = d.date_key

JOIN hotel_bookings.dim_hotel h
    ON f.hotel_key = h.hotel_key

GROUP BY
    h.hotel,
    d.year,
    d.month_number,
    d.month_name;