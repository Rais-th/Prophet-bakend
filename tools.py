"""
Alpha Prophet CLI Tools
Functions that Claude can call to interact with the warehouse model
"""

import os
import sys
import pandas as pd
from typing import Dict, Any, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import East Coast location analyzer
from analysis.east_coast_location import analyze_east_coast_locations

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_2023 = os.path.join(BASE_DIR, 'Dataset', 'Sales 2023.xlsx')
DATA_2024 = os.path.join(BASE_DIR, 'Dataset', 'Sales 2024.xlsx')
DATA_2025 = os.path.join(BASE_DIR, 'Dataset', '2025 YTD SALES_10.30.25.xlsx')
BACKLOG_FILE = os.path.join(BASE_DIR, 'Backlog and freight', 'Backlog excel report(2).xlsx')

# Freight files
FREIGHT_HOUSTON = os.path.join(BASE_DIR, 'Backlog and freight', 'Houston Freight 2025.xlsx')
FREIGHT_WM = os.path.join(BASE_DIR, 'Backlog and freight', 'WM Freight 2025.xlsx')
FREIGHT_STOCKTON = os.path.join(BASE_DIR, 'Backlog and freight', 'Stockton Freight 2025.xlsx')

# State to warehouse mapping (v3.1 Smart Routing)
CALIFORNIA_STATES = ['CALIFORNIA', 'OREGON', 'WASHINGTON', 'IDAHO', 'CA', 'OR', 'WA', 'ID']
HOUSTON_STATES = ['TEXAS', 'TX']
# Everything else goes to West Memphis

def get_warehouse_for_state(state: str) -> str:
    """Get the recommended warehouse for a state"""
    state_upper = str(state).upper().strip()

    if state_upper in CALIFORNIA_STATES:
        return 'California'
    elif state_upper in HOUSTON_STATES:
        return 'Houston'
    else:
        return 'West Memphis'

def load_sales_data() -> pd.DataFrame:
    """Load and combine all sales data"""
    all_data = []

    for filepath in [DATA_2023, DATA_2024, DATA_2025]:
        if os.path.exists(filepath):
            try:
                df = pd.read_excel(filepath, sheet_name=0)
                all_data.append(df)
            except:
                pass

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

# ============================================================================
# TOOL DEFINITIONS (for Claude API)
# ============================================================================

TOOLS = [
    {
        "name": "get_distribution",
        "description": "Calculate optimal warehouse distribution for a product purchase. Returns recommended quantities for each warehouse (California, Houston, West Memphis).",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Product name (e.g., 'N 14/146 DC', 'N 21/156 DC')"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Total quantity to distribute"
                },
                "customer_state": {
                    "type": "string",
                    "description": "Optional: Customer's state for specific routing"
                }
            },
            "required": ["product_name", "quantity"]
        }
    },
    {
        "name": "analyze_state",
        "description": "Analyze shipping patterns for a specific state. Returns volume, top products, and recommended warehouse.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "description": "State name (e.g., 'Texas', 'California') or abbreviation (e.g., 'TX', 'CA')"
                }
            },
            "required": ["state"]
        }
    },
    {
        "name": "get_warehouse_info",
        "description": "Get information about a specific warehouse including states served, volume, and top products.",
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse": {
                    "type": "string",
                    "description": "Warehouse name: 'California', 'Houston', or 'West Memphis'"
                }
            },
            "required": ["warehouse"]
        }
    },
    {
        "name": "forecast_demand",
        "description": "Forecast demand for a product based on historical patterns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Product name to forecast"
                },
                "months": {
                    "type": "integer",
                    "description": "Number of months to forecast (default: 3)"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "get_backlog_summary",
        "description": "Get summary of current backlog (open orders for 2026).",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {
                    "type": "string",
                    "description": "Group by: 'warehouse', 'state', or 'product'"
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_routing",
        "description": "Compare current routing vs model recommendation for cost savings analysis.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "recommend_east_coast_location",
        "description": "Analyze shipping data to recommend optimal East Coast warehouse locations. Returns top 5 strategic locations with reasoning based on demand, infrastructure, and coverage. Use this when asked about East Coast warehouse, distribution center, or 3PL locations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_n": {
                    "type": "integer",
                    "description": "Number of locations to recommend (default 5)"
                }
            },
            "required": []
        }
    },
    {
        "name": "search_orders",
        "description": "Search historical SALES orders by customer, product, date range, or state. Use for questions like 'Show Anixter orders', 'What did we ship to Texas last quarter?', 'Find orders for N 14/146 DC in 2024'. Data: 2023-Oct 2025.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name to search (partial match, e.g., 'Anixter', 'Graybar')"
                },
                "product": {
                    "type": "string",
                    "description": "Product name to search (partial match, e.g., 'N 14/146 DC')"
                },
                "state": {
                    "type": "string",
                    "description": "State name or abbreviation (e.g., 'Texas', 'TX')"
                },
                "date_range": {
                    "type": "string",
                    "description": "Date range: 'last_month', 'last_quarter', 'last_year', 'ytd', '2024', '2023', or 'YYYY-MM' format"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of order details to return (default 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "search_freight",
        "description": "Search actual SHIPMENTS from warehouses by date, warehouse, or destination. Use for 'What shipped from Houston on 12/29?', 'Show December freight', 'Shipments to Texas'. Data: 2024-Dec 2025.",
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse": {
                    "type": "string",
                    "description": "Warehouse: 'Houston', 'West Memphis', 'California', or 'all'"
                },
                "date_range": {
                    "type": "string",
                    "description": "Date: 'last_month', '2025-12', '12/29/2025', 'December 2025'"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination state or city (e.g., 'TX', 'Texas', 'Los Fresnos')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max shipments to return (default 10)"
                }
            },
            "required": []
        }
    }
]

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def get_distribution(product_name: str, quantity: int, customer_state: str = None) -> Dict[str, Any]:
    """Calculate optimal warehouse distribution"""

    # If customer state is provided, route to that warehouse
    if customer_state:
        warehouse = get_warehouse_for_state(customer_state)
        return {
            "product": product_name,
            "total_quantity": quantity,
            "distribution": {
                "California": quantity if warehouse == "California" else 0,
                "Houston": quantity if warehouse == "Houston" else 0,
                "West Memphis": quantity if warehouse == "West Memphis" else 0
            },
            "method": f"State-based routing ({customer_state} → {warehouse})",
            "confidence": "HIGH"
        }

    # Load historical data to find product patterns
    df = load_sales_data()

    if df.empty:
        # Default distribution if no data
        return {
            "product": product_name,
            "total_quantity": quantity,
            "distribution": {
                "California": int(quantity * 0.10),
                "Houston": int(quantity * 0.25),
                "West Memphis": int(quantity * 0.65)
            },
            "method": "Default distribution (no historical data)",
            "confidence": "LOW"
        }

    # Filter USA and get product data
    df_usa = df[df['Ship-to Country'] == 'USA'].copy()
    df_usa['State'] = df_usa['Description.1'].fillna('UNKNOWN')
    df_usa['Product'] = df_usa['SO item short text'].fillna('UNKNOWN')
    df_usa['Quantity'] = df_usa['SO item Req.Qty'].fillna(0)

    # Find matching products
    product_df = df_usa[df_usa['Product'].str.contains(product_name, case=False, na=False)]

    if len(product_df) < 5:
        # Not enough data, use default
        return {
            "product": product_name,
            "total_quantity": quantity,
            "distribution": {
                "California": int(quantity * 0.10),
                "Houston": int(quantity * 0.25),
                "West Memphis": int(quantity * 0.65)
            },
            "method": f"Default distribution (only {len(product_df)} historical orders)",
            "confidence": "MEDIUM"
        }

    # Calculate distribution based on historical state patterns
    product_df = product_df.copy()
    product_df['Warehouse'] = product_df['State'].apply(get_warehouse_for_state)
    warehouse_dist = product_df.groupby('Warehouse')['Quantity'].sum()
    total_qty = warehouse_dist.sum()

    if total_qty == 0:
        total_qty = 1

    distribution = {}
    for wh in ['California', 'Houston', 'West Memphis']:
        pct = warehouse_dist.get(wh, 0) / total_qty
        distribution[wh] = int(quantity * pct)

    # Adjust for rounding
    diff = quantity - sum(distribution.values())
    distribution['West Memphis'] += diff

    return {
        "product": product_name,
        "total_quantity": quantity,
        "distribution": distribution,
        "historical_orders": len(product_df),
        "method": "Historical pattern analysis",
        "confidence": "HIGH" if len(product_df) > 20 else "MEDIUM"
    }


def analyze_state(state: str) -> Dict[str, Any]:
    """Analyze shipping patterns for a state"""

    df = load_sales_data()

    if df.empty:
        return {"error": "Could not load sales data"}

    # Filter USA
    df_usa = df[df['Ship-to Country'] == 'USA'].copy()
    df_usa['State'] = df_usa['Description.1'].fillna('UNKNOWN')
    df_usa['Product'] = df_usa['SO item short text'].fillna('UNKNOWN')
    df_usa['Quantity'] = df_usa['SO item Req.Qty'].fillna(0)

    # Normalize state name
    state_upper = state.upper().strip()

    # Filter by state
    state_df = df_usa[df_usa['State'].str.upper() == state_upper]

    if len(state_df) == 0:
        return {
            "state": state,
            "error": f"No data found for state: {state}",
            "recommended_warehouse": get_warehouse_for_state(state)
        }

    # Calculate stats
    total_orders = len(state_df)
    total_quantity = state_df['Quantity'].sum()

    # Top products
    top_products = state_df.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(5)

    return {
        "state": state,
        "total_orders": int(total_orders),
        "total_quantity": int(total_quantity),
        "recommended_warehouse": get_warehouse_for_state(state),
        "top_products": [
            {"product": prod, "quantity": int(qty)}
            for prod, qty in top_products.items()
        ],
        "avg_order_size": int(total_quantity / total_orders) if total_orders > 0 else 0
    }


def get_warehouse_info(warehouse: str) -> Dict[str, Any]:
    """Get information about a warehouse"""

    warehouse_states = {
        "California": ["California", "Oregon", "Washington", "Idaho"],
        "Houston": ["Texas"],
        "West Memphis": ["All other states (Main Hub)"]
    }

    df = load_sales_data()

    if df.empty:
        return {
            "warehouse": warehouse,
            "states_served": warehouse_states.get(warehouse, []),
            "error": "Could not load sales data for volume calculation"
        }

    # Filter USA
    df_usa = df[df['Ship-to Country'] == 'USA'].copy()
    df_usa['State'] = df_usa['Description.1'].fillna('UNKNOWN')
    df_usa['Product'] = df_usa['SO item short text'].fillna('UNKNOWN')
    df_usa['Quantity'] = df_usa['SO item Req.Qty'].fillna(0)
    df_usa['Warehouse'] = df_usa['State'].apply(get_warehouse_for_state)

    # Filter by warehouse
    wh_df = df_usa[df_usa['Warehouse'] == warehouse]

    # Calculate stats
    total_orders = len(wh_df)
    total_quantity = wh_df['Quantity'].sum()

    # Top products
    top_products = wh_df.groupby('Product')['Quantity'].sum().sort_values(ascending=False).head(5)

    # Top states
    top_states = wh_df.groupby('State')['Quantity'].sum().sort_values(ascending=False).head(5)

    return {
        "warehouse": warehouse,
        "states_served": warehouse_states.get(warehouse, []),
        "total_orders": int(total_orders),
        "total_quantity": int(total_quantity),
        "pct_of_total": round(total_orders / len(df_usa) * 100, 1) if len(df_usa) > 0 else 0,
        "top_products": [
            {"product": prod, "quantity": int(qty)}
            for prod, qty in top_products.items()
        ],
        "top_states": [
            {"state": st, "quantity": int(qty)}
            for st, qty in top_states.items()
        ]
    }


def forecast_demand(product_name: str, months: int = 3) -> Dict[str, Any]:
    """Forecast demand for a product"""

    df = load_sales_data()

    if df.empty:
        return {"error": "Could not load sales data"}

    # Filter USA
    df_usa = df[df['Ship-to Country'] == 'USA'].copy()
    df_usa['Product'] = df_usa['SO item short text'].fillna('UNKNOWN')
    df_usa['Quantity'] = pd.to_numeric(df_usa['SO item Req.Qty'], errors='coerce').fillna(0)

    # Try to get actual date range
    date_col = None
    for col in df_usa.columns:
        if 'date' in col.lower() or 'created' in col.lower():
            date_col = col
            break

    # Calculate actual months of data
    data_months = 34  # Default: Jan 2023 - Oct 2025
    if date_col:
        try:
            df_usa['_date'] = pd.to_datetime(df_usa[date_col], errors='coerce')
            valid_dates = df_usa['_date'].dropna()
            if len(valid_dates) > 0:
                min_date = valid_dates.min()
                max_date = valid_dates.max()
                data_months = max(1, (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month) + 1)
        except:
            pass

    # Find matching products
    product_df = df_usa[df_usa['Product'].str.contains(product_name, case=False, na=False)]

    if len(product_df) < 5:
        return {
            "product": product_name,
            "error": f"Not enough historical data ({len(product_df)} orders)",
            "recommendation": "Use default distribution"
        }

    # Calculate monthly average from actual data period
    total_quantity = product_df['Quantity'].sum()
    total_orders = len(product_df)

    monthly_avg_qty = total_quantity / data_months
    monthly_avg_orders = total_orders / data_months

    forecast_qty = int(monthly_avg_qty * months)
    forecast_orders = int(monthly_avg_orders * months)

    return {
        "product": product_name,
        "forecast_period": f"{months} months",
        "predicted_quantity": forecast_qty,
        "predicted_orders": forecast_orders,
        "monthly_avg_quantity": int(monthly_avg_qty),
        "monthly_avg_orders": round(monthly_avg_orders, 1),
        "historical_total_quantity": int(total_quantity),
        "historical_total_orders": int(total_orders),
        "data_months_analyzed": data_months,
        "confidence": "HIGH" if total_orders > 50 else "MEDIUM",
        "method": f"Monthly average from {data_months} months of data"
    }


def get_backlog_summary(group_by: str = "warehouse") -> Dict[str, Any]:
    """Get backlog summary"""

    if not os.path.exists(BACKLOG_FILE):
        return {"error": "Backlog file not found"}

    try:
        df = pd.read_excel(BACKLOG_FILE, sheet_name='Sheet1')
    except:
        return {"error": "Could not read backlog file"}

    # Extract state from zone
    def extract_state(zone):
        if pd.isna(zone):
            return None
        return str(zone)[:2].upper()

    df['State'] = df['Ship-toTrasp.Zone'].apply(extract_state)
    df['Quantity'] = pd.to_numeric(df['Order Qty'], errors='coerce').fillna(0)

    # Extract warehouse
    def extract_warehouse(inco2):
        if pd.isna(inco2):
            return 'Unknown'
        inco2_upper = str(inco2).upper()
        if 'MEMPHIS' in inco2_upper:
            return 'West Memphis'
        elif 'HOUSTON' in inco2_upper:
            return 'Houston'
        elif 'STOCKTON' in inco2_upper:
            return 'California'
        return 'Unknown'

    df['Warehouse'] = df['Inco 2'].apply(extract_warehouse)

    if group_by == "warehouse":
        summary = df.groupby('Warehouse').agg({
            'Quantity': ['sum', 'count']
        })
        summary.columns = ['total_quantity', 'order_count']

        return {
            "backlog_summary": "By Warehouse",
            "total_orders": int(df['Quantity'].count()),
            "total_quantity": int(df['Quantity'].sum()),
            "breakdown": [
                {
                    "warehouse": wh,
                    "orders": int(row['order_count']),
                    "quantity": int(row['total_quantity'])
                }
                for wh, row in summary.iterrows()
            ]
        }

    elif group_by == "state":
        summary = df.groupby('State').agg({
            'Quantity': ['sum', 'count']
        }).sort_values(('Quantity', 'sum'), ascending=False).head(10)
        summary.columns = ['total_quantity', 'order_count']

        return {
            "backlog_summary": "Top 10 States",
            "breakdown": [
                {
                    "state": st,
                    "orders": int(row['order_count']),
                    "quantity": int(row['total_quantity'])
                }
                for st, row in summary.iterrows()
            ]
        }

    return {"error": f"Unknown group_by: {group_by}"}


def compare_routing() -> Dict[str, Any]:
    """Compare current routing vs model recommendation"""

    if not os.path.exists(BACKLOG_FILE):
        return {"error": "Backlog file not found"}

    try:
        df = pd.read_excel(BACKLOG_FILE, sheet_name='Sheet1')
    except:
        return {"error": "Could not read backlog file"}

    # Extract state and warehouse
    def extract_state(zone):
        if pd.isna(zone):
            return None
        return str(zone)[:2].upper()

    def extract_warehouse(inco2):
        if pd.isna(inco2):
            return None
        inco2_upper = str(inco2).upper()
        if 'MEMPHIS' in inco2_upper:
            return 'West Memphis'
        elif 'HOUSTON' in inco2_upper:
            return 'Houston'
        elif 'STOCKTON' in inco2_upper:
            return 'California'
        return None

    df['State'] = df['Ship-toTrasp.Zone'].apply(extract_state)
    df['Actual_WH'] = df['Inco 2'].apply(extract_warehouse)
    df['Model_WH'] = df['State'].apply(get_warehouse_for_state)
    df['Quantity'] = pd.to_numeric(df['Order Qty'], errors='coerce').fillna(0)

    # Filter valid
    valid_df = df[df['Actual_WH'].notna()].copy()

    # Texas analysis (main opportunity)
    tx_df = valid_df[valid_df['State'] == 'TX']
    tx_at_houston = tx_df[tx_df['Actual_WH'] == 'Houston']
    tx_at_wm = tx_df[tx_df['Actual_WH'] == 'West Memphis']

    return {
        "comparison": "Current vs Model Routing",
        "total_orders": len(valid_df),
        "texas_opportunity": {
            "total_tx_orders": len(tx_df),
            "currently_at_houston": len(tx_at_houston),
            "currently_at_west_memphis": len(tx_at_wm),
            "model_would_route_to_houston": len(tx_df),
            "units_to_shift": int(tx_at_wm['Quantity'].sum()),
            "potential_savings": "Significant - ~300 miles shorter per shipment"
        },
        "summary": {
            "current_houston_pct": round(len(valid_df[valid_df['Actual_WH'] == 'Houston']) / len(valid_df) * 100, 1),
            "model_houston_pct": round(len(valid_df[valid_df['Model_WH'] == 'Houston']) / len(valid_df) * 100, 1)
        }
    }


def search_orders(customer: str = None, product: str = None, state: str = None,
                  date_range: str = None, limit: int = 10) -> Dict[str, Any]:
    """Search orders by customer, product, state, or date range"""
    from datetime import datetime, timedelta

    df = load_sales_data()

    if df.empty:
        return {"error": "Could not load sales data"}

    # Prepare data
    df_search = df.copy()

    # Standardize column names we need
    df_search['customer'] = df_search['Sell-to Name'].fillna('').astype(str)
    df_search['ship_to'] = df_search['Ship-to Name'].fillna('').astype(str)
    df_search['product'] = df_search['SO item short text'].fillna('').astype(str)
    df_search['state'] = df_search['Description.1'].fillna('').astype(str)
    df_search['quantity'] = pd.to_numeric(df_search['SO item Req.Qty'], errors='coerce').fillna(0)

    # Parse dates
    date_col = 'SO Document Date'
    if date_col in df_search.columns:
        df_search['order_date'] = pd.to_datetime(df_search[date_col], errors='coerce')
    else:
        df_search['order_date'] = pd.NaT

    filters_applied = []

    # Filter by customer
    if customer:
        customer_upper = customer.upper()
        mask = df_search['customer'].str.upper().str.contains(customer_upper, na=False)
        mask |= df_search['ship_to'].str.upper().str.contains(customer_upper, na=False)
        df_search = df_search[mask]
        filters_applied.append(f"customer contains '{customer}'")

    # Filter by product
    if product:
        df_search = df_search[df_search['product'].str.upper().str.contains(product.upper(), na=False)]
        filters_applied.append(f"product contains '{product}'")

    # Filter by state
    if state:
        state_upper = state.upper().strip()
        # Handle abbreviations
        state_map = {
            'TX': 'TEXAS', 'CA': 'CALIFORNIA', 'NY': 'NEW YORK', 'FL': 'FLORIDA',
            'PA': 'PENNSYLVANIA', 'VA': 'VIRGINIA', 'NJ': 'NEW JERSEY', 'NC': 'NORTH CAROLINA',
            'GA': 'GEORGIA', 'OH': 'OHIO', 'MI': 'MICHIGAN', 'IL': 'ILLINOIS',
            'WA': 'WASHINGTON', 'OR': 'OREGON', 'AZ': 'ARIZONA', 'CO': 'COLORADO',
            'MA': 'MASSACHUSETTS', 'MD': 'MARYLAND', 'MN': 'MINNESOTA', 'LA': 'LOUISIANA'
        }
        state_full = state_map.get(state_upper, state_upper)
        df_search = df_search[df_search['state'].str.upper() == state_full]
        filters_applied.append(f"state = '{state}'")

    # Filter by date range
    if date_range:
        today = datetime.now()
        start_date = None
        end_date = None

        if date_range.lower() == 'last_month':
            start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_date = today.replace(day=1) - timedelta(days=1)
            filters_applied.append("last month")
        elif date_range.lower() == 'last_quarter':
            current_quarter = (today.month - 1) // 3
            if current_quarter == 0:
                start_date = datetime(today.year - 1, 10, 1)
                end_date = datetime(today.year - 1, 12, 31)
            else:
                start_month = (current_quarter - 1) * 3 + 1
                end_month = current_quarter * 3
                start_date = datetime(today.year, start_month, 1)
                end_date = datetime(today.year, end_month + 1, 1) - timedelta(days=1)
            filters_applied.append("last quarter")
        elif date_range.lower() == 'last_year':
            start_date = datetime(today.year - 1, 1, 1)
            end_date = datetime(today.year - 1, 12, 31)
            filters_applied.append(f"year {today.year - 1}")
        elif date_range.lower() == 'ytd':
            start_date = datetime(today.year, 1, 1)
            end_date = today
            filters_applied.append(f"YTD {today.year}")
        elif date_range.isdigit() and len(date_range) == 4:
            year = int(date_range)
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            filters_applied.append(f"year {year}")
        elif '-' in date_range and len(date_range) == 7:
            # YYYY-MM format
            try:
                start_date = datetime.strptime(date_range + '-01', '%Y-%m-%d')
                if start_date.month == 12:
                    end_date = datetime(start_date.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
                filters_applied.append(f"month {date_range}")
            except:
                pass
        else:
            # Try parsing specific date formats: MM/DD/YYYY, YYYY-MM-DD, etc.
            date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y']
            for fmt in date_formats:
                try:
                    specific_date = datetime.strptime(date_range, fmt)
                    start_date = specific_date
                    end_date = specific_date + timedelta(days=1) - timedelta(seconds=1)
                    filters_applied.append(f"date {specific_date.strftime('%Y-%m-%d')}")
                    break
                except:
                    continue

        if start_date and end_date:
            df_search = df_search[
                (df_search['order_date'] >= start_date) &
                (df_search['order_date'] <= end_date)
            ]
        elif date_range and not filters_applied:
            # Couldn't parse the date
            return {
                "error": f"Could not parse date: '{date_range}'",
                "supported_formats": ["last_month", "last_quarter", "last_year", "ytd", "2024", "2024-06", "01/15/2024"]
            }

    if len(df_search) == 0:
        return {
            "filters": filters_applied,
            "total_orders": 0,
            "message": "No orders found matching criteria"
        }

    # Calculate summary
    total_orders = len(df_search)
    total_quantity = int(df_search['quantity'].sum())

    # Top products
    top_products = df_search.groupby('product')['quantity'].sum().sort_values(ascending=False).head(5)

    # Top customers
    top_customers = df_search.groupby('customer')['quantity'].sum().sort_values(ascending=False).head(5)

    # Date range in results
    valid_dates = df_search['order_date'].dropna()
    date_range_str = "N/A"
    if len(valid_dates) > 0:
        min_date = valid_dates.min().strftime('%Y-%m-%d')
        max_date = valid_dates.max().strftime('%Y-%m-%d')
        date_range_str = f"{min_date} to {max_date}"

    # Sample orders (most recent)
    sample_orders = []
    df_sorted = df_search.sort_values('order_date', ascending=False).head(limit)
    for _, row in df_sorted.iterrows():
        order_date = row['order_date'].strftime('%Y-%m-%d') if pd.notna(row['order_date']) else 'N/A'
        sample_orders.append({
            "date": order_date,
            "customer": row['customer'][:40],
            "product": row['product'],
            "quantity": int(row['quantity']),
            "state": row['state']
        })

    return {
        "filters_applied": filters_applied,
        "summary": {
            "total_orders": total_orders,
            "total_quantity": total_quantity,
            "date_range": date_range_str,
            "avg_order_size": int(total_quantity / total_orders) if total_orders > 0 else 0
        },
        "top_products": [
            {"product": p, "quantity": int(q)} for p, q in top_products.items()
        ],
        "top_customers": [
            {"customer": c[:40], "quantity": int(q)} for c, q in top_customers.items()
        ],
        "sample_orders": sample_orders
    }


def load_freight_data(warehouse: str = "all") -> pd.DataFrame:
    """Load freight data from warehouse files"""
    from datetime import datetime

    all_data = []

    warehouse_files = {
        'Houston': FREIGHT_HOUSTON,
        'West Memphis': FREIGHT_WM,
        'California': FREIGHT_STOCKTON
    }

    if warehouse.lower() == 'all':
        files_to_load = warehouse_files
    else:
        # Match warehouse name
        matched = None
        for wh_name in warehouse_files:
            if warehouse.lower() in wh_name.lower():
                matched = wh_name
                break
        if matched:
            files_to_load = {matched: warehouse_files[matched]}
        else:
            return pd.DataFrame()

    for wh_name, filepath in files_to_load.items():
        if not os.path.exists(filepath):
            continue

        try:
            xl = pd.ExcelFile(filepath)
            for sheet in xl.sheet_names:
                # Skip non-month sheets
                if sheet.lower() in ['sheet1', 'sheet2', 'full year']:
                    continue
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet)
                    if not df.empty:
                        df['_warehouse'] = wh_name
                        df['_sheet'] = sheet
                        all_data.append(df)
                except:
                    pass
        except:
            pass

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()


def search_freight(warehouse: str = "all", date_range: str = None,
                   destination: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    SMART freight search - Elon Musk level intelligence
    - Fuzzy matching for customer/destination
    - Auto-expands search if no results
    - Cross-references dates to find best matches
    - Suggests alternatives when exact match fails
    """
    from datetime import datetime, timedelta

    df_full = load_freight_data("all")  # Always load all for smart search

    if df_full.empty:
        return {"error": "Could not load freight data"}

    # Standardize columns
    df_full['ship_date'] = pd.to_datetime(df_full['Date Shipped'], errors='coerce')
    df_full['destination'] = df_full['Ship to on SO'].fillna('').astype(str)
    df_full['weight'] = pd.to_numeric(df_full['Weight'], errors='coerce').fillna(0)
    df_full['cost'] = pd.to_numeric(df_full['Cost'], errors='coerce').fillna(0)
    df_full['warehouse'] = df_full['_warehouse']
    df_full['state'] = df_full['destination'].str.strip().str[-2:].str.upper()

    # Extract customer name (before the hyphen)
    df_full['customer'] = df_full['destination'].str.split('-').str[0].str.strip()
    df_full['city_state'] = df_full['destination'].str.split('-').str[-1].str.strip()

    filters_applied = []
    smart_notes = []
    df = df_full.copy()

    # SMART WAREHOUSE FILTER
    if warehouse.lower() != 'all':
        df = df[df['warehouse'].str.lower().str.contains(warehouse.lower())]
        filters_applied.append(f"warehouse = '{warehouse}'")

    # SMART DESTINATION SEARCH
    destination_matches_before_date = None
    if destination:
        dest_upper = destination.upper().strip()

        # Strategy 1: Exact state match (2 chars)
        if len(dest_upper) == 2:
            df = df[df['state'] == dest_upper]
            filters_applied.append(f"state = '{dest_upper}'")

        # Strategy 2: Detect "Customer-Location" pattern (e.g., "Anixter-Ashland VA")
        elif '-' in dest_upper:
            # User is searching for specific customer + location combo
            parts = dest_upper.split('-')
            search_customer = parts[0].strip()
            search_location = '-'.join(parts[1:]).strip()

            # Exact match first
            exact_match = df[df['destination'].str.upper().str.contains(dest_upper, na=False)]

            if len(exact_match) > 0:
                df = exact_match
                filters_applied.append(f"exact match '{destination}'")
            else:
                # Try customer + partial location
                customer_match = df[df['customer'].str.upper().str.contains(search_customer, na=False)]
                if len(customer_match) > 0:
                    location_match = customer_match[customer_match['city_state'].str.upper().str.contains(search_location.replace(' ', ''), na=False)]
                    if len(location_match) > 0:
                        df = location_match
                        filters_applied.append(f"customer '{search_customer}' + location '{search_location}'")
                    else:
                        # Just use customer match
                        df = customer_match
                        filters_applied.append(f"customer '{search_customer}'")
                        smart_notes.append(f"Found {len(customer_match)} '{search_customer}' shipments, but none to '{search_location}'")

                        # Show which locations this customer shipped to
                        customer_locations = customer_match['destination'].unique()[:5]
                        smart_notes.append(f"'{search_customer}' shipped to: {', '.join([loc[-15:] for loc in customer_locations])}")
                else:
                    # Fall back to location-only search
                    location_match = df[df['destination'].str.upper().str.contains(search_location, na=False)]
                    if len(location_match) > 0:
                        df = location_match
                        filters_applied.append(f"location contains '{search_location}'")
                        smart_notes.append(f"No '{search_customer}' found, showing all shipments to '{search_location}'")

        else:
            # Strategy 3: Try customer name match first (fuzzy)
            customer_match = df[df['customer'].str.upper().str.contains(dest_upper, na=False)]

            if len(customer_match) > 0:
                df = customer_match
                filters_applied.append(f"customer contains '{destination}'")
            else:
                # Strategy 4: Try full destination match
                dest_match = df[df['destination'].str.upper().str.contains(dest_upper, na=False)]

                if len(dest_match) > 0:
                    df = dest_match
                    filters_applied.append(f"destination contains '{destination}'")
                else:
                    # Strategy 5: Try city match
                    city_match = df[df['city_state'].str.upper().str.contains(dest_upper, na=False)]

                    if len(city_match) > 0:
                        df = city_match
                        filters_applied.append(f"city contains '{destination}'")
                    else:
                        # Strategy 6: Fuzzy - try partial word match
                        words = dest_upper.split()
                        for word in words:
                            if len(word) >= 3:
                                partial_match = df[df['destination'].str.upper().str.contains(word, na=False)]
                                if len(partial_match) > 0:
                                    df = partial_match
                                    filters_applied.append(f"partial match '{word}'")
                                    smart_notes.append(f"No exact match for '{destination}', found partial match on '{word}'")
                                    break

        # Save matches before date filter for smart suggestions
        destination_matches_before_date = df.copy()

    # Filter by date
    if date_range:
        today = datetime.now()
        start_date = None
        end_date = None

        # Handle month names like "December 2025"
        month_names = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }

        date_lower = date_range.lower().strip()

        # Check for "December 2025" format
        for month_name, month_num in month_names.items():
            if month_name in date_lower:
                # Extract year
                import re
                year_match = re.search(r'20\d{2}', date_range)
                if year_match:
                    year = int(year_match.group())
                    start_date = datetime(year, month_num, 1)
                    if month_num == 12:
                        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
                    filters_applied.append(f"{month_name.title()} {year}")
                break

        # Try other formats if not matched
        if not start_date:
            if date_lower == 'last_month':
                start_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                end_date = today.replace(day=1) - timedelta(days=1)
                filters_applied.append("last month")
            elif '-' in date_range and len(date_range) == 7:
                try:
                    start_date = datetime.strptime(date_range + '-01', '%Y-%m-%d')
                    if start_date.month == 12:
                        end_date = datetime(start_date.year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
                    filters_applied.append(f"month {date_range}")
                except:
                    pass
            else:
                # Try specific date formats
                date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y']
                for fmt in date_formats:
                    try:
                        specific_date = datetime.strptime(date_range, fmt)
                        start_date = specific_date
                        end_date = specific_date + timedelta(days=1) - timedelta(seconds=1)
                        filters_applied.append(f"date {specific_date.strftime('%Y-%m-%d')}")
                        break
                    except:
                        continue

        if start_date and end_date:
            df_before_date = df.copy()
            df = df[(df['ship_date'] >= start_date) & (df['ship_date'] <= end_date)]

            # SMART: If no results but we had destination matches, find when they DID ship
            if len(df) == 0 and destination_matches_before_date is not None and len(destination_matches_before_date) > 0:
                # Find the actual dates this destination shipped
                actual_dates = destination_matches_before_date['ship_date'].dropna().sort_values()
                if len(actual_dates) > 0:
                    recent_dates = actual_dates.tail(5).dt.strftime('%Y-%m-%d').tolist()
                    total_historical = len(destination_matches_before_date)
                    total_weight = int(destination_matches_before_date['weight'].sum())

                    # Get the closest date to what was searched
                    search_date = start_date
                    closest_date = min(actual_dates, key=lambda x: abs((x - search_date).days))

                    smart_notes.append(f"No shipments on {start_date.strftime('%Y-%m-%d')}")
                    smart_notes.append(f"But found {total_historical} shipments to this destination on other dates")
                    smart_notes.append(f"Closest date: {closest_date.strftime('%Y-%m-%d')}")

                    # Return the actual matches instead of empty
                    df = destination_matches_before_date
                    filters_applied = [f for f in filters_applied if 'date' not in f.lower()]
                    filters_applied.append(f"Expanded search (no results for {start_date.strftime('%Y-%m-%d')})")

    if len(df) == 0:
        # SMART: Suggest similar destinations if nothing found
        suggestions = []
        if destination:
            # Find similar destination names
            all_destinations = df_full['destination'].unique()
            dest_upper = destination.upper()
            for d in all_destinations:
                if any(word in d.upper() for word in dest_upper.split() if len(word) >= 3):
                    suggestions.append(d)
            suggestions = list(set(suggestions))[:5]

        return {
            "filters": filters_applied,
            "total_shipments": 0,
            "message": "No shipments found matching criteria",
            "suggestions": suggestions if suggestions else None,
            "smart_notes": smart_notes if smart_notes else None
        }

    # Calculate summary
    total_shipments = len(df)
    total_weight = int(df['weight'].sum())
    total_cost = float(df['cost'].sum())

    # By warehouse
    by_warehouse = df.groupby('warehouse').agg({
        'weight': 'sum',
        'cost': 'sum',
        'destination': 'count'
    }).rename(columns={'destination': 'shipments'})

    # Top destinations
    top_destinations = df.groupby('destination')['weight'].sum().sort_values(ascending=False).head(5)

    # Date range
    valid_dates = df['ship_date'].dropna()
    date_range_str = "N/A"
    if len(valid_dates) > 0:
        date_range_str = f"{valid_dates.min().strftime('%Y-%m-%d')} to {valid_dates.max().strftime('%Y-%m-%d')}"

    # Sample shipments
    sample_shipments = []
    df_sorted = df.sort_values('ship_date', ascending=False).head(limit)
    for _, row in df_sorted.iterrows():
        ship_date = row['ship_date'].strftime('%Y-%m-%d') if pd.notna(row['ship_date']) else 'N/A'
        sample_shipments.append({
            "date": ship_date,
            "warehouse": row['warehouse'],
            "destination": row['destination'][:40],
            "weight": int(row['weight']),
            "cost": round(row['cost'], 2) if row['cost'] > 0 else None
        })

    result = {
        "filters_applied": filters_applied,
        "summary": {
            "total_shipments": total_shipments,
            "total_weight_lbs": total_weight,
            "total_cost": round(total_cost, 2),
            "date_range": date_range_str
        },
        "by_warehouse": [
            {"warehouse": wh, "shipments": int(row['shipments']), "weight": int(row['weight']), "cost": round(row['cost'], 2)}
            for wh, row in by_warehouse.iterrows()
        ],
        "top_destinations": [
            {"destination": d[:40], "weight": int(w)} for d, w in top_destinations.items()
        ],
        "sample_shipments": sample_shipments
    }

    # Include smart notes if any were generated
    if smart_notes:
        result["smart_notes"] = smart_notes

    return result


def recommend_east_coast_location(top_n: int = 5) -> Dict[str, Any]:
    """Recommend optimal East Coast warehouse locations"""

    result = analyze_east_coast_locations(top_n=top_n)

    if 'error' in result:
        return result

    # Format for clean AI response
    formatted = {
        "analysis_summary": {
            "total_east_coast_volume": result['summary']['total_east_coast_volume'],
            "total_orders": result['summary']['total_east_coast_orders'],
            "data_period": result['summary']['data_years']
        },
        "demand_by_region": result['region_breakdown'],
        "top_demand_states": [
            {"state": s['state_abbr'], "volume": int(s['total_volume']), "orders": s['order_count']}
            for s in result['top_states']
        ],
        "recommended_locations": [
            {
                "rank": i + 1,
                "city": loc['city'],
                "state": loc['state'],
                "region": loc['region'],
                "serviceable_volume": loc['serviceable_volume'],
                "coverage_pct": loc['serviceable_pct'],
                "states_covered": loc['serves'],
                "distance_from_west_memphis": loc['distance_from_wm'],
                "why": loc['why']
            }
            for i, loc in enumerate(result['strategic_locations'])
        ]
    }

    return formatted


# ============================================================================
# TOOL EXECUTOR
# ============================================================================

def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name"""

    tools_map = {
        "get_distribution": get_distribution,
        "analyze_state": analyze_state,
        "get_warehouse_info": get_warehouse_info,
        "forecast_demand": forecast_demand,
        "get_backlog_summary": get_backlog_summary,
        "compare_routing": compare_routing,
        "recommend_east_coast_location": recommend_east_coast_location,
        "search_orders": search_orders,
        "search_freight": search_freight
    }

    if tool_name not in tools_map:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        return tools_map[tool_name](**tool_input)
    except Exception as e:
        return {"error": str(e)}
