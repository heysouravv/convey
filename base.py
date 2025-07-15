from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from typing import List, Dict, Optional
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
import uuid
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, joinedload
import datetime
from agno.agent import Agent as AgnoAgent
from agno.models.openai import OpenAIChat
from agno.team.team import Team
from agno.tools import tool

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
    carts = relationship('Cart', back_populates='user')

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
    user = relationship('User', back_populates='carts')

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
@tool
def get_product_list() -> List[dict]:
    return PRODUCTS

@tool
def check_stock(product_id: str) -> dict:
    for p in PRODUCTS:
        if p["id"] == product_id:
            return {"product_id": product_id, "stock": p["stock"]}
    return {"product_id": product_id, "stock": 0}

@tool
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

@tool
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

@tool
def get_address(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.addresses)).filter_by(email=user_id).first()
    if user and user.addresses:
        result = user.addresses[0].address
    else:
        result = "No address set."
    session.close()
    return result

@tool
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

@tool
def get_size(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.sizes)).filter_by(email=user_id).first()
    if user and user.sizes:
        result = user.sizes[0].size
    else:
        result = "No size set."
    session.close()
    return result

@tool
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

@tool
def get_calendar_location(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.travels:
        return user.travels[0].location if user.travels else "office"
    return "office"

@tool
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

@tool
def get_payment_method(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.payments)).filter_by(email=user_id).first()
    if user and user.payments:
        result = user.payments[0].method
    else:
        result = "No payment method set."
    session.close()
    return result

@tool
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

@tool
def get_preference(user_id: str, key: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.preferences:
        pref = next((p for p in user.preferences if p.key == key), None)
        return pref.value if pref else "Not set"
    return "Not set"

@tool
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

@tool
def get_travel_status(user_id: str) -> dict:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.travels)).filter_by(email=user_id).first()
    if user and user.travels:
        travel = user.travels[0]
        result = {"status": travel.status, "location": travel.location}
    else:
        result = {"status": "home", "location": get_address(user_id)}
    session.close()
    return result

@tool
def checkout(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.addresses), joinedload(User.carts)).filter_by(email=user_id).first()
    if not user:
        session.close()
        return "User not found. Please register."

    if not user.addresses:
        session.close()
        return "No address set. Please provide a shipping address before checkout."

    order_id = str(uuid.uuid4())
    order = Order(user_id=user.id, address=user.addresses[0].address, status="Processing")
    session.add(order)
    session.commit()  # Commit to get order.id

    for item in user.carts:
        product = next((p for p in PRODUCTS if p["id"] == item.product_id), None)
        if product:
            order_item = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity)
            session.add(order_item)
            product["stock"] = max(0, product["stock"] - item.quantity)
        session.delete(item)  # Remove from cart after checkout

    session.commit()
    session.close()
    return f"Order placed! Your order ID is {order_id}."

@tool
def check_order_status(order_id: str) -> str:
    session = SessionLocal()
    order = session.query(Order).filter_by(id=int(order_id)).first()
    session.close()
    if not order:
        return "Order not found."
    return f"Order {order_id} for {order.user.email} is currently: {order.status}"

def check_delivery_date(product_id: str, zip_code: str) -> str:
    return f"Estimated delivery for {product_id} to {zip_code}: 3-5 business days."

@tool
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

@tool
def get_birthday(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).filter_by(email=user_id).first()
    session.close()
    if user and user.birthdays:
        return user.birthdays[0].birthday if user.birthdays else ""
    return ""

@tool
def get_order_history(user_id: str) -> List[Dict]:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.orders)).filter_by(email=user_id).first()
    if not user or not user.orders:
        result = []
    else:
        result = [
            {
                "id": o.id,
                "address": o.address,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None
            }
            for o in user.orders
        ]
    session.close()
    return result

@tool
def is_duplicate_order(user_id: str, product_id: str) -> bool:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.orders).joinedload(Order.items)).filter_by(email=user_id).first()
    found = False
    if user and user.orders:
        for order in user.orders:
            for item in order.items:
                if item.product_id == product_id:
                    found = True
                    break
            if found:
                break
    session.close()
    return found

@tool
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

@tool
def get_concierge_tone(user_id: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.preferences)).filter_by(email=user_id).first()
    if user and user.preferences:
        pref = next((p for p in user.preferences if p.key == "concierge_tone"), None)
        result = pref.value if pref else "professional"
    else:
        result = "professional"
    session.close()
    return result

# --- Persistent Memory Setup ---
memory = Memory(
    db=SqliteMemoryDb(table_name="memory", db_file="memory.db"),
)

# --- Shopping Session State Helper ---
class ShoppingSession:
    def __init__(self, memory: Memory, user_id: str, session_id: str):
        self.memory = memory
        self.user_id = user_id
        self.session_id = session_id

    def get_slot(self, slot: str) -> Optional[str]:
        return self.memory.get(f"shopping_{slot}", user_id=self.user_id, session_id=self.session_id)

    def set_slot(self, slot: str, value: str):
        self.memory.set(f"shopping_{slot}", value, user_id=self.user_id, session_id=self.session_id)

    def clear(self):
        for slot in ["product", "size", "address", "payment"]:
            self.memory.delete(f"shopping_{slot}", user_id=self.user_id, session_id=self.session_id)

# Example usage in tool functions (pseudo):
# session = ShoppingSession(memory, user_id, session_id)
# session.set_slot("product", "Classic Blue Jeans")
# size = session.get_slot("size")

# --- Concierge Instructions ---
concierge_instructions = [
    "You are a discreet, highly efficient shopping concierge for HNI clients.",
    "Current User ID: {current_user_id}",
    "Current Session ID: {current_session_id}",
    "Always be brief, direct, and professional. Responses must be short, crisp, and perfect—never verbose.",
    "Never mention user_id, email, or tool call arguments in your response.",
    "Maintain a shopping session state for each user and session, tracking the current product, size, address, and payment method.",
    "When a user requests a product, always show product details (name, brand, price, stock) before proceeding, and store the product in session state.",
    "If the user provides a size, address, or payment, update the session state accordingly.",
    "If the user refers to 'the jeans', 'the 32 one', or similar, use the most recently discussed product and size from the session state.",
    "If multiple products match, list options and ask the user to choose, then store the choice in session state.",
    "Before placing an order, confirm all key details: product, size (if relevant), delivery address, and payment method. Summarize these for the user and ask for explicit confirmation before placing the order.",
    "If information is missing (e.g., size, address, payment), summarize what is needed and politely ask only for the missing detail.",
    "If an item is out of stock, suggest alternatives or offer to notify when available.",
    "Example: 'I found Classic Blue Jeans by Levi's ($89.99, in stock). What size would you like?'",
    "Example: 'Great! Size 32 selected. Your delivery address is 123 Main St, Springfield, 90210, and payment will be with Visa ending 5678. Shall I place the order?'",
    "Example: 'Order placed: Classic Blue Jeans (size: 32). Delivery: 123 Main St, Springfield, 90210. Payment: Visa ending 5678.'",
    "Example: 'Sorry, the requested item is out of stock. Would you like to try a different color or brand?'",
    "Example: 'Please provide your preferred size for the green hoodie.'",
    "Example: 'Here are a few options: 1) Classic Blue Jeans by Levi's, 2) Slim Fit Jeans by Zara. Which do you prefer?'",
    "Example: 'You mentioned size 32 earlier. Would you like to use that for these jeans as well?'",
    "Example: 'You previously selected Classic Blue Jeans. Would you like to proceed with that product?'",
    "Responses must be natural, never robotic or verbose.",
    "Tone: short, crisp, professional, and user-friendly. If a specific brand or persona is set, match that style (e.g., luxury, playful, ultra-formal, minimalist, etc.).",
]

# --- Create the Concierge Shopping Agent ---
shopping_agent = AgnoAgent(
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
    add_state_in_messages=True,
)

# --- Coffee Agent Tool Functions ---
def get_coffee_menu() -> list:
    return [
        {"id": "c1", "name": "Espresso", "sizes": ["small", "medium", "large"], "price": 3.0},
        {"id": "c2", "name": "Latte", "sizes": ["small", "medium", "large"], "price": 4.0},
        {"id": "c3", "name": "Cappuccino", "sizes": ["small", "medium", "large"], "price": 4.5},
        {"id": "c4", "name": "Cold Brew", "sizes": ["medium", "large"], "price": 4.0},
    ]

@tool
def order_coffee(user_id: str, coffee_id: str, size: str = "medium") -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.addresses), joinedload(User.payments), joinedload(User.preferences)).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    menu = get_coffee_menu()
    coffee = next((c for c in menu if c["id"] == coffee_id), None)
    if not coffee:
        session.close()
        return "Sorry, that coffee is not available."
    address = user.addresses[0].address if user.addresses else "No address set"
    payment = user.payments[0].method if user.payments else "No payment method set"
    session.close()
    return f"Ordered a {size} {coffee['name']} for {user_id}, to be delivered to {address}, paid with {payment}."

@tool
def get_coffee_pref(user_id: str, key: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.preferences)).filter_by(email=user_id).first()
    session.close()
    if user and user.preferences:
        pref = next((p for p in user.preferences if p.key == key), None)
        return pref.value if pref else "Not set"
    return "Not set"

@tool
def set_coffee_pref(user_id: str, key: str, value: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.preferences)).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    user.preferences.append(Preference(key=key, value=value))
    session.commit()
    session.close()
    return f"Coffee preference {key} set to {value}"

# --- Coffee Agent ---

coffee_agent = AgnoAgent(
    name="Coffee Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[
        get_coffee_menu,
        order_coffee,
        get_coffee_pref,
        set_coffee_pref,
        get_address,  # shared
        set_address,  # shared
        get_payment_method,  # shared
        set_payment_method,  # shared
    ],
    enable_user_memories=True,
    add_history_to_messages=True,
    num_history_runs=3,
    instructions=[
        "You are a coffee ordering assistant.",
        "The user_id argument is always provided by the system and is the user's email (e.g., priya@example.com). Never ask the user for their email or user_id. Always use the user_id argument passed to you for all tool calls.",
        "Always confirm orders and preferences in short, crisp, user-friendly language.",
        "Never mention user_id, email, or tool call arguments in your response.",
        "If information is missing (e.g., size, type), politely ask only for the missing detail.",
        "If an item is unavailable, suggest alternatives or offer to notify when available.",
        "Example: 'Coffee preference updated: size large.'",
        "Example: 'Latte (size: large) ordered.'",
        "Example: 'Order cancelled.'",
        "Example: 'Sorry, cappuccino is not available in large. Would you like medium instead?'",
        "Example: 'Please specify your preferred coffee type.'",
        "Responses must be natural, never robotic or verbose.",
        "Tone: short, crisp, professional, and user-friendly. If a specific brand or persona is set, match that style.",
    ],
    show_tool_calls=True,
    markdown=True,
    add_state_in_messages=True,
)

# --- Shared User Profile Agent Tool Functions ---
@tool
def set_user_address(user_id: str, address: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.addresses)).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    if user.addresses:
        user.addresses[0].address = address
    else:
        user.addresses.append(Address(address=address))
    session.commit()
    session.close()
    return f"Address updated to {address}."

@tool
def set_payment_method(user_id: str, method: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.payments)).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    if user.payments:
        user.payments[0].method = method
    else:
        user.payments.append(Payment(method=method))
    session.commit()
    session.close()
    return f"Payment method set to {method}."

@tool
def set_user_pref(user_id: str, key: str, value: str) -> str:
    session = SessionLocal()
    user = session.query(User).options(joinedload(User.preferences)).filter_by(email=user_id).first()
    if not user:
        user = User(email=user_id)
        session.add(user)
        session.commit()
    pref = next((p for p in user.preferences if p.key == key), None)
    if pref:
        pref.value = value
    else:
        user.preferences.append(Preference(key=key, value=value))
    session.commit()
    session.close()
    return f"Preference {key} set to {value} for the user."

# --- User Profile Agent ---
user_profile_agent = AgnoAgent(
    name="User Profile Agent",
    model=OpenAIChat(id="gpt-4o"),
    tools=[set_user_address, set_payment_method, set_user_pref],
    enable_user_memories=True,
    add_history_to_messages=True,
    num_history_runs=3,
    instructions=[
        "You manage user preferences, addresses, and payment methods.",
        "The user_id argument is always provided by the system and is the user's email (e.g., priya@example.com). Never ask the user for their email or user_id. Always use the user_id argument passed to you for all tool calls.",
        "Always confirm updates in short, crisp, user-friendly language.",
        "Never mention user_id, email, or tool call arguments in your response.",
        "If information is missing, politely ask only for the missing detail.",
        "Example: 'Address updated to 123 Main St, Springfield, 90210.'",
        "Example: 'Payment method set to Visa ending 5678.'",
        "Example: 'Preference updated: style=casual.'",
        "Example: 'Please provide your preferred payment method.'",
        "Responses must be natural, never robotic or verbose.",
        "Tone: short, crisp, professional, and user-friendly. If a specific brand or persona is set, match that style.",
    ],
    show_tool_calls=True,
    markdown=True,
    add_state_in_messages=True,
)

# --- Orchestrator Team ---
orchestrator_team = Team(
    name="Orchestrator Team",
    mode="route",
    model=OpenAIChat("gpt-4o"),
    members=[user_profile_agent, shopping_agent, coffee_agent],
    show_tool_calls=True,
    markdown=True,
    show_members_responses=True,
    instructions=[
        "You are an orchestrator that routes user requests to the appropriate agent.",
        "If the request is about preferences, address, or payment, route to the user profile agent.",
        "If the request is about shopping (clothes, fashion, etc.), route to the shopping agent.",
        "If the request is about coffee or drinks, route to the coffee agent.",
        "The user_id argument is always provided by the system and is the user's email (e.g., priya@example.com). Never ask the user for their email or user_id.",
        "Preferences are global and managed by the user profile agent.",
        "Current User ID: {current_user_id}",
        "Current Session ID: {current_session_id}",
    ],
    add_state_in_messages=True,
)

# --- Example Usage ---
if __name__ == "__main__":
    user_id = "priya@example.com"
    session_id = "priya_session_1"
    print("=== Orchestrator Team Chat (as priya@example.com) ===")
    print("Type 'exit' or 'quit' to end the chat.\n")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        orchestrator_team.print_response(user_input, user_id=user_id, session_id=session_id)
