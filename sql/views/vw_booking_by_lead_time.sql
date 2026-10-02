-- ============================================================================
-- VIEW: vw_booking_by_lead_time
-- CAMADA: Gold / Business
-- OBJETIVO:
--     Segmenta as reservas por faixas de lead time para analisar como
--     a antecedência da reserva está relacionada ao volume de reservas,
--     cancelamentos, receita, ADR e duração da estadia.
--
-- GRANULARIDADE:
--     Uma linha por faixa de lead time.
--
-- PRINCIPAIS INDICADORES:
--     - Total de reservas
--     - Reservas canceladas e confirmadas
--     - Taxa de cancelamento
--     - Lead time médio
--     - ADR médio
--     - Média e total de noites
--     - Receita estimada total
-- ============================================================================

CREATE OR REPLACE VIEW hotel_bookings.vw_booking_by_lead_time AS

SELECT
    CASE
        WHEN lead_time <= 7
            THEN '0-7 dias'

        WHEN lead_time <= 30
            THEN '8-30 dias'

        WHEN lead_time <= 60
            THEN '31-60 dias'

        WHEN lead_time <= 90
            THEN '61-90 dias'

        WHEN lead_time <= 180
            THEN '91-180 dias'

        ELSE '181+ dias'
    END AS lead_time_range,

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

    ROUND(AVG(lead_time), 2) AS avg_lead_time,

    ROUND(AVG(adr), 2) AS avg_adr,

    ROUND(AVG(total_nights), 2) AS avg_nights,

    SUM(total_nights) AS total_nights,

    SUM(estimated_revenue) AS total_estimated_revenue

FROM hotel_bookings.fact_booking

GROUP BY
    CASE
        WHEN lead_time <= 7
            THEN '0-7 dias'

        WHEN lead_time <= 30
            THEN '8-30 dias'

        WHEN lead_time <= 60
            THEN '31-60 dias'

        WHEN lead_time <= 90
            THEN '61-90 dias'

        WHEN lead_time <= 180
            THEN '91-180 dias'

        ELSE '181+ dias'
    END;