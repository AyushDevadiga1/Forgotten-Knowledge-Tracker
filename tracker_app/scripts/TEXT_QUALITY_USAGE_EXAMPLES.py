"""
Example OCR Integration with Text Quality Validation
Shows exactly how to use the text quality validator in your OCR pipeline
"""

from core.text_quality_validator import validate_and_clean_extraction, validate_batch_extraction

# ============================================================
# EXAMPLE 1: Single Text Extraction (Most Common)
# ============================================================

def extract_screen_content_with_validation(image, source="webcam", ocr_confidence=0.8):
    """
    Extract text from screen with quality validation
    
    Usage:
        result = extract_screen_content_with_validation(frame, source="webcam")
        if result['is_useful']:
            store_content(result)
    """
    # Your existing OCR extraction
    import pytesseract
    raw_text = pytesseract.image_to_string(image)
    
    # NEW: Validate and clean
    validation = validate_and_clean_extraction(
        raw_extracted_text=raw_text,
        ocr_confidence=ocr_confidence
    )
    
    # Check if worth storing
    if validation['status'] == 'ACCEPTED':  # quality >= 0.40
        print(f"✅ Good content: {validation['cleaned_text'][:50]}...")
        print(f"   Quality: {validation['quality_score']:.2f}")
        print(f"   Keywords: {validation['keywords']}")
        
        return {
            'status': 'VALID',
            'text': validation['cleaned_text'],
            'keywords': validation['keywords'],
            'quality_score': validation['quality_score'],
            'source': source,
            'is_ui_garbage': False
        }
    
    elif validation['status'] == 'REJECTED':  # quality < 0.10
        print(f"❌ Garbage content (rejected): {validation['message']}")
        print(f"   Quality: {validation['quality_score']:.2f}")
        
        # Log for analysis but don't store
        return {
            'status': 'REJECTED',
            'text': None,
            'quality_score': validation['quality_score'],
            'reason': validation['message'],
            'source': source
        }
    
    else:  # QUESTIONABLE: 0.10 <= quality < 0.40
        print(f"⚠️  Questionable content: {validation['message']}")
        print(f"   Quality: {validation['quality_score']:.2f}")
        
        # Store with warning flag
        return {
            'status': 'QUESTIONABLE',
            'text': validation['cleaned_text'],
            'keywords': validation['keywords'],
            'quality_score': validation['quality_score'],
            'source': source,
            'warning': True
        }

# ============================================================
# EXAMPLE 2: Batch Extraction (Multiple Screens)
# ============================================================

def batch_extract_from_screenshots(screenshots, ocr_confidence=0.8):
    """
    Extract from multiple screenshots and validate all
    
    Usage:
        results = batch_extract_from_screenshots([img1, img2, img3])
    """
    import pytesseract
    
    # Step 1: Extract from all
    extracted_texts = []
    for i, img in enumerate(screenshots):
        raw_text = pytesseract.image_to_string(img)
        extracted_texts.append({
            'text': raw_text,
            'confidence': ocr_confidence,
            'source': f'screenshot_{i}',
            'timestamp': time.time()
        })
    
    # Step 2: Validate all
    validated_results = validate_batch_extraction(extracted_texts)
    
    # Step 3: Return statistics
    print(f"Batch Results:")
    print(f"  Total extracted: {validated_results['total_inputs']}")
    print(f"  Accepted: {validated_results['accepted']}")
    print(f"  Rejected: {validated_results['rejected']}")
    print(f"  Questionable: {validated_results['questionable']}")
    print(f"  Avg quality: {validated_results['avg_quality']:.2f}")
    
    return validated_results

# ============================================================
# EXAMPLE 3: Real-Time Text Tracking (Stream Integration)
# ============================================================

class TextQualityTracker:
    """Track text quality metrics in real-time"""
    
    def __init__(self):
        self.total_extracted = 0
        self.total_accepted = 0
        self.total_rejected = 0
        self.quality_scores = []
    
    def process_extraction(self, raw_text, confidence=0.8):
        """Process single extraction, track metrics"""
        self.total_extracted += 1
        
        validation = validate_and_clean_extraction(raw_text, confidence)
        self.quality_scores.append(validation['quality_score'])
        
        if validation['status'] == 'ACCEPTED':
            self.total_accepted += 1
        elif validation['status'] == 'REJECTED':
            self.total_rejected += 1
        
        return validation
    
    def get_statistics(self):
        """Get real-time quality statistics"""
        if self.total_extracted == 0:
            return None
        
        return {
            'total_extractions': self.total_extracted,
            'accepted_count': self.total_accepted,
            'rejected_count': self.total_rejected,
            'acceptance_rate': self.total_accepted / self.total_extracted,
            'rejection_rate': self.total_rejected / self.total_extracted,
            'avg_quality_score': sum(self.quality_scores) / len(self.quality_scores),
            'max_quality': max(self.quality_scores) if self.quality_scores else 0,
            'min_quality': min(self.quality_scores) if self.quality_scores else 0,
        }
    
    def print_report(self):
        """Print human-readable report"""
        stats = self.get_statistics()
        if not stats:
            print("No data to report")
            return
        
        print("\n" + "="*60)
        print("TEXT QUALITY REPORT")
        print("="*60)
        print(f"Total Extractions:  {stats['total_extractions']}")
        print(f"Accepted:           {stats['accepted_count']} ({stats['acceptance_rate']*100:.1f}%)")
        print(f"Rejected:           {stats['rejected_count']} ({stats['rejection_rate']*100:.1f}%)")
        print(f"Avg Quality Score:  {stats['avg_quality_score']:.2f}/1.0")
        print(f"Range:              {stats['min_quality']:.2f} - {stats['max_quality']:.2f}")
        print("="*60 + "\n")

# ============================================================
# EXAMPLE 4: Database Storage with Quality Metadata
# ============================================================

def store_extracted_text_with_validation(db, raw_text, session_id, ocr_confidence=0.8):
    """
    Store text in database only if quality acceptable
    Includes quality metadata for future analysis
    """
    validation = validate_and_clean_extraction(raw_text, ocr_confidence)
    
    # Only store if quality >= 0.40
    if validation['quality_score'] >= 0.40:
        # Store main content
        content_id = db.insert_session_content(
            session_id=session_id,
            raw_text=raw_text,
            cleaned_text=validation['cleaned_text'],
            quality_score=validation['quality_score'],
            validation_status=validation['status'],
            is_coherent=validation['is_coherent']
        )
        
        # Store keywords
        for keyword in validation['keywords']:
            db.insert_keyword(
                content_id=content_id,
                keyword=keyword,
                quality_score=validation['quality_score'],
                source='ocr'
            )
        
        print(f"✅ Stored content (id={content_id}, quality={validation['quality_score']:.2f})")
        return content_id
    
    else:
        # Log rejection but don't store
        db.insert_rejected_extraction(
            session_id=session_id,
            raw_text=raw_text,
            quality_score=validation['quality_score'],
            reason=validation['message']
        )
        
        print(f"❌ Rejected: {validation['message']} (quality={validation['quality_score']:.2f})")
        return None

# ============================================================
# EXAMPLE 5: Quality-Based Filtering (Dashboard)
# ============================================================

def get_high_quality_keywords(db, min_quality=0.50):
    """Retrieve only high-quality keywords for dashboard"""
    keywords = db.query_keywords(f"quality_score >= {min_quality}")
    
    print(f"Retrieved {len(keywords)} high-quality keywords (quality >= {min_quality})")
    
    return keywords

def get_quality_analysis(db):
    """Analyze text quality distribution"""
    all_keywords = db.query_all_keywords()
    
    high_quality = [k for k in all_keywords if k['quality_score'] >= 0.60]
    acceptable = [k for k in all_keywords if 0.40 <= k['quality_score'] < 0.60]
    low_quality = [k for k in all_keywords if k['quality_score'] < 0.40]
    
    return {
        'high_quality': len(high_quality),
        'acceptable': len(acceptable),
        'low_quality': len(low_quality),
        'total': len(all_keywords),
        'avg_quality': sum(k['quality_score'] for k in all_keywords) / len(all_keywords) if all_keywords else 0
    }

# ============================================================
# EXAMPLE 6: Integration with Enhanced Tracker
# ============================================================

# In core/tracker_enhanced.py, modify the OCR extraction:

def extract_and_store_screen_content(self, image, session_id):
    """Enhanced extraction with quality validation"""
    from core.text_quality_validator import validate_and_clean_extraction
    
    # Get OCR result with confidence
    ocr_result = self._run_ocr(image)  # existing method
    raw_text = ocr_result['text']
    ocr_confidence = ocr_result.get('confidence', 0.8)
    
    # NEW: Validate quality before storing
    validation = validate_and_clean_extraction(
        raw_text=raw_text,
        ocr_confidence=ocr_confidence
    )
    
    # Store only if quality acceptable
    if validation['is_useful']:
        self.db.insert_extracted_text(
            session_id=session_id,
            text=validation['cleaned_text'],
            keywords=validation['keywords'],
            quality_score=validation['quality_score'],
            original_text=raw_text
        )
        
        # Update analytics
        self.analytics.track_text_extraction(
            quality=validation['quality_score'],
            status='ACCEPTED'
        )
    else:
        # Log rejected extraction
        self.analytics.track_text_extraction(
            quality=validation['quality_score'],
            status='REJECTED',
            reason=validation['message']
        )
    
    return validation

# ============================================================
# EXAMPLE 7: Testing & Validation
# ============================================================

def test_text_extraction_quality():
    """Test suite for extraction quality"""
    test_cases = [
        ("Python machine learning", 0.9, True, "Good technical content"),
        ("asdfjkl;qwerty", 0.5, False, "Keyboard mash gibberish"),
        ("loading... please wait", 0.8, False, "UI element"),
        ("Data science analytics", 0.85, True, "Valid keywords"),
        ("!@#$%^&*()", 0.9, False, "Only special characters"),
        ("a", 0.8, False, "Too short"),
    ]
    
    passed = 0
    failed = 0
    
    print("\nRunning Extraction Quality Tests...\n")
    
    for text, confidence, should_accept, description in test_cases:
        validation = validate_and_clean_extraction(text, confidence)
        is_accepted = validation['is_useful']
        
        if is_accepted == should_accept:
            print(f"✅ PASS: {description}")
            print(f"   Text: '{text}' → Quality: {validation['quality_score']:.2f}")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   Expected: {'ACCEPT' if should_accept else 'REJECT'}")
            print(f"   Got: {'ACCEPT' if is_accepted else 'REJECT'} (quality: {validation['quality_score']:.2f})")
            failed += 1
        print()
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(test_cases)}")
    return failed == 0

# ============================================================
# USAGE
# ============================================================

if __name__ == "__main__":
    # Test 1: Single extraction
    print("=" * 60)
    print("TEST 1: Single Extraction")
    print("=" * 60)
    result = extract_screen_content_with_validation(
        image=None,  # Your image
        ocr_confidence=0.85
    )
    
    # Test 2: Real-time tracking
    print("\nTEST 2: Real-Time Quality Tracking")
    print("=" * 60)
    tracker = TextQualityTracker()
    for i in range(10):
        # Simulate extractions
        tracker.process_extraction("Python machine learning", 0.8)
        tracker.process_extraction("asdfjkl;qwerty", 0.5)
    tracker.print_report()
    
    # Test 3: Validation tests
    print("\nTEST 3: Quality Validation Tests")
    print("=" * 60)
    test_text_extraction_quality()
