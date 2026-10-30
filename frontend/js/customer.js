let sessionId = localStorage.getItem("bk_session");

if (!sessionId) {
    sessionId = crypto.randomUUID
        ? crypto.randomUUID()
        : String(Date.now()) + Math.random();

    localStorage.setItem("bk_session", sessionId);
}

let pendingItems = [];

function addMessage(message, className) {
    const paragraph = document.createElement("p");
    paragraph.className = className;
    paragraph.textContent = message;

    el("chatLog").appendChild(paragraph);
    el("chatLog").scrollTop = el("chatLog").scrollHeight;
}


// Load menu from backend

async function loadMenu() {
    const menu = document.getElementById("menu");

    try {
        const items = await api("/customer/menu");

        const foodImages = {
            pizza: "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=600",
            burger: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600",
            pasta: "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?w=600",
            biryani: "https://images.unsplash.com/photo-1563379091339-03246963d96c?w=600",
            salad: "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=600"
        };

        if (!items || items.length === 0) {
            menu.innerHTML = "<p class='empty'>No menu items available.</p>";
            return;
        }

        menu.innerHTML = items.map(item => {
            const name = item.dish_name || item.name || "Food Item";

            const key = name.toLowerCase();
            const image = item.image_url ||
                Object.entries(foodImages).find(([food]) =>
                    key.includes(food)
                )?.[1] ||
                "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600";

            return `
                <article class="dish">
                    <img
                        src="${esc(image)}"
                        alt="${esc(name)}"
                        loading="lazy"
                    >

                    <div class="dish-content">
                        <h3>${esc(name)}</h3>
                        <p>${esc(item.description || "Freshly prepared with love.")}</p>
                        <strong>₹${Number(item.price || 0).toFixed(2)}</strong>
                    </div>
                </article>
            `;
        }).join("");

    } catch (error) {
        menu.innerHTML = "<p class='empty'>Unable to load menu. Please try again.</p>";
        console.error(error);
    }
}
// Send message to AI agent

el("chatForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const message = el("chatInput").value.trim();

    if (!message) return;

    addMessage(message, "you");

    el("chatInput").value = "";
    el("checkout").hidden = true;
    el("availability").innerHTML = "";
    el("customerMessage").textContent = "Checking your order...";

    try {
        const data = await api("/customer/chat", {
            method: "POST",
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                customer_name: el("customerName").value.trim() || "Customer"
            })
        });

        addMessage(data.reply || "Please tell me what you would like to order.", "bot");

        pendingItems = data.available_items || [];

        if (data.unavailable_items && data.unavailable_items.length) {
            const details = data.unavailable_items.map(item =>
                `${item.dish_name}: requested ${item.requested_quantity}, available ${item.available_quantity}`
            ).join("\n");

            addMessage("Availability details:\n" + details, "bot");
        }

        if (pendingItems.length) {
            el("availability").innerHTML = `
                <h3>Order Summary</h3>
                ${pendingItems.map(item => `
                    <div class="table-row">
                        <span>${esc(item.dish_name)} × ${item.quantity}</span>
                        <strong>₹${(Number(item.price) * Number(item.quantity)).toFixed(2)}</strong>
                    </div>
                `).join("")}
            `;

            el("checkout").hidden = false;
        }

        el("customerMessage").textContent = "";

    } catch (error) {
        addMessage(error.message, "bot");
        el("customerMessage").textContent = "";
    }
});


// Place order

el("checkout").addEventListener("click", async function() {
    if (!pendingItems.length) return;

    el("checkout").disabled = true;
    el("checkout").textContent = "Placing order...";

    try {
        const data = await api("/customer/checkout", {
            method: "POST",
            body: JSON.stringify({
                session_id: sessionId,
                customer_name: el("customerName").value.trim() || "Customer",
                items: pendingItems.map(item => ({
                    dish_name: item.dish_name,
                    quantity: item.quantity
                }))
            })
        });

        if (data.order) {
            addMessage(
                `Your order #${data.order.id} has been placed successfully. Current status: ${data.order.status}.`,
                "bot"
            );

            pendingItems = [];
            el("availability").innerHTML = "";
            el("checkout").hidden = true;

            await loadOrderHistory();

        } else {
            addMessage(
                data.message || "Please review your order availability.",
                "bot"
            );

            pendingItems = data.available_items || [];
        }

    } catch (error) {
        addMessage(error.message, "bot");
    } finally {
        el("checkout").disabled = false;
        el("checkout").textContent = "Confirm Order";
    }
});


// Show customer's order history

async function loadOrderHistory() {
    try {
        const orders = await api(
            "/customer/orders?session_id=" + encodeURIComponent(sessionId)
        );

        if (!orders.length) {
            el("tracking").innerHTML = '<p class="empty">No orders placed yet.</p>';
            return;
        }

        el("tracking").innerHTML = orders.map(order => `
            <div class="table-row">
                <span>
                    <strong>Order #${order.id}</strong>
                    <small>
                        ${order.items.map(item =>
                            `${esc(item.dish_name)} × ${item.quantity}`
                        ).join(", ")}
                    </small>
                    <small>₹${Number(order.total_price).toFixed(2)}</small>
                </span>

                <span class="pill">${esc(order.status)}</span>
            </div>
        `).join("");

    } catch (error) {
        el("tracking").textContent = error.message;
    }
}


// Initial load and periodic tracking refresh

loadMenu();
loadOrderHistory();

setInterval(loadOrderHistory, 10000);