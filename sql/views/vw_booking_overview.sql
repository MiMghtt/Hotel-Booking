-- ============================================================================
-- VIEW: vw_booking_overview
-- CAMADA: Gold / Business
-- OBJETIVO:
--     Consolida os principais indicadores das reservas em uma única visão,
--     permitindo uma análise geral do volume de reservas, cancelamentos,
--     receita, ADR, lead time, hóspedes e noites.
--
-- GRANULARIDADE:
--     Uma única linha representando o conjunto total de reservas.
--
-- PRINCIPAIS INDICADORES:
--     - Total de reservas
--     - Reservas canceladas e confirmadas
--     - Taxa de cancelamento
--     - Receita estimada total
--     - ADR médio
--     - Lead time médio
--     - Total de hóspedes e noites
-- ============================================================================

CREATE OR REPLACE VIEW hotel_bookings.vw_booking_overview AS

SELECT
    COUNT(*) AS total_bookings,

    SUM(
        CASE
            WHEN is_canceled = 1 THEN 1
            ELSE 0
        END
    ) AS canceled_bookings,

    SUM(
        CASE
            WHEN is_canceled = 0 THEN 1
            ELSE 0
        END
    ) AS confirmed_bookings,

    ROUND(
        100.0 *
        SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate,

    SUM(total_guests) AS total_guests,

    SUM(total_nights) AS total_nights,

    ROUND(AVG(total_nights), 2) AS avg_nights_per_booking,

    ROUND(AVG(lead_time), 2) AS avg_lead_time,

    ROUND(AVG(adr), 2) AS avg_adr,

    SUM(estimated_revenue) AS total_estimated_revenue,

    ROUND(
        AVG(estimated_revenue),
        2
    ) AS avg_revenue_per_booking

FROM hotel_bookings.fact_booking;