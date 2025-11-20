import streamlit as st
import json
from drive_through_assistant import DriveThroughAssistant


# Page configuration
st.set_page_config(
    page_title="AI Drive-Through Assistant",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stChatMessage {
        padding: 1rem;
    }
    .order-item {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background-color: gray;
        border-radius: 0.5rem;
        border-left: 3px solid #1f77b4;
    }
    .menu-item {
        padding: 0.75rem;
        margin: 0.5rem 0;
        background-color: gray;
        border-radius: 0.5rem;
        border-left: 3px solid #2ca02c;
    }
    .menu-item strong {
        font-size: 1.05em;
    }
    .order-item strong {
        font-size: 1.05em;
    }
    .total-box {
        background-color: gray;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 0.5rem;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


# Initialize session state
if "assistant" not in st.session_state:
    st.session_state.assistant = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "initialized" not in st.session_state:
    st.session_state.initialized = False


# Default menu
DEFAULT_MENU = {
    'Big Mac': 5,
    'Large Fry': 3,
    'Coke': 2
}

# Default model for OpenRouter
DEFAULT_MODEL = "meta-llama/llama-3.2-3b-instruct:free"


def initialize_assistant():
    """Initialize the DriveThroughAssistant with API key and model."""
    api_key = st.session_state.get("api_key_input", None)
    
    if not api_key:
        st.error("⚠️ Please enter your OpenRouter API key in the sidebar to start.")
        return False
    
    try:
        model = st.session_state.get("model_input", DEFAULT_MODEL)
        menu = st.session_state.get("custom_menu", DEFAULT_MENU)
        
        assistant = DriveThroughAssistant(
            api_key=api_key,
            model=model,
            menu=menu
        )
        
        st.session_state.assistant = assistant
        st.session_state.initialized = True
        return True
    except Exception as e:
        st.error(f"Error initializing assistant: {str(e)}")
        return False


# Sidebar configuration
with st.sidebar:
    st.title("🍔 Drive-Through Setup")
    
    # API Key input
    api_key = st.text_input(
        "OpenRouter API Key",
        type="password",
        key="api_key_input",
        help="Enter your OpenRouter API key"
    )
    
    # Model selection
    model = st.selectbox(
        "Model",
        options=[
            "meta-llama/llama-3.2-3b-instruct:free",
            "openai/gpt-3.5-turbo",
            "openai/gpt-4",
            "anthropic/claude-3-haiku",
            "anthropic/claude-3-sonnet",
            "google/gemini-pro",
        ],
        index=0,
        key="model_input",
        help="Select the LLM model to use"
    )
    
    # Initialize button
    if st.button("Initialize Assistant", type="primary"):
        if api_key:
            if initialize_assistant():
                st.success("✅ Assistant initialized!")
                st.session_state.messages = []
            else:
                st.error("❌ Failed to initialize assistant.")
        else:
            st.error("⚠️ Please enter an API key first.")
    
    # Display current model being used
    if st.session_state.assistant:
        st.info(f"🤖 **Current Model:**\n`{st.session_state.assistant.model}`")
    
    st.divider()
    
    # Menu display
    st.subheader("📋 Menu")
    menu_to_display = st.session_state.get("custom_menu", DEFAULT_MENU)
    
    if menu_to_display:
        for item, price in menu_to_display.items():
            st.markdown(f"""
            <div class="menu-item">
                <strong>{item}</strong><br>
                <span style="color: white; font-size: 0.9em;">${price:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No menu items available.")
    
    st.divider()
    
    # Current order display
    st.subheader("🛒 Current Order")
    
    if st.session_state.assistant:
        current_order = st.session_state.assistant.current_order
        
        if current_order:
            st.markdown("---")
            for item, qty in current_order.items():
                price = menu_to_display.get(item, 0)
                item_total = price * qty
                st.markdown(f"""
                <div class="order-item">
                    <strong>{item}</strong><br>
                    <span style="color: white;">Quantity: {qty} × ${price:.2f} = <strong>${item_total:.2f}</strong></span>
                </div>
                """, unsafe_allow_html=True)
            
            total = st.session_state.assistant.calculate_total()
            st.markdown(f"""
            <div class="total-box">
                <h3 style="margin: 0;">Total: ${total:.2f}</h3>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
            
            # Clear order button
            if st.button("🗑️ Clear Order", type="secondary", use_container_width=True):
                st.session_state.assistant.clear_order()
                st.session_state.messages = []
                st.rerun()
        else:
            st.info("No items in order yet.")
    else:
        st.info("Initialize assistant to see orders.")
    
    st.divider()
    
    # Order history
    st.subheader("📜 Order History")
    if st.session_state.assistant and st.session_state.assistant.history:
        # Show last few history entries
        for i, msg in enumerate(st.session_state.assistant.history[-5:]):
            if msg["role"] == "user":
                st.caption(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                st.caption(f"Assistant: {msg['content']}")
    else:
        st.info("No history yet.")


# Main area - Chat interface
st.title("🤖 AI Drive-Through Assistant")
st.caption("Place your order by chatting with the AI assistant!")

# Display current model if initialized
if st.session_state.initialized and st.session_state.assistant:
    st.caption(f"**Model:** `{st.session_state.assistant.model}`")

# Check if assistant is initialized
if not st.session_state.initialized or not st.session_state.assistant:
    st.info("👈 Please initialize the assistant using the sidebar configuration.")
    st.stop()

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to order?"):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process message with assistant
    with st.chat_message("assistant"):
        with st.spinner("Processing your order..."):
            try:
                # Get menu for pricing
                menu_for_display = st.session_state.get("custom_menu", DEFAULT_MENU)
                
                # Process the message - now returns (order, message)
                updated_order, ai_message = st.session_state.assistant.process_user_message(prompt)
                
                # Display the AI's conversational response
                st.markdown(ai_message)
                
                # Also show current order details if there are items
                if updated_order:
                    st.markdown("\n**Current Order:**")
                    for item, qty in updated_order.items():
                        price = menu_for_display.get(item, 0)
                        st.markdown(f"- {item} × {qty} = ${price * qty:.2f}")
                    
                    total = st.session_state.assistant.calculate_total()
                    st.markdown(f"\n**Total: ${total:.2f}**")
                
                # Format full response for message history
                response = ai_message
                if updated_order:
                    response_parts = [ai_message, "\n**Current Order:**"]
                    for item, qty in updated_order.items():
                        price = menu_for_display.get(item, 0)
                        response_parts.append(f"- {item} × {qty} = ${price * qty:.2f}")
                    response_parts.append(f"\n**Total: ${st.session_state.assistant.calculate_total():.2f}**")
                    response = "\n".join(response_parts)
                
                # Add assistant response to messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                
            except Exception as e:
                error_msg = f"❌ Error processing your order: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
    
    # Rerun to update sidebar with new order
    st.rerun()

