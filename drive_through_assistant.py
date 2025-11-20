import json
import requests


def get_response_from_messages_openrouter(api_key, model, messages, temperature=0.1):
    """
    Call OpenRouter API to get LLM response.
    
    Args:
        api_key: OpenRouter API key
        model: Model identifier (e.g., 'openai/gpt-3.5-turbo', 'anthropic/claude-3-haiku')
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature
    
    Returns:
        Response text from the model
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",  # Optional: For usage tracking
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Extract the response text
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise ValueError("Unexpected API response format")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"OpenRouter API error: {str(e)}")


class DriveThroughAssistant:
    def __init__(self, api_key, model, menu):
        self.api_key = api_key
        self.model = model
        self.menu = menu
        self.current_order = {}  # State: {'Item Name': Quantity}
        self.history = []        # Context: List of past messages

    def get_system_prompt(self):
        # We inject the CURRENT ORDER status directly into the prompt
        menu_items = ", ".join(self.menu.keys())
        return f"""
You are a smart drive-through cashier.

MENU:
{json.dumps(self.menu, indent=2)}

CURRENT ORDER STATE:
{json.dumps(self.current_order, indent=2)}

INSTRUCTIONS:
1. Update the 'CURRENT ORDER STATE' based on the user's new message.
2. Handle additions, removals, and substitutions (e.g., "switch X for Y").
3. If the user tries to order something NOT on the menu, inform them clearly that the item does not exist.
4. Output a JSON object with two fields:
   - "message": A brief conversational response (e.g., "Added Big Mac to your order", "Item does not exist: Pizza", "Removed Large Fry", "Updated: Changed Coke to Large Fry")
   - "order": The NEW FINAL ORDER STATE as a JSON object

IMPORTANT:
- The "message" should be concise and friendly (1-2 sentences max)
- If an item is NOT on the menu, set the message to indicate that the item does not exist
- Only include items that are actually on the menu in the "order" field

Example Output format:
{{
    "message": "Added 2 Big Macs and 1 Large Fry to your order",
    "order": {{
        "Big Mac": 2,
        "Large Fry": 1
    }}
}}

Or if item doesn't exist:
{{
    "message": "Item does not exist: Pizza. Available items are: {menu_items}",
    "order": {{
        "Big Mac": 1
    }}
}}
"""

    def process_user_message(self, user_input):
        # 1. Add user message to history (for context)
        self.history.append({"role": "user", "content": user_input})

        # 2. Construct the full prompt
        # Note: We put the system prompt LAST or re-insert it so the LLM 
        # always sees the up-to-date 'Current Order' clearly.
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
        ]

        # Append only the last few turns of conversation to save tokens/confusion
        # (Optional: strictly speaking, in this State Update approach, 
        # you often only need the immediate last command if the State is accurate, 
        # but keeping history helps with context like "No, the other one")
        messages.extend(self.history[-3:])

        # 3. Call the Model
        response_text = get_response_from_messages_openrouter(
            self.api_key, self.model, messages, temperature=0.1
        )

        # 4. Update State
        ai_message = "Order updated."
        try:
            # Clean up potential markdown wrapping like ```json ... ```
            clean_text = response_text.replace("```json", "").replace("```", "").strip()

            # Parse JSON
            response_data = json.loads(clean_text)

            # Extract message and order from response
            if isinstance(response_data, dict):
                # New format with message and order fields
                if "message" in response_data:
                    ai_message = response_data["message"]
                if "order" in response_data:
                    new_order_state = response_data["order"]
                else:
                    # Fallback: treat whole response as order (backwards compatibility)
                    new_order_state = response_data
            else:
                # Fallback: response is just the order
                new_order_state = response_data

            # Validate against menu (Double check to ensure no hallucinations)
            validated_order = {k: v for k, v in new_order_state.items() if k in self.menu}

            self.current_order = validated_order

            # Add AI response to history
            self.history.append({
                "role": "assistant",
                "content": ai_message
            })

            return self.current_order, ai_message
        except json.JSONDecodeError:
            error_msg = "Error: LLM did not output valid JSON."
            print(error_msg)
            print("Raw output:", response_text)
            self.history.append({
                "role": "assistant",
                "content": "Sorry, I had trouble processing that. Please try again."
            })
            return self.current_order, "Sorry, I had trouble processing that. Please try again."
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print(error_msg)
            self.history.append({
                "role": "assistant",
                "content": "Sorry, I encountered an error. Please try again."
            })
            return self.current_order, "Sorry, I encountered an error. Please try again."

    def calculate_total(self):
        total = 0
        for item, qty in self.current_order.items():
            price = self.menu.get(item, 0)
            total += price * qty
        return total

    def clear_order(self):
        """Reset the order and history."""
        self.current_order = {}
        self.history = []

