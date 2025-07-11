from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import utils
import os

app = Flask(__name__)

@app.route('/')
def index():
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
        
        return jsonify({'success': True, 'destinations': sorted_destinations})
    except Exception as e:
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
        return jsonify({'success': True, 'connections': results})
    except Exception as e:
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
