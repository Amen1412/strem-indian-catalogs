# Stremio Indian Movies Catalog Addon

A Stremio catalog addon that fetches Indian movies (Malayalam, Hindi, Tamil, Kannada) available on OTT platforms, sorted by release date in descending order.

## Features

- 🎬 Multiple language catalogs (Malayalam, Hindi, Tamil, Kannada)
- 🔄 Auto-refresh daily via Vercel cron jobs
- ⚙️ Configuration page to set TMDB API key and select languages
- 🚀 Deployable on Vercel

## Deployment to Vercel

1. **Install Vercel CLI** (if not already installed):
   ```bash
   npm i -g vercel
   ```

2. **Deploy to Vercel**:
   ```bash
   vercel
   ```

3. **Set Environment Variables** (optional, can also be set via `/configure` page):
   - `TMDB_API_KEY`: Your TMDB API key (get it from [TMDB Settings](https://www.themoviedb.org/settings/api))
   - `ENABLED_LANGUAGES`: Comma-separated list (e.g., `malayalam,hindi,tamil,kannada`)

4. **Configure the Addon**:
   - Visit `https://your-deployment.vercel.app/configure`
   - Enter your TMDB API key
   - Select the languages you want
   - Click "Save Configuration"

5. **Add to Stremio**:
   - Open Stremio
   - Go to Addons
   - Click "Add Addon"
   - Enter: `https://your-deployment.vercel.app/manifest.json`

## Endpoints

- `/manifest.json` - Stremio manifest
- `/catalog/movie/{language}.json` - Movie catalog for a specific language
- `/configure` - Configuration page
- `/refresh` - Manual refresh trigger
- `/api/cron/refresh` - Auto-refresh endpoint (called daily by Vercel cron)

## Auto-Refresh

The addon automatically refreshes once per day at midnight UTC via Vercel's cron jobs. You can also manually trigger a refresh by visiting `/refresh`.

## Configuration

Configuration can be done in two ways:

1. **Via Web Interface**: Visit `/configure` page
2. **Via Environment Variables**: Set `TMDB_API_KEY` and `ENABLED_LANGUAGES` in Vercel dashboard

## Supported Languages

- Malayalam (ml)
- Hindi (hi)
- Tamil (ta)
- Kannada (kn)

## Requirements

- Python 3.x
- TMDB API key
- Vercel account (for deployment)

## Local Development

For local development, you can still use the original Flask app (`app.py`):

```bash
pip install -r requirements.txt
python app.py
```

The app will run on `http://localhost:7000`


