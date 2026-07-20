document.addEventListener('DOMContentLoaded', () => {
    // --- Global State ---
    let products = [];

    // --- Tab Navigation ---
    const navBtns = document.querySelectorAll('.nav-btn');
    const sections = document.querySelectorAll('.task-section');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const target = btn.getAttribute('data-target');
            sections.forEach(sec => {
                if(sec.id === target) {
                    sec.classList.remove('hidden');
                } else {
                    sec.classList.add('hidden');
                }
            });

            // Trigger reflows for plotly charts if needed
            if(target === 'task2' && products.length > 0) {
                // If deduplication wasn't run yet, run it
                if(!document.getElementById('tsne-plot').data) {
                    document.getElementById('run-dedup-btn').click();
                }
            }
        });
    });

    // --- Utility: Render Product Card ---
    function createProductCard(product, onClick = null, highlight = false, simScore = null) {
        const div = document.createElement('div');
        div.className = `product-card ${highlight ? 'duplicate-highlight' : ''}`;
        
        let simBadge = '';
        if (simScore !== null) {
            const pct = (simScore * 100).toFixed(1);
            simBadge = `<div class="sim-badge">${pct}% Match</div>`;
        }

        div.innerHTML = `
            ${simBadge}
            <img src="${product.image_url}" loading="lazy" alt="${product.name}">
            <div class="product-info">
                <div class="product-category">${product.category} > ${product.subcategory}</div>
                <div class="product-name">${product.name}</div>
                <div class="product-price">₹${product.price.toFixed(2)}</div>
            </div>
        `;
        if (onClick) {
            div.addEventListener('click', () => onClick(product));
        }
        return div;
    }

    // --- TASK 1: Smart Recommendations ---
    const catalogGrid = document.getElementById('catalog-grid');
    const targetProductContainer = document.getElementById('target-product-container');
    const recsContainer = document.getElementById('recommendations-container');

    async function loadCatalog() {
        try {
            const res = await fetch('/api/products');
            products = await res.json();
            
            catalogGrid.innerHTML = '';
            products.forEach(p => {
                const card = createProductCard(p, handleProductClick);
                catalogGrid.appendChild(card);
            });
        } catch (error) {
            console.error("Failed to load catalog", error);
            catalogGrid.innerHTML = '<div class="col-span-full text-center text-red-500">Failed to load catalog. Ensure backend is running.</div>';
        }
    }

    async function handleProductClick(product) {
        // Show target
        targetProductContainer.innerHTML = '<p class="text-sm text-gray-400 mb-2">Selected Item:</p>';
        targetProductContainer.appendChild(createProductCard(product));
        targetProductContainer.classList.remove('hidden');

        // Show loading
        recsContainer.innerHTML = '<div class="text-center py-8"><div class="loader mx-auto"></div></div>';

        // Fetch recommendations
        try {
            const res = await fetch(`/api/recommendations/${product.id}`);
            const data = await res.json();
            
            recsContainer.innerHTML = '';
            if(data.recommendations.length === 0) {
                recsContainer.innerHTML = '<p class="text-gray-400 text-center">No recommendations found.</p>';
                return;
            }

            data.recommendations.forEach(rec => {
                recsContainer.appendChild(createProductCard(rec));
            });
        } catch (e) {
            recsContainer.innerHTML = '<p class="text-red-500 text-center">Error fetching recommendations.</p>';
        }
    }

    // --- TASK 2: Deduplication ---
    const thresholdInput = document.getElementById('sim-threshold');
    const thresholdVal = document.getElementById('threshold-val');
    const runDedupBtn = document.getElementById('run-dedup-btn');
    const origCatalog = document.getElementById('original-catalog');
    const cleanedCatalog = document.getElementById('cleaned-catalog');
    
    thresholdInput.addEventListener('input', (e) => {
        thresholdVal.textContent = parseFloat(e.target.value).toFixed(2);
    });

    runDedupBtn.addEventListener('click', async () => {
        const threshold = parseFloat(thresholdInput.value);
        
        // Show loading state on button
        const originalText = runDedupBtn.textContent;
        runDedupBtn.innerHTML = '<div class="loader w-4 h-4 inline-block align-middle mr-2 border-2 border-white border-t-transparent"></div> Processing...';
        runDedupBtn.disabled = true;

        try {
            const res = await fetch('/api/deduplicate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ threshold })
            });
            const data = await res.json();
            
            document.getElementById('orig-count').textContent = data.original_count;
            document.getElementById('clean-count').textContent = data.cleaned_count;

            // Render Catalogs
            origCatalog.innerHTML = '';
            // We'll highlight duplicates in the original catalog
            const cleanedIds = new Set(data.cleaned_catalog.map(p => p.id));
            products.forEach(p => {
                const isDup = !cleanedIds.has(p.id);
                origCatalog.appendChild(createProductCard(p, null, isDup));
            });

            cleanedCatalog.innerHTML = '';
            data.cleaned_catalog.forEach(p => {
                cleanedCatalog.appendChild(createProductCard(p));
            });

            // Render t-SNE Plotly
            renderTsne(data.scatter_data);
            
            // Render Heatmap Plotly
            renderHeatmap(data.similarity_matrix, data.scatter_data.map(d => d.id));

        } catch (e) {
            console.error(e);
            alert("Error running deduplication");
        } finally {
            runDedupBtn.textContent = originalText;
            runDedupBtn.disabled = false;
        }
    });

    function renderTsne(scatterData) {
        const unique = scatterData.filter(d => !d.is_duplicate);
        const duplicates = scatterData.filter(d => d.is_duplicate);

        const trace1 = {
            x: unique.map(d => d.tsne[0]),
            y: unique.map(d => d.tsne[1]),
            mode: 'markers',
            type: 'scatter',
            name: 'Unique Items',
            text: unique.map(d => `${d.name} (${d.category})`),
            marker: { size: 10, color: '#10B981' }
        };

        const trace2 = {
            x: duplicates.map(d => d.tsne[0]),
            y: duplicates.map(d => d.tsne[1]),
            mode: 'markers',
            type: 'scatter',
            name: 'Duplicates',
            text: duplicates.map(d => `${d.name} (${d.category})`),
            marker: { size: 8, color: '#EF4444', symbol: 'x' }
        };

        const layout = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: '#9CA3AF' },
            xaxis: { showgrid: false, zeroline: false },
            yaxis: { showgrid: false, zeroline: false },
            margin: { l: 20, r: 20, b: 20, t: 20 },
            legend: { orientation: 'h', y: -0.1 }
        };

        Plotly.newPlot('tsne-plot', [trace1, trace2], layout, {responsive: true});
    }

    function renderHeatmap(matrix, labels) {
        const trace = {
            z: matrix,
            type: 'heatmap',
            colorscale: 'Viridis',
            hoverongaps: false
        };

        const layout = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: '#9CA3AF', size: 8 },
            margin: { l: 20, r: 20, b: 20, t: 20 },
            xaxis: { showticklabels: false },
            yaxis: { showticklabels: false }
        };

        Plotly.newPlot('heatmap-plot', [trace], layout, {responsive: true});
    }

    // --- TASK 3: Visual Search ---
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const searchResults = document.getElementById('search-results');
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if(e.key === 'Enter') performSearch();
    });

    async function performSearch() {
        const query = searchInput.value.trim();
        if(!query) return;

        searchBtn.innerHTML = '<div class="loader w-4 h-4 inline-block align-middle"></div>';
        searchBtn.disabled = true;
        searchResults.innerHTML = '<div class="col-span-full text-center py-12"><div class="loader mx-auto"></div><p class="mt-4 text-gray-400">Searching embedding space...</p></div>';

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ query })
            });
            const data = await res.json();
            
            document.getElementById('search-stats').classList.remove('hidden');
            document.getElementById('search-time').textContent = data.time_ms;

            searchResults.innerHTML = '';
            if(data.results.length === 0) {
                searchResults.innerHTML = '<p class="col-span-full text-center text-gray-400">No results found.</p>';
            } else {
                data.results.forEach(p => {
                    searchResults.appendChild(createProductCard(p, null, false, p.similarity_score));
                });
            }

            renderSearchTsne(data.query_coords);

        } catch (e) {
            console.error(e);
            searchResults.innerHTML = '<p class="col-span-full text-center text-red-500">Search failed.</p>';
        } finally {
            searchBtn.textContent = 'Search';
            searchBtn.disabled = false;
        }
    }

    function renderSearchTsne(queryCoords) {
        // Base products
        const trace1 = {
            x: products.map(d => d.tsne[0]),
            y: products.map(d => d.tsne[1]),
            mode: 'markers',
            type: 'scatter',
            name: 'Products',
            text: products.map(d => d.name),
            marker: { size: 6, color: '#374151' },
            hoverinfo: 'text'
        };

        // Query
        const trace2 = {
            x: [queryCoords[0]],
            y: [queryCoords[1]],
            mode: 'markers',
            type: 'scatter',
            name: 'Search Query',
            text: ['Your Query'],
            marker: { size: 14, color: '#4F46E5', symbol: 'star' }
        };

        const layout = {
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            font: { color: '#9CA3AF' },
            xaxis: { showgrid: false, zeroline: false, showticklabels: false },
            yaxis: { showgrid: false, zeroline: false, showticklabels: false },
            margin: { l: 0, r: 0, b: 0, t: 0 },
            showlegend: false
        };

        Plotly.newPlot('search-tsne-plot', [trace1, trace2], layout, {responsive: true});
    }

    // Initialize
    loadCatalog();
});
