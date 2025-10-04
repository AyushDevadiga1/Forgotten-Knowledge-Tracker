(venv) PS C:\Users\hp\Desktop\FKT\tracker_app> python test_audio.py
=== Audio Classifier Metrics ===
Accuracy: 0.4
         speech  music  silence
speech        2      3        1
music         1      4        1
silence       2      4        2

Classification Report:
              precision    recall  f1-score  support
music          0.400000  0.333333  0.363636      6.0
silence        0.363636  0.666667  0.470588      6.0
speech         0.500000  0.250000  0.333333      8.0
accuracy       0.400000  0.400000  0.400000      0.4
macro avg      0.421212  0.416667  0.389186     20.0
weighted avg   0.429091  0.400000  0.383601     20.0

=== Intent Classifier Metrics ===
Accuracy: 0.35
          idle  passive  studying
idle         1        4         3
passive      2        5         1
studying     0        3         1

Classification Report:
              precision    recall  f1-score  support
idle           0.333333  0.125000  0.181818     8.00
passive        0.416667  0.625000  0.500000     8.00
studying       0.200000  0.250000  0.222222     4.00
accuracy       0.350000  0.350000  0.350000     0.35
macro avg      0.316667  0.333333  0.301347    20.00
weighted avg   0.340000  0.350000  0.317172    20.00