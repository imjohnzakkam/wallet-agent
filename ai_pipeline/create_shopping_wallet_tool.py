from typing import List, Optional
from backend.api.shopping_list import create_shopping_list_pass as generate_pass_link

def create_shopping_list_pass(
    items: List[str],
    store: Optional[str] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Creates a shopping list wallet pass with the given items.

    Args:
        items: A list of items for the shopping list.
        store: The store where the items can be purchased.
        notes: Any additional notes for the shopping list.
    
    Returns:
        A dictionary representing the created shopping list pass with a wallet link.
    """
    
    title = f"Shopping list for {store}" if store else "My Shopping List"
    
    current_items = items[:] # create a copy
    if notes:
        current_items.append(f"Notes: {notes}")

    # Generate the Google Wallet pass link
    wallet_link = generate_pass_link(items=current_items, title=store)
    
    print(f"Shopping list created with items: {items}, store: {store}, notes: {notes}")
    
    shopping_list_data = {
        "items": items,
        "store": store,
        "notes": notes,
        "wallet_link": wallet_link
    }
    
    return shopping_list_data