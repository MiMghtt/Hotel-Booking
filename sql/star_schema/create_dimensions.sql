-- =========================================================
-- GOLD - DIMENSIONS
-- Schema: hotel_bookings
--
-- Origem:
--   hotel_bookings.silver
--
-- Tabelas criadas:
--   dim_date
--   dim_hotel
--   dim_customer
--   dim_room
--   dim_channel
-- =========================================================


-- =========================================================
-- 1. DIM DATE
-- =========================================================

CREATE TABLE IF NOT EXISTS hotel_bookings.dim_date (

    date_key        INTEGER       NOT NULL,
    full_date       DATE          NOT NULL,

    year            INTEGER       NOT NULL,
    month_number    INTEGER       NOT NULL,
    month_name      VARCHAR(20)   NOT NULL,

    week_number     INTEGER,
    day_of_month    INTEGER       NOT NULL,

    quarter         INTEGER       NOT NULL,

    PRIMARY KEY (date_key)
);


-- =========================================================
-- 2. DIM HOTEL
-- =========================================================

CREATE TABLE IF NOT EXISTS hotel_bookings.dim_hotel (

    hotel_key       INTEGER       NOT NULL,
    hotel           VARCHAR(100)  NOT NULL,

    PRIMARY KEY (hotel_key)
);


-- =========================================================
-- 3. DIM CUSTOMER
-- =========================================================

CREATE TABLE IF NOT EXISTS hotel_bookings.dim_customer (

    customer_key        INTEGER       NOT NULL,

    country             VARCHAR(20),
    customer_type       VARCHAR(50),
    is_repeated_guest   INTEGER,

    PRIMARY KEY (customer_key)
);


-- =========================================================
-- 4. DIM ROOM
-- =========================================================

CREATE TABLE IF NOT EXISTS hotel_bookings.dim_room (

    room_key              INTEGER       NOT NULL,

    reserved_room_type    VARCHAR(10),
    assigned_room_type    VARCHAR(10),

    PRIMARY KEY (room_key)
);


-- =========================================================
-- 5. DIM CHANNEL
-- =========================================================

CREATE TABLE IF NOT EXISTS hotel_bookings.dim_channel (

    channel_key             INTEGER       NOT NULL,

    market_segment          VARCHAR(50),
    distribution_channel    VARCHAR(50),

    PRIMARY KEY (channel_key)
);