import logging
from typing import Dict, List
from backend.firestudio.firebase import FirebaseClient
from collections import defaultdict, Counter
import statistics
from datetime import datetime, timedelta


# Initialize the client globally
db_client = FirebaseClient()

logger = logging.getLogger(__name__)

def _fetch_receipts(user_id: str, params: Dict) -> List[Dict]:
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

def _fetch_receipts_all_categories(start_date: str, end_date: str, user_id: str = None) -> List[Dict]:
    """
    Fetches all receipts for a user within a specified date range, without any filtering.

    This is a convenience wrapper around `_fetch_receipts` that simplifies fetching
    all receipts between two dates.

    Args:
        start_date: The start date in YYYY-MM-DD format.
        end_date: The end date in YYYY-MM-DD format.
        user_id: The identifier for the user.

    Returns:
        A list of all receipt dictionaries within the date range.
    """
    params = {"start_date": start_date, "end_date": end_date}
    return _fetch_receipts(user_id, params)

def find_purchases(start_date: str, end_date: str, user_id: str = None) -> List[Dict]:
    """
    Finds purchase records for a user within a specified date range.
    Args:
        start_date: The start date in YYYY-MM-DD format. Relative dates like 'first day of this month' are acceptable.
        end_date: The end date in YYYY-MM-DD format. Relative dates like 'today' are acceptable.
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: find_purchases for user {user_id} from {start_date} to {end_date}")
    return _fetch_receipts_all_categories(start_date, end_date, user_id)

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

def get_spending_for_category(category: str, start_date: str, end_date: str, user_id: str = None) -> float:
    """
    Calculates the total spending for a given category in a date range.
    Args:
        category: The category to analyze (e.g., 'grocery', 'fuel').
        start_date: The start date for the analysis in YYYY-MM-DD format.
        end_date: The end date for the analysis in YYYY-MM-DD format.
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_spending_for_category for user {user_id} in '{category}' from {start_date} to {end_date}")
    params = {"start_date": start_date, "end_date": end_date, "category": category}
    receipts = _fetch_receipts(user_id, params)
    total_spending = sum(r.get('amount', 0) for r in receipts)
    return total_spending 


def get_average_daily_spending(start_date: str, end_date: str, user_id: str = None) -> float:
    """
    Calculates the average daily spending within a date range.
    Args:
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_average_daily_spending for user {user_id}")
    receipts = _fetch_receipts_all_categories(start_date, end_date, user_id)
    if not receipts:
        return 0.0
    
    total_amount = sum(r.get('amount', 0) for r in receipts)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days = (end - start).days + 1
    
    return total_amount / days if days > 0 else 0.0

def get_spending_by_day_of_week(start_date: str, end_date: str, user_id: str = None) -> Dict[str, float]:
    """
    Analyzes spending patterns by day of the week.
    Args:
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_spending_by_day_of_week for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    day_spending = defaultdict(float)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for receipt in receipts:
        if 'date' in receipt:
            date = datetime.strptime(receipt['date'], '%Y-%m-%d')
            day_name = days[date.weekday()]
            day_spending[day_name] += receipt.get('amount', 0)
    
    return dict(day_spending)

def get_monthly_spending_trend(months: int, user_id: str = None) -> List[Dict[str, float]]:
    """
    Returns monthly spending totals for the past N months.
    Args:
        months: Number of months to analyze
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_monthly_spending_trend for user {user_id} for {months} months")
    end_date = datetime.now()
    monthly_totals = []
    
    for i in range(months):
        month_end = end_date.replace(day=1) - timedelta(days=1)
        month_start = month_end.replace(day=1)
        
        if i == 0:  # Current month
            month_end = end_date
        
        receipts = _fetch_receipts(user_id, {
            "start_date": month_start.strftime('%Y-%m-%d'),
            "end_date": month_end.strftime('%Y-%m-%d')
        })
        
        total = sum(r.get('amount', 0) for r in receipts)
        monthly_totals.append({
            "month": month_start.strftime('%B %Y'),
            "total": total
        })
        
        end_date = month_start - timedelta(days=1)
    
    return list(reversed(monthly_totals))

# ========== VENDOR AND CATEGORY ANALYSIS ==========

def get_top_vendors(limit: int, start_date: str, end_date: str, user_id: str = None) -> List[Dict]:
    """
    Returns the top vendors by total spending.
    Args:
        limit: Maximum number of vendors to return
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_top_vendors for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    vendor_spending = defaultdict(lambda: {"total": 0, "count": 0})
    
    for receipt in receipts:
        vendor = receipt.get('vendor_name', 'Unknown')
        vendor_spending[vendor]["total"] += receipt.get('amount', 0)
        vendor_spending[vendor]["count"] += 1
    
    sorted_vendors = sorted(
        vendor_spending.items(), 
        key=lambda x: x[1]["total"], 
        reverse=True
    )[:limit]
    
    return [
        {
            "vendor": vendor,
            "total_spent": data["total"],
            "transaction_count": data["count"],
            "average_per_transaction": data["total"] / data["count"] if data["count"] > 0 else 0
        }
        for vendor, data in sorted_vendors
    ]

def get_category_breakdown(start_date: str, end_date: str, user_id: str = None) -> Dict[str, Dict]:
    """
    Provides a detailed breakdown of spending by category.
    Args:
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_category_breakdown for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    category_data = defaultdict(lambda: {"total": 0, "count": 0, "items": []})
    
    for receipt in receipts:
        category = receipt.get('category', 'Uncategorized')
        category_data[category]["total"] += receipt.get('amount', 0)
        category_data[category]["count"] += 1
        
        if 'items' in receipt:
            category_data[category]["items"].extend(receipt['items'])
    
    return {
        cat: {
            "total_spent": data["total"],
            "transaction_count": data["count"],
            "percentage": 0,  # Will be calculated later
            "average_per_transaction": data["total"] / data["count"] if data["count"] > 0 else 0
        }
        for cat, data in category_data.items()
    }

# ========== ITEM AND INVENTORY TRACKING ==========

def get_frequently_purchased_items(min_frequency: int, start_date: str, end_date: str, user_id: str = None) -> List[Dict]:
    """
    Finds items that have been purchased at least N times.
    Args:
        min_frequency: Minimum number of times an item must be purchased
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_frequently_purchased_items for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    item_counter = Counter()
    item_details = defaultdict(lambda: {"total_spent": 0, "prices": []})
    
    for receipt in receipts:
        if 'items' in receipt:
            for item in receipt['items']:
                item_name = item.get('name', '').lower().strip()
                if item_name:
                    item_counter[item_name] += 1
                    item_details[item_name]["total_spent"] += item.get('price', 0)
                    item_details[item_name]["prices"].append(item.get('price', 0))
    
    frequent_items = []
    for item_name, count in item_counter.items():
        if count >= min_frequency:
            prices = item_details[item_name]["prices"]
            frequent_items.append({
                "item": item_name,
                "purchase_count": count,
                "total_spent": item_details[item_name]["total_spent"],
                "average_price": statistics.mean(prices) if prices else 0,
                "price_variance": statistics.stdev(prices) if len(prices) > 1 else 0
            })
    
    return sorted(frequent_items, key=lambda x: x["purchase_count"], reverse=True)

def check_inventory_status(item_names: List[str], user_id: str = None) -> Dict[str, Dict]:
    """
    Checks when specific items were last purchased and estimates if they need replenishment.
    Args:
        item_names: List of item names to check
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: check_inventory_status for user {user_id}")
    # Get receipts from the last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    })
    
    inventory_status = {}
    
    for item_name in item_names:
        item_lower = item_name.lower().strip()
        last_purchase = None
        purchase_dates = []
        
        for receipt in receipts:
            if 'items' in receipt:
                for item in receipt['items']:
                    if item_lower in item.get('name', '').lower():
                        purchase_date = datetime.strptime(receipt['date'], '%Y-%m-%d')
                        purchase_dates.append(purchase_date)
                        if not last_purchase or purchase_date > last_purchase:
                            last_purchase = purchase_date
        
        if last_purchase:
            days_since = (datetime.now() - last_purchase).days
            
            # Calculate average purchase interval if multiple purchases
            avg_interval = None
            if len(purchase_dates) > 1:
                purchase_dates.sort()
                intervals = [(purchase_dates[i+1] - purchase_dates[i]).days 
                           for i in range(len(purchase_dates)-1)]
                avg_interval = statistics.mean(intervals) if intervals else None
            
            inventory_status[item_name] = {
                "last_purchased": last_purchase.strftime('%Y-%m-%d'),
                "days_since_purchase": days_since,
                "purchase_count": len(purchase_dates),
                "average_purchase_interval": avg_interval,
                "needs_replenishment": days_since > (avg_interval * 1.2) if avg_interval else False
            }
        else:
            inventory_status[item_name] = {
                "last_purchased": None,
                "days_since_purchase": None,
                "purchase_count": 0,
                "average_purchase_interval": None,
                "needs_replenishment": None
            }
    
    return inventory_status

# ========== SAVINGS AND BUDGET ANALYSIS ==========

def detect_recurring_subscriptions(user_id: str = None) -> List[Dict]:
    """
    Identifies potential recurring subscriptions based on spending patterns.
    Args:
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: detect_recurring_subscriptions for user {user_id}")
    # Look at the last 90 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    })
    
    vendor_transactions = defaultdict(list)
    
    for receipt in receipts:
        vendor = receipt.get('vendor_name')
        if vendor:
            vendor_transactions[vendor].append({
                "date": datetime.strptime(receipt['date'], '%Y-%m-%d'),
                "amount": receipt.get('amount', 0)
            })
    
    subscriptions = []
    
    for vendor, transactions in vendor_transactions.items():
        if len(transactions) >= 2:
            # Sort by date
            transactions.sort(key=lambda x: x['date'])
            
            # Check if amounts are similar
            amounts = [t['amount'] for t in transactions]
            avg_amount = statistics.mean(amounts)
            amount_variance = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            # Check if intervals are regular
            intervals = []
            for i in range(len(transactions) - 1):
                interval = (transactions[i+1]['date'] - transactions[i]['date']).days
                intervals.append(interval)
            
            if intervals:
                avg_interval = statistics.mean(intervals)
                interval_variance = statistics.stdev(intervals) if len(intervals) > 1 else 0
                
                # Detect if likely subscription (low variance in amount and interval)
                is_likely_subscription = (
                    amount_variance < avg_amount * 0.1 and  # Amount varies less than 10%
                    interval_variance < avg_interval * 0.2 and  # Interval varies less than 20%
                    25 <= avg_interval <= 35  # Monthly-ish
                )
                
                if is_likely_subscription:
                    subscriptions.append({
                        "vendor": vendor,
                        "estimated_monthly_cost": avg_amount,
                        "transaction_count": len(transactions),
                        "average_interval_days": avg_interval,
                        "last_charge": transactions[-1]['date'].strftime('%Y-%m-%d'),
                        "next_expected_charge": (transactions[-1]['date'] + timedelta(days=int(avg_interval))).strftime('%Y-%m-%d')
                    })
    
    return subscriptions

def find_savings_opportunities(category: str, percentile_threshold: int, user_id: str = None) -> Dict:
    """
    Identifies items in a category where the user is paying above a certain percentile.
    Args:
        category: The category to analyze
        percentile_threshold: The percentile threshold (e.g., 75 means items above 75th percentile price)
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: find_savings_opportunities for user {user_id} in {category}")
    # Get receipts from the last 60 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "category": category
    })
    
    item_prices = defaultdict(list)
    
    for receipt in receipts:
        if 'items' in receipt:
            for item in receipt['items']:
                item_name = item.get('name', '').lower().strip()
                if item_name and item.get('price'):
                    item_prices[item_name].append({
                        "price": item['price'],
                        "vendor": receipt.get('vendor_name'),
                        "date": receipt.get('date')
                    })
    
    savings_opportunities = []
    
    for item_name, price_data in item_prices.items():
        if len(price_data) >= 3:  # Need at least 3 data points
            prices = [p['price'] for p in price_data]
            threshold_price = statistics.quantiles(prices, n=100)[percentile_threshold-1]
            
            high_price_instances = [p for p in price_data if p['price'] > threshold_price]
            
            if high_price_instances:
                savings_opportunities.append({
                    "item": item_name,
                    "average_price": statistics.mean(prices),
                    "lowest_price": min(prices),
                    "highest_price": max(prices),
                    "threshold_price": threshold_price,
                    "potential_savings_per_purchase": statistics.mean([p['price'] for p in high_price_instances]) - statistics.mean(prices),
                    "high_price_vendors": list(set([p['vendor'] for p in high_price_instances if p['vendor']]))
                })
    
    return {
        "category": category,
        "total_opportunities": len(savings_opportunities),
        "opportunities": sorted(savings_opportunities, key=lambda x: x['potential_savings_per_purchase'], reverse=True)
    }

def compare_spending_to_budget(budget_amount: float, start_date: str, end_date: str, user_id: str = None) -> Dict:
    """
    Compares actual spending to a budget amount for a given period.
    Args:
        budget_amount: The budget amount to compare against
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: compare_spending_to_budget for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    total_spent = sum(r.get('amount', 0) for r in receipts)
    variance = total_spent - budget_amount
    variance_percentage = (variance / budget_amount * 100) if budget_amount > 0 else 0
    
    # Calculate daily burn rate
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days_in_period = (end - start).days + 1
    daily_budget = budget_amount / days_in_period if days_in_period > 0 else 0
    
    # Current progress
    today = datetime.now()
    if start <= today <= end:
        days_elapsed = (today - start).days + 1
        expected_spending = daily_budget * days_elapsed
        actual_vs_expected = total_spent - expected_spending
    else:
        days_elapsed = days_in_period
        expected_spending = budget_amount
        actual_vs_expected = variance
    
    return {
        "budget_amount": budget_amount,
        "total_spent": total_spent,
        "variance": variance,
        "variance_percentage": variance_percentage,
        "is_over_budget": total_spent > budget_amount,
        "daily_budget": daily_budget,
        "average_daily_spending": total_spent / days_elapsed if days_elapsed > 0 else 0,
        "days_elapsed": days_elapsed,
        "days_remaining": days_in_period - days_elapsed,
        "on_track": actual_vs_expected <= 0,
        "projected_total": (total_spent / days_elapsed * days_in_period) if days_elapsed > 0 else 0
    }

# ========== TAX AND FEE ANALYSIS ==========

def calculate_total_taxes(start_date: str, end_date: str, user_id: str = None) -> Dict[str, float]:
    """
    Calculates total taxes paid across all receipts in a date range.
    Args:
        start_date: The start date in YYYY-MM-DD format
        end_date: The end date in YYYY-MM-DD format
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: calculate_total_taxes for user {user_id}")
    receipts = _fetch_receipts(user_id, {"start_date": start_date, "end_date": end_date})
    
    tax_totals = defaultdict(float)
    total_tax = 0
    
    for receipt in receipts:
        if 'taxes' in receipt:
            for tax_type, tax_amount in receipt['taxes'].items():
                tax_totals[tax_type] += tax_amount
                total_tax += tax_amount
    
    return {
        "total_tax": total_tax,
        "tax_breakdown": dict(tax_totals),
        "receipt_count": len(receipts),
        "average_tax_per_receipt": total_tax / len(receipts) if receipts else 0
    }

# ========== SHOPPING LIST AND MEAL PLANNING ==========

def get_items_from_receipts(category: str, days_back: int, user_id: str = None) -> List[str]:
    """
    Extracts all unique items from receipts in a specific category from the past N days.
    Args:
        category: The category to filter by (e.g., 'grocery')
        days_back: Number of days to look back
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: get_items_from_receipts for user {user_id}")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d'),
        "category": category
    })
    
    unique_items = set()
    
    for receipt in receipts:
        if 'items' in receipt:
            for item in receipt['items']:
                item_name = item.get('name', '').strip()
                if item_name:
                    unique_items.add(item_name)
    
    return sorted(list(unique_items))

def suggest_shopping_list(missing_items: List[str], user_id: str = None) -> Dict:
    """
    Creates a shopping list with estimated costs based on historical prices.
    Args:
        missing_items: List of items needed
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: suggest_shopping_list for user {user_id}")
    # Look at the last 30 days for price history
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    })
    
    item_price_history = defaultdict(list)
    
    for receipt in receipts:
        if 'items' in receipt:
            for item in receipt['items']:
                item_name = item.get('name', '').lower().strip()
                if item_name and item.get('price'):
                    item_price_history[item_name].append({
                        "price": item['price'],
                        "vendor": receipt.get('vendor_name')
                    })
    
    shopping_list = []
    total_estimated_cost = 0
    
    for requested_item in missing_items:
        requested_lower = requested_item.lower().strip()
        best_match = None
        
        # Try to find exact or partial match
        for historical_item in item_price_history:
            if requested_lower in historical_item or historical_item in requested_lower:
                best_match = historical_item
                break
        
        if best_match:
            prices = [p['price'] for p in item_price_history[best_match]]
            avg_price = statistics.mean(prices)
            min_price = min(prices)
            
            # Find vendor with lowest price
            lowest_price_vendor = None
            for price_data in item_price_history[best_match]:
                if price_data['price'] == min_price:
                    lowest_price_vendor = price_data['vendor']
                    break
            
            shopping_list.append({
                "item": requested_item,
                "estimated_price": avg_price,
                "lowest_historical_price": min_price,
                "recommended_vendor": lowest_price_vendor,
                "price_confidence": "high" if len(prices) >= 3 else "medium"
            })
            total_estimated_cost += avg_price
        else:
            shopping_list.append({
                "item": requested_item,
                "estimated_price": None,
                "lowest_historical_price": None,
                "recommended_vendor": None,
                "price_confidence": "no_data"
            })
    
    return {
        "shopping_list": shopping_list,
        "total_estimated_cost": total_estimated_cost,
        "items_with_price_data": len([i for i in shopping_list if i['estimated_price'] is not None]),
        "items_without_price_data": len([i for i in shopping_list if i['estimated_price'] is None])
    }

# ========== ANOMALY DETECTION ==========

def detect_unusual_spending(sensitivity: float, days_back: int, user_id: str = None) -> List[Dict]:
    """
    Detects receipts with unusually high amounts based on statistical analysis.
    Args:
        sensitivity: Standard deviation multiplier (e.g., 2.0 for 2 standard deviations)
        days_back: Number of days to analyze
        user_id: The identifier for the user. This is an internal parameter.
    """
    logger.info(f"TOOL: detect_unusual_spending for user {user_id}")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    receipts = _fetch_receipts(user_id, {
        "start_date": start_date.strftime('%Y-%m-%d'),
        "end_date": end_date.strftime('%Y-%m-%d')
    })
    
    if len(receipts) < 3:
        return []
    
    amounts = [r.get('amount', 0) for r in receipts]
    mean_amount = statistics.mean(amounts)
    stdev_amount = statistics.stdev(amounts)
    
    threshold = mean_amount + (sensitivity * stdev_amount)
    
    unusual_spending = []
    for receipt in receipts:
        amount = receipt.get('amount', 0)
        if amount > threshold:
            unusual_spending.append({
                "date": receipt.get('date'),
                "vendor": receipt.get('vendor_name'),
                "amount": amount,
                "category": receipt.get('category'),
                "deviation": (amount - mean_amount) / stdev_amount if stdev_amount > 0 else 0,
                "percentage_above_average": ((amount - mean_amount) / mean_amount * 100) if mean_amount > 0 else 0
            })
    
    return sorted(unusual_spending, key=lambda x: x['amount'], reverse=True)

all_tool_calls ={
    "_fetch_receipts_all_categories": _fetch_receipts_all_categories,
    "find_purchases": find_purchases,
    "get_largest_purchase": get_largest_purchase,
    "get_spending_for_category": get_spending_for_category,
    "get_average_daily_spending": get_average_daily_spending,
    "get_spending_by_day_of_week": get_spending_by_day_of_week,
    "get_monthly_spending_trend": get_monthly_spending_trend,
    "get_top_vendors": get_top_vendors,
    "get_category_breakdown": get_category_breakdown,
    "get_frequently_purchased_items": get_frequently_purchased_items,
    "check_inventory_status": check_inventory_status,
    "detect_recurring_subscriptions": detect_recurring_subscriptions,
    "find_savings_opportunities": find_savings_opportunities,
    "compare_spending_to_budget": compare_spending_to_budget,
    "calculate_total_taxes": calculate_total_taxes,
    "get_items_from_receipts": get_items_from_receipts,
    "suggest_shopping_list": suggest_shopping_list,
    "detect_unusual_spending": detect_unusual_spending,
}
