import csv
import json
from datetime import datetime
from collections import defaultdict

SCREEN_MAPPING = {
    "1020": ("Movie Home", 1),
    "1021": ("Phim Detail", 2),
    "1022": ("Chọn Suất Chiếu", 3),
    "1023": ("Chọn Ghế", 4),
    "1024": ("Chọn Bắp Nước", 5),
    "1025": ("Confirm", 6),
    "1026": ("Thanh Toán", 7),
}

def parse_duration(duration_str):
    if not duration_str:
        return None
    duration_str = duration_str.replace('"', '').replace(',', '')
    try:
        return int(duration_str)
    except ValueError:
        return None

def get_screen_id(event_id):
    parts = event_id.split('.')
    return parts[0] if parts else None

def main():
    csv_file = "events_raw.csv"
    output_file = "funnel.json"
    
    sessions = defaultdict(list)
    total_events = 0
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_events += 1
            session_id = row['session_tracking_id']
            sessions[session_id].append(row)
    
    session_max_step = {}
    session_screen_ids = defaultdict(set)
    session_info = {}
    
    for session_id, events in sessions.items():
        screen_ids = set()
        for event in events:
            screen_id = get_screen_id(event['event_id'])
            if screen_id in SCREEN_MAPPING:
                screen_ids.add(screen_id)
        
        session_screen_ids[session_id] = screen_ids
        
        if screen_ids:
            max_screen_id = max(screen_ids, key=lambda x: SCREEN_MAPPING[x][1])
            max_step = SCREEN_MAPPING[max_screen_id][1]
            session_max_step[session_id] = max_step
        else:
            session_max_step[session_id] = 0
        
        if events:
            first_event = events[0]
            session_info[session_id] = {
                'platform': first_event['platform'],
                'network': first_event['network'],
                'user_segment': first_event['user_segment']
            }
    
    step_sessions = defaultdict(list)
    for session_id, max_step in session_max_step.items():
        for step in range(1, max_step + 1):
            step_sessions[step].append(session_id)
    
    total_sessions = len(step_sessions[1]) if step_sessions[1] else 1
    
    step_durations = defaultdict(list)
    step_breakdowns = defaultdict(lambda: {
        'by_platform': defaultdict(int),
        'by_network': defaultdict(int),
        'by_segment': defaultdict(int)
    })
    
    for step in range(1, 8):
        for session_id in step_sessions[step]:
            if session_id in session_info:
                info = session_info[session_id]
                step_breakdowns[step]['by_platform'][info['platform']] += 1
                step_breakdowns[step]['by_network'][info['network']] += 1
                step_breakdowns[step]['by_segment'][info['user_segment']] += 1
    
    for session_id, events in sessions.items():
        max_step = session_max_step[session_id]
        for event in events:
            screen_id = get_screen_id(event['event_id'])
            if screen_id in SCREEN_MAPPING:
                step = SCREEN_MAPPING[screen_id][1]
                if step <= max_step:
                    duration = parse_duration(event['duration_ms'])
                    if duration is not None:
                        step_durations[step].append(duration)
    
    funnel_steps = []
    prev_reached = total_sessions
    biggest_dropoff_step = 2
    biggest_dropoff_pct = 0.0
    
    for step in range(1, 8):
        screen_id = str(1019 + step)
        screen_name, _ = SCREEN_MAPPING[screen_id]
        sessions_reached = len(step_sessions[step])
        
        if sessions_reached == 0:
            sessions_reached = 0
            reach_pct = 0.0
            step_conversion_pct = 0.0
            dropoff_pct = 100.0
            sessions_dropped = prev_reached
            avg_duration_ms = 0
        else:
            reach_pct = round(sessions_reached / total_sessions * 100, 1)
            if step == 1:
                step_conversion_pct = 100.0
                dropoff_pct = 0.0
                sessions_dropped = 0
            else:
                step_conversion_pct = round(sessions_reached / prev_reached * 100, 1)
                dropoff_pct = round(100 - step_conversion_pct, 1)
                sessions_dropped = prev_reached - sessions_reached
            
            if step >= 2 and dropoff_pct > biggest_dropoff_pct:
                biggest_dropoff_pct = dropoff_pct
                biggest_dropoff_step = step
            
            durations = step_durations[step]
            avg_duration_ms = round(sum(durations) / len(durations)) if durations else 0
        
        prev_reached = sessions_reached
        
        by_platform = dict(step_breakdowns[step]['by_platform'])
        by_network = dict(step_breakdowns[step]['by_network'])
        by_segment = dict(step_breakdowns[step]['by_segment'])
        
        step_data = {
            "step": step,
            "screen_id": screen_id,
            "screen_name": screen_name,
            "sessions_reached": sessions_reached,
            "sessions_dropped": sessions_dropped,
            "reach_pct": reach_pct,
            "step_conversion_pct": step_conversion_pct,
            "dropoff_pct": dropoff_pct,
            "avg_duration_ms": avg_duration_ms,
            "breakdown": {
                "by_platform": by_platform,
                "by_network": by_network,
                "by_segment": by_segment
            }
        }
        funnel_steps.append(step_data)
    
    sessions_completed = len(step_sessions[7])
    overall_conversion_pct = round(sessions_completed / total_sessions * 100, 1)
    
    meta = {
        "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "source_file": csv_file,
        "total_sessions": total_sessions,
        "total_events": total_events,
        "overall_conversion_pct": overall_conversion_pct,
        "biggest_dropoff_step": biggest_dropoff_step,
        "biggest_dropoff_screen": SCREEN_MAPPING[str(1019 + biggest_dropoff_step)][0],
        "biggest_dropoff_pct": biggest_dropoff_pct
    }
    
    output = {
        "meta": meta,
        "funnel_steps": funnel_steps
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {output_file}")
    print(f"Total sessions: {total_sessions}")
    print(f"Total events: {total_events}")
    print(f"Overall conversion: {overall_conversion_pct}%")

if __name__ == "__main__":
    main()
