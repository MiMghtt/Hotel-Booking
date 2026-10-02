# Hotel Booking Data Pipeline

Pipeline de dados desenvolvido para transformar dados de reservas hoteleiras em uma camada analítica estruturada, com processamento em Python, armazenamento e modelagem no Amazon Redshift e visualização no Power BI.

## 🎯 Objetivo

Construir uma solução de dados de ponta a ponta capaz de:

- ingerir dados brutos de reservas;
- aplicar limpeza, padronização e transformações;
- criar campos derivados para análise;
- aplicar regras de qualidade e rastrear registros inválidos;
- organizar os dados em um modelo dimensional;
- disponibilizar consultas analíticas por meio de views de negócio;
- alimentar um dashboard no Power BI com indicadores operacionais e comerciais.

---

## 🏗️ Arquitetura

<img width="2043" height="770" alt="architecture" src="https://github.com/user-attachments/assets/7ec9e9e8-c679-457b-9663-587e7dd68f64" />

---

## 🔄 ETL e criação dos campos derivados

Após a leitura e padronização do dataset, o ETL cria campos derivados que não existiam originalmente na fonte. Essas colunas transformam informações operacionais em atributos prontos para análises de período, ocupação e receita.

### `arrival_date`

```python
df = create_arrival_date(df)
```

Combina:

- `arrival_date_year`
- `arrival_date_month`
- `arrival_date_day_of_month`

em uma única coluna de data.

O campo `arrival_date` facilita filtros temporais, agregações por período e a criação da `dim_date`. Em vez de trabalhar separadamente com ano, mês e dia, o modelo passa a possuir uma data única que pode ser relacionada à dimensão calendário.

### `total_nights`

```python
df = create_total_nights(df)
```

Calcula o total de noites da reserva:

```text
total_nights =
stays_in_weekend_nights + stays_in_week_nights
```

Esse campo consolida as duas medidas originais de permanência em uma métrica única. Ele é utilizado para analisar volume de noites vendidas, duração média das reservas e também participa do cálculo da receita estimada.

### `total_guests`

```python
df = create_total_guests(df)
```

Calcula o total de hóspedes:

```text
total_guests =
adults + children + babies
```

A coluna permite analisar ocupação e quantidade de pessoas associadas às reservas sem precisar repetir a soma em cada consulta analítica.

### `estimated_revenue`

```python
df = create_estimated_revenue(df)
```

Estima a receita associada à reserva a partir do ADR (`adr`) e da quantidade total de noites:

```text
estimated_revenue =
adr × total_nights
```

Essa métrica transforma o valor diário da hospedagem em uma estimativa de receita por reserva e posteriormente permite calcular receita total e receita média no modelo analítico.

Além de ser utilizada nas análises, a regra também é validada na etapa de Data Quality para garantir que o valor armazenado permaneça consistente com sua fórmula de origem.

---

## 🧪 Data Quality

A qualidade dos dados é tratada em duas etapas: durante o ETL, para classificação e tratamento dos registros, e posteriormente no Redshift, para validar a integridade da tabela Silver.

### Tratamento e classificação

O objetivo não é simplesmente excluir registros suspeitos. Registros que apresentam problemas de qualidade são mantidos na Silver para rastreabilidade, mas classificados para impedir que contaminem as análises da camada Gold.

Principais regras aplicadas:

| Regra | Tratamento | Motivo |
|---|---|---|
| `adr < 0` | `INVALID_ADR` | ADR negativo não representa um valor válido de diária |
| `adr > 5000` + reserva cancelada | `INVALID_EXTREME_ADR` | combinação considerada anômala para a análise |
| `adults > 20` + `adr = 0` + reserva cancelada | `INVALID_EXTREME_OCCUPANCY` | identifica registros extremos de ocupação sem valor de diária |
| adultos/crianças/bebês negativos | inválido estrutural | quantidade negativa não possui significado operacional |
| noites/hóspedes negativos | inválido estrutural | viola a lógica básica das métricas derivadas |

Valores como `adr = 0` e `adults = 0` não são automaticamente considerados inválidos, pois podem representar situações legítimas do dataset. A classificação foi baseada na combinação de atributos, evitando remover registros apenas por apresentarem um valor isoladamente incomum.

### Validações da Silver

A rotina de Data Quality também verifica:

1. **Volume** — garante que a tabela não esteja vazia e monitora se a quantidade de registros está dentro do esperado.
2. **Valores nulos** — verifica campos críticos como hotel, cancelamento, ano/mês de chegada e ADR.
3. **Possíveis duplicidades** — compara uma combinação de atributos relevantes para identificar registros potencialmente duplicados.
4. **Ranges e regras de negócio** — valida valores negativos e domínios esperados, como `is_canceled` limitado a `0` ou `1`.
5. **Consistência** — verifica se os campos derivados continuam coerentes com suas origens:
   - `total_nights = stays_in_weekend_nights + stays_in_week_nights`;
   - `total_guests = adults + children + babies`;
   - `estimated_revenue ≈ adr × total_nights`, considerando tolerância de `0,01`.

Essas verificações evitam que erros estruturais ou inconsistências matemáticas avancem para a camada analítica.

---

## ⭐ Modelo dimensional Gold

Os registros classificados como `VALID` são utilizados para construir a camada Gold em um modelo Star Schema.

### Fact

`fact_booking`

Concentra as métricas e atributos transacionais das reservas, como:

- `lead_time`
- `total_nights`
- `total_guests`
- `adr`
- `estimated_revenue`
- `is_canceled`
- `booking_changes`
- `total_of_special_requests`

### Dimensions

- `dim_date` — calendário e atributos de data;
- `dim_hotel` — hotel da reserva;
- `dim_customer` — perfil do cliente;
- `dim_room` — tipos de quarto reservado e atribuído;
- `dim_channel` — segmento de mercado e canal de distribuição.

Essa estrutura separa métricas de negócio das dimensões utilizadas para filtragem e agrupamento, facilitando as consultas analíticas e o consumo pelo Power BI.

<img width="1536" height="1024" alt="star-schema" src="https://github.com/user-attachments/assets/6a2a06c4-e4f7-4f1c-bc59-60f8445e97e8" />


---

## 📊 Business Views

Depois da construção da Gold, foram criadas cinco views no Redshift. Elas funcionam como uma camada semântica de negócio: organizam métricas e dimensões em estruturas voltadas diretamente às perguntas que o dashboard precisa responder.

### `vw_booking_overview`

Consolida os principais indicadores gerais da operação:

- total de reservas;
- reservas canceladas e confirmadas;
- taxa de cancelamento;
- total de hóspedes;
- total de noites;
- média de noites por reserva;
- lead time médio;
- ADR médio;
- receita estimada total;
- receita média por reserva.

É a principal visão de **resumo executivo** e concentra os mesmos conceitos utilizados nos cards do Power BI.

### `vw_booking_seasonality_hotel`

Relaciona reservas com a dimensão de data e hotel para analisar:

- reservas por mês;
- cancelamentos;
- taxa de cancelamento;
- noites;
- hóspedes;
- ADR médio;
- receita estimada.

Essa view sustenta a análise de **sazonalidade e comportamento por hotel**.

### `vw_booking_by_lead_time`

Agrupa as reservas em faixas de antecedência:

- `0-7`
- `8-30`
- `31-60`
- `61-90`
- `91-180`
- `181+`

Permite entender como o volume de reservas se distribui de acordo com o tempo entre a reserva e a chegada.

### `vw_booking_by_channel`

Agrupa as reservas por:

- segmento de mercado;
- canal de distribuição.

Além do volume de reservas, permite comparar cancelamentos, noites, hóspedes, ADR e receita estimada.

Essa visão é utilizada para a análise de **reservas por segmento/canal** no Power BI.

### `vw_room_match`

Compara o tipo de quarto originalmente reservado com o tipo de quarto efetivamente atribuído.

Permite medir:

- quantidade de reservas;
- reservas com correspondência entre quarto reservado e atribuído;
- alterações de quarto;
- taxa de correspondência;
- taxa de alteração.

Essa visão permite identificar diferenças entre expectativa de reserva e alocação efetiva.

---

## 📈 Power BI e conexão com as Business Views

O Power BI foi conectado ao modelo analítico do Amazon Redshift. O Star Schema fornece as relações entre fatos e dimensões, enquanto as Business Views organizam os principais recortes analíticos utilizados no dashboard.

A relação entre as camadas pode ser resumida assim:

```text
Silver
  ↓
Gold / Star Schema
  ↓
Business Views
  ↓
Power BI
```

### Indicadores principais

Os cards do dashboard representam os principais indicadores definidos na `vw_booking_overview`:

| Indicador | Conceito no modelo | Relação com a View |
|---|---|---|
| **ADR Médio** | Média de `adr` | `vw_booking_overview.avg_adr` |
| **Lead Time Médio** | Média de `lead_time` | `vw_booking_overview.avg_lead_time` |
| **Receita Estimada** | Soma de `estimated_revenue` | `vw_booking_overview.total_estimated_revenue` |
| **Room Nights Vendidas** | Soma de `total_nights` | `vw_booking_overview.total_nights` |
| **Taxa de Cancelamento** | Cancelamentos / total de reservas | `vw_booking_overview.cancellation_rate` |

Assim, os indicadores do Power BI não são métricas isoladas: eles refletem as mesmas regras e métricas consolidadas na camada de negócio.

### Visuais e suas respectivas análises

Além dos cards, os gráficos do dashboard estão relacionados às demais views:

| Visual do Power BI | Fonte conceitual | Objetivo |
|---|---|---|
| **Reservas por Mês** | `vw_booking_seasonality_hotel` | analisar sazonalidade |
| **Total de Reservas por Hotel** | `vw_booking_seasonality_hotel` | comparar hotéis |
| **Total de Reservas por Segmento** | `vw_booking_by_channel` | analisar origem/segmentação das reservas |
| **Reservas por Lead Time** | `vw_booking_by_lead_time` | analisar antecedência das reservas |

Os filtros de **período, tipo de cliente, hotel e canal de distribuição** utilizam as dimensões do Star Schema, permitindo que os indicadores e visuais sejam recalculados conforme o contexto selecionado.

---

## 📊 Dashboard

<img width="745" height="412" alt="dashboard" src="https://github.com/user-attachments/assets/b80bcc9c-1cbb-4687-ba49-3c88f7b9f2d7" />


### Principais indicadores apresentados

- **ADR Médio:** R$ 106,29
- **Lead Time Médio:** 79,86 dias
- **Receita Estimada:** R$ 34,46 milhões
- **Room Nights Vendidas:** 317 mil
- **Taxa de Cancelamento:** 27,48%

[📥 Baixar arquivo Power BI (.pbix)](./Hotel-Booking.pbix)

---

## 📁 Estrutura do projeto

```text
hotel-booking-pipeline/
├── README.md
├── Hotel-Booking.pbix
├── data/
│   └── hotel_bookings.csv
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── data_quality.md
│   ├── data_model.md
│   └── business_views.md
├── sql/
│   ├── star_schema/
│   │   ├── create_dimensions.sql
│   │   └── create_fact.sql
│   └── views/
│       ├── vw_booking_by_channel.sql
│       ├── vw_booking_by_lead_time.sql
│       ├── vw_booking_overview.sql
│       ├── vw_booking_seasonality_hotel.sql
│       └── vw_room_match.sql
├── src/
│   ├── etl.py
│   ├── data_quality_silver.py
│   ├── gold.py
│   ├── data_quality_gold.py
│   └── create_views.py
├── requirements.txt
└── .gitignore
```

---

## 🛠️ Tecnologias

- **Python** — ETL, transformação e validação;
- **Pandas** — tratamento dos dados;
- **SQLAlchemy / psycopg2** — conexão com Redshift;
- **Amazon S3** — armazenamento dos dados RAW;
- **Amazon Redshift Serverless** — Silver, Gold e Business Views;
- **SQL** — modelagem e camada analítica;
- **Power BI** — dashboard e análise dos indicadores;
- **Git/GitHub** — versionamento do projeto.

---

## ▶️ Execução

1. Configure as credenciais no `.env`.
2. Execute o ETL para carregar e transformar os dados.
3. Execute a rotina de Data Quality da Silver.
4. Execute a construção da camada Gold.
5. Execute a validação da Gold.
6. Crie as Business Views.
7. Conecte o Power BI ao Redshift.
8. Atualize o modelo e o dashboard.

---

## 🔐 Segurança

As credenciais de AWS e Redshift são armazenadas em `.env` e não fazem parte do repositório.

O `.gitignore` também impede o versionamento de ambientes virtuais, arquivos compilados e configurações locais.

---

## 👤 Autor

**Michelle Marighetti**

Projeto desenvolvido como estudo prático de Engenharia de Dados, com foco em ETL, qualidade, modelagem dimensional, SQL analítico, AWS e BI.
