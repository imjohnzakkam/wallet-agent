import logging
from typing import Dict, List
from backend.firestudio.firebase import FirebaseClient


logger = logging.getLogger(__name__)

def _fetch_receipts(db_client: FirebaseClient, user_id: str, params: Dict) -> List[Dict]:
    """Fetch receipts from Firestore based on query parameters."""
    if not db_client:
        logger.warning("Firestore is not available. Cannot fetch receipts.")
        return []

    try:
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        receipts = db_client.get_receipts_by_timerange(user_id, start_date, end_date)

        if params.get("category"):
            receipts = [r for r in receipts if r.get('category') == params["category"]]
        if params.get("vendor_name"):
            receipts = [r for r in receipts if r.get('vendor_name') == params["vendor_name"]]
        if params.get("amount_condition"):
            cond = params["amount_condition"]
            op = cond.get("operator")
            val = float(cond.get("value", 0))
            op_map = {"gt": lambda x: x > val, "lt": lambda x: x < val, "eq": lambda x: x == val}
            if op in op_map:
                receipts = [r for r in receipts if op_map[op](r.get('amount', 0))]

        logger.info(f"Fetched and filtered {len(receipts)} receipts for user {user_id} with params {params}")
        return receipts

    except Exception as e:
        logger.error(f"Error fetching receipts from Firestore: {e}", exc_info=True)
        return []

def find_purchases(start_date: str, end_date: str, db_client=None, user_id: str = None) -> List[Dict]:
    """
    Finds purchase records for a user within a specified date range.
    Args:
        start_date: The start date in YYYY-MM-DD format. Relative dates like 'first day of this month' are acceptable.
        end_date: The end date in YYYY-MM-DD format. Relative dates like 'today' are acceptable.
        db_client: The Firebase client. This is an internal parameter.
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: find_purchases for user {user_id} from {start_date} to {end_date}")
    params = {"start_date": start_date, "end_date": end_date}
    return _fetch_receipts(db_client, user_id, params)

def get_largest_purchase(purchases: List[Dict]) -> Dict:
    """
    Finds the single largest purchase from a list of purchases.
    Use the result of 'find_purchases' as input.
    Args:
        purchases: A list of purchase records, where each record is a dictionary.
    """
    logger.info("TOOL: get_largest_purchase")
    if not purchases:
        return {}
    return max(purchases, key=lambda p: p.get('amount', 0))

def get_spending_for_category(category: str, start_date: str, end_date: str, db_client=None, user_id: str = None) -> float:
    """
    Calculates the total spending for a given category in a date range.
    Args:
        category: The category to analyze (e.g., 'grocery', 'fuel').
        start_date: The start date for the analysis in YYYY-MM-DD format.
        end_date: The end date for the analysis in YYYY-MM-DD format.
        db_client: The Firebase client. This is an internal parameter.
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_spending_for_category for user {user_id} in '{category}' from {start_date} to {end_date}")
    params = {"start_date": start_date, "end_date": end_date, "category": category}
    receipts = _fetch_receipts(db_client, user_id, params)
    total_spending = sum(r.get('amount', 0) for r in receipts)
    return total_spending 

all_tool_calls ={
    "find_purchases": find_purchases,
    "get_largest_purchase": get_largest_purchase,
    "get_spending_for_category": get_spending_for_category,
}