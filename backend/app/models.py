from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(160), unique=True, index=True, nullable=False)
    phone = Column(String(30))
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)
    is_available = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True)
    dish_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    image_url = Column(String(500), default="")
    active = Column(Boolean, default=True)

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    day = Column(Date, nullable=False)
    quantity = Column(Integer, default=0)
    __table_args__ = (UniqueConstraint("menu_id", "day"),)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(100), default="Customer")
    session_id = Column(String(100), index=True, nullable=False)
    status = Column(String(30), default="CONFIRMED")
    total_price = Column(Float, default=0)
    failure_reason = Column(Text)
    chef_id = Column(Integer, ForeignKey("users.id"))
    delivery_id = Column(Integer, ForeignKey("users.id"))
    cook_failures = Column(Integer, default=0)
    delivery_failures = Column(Integer, default=0)
    final_result = Column(String(20), default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    items = relationship("OrderItem", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)

class OrderHistory(Base):
    __tablename__ = "order_history"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(String(30), nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
