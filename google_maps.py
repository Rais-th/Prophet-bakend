"""
Google Maps Integration for Alpha Prophet
- Places API: Find business addresses from customer name + city
- Distance Matrix API: Calculate actual miles between warehouses and destinations
"""

import os
import re
import requests
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# Warehouse addresses (actual locations)
WAREHOUSE_LOCATIONS = {
    'Houston': '10310 Fairbanks N Houston Rd, Houston, TX 77064',
    'West Memphis': '1400 N 8th St, West Memphis, AR 72301',
    'California': '4401 Arch Rd, Stockton, CA 95215'
}


def parse_destination(destination: str) -> Tuple[str, str, str]:
    """
    Parse destination string like 'Georgia Power-Forest Park GA'
    Returns: (customer_name, city, state)
    """
    destination = destination.strip()

    # Pattern: "CustomerName-City ST" or "CustomerName-City State"
    # State is last 2 chars if uppercase letters
    state = ''
    if len(destination) >= 2:
        last_two = destination[-2:].strip()
        if last_two.isupper() and last_two.isalpha():
            state = last_two
            destination = destination[:-2].strip()

    # Split by hyphen
    if '-' in destination:
        parts = destination.split('-', 1)
        customer = parts[0].strip()
        city = parts[1].strip() if len(parts) > 1 else ''
    else:
        # No hyphen - assume it's all city/location
        customer = ''
        city = destination

    return customer, city, state


def find_business_address(customer: str, city: str, state: str) -> Dict[str, Any]:
    """
    Use Google Places API to find actual business address
    """
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == 'your-google-maps-api-key-here':
        return {
            'success': False,
            'error': 'Google Maps API key not configured'
        }

    # Build search query
    if customer:
        query = f"{customer} {city} {state}".strip()
    else:
        query = f"{city} {state}".strip()

    try:
        # Use Places Text Search API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            'query': query,
            'key': GOOGLE_MAPS_API_KEY
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            place = data['results'][0]
            return {
                'success': True,
                'name': place.get('name', ''),
                'address': place.get('formatted_address', ''),
                'location': place.get('geometry', {}).get('location', {}),
                'place_id': place.get('place_id', '')
            }
        elif data.get('status') == 'ZERO_RESULTS':
            # Fall back to city, state only
            return {
                'success': True,
                'name': customer or city,
                'address': f"{city}, {state}",
                'location': None,
                'fallback': True
            }
        else:
            return {
                'success': False,
                'error': data.get('status', 'Unknown error')
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def calculate_distances(destination_address: str) -> Dict[str, Any]:
    """
    Calculate distances from all warehouses to a destination using Distance Matrix API
    """
    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == 'your-google-maps-api-key-here':
        return {
            'success': False,
            'error': 'Google Maps API key not configured'
        }

    try:
        # Build origins string (all warehouses)
        origins = '|'.join(WAREHOUSE_LOCATIONS.values())

        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': origins,
            'destinations': destination_address,
            'units': 'imperial',
            'key': GOOGLE_MAPS_API_KEY
        }

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') != 'OK':
            return {
                'success': False,
                'error': data.get('status', 'Unknown error')
            }

        distances = {}
        warehouse_names = list(WAREHOUSE_LOCATIONS.keys())

        for i, row in enumerate(data.get('rows', [])):
            elements = row.get('elements', [])
            if elements and elements[0].get('status') == 'OK':
                element = elements[0]
                warehouse = warehouse_names[i]

                # Parse distance (e.g., "793 mi")
                distance_text = element.get('distance', {}).get('text', '')
                distance_miles = element.get('distance', {}).get('value', 0) / 1609.34  # meters to miles

                # Parse duration (e.g., "11 hours 45 mins")
                duration_text = element.get('duration', {}).get('text', '')
                duration_seconds = element.get('duration', {}).get('value', 0)

                distances[warehouse] = {
                    'miles': round(distance_miles, 1),
                    'miles_text': distance_text,
                    'drive_time': duration_text,
                    'drive_seconds': duration_seconds
                }

        return {
            'success': True,
            'distances': distances
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def estimate_cost_by_distance(miles: float, weight_lbs: float = 40000) -> float:
    """
    Estimate shipping cost based on distance
    Using average rate of ~$3.50/mile for full truckload
    """
    # Base rate per mile (varies by market, but this is a reasonable average)
    rate_per_mile = 3.50

    # Adjust for weight (LTL costs more per lb)
    if weight_lbs < 10000:
        rate_per_mile *= 1.5  # LTL premium
    elif weight_lbs < 20000:
        rate_per_mile *= 1.2

    return round(miles * rate_per_mile, 2)


def optimize_shipment(destination: str, weight_lbs: float = 40000) -> Dict[str, Any]:
    """
    Main function: Find optimal warehouse for a shipment

    1. Parse destination
    2. Find actual business address via Google Places
    3. Calculate distances from all warehouses
    4. Estimate costs and recommend best option
    """
    # Step 1: Parse destination
    customer, city, state = parse_destination(destination)

    if not city and not state:
        return {
            'success': False,
            'error': f"Could not parse destination: {destination}"
        }

    # Step 2: Find business address
    place_result = find_business_address(customer, city, state)

    if not place_result.get('success'):
        # If Places API fails, fall back to city, state
        full_address = f"{city}, {state}" if state else city
        place_info = {
            'name': customer or city,
            'address': full_address,
            'fallback': True
        }
    else:
        full_address = place_result.get('address', f"{city}, {state}")
        place_info = {
            'name': place_result.get('name', customer),
            'address': full_address,
            'place_id': place_result.get('place_id'),
            'fallback': place_result.get('fallback', False)
        }

    # Step 3: Calculate distances
    distance_result = calculate_distances(full_address)

    if not distance_result.get('success'):
        return {
            'success': False,
            'error': f"Could not calculate distances: {distance_result.get('error')}",
            'destination_parsed': {
                'customer': customer,
                'city': city,
                'state': state
            }
        }

    distances = distance_result['distances']

    # Step 4: Calculate costs and find best option
    options = []
    for warehouse, dist_info in distances.items():
        miles = dist_info['miles']
        estimated_cost = estimate_cost_by_distance(miles, weight_lbs)

        options.append({
            'warehouse': warehouse,
            'miles': miles,
            'drive_time': dist_info['drive_time'],
            'estimated_cost': estimated_cost,
            'cost_per_mile': round(estimated_cost / miles, 2) if miles > 0 else 0
        })

    # Sort by cost (cheapest first)
    options.sort(key=lambda x: x['estimated_cost'])

    best = options[0]
    worst = options[-1]
    savings = worst['estimated_cost'] - best['estimated_cost']

    return {
        'success': True,
        'destination': {
            'original': destination,
            'customer': place_info['name'],
            'full_address': place_info['address'],
            'lookup_method': 'city_state_fallback' if place_info.get('fallback') else 'google_places'
        },
        'weight_lbs': weight_lbs,
        'pallets': round(weight_lbs / 920, 1),
        'routing_options': options,
        'recommendation': {
            'best_warehouse': best['warehouse'],
            'best_cost': best['estimated_cost'],
            'best_miles': best['miles'],
            'best_drive_time': best['drive_time'],
            'worst_warehouse': worst['warehouse'],
            'worst_cost': worst['estimated_cost'],
            'potential_savings': round(savings, 2),
            'savings_pct': round((savings / worst['estimated_cost']) * 100, 1) if worst['estimated_cost'] > 0 else 0
        },
        'insight': f"Ship from {best['warehouse']} ({best['miles']:.0f} mi, {best['drive_time']}) - saves ${savings:,.0f} vs {worst['warehouse']}"
    }


# Quick test
if __name__ == '__main__':
    # Test parsing
    test_destinations = [
        'Georgia Power-Forest Park GA',
        'AEP-Los Fresnos TX',
        'Quanta-Morton MN',
        'Anixter-Ashland VA'
    ]

    for dest in test_destinations:
        customer, city, state = parse_destination(dest)
        print(f"{dest} -> Customer: '{customer}', City: '{city}', State: '{state}'")

    print("\n--- Testing optimize_shipment ---")
    result = optimize_shipment('Georgia Power-Forest Park GA', 40000)
    import json
    print(json.dumps(result, indent=2))
