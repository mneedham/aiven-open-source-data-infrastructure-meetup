# London Open Source Data Infrastructure Meetup - December 2023

https://www.meetup.com/uk-open-source-data-infrastructure-meetup/events/297395569/

**Analytics on your laptop with ClickHouse Local**

Although ClickHouse is usually used for large-scale data analytics with lots of concurrent users, we can also use it to run analytics from our laptop with ClickHouse local. In this talk, I'll give an introduction to ClickHouse and its use cases, before showing how to analyse data both on my machine and from the internet if the WiFi treats us well!

## Setting up ClickHouse

```bash
curl https://clickhouse.com/ | sh
```

```bash
./clickhouse local -m
```

## Demo 1: Mid Journey Metadata

https://huggingface.co/datasets/vivym/midjourney-messages

Parquet files containing metadata about images created on Mid Journey

### View the metadata

```sql
FROM url('https://huggingface.co/datasets/vivym/midjourney-messages/resolve/main/data/000000.parquet', ParquetMetadata)
SELECT *;
```

```sql
CREATE OR REPLACE FUNCTION midJourneyRemote AS 
files -> 'https://huggingface.co/datasets/vivym/midjourney-messages/resolve/main/data/' || files;
```

```sql
CREATE OR REPLACE FUNCTION midJourneyLocal AS 
files -> 'demo1/' || files;
```


```sql
FROM url(midJourneyRemote('000000.parquet'), ParquetMetadata)
SELECT *
SETTINGS max_http_get_redirects=1
Format Vertical;
```

```sql
FROM url(midJourneyRemote('000000.parquet'), ParquetMetadata)
ARRAY JOIN columns AS col
SELECT untuple(col) AS c
SETTINGS max_http_get_redirects=1
Format Vertical;
```

```sql
FROM url(midJourneyRemote('000000.parquet'), ParquetMetadata) 
ARRAY JOIN columns AS col
SELECT col.name, col.physical_type, col.logical_type
SETTINGS max_http_get_redirects=1;
```

```sql
FROM file(midJourneyLocal('000000.parquet'), ParquetMetadata) 
ARRAY JOIN columns AS col
SELECT col.name, col.physical_type, col.logical_type;
```


### Query the data

```sql
FROM file(midJourneyLocal('000000.parquet'), Parquet) 
select 
    sum(size) AS raw, formatReadableSize(raw), 
    avg(size) avgRaw, formatReadableSize(avgRaw), 
    count();
```

```sql
FROM file(midJourneyLocal('0000{00..55}.parquet'), Parquet) 
select 
    sum(size) AS raw, formatReadableSize(raw), 
    avg(size) avgRaw, formatReadableSize(avgRaw), 
    count();
```

```sql
FROM file(midJourneyLocal('0000{00..55}.parquet'), Parquet)
select
    url, content, formatReadableSize(size) 
order by size desc 
limit 10 
Format Vertical;
```

## Demo 1: Wikimedia 

### Exploring the stream

```bash
docker-compose up
```

```bash
rpk topic create -p 5 wiki_events
```

```bash
curl -N https://stream.wikimedia.org/v2/stream/recentchange 
```

```bash
curl -N https://stream.wikimedia.org/v2/stream/recentchange |
awk '/^data: /{gsub(/^data: /, ""); print}' |
jq -cr --arg sep ø '[.meta.id, tostring] | join($sep)' |
kcat -P -b localhost:9092 -t wiki_events -Kø
```

### Importing the stream

```sql
CREATE DATABASE wiki;
```

```sql
USE wiki;
```

```sql
CREATE TABLE wikiQueue(
    id UInt32,
    type String,
    title String,
    title_url String,
    comment String,
    timestamp UInt64,
    user String,
    bot Boolean,
    server_url String,
    server_name String,
    wiki String,
    meta Tuple(uri String, id String, stream String, topic String, domain String)
)
ENGINE = Kafka('localhost:9092', 'wiki_events', 'consumer-group-wiki', 'JSONEachRow')
SETTINGS kafka_flush_interval_ms=1000;
```

```sql
CREATE TABLE wiki (
    dateTime DateTime64(3, 'UTC'),
    type String,
    title String,
    title_url String,
    id String,
    stream String,
    topic String,
    user String,
    bot Boolean, 
    server_name String,
    wiki String
) ENGINE = MergeTree ORDER BY dateTime;
```

```sql
CREATE MATERIALIZED VIEW wiki_mv TO wiki AS 
SELECT toDateTime(timestamp) AS dateTime,
       type, title, title_url, 
       tupleElement(meta, 'id') AS id, 
       tupleElement(meta, 'stream') AS stream, 
       tupleElement(meta, 'topic') AS topic, 
       user, bot, server_name, wiki
FROM wikiQueue;
```

### Querying the stream

```sql
FROM wiki select * LIMIT 1 Format Vertical;
```

```sql
FROM wiki
SELECT user, COUNT(*) AS updates
GROUP BY user
ORDER BY updates DESC
LIMIT 10;
```

```sql
WITH users AS (
    SELECT user, COUNT(*) AS updates
    FROM wiki
    GROUP BY user
    ORDER BY updates DESC
)
SELECT
    user,
    updates,
    bar(updates, 0, (SELECT max(updates) FROM users), 30) AS plot
FROM users
LIMIT 10;
```

## Flushing Kafka --> ClickHouse

Check the lag of the consumer group:

```bash
rpk group describe consumer-group-wiki
```

(Need to have ClickHouse Local running for messages to be consumed)

Drop the Kafka engine table and re-create it to adjust the flush interval.

```sql
drop table wikiQueue;
```

```sql
CREATE TABLE wikiQueue(
    id UInt32,
    type String,
    title String,
    title_url String,
    comment String,
    timestamp UInt64,
    user String,
    bot Boolean,
    server_url String,
    server_name String,
    wiki String,
    meta Tuple(uri String, id String, stream String, topic String, domain String)
)
ENGINE = Kafka('localhost:9092', 'wiki_events', 'consumer-group-wiki', 'JSONEachRow')
SETTINGS kafka_flush_interval_ms=1000;
```
