# Listarr

A single-user, self-hosted Flask application for discovering content via TMDB (The Movie Database) and importing curated lists into Radarr/Sonarr media servers.

## Features

- 🎬 **TMDB Integration**: Discover movies and TV shows (Trending, Popular, Top Rated, Discover with filters)
- 🔗 **IMDB ID Mapping**: Legal IMDB ID retrieval via TMDB (no web scraping)
- 🎯 **Radarr/Sonarr Import**: Fully configured import settings with quality profiles and root folders
- 🚀 **Bulk Import API**: 8x faster imports using batch operations (50 items per batch)
- 📊 **Dashboard Stats**: Read-only summary from Radarr/Sonarr with cached stats, "Added by Listarr" counter, and recent jobs
- 🔒 **Encrypted Storage**: API keys encrypted at rest with Fernet encryption
- ⏰ **Automated Scheduling**: Cron-based scheduling for automatic list execution
  - Presets for common intervals (hourly, daily, weekly)
  - Custom cron expressions for advanced users
  - Global pause toggle for maintenance
  - Pre-flight health checks before job execution
- 💾 **SQLite Database**: Persistent storage with WAL mode
- 🐳 **Docker-first**: Container-ready deployment

## Quick Start

### Development Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd listarr
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run first-time setup**

   ```bash
   python setup.py
   ```

   This creates:
   - Encryption key at `instance/.fernet_key`
   - SQLite database at `instance/listarr.db`

4. **Start the development server**

   ```bash
   python run.py
   ```

5. **Access the application**
   Open your browser to: http://localhost:5000

### Docker Deployment

1. **Create environment file**

   ```bash
   cp .env.example .env
   # Edit .env and set LISTARR_SECRET_KEY
   ```

2. **Build and run with Docker Compose**

   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   Open your browser to: http://localhost:5000

4. **View logs**
   ```bash
   docker-compose logs -f listarr
   ```

## Configuration

### Environment Variables

- `LISTARR_SECRET_KEY`: Flask secret key for sessions (required in production)
- `FERNET_KEY`: Optional override for encryption key (default: loaded from file)
- `FLASK_ENV`: Flask environment (development/production)
- `PORT`: Port to run the application on (default: 5000)
- `TZ`: Server timezone for schedule interpretation (default: UTC)
- `SCHEDULER_WORKER`: Internal Gunicorn worker flag (auto-managed, do not set manually)

### API Keys

Configure API keys through the web interface:

1. **TMDB API Key** - Settings page (`/settings`)
   - Test connection before saving
   - Required for list discovery
2. **Radarr API Key** - Config page (`/config`)
   - Configure URL and API key
   - Set default import settings (quality profile, root folder, monitoring)
3. **Sonarr API Key** - Config page (`/config`)
   - Configure URL and API key
   - Set default import settings (quality profile, root folder, season folder, monitoring)

All API keys are encrypted at rest using Fernet symmetric encryption.

## Usage

### Scheduling Lists

Listarr allows you to automate list execution using cron-based scheduling:

1. **Create a scheduled list** via the wizard:
   - Select a schedule preset (hourly, daily, weekly, etc.)
   - Or use a custom cron expression for advanced scheduling
   - The list will execute automatically at the specified intervals

2. **Edit existing lists** to add or change schedules:
   - Navigate to the Lists page and click "Edit"
   - Update the schedule preset or cron expression
   - Changes take effect immediately

3. **Manage schedules** on the Schedule page (`/schedule`):
   - View all scheduled lists and their next run times
   - Global pause toggle for maintenance (pauses all scheduled jobs)
   - Resume scheduling when ready

4. **Monitor upcoming jobs** on the Dashboard:
   - The Upcoming widget shows the next 5 scheduled jobs
   - Displays relative times ("in 2 hours", "in 3 days")
   - Updates automatically during job execution

## Project Structure

```
listarr/
├── listarr/              # Main application package
│   ├── forms/           # WTForms form definitions
│   ├── models/          # SQLAlchemy database models
│   ├── routes/          # Blueprint-based routes
│   ├── services/        # Business logic layer
│   │   ├── http_client.py       # Shared HTTP client with retry logic
│   │   ├── tmdb_service.py      # Direct TMDB API calls
│   │   ├── radarr_service.py    # Direct Radarr API calls
│   │   ├── sonarr_service.py    # Direct Sonarr API calls
│   │   └── crypto_utils.py      # Fernet encryption utilities
│   ├── static/          # Static assets (JS, images)
│   └── templates/       # Jinja2 HTML templates
├── instance/            # Runtime data (database, encryption key)
│   ├── .fernet_key     # Encryption key (NEVER commit!)
│   └── listarr.db      # SQLite database
├── run.py              # Development server entry point
├── setup.py            # First-time initialization script
└── requirements.txt    # Python dependencies
```

## Development Status

**~92% Complete** - 10 of 12 main phases complete, plus 8 sub-phases. All core features implemented including list management, wizard UI, TMDB caching, bulk import automation, job execution framework, 493 tests, automated scheduling, direct API integration, and comprehensive UI/UX improvements. Remaining: security hardening and release readiness.

### Completed Phases

- ✅ **Phase 1: List Management** - CRUD operations for TMDB lists
- ✅ **Phase 2: List Creation Wizard** - 4-step wizard with presets, filters, live preview
- ✅ **Phase 3: TMDB Caching** - TTL-based caching to respect rate limits
- ✅ **Phase 3.1: Config Tags** - Tag storage with create-if-missing pattern
- ✅ **Phase 4: Import Engine** - Radarr/Sonarr import with error handling
- ✅ **Phase 5: Manual Trigger UI** - Run Now button with status feedback
- ✅ **Phase 6: Job Framework** - Background processing, Jobs page, dashboard widget
- ✅ **Phase 6.1: Bug Fixes** - Tag override logic, logging, UI feedback
- ✅ **Phase 6.2: List Enhancements** - Top Rated presets, region filtering, larger limits
- ✅ **Phase 6.3: Test Coverage** - 493 tests
- ✅ **Phase 7: Scheduler System** - Cron-based automated list execution
- ✅ **Phase 8: API Consolidation** - Direct API calls replacing pyarr and tmdbv3api
- ✅ **Phase 9: Code Quality** - Refactoring and code cleanup
- ✅ **Phase 9.1: Config Deduplication** - 55% route reduction, 57% JS reduction
- ✅ **Phase 10: UI/UX Simplification** - Jinja macros, JS consolidation
- ✅ **Phase 10.1-10.5: UI Enhancements** - Bulk import API (8x faster), skeleton loading, activity-based timeout

### Planned Phases

- 🔮 **Phase 11: Security Hardening** - Flask/Docker security, input validation
- 🔮 **Phase 12: Release Readiness** - Final polish and v1.0 release

See [CLAUDE.md](CLAUDE.md) for comprehensive development documentation.

## Technology Stack

### Backend

- **Flask 3.0.0**: Web framework
- **SQLAlchemy 2.0.44**: ORM and database management
- **Flask-WTF**: CSRF protection and forms
- **cryptography 44.0.1**: Fernet encryption for API keys
- **requests 2.32.4**: Direct HTTP integration with Radarr/Sonarr/TMDB APIs
- **APScheduler 3.11.2**: Cron-based job scheduling
- **gunicorn 22.0.0**: Production WSGI server

### Frontend

- **Tailwind CSS**: Utility-first styling
- **Vanilla JavaScript**: Dynamic UI with shared utils.js library
- **Jinja2**: Server-side templating with macro library

### Database

- **SQLite**: Embedded database with WAL mode

## IMDB Integration Strategy

**Important**: Listarr uses TMDB as the primary data source with **legal IMDB ID mapping**.

- ✅ IMDB IDs retrieved via TMDB's `external_ids` endpoint
- ✅ No web scraping (respects IMDB Terms of Service)
- ✅ Fast, reliable, and officially supported
- ✅ IMDB links displayed in UI for user reference
- ❌ Does NOT use `cinemagoer` or any web scraping libraries

This approach ensures legal compliance while providing IMDB references for users.

## Security

- 🔐 **API keys encrypted at rest** (Fernet symmetric encryption)
- 🛡️ **CSRF protection** on all forms and AJAX requests
- 🔒 **Secrets excluded** from version control (.gitignore)
- 👤 **Single-user design** (no multi-tenancy)
- 🏠 **Self-hosted** for homelab environments
- 🔑 **Instance path isolation** for encryption key storage

**Important**: This application is designed for single-user, self-hosted deployments. Do not expose directly to the public internet without additional security measures (reverse proxy, authentication, firewall).

## Data Persistence

The `instance/` folder contains all runtime data:

- `listarr.db` - SQLite database
- `.fernet_key` - Encryption key (auto-generated by setup.py)

**Docker users**: The `instance/` folder is automatically persisted via a named volume in docker-compose.yml.

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Comprehensive developer documentation
  - Architecture patterns and design decisions
  - Implementation phases and roadmap
  - IMDB integration strategy
  - Security considerations
  - Testing guidelines and patterns
- **[CHANGELOG.md](docs/CHANGELOG.md)** - Detailed changelog of all changes

- **Project Philosophy**: Read-only stats + push actions (no full media management)
- **Design Pattern**: Application factory with blueprint-based routing

## Roadmap

| Phase                     | Status      | Description                                                 |
| ------------------------- | ----------- | ----------------------------------------------------------- |
| 1. List Management        | ✅ Complete | CRUD operations for TMDB lists through web interface        |
| 2. List Creation Wizard   | ✅ Complete | Multi-step wizard with presets, filters, and live preview   |
| 3. TMDB Caching           | ✅ Complete | Smart caching to respect API rate limits                    |
| 3.1 Config Tags           | ✅ Complete | Tag storage with create-if-missing pattern                  |
| 4. Import Engine          | ✅ Complete | Import system for Radarr/Sonarr with error handling         |
| 5. Manual Trigger UI      | ✅ Complete | Run lists on-demand from UI                                 |
| 6. Job Framework          | ✅ Complete | Background job processing with history tracking             |
| 6.1 Bug Fixes             | ✅ Complete | Bugs from manual testing resolved                           |
| 6.2 List Enhancements     | ✅ Complete | Top Rated presets, region filtering, larger limits          |
| 6.3 Test Coverage         | ✅ Complete | Enhanced coverage (493 tests)                               |
| 7. Scheduler System       | ✅ Complete | Cron-based automated list execution                         |
| 8. API Consolidation      | ✅ Complete | Direct API calls replacing pyarr and tmdbv3api              |
| 9. Code Quality           | ✅ Complete | Refactoring and code cleanup                                |
| 9.1 Config Deduplication  | ✅ Complete | 55% route reduction, 57% JS reduction                       |
| 10. UI/UX Simplification  | ✅ Complete | Jinja macros, JS consolidation                              |
| 10.1-10.5 UI Enhancements | ✅ Complete | Bulk import (8x faster), skeleton loading, timeout handling |
| 11. Security Hardening    | 🔮 Planned  | Flask/Docker security, input validation                     |
| 12. Release Readiness     | 🔮 Planned  | Final polish and v1.0 release                               |

## License

[Add your license here]

## Contributing

This is a personal project for homelab use. Contributions are welcome!

## Support

For issues or questions, please open an issue on GitHub.
