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
            
            if(target === 'task4') {
                loadOrdersList();
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
            
            // Hover cart overlay button
            const hoverCartBtn = document.createElement('button');
            hoverCartBtn.className = 'product-card-hover-cart';
            hoverCartBtn.innerHTML = `
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
            `;
            hoverCartBtn.title = 'Add to Cart';
            hoverCartBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                addToCart(product);
            });
            div.appendChild(hoverCartBtn);
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
        
        // Add To Cart and Buy Now buttons for selected item
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'mt-3 flex gap-2 w-full';
        
        const addToCartBtn = document.createElement('button');
        addToCartBtn.className = 'flex-1 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center';
        addToCartBtn.innerHTML = `
            <svg class="w-4 h-4 mr-1 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path>
            </svg> Add to Cart
        `;
        addToCartBtn.addEventListener('click', () => addToCart(product));
        
        const buyNowBtn = document.createElement('button');
        buyNowBtn.className = 'flex-1 py-2 bg-gradient-to-r from-primary to-indigo-600 hover:from-indigo-600 hover:to-primary text-white text-xs font-semibold rounded-lg transition-all flex items-center justify-center';
        buyNowBtn.innerHTML = 'Buy Now';
        buyNowBtn.addEventListener('click', () => {
            addToCart(product);
            openCartDrawer();
        });
        
        actionsDiv.appendChild(addToCartBtn);
        actionsDiv.appendChild(buyNowBtn);
        targetProductContainer.appendChild(actionsDiv);
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

    // --- Shopping Cart & Payment Simulator & Tracking Logic ---
    let cart = JSON.parse(localStorage.getItem('clip_blip_cart')) || [];
    
    function saveCart() {
        localStorage.setItem('clip_blip_cart', JSON.stringify(cart));
        updateCartBadge();
    }
    
    function updateCartBadge() {
        const badge = document.getElementById('cart-badge');
        const totalCount = cart.reduce((sum, item) => sum + item.quantity, 0);
        if (totalCount > 0) {
            badge.textContent = totalCount;
            badge.classList.remove('opacity-0');
            badge.classList.add('opacity-100');
        } else {
            badge.classList.add('opacity-0');
            badge.classList.remove('opacity-100');
        }
    }
    
    function addToCart(product, qty = 1) {
        const existing = cart.find(item => item.id === product.id);
        if (existing) {
            existing.quantity += qty;
        } else {
            cart.push({
                id: product.id,
                name: product.name,
                price: product.price,
                image_url: product.image_url,
                category: product.category,
                subcategory: product.subcategory,
                quantity: qty
            });
        }
        saveCart();
        updateCartUI();
        showToast(`${product.name} added to cart!`);
    }
    
    function showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-4 left-4 bg-emerald-600 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow-lg z-[100] transition-opacity duration-300 opacity-0';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.classList.remove('opacity-0');
        }, 50);
        setTimeout(() => {
            toast.classList.add('opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    function removeFromCart(id) {
        cart = cart.filter(item => item.id !== id);
        saveCart();
        updateCartUI();
    }
    
    function updateQuantity(id, delta) {
        const item = cart.find(i => i.id === id);
        if (item) {
            item.quantity += delta;
            if (item.quantity <= 0) {
                removeFromCart(id);
                return;
            }
        }
        saveCart();
        updateCartUI();
    }
    
    function updateCartUI() {
        const container = document.getElementById('cart-items-container');
        if (cart.length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-500">
                    <svg class="w-16 h-16 mx-auto mb-4 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
                    <p>Your cart is empty</p>
                </div>
            `;
            document.getElementById('cart-subtotal').textContent = '₹0.00';
            document.getElementById('cart-tax').textContent = '₹0.00';
            document.getElementById('cart-delivery').textContent = '₹0.00';
            document.getElementById('cart-total').textContent = '₹0.00';
            return;
        }
        
        container.innerHTML = '';
        let subtotal = 0;
        cart.forEach(item => {
            subtotal += item.price * item.quantity;
            const div = document.createElement('div');
            div.className = 'flex items-center space-x-4 bg-card/60 p-3 rounded-xl border border-gray-800/80 mb-2';
            div.innerHTML = `
                <img src="${item.image_url}" class="w-12 h-12 object-cover rounded-lg border border-gray-800 shrink-0" alt="${item.name}">
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-semibold text-white truncate">${item.name}</div>
                    <div class="text-xs text-gray-400">₹${item.price.toFixed(2)} each</div>
                </div>
                <div class="flex items-center space-x-2 shrink-0">
                    <button class="w-6 h-6 bg-gray-800 hover:bg-gray-700 text-white rounded flex items-center justify-center text-xs font-bold" onclick="updateQuantity('${item.id}', -1)">-</button>
                    <span class="text-xs font-bold text-gray-200 w-4 text-center">${item.quantity}</span>
                    <button class="w-6 h-6 bg-gray-800 hover:bg-gray-700 text-white rounded flex items-center justify-center text-xs font-bold" onclick="updateQuantity('${item.id}', 1)">+</button>
                </div>
                <button class="text-gray-500 hover:text-red-500 transition-colors p-1 shrink-0" onclick="removeFromCart('${item.id}')">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L4 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            `;
            container.appendChild(div);
        });
        
        const tax = subtotal * 0.18;
        const delivery = subtotal > 1000 ? 0 : 80;
        const total = subtotal + tax + delivery;
        
        document.getElementById('cart-subtotal').textContent = `₹${subtotal.toFixed(2)}`;
        document.getElementById('cart-tax').textContent = `₹${tax.toFixed(2)}`;
        document.getElementById('cart-delivery').textContent = delivery === 0 ? 'Free' : `₹${delivery.toFixed(2)}`;
        document.getElementById('cart-total').textContent = `₹${total.toFixed(2)}`;
    }
    
    // Bind to window so global inline onclicks work
    window.updateQuantity = updateQuantity;
    window.removeFromCart = removeFromCart;
    window.addToCart = addToCart;

    // Toggle Drawer Elements
    const cartToggleBtn = document.getElementById('cart-toggle-btn');
    const cartCloseBtn = document.getElementById('cart-close-btn');
    const cartDrawerOverlay = document.getElementById('cart-drawer-overlay');
    const cartDrawer = document.getElementById('cart-drawer');
    
    function openCartDrawer() {
        cartDrawerOverlay.classList.remove('hidden');
        setTimeout(() => {
            cartDrawerOverlay.classList.add('active');
            cartDrawer.classList.add('active');
            document.body.classList.add('modal-open');
        }, 50);
    }
    
    function closeCartDrawer() {
        cartDrawerOverlay.classList.remove('active');
        cartDrawer.classList.remove('active');
        document.body.classList.remove('modal-open');
        setTimeout(() => {
            cartDrawerOverlay.classList.add('hidden');
        }, 300);
    }
    
    cartToggleBtn.addEventListener('click', openCartDrawer);
    cartCloseBtn.addEventListener('click', closeCartDrawer);
    cartDrawerOverlay.addEventListener('click', (e) => {
        if (e.target === cartDrawerOverlay) closeCartDrawer();
    });

    // Checkout Modal Elements
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkoutModal = document.getElementById('checkout-modal');
    const checkoutCloseBtn = document.getElementById('checkout-close-btn');
    const checkoutCancelBtn = document.getElementById('checkout-cancel-btn');
    const placeOrderBtn = document.getElementById('place-order-btn');
    
    checkoutBtn.addEventListener('click', () => {
        if (cart.length === 0) {
            alert('Your cart is empty');
            return;
        }
        closeCartDrawer();
        let subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
        let tax = subtotal * 0.18;
        let delivery = subtotal > 1000 ? 0 : 80;
        let total = subtotal + tax + delivery;
        document.getElementById('checkout-total-val').textContent = total.toFixed(2);
        
        checkoutModal.classList.remove('hidden');
        setTimeout(() => {
            checkoutModal.classList.add('active');
            document.body.classList.add('modal-open');
        }, 50);
    });
    
    function closeCheckoutModal() {
        checkoutModal.classList.remove('active');
        document.body.classList.remove('modal-open');
        setTimeout(() => {
            checkoutModal.classList.add('hidden');
        }, 300);
    }
    
    checkoutCloseBtn.addEventListener('click', closeCheckoutModal);
    checkoutCancelBtn.addEventListener('click', closeCheckoutModal);

    placeOrderBtn.addEventListener('click', async () => {
        const name = document.getElementById('ship-name').value.trim();
        const phone = document.getElementById('ship-phone').value.trim();
        const address = document.getElementById('ship-address').value.trim();
        const city = document.getElementById('ship-city').value.trim();
        const zip = document.getElementById('ship-zip').value.trim();
        
        if (!name || !phone || !address || !city || !zip) {
            alert('Please fill out all shipping details.');
            return;
        }
        
        const paymentMethod = document.querySelector('input[name="payment_method"]:checked').value;
        
        let subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
        let tax = subtotal * 0.18;
        let delivery = subtotal > 1000 ? 0 : 80;
        let total = subtotal + tax + delivery;
        
        const shippingAddress = { name, phone, address, city, zip };
        
        if (paymentMethod === 'online') {
            closeCheckoutModal();
            
            // Create order on backend first to retrieve Razorpay details
            try {
                const res = await fetch('/api/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        items: cart,
                        shipping_address: shippingAddress,
                        payment_method: 'online',
                        total_amount: total
                    })
                });
                const result = await res.json();
                if (!result.success) {
                    alert('Order creation failed: ' + result.error);
                    return;
                }
                
                // If backend created a simulated/mock Order ID, run the custom visual simulator
                if (result.order.razorpay_order_id.startsWith('order_mock_')) {
                    console.log("Using custom Razorpay simulator overlay...");
                    openRazorpayModal(total, shippingAddress, result.order.id);
                    return;
                }
                
                // Otherwise, open the official Razorpay Checkout widget
                console.log("Opening official Razorpay checkout...");
                const options = {
                    "key": result.order.razorpay_key_id,
                    "amount": Math.round(total * 100),
                    "currency": "INR",
                    "name": "CLIP-BLIP Shopping Store",
                    "description": `Payment for Order ${result.order.id}`,
                    "image": "/static/images/logo.jpg",
                    "order_id": result.order.razorpay_order_id,
                    "handler": async function (response) {
                        try {
                            const verifyRes = await fetch('/api/orders/verify', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    order_id: result.order.id,
                                    razorpay_payment_id: response.razorpay_payment_id,
                                    razorpay_signature: response.razorpay_signature
                                })
                            });
                            const verifyResult = await verifyRes.json();
                            if (verifyResult.success) {
                                cart = [];
                                saveCart();
                                updateCartUI();
                                
                                const ordersTab = document.querySelector('button[data-target="task4"]');
                                ordersTab.click();
                                
                                await loadOrdersList();
                                selectOrderToTrack(result.order.id);
                                showToast("Payment verified! Order is placed successfully.");
                            } else {
                                alert('Payment verification failed: ' + verifyResult.error);
                            }
                        } catch (e) {
                            console.error(e);
                            alert('Error verifying payment.');
                        }
                    },
                    "prefill": {
                        "name": shippingAddress.name,
                        "contact": shippingAddress.phone,
                        "email": `${shippingAddress.name.toLowerCase().replace(/\s+/g, '')}@example.com`
                    },
                    "theme": {
                        "color": "#4F46E5"
                    }
                };
                
                const rzp = new Razorpay(options);
                rzp.on('payment.failed', function (response){
                    alert("Payment Failed: " + response.error.description);
                });
                rzp.open();
                
            } catch (e) {
                console.error(e);
                alert('Error creating payment: ' + e.message);
            }
        } else {
            closeCheckoutModal();
            await submitOrder(shippingAddress, 'cod', 'Pending', total);
        }
    });

    // Razorpay Simulator Modal Elements (Fallback)
    const rzpModal = document.getElementById('razorpay-modal');
    const rzpSubmitBtn = document.getElementById('rzp-submit-btn');
    const rzpCancelBtn = document.getElementById('rzp-cancel-btn');
    const rzpOtpModal = document.getElementById('rzp-otp-modal');
    const rzpOtpSubmitBtn = document.getElementById('rzp-otp-submit-btn');
    const rzpOtpInput = document.getElementById('rzp-otp-input');
    
    const rzpCardNumInput = document.getElementById('rzp-card-number');
    if (rzpCardNumInput) {
        rzpCardNumInput.addEventListener('input', (e) => {
            let val = e.target.value.replace(/\D/g, '');
            let formatted = '';
            for (let i = 0; i < val.length; i++) {
                if (i > 0 && i % 4 === 0) formatted += ' ';
                formatted += val[i];
            }
            e.target.value = formatted;
        });
    }
    
    const rzpCardExpiryInput = document.getElementById('rzp-card-expiry');
    if (rzpCardExpiryInput) {
        rzpCardExpiryInput.addEventListener('input', (e) => {
            let val = e.target.value.replace(/\D/g, '');
            if (val.length >= 2) {
                e.target.value = val.slice(0, 2) + '/' + val.slice(2, 4);
            } else {
                e.target.value = val;
            }
        });
    }
    
    const rzpTabs = document.querySelectorAll('.rzp-tab');
    const rzpViews = document.querySelectorAll('.rzp-view');
    
    rzpTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            rzpTabs.forEach(t => {
                t.classList.remove('active', 'text-[#2e5cd5]', 'border-l-4', 'border-l-[#2e5cd5]');
                t.classList.add('text-gray-600');
            });
            tab.classList.add('active', 'text-[#2e5cd5]', 'border-l-4', 'border-l-[#2e5cd5]');
            tab.classList.remove('text-gray-600');
            
            const target = tab.getAttribute('data-rzp-target');
            rzpViews.forEach(v => {
                if (v.id === target) v.classList.remove('hidden');
                else v.classList.add('hidden');
            });
        });
    });
    
    let rzpTotalAmount = 0;
    let rzpShippingAddress = null;
    let rzpOrderId = null; // internal order reference
    
    function openRazorpayModal(amount, shippingAddress, internalOrderId) {
        rzpTotalAmount = amount;
        rzpShippingAddress = shippingAddress;
        rzpOrderId = internalOrderId;
        document.getElementById('rzp-amount').textContent = `₹${amount.toFixed(2)}`;
        document.getElementById('rzp-email-phone').textContent = `${shippingAddress.name.toLowerCase().replace(/\s+/g, '')}@example.com | ${shippingAddress.phone}`;
        
        rzpModal.classList.remove('hidden');
        setTimeout(() => {
            rzpModal.classList.add('active');
            document.body.classList.add('modal-open');
        }, 50);
    }
    
    function closeRazorpayModal() {
        rzpModal.classList.remove('active');
        document.body.classList.remove('modal-open');
        setTimeout(() => {
            rzpModal.classList.add('hidden');
        }, 300);
    }
    
    if (rzpCancelBtn) rzpCancelBtn.addEventListener('click', closeRazorpayModal);
    
    if (rzpSubmitBtn) {
        rzpSubmitBtn.addEventListener('click', () => {
            const activeTab = document.querySelector('.rzp-tab.active').getAttribute('data-rzp-target');
            if (activeTab === 'rzp-card') {
                const num = document.getElementById('rzp-card-number').value.replace(/\s+/g, '');
                const exp = document.getElementById('rzp-card-expiry').value;
                const cvv = document.getElementById('rzp-card-cvv').value;
                const name = document.getElementById('rzp-card-name').value;
                
                if (num.length < 15 || exp.length < 5 || cvv.length < 3 || !name) {
                    alert('Please enter valid Card details.');
                    return;
                }
            } else if (activeTab === 'rzp-upi') {
                const upiId = document.getElementById('rzp-upi-id').value;
                if (!upiId.includes('@')) {
                    alert('Please enter a valid UPI ID (e.g. user@bank).');
                    return;
                }
            }
            
            closeRazorpayModal();
            openOtpModal();
        });
    }
    
    function openOtpModal() {
        rzpOtpModal.classList.remove('hidden');
        document.getElementById('rzp-processing-screen').classList.remove('hidden');
        document.getElementById('rzp-otp-screen').classList.add('hidden');
        document.getElementById('rzp-success-screen').classList.add('hidden');
        
        setTimeout(() => {
            rzpOtpModal.classList.add('active');
            document.body.classList.add('modal-open');
        }, 50);
        
        setTimeout(() => {
            document.getElementById('rzp-processing-screen').classList.add('hidden');
            document.getElementById('rzp-otp-screen').classList.remove('hidden');
            rzpOtpInput.value = '';
            rzpOtpInput.focus();
        }, 2000);
    }
    
    if (rzpOtpSubmitBtn) {
        rzpOtpSubmitBtn.addEventListener('click', () => {
            const otp = rzpOtpInput.value.trim();
            if (otp.length !== 6) {
                alert('Please enter a valid 6-digit OTP.');
                return;
            }
            
            document.getElementById('rzp-otp-screen').classList.add('hidden');
            document.getElementById('rzp-processing-screen').classList.remove('hidden');
            
            setTimeout(() => {
                document.getElementById('rzp-processing-screen').classList.add('hidden');
                document.getElementById('rzp-success-screen').classList.remove('hidden');
                
                setTimeout(async () => {
                    rzpOtpModal.classList.remove('active');
                    document.body.classList.remove('modal-open');
                    setTimeout(() => {
                        rzpOtpModal.classList.add('hidden');
                    }, 300);
                    
                    // Verify the payment
                    try {
                        const verifyRes = await fetch('/api/orders/verify', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                order_id: rzpOrderId,
                                razorpay_payment_id: "pay_sim_" + Date.now(),
                                razorpay_signature: "sig_sim_" + Date.now()
                            })
                        });
                        const verifyResult = await verifyRes.json();
                        if (verifyResult.success) {
                            cart = [];
                            saveCart();
                            updateCartUI();
                            
                            const ordersTab = document.querySelector('button[data-target="task4"]');
                            ordersTab.click();
                            
                            await loadOrdersList();
                            selectOrderToTrack(rzpOrderId);
                            showToast("Simulated payment verified successfully!");
                        } else {
                            alert('Simulated Verification Failed');
                        }
                    } catch (e) {
                        console.error(e);
                        alert('Error verifying payment.');
                    }
                }, 2000);
            }, 1500);
        });
    }

    async function submitOrder(shippingAddress, paymentMethod, paymentStatus, totalAmount) {
        try {
            const res = await fetch('/api/orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    items: cart,
                    shipping_address: shippingAddress,
                    payment_method: paymentMethod,
                    payment_status: paymentStatus,
                    total_amount: totalAmount
                })
            });
            const result = await res.json();
            if (result.success) {
                cart = [];
                saveCart();
                updateCartUI();
                
                const ordersTab = document.querySelector('button[data-target="task4"]');
                ordersTab.click();
                
                await loadOrdersList();
                selectOrderToTrack(result.order.id);
            } else {
                alert('Failed to place order: ' + result.error);
            }
        } catch (e) {
            console.error(e);
            alert('Error placing order.');
        }
    }

    // --- Order Tracking Logic ---
    let activeTrackingTimer = null;
    let activeTrackingOrderId = null;
    
    async function loadOrdersList() {
        const listContainer = document.getElementById('orders-list');
        try {
            const res = await fetch('/api/orders');
            const orders = await res.json();
            
            if (orders.length === 0) {
                listContainer.innerHTML = `
                    <div class="p-4 bg-card rounded-lg text-center text-gray-500 border border-gray-800">
                        No orders placed yet. Add items to cart and check out.
                    </div>
                `;
                return;
            }
            
            listContainer.innerHTML = '';
            orders.forEach(order => {
                const div = document.createElement('div');
                div.className = `p-4 rounded-xl border border-gray-800 hover:border-primary transition-all cursor-pointer bg-card/40 mb-3 ${activeTrackingOrderId === order.id ? 'border-primary ring-1 ring-primary/30' : ''}`;
                
                let badgeColor = 'bg-gray-800 text-gray-400';
                if (order.status === 'Delivered') badgeColor = 'bg-emerald-500/20 text-emerald-400';
                else if (order.status === 'Out for Delivery') badgeColor = 'bg-amber-500/20 text-amber-400';
                else if (order.status === 'Shipped') badgeColor = 'bg-primary/20 text-primary';
                else if (order.status === 'Preparing & Packaging') badgeColor = 'bg-indigo-500/20 text-indigo-400';
                
                div.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <span class="text-xs font-mono font-bold text-gray-400">${order.id}</span>
                        <span class="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${badgeColor}">${order.status}</span>
                    </div>
                    <div class="text-xs text-gray-300">${order.items.length} item(s) • ₹${order.total_amount.toFixed(2)}</div>
                    <div class="text-[10px] text-gray-500 mt-2">Placed: ${new Date(order.created_at * 1000).toLocaleString()}</div>
                `;
                
                div.addEventListener('click', () => {
                    document.querySelectorAll('#orders-list > div').forEach(c => c.classList.remove('border-primary', 'ring-1', 'ring-primary/30'));
                    div.classList.add('border-primary', 'ring-1', 'ring-primary/30');
                    selectOrderToTrack(order.id);
                });
                listContainer.appendChild(div);
            });
        } catch (e) {
            console.error(e);
            listContainer.innerHTML = '<div class="p-4 text-center text-red-500">Failed to load order history.</div>';
        }
    }
    
    async function selectOrderToTrack(orderId) {
        activeTrackingOrderId = orderId;
        document.getElementById('tracking-welcome-container').classList.add('hidden');
        document.getElementById('tracking-details-container').classList.remove('hidden');
        
        if (activeTrackingTimer) clearInterval(activeTrackingTimer);
        
        await updateTrackingDisplay(orderId);
        
        activeTrackingTimer = setInterval(() => {
            updateTrackingDisplay(orderId);
        }, 3000);
    }
    
    async function updateTrackingDisplay(orderId) {
        if (activeTrackingOrderId !== orderId) return;
        try {
            const res = await fetch(`/api/orders/${orderId}`);
            if (res.status === 404) {
                clearInterval(activeTrackingTimer);
                return;
            }
            const order = await res.json();
            
            document.getElementById('track-order-id').textContent = order.id;
            document.getElementById('track-payment-method').textContent = order.payment_method.toUpperCase();
            document.getElementById('track-total-price').textContent = `₹${order.total_amount.toFixed(2)}`;
            document.getElementById('track-eta').textContent = `Status: ${order.tracking.status} (${order.tracking.eta})`;
            
            const sa = order.shipping_address;
            document.getElementById('track-shipping-address').innerHTML = `
                ${sa.name}<br>
                ${sa.address}, ${sa.city} - ${sa.zip}<br>
                Ph: ${sa.phone}
            `;
            
            document.getElementById('track-agent-name').textContent = order.tracking.delivery_agent.name;
            document.getElementById('track-agent-vehicle').textContent = order.tracking.delivery_agent.vehicle;
            
            const itemsContainer = document.getElementById('tracking-items');
            itemsContainer.innerHTML = '';
            order.items.forEach(item => {
                const itemDiv = document.createElement('div');
                itemDiv.className = 'flex justify-between text-xs text-gray-300';
                itemDiv.innerHTML = `
                    <span class="truncate pr-2">${item.name} <span class="text-gray-500">x${item.quantity}</span></span>
                    <span class="font-semibold shrink-0">₹${(item.price * item.quantity).toFixed(2)}</span>
                `;
                itemsContainer.appendChild(itemDiv);
            });
            
            const stepper = document.getElementById('tracking-stepper');
            stepper.innerHTML = '';
            order.tracking.stages.forEach(stage => {
                const div = document.createElement('div');
                div.className = `stepper-item ${stage.status}`;
                
                let descColor = 'text-gray-500';
                let nameColor = 'text-gray-400 font-semibold';
                if (stage.status === 'completed') {
                    descColor = 'text-gray-400';
                    nameColor = 'text-emerald-400 font-bold';
                } else if (stage.status === 'active') {
                    descColor = 'text-primary font-medium';
                    nameColor = 'text-white font-extrabold animate-pulse';
                }
                
                div.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div class="${nameColor} text-sm">${stage.name}</div>
                        <div class="text-[10px] text-gray-500 font-mono">${stage.time_str}</div>
                    </div>
                    <p class="${descColor} text-xs mt-1 leading-tight">${stage.desc}</p>
                `;
                stepper.appendChild(div);
            });
            
            const elapsed = Math.min(120, order.tracking.elapsed);
            const percent = elapsed / 120;
            
            const progressPath = document.getElementById('route-path-progress');
            if (progressPath) {
                const totalLength = progressPath.getTotalLength() || 1000;
                const drawLength = totalLength * percent;
                progressPath.style.strokeDasharray = `${drawLength} ${totalLength}`;
                
                const point = progressPath.getPointAtLength(drawLength);
                const truckIcon = document.getElementById('truck-delivery-icon');
                if (truckIcon) {
                    truckIcon.setAttribute('transform', `translate(${point.x}, ${point.y})`);
                }
            }
            
            const isDelivered = order.tracking.status === 'Delivered';
            document.getElementById('btn-speed-up').disabled = isDelivered;
            document.getElementById('btn-advance-status').disabled = isDelivered;
            
        } catch (e) {
            console.error(e);
        }
    }
    
    document.getElementById('btn-speed-up').addEventListener('click', async () => {
        if (!activeTrackingOrderId) return;
        try {
            await fetch(`/api/orders/${activeTrackingOrderId}/advance`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ multiplier: 12.0 })
            });
            showToast("Simulation speed boosted! ETA shrinking.");
            updateTrackingDisplay(activeTrackingOrderId);
        } catch (e) {
            console.error(e);
        }
    });
    
    document.getElementById('btn-advance-status').addEventListener('click', async () => {
        if (!activeTrackingOrderId) return;
        try {
            await fetch(`/api/orders/${activeTrackingOrderId}/advance`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'Delivered' })
            });
            showToast("Order delivered instantly!");
            updateTrackingDisplay(activeTrackingOrderId);
            loadOrdersList();
        } catch (e) {
            console.error(e);
        }
    });

    // Initialize UI
    updateCartBadge();
    updateCartUI();
    loadCatalog();
});
