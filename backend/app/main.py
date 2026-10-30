from datetime import date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.config import settings
from app.db import Base, engine, get_db
from app.models import User, MenuItem, Inventory, Order, OrderItem, OrderHistory
from app.security import hash_password, verify_password, create_token, decode_token
from app.agent import extract_order

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bloom Kitchen API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
oauth = OAuth2PasswordBearer(tokenUrl="/auth/login")

class StaffInput(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: str
    phone: Optional[str] = None
class LoginInput(BaseModel):
    email: EmailStr
    password: str
class DishInput(BaseModel):
    dish_name: str
    price: float = Field(gt=0)
    description: str = ""
    image_url: str = ""
class StockInput(BaseModel):
    quantity: int = Field(ge=0)
class ChatInput(BaseModel):
    message: str
    session_id: str
    customer_name: str = "Customer"
class CheckoutInput(BaseModel):
    session_id: str
    customer_name: str = "Customer"
    items: list[dict]
class ActionInput(BaseModel):
    success: bool
    failure_reason: Optional[str] = None

def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    account = db.get(User, int(payload["sub"]))
    if not account or not account.is_active:
        raise HTTPException(401, "Account unavailable")
    return account

def require_role(*roles):
    def dependency(account=Depends(current_user)):
        if account.role not in roles:
            raise HTTPException(403, "You do not have permission")
        return account
    return dependency

def order_json(order):
    return {"id": order.id, "customer_name": order.customer_name, "status": order.status,
            "total_price": order.total_price, "failure_reason": order.failure_reason,
            "cook_failures": order.cook_failures, "delivery_failures": order.delivery_failures,
            "final_result": order.final_result,
            "items": [{"dish_name": i.dish_name, "quantity": i.quantity, "unit_price": i.unit_price}
                      for i in order.items]}

def check_items(db, requested):
    accepted, issues = [], []
    for item in requested:
        name, qty = str(item["dish_name"]), int(item["quantity"])
        menu_item = db.query(MenuItem).filter(func.lower(MenuItem.dish_name) == name.lower(),
                                              MenuItem.active.is_(True)).first()
        stock = db.query(Inventory).filter_by(menu_id=menu_item.id, day=date.today()).first() if menu_item else None
        available = stock.quantity if stock else 0
        if not menu_item or available < qty:
            issues.append({"dish_name": name, "requested_quantity": qty, "available_quantity": available})
        if menu_item and available > 0:
            accepted.append({"menu_id": menu_item.id, "dish_name": menu_item.dish_name,
                             "quantity": min(qty, available), "price": menu_item.price})
    return accepted, issues

def assign_staff(db):
    chef = db.query(User).filter_by(role="chef", is_available=True, is_active=True).first()
    delivery = db.query(User).filter_by(role="delivery", is_available=True, is_active=True).first()
    if not chef or not delivery:
        return None
    chef.is_available = False
    delivery.is_available = False
    return chef, delivery

@app.get("/")
def root():
    return {"app": "Bloom Kitchen", "status": "running"}

@app.post("/auth/bootstrap-owner")
def bootstrap_owner(data: StaffInput, db: Session = Depends(get_db)):
    if data.role != "owner":
        raise HTTPException(400, "role must be owner")
    if db.query(User).filter_by(role="owner").first():
        raise HTTPException(409, "Owner already exists")
    account = User(name=data.name, email=data.email, phone=data.phone,
                   password_hash=hash_password(data.password), role="owner")
    db.add(account); db.commit()
    return {"message": "Owner account created"}

@app.post("/auth/register")
def register_staff(data: StaffInput, db: Session = Depends(get_db), owner=Depends(require_role("owner"))):
    if data.role not in ("chef", "delivery"):
        raise HTTPException(400, "Staff role must be chef or delivery")
    if db.query(User).filter_by(email=data.email).first():
        raise HTTPException(409, "Email already registered")
    db.add(User(name=data.name, email=data.email, phone=data.phone,
                password_hash=hash_password(data.password), role=data.role))
    db.commit()
    return {"message": "Staff account created"}

@app.post("/auth/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    account = db.query(User).filter_by(email=data.email, is_active=True).first()
    if not account or not verify_password(data.password, account.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(account), "token_type": "bearer",
            "user": {"id": account.id, "name": account.name, "role": account.role}}

@app.get("/auth/me")
def me(account=Depends(current_user)):
    return {"id": account.id, "name": account.name, "role": account.role}

@app.get("/customer/menu")
def customer_menu(db: Session = Depends(get_db)):
    return [{"id": m.id, "dish_name": m.dish_name, "description": m.description,
             "price": m.price, "image_url": m.image_url}
            for m in db.query(MenuItem).filter_by(active=True).all()]

@app.post("/customer/chat")
def customer_chat(data: ChatInput, db: Session = Depends(get_db)):
    result = extract_order(data.message)
    if not result["is_food_order"]:
        return {"reply": "I am Bloom Kitchen's food-ordering assistant. I can help with our menu and food orders."}
    if not result["items"]:
        return {"reply": result.get("reply") or "Tell me the dish and quantity you want."}
    accepted, issues = check_items(db, result["items"])
    return {"reply": "Some requested quantities are unavailable. Review the available quantity before checkout."
            if issues else "Your requested items are available. Confirm checkout to place the order.",
            "requested_items": result["items"], "available_items": accepted,
            "unavailable_items": issues, "requires_confirmation": True}

@app.post("/customer/checkout")
def customer_checkout(data: CheckoutInput, db: Session = Depends(get_db)):
    accepted, issues = check_items(db, data.items)
    if issues:
        return {"message": "Inventory is insufficient or changed. Please review availability.",
                "available_items": accepted, "unavailable_items": issues}
    assignment = assign_staff(db)
    if not assignment:
        raise HTTPException(409, "No available chef or delivery staff. Please try later.")
    chef, rider = assignment
    try:
        total = sum(i["quantity"] * i["price"] for i in accepted)
        order = Order(customer_name=data.customer_name, session_id=data.session_id,
                      total_price=total, chef_id=chef.id, delivery_id=rider.id, status="CONFIRMED")
        db.add(order); db.flush()
        for item in accepted:
            stock = db.query(Inventory).filter_by(menu_id=item["menu_id"], day=date.today()).first()
            if not stock or stock.quantity < item["quantity"]:
                raise ValueError("Inventory changed during checkout; please retry.")
            stock.quantity -= item["quantity"]
            db.add(OrderItem(order_id=order.id, dish_name=item["dish_name"],
                             quantity=item["quantity"], unit_price=item["price"]))
        db.add(OrderHistory(order_id=order.id, status="CONFIRMED", note="Automatically assigned chef and delivery staff"))
        db.commit(); db.refresh(order)
        return {"order": order_json(order)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(409, str(exc))

@app.get("/customer/orders")
def customer_orders(session_id: str, db: Session = Depends(get_db)):
    return [order_json(o) for o in db.query(Order).filter_by(session_id=session_id).order_by(Order.id.desc()).all()]

@app.get("/customer/orders/{order_id}")
def customer_order(order_id: int, session_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter_by(id=order_id, session_id=session_id).first()
    if not order: raise HTTPException(404, "Order not found")
    return order_json(order)

@app.get("/owner/menu")
def owner_menu(db: Session = Depends(get_db), owner=Depends(require_role("owner"))):
    return [{"id":m.id,"dish_name":m.dish_name,"price":m.price,"description":m.description,
             "image_url":m.image_url,"active":m.active} for m in db.query(MenuItem).all()]

@app.post("/owner/menu")
def create_menu_item(data: DishInput, db: Session = Depends(get_db), owner=Depends(require_role("owner"))):
    if db.query(MenuItem).filter_by(dish_name=data.dish_name).first():
        raise HTTPException(409, "Dish already exists")
    item = MenuItem(**data.model_dump()); db.add(item); db.commit()
    return {"message":"Menu item added","id":item.id}

@app.patch("/owner/menu/{menu_id}")
def update_menu_item(menu_id:int,data:DishInput,db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    item=db.get(MenuItem,menu_id)
    if not item: raise HTTPException(404,"Dish not found")
    for key,value in data.model_dump().items(): setattr(item,key,value)
    db.commit(); return {"message":"Menu item updated"}

@app.delete("/owner/menu/{menu_id}")
def deactivate_menu_item(menu_id:int,db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    item=db.get(MenuItem,menu_id)
    if not item: raise HTTPException(404,"Dish not found")
    item.active=False; db.commit(); return {"message":"Dish removed from menu"}

@app.get("/owner/inventory")
def owner_inventory(db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    output=[]
    for item in db.query(MenuItem).filter_by(active=True).all():
        stock=db.query(Inventory).filter_by(menu_id=item.id,day=date.today()).first()
        output.append({"menu_id":item.id,"dish_name":item.dish_name,"quantity":stock.quantity if stock else 0})
    return output

@app.put("/owner/inventory/{menu_id}")
def update_inventory(menu_id:int,data:StockInput,db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    if not db.get(MenuItem,menu_id): raise HTTPException(404,"Dish not found")
    stock=db.query(Inventory).filter_by(menu_id=menu_id,day=date.today()).first()
    if stock: stock.quantity=data.quantity
    else: db.add(Inventory(menu_id=menu_id,day=date.today(),quantity=data.quantity))
    db.commit(); return {"message":"Today's inventory saved"}

@app.get("/owner/staff")
def owner_staff(db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    return [{"id":u.id,"name":u.name,"email":u.email,"phone":u.phone,"role":u.role,
             "is_available":u.is_available,"is_active":u.is_active}
            for u in db.query(User).filter(User.role.in_(["chef","delivery"])).all()]

@app.get("/owner/orders")
def owner_orders(db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    return [order_json(o) for o in db.query(Order).order_by(Order.id.desc()).all()]

@app.get("/owner/reports/daily")
def daily_report(db:Session=Depends(get_db),owner=Depends(require_role("owner"))):
    orders=db.query(Order).filter(func.date(Order.created_at)==date.today()).all()
    return {"total_orders":len(orders),"successful_orders":sum(o.final_result=="SUCCESS" for o in orders),
            "failed_orders":sum(o.final_result=="FAILED" for o in orders),
            "failure_reasons":[{"order_id":o.id,"reason":o.failure_reason} for o in orders if o.failure_reason],
            "orders":[order_json(o) for o in orders]}

@app.get("/chef/orders")
def chef_orders(db:Session=Depends(get_db),chef=Depends(require_role("chef"))):
    return [order_json(o) for o in db.query(Order).filter_by(chef_id=chef.id).filter(Order.status.in_(["CONFIRMED","COOKING"])).all()]

@app.post("/chef/orders/{order_id}/cook")
def chef_action(order_id:int,data:ActionInput,db:Session=Depends(get_db),chef=Depends(require_role("chef"))):
    order=db.query(Order).filter_by(id=order_id,chef_id=chef.id).first()
    if not order: raise HTTPException(404,"Assigned order not found")
    if data.success:
        order.status="READY"; order.failure_reason=None; chef.is_available=True
    else:
        order.cook_failures += 1; order.failure_reason=data.failure_reason
        if order.cook_failures >= 2:
            order.status="FAILED"; order.final_result="FAILED"; chef.is_available=True
        else: order.status="COOKING"
    db.add(OrderHistory(order_id=order.id,status=order.status,note=data.failure_reason or order.status))
    db.commit(); return order_json(order)

@app.get("/delivery/orders")
def delivery_orders(db:Session=Depends(get_db),rider=Depends(require_role("delivery"))):
    return [order_json(o) for o in db.query(Order).filter_by(delivery_id=rider.id).filter(Order.status=="READY").all()]

@app.post("/delivery/orders/{order_id}/deliver")
def delivery_action(order_id:int,data:ActionInput,db:Session=Depends(get_db),rider=Depends(require_role("delivery"))):
    order=db.query(Order).filter_by(id=order_id,delivery_id=rider.id).first()
    if not order: raise HTTPException(404,"Assigned order not found")
    if data.success:
        order.status="COMPLETED"; order.final_result="SUCCESS"; rider.is_available=True
    else:
        order.delivery_failures += 1; order.failure_reason=data.failure_reason
        if order.delivery_failures >= 2:
            order.status="FAILED"; order.final_result="FAILED"; rider.is_available=True
        else:
            order.status="READY"
    db.add(OrderHistory(order_id=order.id,status=order.status,note=data.failure_reason or order.status))
    db.commit(); return order_json(order)
