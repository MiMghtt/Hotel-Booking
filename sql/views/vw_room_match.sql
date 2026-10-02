-- ============================================================================
-- VIEW: vw_room_match
-- CAMADA: Gold / Business
-- OBJETIVO:
--     Analisa a relação entre o tipo de quarto reservado e o tipo de quarto
--     efetivamente alocado, identificando alterações na acomodação e
--     calculando a taxa de correspondência entre reserva e alocação.
--
-- GRANULARIDADE:
--     Uma linha por combinação de tipo de quarto reservado e alocado.
--
-- PRINCIPAIS INDICADORES:
--     - Total de reservas
--     - Reservas com correspondência
--     - Reservas com alteração de quarto
--     - Taxa de correspondência
--     - Taxa de alteração
-- ============================================================================

CREATE OR REPLACE VIEW hotel_bookings.vw_room_match AS

SELECT
    r.reserved_room_type,

    r.assigned_room_type,

    COUNT(*) AS total_bookings,

    SUM(
        CASE
            WHEN r.reserved_room_type = r.assigned_room_type
            THEN 1
            ELSE 0
        END
    ) AS matched_bookings,

    SUM(
        CASE
            WHEN r.reserved_room_type <> r.assigned_room_type
            THEN 1
            ELSE 0
        END
    ) AS changed_bookings,

    ROUND(
        100.0 *
        SUM(
            CASE
                WHEN r.reserved_room_type = r.assigned_room_type
                THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS match_rate,

    ROUND(
        100.0 *
        SUM(
            CASE
                WHEN r.reserved_room_type <> r.assigned_room_type
                THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT(*), 0),
        2
    ) AS change_rate

FROM hotel_bookings.fact_booking f

JOIN hotel_bookings.dim_room r
    ON f.room_key = r.room_key

GROUP BY
    r.reserved_room_type,
    r.assigned_room_type;