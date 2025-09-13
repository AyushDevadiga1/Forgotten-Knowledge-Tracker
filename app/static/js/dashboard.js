// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('KnowledgeTracker Dashboard loaded');
    initializeEventListeners();
    loadInitialData();
});

function initializeEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.querySelector('.google-search-btn');
    
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
    }
    
    // Button event listeners
    const viewAudioBtn = document.querySelector('[onclick="loadAudioRecordings()"]');
    const viewScreenshotsBtn = document.querySelector('[onclick="loadScreenshots()"]');
    const analyzeBtn = document.querySelector('[onclick="analyzeKnowledge()"]');
    const refreshBtn = document.getElementById('refreshBtn');
    
    if (viewAudioBtn) viewAudioBtn.addEventListener('click', loadAudioRecordings);
    if (viewScreenshotsBtn) viewScreenshotsBtn.addEventListener('click', loadScreenshots);
    if (analyzeBtn) analyzeBtn.addEventListener('click', analyzeKnowledge);
    if (refreshBtn) refreshBtn.addEventListener('click', refreshData);
}

function loadInitialData() {
    // Load initial data if needed
    console.log('Loading initial data...');
}

// Search function
async function performSearch() {
    console.log('Performing search...');
    const query = document.getElementById('searchInput').value.trim();
    const resultsContainer = document.getElementById('searchResults');
    
    if (!query) {
        resultsContainer.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                Please enter a search term
            </div>
        `;
        return;
    }
    
    // Show loading
    resultsContainer.innerHTML = `
        <div class="text-center py-3">
            <div class="google-loading"></div>
            <p class="text-muted mt-2">Searching knowledge...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Search failed');
        
        const results = await response.json();
        displaySearchResults(results);
    } catch (error) {
        console.error('Search error:', error);
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                Search failed: ${error.message}
            </div>
        `;
    }
}

function displaySearchResults(results) {
    const container = document.getElementById('searchResults');
    
    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i>
                No results found. Try different keywords.
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map(result => `
        <div class="search-result google-card">
            <div class="google-card-body">
                <h6 class="mb-2">${escapeHtml(result.title || 'Unknown Title')}</h6>
                <p class="text-muted mb-2">${escapeHtml(result.snippet || 'No description available')}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="google-badge badge-${result.type || 'window'}">
                        ${result.type || 'unknown'}
                    </span>
                    <small class="text-muted">${formatDate(result.timestamp)}</small>
                </div>
            </div>
        </div>
    `).join('');
}

// Audio recordings
async function loadAudioRecordings() {
    console.log('Loading audio recordings...');
    const contentArea = document.getElementById('contentArea');
    
    contentArea.innerHTML = `
        <div class="google-card-header">
            <h6 class="mb-0"><i class="fas fa-microphone me-2"></i>Loading Audio Recordings...</h6>
        </div>
        <div class="google-card-body text-center">
            <div class="google-loading"></div>
        </div>
    `;
    
    try {
        const response = await fetch('/api/audio?limit=10');
        if (!response.ok) throw new Error('Failed to load audio');
        
        const recordings = await response.json();
        displayAudioRecordings(recordings);
    } catch (error) {
        console.error('Audio load error:', error);
        contentArea.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                Failed to load audio recordings: ${error.message}
            </div>
        `;
    }
}

function displayAudioRecordings(recordings) {
    const contentArea = document.getElementById('contentArea');
    
    if (!recordings || recordings.length === 0) {
        contentArea.innerHTML = `
            <div class="google-card">
                <div class="google-card-header">
                    <h6 class="mb-0"><i class="fas fa-microphone me-2"></i>Audio Recordings</h6>
                </div>
                <div class="google-card-body">
                    <p class="text-muted text-center">No audio recordings found</p>
                </div>
            </div>
        `;
        return;
    }
    
    contentArea.innerHTML = `
        <div class="google-card">
            <div class="google-card-header">
                <h6 class="mb-0"><i class="fas fa-microphone me-2"></i>Audio Recordings (${recordings.length})</h6>
            </div>
            <div class="google-card-body">
                ${recordings.map(rec => `
                    <div class="mb-3 p-3 border rounded">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <strong class="text-truncate">${escapeHtml(rec.file_path || 'Unknown file')}</strong>
                            <span class="badge bg-info">${rec.duration || 0}s</span>
                        </div>
                        <div class="text-muted mb-2">
                            <small>${formatDate(rec.timestamp)}</small>
                        </div>
                        <p class="mb-1">${escapeHtml(rec.transcribed_text ? rec.transcribed_text.substring(0, 150) + '...' : 'No transcription available')}</p>
                        ${rec.confidence ? `<small class="text-muted">Confidence: ${(rec.confidence * 100).toFixed(1)}%</small>` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Screenshots
async function loadScreenshots() {
    console.log('Loading screenshots...');
    const contentArea = document.getElementById('contentArea');
    
    contentArea.innerHTML = `
        <div class="google-card-header">
            <h6 class="mb-0"><i class="fas fa-camera me-2"></i>Loading Screenshots...</h6>
        </div>
        <div class="google-card-body text-center">
            <div class="google-loading"></div>
        </div>
    `;
    
    try {
        const response = await fetch('/api/screenshots?limit=10');
        if (!response.ok) throw new Error('Failed to load screenshots');
        
        const screenshots = await response.json();
        displayScreenshots(screenshots);
    } catch (error) {
        console.error('Screenshots load error:', error);
        contentArea.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-circle"></i>
                Failed to load screenshots: ${error.message}
            </div>
        `;
    }
}

function displayScreenshots(screenshots) {
    const contentArea = document.getElementById('contentArea');
    
    if (!screenshots || screenshots.length === 0) {
        contentArea.innerHTML = `
            <div class="google-card">
                <div class="google-card-header">
                    <h6 class="mb-0"><i class="fas fa-camera me-2"></i>Screenshots</h6>
                </div>
                <div class="google-card-body">
                    <p class="text-muted text-center">No screenshots found</p>
                </div>
            </div>
        `;
        return;
    }
    
    contentArea.innerHTML = `
        <div class="google-card">
            <div class="google-card-header">
                <h6 class="mb-0"><i class="fas fa-camera me-2"></i>Screenshots (${screenshots.length})</h6>
            </div>
            <div class="google-card-body">
                ${screenshots.map(shot => `
                    <div class="mb-3 p-3 border rounded">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <strong class="text-truncate">${escapeHtml(shot.window_title || 'Unknown window')}</strong>
                            <span class="badge bg-secondary">${shot.app_name || 'Unknown app'}</span>
                        </div>
                        <div class="text-muted mb-2">
                            <small>${formatDate(shot.timestamp)}</small>
                        </div>
                        <p class="mb-1">${escapeHtml(shot.extracted_text ? shot.extracted_text.substring(0, 150) + '...' : 'No text extracted')}</p>
                        ${shot.confidence ? `<small class="text-muted">Confidence: ${(shot.confidence * 100).toFixed(1)}%</small>` : ''}
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Analyze knowledge
function analyzeKnowledge() {
    console.log('Analyzing knowledge patterns...');
    const contentArea = document.getElementById('contentArea');
    
    contentArea.innerHTML = `
        <div class="google-card">
            <div class="google-card-header">
                <h6 class="mb-0"><i class="fas fa-brain me-2"></i>Knowledge Analysis</h6>
            </div>
            <div class="google-card-body">
                <div class="text-center py-4">
                    <i class="fas fa-chart-line text-primary" style="font-size: 48px;"></i>
                    <h5 class="mt-3">Knowledge Patterns</h5>
                    <p class="text-muted">Analyzing your learning patterns and memory retention...</p>
                    
                    <div class="row mt-4">
                        <div class="col-md-6">
                            <div class="google-card">
                                <div class="google-card-body text-center">
                                    <i class="fas fa-clock text-info mb-2"></i>
                                    <h5>78%</h5>
                                    <p class="text-muted mb-0">Retention Rate</p>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="google-card">
                                <div class="google-card-body text-center">
                                    <i class="fas fa-trending-up text-success mb-2"></i>
                                    <h5>+12%</h5>
                                    <p class="text-muted mb-0">This Week</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <button class="btn google-btn-primary mt-4">
                        <i class="fas fa-download me-2"></i>Export Report
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Refresh data
async function refreshData() {
    console.log('Refreshing data...');
    const btn = document.getElementById('refreshBtn');
    const icon = btn.querySelector('i');
    
    // Start loading animation
    btn.disabled = true;
    icon.className = 'fas fa-spinner fa-spin';
    
    try {
        // Reload the page after a short delay
        setTimeout(() => {
            window.location.reload();
        }, 1000);
    } catch (error) {
        console.error('Refresh error:', error);
        btn.disabled = false;
        icon.className = 'fas fa-sync-alt';
    }
}

// Utility functions
function formatDate(timestamp) {
    if (!timestamp) return 'Unknown date';
    try {
        return new Date(timestamp).toLocaleDateString() + ' ' + 
               new Date(timestamp).toLocaleTimeString();
    } catch (e) {
        return timestamp;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// Make functions globally available
window.performSearch = performSearch;
window.loadAudioRecordings = loadAudioRecordings;
window.loadScreenshots = loadScreenshots;
window.analyzeKnowledge = analyzeKnowledge;
window.refreshData = refreshData;