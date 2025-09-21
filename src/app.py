from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import logging
from src import utils
import os
import time
from src.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))

# Configure Flask to trust proxy headers
app.config['PREFERRED_URL_SCHEME'] = 'https'
# Trust the proxy headers (nginx is on localhost, so we can trust it)
app.config['PROXY_FIX'] = 1

def get_client_ip():
    """Get the real client IP address, handling proxy headers"""
    # Check for X-Forwarded-For header first
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs, take the first one
        forwarded_for = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        if forwarded_for:
            return forwarded_for
    
    # Fall back to X-Real-IP header
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # Finally fall back to remote_addr
    return request.remote_addr

# Request timing middleware
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        request_logger = logging.getLogger('request_timing')
        # Get query string
        query_string = request.query_string.decode('utf-8') if request.query_string else ''
        # Get JSON body if present
        try:
            json_body = request.get_json(silent=True)
        except Exception:
            json_body = None
        # Get headers, excluding sensitive ones
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']}
        # Only log response data if it's JSON
        response_data = None
        if response.is_json:
            response_data = response.get_json(silent=True)
        request_logger.info(
            "Request: %s %s - Status: %s - Duration: %.3fs - IP: %s - User-Agent: %s - Query: %s - JSON: %s - Headers: %s%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            get_client_ip(),
            request.headers.get('User-Agent', 'Unknown'),
            query_string,
            json_body,
            headers,
            f" - Response: {response_data}" if response_data is not None else ""
        )
    return response

@app.route('/')
def index():
    client_ip = get_client_ip()
    logger.info("Serving index page to %s", client_ip)
    start_time = time.time()
    
    # Generate dates for the next 30 days
    today = datetime.now()
    dates = []
    for i in range(30):
        date = today + timedelta(days=i)
        dates.append({
            'value': date.strftime('%Y-%m-%d'),
            'label': date.strftime('%A, %B %d, %Y')
        })
    
    # Get all destinations from database
    all_destinations = utils.get_all_towns()
    
    # Get station groups for the template
    station_groups = utils.STATION_GROUPS
    
    processing_time = time.time() - start_time
    logger.info("Index page served in %.3fs", processing_time)
    return render_template('index.html', dates=dates, destinations=all_destinations, station_groups=station_groups)

@app.route('/get_destinations', methods=['POST'])
def get_destinations():
    data = request.get_json()
    selected_date = data.get('date')
    stations = data.get('stations', ['PARIS (intramuros)'])
    
    # Handle both single station (backward compatibility) and multiple stations
    if isinstance(stations, str):
        stations = [stations]
    
    # If no stations provided or empty array, default to PARIS
    if not stations:
        stations = ['PARIS (intramuros)']
    
    client_ip = get_client_ip()
    logger.info("Processing destinations request from %s for date %s with stations: %s", 
                client_ip, selected_date, stations)
    
    start_time = time.time()
    try:
        # Get trips from all selected stations
        all_trips = []
        for station in stations:
            station_trips = utils.find_optimal_destinations(station, selected_date)
            all_trips.extend(station_trips)
        
        # Group trips by destination
        grouped_trips = {}
        for trip in all_trips:
            dest = trip['destination']
            if dest not in grouped_trips:
                grouped_trips[dest] = {
                    'destination': dest,
                    'trips': [],
                    'outbound_trips': [],
                    'return_trips': [],
                    'avg_travel_time': 0,
                    'max_time_at_destination': 0
                }
            
            grouped_trips[dest]['trips'].append(trip)
            
            # Add to outbound trips
            outbound_key = f"{trip['outbound_departure']}-{trip['outbound_arrival']}"
            existing_outbound_keys = [f"{t['departure']}-{t['arrival']}" for t in grouped_trips[dest]['outbound_trips']]
            if outbound_key not in existing_outbound_keys:
                grouped_trips[dest]['outbound_trips'].append({
                    'departure': trip['outbound_departure'],
                    'arrival': trip['outbound_arrival'],
                    'train_no': trip['outbound_train'],
                    'axe': trip.get('outbound_axe', 'N/A')
                })
            
            # Add to return trips
            return_key = f"{trip['return_departure']}-{trip['return_arrival']}"
            existing_return_keys = [f"{t['departure']}-{t['arrival']}" for t in grouped_trips[dest]['return_trips']]
            if return_key not in existing_return_keys:
                grouped_trips[dest]['return_trips'].append({
                    'departure': trip['return_departure'],
                    'arrival': trip['return_arrival'],
                    'train_no': trip['return_train'],
                    'axe': trip.get('return_axe', 'N/A')
                })
        
        # Calculate averages and max for each destination
        for dest_data in grouped_trips.values():
            travel_times = []
            times_at_dest = []
            axes = []
            
            for trip in dest_data['trips']:
                # Parse travel time (e.g., "2h49m" -> minutes)
                travel_time_str = trip['total_travel_time']
                travel_minutes = parse_time_to_minutes(travel_time_str)
                travel_times.append(travel_minutes)
                
                # Parse time at destination
                dest_time_str = trip['time_at_destination']
                dest_minutes = parse_time_to_minutes(dest_time_str)
                times_at_dest.append(dest_minutes)
                
                # Collect axes
                if 'outbound_axe' in trip:
                    axes.append(trip['outbound_axe'])
                if 'return_axe' in trip:
                    axes.append(trip['return_axe'])
            
            # Calculate average travel time and max time at destination
            avg_travel_minutes = round(sum(travel_times) / len(travel_times))
            max_dest_minutes = max(times_at_dest)
            
            dest_data['avg_travel_time'] = format_minutes_to_time(avg_travel_minutes)
            dest_data['max_time_at_destination'] = format_minutes_to_time(max_dest_minutes)
            
            # Sort outbound and return trips by departure time
            dest_data['outbound_trips'].sort(key=lambda x: x['departure'])
            dest_data['return_trips'].sort(key=lambda x: x['departure'])
            
            # Find the most frequent axis, with special handling for INTERNATIONAL
            from collections import Counter
            if axes:
                axe_counts = Counter(axes)
                
                # Check if ALL axes are INTERNATIONAL
                if len(axe_counts) == 1 and 'INTERNATIONAL' in axe_counts:
                    most_common_axe = 'INTERNATIONAL'
                else:
                    # Filter out INTERNATIONAL and find the most common non-international axis
                    non_international_axes = {axe: count for axe, count in axe_counts.items() if axe != 'INTERNATIONAL'}
                    if non_international_axes:
                        most_common_axe = max(non_international_axes.items(), key=lambda x: x[1])[0]
                    else:
                        most_common_axe = None
            else:
                most_common_axe = None
            dest_data['main_axe'] = most_common_axe
        
        # Sort by max time at destination (descending)
        sorted_destinations = sorted(
            grouped_trips.values(), 
            key=lambda x: parse_time_to_minutes(x['max_time_at_destination']), 
            reverse=True
        )
        
        processing_time = time.time() - start_time
        logger.info("Found %d destinations in %.3fs", len(sorted_destinations), processing_time)
        logger.debug("Destinations result: %s", sorted_destinations)
        return jsonify({'success': True, 'destinations': sorted_destinations})
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception("Error in get_destinations after %.3fs", processing_time)
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_trip_connections', methods=['POST'])
def get_trip_connections_endpoint():
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    origin = data.get('origin')
    destination = data.get('destination')

    # Validate input
    if not (start_date and end_date and origin and destination):
        return jsonify({'success': False, 'error': 'Paramètres requis manquants.'}), 400

    # Ensure origin and destination are always flat lists of strings
    if isinstance(origin, str):
        origins = [origin]
    else:
        origins = list(origin) if origin else []
    if isinstance(destination, str):
        destinations = [destination]
    else:
        destinations = list(destination) if destination else []

    client_ip = get_client_ip()
    logger.info(
        "Processing connections request from %s: %s -> %s (%s to %s)",
        client_ip,
        origins,
        destinations,
        start_date,
        end_date,
    )
    
    start_time = time.time()
    try:
        # Build date window (inclusive)
        from datetime import datetime, timedelta
        d1 = datetime.strptime(start_date, '%Y-%m-%d')
        d2 = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (d2 - d1).days + 1
        dates = [(d1 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_days)]
        # Allow station group connections by default
        allow_station_groups = data.get('allow_station_groups', True)
        results = utils.get_trip_connections(dates, origins, destinations, allow_station_groups=allow_station_groups)
        processing_time = time.time() - start_time
        logger.info("Found %d connections in %.3fs", len(results), processing_time)
        logger.debug("Connections result: %s", results)
        return jsonify({'success': True, 'connections': results})
    except Exception as e:
        processing_time = time.time() - start_time
        logger.exception("Error in get_trip_connections_endpoint after %.3fs", processing_time)
        return jsonify({'success': False, 'error': str(e)})

def parse_time_to_minutes(time_str):
    """Convert time string like '2h49m' to minutes"""
    import re
    hours = 0
    minutes = 0
    
    # Extract hours
    hour_match = re.search(r'(\d+)h', time_str)
    if hour_match:
        hours = int(hour_match.group(1))
    
    # Extract minutes
    minute_match = re.search(r'(\d+)m', time_str)
    if minute_match:
        minutes = int(minute_match.group(1))
    
    return hours * 60 + minutes

def format_minutes_to_time(minutes):
    """Convert minutes to time string like '2h49m'"""
    hours = minutes // 60
    mins = minutes % 60
    
    if hours == 0:
        return f"{mins}m"
    elif mins == 0:
        return f"{hours}h"
    else:
        return f"{hours}h{mins}m"

if __name__ == '__main__':
    # Use environment variables for production settings
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    port = 5001 if debug_mode else 5000
    app.run(
        debug=debug_mode,
        host='0.0.0.0', 
        port=port
    )
