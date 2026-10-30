# Bloom Kitchen Frontend

A responsive restaurant management frontend inspired by lotus flowers,
sage green, cream and soft pink.

## Technologies

- HTML5
- CSS3
- JavaScript
- FastAPI backend
- JWT authentication
- LocalStorage

## Folder Structure

frontend/
│
├── css/
│   └── style.css
│
├── js/
│   ├── app.js
│   ├── login.js
│   ├── customer.js
│   ├── owner.js
│   ├── chef.js
│   └── delivery.js
│
├── chef.html
├── customer.html
├── delivery.html
├── index.html
├── login.html
├── owner.html
└── README.md

## Start Frontend

Open PowerShell:

    cd C:\Users\HP\bloom_kitchen_project\frontend

Run:

    python -m http.server 5500

Open:

    http://127.0.0.1:5500

## Start Backend

Open another terminal:

    cd C:\Users\HP\bloom_kitchen_project\backend

Activate virtual environment:

    .venv\Scripts\activate

Start FastAPI:

    uvicorn app.main:app --reload

API documentation:

    http://127.0.0.1:8000/docs

## Features

### Customer
- View menu
- Chat with food-ordering AI
- Check available quantities
- Confirm orders
- View order status

### Owner
- Add menu items
- Edit menu items
- Delete menu items
- Update daily inventory
- Register chef and delivery staff
- View orders
- View daily report

### Chef
- View assigned orders
- Mark orders ready
- Report cooking failures

### Delivery
- View assigned ready orders
- Mark orders delivered
- Report delivery failures

## Important

The frontend uses the API at:

http://127.0.0.1:8000

Change the API constant in js/app.js if your backend
runs at a different address.