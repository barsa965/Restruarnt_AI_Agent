let ownerReady = false;

async function startOwnerDashboard() {
    ownerReady = await requireRole("owner");

    if (!ownerReady) return;

    await refreshOwner();

    setInterval(refreshOwner, 15000);
}

startOwnerDashboard();


// Add or edit menu item

el("dishForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    if (!ownerReady) return;

    const id = el("dishId").value;

    const dish = {
        dish_name: el("dishName").value.trim(),
        price: Number(el("price").value),
        image_url: el("image").value.trim(),
        description: el("description").value.trim()
    };

    try {
        if (id) {
            await api(`/owner/menu/${id}`, {
                method: "PATCH",
                body: JSON.stringify(dish)
            });
        } else {
            await api("/owner/menu", {
                method: "POST",
                body: JSON.stringify(dish)
            });
        }

        resetDishForm();
        await refreshOwner();

        el("ownerMessage").textContent =
            id ? "Menu item updated." : "Menu item added.";

    } catch (error) {
        el("ownerMessage").textContent = error.message;
    }
});


// Reset menu form

function resetDishForm() {
    el("dishForm").reset();
    el("dishId").value = "";
    el("dishFormTitle").textContent = "Add Menu Item";
    el("dishSubmit").textContent = "Add Dish";
    el("cancelEdit").hidden = true;
}

el("cancelEdit").addEventListener("click", resetDishForm);


// Register staff

el("staffForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    if (!ownerReady) return;

    try {
        await api("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                name: el("staffName").value.trim(),
                email: el("staffEmail").value.trim(),
                password: el("staffPassword").value,
                phone: el("staffPhone").value.trim() || null,
                role: el("staffRole").value
            })
        });

        this.reset();

        el("ownerMessage").textContent = "Staff account created successfully.";

        await refreshOwner();

    } catch (error) {
        el("ownerMessage").textContent = error.message;
    }
});


// Load owner dashboard information

async function refreshOwner() {
    if (!ownerReady) return;

    try {
        const [report, menu, inventory, staff, orders] = await Promise.all([
            api("/owner/reports/daily"),
            api("/owner/menu"),
            api("/owner/inventory"),
            api("/owner/staff"),
            api("/owner/orders")
        ]);

        // Dashboard statistics

        el("stats").innerHTML = [
            ["Total Orders", report.total_orders],
            ["Successful", report.successful_orders],
            ["Failed", report.failed_orders],
            ["Staff Members", staff.length]
        ].map(([label, value]) => `
            <div class="stat">
                <small>${label}</small>
                <strong>${value}</strong>
            </div>
        `).join("");


        // Menu list

        el("menuTable").innerHTML = menu.map(item => `
            <div class="table-row">
                <span>
                    <strong>${esc(item.dish_name)}</strong>
                    <small>₹${Number(item.price).toFixed(2)}</small>
                    <small>${item.active ? "Active" : "Inactive"}</small>
                </span>

                <span class="actions">
                    <button class="btn btn-secondary"
                        onclick="editDish(${item.id})">Edit</button>

                    <button class="btn"
                        onclick="removeDish(${item.id})">Delete</button>
                </span>
            </div>
        `).join("") || '<p class="empty">No menu items found.</p>';


        // Inventory list

        el("inventory").innerHTML = inventory.map(item => `
            <div class="table-row">
                <span>
                    <strong>${esc(item.dish_name)}</strong>
                    <small>Available: ${item.quantity}</small>
                </span>

                <span>
                    <input
                        id="stock-${item.menu_id}"
                        type="number"
                        min="0"
                        value="${item.quantity}"
                        style="width:85px"
                    >

                    <button class="btn btn-secondary"
                        onclick="saveStock(${item.menu_id})">
                        Save
                    </button>
                </span>
            </div>
        `).join("") || '<p class="empty">No inventory items.</p>';


        // Staff list

        el("staffList").innerHTML = staff.map(person => `
            <div class="table-row">
                <span>
                    <strong>${esc(person.name)}</strong>
                    <small>${esc(person.email)}</small>
                    <small>${esc(person.phone || "No phone number")}</small>
                </span>

                <span class="pill">
                    ${person.is_available ? "Available" : "Assigned"}
                </span>
            </div>
        `).join("") || '<p class="empty">No staff members.</p>';


        // Recent orders

        el("orders").innerHTML = orders.slice(0, 15).map(order => `
            <div class="table-row">
                <span>
                    <strong>Order #${order.id}</strong>
                    <small>${esc(order.customer_name)}</small>
                    <small>
                        ${order.items.map(item =>
                            `${esc(item.dish_name)} × ${item.quantity}`
                        ).join(", ")}
                    </small>
                    <small>₹${Number(order.total_price).toFixed(2)}</small>
                </span>

                <span class="pill">${esc(order.status)}</span>
            </div>
        `).join("") || '<p class="empty">No orders yet.</p>';


        // Failure report

        el("failureReport").innerHTML =
            report.failure_reasons.length
                ? report.failure_reasons.map(item => `
                    <div class="table-row">
                        <strong>Order #${item.order_id}</strong>
                        <span>${esc(item.reason)}</span>
                    </div>
                `).join("")
                : '<p class="empty">No failures reported today.</p>';

    } catch (error) {
        el("ownerMessage").textContent = "Dashboard error: " + error.message;
    }
}


// Edit menu item

async function editDish(id) {
    try {
        const menu = await api("/owner/menu");
        const item = menu.find(dish => dish.id === id);

        if (!item) throw new Error("Dish not found.");

        el("dishId").value = item.id;
        el("dishName").value = item.dish_name;
        el("price").value = item.price;
        el("image").value = item.image_url || "";
        el("description").value = item.description || "";

        el("dishFormTitle").textContent = "Edit Menu Item";
        el("dishSubmit").textContent = "Save Changes";
        el("cancelEdit").hidden = false;

        el("dishForm").scrollIntoView({ behavior: "smooth" });

    } catch (error) {
        alert(error.message);
    }
}


// Delete menu item

async function removeDish(id) {
    if (!confirm("Are you sure you want to remove this dish?")) return;

    try {
        await api(`/owner/menu/${id}`, {
            method: "DELETE"
        });

        await refreshOwner();

    } catch (error) {
        alert(error.message);
    }
}


// Update daily inventory

async function saveStock(id) {
    try {
        const quantity = Number(el(`stock-${id}`).value);

        if (!Number.isInteger(quantity) || quantity < 0) {
            throw new Error("Enter a valid non-negative whole number.");
        }

        await api(`/owner/inventory/${id}`, {
            method: "PUT",
            body: JSON.stringify({ quantity })
        });

        el("ownerMessage").textContent = "Inventory updated.";

        await refreshOwner();

    } catch (error) {
        alert(error.message);
    }
}