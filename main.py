import json
from typing import List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path

class Product(BaseModel):
    name: str
    price: float
    description: str
    created_at: str

app = FastAPI(title="E-Shop-СI-CD")

with open(Path(__file__).parent / "shop.json", "r", encoding="utf-8") as f:
    PRODUCTS = json.load(f)

# Глобальные хранилища для корзины и заказов
CART = []          # каждый элемент: {"pid": int, "qty": int, "name": str, "price": float}
ORDERS = []        # каждый элемент: {"order_id": int, "items": list, "total": float}

@app.get("/products")
async def get_products():
    return PRODUCTS

@app.get("/product/{pid}")
async def get_product(pid: int):
    if 0 <= pid < len(PRODUCTS):
        return PRODUCTS[pid]
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/health")
async def health():
    return {"status": "ok", "products": len(PRODUCTS)}

@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    """Поиск товаров по подстроке в названии (q). Регистр не учитывается."""
    q_lower = q.lower()
    results = [p for p in PRODUCTS if q_lower in p["name"].lower()]
    return results

@app.get("/cart")
async def get_cart():
    """Возвращает содержимое корзины и общую сумму."""
    total = sum(item["price"] * item["qty"] for item in CART)
    return {"cart": CART, "total": total}

@app.post("/cart/add")
async def add_cart(pid: int, qty: int = 1):
    """Добавляет товар в корзину по id (pid) и количеству (qty). 404 при неверном pid."""
    if not (0 <= pid < len(PRODUCTS)):
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS[pid]
    # Проверяем, есть ли уже такой товар в корзине
    for item in CART:
        if item["pid"] == pid:
            item["qty"] += qty
            break
    else:
        CART.append({
            "pid": pid,
            "qty": qty,
            "name": product["name"],
            "price": product["price"]
        })
    return {"ok": True}

@app.delete("/cart")
async def clear_cart():
    """Очищает корзину полностью."""
    CART.clear()
    return {"ok": True}

@app.post("/checkout")
async def checkout():
    """Оформляет заказ: сохраняет текущую корзину в заказы, очищает корзину. 400 если корзина пуста."""
    if not CART:
        raise HTTPException(status_code=400, detail="Cart is empty")
    total = sum(item["price"] * item["qty"] for item in CART)
    order_id = len(ORDERS) + 1
    order = {
        "order_id": order_id,
        "items": CART.copy(),
        "total": total
    }
    ORDERS.append(order)
    CART.clear()
    return order

@app.get("/orders")
async def get_orders():
    """Возвращает список всех оформленных заказов."""
    return ORDERS