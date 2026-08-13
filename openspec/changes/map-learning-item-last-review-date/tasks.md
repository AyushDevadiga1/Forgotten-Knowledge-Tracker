## 1. Map the column

- [x] 1.1 `tracker_app/db/models.py` `LearningItem`: add `last_review_date = Column(DateTime, nullable=True)` (position after `next_review_date`)

## 2. Persist it on review

- [x] 2.1 `tracker_app/learning/learning_tracker.py` `record_review`: set `item_record.last_review_date = review_date` for both the sm2 and leitner branches (before `LearningRepository.record_review`)
- [x] 2.2 Keep `_row_to_dict` returning the field (now real data); simplify `getattr(row, 'last_review_date', None)` to direct attribute access

## 3. Regression coverage

- [x] 3.1 Test: after `record_review(..., algorithm='sm2')`, `get_item()` returns non-null `last_review_date` and a fresh session reload still sees it
- [x] 3.2 Test: same for `algorithm='leitner'`
- [x] 3.3 Run `venv\Scripts\python.exe -m pytest tracker_app/tests -q` and confirm full suite green
