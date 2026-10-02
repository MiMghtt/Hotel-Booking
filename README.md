# Hotel Booking Data Pipeline

Projeto de engenharia e análise de dados desenvolvido a partir de um dataset de reservas de hotéis.

O fluxo transforma os dados brutos em uma camada analítica no Amazon Redshift, aplica regras de qualidade, organiza os dados em um modelo dimensional e disponibiliza indicadores e análises no Power BI.

## Arquitetura

### Fluxo utilizado

```text
CSV
 ↓
Python / ETL
 ↓
Amazon Redshift
 ↓
Business Views
 ↓
Power BI / Indicadores
```

![Arquitetura do pipeline]<img width="2043" height="770" alt="architecture" src="https://github.com/user-attachments/assets/e95b2e41-9012-462b-bf55-174397dd5267" />


### Tecnologias

- Python
- Pandas
- Boto3
- SQL
- SQLAlchemy
- Amazon S3
- Amazon Redshift Serverless
- Power BI

## Camadas de dados

### RAW

O dataset original é armazenado no Amazon S3:

```text
s3://hotel-booking-mmarighetti/raw/hotel_bookings.csv
```

A camada RAW mantém os dados na forma original.

### ETL

O processo em Python realiza:

- leitura do CSV no S3;
- padronização dos nomes das colunas;
- tratamento de valores nulos;
- conversão de tipos;
- criação de campos derivados;
- aplicação das regras de qualidade;
- remoção de duplicidades exatas;
- validação dos dados;
- carga no Redshift.

### Silver

Tabela:

```text
hotel_bookings.silver
```

A Silver contém os dados tratados e também mantém registros classificados como inválidos quando necessário para rastreabilidade.

Principais status de qualidade:

| Status | Regra |
|---|---|
| `VALID` | Registro sem violação das regras definidas |
| `INVALID_ADR` | `adr < 0` |
| `INVALID_EXTREME_ADR` | `adr > 5000` e reserva cancelada |
| `INVALID_EXTREME_OCCUPANCY` | `adults > 20`, `adr = 0` e reserva cancelada |

Somente registros `VALID` são utilizados para construir a Gold.

### Gold

A Gold utiliza um modelo dimensional em Star Schema.

![Modelo dimensional]<img width="1536" height="1024" alt="star-schema" src="https://github.com/user-attachments/assets/ac18de67-5d87-41f4-be50-5fdd92ed6cad" />


Tabelas:

```text
dim_date
dim_hotel
dim_customer
dim_room
dim_channel
fact_booking
```

A `fact_booking` concentra as métricas e eventos das reservas, enquanto as dimensões fornecem o contexto para análise.

Relacionamentos:

```text
dim_date      1 ─── N fact_booking
dim_hotel     1 ─── N fact_booking
dim_customer  1 ─── N fact_booking
dim_room      1 ─── N fact_booking
dim_channel   1 ─── N fact_booking
```

# Indicadores

Os indicadores foram construídos no Power BI utilizando medidas DAX sobre a `fact_booking`.

## 1. ADR Médio

### Objetivo de negócio

Medir o valor médio da diária das reservas, permitindo acompanhar o nível de preço praticado.

### Fórmula utilizada

```text
ADR Médio = Média do campo adr
```

DAX:

```DAX
ADR Médio =
AVERAGE(fact_booking[adr])
```

### Query SQL

```sql
SELECT
    AVG(adr) AS adr_medio
FROM hotel_bookings.fact_booking;
```

### Interpretação dos resultados

O dashboard apresenta um ADR médio de aproximadamente **106,29**.

Esse indicador representa o valor médio de diária observado nas reservas consideradas na camada analítica.

---

## 2. Lead Time Médio

### Objetivo de negócio

Medir com quantos dias de antecedência, em média, as reservas são realizadas.

Esse indicador ajuda a entender o comportamento de planejamento dos clientes e o nível de antecedência da demanda.

### Fórmula utilizada

```text
Lead Time Médio = Média do campo lead_time
```

DAX:

```DAX
Lead Time Médio =
AVERAGE(fact_booking[lead_time])
```

### Query SQL

```sql
SELECT
    AVG(lead_time) AS lead_time_medio
FROM hotel_bookings.fact_booking;
```

### Interpretação dos resultados

O dashboard apresenta um Lead Time Médio de aproximadamente **79,86 dias**.

Isso significa que, em média, as reservas são realizadas cerca de 80 dias antes da data de chegada.

---

## 3. Room Nights Vendidas

### Objetivo de negócio

Medir o volume total de noites comercializadas pelas reservas.

Esse indicador é mais representativo do volume de hospedagem do que simplesmente contar reservas, pois considera a duração de cada estadia.

### Fórmula utilizada

```text
Room Nights Vendidas = Soma de total_nights
```

DAX:

```DAX
Room Nights Vendidas =
SUM(fact_booking[total_nights])
```

### Query SQL

```sql
SELECT
    SUM(total_nights) AS room_nights_vendidas
FROM hotel_bookings.fact_booking;
```

### Interpretação dos resultados

O dashboard apresenta aproximadamente **317 mil Room Nights Vendidas**.

Isso representa o volume acumulado de noites de hospedagem associado às reservas analisadas.

---

## 4. Receita Estimada

### Objetivo de negócio

Estimar o valor de receita associado às reservas a partir da diária média e da quantidade de noites.

### Fórmula utilizada

A receita estimada é calculada no ETL:

```text
estimated_revenue = adr × total_nights
```

No Power BI:

```DAX
Receita Estimada =
SUM(fact_booking[estimated_revenue])
```

### Query SQL

```sql
SELECT
    SUM(estimated_revenue) AS receita_estimada
FROM hotel_bookings.fact_booking;
```

### Interpretação dos resultados

O dashboard apresenta aproximadamente **R$ 34,46 milhões** em receita estimada.

O valor representa uma estimativa baseada no ADR e no total de noites, não necessariamente a receita financeira efetivamente recebida.

---

## 5. Taxa de Cancelamento

### Objetivo de negócio

Medir a proporção de reservas canceladas em relação ao total de reservas.

Esse indicador ajuda a acompanhar o nível de cancelamento da operação.

### Fórmula utilizada

```text
Taxa de Cancelamento =
Reservas canceladas / Total de reservas
```

DAX:

```DAX
Taxa de Cancelamento =
DIVIDE(
    CALCULATE(
        COUNTROWS(fact_booking),
        fact_booking[is_canceled] = 1
    ),
    COUNTROWS(fact_booking),
    0
)
```

### Query SQL

```sql
SELECT
    100.0
    * SUM(CASE WHEN is_canceled = 1 THEN 1 ELSE 0 END)
    / NULLIF(COUNT(*), 0) AS taxa_cancelamento
FROM hotel_bookings.fact_booking;
```

### Interpretação dos resultados

O dashboard apresenta uma taxa de cancelamento de aproximadamente **27,48%**.

Isso significa que cerca de 27 em cada 100 reservas analisadas estão classificadas como canceladas.

# Dashboard

O resultado final foi disponibilizado no Power BI com cinco indicadores principais, filtros e quatro análises complementares.

![Dashboard Power BI]<img width="745" height="412" alt="dashboard" src="https://github.com/user-attachments/assets/93b9dd26-5c86-447e-befe-13fe552555df" />


### Indicadores

- ADR Médio
- Lead Time Médio
- Room Nights Vendidas
- Receita Estimada
- Taxa de Cancelamento

### Filtros

- Período
- Tipo de Cliente
- Hotel
- Canal de Distribuição

### Análises

- Reservas por mês
- Reservas por hotel
- Reservas por segmento
- Reservas por faixa de Lead Time

## Business Views

Foram criadas cinco Business Views no schema `hotel_bookings`:

| View | Objetivo |
|---|---|
| `vw_booking_overview` | Visão geral das reservas |
| `vw_booking_seasonality_hotel` | Sazonalidade por hotel |
| `vw_booking_by_lead_time` | Reservas por faixa de antecedência |
| `vw_room_match` | Comparação entre quarto reservado e atribuído |
| `vw_booking_by_channel` | Análise por canal |

As Views complementam o modelo dimensional e disponibilizam análises já organizadas para consumo.

## Data Quality

A estratégia adotada foi manter rastreabilidade na Silver e impedir que registros classificados como inválidos contaminem a camada analítica.

```text
RAW
 ↓
ETL + Data Quality
 ↓
SILVER
 ├── VALID
 └── INVALID_*
        ↓
      GOLD
        ↓
   BUSINESS VIEWS
        ↓
      POWER BI
```

Os registros classificados como inválidos permanecem na Silver quando a regra possui finalidade de auditoria. A Gold utiliza somente registros `VALID`.

## Estrutura do projeto

```text
hotel-booking-pipeline/
│
├── README.md
├── docs/
├── sql/
│   ├── star_schema/
│   └── views/
├── src/
│   ├── etl.py
│   ├── data_quality_silver.py
│   ├── gold.py
│   ├── data_quality_gold.py
│   └── create_views.py
├── tests/
├── requirements.txt
├── .env
└── .gitignore
```

## Execução

```bash
python src/etl.py
python src/data_quality_silver.py
python src/gold.py
python src/data_quality_gold.py
python src/create_views.py
```

Fluxo:

```text
ETL
 ↓
Silver
 ↓
Data Quality
 ↓
Gold
 ↓
Business Views
 ↓
Power BI
```

## Resultado

O projeto implementa um fluxo completo de dados, desde a ingestão do dataset bruto até o consumo analítico, combinando tratamento de dados, regras de qualidade, modelagem dimensional, SQL analítico e visualização de indicadores de negócio.
