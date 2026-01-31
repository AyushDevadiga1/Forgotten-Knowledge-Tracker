# Web Dashboard

Flask-based web interface for the Forgotten Knowledge Tracker.

## Files

- `app.py` - Main Flask application
- `templates/` - Jinja2 HTML templates
- `static/` - CSS, JavaScript, images (if needed)

## Running the Dashboard

```bash
python -m tracker_app.web.app
# or
cd tracker_app/web
python app.py
```

Access at: http://localhost:5000

## Routes

- `/` - Dashboard home
- `/add` - Add new flashcard
- `/review` - Start review session
- `/review/<item_id>` - Review specific item
- `/stats` - JSON API for statistics

##Features

- SM-2 spaced repetition scheduling
- Discovered concepts from automated tracker
- Premium Tailwind CSS design
- Mobile-responsive layout
