(venv) PS C:\Users\hp\Desktop\FKT\tracker_app> python test_audio.py
Audio classifier not found. Please train one or use default labels.
Traceback (most recent call last):
  File "C:\Users\hp\Desktop\FKT\tracker_app\test_audio.py", line 9, in <module>
    from core.intent_module import predict_intent  # assumes this function works with feature dict
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\hp\Desktop\FKT\tracker_app\core\intent_module.py", line 7, in <module>
    from core.intent_module import predict_intent
ImportError: cannot import name 'predict_intent' from partially initialized module 'core.intent_module' (most likely due to a circular import) (C:\Users\hp\Desktop\FKT\tracker_app\core\intent_module.py)