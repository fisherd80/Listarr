# Listarr

A single-user, self-hosted Flask application for discovering content via TMDB (The Movie Database) and importing curated lists into Radarr/Sonarr media servers.

## Features

- 🎬 **TMDB Integration**: Discover movies and TV shows (Trending, Popular, Discover with filters)
- 🔗 **IMDB ID Mapping**: Legal IMDB ID retrieval via TMDB (no web scraping)
- 🎯 **Radarr/Sonarr Import**: Fully configured import settings with quality profiles and root folders
- 📤 **Queue-based Imports**: Push content to media servers (planned)
- 📊 **Dashboard Stats**: Read-only summary from Radarr/Sonarr with cached stats, "Added by Listarr" counter, and recent jobs
- 🔒 **Encrypted Storage**: API keys encrypted at rest with Fernet encryption
- ⏰ **Scheduled Execution**: Cron-based list automation (planned)
- 💾 **SQLite Database**: Persistent storage with no external database required
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

## Project Structure

```
listarr/
├── listarr/              # Main application package
│   ├── forms/           # WTForms form definitions
│   ├── models/          # SQLAlchemy database models
│   ├── routes/          # Blueprint-based routes
│   ├── services/        # Business logic layer
│   │   ├── tmdb_service.py      # TMDB API integration (tmdbv3api)
│   │   ├── radarr_service.py    # Radarr API integration (pyarr)
│   │   ├── sonarr_service.py    # Sonarr API integration (pyarr)
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

**~70% Complete** - Phase 1 and Phase 2 complete. Dashboard with live stats, caching, and recent jobs fully implemented. Working on list generation and job execution.

### ✅ Phase 1: Complete (Config & API Integration)

- ✅ Flask application factory with SQLAlchemy
- ✅ Fernet encryption for API keys with instance_path support
- ✅ Database models for all core entities (ServiceConfig, MediaImportSettings, List, Job, etc.)
- ✅ **Settings page**: TMDB API key management with test connection
- ✅ **Config page**: Radarr/Sonarr URL and API key configuration
- ✅ **Import Settings**: Fully functional dropdowns for:
  - Quality Profiles (fetched from Radarr/Sonarr)
  - Root Folders (fetched from Radarr/Sonarr)
  - Monitoring, Search on Add, Season Folder (Sonarr only)
  - Save/load functionality with database persistence
  - Client and server-side validation
  - Flag-based caching to prevent redundant API calls
- ✅ **TMDB Service**: Complete integration using tmdbv3api library
  - Trending movies/TV (day/week)
  - Popular movies/TV
  - Discover with filters (genre, year, rating, language)
  - Movie/TV details retrieval
  - **IMDB ID mapping** via TMDB external_ids (legal, no web scraping)
- ✅ **PyArr Integration**: Full Radarr/Sonarr API client integration
- ✅ **CSRF Protection**: All forms and AJAX requests protected
- ✅ **Docker Configuration**: Production-ready containerization
- ✅ **Comprehensive Documentation**: CLAUDE.md with architecture and patterns

### ✅ Phase 2: Complete (Dashboard & Stats)

- ✅ Dashboard with live stats from Radarr/Sonarr
  - System status, media counts, missing counts
  - **"Added by Listarr"** counter (total items added from completed jobs)
  - Manual and auto-refresh functionality (5-minute interval)
  - Status indicators (online/offline/not configured)
  - Recent jobs table with execution history (last 5 jobs)
  - **In-memory caching** for fast page loads (calculated at startup)
  - Cache refresh on-demand via `?refresh=true` parameter
- 🚧 List generation wizard UI (In Progress)
  - Multi-step form for creating lists
  - Preview with pagination
  - Integration with TMDB service
  - IMDB link display

### 📋 Phase 3: Planned (Job Execution & Monitoring)

- Job execution engine (background task runner)
- Import queue logic with conflict handling
- Jobs page for activity monitoring
- Inline logs with retry/cancel support

### 🔮 Phase 4: Planned (Advanced Features)

- Scheduling system with cron integration
- Cache management for cached lists (TTL-based)
- Global blacklist system
- Tag functionality for import settings

See [CLAUDE.md](CLAUDE.md) for comprehensive development documentation.

## Technology Stack

### Backend

- **Flask 3.0.0**: Web framework
- **SQLAlchemy 2.0.23**: ORM and database management
- **Flask-WTF**: CSRF protection and forms
- **cryptography 41.0.7**: Fernet encryption for API keys
- **tmdbv3api 1.9.0**: TMDB API client
- **pyarr >=5.0.0**: Radarr/Sonarr API client
- **gunicorn 21.2.0**: Production WSGI server

### Frontend

- **Tailwind CSS**: Utility-first styling
- **Vanilla JavaScript**: Dynamic UI interactions
- **Jinja2**: Server-side templating

### Database

- **SQLite**: Embedded database for simplicity

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

- **[CLAUDE.md](docs/CLAUDE.md)** - Comprehensive developer documentation
  - Architecture patterns and design decisions
  - Implementation phases and roadmap
  - IMDB integration strategy
  - Security considerations
  - Testing guidelines and patterns
- **[CHANGELOG.md](docs/CHANGELOG.md)** - Detailed changelog of all changes
- **[DASHBOARD_FEATURES.md](docs/DASHBOARD_FEATURES.md)** - Comprehensive dashboard features documentation
- **Test Documentation**:
  - [TEST_REVIEW.md](docs/TEST_REVIEW.md) - Comprehensive test suite review
  - [TEST_STATUS.md](docs/TEST_STATUS.md) - Current test suite status (363 tests, 100% passing)
  - [CONFIG_ROUTES_TEST_REVIEW.md](docs/CONFIG_ROUTES_TEST_REVIEW.md) - Config routes test analysis
  - [CONFIG_ROUTES_TEST_IMPLEMENTATION.md](docs/CONFIG_ROUTES_TEST_IMPLEMENTATION.md) - Test implementation summary
- **Project Philosophy**: Read-only stats + push actions (no full media management)
- **Design Pattern**: Application factory with blueprint-based routing

## Roadmap

| Phase   | Status      | Description                                                |
| ------- | ----------- | ---------------------------------------------------------- |
| Phase 1 | ✅ Complete | API integration (TMDB, Radarr, Sonarr) and Import Settings |
| Phase 2 | ✅ Complete | Dashboard stats with caching, "Added by Listarr", and recent jobs |
| Phase 3 | 📋 Planned  | List generation UI, job execution engine, and monitoring   |
| Phase 4 | 🔮 Planned  | Scheduling, caching, and advanced features                 |

## License

[Add your license here]

## Contributing

This is a personal project for homelab use. Contributions are welcome!

## Support

For issues or questions, please open an issue on GitHub.
