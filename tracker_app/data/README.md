# Data Directory

This directory contains runtime data for the Forgotten Knowledge Tracker.

## Contents

All SQLite databases and generated files are stored here:

- `sessions.db` - Activity tracking sessions
- `learning_tracker.db` - User flashcards and SM-2 scheduler data
- `tracking_concepts.db` - Discovered concepts from automated tracker
- `intent_validation.db` - Intent prediction accuracy logs
- `tracking_analytics.db` - Usage analytics and metrics
- `knowledge_graph.pkl` - NetworkX graph of concept relationships

## Important Notes

⚠️ **This directory is auto-created** on first run. Do not manually create database files.

⚠️ **Gitignored** - Database files are excluded from version control to keep your learning data private.

⚠️ **Backup** - To backup your learning data, simply copy all `.db` files to a safe location.

## Database Schema

For schema details, see [`tracker_app/docs/DATABASE.md`](../docs/DATABASE.md)
