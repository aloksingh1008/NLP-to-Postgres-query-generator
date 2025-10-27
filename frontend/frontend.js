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

        // SQL Generation with MCP
        document.getElementById('sql-generate-btn').addEventListener('click', () => this.generateSQL(false));
        document.getElementById('sql-force-csv-btn').addEventListener('click', () => this.generateSQL(true));
        document.getElementById('clear-sql-btn').addEventListener('click', () => this.clearSQLResults());
        document.getElementById('sql-query-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.generateSQL(false);
        });
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
                <div class="row">
                    <div class="col-md-6">
                        <h6><i class="fas fa-list"></i> All Columns (${data.total_all_columns ? data.total_all_columns.length : data.total_unique_columns.length}) - Including Duplicates</h6>
                        <div class="column-list" style="max-height: 150px; overflow-y: auto;">${data.total_all_columns ? data.total_all_columns.join(', ') : data.total_unique_columns.join(', ')}</div>
                    </div>
                    <div class="col-md-6">
                        <h6><i class="fas fa-list"></i> Unique Columns (${data.total_unique_columns.length})</h6>
                        <div class="column-list" style="max-height: 150px; overflow-y: auto;">${data.total_unique_columns.join(', ')}</div>
                    </div>
                </div>
                <div class="mt-3">
                    <button class="btn btn-info btn-sm me-2" type="button" id="get-table-names-btn-all" data-columns='${JSON.stringify(data.total_all_columns || data.total_unique_columns)}'>
                        <i class="fas fa-table"></i> Get Table Names (All)
                    </button>
                    <button class="btn btn-secondary btn-sm" type="button" id="get-table-names-btn-unique" data-columns='${JSON.stringify(data.total_unique_columns)}'>
                        <i class="fas fa-table"></i> Get Table Names (Unique)
                    </button>
                </div>
            </div>
        </div>`;

        resultsContainer.innerHTML = html;
        
        // Add event listeners for the new buttons
        document.getElementById('get-table-names-btn-all').addEventListener('click', (e) => {
            const columnIds = JSON.parse(e.target.getAttribute('data-columns'));
            this.getTableNames(columnIds, 'get-table-names-btn-all');
        });
        
        document.getElementById('get-table-names-btn-unique').addEventListener('click', (e) => {
            const columnIds = JSON.parse(e.target.getAttribute('data-columns'));
            this.getTableNames(columnIds, 'get-table-names-btn-unique');
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

    async getTableNames(columnIds, buttonId = 'get-table-names-btn-all') {
        const button = document.getElementById(buttonId);
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
                                <p><strong>Unique Tables:</strong> ${data.unique_tables}</p>
                                <p><strong>Columns Found:</strong> ${data.columns_found}/${data.total_columns_processed}</p>
                                ${data.columns_not_found > 0 ? `<p class="text-warning"><strong>Columns Not Found:</strong> ${data.columns_not_found}</p>` : ''}
                            </div>
                        </div>
                        <div class="mt-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>All Table Names (including duplicates):</strong></p>
                                    <div class="column-list bg-light" style="max-height: 200px; overflow-y: auto;">${data.table_names.join(', ')}</div>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Unique Table Names:</strong></p>
                                    <div class="column-list bg-light" style="max-height: 200px; overflow-y: auto;">${data.unique_table_names.join(', ')}</div>
                                </div>
                            </div>
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
        const button = document.getElementById('nl-query-btn');
        const resultsContainer = document.getElementById('search-results');
        
        if (!query) {
            alert('Please enter a natural language query');
            return;
        }
        
        // Disable button and show loading
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        
        resultsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-spinner fa-spin"></i> Processing natural language query with AI...
                <p class="small mb-0 mt-2">Using OpenAI API configured on the server...</p>
            </div>
        `;

        try {
            const response = await fetch(`${this.apiBaseUrl}/natural-language-query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: query
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
                            <div class="col-md-3">
                                <p><strong>Words Processed:</strong> ${data.summary.total_words_processed}</p>
                            </div>
                            <div class="col-md-3">
                                <p><strong>Total Columns:</strong> ${data.summary.total_columns_found}</p>
                                <small class="text-muted">Unique: ${data.summary.unique_columns_found || 0}</small>
                            </div>
                            <div class="col-md-3">
                                <p><strong>Total Tables:</strong> ${data.summary.total_tables_found}</p>
                                <small class="text-muted">Unique: ${data.summary.unique_tables_found || 0}</small>
                            </div>
                            <div class="col-md-3">
                                <p><strong>Duplicates:</strong></p>
                                <small class="text-muted">Columns: ${data.summary.total_columns_found - (data.summary.unique_columns_found || 0)}</small><br>
                                <small class="text-muted">Tables: ${data.summary.total_tables_found - (data.summary.unique_tables_found || 0)}</small>
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
                                        <small class="text-muted">Unique: ${[...new Set(result.columns)].length}</small><br>
                                        <p><strong>Tables Found:</strong> ${result.tables.length}</p>
                                        <small class="text-muted">Unique: ${[...new Set(result.tables)].length}</small><br>
                                        <p><strong>Search Time:</strong> ${result.search_time_ms.toFixed(2)}ms</p>
                                        ${result.error ? `<p class="text-danger"><strong>Error:</strong> ${result.error}</p>` : ''}
                                    </div>
                                    <div class="col-md-6">
                                        ${result.columns.length > 0 ? `
                                            <p><strong>Columns (including duplicates):</strong></p>
                                            <div class="column-list" style="max-height: 100px; overflow-y: auto;">${result.columns.slice(0, 10).join(', ')}${result.columns.length > 10 ? '...' : ''}</div>
                                        ` : ''}
                                        ${result.tables.length > 0 ? `
                                            <p class="mt-2"><strong>Tables (including duplicates):</strong></p>
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
                                <div class="mb-3">
                                    <p><strong>All Columns (${data.summary.all_columns.length}) - Including Duplicates:</strong></p>
                                    <div class="column-list bg-white" style="max-height: 150px; overflow-y: auto;">${data.summary.all_columns.join(', ')}</div>
                                </div>
                                <div>
                                    <p><strong>Unique Columns (${data.summary.unique_columns_found || 0}):</strong></p>
                                    <div class="column-list bg-light" style="max-height: 100px; overflow-y: auto;">${[...new Set(data.summary.all_columns)].join(', ')}</div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <p><strong>All Tables (${data.summary.all_tables.length}) - Including Duplicates:</strong></p>
                                    <div class="column-list bg-white" style="max-height: 150px; overflow-y: auto;">${data.summary.all_tables.join(', ')}</div>
                                </div>
                                <div>
                                    <p><strong>Unique Tables (${data.summary.unique_tables_found || 0}):</strong></p>
                                    <div class="column-list bg-light" style="max-height: 100px; overflow-y: auto;">${[...new Set(data.summary.all_tables)].join(', ')}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

                resultsContainer.innerHTML = html;
                
                // Display table ranking if available
                if (data.table_ranking) {
                    this.displayTableRanking(data.table_ranking, data.ranking_time_ms || 0);
                }

                // Display relationship traversal if available
                if (data.relationship_traversal) {
                    this.displayRelationshipTraversal(data.relationship_traversal, data.traversal_time_ms || 0);
                }

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
        document.getElementById('search-results').innerHTML = '';
        // Hide table ranking card
        document.getElementById('table-ranking-card').style.display = 'none';
        // Hide relationship traversal card
        document.getElementById('relationship-traversal-card').style.display = 'none';
    }
    
    displayTableRanking(rankingData, executionTime) {
        const rankingCard = document.getElementById('table-ranking-card');
        const resultsContainer = document.getElementById('table-ranking-results');
        
        // Show the ranking card
        rankingCard.style.display = 'block';
        
        // Update summary metrics
        if (rankingData.summary) {
            document.getElementById('ranking-unique-tables').textContent = rankingData.total_unique_tables || 0;
            document.getElementById('ranking-multi-keyword-tables').textContent = 
                rankingData.summary.tables_across_multiple_keywords || 0;
            document.getElementById('ranking-avg-keywords').textContent = 
                (rankingData.summary.average_keywords_per_table || 0).toFixed(1);
        }
        
        // Build the table ranking display
        let html = `
            <div class="mb-3">
                <h6><i class="fas fa-info-circle"></i> Analysis Overview</h6>
                <p class="small text-muted">
                    Tables are ranked by <strong>cross-keyword relevance</strong> - 
                    tables appearing across multiple keywords are prioritized as they are more central to your query.
                </p>
                <p><strong>Analysis Time:</strong> ${executionTime.toFixed(2)}ms</p>
                <p><strong>Total Occurrences:</strong> ${rankingData.total_occurrences || 0}</p>
                ${rankingData.summary ? `
                    <p><strong>Multi-Keyword Tables:</strong> ${rankingData.summary.tables_across_multiple_keywords} 
                    (${rankingData.summary.multi_keyword_percentage}%)</p>
                ` : ''}
            </div>
            <hr>
        `;
        
        if (rankingData.top_tables && rankingData.top_tables.length > 0) {
            html += '<h6><i class="fas fa-trophy text-warning"></i> Top Ranked Tables</h6>';
            
            rankingData.top_tables.forEach((table, index) => {
                const rankClass = index < 3 ? `rank-${index + 1}` : '';
                const medals = ['🥇', '🥈', '🥉'];
                const medal = index < 3 ? `<span class="rank-medal">${medals[index]}</span>` : '';
                
                html += `
                    <div class="table-ranking-item ${rankClass}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="mb-2">
                                    ${medal}
                                    <span class="table-name">#${index + 1}: ${table.table}</span>
                                </div>
                                <div class="row small">
                                    <div class="col-md-6">
                                        <p class="mb-1">
                                            <i class="fas fa-key text-primary"></i> 
                                            <strong>Keywords:</strong> ${table.keyword_count} 
                                            ${table.keyword_count > 1 ? '✓' : ''}
                                        </p>
                                        <p class="mb-1">
                                            <i class="fas fa-hashtag text-info"></i> 
                                            <strong>Frequency:</strong> ${table.frequency}
                                        </p>
                                        <p class="mb-1">
                                            <i class="fas fa-percentage text-success"></i> 
                                            <strong>Percentage:</strong> ${table.percentage}%
                                        </p>
                                    </div>
                                    <div class="col-md-6">
                                        <p class="mb-1"><strong>Contributing Keywords:</strong></p>
                                        <div>
                                            ${table.contributing_keywords.map(kw => 
                                                `<span class="keyword-badge">${kw}</span>`
                                            ).join('')}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            // Add view all rankings button if there are more tables
            if (rankingData.all_rankings && rankingData.all_rankings.length > rankingData.top_tables.length) {
                html += `
                    <div class="mt-3 text-center">
                        <button class="btn btn-outline-primary btn-sm" type="button" id="view-all-rankings-btn">
                            <i class="fas fa-list"></i> View All ${rankingData.all_rankings.length} Rankings
                        </button>
                    </div>
                `;
            }
        } else {
            html += '<p class="text-muted">No table rankings available.</p>';
        }
        
        resultsContainer.innerHTML = html;
        
        // Add event listener for view all button if it exists
        const viewAllBtn = document.getElementById('view-all-rankings-btn');
        if (viewAllBtn) {
            viewAllBtn.addEventListener('click', () => {
                this.displayAllRankings(rankingData.all_rankings);
            });
        }
        
        // Scroll to the ranking card
        rankingCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    displayAllRankings(allRankings) {
        const resultsContainer = document.getElementById('table-ranking-results');
        
        let html = `
            <div class="mb-3">
                <h6><i class="fas fa-list"></i> Complete Table Rankings (${allRankings.length} tables)</h6>
                <button class="btn btn-sm btn-outline-secondary mb-2" id="back-to-top-rankings-btn">
                    <i class="fas fa-arrow-left"></i> Back to Top Rankings
                </button>
            </div>
        `;
        
        allRankings.forEach((table, index) => {
            html += `
                <div class="table-ranking-item">
                    <div class="small">
                        <span class="table-name">#${index + 1}: ${table.table}</span>
                        <div class="mt-1">
                            <span class="badge bg-primary">${table.keyword_count} keywords</span>
                            <span class="badge bg-info">${table.frequency}x</span>
                            <span class="badge bg-success">${table.percentage}%</span>
                        </div>
                        <div class="mt-1">
                            ${table.contributing_keywords.map(kw => 
                                `<span class="keyword-badge">${kw}</span>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
        });
        
        resultsContainer.innerHTML = html;
        
        // Add back button functionality
        document.getElementById('back-to-top-rankings-btn').addEventListener('click', () => {
            // Reload the table ranking display (would need to store the original data)
            location.reload(); // Simple solution for now
        });
    }

    displayRelationshipTraversal(traversalData, executionTime) {
        const traversalCard = document.getElementById('relationship-traversal-card');
        const resultsContainer = document.getElementById('relationship-traversal-results');
        
        // Show the traversal card
        traversalCard.style.display = 'block';
        
        // Build the relationship traversal display
        let html = `
            <div class="mb-3">
                <h6><i class="fas fa-project-diagram"></i> Relationship Traversal Overview</h6>
                <p class="small text-muted">
                    Using <strong>BFS (Breadth-First Search)</strong> algorithm to discover related tables 
                    through foreign key relationships. Tables with maximum frequency are used as starting points.
                </p>
                <p><strong>Traversal Time:</strong> ${executionTime.toFixed(2)}ms</p>
                <p><strong>Traversal Status:</strong> ${traversalData.traversal_enabled ? 
                    '<span class="badge bg-success">✓ Enabled</span>' : 
                    '<span class="badge bg-secondary">Disabled</span>'}</p>
            </div>
        `;
        
        if (traversalData.error) {
            html += `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> <strong>Traversal Error:</strong> ${traversalData.error}
                </div>
            `;
        }
        
        if (traversalData.traversal_enabled) {
            // Display max frequency and starting tables
            html += `
                <div class="card mb-3 border-primary">
                    <div class="card-header bg-primary bg-opacity-10">
                        <h6 class="mb-0"><i class="fas fa-flag-checkered"></i> BFS Starting Point</h6>
                    </div>
                    <div class="card-body">
                        <p><strong>Maximum Frequency:</strong> <span class="badge bg-primary fs-6">${traversalData.max_frequency}</span></p>
                        <p><strong>Tables with Max Frequency:</strong></p>
                        <div class="d-flex flex-wrap gap-2">
                            ${traversalData.tables_with_max_frequency.map(table => 
                                `<span class="badge bg-primary">${table}</span>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            // Display statistics
            html += `
                <div class="row mb-3">
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <div class="metric-value text-primary">${traversalData.total_original_tables}</div>
                            <div class="metric-label">Original Tables</div>
                            <small class="text-muted">From search results</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <div class="metric-value text-success">${traversalData.total_related_tables}</div>
                            <div class="metric-label">Related Tables</div>
                            <small class="text-muted">Found via relationships</small>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center p-3 bg-light rounded">
                            <div class="metric-value text-info">${traversalData.total_relevant_tables}</div>
                            <div class="metric-label">Total Relevant</div>
                            <small class="text-muted">Combined tables</small>
                        </div>
                    </div>
                </div>
            `;
            
            // Display original tables
            if (traversalData.original_tables && traversalData.original_tables.length > 0) {
                html += `
                    <div class="card mb-3 border-primary">
                        <div class="card-header bg-primary bg-opacity-10">
                            <h6 class="mb-0"><i class="fas fa-search"></i> Original Tables (${traversalData.original_tables.length})</h6>
                        </div>
                        <div class="card-body">
                            <p class="small text-muted">Tables found directly from keyword search</p>
                            <div class="d-flex flex-wrap gap-2">
                                ${traversalData.original_tables.map(table => 
                                    `<span class="badge bg-primary">${table}</span>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Display related tables (found through traversal)
            if (traversalData.related_tables && traversalData.related_tables.length > 0) {
                html += `
                    <div class="card mb-3 border-success">
                        <div class="card-header bg-success bg-opacity-10">
                            <h6 class="mb-0"><i class="fas fa-link"></i> Related Tables (${traversalData.related_tables.length})</h6>
                        </div>
                        <div class="card-body">
                            <p class="small text-muted">Tables discovered through foreign key relationships</p>
                            <div class="d-flex flex-wrap gap-2">
                                ${traversalData.related_tables.map(table => 
                                    `<span class="badge bg-success">${table}</span>`
                                ).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                html += `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> No additional related tables found through relationship traversal.
                    </div>
                `;
            }
            
            // Display all relevant tables
            if (traversalData.all_relevant_tables && traversalData.all_relevant_tables.length > 0) {
                html += `
                    <div class="card border-info">
                        <div class="card-header bg-info bg-opacity-10">
                            <h6 class="mb-0"><i class="fas fa-database"></i> All Relevant Tables (${traversalData.all_relevant_tables.length})</h6>
                        </div>
                        <div class="card-body">
                            <p class="small text-muted">Complete list for query generation</p>
                            <div class="column-list bg-light" style="max-height: 200px; overflow-y: auto;">
                                ${traversalData.all_relevant_tables.join(', ')}
                            </div>
                            <button class="btn btn-sm btn-outline-primary mt-2" onclick="navigator.clipboard.writeText('${traversalData.all_relevant_tables.join(', ')}')">
                                <i class="fas fa-copy"></i> Copy All Tables
                            </button>
                        </div>
                    </div>
                `;
            }
        } else {
            html += `
                <div class="alert alert-secondary">
                    <i class="fas fa-info-circle"></i> ${traversalData.note || 'Relationship traversal not performed.'}
                </div>
            `;
        }
        
        resultsContainer.innerHTML = html;
        
        // Scroll to the traversal card
        traversalCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    async generateSQL(forceCSV = false) {
        const query = document.getElementById('sql-query-input').value.trim();
        if (!query) {
            this.displaySQLError('Please enter a query');
            return;
        }

        const maxDepth = parseInt(document.getElementById('sql-max-depth').value) || 2;
        const threshold = parseInt(document.getElementById('sql-threshold').value) || 10;
        const debug = document.getElementById('sql-debug-mode').checked;
        const dryRun = true; // Always use dry run (no DB execution)

        const resultsDiv = document.getElementById('sql-generation-results');
        resultsDiv.innerHTML = `
            <div class="alert alert-info">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                <strong>Generating SQL queries...</strong>
                <p class="small mb-0 mt-2">Analyzing tables and generating optimized queries with AI.</p>
            </div>
        `;

        try {
            const startTime = performance.now();
            
            console.log('Sending SQL generation request:', {
                query, maxDepth, threshold, forceCSV, debug, dryRun
            });
            
            const response = await fetch('http://localhost:8000/sql/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    max_depth: maxDepth,
                    auto_export_threshold: threshold,
                    force_csv: forceCSV,
                    debug: debug,
                    dry_run: dryRun  // Add dry_run parameter
                })
            });

            const endTime = performance.now();
            const duration = (endTime - startTime).toFixed(2);

            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                console.error('Error response:', errorData);
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }

            const data = await response.json();
            console.log('SQL Generation Response:', data);
            
            this.displaySQLResults(data, duration);

        } catch (error) {
            console.error('SQL Generation Error:', error);
            this.displaySQLError('SQL Generation failed: ' + error.message);
        }
    }

    displaySQLResults(data, duration) {
        const resultsDiv = document.getElementById('sql-generation-results');
        
        if (!data.success) {
            this.displaySQLError(data.error || 'Unknown error occurred');
            return;
        }

        let html = `
            <div class="card bg-white mt-3">
                <div class="card-header bg-success text-white">
                    <h6 class="mb-0">
                        <i class="fas fa-check-circle"></i> SQL Generated Successfully
                        <small class="float-end">${duration}ms</small>
                    </h6>
                </div>
                <div class="card-body">
                    <div class="alert alert-info mb-3">
                        <i class="fas fa-info-circle"></i> 
                        <strong>Mode: SQL Generation Only</strong> - Queries are not executed against the database.
                    </div>
                    <div class="mb-3">
                        <strong>Your Query:</strong> 
                        <div class="bg-light p-2 rounded mt-1">
                            ${this.escapeHtml(data.user_query)}
                        </div>
                    </div>
                    <div class="mb-3">
                        <strong>Relevant Tables Identified:</strong>
                        <div class="mt-2">
                            ${data.relevant_tables.map(table => 
                                `<span class="badge bg-primary me-1 mb-1">${table}</span>`
                            ).join('')}
                        </div>
                    </div>
        `;

        // Display SQL Queries
        if (data.sql_queries) {
            html += `
                <div class="mb-3">
                    <h5 class="text-primary">
                        <i class="fas fa-code"></i> Generated SQL Queries (3 Types)
                    </h5>
                    <p class="text-muted small">Three different queries generated for different use cases:</p>
                    
                    <!-- Count SQL -->
                    <div class="mt-3 border rounded p-3 bg-light">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="text-success mb-0">
                                <span class="badge bg-success me-2">1</span>
                                COUNT SQL
                            </h6>
                            <button class="btn btn-sm btn-outline-secondary" onclick="navigator.clipboard.writeText(\`${this.escapeBackticks(data.sql_queries.count_sql)}\`); alert('Copied!')">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                        </div>
                        <p class="small text-muted mb-2">
                            <i class="fas fa-info-circle"></i> Returns the total number of matching records
                        </p>
                        <div class="bg-dark text-light p-3 rounded" style="font-family: 'Courier New', monospace; font-size: 0.9rem; overflow-x: auto; white-space: pre-wrap;">
${this.formatSQL(data.sql_queries.count_sql)}</div>
                    </div>
                    
                    <!-- Query SQL -->
                    <div class="mt-3 border rounded p-3 bg-light">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="text-primary mb-0">
                                <span class="badge bg-primary me-2">2</span>
                                QUERY SQL (Preview with LIMIT)
                            </h6>
                            <button class="btn btn-sm btn-outline-secondary" onclick="navigator.clipboard.writeText(\`${this.escapeBackticks(data.sql_queries.query_sql)}\`); alert('Copied!')">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                        </div>
                        <p class="small text-muted mb-2">
                            <i class="fas fa-info-circle"></i> Returns limited rows for quick preview (with LIMIT clause)
                        </p>
                        <div class="bg-dark text-light p-3 rounded" style="font-family: 'Courier New', monospace; font-size: 0.9rem; overflow-x: auto; white-space: pre-wrap;">
${this.formatSQL(data.sql_queries.query_sql)}</div>
                    </div>
                    
                    <!-- CSV SQL -->
                    <div class="mt-3 border rounded p-3 bg-light">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <h6 class="text-warning mb-0">
                                <span class="badge bg-warning me-2">3</span>
                                CSV SQL (Full Data Export)
                            </h6>
                            <button class="btn btn-sm btn-outline-secondary" onclick="navigator.clipboard.writeText(\`${this.escapeBackticks(data.sql_queries.csv_sql)}\`); alert('Copied!')">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                        </div>
                        <p class="small text-muted mb-2">
                            <i class="fas fa-info-circle"></i> Returns all matching records without LIMIT (for full data export)
                        </p>
                        <div class="bg-dark text-light p-3 rounded" style="font-family: 'Courier New', monospace; font-size: 0.9rem; overflow-x: auto; white-space: pre-wrap;">
${this.formatSQL(data.sql_queries.csv_sql)}</div>
                    </div>
                </div>
            `;
        }

        // Show message instead of DB results (dry run mode)
        html += `
                    <div class="alert alert-success mt-3">
                        <i class="fas fa-check-circle"></i> 
                        <strong>${data.message || 'SQL queries generated successfully!'}</strong>
                        <p class="mb-0 mt-2 small">
                            You can copy any of the queries above and execute them in your database client.
                        </p>
                    </div>
                    <div class="mt-3 text-muted small">
                        <i class="fas fa-clock"></i> 
                        Generated at: ${new Date(data.timestamp).toLocaleString()}
                    </div>
                </div>
            </div>
        `;

        resultsDiv.innerHTML = html;
    }

    displaySQLError(message) {
        const resultsDiv = document.getElementById('sql-generation-results');
        resultsDiv.innerHTML = `
            <div class="alert alert-danger mt-3">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
    }

    clearSQLResults() {
        document.getElementById('sql-query-input').value = '';
        document.getElementById('sql-generation-results').innerHTML = '';
    }

    formatSQL(sql) {
        // Basic SQL formatting for display
        return this.escapeHtml(sql)
            .replace(/\b(SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|GROUP BY|ORDER BY|HAVING|LIMIT|COUNT|AS)\b/gi, 
                match => `<span style="color: #ff79c6;">${match}</span>`)
            .replace(/\b(table\d+|column\d+)\b/gi,
                match => `<span style="color: #50fa7b;">${match}</span>`);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeBackticks(str) {
        return str ? str.replace(/`/g, '\\`').replace(/\$/g, '\\$') : '';
    }

    async downloadCSV(filename) {
        try {
            // In a real implementation, you would have an endpoint to download the file
            // For now, we'll show a message
            alert(`Download functionality would download: ${filename}\n\nIn production, this would trigger a file download from the server.`);
            
            // Example implementation:
            // const response = await fetch(`http://localhost:8000/sql/download/${filename}`);
            // const blob = await response.blob();
            // const url = window.URL.createObjectURL(blob);
            // const a = document.createElement('a');
            // a.href = url;
            // a.download = filename;
            // document.body.appendChild(a);
            // a.click();
            // window.URL.revokeObjectURL(url);
            // document.body.removeChild(a);
        } catch (error) {
            alert('Download failed: ' + error.message);
        }
    }

    exportTableToCSV() {
        // Export visible table to CSV
        const table = document.querySelector('.table');
        if (!table) return;

        let csv = [];
        const rows = table.querySelectorAll('tr');
        
        for (let row of rows) {
            let cols = row.querySelectorAll('td, th');
            let csvRow = [];
            for (let col of cols) {
                csvRow.push('"' + col.textContent.replace(/"/g, '""') + '"');
            }
            csv.push(csvRow.join(','));
        }
        
        const csvContent = csv.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'query_results_' + new Date().getTime() + '.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.searchDashboard = new SearchEngineDashboard();
});
