// Word Column Mapper Frontend JavaScript
class SearchEngineDashboard {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.queryHistory = [];
        this.performanceData = [];
        this.chart = null;
        
        this.initializeEventListeners();
        this.checkApiStatus();
        this.initializeChart();
        this.loadSystemStatus();
        
        // Auto-refresh system status every 30 seconds
        setInterval(() => this.loadSystemStatus(), 30000);
    }

    initializeEventListeners() {
        // Search functionality
        document.getElementById('search-btn').addEventListener('click', () => this.performSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });
        document.getElementById('clear-btn').addEventListener('click', () => this.clearResults());

        // Quick test buttons
        document.querySelectorAll('.quick-test-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                document.getElementById('search-input').value = query;
                this.performSearch();
            });
        });

        // Reverse lookup
        document.getElementById('reverse-btn').addEventListener('click', () => this.performReverseLookup());
        document.getElementById('reverse-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performReverseLookup();
        });

        // Set operations
        document.getElementById('set-operation-btn').addEventListener('click', () => this.performSetOperation());

        // Recreate mappings
        document.getElementById('recreate-mappings-btn').addEventListener('click', () => this.recreateMappings());

        // Natural language query
        document.getElementById('nl-query-btn').addEventListener('click', () => this.processNaturalLanguageQuery());
        document.getElementById('clear-nl-btn').addEventListener('click', () => this.clearNaturalLanguageQuery());
    }

    async checkApiStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/health`);
            const data = await response.json();
            
            const statusElement = document.getElementById('api-status');
            if (data.status === 'healthy') {
                statusElement.textContent = 'Healthy';
                statusElement.className = 'text-success';
            } else {
                statusElement.textContent = 'Unhealthy';
                statusElement.className = 'text-danger';
            }
        } catch (error) {
            document.getElementById('api-status').textContent = 'Offline';
            document.getElementById('api-status').className = 'text-danger';
        }
    }

    async performSearch() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;

        const includeSuggestions = document.getElementById('include-suggestions').checked;
        
        this.showLoading(true);
        
        try {
            const startTime = performance.now();
            const response = await fetch(`${this.apiBaseUrl}/search/${encodeURIComponent(query)}?include_suggestions=${includeSuggestions}`);
            const endTime = performance.now();
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displaySearchResults(data, endTime - startTime);
            this.addToQueryHistory(query, data, endTime - startTime);
            this.updatePerformanceMetrics(data);
            
        } catch (error) {
            this.displayError('Search failed: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    displaySearchResults(data, clientTime) {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = '';

        if (data.total_results === 0) {
            resultsContainer.innerHTML = `
                <div class="search-result no-match">
                    <h6><i class="fas fa-times-circle text-danger"></i> No Results Found</h6>
                    <p><strong>Query:</strong> "${data.query}"</p>
                    <p><strong>Execution Time:</strong> ${data.execution_time_ms.toFixed(2)}ms (client: ${clientTime.toFixed(2)}ms)</p>
                    ${data.suggestions && data.suggestions.length > 0 ? 
                        `<p><strong>Suggestions:</strong> ${data.suggestions.join(', ')}</p>` : ''}
                </div>
            `;
            return;
        }

        const resultClass = data.exact_match ? 'exact-match' : 'fuzzy-match';
        
        let html = `
            <div class="search-result ${resultClass}">
                <h6>
                    <i class="fas fa-${data.exact_match ? 'check-circle text-success' : 'search text-warning'}"></i>
                    Search Results for "${data.query}"
                </h6>
                <p><strong>Execution Time:</strong> ${data.execution_time_ms.toFixed(2)}ms (client: ${clientTime.toFixed(2)}ms)</p>
                <p><strong>Total Results:</strong> ${data.total_results}</p>
                <p><strong>Match Type:</strong> ${data.exact_match ? 'Exact Match' : 'Fuzzy Match'}</p>
        `;

        data.results.forEach((result, index) => {
            const confidencePercent = (result.confidence * 100).toFixed(1);
            html += `
                <div class="mt-3 p-3 border rounded">
                    <h6>Result ${index + 1}: ${result.word}</h6>
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Confidence:</strong> ${confidencePercent}%</p>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
                            </div>
                            <p><strong>Match Type:</strong> ${result.match_type}</p>
                            ${result.edit_distance !== null ? `<p><strong>Edit Distance:</strong> ${result.edit_distance}</p>` : ''}
                            ${result.changes ? `<p><strong>Changes:</strong> ${result.changes}</p>` : ''}
                        </div>
                        <div class="col-md-6">
                            <p><strong>Columns (${result.columns.length}):</strong></p>
                            <div class="column-list">${result.columns.join(', ')}</div>
                        </div>
                    </div>
                    ${result.changes ? `
                        <div class="typo-analysis">
                            <strong>Typo Analysis:</strong><br>
                            Input: "${data.query}" → Matched: "${result.word}"<br>
                            ${result.changes}
                        </div>
                    ` : ''}
                </div>
            `;
        });

        html += `
            <div class="mt-3 p-3 bg-light rounded">
                <h6><i class="fas fa-list"></i> All Unique Columns (${data.total_unique_columns.length})</h6>
                <div class="column-list">${data.total_unique_columns.join(', ')}</div>
                <div class="mt-3">
                    <button class="btn btn-info btn-sm" type="button" id="get-table-names-btn" data-columns='${JSON.stringify(data.total_unique_columns)}'>
                        <i class="fas fa-table"></i> Get Table Names
                    </button>
                </div>
            </div>
        </div>`;

        resultsContainer.innerHTML = html;
        
        // Add event listener for the new button
        document.getElementById('get-table-names-btn').addEventListener('click', (e) => {
            const columnIds = JSON.parse(e.target.getAttribute('data-columns'));
            this.getTableNames(columnIds);
        });
    }

    async performReverseLookup() {
        const columnId = document.getElementById('reverse-input').value.trim();
        if (!columnId) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/reverse/${encodeURIComponent(columnId)}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    document.getElementById('reverse-results').innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle"></i> Column "${columnId}" not found
                        </div>
                    `;
                    return;
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displayReverseResults(data);
            
        } catch (error) {
            document.getElementById('reverse-results').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i> Reverse lookup failed: ${error.message}
                </div>
            `;
        }
    }

    displayReverseResults(data) {
        const html = `
            <div class="alert alert-success">
                <h6><i class="fas fa-check-circle"></i> Column "${data.column_id}"</h6>
                <p><strong>Execution Time:</strong> ${data.execution_time_ms.toFixed(2)}ms</p>
                <p><strong>Total Mappings:</strong> ${data.total_mappings}</p>
                <p><strong>Words:</strong></p>
                <div class="column-list">${data.words.join(', ')}</div>
            </div>
        `;
        document.getElementById('reverse-results').innerHTML = html;
    }

    async performSetOperation() {
        const words = document.getElementById('set-words').value.trim();
        const operation = document.getElementById('operation-type').value;
        
        if (!words) return;

        const wordList = words.split(',').map(w => w.trim()).filter(w => w);
        if (wordList.length < 2) {
            alert('Please enter at least 2 words for set operations');
            return;
        }

        try {
            const queryParams = wordList.map(word => `words=${encodeURIComponent(word)}`).join('&');
            const response = await fetch(`${this.apiBaseUrl}/${operation}?${queryParams}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.displaySetOperationResults(data);
            
        } catch (error) {
            document.getElementById('set-operation-results').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i> Set operation failed: ${error.message}
                </div>
            `;
        }
    }

    displaySetOperationResults(data) {
        const operationName = data.operation === 'AND' ? 'Intersection' : 'Union';
        const columns = data.intersection_columns || data.union_columns || [];
        const count = data.total_common_columns || data.total_unique_columns || 0;
        
        const html = `
            <div class="alert alert-info">
                <h6><i class="fas fa-sitemap"></i> ${operationName} Results</h6>
                <p><strong>Query Words:</strong> ${data.query_words.join(', ')}</p>
                <p><strong>Execution Time:</strong> ${data.execution_time_ms.toFixed(2)}ms</p>
                <p><strong>Total ${operationName === 'Intersection' ? 'Common' : 'Unique'} Columns:</strong> ${count}</p>
                ${columns.length > 0 ? `
                    <p><strong>Columns:</strong></p>
                    <div class="column-list">${columns.join(', ')}</div>
                ` : '<p class="text-muted">No columns found</p>'}
                ${data.note ? `<p class="text-muted"><em>${data.note}</em></p>` : ''}
            </div>
        `;
        document.getElementById('set-operation-results').innerHTML = html;
    }

    addToQueryHistory(query, data, clientTime) {
        const historyItem = {
            query,
            timestamp: new Date().toLocaleTimeString(),
            executionTime: data.execution_time_ms,
            clientTime: clientTime,
            totalResults: data.total_results,
            exactMatch: data.exact_match
        };
        
        this.queryHistory.unshift(historyItem);
        if (this.queryHistory.length > 20) {
            this.queryHistory = this.queryHistory.slice(0, 20);
        }
        
        this.updateQueryHistoryDisplay();
    }

    updateQueryHistoryDisplay() {
        const historyContainer = document.getElementById('query-history');
        
        if (this.queryHistory.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted">No queries yet</p>';
            return;
        }
        
        const html = this.queryHistory.map(item => `
            <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                <div>
                    <strong>${item.query}</strong><br>
                    <small class="text-muted">${item.timestamp}</small>
                </div>
                <div class="text-end">
                    <span class="badge bg-${item.exactMatch ? 'success' : 'warning'}">${item.exactMatch ? 'Exact' : 'Fuzzy'}</span><br>
                    <small class="text-muted">${item.executionTime.toFixed(1)}ms</small>
                </div>
            </div>
        `).join('');
        
        historyContainer.innerHTML = html;
    }

    updatePerformanceMetrics(data) {
        this.performanceData.push({
            timestamp: new Date(),
            executionTime: data.execution_time_ms,
            totalResults: data.total_results,
            exactMatch: data.exact_match
        });
        
        if (this.performanceData.length > 50) {
            this.performanceData = this.performanceData.slice(-50);
        }
        
        this.updatePerformanceDisplay();
        this.updateChart();
    }

    updatePerformanceDisplay() {
        if (this.performanceData.length === 0) return;
        
        const avgResponseTime = this.performanceData.reduce((sum, item) => sum + item.executionTime, 0) / this.performanceData.length;
        const totalQueries = this.performanceData.length;
        const successfulQueries = this.performanceData.filter(item => item.totalResults > 0).length;
        const successRate = (successfulQueries / totalQueries) * 100;
        
        document.getElementById('avg-response-time').textContent = avgResponseTime.toFixed(2);
        document.getElementById('total-queries').textContent = totalQueries;
        document.getElementById('success-rate').textContent = successRate.toFixed(1) + '%';
        document.getElementById('cache-hit-rate').textContent = '0%'; // Will be implemented with caching
    }

    initializeChart() {
        const ctx = document.getElementById('performance-chart').getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Response Time (ms)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Query Number'
                        }
                    }
                }
            }
        });
    }

    updateChart() {
        if (!this.chart) return;
        
        const labels = this.performanceData.map((_, index) => index + 1);
        const data = this.performanceData.map(item => item.executionTime);
        
        this.chart.data.labels = labels;
        this.chart.data.datasets[0].data = data;
        this.chart.update();
    }

    async loadSystemStatus() {
        try {
            const [healthResponse, metricsResponse] = await Promise.all([
                fetch(`${this.apiBaseUrl}/health`),
                fetch(`${this.apiBaseUrl}/metrics`)
            ]);
            
            const healthData = await healthResponse.json();
            const metricsData = await metricsResponse.json();
            
            const html = `
                <div class="mb-3">
                    <h6><i class="fas fa-heartbeat text-success"></i> Service Status</h6>
                    <p><strong>Status:</strong> <span class="badge bg-success">${healthData.status}</span></p>
                    <p><strong>Version:</strong> ${healthData.version}</p>
                    <p><strong>Uptime:</strong> ${Math.round(healthData.uptime)}s</p>
                </div>
                <div class="mb-3">
                    <h6><i class="fas fa-chart-bar"></i> System Metrics</h6>
                    <p><strong>Total Queries:</strong> ${metricsData.total_queries}</p>
                    <p><strong>Avg Response Time:</strong> ${metricsData.average_response_time_ms.toFixed(2)}ms</p>
                    <p><strong>Memory Usage:</strong> ${metricsData.memory_usage_mb.toFixed(1)}MB</p>
                </div>
                <div>
                    <h6><i class="fas fa-cogs"></i> Dependencies</h6>
                    ${Object.entries(healthData.dependencies).map(([name, status]) => `
                        <p><strong>${name}:</strong> <span class="badge bg-${status === 'healthy' ? 'success' : 'danger'}">${status}</span></p>
                    `).join('')}
                </div>
            `;
            
            document.getElementById('system-status').innerHTML = html;
            
        } catch (error) {
            document.getElementById('system-status').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load system status: ${error.message}
                </div>
            `;
        }
    }

    showLoading(show) {
        const loadingElement = document.querySelector('.loading');
        if (show) {
            loadingElement.classList.add('show');
        } else {
            loadingElement.classList.remove('show');
        }
    }

    clearResults() {
        document.getElementById('search-input').value = '';
        document.getElementById('search-results').innerHTML = '';
        document.getElementById('reverse-input').value = '';
        document.getElementById('reverse-results').innerHTML = '';
        document.getElementById('set-words').value = '';
        document.getElementById('set-operation-results').innerHTML = '';
    }

    displayError(message) {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }

    async recreateMappings() {
        const button = document.getElementById('recreate-mappings-btn');
        const resultsContainer = document.getElementById('recreate-mappings-results');
        
        // Disable button and show loading
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recreating...';
        
        resultsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin"></i> Starting mapping recreation process...
            </div>
        `;

        try {
            const response = await fetch(`${this.apiBaseUrl}/recreate-mappings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                // Success
                let html = `
                    <div class="alert alert-success">
                        <h6><i class="fas fa-check-circle"></i> Mappings Recreated Successfully!</h6>
                        <p><strong>Total Time:</strong> ${data.total_time_ms.toFixed(2)}ms</p>
                        <p><strong>Mappings Loaded:</strong> ${data.mappings_loaded}</p>
                        <hr>
                        <h6>Process Steps:</h6>
                `;

                data.steps.forEach((step, index) => {
                    const statusIcon = step.status === 'success' ? 'check-circle text-success' : 
                                     step.status === 'error' ? 'times-circle text-danger' : 
                                     'exclamation-triangle text-warning';
                    
                    html += `
                        <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                            <div>
                                <strong>${index + 1}. ${step.step}</strong><br>
                                <small class="text-muted">${step.status}</small>
                            </div>
                            <div class="text-end">
                                <i class="fas fa-${statusIcon}"></i><br>
                                <small class="text-muted">${step.time_ms.toFixed(1)}ms</small>
                            </div>
                        </div>
                    `;
                    
                    if (step.error) {
                        html += `<div class="alert alert-danger mt-2"><small>${step.error}</small></div>`;
                    }
                    if (step.output) {
                        html += `<div class="alert alert-info mt-2"><small>${step.output}</small></div>`;
                    }
                });

                html += '</div>';
                resultsContainer.innerHTML = html;

                // Refresh system status to show updated mappings
                setTimeout(() => this.loadSystemStatus(), 1000);

            } else {
                // Error
                let html = `
                    <div class="alert alert-danger">
                        <h6><i class="fas fa-times-circle"></i> Mapping Recreation Failed</h6>
                        <p><strong>Error:</strong> ${data.error || 'Unknown error'}</p>
                        <p><strong>Total Time:</strong> ${data.total_time_ms.toFixed(2)}ms</p>
                `;

                if (data.steps && data.steps.length > 0) {
                    html += '<hr><h6>Process Steps:</h6>';
                    data.steps.forEach((step, index) => {
                        const statusIcon = step.status === 'success' ? 'check-circle text-success' : 
                                         step.status === 'error' ? 'times-circle text-danger' : 
                                         'exclamation-triangle text-warning';
                        
                        html += `
                            <div class="d-flex justify-content-between align-items-center border-bottom py-2">
                                <div>
                                    <strong>${index + 1}. ${step.step}</strong><br>
                                    <small class="text-muted">${step.status}</small>
                                </div>
                                <div class="text-end">
                                    <i class="fas fa-${statusIcon}"></i><br>
                                    <small class="text-muted">${step.time_ms.toFixed(1)}ms</small>
                                </div>
                            </div>
                        `;
                        
                        if (step.error) {
                            html += `<div class="alert alert-danger mt-2"><small>${step.error}</small></div>`;
                        }
                    });
                }

                html += '</div>';
                resultsContainer.innerHTML = html;
            }

        } catch (error) {
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i> Failed to recreate mappings: ${error.message}
                </div>
            `;
        } finally {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-sync-alt"></i> Recreate Mappings';
        }
    }

    async getTableNames(columnIds) {
        const button = document.getElementById('get-table-names-btn');
        const resultsContainer = document.getElementById('search-results');
        
        // Disable button and show loading
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting Tables...';
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/get-table-names`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(columnIds)
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                // Success - add table names section to existing results
                const tableNamesSection = `
                    <div class="mt-3 p-3 bg-info bg-opacity-10 rounded border border-info">
                        <h6><i class="fas fa-table text-info"></i> Table Names</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Total Tables:</strong> ${data.total_tables}</p>
                                <p><strong>Columns Found:</strong> ${data.columns_found}/${data.total_columns_processed}</p>
                                ${data.columns_not_found > 0 ? `<p class="text-warning"><strong>Columns Not Found:</strong> ${data.columns_not_found}</p>` : ''}
                            </div>
                        </div>
                        <div class="mt-3">
                            <p><strong>All Table Names:</strong></p>
                            <div class="column-list bg-light" style="max-height: 200px; overflow-y: auto;">${data.table_names.join(', ')}</div>
                        </div>
                        ${data.not_found_columns.length > 0 ? `
                            <div class="mt-2">
                                <p class="text-warning"><strong>Columns not found in mapping:</strong></p>
                                <div class="column-list bg-warning bg-opacity-25">${data.not_found_columns.join(', ')}</div>
                            </div>
                        ` : ''}
                    </div>
                `;
                
                // Append to existing results
                resultsContainer.innerHTML += tableNamesSection;

            } else {
                // Error
                const errorSection = `
                    <div class="mt-3 p-3 bg-danger bg-opacity-10 rounded border border-danger">
                        <h6><i class="fas fa-exclamation-triangle text-danger"></i> Failed to Get Table Names</h6>
                        <p><strong>Error:</strong> ${data.error || 'Unknown error'}</p>
                        <p><strong>Columns Processed:</strong> ${data.column_ids ? data.column_ids.length : 0}</p>
                    </div>
                `;
                
                resultsContainer.innerHTML += errorSection;
            }

        } catch (error) {
            const errorSection = `
                <div class="mt-3 p-3 bg-danger bg-opacity-10 rounded border border-danger">
                    <h6><i class="fas fa-exclamation-triangle text-danger"></i> Failed to Get Table Names</h6>
                    <p><strong>Error:</strong> ${error.message}</p>
                </div>
            `;
            
            resultsContainer.innerHTML += errorSection;
        } finally {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-table"></i> Get Table Names';
        }
    }

    async processNaturalLanguageQuery() {
        const query = document.getElementById('nl-query-input').value.trim();
        const apiKey = document.getElementById('openai-api-key').value.trim();
        const button = document.getElementById('nl-query-btn');
        const resultsContainer = document.getElementById('search-results');
        
        if (!query) {
            alert('Please enter a natural language query');
            return;
        }
        
        if (!apiKey) {
            alert('Please enter your OpenAI API key');
            return;
        }
        
        // Disable button and show loading
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        resultsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin"></i> Processing natural language query with AI...
            </div>
        `;

        try {
            const response = await fetch(`${this.apiBaseUrl}/natural-language-query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query,
                    openai_api_key: apiKey
                })
            });

            const data = await response.json();

            if (response.ok && data.status === 'success') {
                // Success - display the complete pipeline results
                let html = `
                    <div class="alert alert-success">
                        <h6><i class="fas fa-check-circle"></i> Natural Language Query Processed Successfully!</h6>
                        <p><strong>Original Query:</strong> "${data.original_query}"</p>
                        <p><strong>ChatGPT Processing Time:</strong> ${data.chatgpt_time_ms.toFixed(2)}ms</p>
                        <hr>
                        <h6><i class="fas fa-brain"></i> Extracted Words:</h6>
                        <div class="mb-3">
                            ${data.relevant_words.map(word => `<span class="badge bg-primary me-1">${word}</span>`).join('')}
                        </div>
                        <hr>
                        <h6><i class="fas fa-chart-bar"></i> Summary:</h6>
                        <div class="row">
                            <div class="col-md-4">
                                <p><strong>Words Processed:</strong> ${data.summary.total_words_processed}</p>
                            </div>
                            <div class="col-md-4">
                                <p><strong>Total Columns:</strong> ${data.summary.total_columns_found}</p>
                            </div>
                            <div class="col-md-4">
                                <p><strong>Total Tables:</strong> ${data.summary.total_tables_found}</p>
                            </div>
                        </div>
                    </div>
                `;

                // Display results for each word
                data.search_results.forEach((result, index) => {
                    const statusIcon = result.error ? 'times-circle text-danger' : 
                                     result.total_results > 0 ? 'check-circle text-success' : 
                                     'exclamation-triangle text-warning';
                    
                    html += `
                        <div class="card mt-3">
                            <div class="card-header">
                                <h6><i class="fas fa-${statusIcon}"></i> Word ${index + 1}: "${result.word}"</h6>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6">
                                        <p><strong>Search Results:</strong> ${result.total_results}</p>
                                        <p><strong>Columns Found:</strong> ${result.columns.length}</p>
                                        <p><strong>Tables Found:</strong> ${result.tables.length}</p>
                                        <p><strong>Search Time:</strong> ${result.search_time_ms.toFixed(2)}ms</p>
                                        ${result.error ? `<p class="text-danger"><strong>Error:</strong> ${result.error}</p>` : ''}
                                    </div>
                                    <div class="col-md-6">
                                        ${result.columns.length > 0 ? `
                                            <p><strong>Columns:</strong></p>
                                            <div class="column-list" style="max-height: 100px; overflow-y: auto;">${result.columns.slice(0, 10).join(', ')}${result.columns.length > 10 ? '...' : ''}</div>
                                        ` : ''}
                                        ${result.tables.length > 0 ? `
                                            <p class="mt-2"><strong>Tables:</strong></p>
                                            <div class="column-list bg-info bg-opacity-10">${result.tables.join(', ')}</div>
                                        ` : ''}
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });

                // Display final summary
                html += `
                    <div class="mt-4 p-3 bg-primary bg-opacity-10 rounded border border-primary">
                        <h6><i class="fas fa-list"></i> Final Results</h6>
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>All Unique Columns (${data.summary.all_columns.length}):</strong></p>
                                <div class="column-list bg-white" style="max-height: 150px; overflow-y: auto;">${data.summary.all_columns.join(', ')}</div>
                            </div>
                            <div class="col-md-6">
                                <p><strong>All Unique Tables (${data.summary.all_tables.length}):</strong></p>
                                <div class="column-list bg-white" style="max-height: 150px; overflow-y: auto;">${data.summary.all_tables.join(', ')}</div>
                            </div>
                        </div>
                    </div>
                `;

                resultsContainer.innerHTML = html;

            } else {
                // Error
                resultsContainer.innerHTML = `
                    <div class="alert alert-danger">
                        <h6><i class="fas fa-times-circle"></i> Natural Language Query Failed</h6>
                        <p><strong>Error:</strong> ${data.error || 'Unknown error'}</p>
                        <p><strong>Original Query:</strong> "${data.original_query || query}"</p>
                    </div>
                `;
            }

        } catch (error) {
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i> Failed to process natural language query: ${error.message}
                </div>
            `;
        } finally {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-magic"></i> Process with AI';
        }
    }

    clearNaturalLanguageQuery() {
        document.getElementById('nl-query-input').value = '';
        document.getElementById('openai-api-key').value = '';
        document.getElementById('search-results').innerHTML = '';
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SearchEngineDashboard();
});
