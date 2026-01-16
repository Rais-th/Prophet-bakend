"""
Google Maps Integration for Alpha Prophet - SMART EDITION
10x more intelligent routing with:
- Smart caching (avoid repeated API calls)
- Batch destination analysis
- State-level fallback when API fails
- Edge case detection (El Paso, border cities)
- Historical cost comparison
- Confidence scoring
- Rich business insights
"""

import os
import re
import json
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# Warehouse addresses (actual locations)
WAREHOUSE_LOCATIONS = {
    'Houston': {
        'address': '10310 Fairbanks N Houston Rd, Houston, TX 77064',
        'coords': (29.8697, -95.4866),
        'city': 'Houston',
        'state': 'TX'
    },
    'West Memphis': {
        'address': '1400 N 8th St, West Memphis, AR 72301',
        'coords': (35.1465, -90.1845),
        'city': 'West Memphis',
        'state': 'AR'
    },
    'California': {
        'address': '4401 Arch Rd, Stockton, CA 95215',
        'coords': (37.9352, -121.2264),
        'city': 'Stockton',
        'state': 'CA'
    }
}

# Historical cost rates ($/lb) from actual freight data
COST_RATES = {
    'Houston': {
        'TX': 0.0277, 'LA': 0.0550, 'OK': 0.0700, 'AR': 0.0650, 'NM': 0.0850,
        'MS': 0.0700, 'AL': 0.0850, 'TN': 0.0900, 'GA': 0.0950, 'FL': 0.1100,
        'default': 0.0850
    },
    'West Memphis': {
        'TN': 0.0350, 'AR': 0.0375, 'MS': 0.0400, 'AL': 0.0375, 'KY': 0.0450,
        'IN': 0.0524, 'OH': 0.0673, 'IL': 0.0773, 'MO': 0.0550, 'VA': 0.0836,
        'NC': 0.0800, 'GA': 0.0750, 'FL': 0.0900, 'TX': 0.1042, 'PA': 0.1001,
        'default': 0.0925
    },
    'California': {
        'CA': 0.0247, 'NV': 0.0450, 'AZ': 0.0645, 'OR': 0.0850, 'WA': 0.0900,
        'UT': 0.0909, 'CO': 0.1000, 'ID': 0.1368, 'TX': 0.1520,
        'default': 0.1200
    }
}

# Edge case cities - where state-level routing is WRONG
EDGE_CASES = {
    # Texas cities closer to other warehouses
    'EL PASO': {'expected': 'Houston', 'better': 'California', 'reason': 'El Paso is 750mi from Houston but only 550mi from Stockton'},
    'ODESSA': {'expected': 'Houston', 'note': 'Far West Texas - verify distance'},
    'MIDLAND': {'expected': 'Houston', 'note': 'Far West Texas - verify distance'},
    'AMARILLO': {'expected': 'Houston', 'note': 'Texas Panhandle - closer to multiple hubs'},
    # Border cities
    'FOREST PARK': {'state': 'GA', 'note': 'Atlanta suburb - verify optimal route'},
    'ASHLAND': {'state': 'VA', 'note': 'Near DC - could go West Memphis or future East Coast'},
}

# In-memory cache with TTL
_cache = {}
_cache_ttl = 3600  # 1 hour

def _cache_key(func_name: str, *args) -> str:
    """Generate cache key"""
    key_data = f"{func_name}:{':'.join(str(a) for a in args)}"
    return hashlib.md5(key_data.encode()).hexdigest()

def _get_cached(key: str) -> Optional[Any]:
    """Get from cache if not expired"""
    if key in _cache:
        data, timestamp = _cache[key]
        if datetime.now() - timestamp < timedelta(seconds=_cache_ttl):
            return data
        del _cache[key]
    return None

def _set_cached(key: str, data: Any):
    """Store in cache"""
    _cache[key] = (data, datetime.now())


def parse_destination(destination: str) -> Tuple[str, str, str]:
    """
    Parse destination string like 'Georgia Power-Forest Park GA'
    Returns: (customer_name, city, state)
    """
    destination = destination.strip()

    # Pattern: "CustomerName-City ST" or "CustomerName-City State"
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
        customer = ''
        city = destination

    return customer, city, state


def get_state_based_cost(warehouse: str, state: str, weight_lbs: float) -> Dict[str, Any]:
    """Calculate cost using historical state-level data"""
    state = state.upper()
    rates = COST_RATES.get(warehouse, COST_RATES['West Memphis'])
    rate = rates.get(state, rates['default'])
    cost = weight_lbs * rate

    return {
        'warehouse': warehouse,
        'rate_per_lb': rate,
        'estimated_cost': round(cost, 2),
        'cost_per_pallet': round(920 * rate, 2),
        'data_source': 'historical_freight_2025',
        'confidence': 'HIGH' if state in rates else 'MEDIUM'
    }


def check_edge_case(city: str, state: str) -> Optional[Dict[str, Any]]:
    """Check if this is a known edge case where state routing is wrong"""
    city_upper = city.upper().strip()

    if city_upper in EDGE_CASES:
        edge = EDGE_CASES[city_upper]
        if 'state' in edge and edge['state'] != state:
            return None  # Different state, not this edge case
        return {
            'is_edge_case': True,
            'city': city,
            'state': state,
            **edge
        }
    return None


def find_business_address(customer: str, city: str, state: str) -> Dict[str, Any]:
    """Use Google Places API to find actual business address (with caching)"""
    cache_key = _cache_key('places', customer, city, state)
    cached = _get_cached(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == 'your-google-maps-api-key-here':
        return {'success': False, 'error': 'Google Maps API key not configured'}

    # Build search query
    query = f"{customer} {city} {state}".strip() if customer else f"{city} {state}".strip()

    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {'query': query, 'key': GOOGLE_MAPS_API_KEY}

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('status') == 'OK' and data.get('results'):
            place = data['results'][0]
            result = {
                'success': True,
                'name': place.get('name', ''),
                'address': place.get('formatted_address', ''),
                'location': place.get('geometry', {}).get('location', {}),
                'place_id': place.get('place_id', ''),
                'types': place.get('types', [])
            }
            _set_cached(cache_key, result)
            return result
        elif data.get('status') == 'ZERO_RESULTS':
            result = {
                'success': True,
                'name': customer or city,
                'address': f"{city}, {state}",
                'location': None,
                'fallback': True
            }
            _set_cached(cache_key, result)
            return result
        else:
            return {'success': False, 'error': data.get('status', 'Unknown error')}

    except Exception as e:
        return {'success': False, 'error': str(e)}


def calculate_distances(destination_address: str) -> Dict[str, Any]:
    """Calculate distances from all warehouses using Routes API (with caching)"""
    cache_key = _cache_key('distances', destination_address)
    cached = _get_cached(cache_key)
    if cached:
        cached['from_cache'] = True
        return cached

    if not GOOGLE_MAPS_API_KEY or GOOGLE_MAPS_API_KEY == 'your-google-maps-api-key-here':
        return {'success': False, 'error': 'Google Maps API key not configured'}

    distances = {}

    # Use Routes API (new) - one call per warehouse
    for warehouse_name, warehouse_info in WAREHOUSE_LOCATIONS.items():
        try:
            url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': GOOGLE_MAPS_API_KEY,
                'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters'
            }
            body = {
                'origin': {
                    'address': warehouse_info['address']
                },
                'destination': {
                    'address': destination_address
                },
                'travelMode': 'DRIVE',
                'routingPreference': 'TRAFFIC_UNAWARE'
            }

            response = requests.post(url, headers=headers, json=body, timeout=10)
            data = response.json()

            if 'routes' in data and len(data['routes']) > 0:
                route = data['routes'][0]
                distance_meters = route.get('distanceMeters', 0)
                duration_str = route.get('duration', '0s')

                # Parse duration (format: "12345s")
                duration_seconds = int(duration_str.replace('s', '')) if duration_str.endswith('s') else 0
                duration_hours = duration_seconds / 3600

                # Format drive time
                hours = int(duration_hours)
                minutes = int((duration_hours - hours) * 60)
                drive_time_text = f"{hours} hr {minutes} min" if hours > 0 else f"{minutes} min"

                distances[warehouse_name] = {
                    'miles': round(distance_meters / 1609.34, 1),
                    'drive_time': drive_time_text,
                    'drive_hours': round(duration_hours, 1),
                    'delivery_days': 1 if duration_hours <= 10 else (2 if duration_hours <= 20 else 3)
                }
            elif 'error' in data:
                return {'success': False, 'error': f"Routes API: {data['error'].get('message', 'Unknown error')}"}

        except Exception as e:
            return {'success': False, 'error': f"Routes API error for {warehouse_name}: {str(e)}"}

    if not distances:
        return {'success': False, 'error': 'No routes calculated'}

    result = {'success': True, 'distances': distances}
    _set_cached(cache_key, result)
    return result


def estimate_shipping_cost(warehouse: str, miles: float, weight_lbs: float, state: str) -> Dict[str, Any]:
    """
    Smart cost estimation combining distance AND historical data
    """
    # Method 1: Distance-based ($3.50/mile for FTL, adjusted for weight)
    rate_per_mile = 3.50
    if weight_lbs < 10000:
        rate_per_mile *= 1.5  # LTL premium
    elif weight_lbs < 20000:
        rate_per_mile *= 1.2

    distance_cost = miles * rate_per_mile

    # Method 2: Historical cost rate ($/lb)
    historical = get_state_based_cost(warehouse, state, weight_lbs)
    historical_cost = historical['estimated_cost']

    # Blend: Use historical if available, otherwise distance
    if historical['confidence'] == 'HIGH':
        # We have real data for this route - trust it more
        blended_cost = historical_cost * 0.7 + distance_cost * 0.3
        primary_method = 'historical'
    else:
        # No historical data - rely on distance
        blended_cost = distance_cost * 0.7 + historical_cost * 0.3
        primary_method = 'distance'

    return {
        'blended_cost': round(blended_cost, 2),
        'distance_cost': round(distance_cost, 2),
        'historical_cost': round(historical_cost, 2),
        'primary_method': primary_method,
        'cost_per_mile': round(rate_per_mile, 2),
        'cost_per_lb': historical['rate_per_lb'],
        'confidence': historical['confidence']
    }


def analyze_routing_decision(best: Dict, current: str, state: str) -> Dict[str, Any]:
    """Analyze if the recommended routing matches state-based default"""
    # What would state-based routing suggest?
    state_upper = state.upper()

    if state_upper in ['CA', 'OR', 'WA', 'NV', 'AZ', 'ID']:
        state_default = 'California'
    elif state_upper == 'TX':
        state_default = 'Houston'
    else:
        state_default = 'West Memphis'

    matches_default = best['warehouse'] == state_default

    return {
        'state_based_default': state_default,
        'google_maps_recommendation': best['warehouse'],
        'recommendations_match': matches_default,
        'routing_insight': (
            f"State-based routing would use {state_default}, Google Maps confirms this is optimal."
            if matches_default else
            f"ROUTING OVERRIDE: State rules suggest {state_default}, but {best['warehouse']} is actually {best['miles']:.0f}mi closer!"
        )
    }


def optimize_shipment(destination: str, weight_lbs: float = 40000) -> Dict[str, Any]:
    """
    SMART shipment optimization with rich analysis

    Features:
    1. Parse & validate destination
    2. Check for known edge cases
    3. Find real address via Google Places (cached)
    4. Calculate actual distances (cached)
    5. Blend distance + historical costs
    6. Compare to state-based defaults
    7. Return actionable insights
    """
    start_time = datetime.now()

    # Step 1: Parse destination
    customer, city, state = parse_destination(destination)

    if not city and not state:
        return {
            'success': False,
            'error': f"Could not parse destination: {destination}",
            'hint': "Use format: 'CustomerName-City ST' (e.g., 'Georgia Power-Forest Park GA')"
        }

    # Step 2: Check for known edge cases
    edge_case = check_edge_case(city, state)

    # Step 3: Find business address
    place_result = find_business_address(customer, city, state)

    if not place_result.get('success'):
        full_address = f"{city}, {state}" if state else city
        place_info = {
            'name': customer or city,
            'address': full_address,
            'lookup_method': 'fallback_city_state'
        }
    else:
        full_address = place_result.get('address', f"{city}, {state}")
        place_info = {
            'name': place_result.get('name', customer),
            'address': full_address,
            'place_id': place_result.get('place_id'),
            'lookup_method': 'google_places' if not place_result.get('fallback') else 'fallback_city_state',
            'from_cache': place_result.get('from_cache', False)
        }

    # Step 4: Calculate distances
    distance_result = calculate_distances(full_address)

    # If Google fails, use state-based fallback with smart estimates
    if not distance_result.get('success'):
        return _fallback_analysis(destination, customer, city, state, weight_lbs,
                                   distance_result.get('error'), edge_case)

    distances = distance_result['distances']

    # Step 5: Calculate costs for each warehouse
    options = []
    for warehouse, dist_info in distances.items():
        cost_analysis = estimate_shipping_cost(warehouse, dist_info['miles'], weight_lbs, state)

        options.append({
            'warehouse': warehouse,
            'miles': dist_info['miles'],
            'drive_time': dist_info['drive_time'],
            'delivery_days': dist_info['delivery_days'],
            'estimated_cost': cost_analysis['blended_cost'],
            'cost_breakdown': {
                'distance_based': cost_analysis['distance_cost'],
                'historical_based': cost_analysis['historical_cost'],
                'method_used': cost_analysis['primary_method']
            },
            'cost_per_mile': round(cost_analysis['blended_cost'] / dist_info['miles'], 2) if dist_info['miles'] > 0 else 0,
            'cost_per_pallet': round(cost_analysis['blended_cost'] / (weight_lbs / 920), 2),
            'confidence': cost_analysis['confidence']
        })

    # Sort by cost
    options.sort(key=lambda x: x['estimated_cost'])

    best = options[0]
    second = options[1] if len(options) > 1 else None
    worst = options[-1]

    # Step 6: Analyze routing decision
    routing_analysis = analyze_routing_decision(best, '', state)

    # Calculate savings
    savings_vs_worst = worst['estimated_cost'] - best['estimated_cost']
    savings_vs_second = second['estimated_cost'] - best['estimated_cost'] if second else 0

    # Build response
    processing_time = (datetime.now() - start_time).total_seconds()

    result = {
        'success': True,
        'destination': {
            'original': destination,
            'customer': place_info['name'],
            'city': city,
            'state': state,
            'full_address': place_info['address'],
            'lookup_method': place_info['lookup_method'],
            'cached': place_info.get('from_cache', False) or distance_result.get('from_cache', False)
        },
        'shipment': {
            'weight_lbs': weight_lbs,
            'pallets': round(weight_lbs / 920, 1),
            'type': 'FTL' if weight_lbs >= 35000 else ('LTL' if weight_lbs < 10000 else 'Partial')
        },
        'routing_options': options,
        'recommendation': {
            'best_warehouse': best['warehouse'],
            'best_cost': best['estimated_cost'],
            'best_miles': best['miles'],
            'best_drive_time': best['drive_time'],
            'delivery_days': best['delivery_days'],
            'confidence': best['confidence'],
            'cost_per_pallet': best['cost_per_pallet']
        },
        'alternatives': {
            'second_best': second['warehouse'] if second else None,
            'second_cost': second['estimated_cost'] if second else None,
            'additional_cost': savings_vs_second,
            'additional_miles': second['miles'] - best['miles'] if second else None
        },
        'savings_analysis': {
            'vs_worst_option': round(savings_vs_worst, 2),
            'vs_second_option': round(savings_vs_second, 2),
            'savings_pct': round((savings_vs_worst / worst['estimated_cost']) * 100, 1) if worst['estimated_cost'] > 0 else 0,
            'annual_impact_estimate': round(savings_vs_worst * 12, 2)  # If monthly
        },
        'routing_analysis': routing_analysis,
        'edge_case_alert': edge_case,
        'insight': _generate_insight(best, worst, savings_vs_worst, routing_analysis, edge_case),
        'meta': {
            'processing_time_ms': round(processing_time * 1000, 1),
            'data_sources': ['google_distance_matrix', 'historical_freight_2025'],
            'cache_hits': 1 if place_info.get('from_cache') or distance_result.get('from_cache') else 0
        }
    }

    return result


def _fallback_analysis(destination: str, customer: str, city: str, state: str,
                       weight_lbs: float, error: str, edge_case: Optional[Dict]) -> Dict[str, Any]:
    """
    Smart fallback when Google API fails - use historical cost data
    """
    options = []

    for warehouse in ['Houston', 'West Memphis', 'California']:
        cost_data = get_state_based_cost(warehouse, state, weight_lbs)

        # Estimate distance based on state (rough approximations)
        approx_miles = _estimate_miles(warehouse, state)

        options.append({
            'warehouse': warehouse,
            'miles': approx_miles,
            'miles_note': 'estimated (Google API unavailable)',
            'drive_time': f"~{approx_miles // 50} hours",
            'estimated_cost': cost_data['estimated_cost'],
            'cost_per_lb': cost_data['rate_per_lb'],
            'cost_per_pallet': cost_data['cost_per_pallet'],
            'confidence': cost_data['confidence'],
            'data_source': 'historical_freight_2025'
        })

    options.sort(key=lambda x: x['estimated_cost'])
    best = options[0]
    worst = options[-1]
    savings = worst['estimated_cost'] - best['estimated_cost']

    return {
        'success': True,
        'fallback_mode': True,
        'fallback_reason': error,
        'destination': {
            'original': destination,
            'customer': customer,
            'city': city,
            'state': state,
            'lookup_method': 'state_level_historical'
        },
        'shipment': {
            'weight_lbs': weight_lbs,
            'pallets': round(weight_lbs / 920, 1)
        },
        'routing_options': options,
        'recommendation': {
            'best_warehouse': best['warehouse'],
            'best_cost': best['estimated_cost'],
            'best_miles': best['miles'],
            'confidence': best['confidence'],
            'cost_per_pallet': best['cost_per_pallet'],
            'note': 'Based on historical freight data (Google Maps unavailable)'
        },
        'savings_analysis': {
            'vs_worst_option': round(savings, 2),
            'savings_pct': round((savings / worst['estimated_cost']) * 100, 1) if worst['estimated_cost'] > 0 else 0
        },
        'edge_case_alert': edge_case,
        'insight': f"**{best['warehouse']}** is recommended based on historical cost data (${best['cost_per_pallet']:.0f}/pallet). Google Maps unavailable for distance verification.",
        'action_needed': 'Enable Google Distance Matrix API for precise distance-based routing'
    }


def _estimate_miles(warehouse: str, state: str) -> int:
    """Rough distance estimates when Google is unavailable"""
    # Very rough approximations based on geography
    distances = {
        'Houston': {
            'TX': 250, 'LA': 350, 'AR': 450, 'OK': 400, 'NM': 650,
            'MS': 500, 'AL': 600, 'TN': 650, 'GA': 800, 'FL': 900,
            'CA': 1500, 'VA': 1300, 'NY': 1600, 'default': 800
        },
        'West Memphis': {
            'AR': 50, 'TN': 100, 'MS': 150, 'MO': 300, 'IL': 350,
            'KY': 350, 'AL': 350, 'IN': 450, 'OH': 550, 'GA': 500,
            'TX': 500, 'VA': 750, 'NC': 650, 'FL': 700, 'PA': 850,
            'NY': 1000, 'CA': 1800, 'default': 600
        },
        'California': {
            'CA': 100, 'NV': 300, 'AZ': 500, 'OR': 450, 'WA': 650,
            'UT': 600, 'CO': 1000, 'TX': 1400, 'ID': 700,
            'VA': 2500, 'NY': 2700, 'FL': 2500, 'default': 1500
        }
    }

    state = state.upper()
    wh_distances = distances.get(warehouse, distances['West Memphis'])
    return wh_distances.get(state, wh_distances['default'])


def _generate_insight(best: Dict, worst: Dict, savings: float,
                      routing: Dict, edge_case: Optional[Dict]) -> str:
    """Generate smart, actionable insight"""

    parts = []

    # Main recommendation
    parts.append(f"**Ship from {best['warehouse']}** ({best['miles']:.0f} mi, {best['drive_time']})")

    # Savings
    if savings > 100:
        parts.append(f"Saves **${savings:,.0f}** vs {worst['warehouse']}")

    # Cost per pallet
    parts.append(f"Cost: **${best['cost_per_pallet']:.0f}/pallet**")

    # Routing override alert
    if not routing['recommendations_match']:
        parts.append(f"**ROUTING OVERRIDE:** Google Maps found a better route than state-based rules!")

    # Edge case alert
    if edge_case:
        parts.append(f"**Edge case:** {edge_case.get('reason', edge_case.get('note', 'Verify routing'))}")

    return " | ".join(parts)


def batch_optimize(destinations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optimize multiple destinations at once

    Input: [{'destination': 'Customer-City ST', 'weight_lbs': 40000}, ...]
    """
    results = []
    total_best_cost = 0
    total_worst_cost = 0

    for item in destinations:
        dest = item.get('destination', '')
        weight = item.get('weight_lbs', 40000)

        result = optimize_shipment(dest, weight)

        if result.get('success'):
            best_cost = result['recommendation']['best_cost']
            worst_cost = result['routing_options'][-1]['estimated_cost'] if result.get('routing_options') else best_cost

            total_best_cost += best_cost
            total_worst_cost += worst_cost

            results.append({
                'destination': dest,
                'best_warehouse': result['recommendation']['best_warehouse'],
                'best_cost': best_cost,
                'savings': worst_cost - best_cost,
                'confidence': result['recommendation'].get('confidence', 'MEDIUM')
            })
        else:
            results.append({
                'destination': dest,
                'error': result.get('error', 'Unknown error')
            })

    return {
        'success': True,
        'results': results,
        'summary': {
            'destinations_analyzed': len(destinations),
            'successful': len([r for r in results if 'error' not in r]),
            'total_optimized_cost': round(total_best_cost, 2),
            'total_worst_case_cost': round(total_worst_cost, 2),
            'total_savings': round(total_worst_cost - total_best_cost, 2)
        }
    }


# Quick test
if __name__ == '__main__':
    import json

    print("=== Testing Smart Google Maps ===\n")

    # Test single destination
    result = optimize_shipment('Oncor-Fort Worth TX', 40000)
    print("Single destination test:")
    print(json.dumps(result, indent=2, default=str))

    print("\n" + "="*50 + "\n")

    # Test batch
    batch_result = batch_optimize([
        {'destination': 'Stuart Irby-Fort Worth TX', 'weight_lbs': 427380},
        {'destination': 'Georgia Power-Forest Park GA', 'weight_lbs': 40000},
        {'destination': 'AEP-El Paso TX', 'weight_lbs': 40000},  # Edge case!
    ])
    print("Batch test:")
    print(json.dumps(batch_result, indent=2, default=str))
