const API = "http://127.0.0.1:8000";

function token() {
    return localStorage.getItem("bk_token") || "";
}

function authHeaders() {
    return token()
        ? { Authorization: "Bearer " + token() }
        : {};
}

async function api(path, options = {}) {
    const headers = {
        ...authHeaders(),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers || {})
    };

    const response = await fetch(API + path, {
        ...options,
        headers
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || data.message || "Request failed");
    }

    return data;
}

function el(id) {
    return document.getElementById(id);
}

function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    }[char]));
}

function logout() {
    localStorage.removeItem("bk_token");
    localStorage.removeItem("bk_user");
    location.href = "login.html";
}

async function requireRole(role) {
    if (!token()) {
        location.href = "login.html";
        return false;
    }

    try {
        const user = await api("/auth/me");

        if (user.role !== role) {
            alert("You do not have permission to access this page.");
            logout();
            return false;
        }

        localStorage.setItem("bk_user", JSON.stringify(user));
        return true;
    } catch (error) {
        logout();
        return false;
    }
}

function showError(elementId, error) {
    const element = el(elementId);
    if (element) element.textContent = error.message || String(error);
}