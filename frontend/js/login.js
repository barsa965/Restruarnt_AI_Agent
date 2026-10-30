el("loginForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    el("message").textContent = "Signing in...";

    try {
        const data = await api("/auth/login", {
            method: "POST",
            body: JSON.stringify({
                email: el("email").value.trim(),
                password: el("password").value
            })
        });

        localStorage.setItem("bk_token", data.access_token);
        localStorage.setItem("bk_user", JSON.stringify(data.user));

        const dashboard = {
            owner: "owner.html",
            chef: "chef.html",
            delivery: "delivery.html"
        };

        location.href = dashboard[data.user.role] || "index.html";

    } catch (error) {
        el("message").textContent = error.message;
    }
});