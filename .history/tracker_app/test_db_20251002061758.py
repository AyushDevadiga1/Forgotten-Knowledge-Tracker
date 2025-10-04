def log_multi_modal(window, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence):
    """
    Log multi-modal data including OCR keywords with scores and occurrences.

    ocr_keywords: dict of {keyword: {"score": float, "count": int}}
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ensure native Python types
    attention_score = int(attention_score)
    interaction_rate = int(interaction_rate)
    intent_confidence = float(intent_confidence)

    # Prepare OCR data for storage
    ocr_data_to_store = {}
    for kw, info in ocr_keywords.items():
        if isinstance(info, dict):
            ocr_data_to_store[kw] = {
                "score": float(info.get("score", 0.5)),
                "count": int(info.get("count", 1))
            }
        else:
            # fallback for older format (just score)
            ocr_data_to_store[kw] = {"score": float(info), "count": 1}

    c.execute('''
        INSERT INTO multi_modal_logs
        (timestamp, window_title, ocr_keywords, audio_label, attention_score, interaction_rate, intent_label, intent_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        window,
        json.dumps(ocr_data_to_store),  # store as dict with scores + counts
        audio_label,
        attention_score,
        interaction_rate,
        intent_label,
        intent_confidence
    ))

    conn.commit()
    conn.close()
