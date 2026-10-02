-- ============================================================================
-- VIEW: vw_booking_by_channel
-- CAMADA: Gold / Business
-- OBJETIVO:
--     Apresenta o desempenho dos canais de aquisição de reservas,
--     permitindo comparar volume de reservas, cancelamentos, receita,
--     ADR, hóspedes e noites entre os diferentes segmentos e canais
--     de distribuição.
--
-- GRANULARIDADE:
--     Uma linha por segmento de mercado e canal de distribuição.
--
-- PRINCIPAIS INDICADORES:
--     - Total de reservas
--     - Reservas canceladas
--     - Taxa de cancelamento
--     - Total de noites e hóspedes
--     - ADR médio
--     - Receita estimada total
-- ============================================================================

CREATE OR REPLACE VIEW hotel_bookings.vw_booking_by_channel AS

SELECT
    c.market_segment,

    c.distribution_channel,

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

JOIN hotel_bookings.dim_channel c
    ON f.channel_key = c.channel_key

GROUP BY
    c.market_segment,
    c.distribution_channel;