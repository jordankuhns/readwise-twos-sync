# Readwise to Twos Sync

A Python application that automatically syncs your Readwise highlights to your Twos app. Perfect for keeping your reading insights organized and accessible in your daily workflow.

## Features

- 🌐 **Web App**: Simple web interface for one-click syncing
- 🔄 Automatic syncing of new Readwise highlights to Twos
- 📅 Configurable sync intervals and lookback periods
- 🛡️ Robust error handling and logging
- 🔧 Easy configuration via environment variables or .env files
- 📦 Installable as a Python package
- 🤖 GitHub Actions ready for automated syncing
- ☁️ Deploy to Vercel, Heroku, or any cloud platform

## Installation

### From PyPI (when published)
```bash
pip install readwise-twos-sync
```

### From Source
```bash
git clone https://github.com/yourusername/readwise-twos-sync.git
cd readwise-twos-sync
pip install -e .
```

## Configuration

You'll need API tokens from both services:

### Readwise API Token
1. Go to [Readwise.io](https://readwise.io/access_token)
2. Copy your access token

### Twos API Credentials
1. Open your Twos app
2. Go to Settings → API
3. Copy your User ID and API Token

### Environment Variables

Create a `.env` file in your project directory:

```env
READWISE_TOKEN=your_readwise_token_here
TWOS_USER_ID=your_twos_user_id_here
TWOS_TOKEN=your_twos_api_token_here

# Optional settings
SYNC_DAYS_BACK=7
LAST_SYNC_FILE=last_sync.json
```

## Usage

### Web Application

The easiest way to use this tool is through the web interface:

1. **Deploy to Vercel** (recommended):
   - Fork this repository
   - Connect it to your Vercel account
   - Deploy with one click
   - Visit your deployed URL

2. **Or run locally**:
   ```bash
   pip install -r requirements-web.txt
   python app.py
   ```
   Then visit `http://localhost:5000`

3. **Enter your API credentials** in the web form and click "Start Sync"

### Command Line
```bash
# Basic sync
readwise-twos-sync

# With custom .env file
readwise-twos-sync --env-file /path/to/.env

# With verbose logging
readwise-twos-sync --verbose

# Show help
readwise-twos-sync --help
```

### Python API
```python
from readwise_twos_sync import SyncManager, Config

# Use default configuration
sync_manager = SyncManager()
sync_manager.sync()

# Or with custom config
config = Config(env_file="/path/to/.env")
sync_manager = SyncManager(config)
sync_manager.sync()
```

## GitHub Actions Setup

Create `.github/workflows/sync.yml`:

```yaml
name: Sync Readwise to Twos

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install readwise-twos-sync
    
    - name: Run sync
      env:
        READWISE_TOKEN: ${{ secrets.READWISE_TOKEN }}
        TWOS_USER_ID: ${{ secrets.TWOS_USER_ID }}
        TWOS_TOKEN: ${{ secrets.TWOS_TOKEN }}
      run: readwise-twos-sync
```

Don't forget to add your API tokens as GitHub repository secrets!

## Web App Deployment

### Deploy to Vercel (Recommended)

1. Fork this repository to your GitHub account
2. Go to [vercel.com](https://vercel.com) and sign up/login
3. Click "New Project" and import your forked repository
4. Deploy with default settings
5. Your app will be live at `https://your-project-name.vercel.app`

### Deploy to Heroku

1. Install the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```
3. Deploy:
   ```bash
   git push heroku main
   ```
4. Your app will be live at `https://your-app-name.herokuapp.com`

### Deploy to Railway

1. Go to [railway.app](https://railway.app) and sign up/login
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your forked repository
4. Railway will automatically detect and deploy your Flask app

### Local Development

```bash
# Install web dependencies
pip install -r requirements-web.txt

# Run the web app
python app.py

# Visit http://localhost:5000
```

## Development

### Setup
```bash
git clone https://github.com/yourusername/readwise-twos-sync.git
cd readwise-twos-sync
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black readwise_twos_sync/
flake8 readwise_twos_sync/
```

## Configuration Options

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `READWISE_TOKEN` | Your Readwise API token | Required |
| `TWOS_USER_ID` | Your Twos user ID | Required |
| `TWOS_TOKEN` | Your Twos API token | Required |
| `SYNC_DAYS_BACK` | Days to look back for initial sync | 7 |
| `LAST_SYNC_FILE` | Path to sync timestamp file | `last_sync.json` |

## How It Works

1. **Fetch Books**: Retrieves your book library from Readwise
2. **Get New Highlights**: Finds highlights updated since last sync
3. **Format & Post**: Formats highlights as "Book Title, Author: Highlight text" and posts to Twos
4. **Track Progress**: Saves sync timestamp for next run

## Troubleshooting

### Common Issues

**Missing API tokens**
```
ValueError: Missing required environment variables: READWISE_TOKEN
```
Make sure all required environment variables are set in your `.env` file.

**Network errors**
The app includes automatic retry logic, but check your internet connection and API token validity.

**No highlights syncing**
Check that your Readwise account has recent highlights and that the sync timestamp file isn't corrupted.

### Logging

Enable verbose logging to see detailed information:
```bash
readwise-twos-sync --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- 🐛 [Report bugs](https://github.com/yourusername/readwise-twos-sync/issues)
- 💡 [Request features](https://github.com/yourusername/readwise-twos-sync/issues)
- 📖 [Documentation](https://github.com/yourusername/readwise-twos-sync)
Sync between Readwise API and Twos API
