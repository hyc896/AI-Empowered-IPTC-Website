# CNBC Technology News Collector

## Overview

CNBC Technology News Collector is an RSS-based message source for collecting technology news from CNBC.

## Data Source Information

- **RSS Feed URL**: https://www.cnbc.com/id/19854910/device/rss/rss.html
- **Format**: Standard RSS 2.0
- **Update Frequency**: ~30 entries per fetch
- **Language**: English
- **Region**: United States
- **Authority**: Top-tier US financial media technology section

## Architecture Features

- **Pure RSS Mode**: No need to visit detail pages, RSS content is complete enough
- **Pre-translation Mode**: Translation completed outside database session
- **Pre-enhancement Mode**: Field enhancement (region + industry_tags + ai_tag) outside database session
- **Sliding Deduplication**: Query latest URL at startup, stop immediately when encountering existing records

## Field Mapping

### Core Fields (Following 2025 Standard)

| RSS Field | Database Field | Description |
|-----------|---------------|-------------|
| id/guid | external_id | External unique identifier |
| title | title | Article title |
| description/summary | content | Article content |
| link | url | Original article link (used for deduplication) |
| author | provider | Author |
| published | published_at | Publication time |
| - | crawled_at | Crawl time (auto-generated) |
| - | summary | Chinese summary (translated) |

### Enhanced Fields (2025 Mandatory)

| Field | Type | Description |
|-------|------|-------------|
| region | VARCHAR(200) | Region (Chinese format, default: "美国") |
| industry_tags | TEXT | Industry tags (comma-separated, max 3, AI-related must include "人工智能") |
| ai_tag | VARCHAR(50) | AI classification tag (AI科研信息/AI产业信息/AI治理信息) |

### Extended Fields

| Field | Type | Description |
|-------|------|-------------|
| category | VARCHAR(100) | Article category |
| language | VARCHAR(10) | Language (default: en) |
| media_content | VARCHAR(500) | Media content URL |
| tags | JSON | Tag list (JSON array) |

## Database

### Table Name
`mp_cnbc_messages`

### Indexes
- `idx_source_id`: source_id
- `idx_published_at`: published_at
- `idx_crawled_at`: crawled_at
- `idx_source_published`: (source_id, published_at) composite index
- `idx_url`: url (UNIQUE INDEX for deduplication)
- `idx_external_id`: external_id
- `idx_category`: category
- `idx_region`: region
- `idx_ai_tag`: ai_tag

## Test Results

### RSS Feed Accessibility Test
- **Status**: ✓ Successfully accessed
- **Entries Retrieved**: 30
- **HTTP Status**: 200
- **Content Length**: ~21KB

### Sample Entry
```
Title: Waymo says it will launch in more Texas and Florida cities in 2026
URL: https://www.cnbc.com/2025/11/18/waymo-texas-florida-2026.html
GUID: 108227526
Published: Tue, 18 Nov 2025 17:38:21 GMT
Summary: Waymo on Tuesday added Houston, San Antonio and Orlando to the list of cities where it plans to launch its robotaxi service in 2026.
```

### Database Registration
- **Source ID**: 8c31f770-c4a2-11f0-b75e-08bfb82ee112
- **Is Active**: True
- **Category**: news
- **Collector Module**: backend.sources.cnbc.collector
- **ChromaDB Collection**: cnbc_tech

## File Structure

```
backend/sources/cnbc/
├── __init__.py              # Package initialization
├── collector.py             # Main collector class (CNBCCollector)
├── register.sql             # Database registration SQL script
├── test_collector.py        # Full collector test (requires LLM)
├── simple_test.py           # Simple test (no LLM required)
└── README.md                # This file
```

## Usage

### Via Message Platform Service
The collector will be automatically invoked by the AutoCollector service based on the schedule configured in the database (every 1 hour).

### Manual Testing
```bash
# Simple test (no LLM required)
python backend/sources/cnbc/simple_test.py

# Full test (requires LLM services)
python backend/sources/cnbc/test_collector.py
```

## Notes

- **Translation/Field Enhancement**: Requires LLM services (Fast LLM client) to be running in production
- **ChromaDB**: Requires ChromaDB to be initialized for vector storage
- **Deduplication**: Uses URL field as unique constraint
- **Error Handling**: Falls back to English content if translation fails
- **Windows Compatibility**: Uses requests + feedparser to avoid timeout issues

## Production Checklist

- [x] ORM Entity created (CNBCMessage)
- [x] Collector implemented (CNBCCollector)
- [x] Database table created (mp_cnbc_messages)
- [x] Message source registered in mp_message_sources
- [x] RSS feed accessibility verified
- [x] Field mapping follows 2025 standard
- [x] Deduplication strategy implemented
- [x] ChromaDB collection configured
- [x] Test scripts provided

## References

- Standard Implementation: `backend/sources/wired/collector.py`
- Database Entities: `backend/database/entities.py`
- Field Standard: `CLAUDE.md` - "Database Design Specifications" section
