from agno.agent import Agent
from agno.models.openai import OpenAIChat
from typing import List, Dict
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
import uuid
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime

# --- Dummy Data ---
PRODUCTS = [
    {"id": "p1", "name": "Classic Blue Jeans", "brand": "Levi's", "color": "blue", "style": "casual", "price": 89.99, "stock": 10},
    {"id": "p2", "name": "Red Running Shoes", "brand": "Nike", "color": "red", "style": "sporty", "price": 129.99, "stock": 0},  # Out of stock for edge case
    {"id": "p3", "name": "Elegant Black Dress", "brand": "Zara", "color": "black", "style": "formal", "price": 79.99, "stock": 3},
    {"id": "p4", "name": "Green Hoodie", "brand": "Uniqlo", "color": "green", "style": "casual", "price": 49.99, "stock": 8},
    {"id": "p5", "name": "White Sneakers", "brand": "Adidas", "color": "white", "style": "sporty", "price": 89.99, "stock": 6},
]

# --- SQLAlchemy Setup ---
Base = declarative_base()
engine = create_engine('sqlite:///shopping.db')
SessionLocal = sessionmaker(bind=engine)

# --- Models ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    addresses = relationship('Address', back_populates='user')
    sizes = relationship('Size', back_populates='user')
    payments = relationship('Payment', back_populates='user')
    preferences = relationship('Preference', back_populates='user')
    travels = relationship('Travel', back_populates='user')
    birthdays = relationship('Birthday', back_populates='user')
    orders = relationship('Order', back_populates='user')

class Address(Base):
    __tablename__ = 'addresses'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    address = Column(Text)
    user = relationship('User', back_populates='addresses')

class Size(Base):
    __tablename__ = 'sizes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    size = Column(String)
    user = relationship('User', back_populates='sizes')

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    method = Column(String)
    user = relationship('User', back_populates='payments')

class Preference(Base):
    __tablename__ = 'preferences'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    key = Column(String)
    value = Column(String)
    user = relationship('User', back_populates='preferences')

class Travel(Base):
    __tablename__ = 'travels'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String)
    location = Column(String)
    user = relationship('User', back_populates='travels')

class Birthday(Base):
    __tablename__ = 'birthdays'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    birthday = Column(String)  # YYYY-MM-DD
    user = relationship('User', back_populates='birthdays')

class Cart(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(String)
    quantity = Column(Integer)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    address = Column(Text)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship('User', back_populates='orders')
    items = relationship('OrderItem', back_populates='order')

class OrderItem(Base):
    __tablename__ = 'order_items'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(String)
    quantity = Column(Integer)
    order = relationship('Order', back_populates='items')

# Create tables
Base.metadata.create_all(engine)

# --- Tool Functions ---
def get_product_list() -> List[dict]:
    return PRODUCTS

def check_stock(product_id: str) -> dict:
    for p in PRODUCTS:
        if p["id"] == product_id:
            return {"product_id": product_id, "stock": p["stock"]}
    return {"product_id": product_id, "stock": 0}

def add_to_cart(user_id: str, product_id: str, quantity: int = 1) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    cart_item = session.query(Cart).filter_by(user_id=user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = Cart(user_id=user.id, product_id=product_id, quantity=quantity)
        session.add(cart_item)
    session.commit()
    session.close()
    return f"Added {quantity} of {product_id} to {user_id}'s cart."

def set_address(user_id: str, address: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.addresses.append(Address(address=address))
    session.commit()
    session.close()
    return f"Address for {user_id} set to: {address}"

def get_address(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.addresses:
        return user.addresses[0].address if user.addresses else "No address set."
    return "No address set."

def set_size(user_id: str, size: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.sizes.append(Size(size=size))
    session.commit()
    session.close()
    return f"Size for {user_id} set to: {size}"

def get_size(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.sizes:
        return user.sizes[0].size if user.sizes else "No size set."
    return "No size set."

def set_calendar_location(user_id: str, location: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.travels.append(Travel(status="home", location=location)) # Assuming default to home
    session.commit()
    session.close()
    return f"Calendar location for {user_id} set to: {location}"

def get_calendar_location(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.travels:
        return user.travels[0].location if user.travels else "office"
    return "office"

def set_payment_method(user_id: str, method: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.payments.append(Payment(method=method))
    session.commit()
    session.close()
    return f"Payment method set to {method}"

def get_payment_method(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.payments:
        return user.payments[0].method if user.payments else "No payment method set."
    return "No payment method set."

def set_preference(user_id: str, key: str, value: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.preferences.append(Preference(key=key, value=value))
    session.commit()
    session.close()
    return f"Preference {key} set to {value}"

def get_preference(user_id: str, key: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.preferences:
        pref = next((p for p in user.preferences if p.key == key), None)
        return pref.value if pref else "Not set"
    return "Not set"

def set_travel_status(user_id: str, status: str, location: str = "") -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.travels.append(Travel(status=status, location=location))
    session.commit()
    session.close()
    return f"Travel status set to {status} at {location}"

def get_travel_status(user_id: str) -> dict:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.travels:
        return user.travels[0].__dict__ if user.travels else {"status": "home", "location": get_address(user_id)}
    return {"status": "home", "location": get_address(user_id)}

def checkout(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        session.close()
        return "User not found. Please register."

    if not user.addresses:
        session.close()
        return "No address set. Please provide a shipping address before checkout."

    order_id = str(uuid.uuid4())
    order = Order(user_id=user.id, address=user.addresses[0].address, status="Processing")
    session.add(order)

    for item in user.carts:
        product = next((p for p in PRODUCTS if p["id"] == item.product_id), None)
        if product:
            order_item = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity)
            session.add(order_item)
            product["stock"] = max(0, product["stock"] - item.quantity)
        else:
            # If product not found, remove from cart
            session.delete(item)

    user.carts = [] # Clear cart after checkout
    session.commit()
    session.close()
    return f"Order placed! Your order ID is {order_id}."

def check_order_status(order_id: str) -> str:
    session = SessionLocal()
    order = session.query(Order).filter_by(id=int(order_id)).first()
    session.close()
    if not order:
        return "Order not found."
    return f"Order {order_id} for {order.user.email} is currently: {order.status}"

def check_delivery_date(product_id: str, zip_code: str) -> str:
    return f"Estimated delivery for {product_id} to {zip_code}: 3-5 business days."

def recommend_products(user_profile: dict) -> List[dict]:
    matches = []
    for p in PRODUCTS:
        if (p["brand"] in user_profile.get("brands", [])) or \
           (p["color"] in user_profile.get("colors", [])) or \
           (p["style"] in user_profile.get("styles", [])):
            matches.append(p)
        if len(matches) >= 3:
            break
    return matches

def get_birthday(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.birthdays:
        return user.birthdays[0].birthday if user.birthdays else ""
    return ""

def get_order_history(user_id: str) -> List[Dict]:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if not user:
        return []
    return [o.__dict__ for o in user.orders]

def is_duplicate_order(user_id: str, product_id: str) -> bool:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if not user:
        return False
    for order in user.orders:
        for item in order.items:
            if item.product_id == product_id:
                return True
    return False

def set_concierge_tone(user_id: str, tone: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.preferences.append(Preference(key="concierge_tone", value=tone))
    session.commit()
    session.close()
    return f"Concierge tone set to {tone}"

def get_concierge_tone(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.preferences:
        pref = next((p for p in user.preferences if p.key == "concierge_tone"), None)
        return pref.value if pref else "professional"
    return "professional"

# --- Persistent Memory Setup ---
memory = Memory(
    db=SqliteMemoryDb(table_name="memory", db_file="memory.db"),
)

# --- Concierge Instructions ---
concierge_instructions = [
    "You are a discreet, highly efficient shopping concierge for HNI clients.",
    "Always be brief, direct, and professional, unless the user has set a different concierge style preference (e.g., ultra-formal, friendly).",
    "For any update to user information (address, size, preferences, payment, travel status, etc.), always use the corresponding tool, even if you already have the information.",
    "Never just acknowledge or update memory directly—always call the tool for any state change.",
    "Use all available context: calendar, preferences, payment method, travel status, birthday, and order history.",
    "If the user is traveling, offer delivery to their travel location or to hold the order until they return.",
    "If the user requests an item they have already ordered, confirm if they want to duplicate the order.",
    "If all info is present, summarize the order and ask for a single confirmation before placing it (e.g., 'Levi's Classic Blue Jeans, size 32, delivery to your office. $89.99. Proceed?').",
    "If info is missing, ask for it in a single, direct message, then proceed directly to confirmation and order placement.",
    "If the product is out of stock, suggest the closest alternative in one sentence.",
    "If the request is ambiguous, clarify in one sentence.",
    "If today is the user's birthday or a special date, offer a relevant service (e.g., gift wrap).",
    "Once confirmed, place the order and summarize in one sentence.",
    "Never use more than 2 sentences. Never use exclamation marks or emojis.",
    "Assume the user expects things to be handled with minimal friction.",
    "Chain tool calls as needed to complete the user's request.",
]

# --- Create the Concierge Shopping Agent ---
shopping_agent = Agent(
    name="Concierge Shopping Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        get_product_list,
        check_stock,
        add_to_cart,
        set_address,
        get_address,
        set_size,
        get_size,
        set_calendar_location,
        get_calendar_location,
        set_payment_method,
        get_payment_method,
        set_preference,
        get_preference,
        set_travel_status,
        get_travel_status,
        checkout,
        check_order_status,
        check_delivery_date,
        recommend_products,
        get_birthday,
        get_order_history,
        is_duplicate_order,
        set_concierge_tone,
        get_concierge_tone,
    ],
    memory=memory,
    enable_user_memories=True,
    add_history_to_messages=True,
    num_history_runs=3,
    instructions=concierge_instructions,
    show_tool_calls=True,
    markdown=True,
)

if __name__ == "__main__":
    user_id = "priya@example.com"
    session_id = "priya_session_1"

    print("=== HNI Concierge Shopping Flow: Tool Use for All State Updates ===")
    # Demonstrate tool calls for info updates (no duplicates)
    shopping_agent.print_response("My waist size is 32.", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("My address is 123 Main St, Springfield, 90210.", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("Set my payment method to Amex ending 1234.", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("Set my preference: no calls, only text.", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("I'm traveling to Paris.", user_id=user_id, session_id=session_id)

    # 1. Travel-aware delivery
    print("\n--- Travel-Aware Delivery ---")
    shopping_agent.print_response("Order a green hoodie for me", user_id=user_id, session_id=session_id)

    # 2. Order history/duplicate order
    print("\n--- Duplicate Order Edge Case ---")
    shopping_agent.print_response("Order a blue jeans for me", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("Order a blue jeans for me", user_id=user_id, session_id=session_id)

    # 3. Concierge style tone
    print("\n--- Concierge Style Tone (Friendly) ---")
    shopping_agent.print_response("Set my concierge style to friendly.", user_id=user_id, session_id=session_id)
    shopping_agent.print_response("Order a black dress for me", user_id=user_id, session_id=session_id) 
