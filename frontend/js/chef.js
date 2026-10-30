let chefReady = false;

async function startChefDashboard() {
    chefReady = await requireRole("chef");

    if (!chefReady) return;

    await loadChefOrders();

    // Refresh assigned orders every 10 seconds.
    setInterval(loadChefOrders, 10000);
}

startChefDashboard();


async function loadChefOrders() {
    if (!chefReady) return;

    try {
        const orders = await api("/chef/orders");

        if (!orders.length) {
            el("orders").innerHTML =
                '<p class="empty">No assigned cooking orders right now.</p>';
            return;
        }

        el("orders").innerHTML = orders.map(order => `
            <article class="panel">
                <span class="pill">${esc(order.status)}</span>

                <h2>Order #${order.id}</h2>

                <p><strong>Customer:</strong> ${esc(order.customer_name)}</p>

                <p><strong>Items:</strong></p>

                ${order.items.map(item => `
                    <div class="table-row">
                        <span>${esc(item.dish_name)}</span>
                        <strong>× ${item.quantity}</strong>
                    </div>
                `).join("")}

                <p class="notice">
                    Cooking failures: ${order.cook_failures}/2
                </p>

                <div class="actions">
                    <button class="btn"
                        onclick="updateCooking(${order.id}, true)">
                        Mark Ready
                    </button>

                    <button class="btn btn-secondary"
                        onclick="updateCooking(${order.id}, false)">
                        Report Failure
                    </button>
                </div>
            </article>
        `).join("");

    } catch (error) {
        showError("chefMessage", error);
    }
}


async function updateCooking(orderId, success) {
    let reason = null;

    if (!success) {
        reason = prompt("Enter the cooking failure reason:");

        if (!reason || !reason.trim()) return;
    }

    try {
        await api(`/chef/orders/${orderId}/cook`, {
            method: "POST",
            body: JSON.stringify({
                success: success,
                failure_reason: reason
            })
        });

        el("chefMessage").textContent = success
            ? "Order marked as ready."
            : "Cooking failure recorded.";

        await loadChefOrders();

    } catch (error) {
        alert(error.message);
    }
}