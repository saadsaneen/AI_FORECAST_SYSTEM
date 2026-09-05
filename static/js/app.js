/**
 * Food Demand Forecasting System - Shared Client JavaScript
 */

// Helper to show alert messages in styled alert boxes
function showAlert(containerId, message, type = "error") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const bgColor = type === "error" ? "bg-red-50 text-red-700 border-red-200" : "bg-emerald-50 text-emerald-700 border-emerald-200";
    const icon = type === "error" ? "⚠️" : "✅";

    container.className = `p-4 mb-4 text-sm border rounded-xl flex items-center gap-3 ${bgColor}`;
    container.innerHTML = `
        <span class="text-base">${icon}</span>
        <div class="font-medium flex-1">${message}</div>
    `;
    container.classList.remove("hidden");
}

function hideAlert(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add("hidden");
    }
}

// Helper to toggle button loading state
function setButtonLoading(buttonEl, isLoading, defaultText) {
    if (!buttonEl) return;
    if (isLoading) {
        buttonEl.disabled = true;
        buttonEl.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
        `;
    } else {
        buttonEl.disabled = false;
        buttonEl.innerHTML = defaultText;
    }
}

// Session checking API function
async function fetchSession() {
    try {
        const res = await fetch("/session-check");
        if (!res.ok) return { logged_in: false };
        return await res.json();
    } catch (e) {
        console.error("Session check error:", e);
        return { logged_in: false };
    }
}

// Logout function
async function logoutUser() {
    try {
        await fetch("/logout");
        window.location.href = "/login";
    } catch (e) {
        console.error("Logout error:", e);
        window.location.href = "/login";
    }
}

// Page Initialization Logic
document.addEventListener("DOMContentLoaded", () => {
    const pageId = document.body.dataset.page;

    if (pageId === "login") {
        setupLoginForm();
    } else if (pageId === "register") {
        setupRegisterForm();
    } else if (pageId === "dashboard") {
        setupDashboardPage();
    } else if (pageId === "food-menu") {
        setupFoodMenuPage();
    }
});

// --- Login Page Logic ---
function setupLoginForm() {
    const form = document.getElementById("login-form");
    const submitBtn = document.getElementById("login-btn");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert("alert-container");
        setButtonLoading(submitBtn, true, "Sign In");

        const username = document.getElementById("name").value.trim();
        const password = document.getElementById("password").value.trim();

        if (!username || !password) {
            showAlert("alert-container", "Please enter both username and password.", "error");
            setButtonLoading(submitBtn, false, "Sign In");
            return;
        }

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: username, password: password })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showAlert("alert-container", "Login successful! Redirecting...", "success");
                setTimeout(() => {
                    window.location.href = "/dashboard";
                }, 400);
            } else {
                showAlert("alert-container", data.error || "Invalid username or password", "error");
                setButtonLoading(submitBtn, false, "Sign In");
            }
        } catch (err) {
            showAlert("alert-container", "Network error. Please try again.", "error");
            setButtonLoading(submitBtn, false, "Sign In");
        }
    });
}

// --- Register Page Logic ---
function setupRegisterForm() {
    const form = document.getElementById("register-form");
    const submitBtn = document.getElementById("register-btn");

    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert("alert-container");
        setButtonLoading(submitBtn, true, "Create Account");

        const username = document.getElementById("name").value.trim();
        const password = document.getElementById("password").value.trim();

        if (!username || !password) {
            showAlert("alert-container", "Please fill in all fields.", "error");
            setButtonLoading(submitBtn, false, "Create Account");
            return;
        }

        try {
            // SECURITY NOTE: Only name and password are sent. No role parameter is included.
            const response = await fetch("/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: username, password: password })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                showAlert("alert-container", "Account created successfully! Redirecting to login...", "success");
                setTimeout(() => {
                    window.location.href = "/login";
                }, 1000);
            } else {
                showAlert("alert-container", data.error || "Registration failed.", "error");
                setButtonLoading(submitBtn, false, "Create Account");
            }
        } catch (err) {
            showAlert("alert-container", "Network error. Please try again.", "error");
            setButtonLoading(submitBtn, false, "Create Account");
        }
    });
}

// --- Dashboard Page Logic ---
async function setupDashboardPage() {
    const sessionData = await fetchSession();
    if (!sessionData.logged_in) {
        window.location.href = "/login";
        return;
    }

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", logoutUser);
    }
}

// --- Food Menu Page Logic ---
async function setupFoodMenuPage() {
    const sessionData = await fetchSession();
    if (!sessionData.logged_in) {
        window.location.href = "/login";
        return;
    }
    if (sessionData.user.role !== "owner") {
        window.location.href = "/dashboard";
        return;
    }

    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", logoutUser);
    }

    // Load Items List
    await loadFoodItems();

    // Setup Add Item Form
    const addItemForm = document.getElementById("add-item-form");
    const addBtn = document.getElementById("add-item-btn");

    if (addItemForm) {
        addItemForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            hideAlert("alert-container");
            setButtonLoading(addBtn, true, "Add Item");

            const itemName = document.getElementById("item_name").value.trim();
            const unit = document.getElementById("unit").value.trim();
            const priceInput = document.getElementById("price");
            const price = priceInput ? parseFloat(priceInput.value) : 0;

            if (!itemName) {
                showAlert("alert-container", "Please enter an item name.", "error");
                setButtonLoading(addBtn, false, "Add Item");
                return;
            }

            if (isNaN(price) || price < 0) {
                showAlert("alert-container", "Please enter a valid non-negative price.", "error");
                setButtonLoading(addBtn, false, "Add Item");
                return;
            }

            try {
                const response = await fetch("/items", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ item_name: itemName, unit: unit, price: price })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    showAlert("alert-container", data.message || "Item added successfully", "success");
                    document.getElementById("item_name").value = "";
                    document.getElementById("unit").value = "pieces";
                    if (priceInput) priceInput.value = "";
                    await loadFoodItems();
                } else {
                    showAlert("alert-container", data.error || "Failed to add item.", "error");
                }
            } catch (err) {
                showAlert("alert-container", "Network error. Failed to add item.", "error");
            } finally {
                setButtonLoading(addBtn, false, "Add Item");
            }
        });
    }
}

// Load food items into table/grid
async function loadFoodItems() {
    const listContainer = document.getElementById("items-list");
    const countBadge = document.getElementById("item-count");
    if (!listContainer) return;

    try {
        const response = await fetch("/items");
        if (response.status === 403) {
            showAlert("alert-container", "Access Denied: Owner role required.", "error");
            setTimeout(() => { window.location.href = "/dashboard"; }, 1500);
            return;
        }

        const data = await response.json();
        const items = data.items || [];

        if (countBadge) {
            countBadge.textContent = items.length;
        }

        if (items.length === 0) {
            listContainer.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-8 text-center text-slate-500">
                        No food items found in the menu. Add your first item above!
                    </td>
                </tr>
            `;
            return;
        }

        listContainer.innerHTML = items.map((item, index) => `
            <tr class="hover:bg-slate-50 transition-colors border-b border-slate-100">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">#${index + 1}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-800">
                    <span class="inline-flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                        ${escapeHtml(item.item_name)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700">
                        ${escapeHtml(item.unit)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-emerald-700">
                    ₹${Number(item.price || 0).toFixed(2)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button onclick="deleteFoodItem(${item.item_id}, '${escapeHtml(item.item_name)}')" 
                            class="inline-flex items-center gap-1.5 text-xs font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-red-200 transition">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        Delete
                    </button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Error loading items:", err);
        listContainer.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-red-600">
                    Error loading menu items. Please refresh the page.
                </td>
            </tr>
        `;
    }
}

// Delete item handler
async function deleteFoodItem(itemId, itemName) {
    if (!confirm(`Are you sure you want to delete '${itemName}' from the food menu?`)) {
        return;
    }

    hideAlert("alert-container");

    try {
        const response = await fetch(`/items/${itemId}`, {
            method: "DELETE"
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showAlert("alert-container", `Item '${itemName}' removed successfully.`, "success");
            await loadFoodItems();
        } else {
            showAlert("alert-container", data.error || "Failed to delete item.", "error");
        }
    } catch (err) {
        showAlert("alert-container", "Network error while deleting item.", "error");
    }
}

// Utility to escape HTML strings to prevent XSS
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
