# FKT - Forgotten Knowledge Tracker
# Deployment Guide

## Quick Deploy with Docker

### Prerequisites
- Docker and Docker Compose installed

### Steps

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/FKT.git
cd FKT
```

2. **Set environment variables**
```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY
```

3. **Build and run**
```bash
docker-compose up -d
```

4. **Access the application**
- Dashboard: http://localhost:5000
- API: http://localhost:5000/api/v1/stats

### Stop the application
```bash
docker-compose down
```

## Deploy to Cloud Platforms

### Railway
1. Fork this repository
2. Connect to Railway
3. Set environment variables in Railway dashboard
4. Deploy automatically

### Render
1. Create new Web Service
2. Connect your repository
3. Build command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
4. Start command: `python -m tracker_app.web.app`

### Heroku
```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

## Production Checklist
- [ ] Set strong SECRET_KEY in .env
- [ ] Set DEBUG=False
- [ ] Use production WSGI server (gunicorn)
- [ ] Set up SSL/HTTPS
- [ ] Configure database backups
- [ ] Set up monitoring (Sentry, etc.)
