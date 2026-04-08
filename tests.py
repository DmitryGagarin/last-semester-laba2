from fastapi.testclient import TestClient
from main import app, CART, ORDERS, PRODUCTS

client = TestClient(app)

def test_health():
    """Проверка endpoint /health"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_products():
    """Проверка endpoint /products"""
    response = client.get("/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def test_search():
    """Проверка поиска товаров по подстроке"""
    # Сброс состояния не нужен
    response = client.get("/search?q=a")  # ищем любую букву 'a'
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    # Поиск с пустым результатом
    response = client.get("/search?q=xyz123nonexistent")
    assert response.status_code == 200
    assert response.json() == []
    # Регистронезависимость (если есть товар с заглавной буквой)
    if len(PRODUCTS) > 0:
        first_product = PRODUCTS[0]
        first_char = first_product["name"][0]
        response_upper = client.get(f"/search?q={first_char.upper()}")
        response_lower = client.get(f"/search?q={first_char.lower()}")
        # Оба запроса должны вернуть одинаковое количество результатов
        assert len(response_upper.json()) == len(response_lower.json())

def test_cart_add():
    """Добавление товара в корзину"""
    # Очищаем корзину перед тестом
    CART.clear()
    # Добавляем первый товар (pid=0, если есть)
    if len(PRODUCTS) == 0:
        return  # нет товаров - тест пропускаем, но лучше бы иметь данные
    response = client.post("/cart/add?pid=0&qty=2")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    # Проверяем содержимое корзины
    assert len(CART) == 1
    assert CART[0]["pid"] == 0
    assert CART[0]["qty"] == 2
    # Добавляем тот же товар ещё раз - должно увеличить количество
    client.post("/cart/add?pid=0&qty=3")
    assert CART[0]["qty"] == 5
    # Добавляем несуществующий товар
    response = client.post("/cart/add?pid=999")
    assert response.status_code == 404
    # Проверяем, что корзина не изменилась
    assert len(CART) == 1

def test_cart_get():
    """Получение содержимого корзины и суммы"""
    CART.clear()
    # Сначала добавим товары
    if len(PRODUCTS) >= 2:
        client.post("/cart/add?pid=0&qty=1")
        client.post("/cart/add?pid=1&qty=2")
    else:
        # Если мало товаров, используем только первый
        client.post("/cart/add?pid=0&qty=1")
    response = client.get("/cart")
    assert response.status_code == 200
    data = response.json()
    assert "cart" in data
    assert "total" in data
    assert isinstance(data["cart"], list)
    assert isinstance(data["total"], (int, float))
    # Проверяем расчёт суммы
    total = sum(item["price"] * item["qty"] for item in data["cart"])
    assert data["total"] == total

def test_cart_clear():
    """Очистка корзины"""
    CART.clear()
    # Добавляем что-то
    if len(PRODUCTS) > 0:
        client.post("/cart/add?pid=0&qty=1")
        assert len(CART) > 0
    # Очищаем
    response = client.delete("/cart")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(CART) == 0

def test_checkout():
    """Оформление заказа"""
    # Очищаем корзину и заказы
    CART.clear()
    ORDERS.clear()
    # Пустая корзина -> 400
    response = client.post("/checkout")
    assert response.status_code == 400
    # Добавляем товары
    if len(PRODUCTS) > 0:
        client.post("/cart/add?pid=0&qty=2")
    else:
        return
    response = client.post("/checkout")
    assert response.status_code == 200
    order = response.json()
    assert "order_id" in order
    assert "items" in order
    assert "total" in order
    assert order["order_id"] == 1
    assert len(order["items"]) == 1
    # Проверяем, что корзина очистилась
    assert len(CART) == 0
    # Проверяем, что заказ добавился в список
    assert len(ORDERS) == 1
    assert ORDERS[0]["order_id"] == 1

def test_orders():
    """Получение списка заказов"""
    ORDERS.clear()
    # Сначала создадим заказ через checkout
    if len(PRODUCTS) > 0:
        client.post("/cart/add?pid=0&qty=1")
        client.post("/checkout")
    response = client.get("/orders")
    assert response.status_code == 200
    orders = response.json()
    assert isinstance(orders, list)
    # Если заказ создан, проверяем его наличие
    if len(ORDERS) > 0:
        assert len(orders) == 1
        assert orders[0]["order_id"] == 1