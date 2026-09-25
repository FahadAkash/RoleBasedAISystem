from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import Product, Order

def get_product_info(db: Session) -> dict:
    """Returns a list of all products in the catalog."""
    products = db.query(Product).all()
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock,
                "category": p.category,
            }
            for p in products
        ]
    }

def get_sales_data(db: Session) -> dict:
    """Returns sales metrics including total revenue and top-selling products."""
    
    total_orders = db.query(Order).count()
    total_revenue = db.query(func.sum(Order.total_price)).scalar() or 0.0
    
    # Get top selling products
    top_products_query = (
        db.query(Product.name, func.sum(Order.quantity).label("total_sold"))
        .join(Order, Product.id == Order.product_id)
        .group_by(Product.id)
        .order_by(func.sum(Order.quantity).desc())
        .limit(5)
        .all()
    )
    
    top_products = [{"name": row.name, "units_sold": row.total_sold} for row in top_products_query]
    
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "top_selling_products": top_products
    }

def manage_cart(user_id: int, action: str, db: Session, product_name: str = None, quantity: int = 1) -> dict:
    """Add, remove, or view items in the user's cart."""
    if action == "view":
        cart_items = db.query(Order).filter(Order.user_id == user_id, Order.status == "in_cart").all()
        if not cart_items:
            return {"message": "Your cart is empty."}
        
        items = []
        total = 0.0
        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            items.append({
                "product_name": product.name,
                "quantity": item.quantity,
                "total_price": item.total_price
            })
            total += item.total_price
        
        return {"cart_items": items, "total_cost": total}
    
    elif action == "add":
        if not product_name:
            return {"error": "Please provide a product name to add."}
        
        product = db.query(Product).filter(Product.name.ilike(f"%{product_name}%")).first()
        if not product:
            return {"error": f"Product '{product_name}' not found."}
        if product.stock < quantity:
            return {"error": f"Not enough stock. Only {product.stock} available."}
        
        # Check if already in cart
        existing = db.query(Order).filter(Order.user_id == user_id, Order.product_id == product.id, Order.status == "in_cart").first()
        if existing:
            existing.quantity += quantity
            existing.total_price += (product.price * quantity)
        else:
            new_order = Order(
                user_id=user_id,
                product_id=product.id,
                quantity=quantity,
                total_price=product.price * quantity,
                status="in_cart"
            )
            db.add(new_order)
            
        # Update stock
        product.stock -= quantity
        db.commit()
        return {"success": True, "message": f"Added {quantity}x {product.name} to your cart."}
        
    return {"error": "Invalid action. Use 'add' or 'view'."}

def checkout_cart(user_id: int, db: Session) -> dict:
    """Checkout all items in the user's cart."""
    cart_items = db.query(Order).filter(Order.user_id == user_id, Order.status == "in_cart").all()
    if not cart_items:
        return {"error": "Your cart is empty. Nothing to checkout."}
    
    total = 0.0
    for item in cart_items:
        item.status = "processing"
        total += item.total_price
        
    db.commit()
    return {"success": True, "message": f"Successfully checked out! Total charged: ${total:.2f}. Orders are now processing."}

def view_order_history(user_id: int, db: Session) -> dict:
    """View the user's past orders and statuses."""
    orders = db.query(Order).filter(Order.user_id == user_id, Order.status != "in_cart").order_by(Order.order_date.desc()).all()
    if not orders:
        return {"message": "You have no order history."}
        
    history = []
    for o in orders:
        product = db.query(Product).filter(Product.id == o.product_id).first()
        history.append({
            "order_id": o.id,
            "product_name": product.name,
            "quantity": o.quantity,
            "total_price": o.total_price,
            "status": o.status,
            "order_date": str(o.order_date)[:10],
            "delivery_date": str(o.delivery_date)[:10] if o.delivery_date else None
        })
        
    return {"orders": history}

def process_return(user_id: int, order_id: int, db: Session) -> dict:
    """Process a return if within 10 days of delivery."""
    from datetime import datetime, timezone
    
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user_id).first()
    if not order:
        return {"error": f"Order #{order_id} not found in your account."}
        
    if order.status != "delivered":
        return {"error": f"Cannot return an order with status '{order.status}'. Must be 'delivered'."}
        
    if not order.delivery_date:
        return {"error": "Delivery date unknown."}
        
    days_since = (datetime.now(timezone.utc) - order.delivery_date.replace(tzinfo=timezone.utc)).days
    
    if days_since > 10:
        return {"error": f"Return policy violation. Order was delivered {days_since} days ago. Returns only accepted within 10 days."}
        
    # Process return
    order.status = "returned"
    
    # Restore stock
    product = db.query(Product).filter(Product.id == order.product_id).first()
    if product:
        product.stock += order.quantity
        
    db.commit()
    return {"success": True, "message": f"Return approved for Order #{order_id}. ${order.total_price:.2f} will be refunded."}

def recommend_products(user_id: int, db: Session) -> dict:
    """Recommend products the user hasn't bought yet."""
    # Find products the user bought
    bought_product_ids = db.query(Order.product_id).filter(Order.user_id == user_id, Order.status != "in_cart").distinct().all()
    bought_ids = [pid[0] for pid in bought_product_ids]
    
    # Get products they haven't bought
    recommendations = db.query(Product).filter(~Product.id.in_(bought_ids)).limit(3).all()
    
    if not recommendations:
        # Fallback to random/all if they bought everything
        recommendations = db.query(Product).limit(3).all()
        
    return {
        "message": "Based on your history, you might like these:",
        "recommendations": [{"name": p.name, "price": p.price, "description": p.description} for p in recommendations]
    }

