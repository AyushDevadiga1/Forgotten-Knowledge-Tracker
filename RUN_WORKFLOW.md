# 🚀 Forgotten Knowledge Tracker (FKT) - Execution Workflow

This guide provides the complete process to set up and run the FKT application locally.

## 📋 Prerequisites
- **Python 3.11+**
- **Tesseract OCR**: Required for the screen scanning engine.
- **Webcam**: Optional, for attention tracking.

---

## 🛠️ Step 1: Environment Setup

The project uses a virtual environment to manage dependencies. Follow these steps to ensure you're using the correct environment.

### 1.1 Activate Virtual Environment
Open a terminal in the project root and run:
```powershell
# Windows
.\venv\Scripts\activate
```

### 1.2 Configuration
Create your environment file from the example:
```powershell
cp .env.example .env
```
*Note: You may need to edit `.env` to set your `TESSERACT_PATH` if it's not in your system PATH.*

---

## 📦 Step 2: Install Dependencies

Ensure all required packages are installed within the venv:
```powershell
python -m pip install -r requirements.txt
```
> [!NOTE]
> If you encounter issues with `mediapipe` or `sentence-transformers`, you can install them manually using `pip install sentence-transformers mediapipe`.

---

## 🏃 Step 3: Running the Application

To have a fully functional system, you only need to run a **single command**. `main.py` automatically orchestrates both the background tracker engine and the web dashboard simultaneously.

### 3.1 Start the Application
```powershell
python -m tracker_app.main
```
👉 **Access UI**: [http://localhost:5000](http://localhost:5000)

> [!IMPORTANT]
> The tracker will ask: `Enable facial attention tracking (webcam)? (y/n)`. 
> Type **'y'** and press Enter to enable the full learning intensity analytics.

---

## 📊 Step 4: Normal Workflow

1. **Work Normally**: Keep the Tracker running while you study or code.
2. **Auto-Discovery**: Concepts found on your screen will automatically appear in the dashboard.
3. **Review**: Periodically visit the dashboard to review "Due" items using the SM-2 spaced repetition algorithm.
4. **Manual Entry**: Use the "Add Item" page for specific facts you want to memorize.

---

## 🔍 Troubleshooting

- **Database Errors**: Ensure the `data/` directory exists. The app calls `setup_directories()` automatically on startup.
- **Model Warnings**: If you see Scikit-learn version warnings, the app will still function, but you can retrain models via `python -m tracker_app.scripts.train_models_from_logs`.
- **Tesseract Not Found**: Verify `TESSERACT_PATH` in `tracker_app/config.py` or `.env`.
