#Visualiser
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Arc, Circle, FancyArrowPatch, PathPatch
import matplotlib.lines as mlines
import matplotlib.transforms as mtransforms
import numpy as np
import matplotlib.patheffects as path_effects
from matplotlib.path import Path
import os
import json
import re
import prior
from PIL import Image
import io

def plot_enhanced_floor_plan(house_data, return_image=True):
    dataset = prior.load_dataset("procthor-10k")
    fig, ax = plt.subplots()

    with open("output.json", "r") as f:
        data = json.load(f)

    scene_id = data.get("id", "")

    match = re.search(r"scene_(\d+)", scene_id)
    scene_number = int(match.group(1))
    # Usage with your dataset

    house_data = dataset["train"][scene_number]
    fig, ax = plt.subplots(figsize=(14, 14), facecolor='white')
    ax.set_aspect('equal')
    ax.set_title('Floor Plan', fontsize=16, fontweight='bold')
    
    # Define color scheme
    wall_color = '#2c2c2c'
    room_colors = {
        'Bedroom': '#bde0fe',
        'Bathroom': '#a2d2ff',
        'Kitchen': '#ffd6a5',
        'LivingRoom': '#caffbf',
        'Dining': '#fdffb6',
        'Hallway': '#ffffff',
        'Office': '#d8bbff',
        'Closet': '#ffc6ff',
        'Utility': '#eeeeee'
    }
    
    # Create empty containers for legend items
    legend_elements = []
    room_polygons = {}
    room_centers = {}
    
    # Store wall segments for later use with doors and windows
    all_walls = []
    for wall in house_data['walls']:
        points = [(p['x'], p['z']) for p in wall['polygon']]
        for i in range(len(points) - 1):
            all_walls.append((points[i], points[i+1]))
    
    # Plot rooms
    for room in house_data['rooms']:
        # Extract room type or assign default
        room_type = room.get('roomType', 'Unknown')
        
        # Map AI2Thor room types to common names
        room_type_mapping = {
            'Bedroom': 'Bedroom',
            'Bathroom': 'Bathroom',
            'Kitchen': 'Kitchen',
            'LivingRoom': 'Living Room',
            'Dining': 'Dining Room',
            'Office': 'Office',
            'Closet': 'Closet',
            'Hallway': 'Hallway',
            'Utility': 'Utility'
        }
        
        display_name = room_type_mapping.get(room_type, room_type)
        
        # Get room vertices
        verts = [(p['x'], p['z']) for p in room['floorPolygon']]
        
        # Determine room color
        face_color = room_colors.get(room_type, '#f0f0f0')
        
        # Create room polygon
        poly = Polygon(verts, closed=True, edgecolor=None, 
                      facecolor=face_color, lw=0, alpha=0.5)
        ax.add_patch(poly)
        
        # Store room polygon and calculate center for labeling
        room_polygons[room_type] = verts
        x_coords = [p[0] for p in verts]
        z_coords = [p[1] for p in verts]
        center_x = sum(x_coords) / len(x_coords)
        center_z = sum(z_coords) / len(z_coords)
        room_centers[room_type] = (center_x, center_z)
        
        # Calculate room area (approximate)
        area = 0
        for i in range(len(verts)):
            j = (i + 1) % len(verts)
            area += verts[i][0] * verts[j][1]
            area -= verts[j][0] * verts[i][1]
        area = abs(area) / 2
        area_sqft = int(area * 10.764)  # Convert to sq ft (assuming units are in meters)
        
        # Add room label with area
        label_text = f"{display_name}\n{area_sqft} sq ft"
        text = ax.text(center_x, center_z, label_text, 
                 ha='center', va='center', fontsize=9, fontweight='bold')
        text.set_path_effects([path_effects.withStroke(linewidth=3, foreground='white')])
    
    # Plot walls with thick black lines
    for wall in house_data['walls']:
        xs = [p['x'] for p in wall['polygon']]
        zs = [p['z'] for p in wall['polygon']]
        ax.plot(xs, zs, color=wall_color, lw=4, solid_capstyle='round')
    
    # Dictionary to map object types to appropriate furniture symbols
    furniture_symbols = {
        'chair': {'shape': 'chair', 'color': '#8B4513', 'size': 1.0},
        'sofa': {'shape': 'sofa', 'color': '#8B4513', 'size': 1.5},
        'table': {'shape': 'table', 'color': '#A0522D', 'size': 1.2},
        'desk': {'shape': 'table', 'color': '#A0522D', 'size': 1.2},
        'bed': {'shape': 'bed', 'color': '#4169E1', 'size': 2.0},
        'toilet': {'shape': 'toilet', 'color': '#6495ED', 'size': 0.8},
        'sink': {'shape': 'sink', 'color': '#6495ED', 'size': 0.7},
        'bathtub': {'shape': 'bathtub', 'color': '#6495ED', 'size': 1.5},
        'shower': {'shape': 'shower', 'color': '#6495ED', 'size': 1.0},
        'fridge': {'shape': 'fridge', 'color': '#FFA07A', 'size': 1.0},
        'stove': {'shape': 'stove', 'color': '#FFA07A', 'size': 1.0},
        'counter': {'shape': 'counter', 'color': '#FFA07A', 'size': 1.2},
        'cabinet': {'shape': 'cabinet', 'color': '#DEB887', 'size': 0.8},
        'plant': {'shape': 'plant', 'color': '#228B22', 'size': 0.7}
    }

    # Function to draw furniture symbols
    def draw_furniture(center_x, center_z, furniture_type, rotation=0):
        props = furniture_symbols.get(furniture_type, 
                                    {'shape': 'generic', 'color': '#808080', 'size': 0.8})
        color = props['color']
        size = props['size']
        shape = props['shape']
        
        # Apply rotation in radians
        rot_rad = np.radians(rotation)
        rotation_matrix = np.array([
            [np.cos(rot_rad), -np.sin(rot_rad)],
            [np.sin(rot_rad), np.cos(rot_rad)]
        ])
        
        def rotate_point(point):
            return np.dot(rotation_matrix, np.array(point)) + np.array([center_x, center_z])
        
        if shape == 'bed':
            # Bed with headboard
            w, h = 1.4*size, 2.0*size
            points = [
                (-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2), (-w/2, -h/2)
            ]
            # Headboard
            headboard = [
                (-w/2, h/2), (w/2, h/2), (w/2, h/2+0.2*size), (-w/2, h/2+0.2*size), (-w/2, h/2)
            ]
            
            # Draw bed frame
            rotated_points = [rotate_point(p) for p in points]
            ax.plot([p[0] for p in rotated_points], [p[1] for p in rotated_points], 
                   color=color, lw=2, solid_capstyle='round')
            
            # Draw headboard
            rotated_headboard = [rotate_point(p) for p in headboard]
            ax.plot([p[0] for p in rotated_headboard], 
                   [p[1] for p in rotated_headboard], 
                   color=color, lw=2, solid_capstyle='round')
            
            # Draw mattress lines
            mattress_lines = [
                [(-w/2+0.1*size, -h/2+0.1*size), (w/2-0.1*size, -h/2+0.1*size)],
                [(w/2-0.1*size, -h/2+0.1*size), (w/2-0.1*size, h/2-0.1*size)],
                [(w/2-0.1*size, h/2-0.1*size), (-w/2+0.1*size, h/2-0.1*size)],
                [(-w/2+0.1*size, h/2-0.1*size), (-w/2+0.1*size, -h/2+0.1*size)]
            ]
            for line in mattress_lines:
                rotated_line = [rotate_point(p) for p in line]
                ax.plot([p[0] for p in rotated_line], [p[1] for p in rotated_line], 
                       color=color, lw=1, linestyle='--')
                       
            # Add a pillow
            pillow_h = 0.3*size
            pillow_points = [
                (-w/3, h/2-pillow_h), (w/3, h/2-pillow_h), 
                (w/3, h/2-0.1*size), (-w/3, h/2-0.1*size),
                (-w/3, h/2-pillow_h)
            ]
            rotated_pillow = [rotate_point(p) for p in pillow_points]
            ax.plot([p[0] for p in rotated_pillow], [p[1] for p in rotated_pillow], 
                   color='#DDDDDD', lw=1)
            poly = Polygon([rotate_point(p) for p in pillow_points[:-1]], 
                          closed=True, edgecolor=color, facecolor='#FFFFFF', 
                          lw=1, alpha=0.7)
            ax.add_patch(poly)
            
        elif shape == 'chair':
            # Simple chair
            r = 0.3*size
            circle = Circle((center_x, center_z), r, facecolor='none', 
                           edgecolor=color, lw=1.5)
            ax.add_patch(circle)
            
            # Chair back
            back_len = 0.2*size
            back_point = rotate_point((0, r))
            back_end = rotate_point((0, r + back_len))
            ax.plot([back_point[0], back_end[0]], [back_point[1], back_end[1]], 
                   color=color, lw=1.5)
                   
        elif shape == 'sofa':
            # Sofa with curved back
            w, d = 1.6*size, 0.8*size
            
            # Base rectangle for seat
            seat_points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_seat = [rotate_point(p) for p in seat_points]
            poly = Polygon(rotated_seat[:-1], closed=True, 
                          edgecolor=color, facecolor='none', lw=1.5)
            ax.add_patch(poly)
            
            # Back and armrests with curved corners
            back_d = 0.15*size
            
            # Left armrest
            armrest_w = 0.15*size
            left_arm = [
                (-w/2, -d/2), (-w/2, d/2), (-w/2-back_d, d/2), 
                (-w/2-back_d, -d/2+armrest_w), (-w/2, -d/2)
            ]
            rotated_left = [rotate_point(p) for p in left_arm]
            ax.plot([p[0] for p in rotated_left], [p[1] for p in rotated_left], 
                   color=color, lw=1.5)
            
            # Right armrest
            right_arm = [
                (w/2, -d/2), (w/2, d/2), (w/2+back_d, d/2), 
                (w/2+back_d, -d/2+armrest_w), (w/2, -d/2)
            ]
            rotated_right = [rotate_point(p) for p in right_arm]
            ax.plot([p[0] for p in rotated_right], [p[1] for p in rotated_right], 
                   color=color, lw=1.5)
            
            # Back of sofa
            back = [
                (-w/2, d/2), (w/2, d/2), (w/2+back_d, d/2), 
                (-w/2-back_d, d/2), (-w/2, d/2)
            ]
            rotated_back = [rotate_point(p) for p in back]
            ax.plot([p[0] for p in rotated_back], [p[1] for p in rotated_back], 
                   color=color, lw=1.5)
            
            # Sofa cushions
            cushion_w = w/3
            for i in range(3):
                x_start = -w/2 + i*cushion_w
                cushion = [
                    (x_start, -d/4), (x_start+cushion_w, -d/4),
                    (x_start+cushion_w, d/4), (x_start, d/4),
                    (x_start, -d/4)
                ]
                rotated_cushion = [rotate_point(p) for p in cushion]
                ax.plot([p[0] for p in rotated_cushion], 
                       [p[1] for p in rotated_cushion], 
                       color=color, lw=1, linestyle=':')
        
        elif shape == 'table':
            # Table as rectangle
            w, d = 1.2*size, 0.8*size
            points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_points = [rotate_point(p) for p in points]
            poly = Polygon(rotated_points[:-1], closed=True, 
                          edgecolor=color, facecolor='none', lw=1.5)
            ax.add_patch(poly)
            
            # Table legs at corners
            leg_size = 0.06*size
            for corner in [(-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)]:
                leg_x, leg_z = corner
                leg_points = [
                    (leg_x-leg_size, leg_z-leg_size),
                    (leg_x+leg_size, leg_z-leg_size),
                    (leg_x+leg_size, leg_z+leg_size),
                    (leg_x-leg_size, leg_z+leg_size),
                    (leg_x-leg_size, leg_z-leg_size)
                ]
                rotated_leg = [rotate_point(p) for p in leg_points]
                ax.plot([p[0] for p in rotated_leg], [p[1] for p in rotated_leg], 
                       color=color, lw=1)
            
        elif shape == 'toilet':
            # Toilet bowl as oval
            r_x, r_z = 0.3*size, 0.4*size
            theta = np.linspace(0, 2*np.pi, 50)
            x = r_x * np.cos(theta)
            z = r_z * np.sin(theta)
            
            # Rotate points
            rotated_points = [rotate_point((x[i], z[i])) for i in range(len(x))]
            
            # Draw bowl
            ax.plot([p[0] for p in rotated_points], [p[1] for p in rotated_points], 
                   color=color, lw=1.5)
            
            # Draw toilet tank
            tank_h = 0.3*size
            tank_w = 0.5*size
            tank_points = [
                (-tank_w/2, r_z), (tank_w/2, r_z),
                (tank_w/2, r_z+tank_h), (-tank_w/2, r_z+tank_h),
                (-tank_w/2, r_z)
            ]
            rotated_tank = [rotate_point(p) for p in tank_points]
            ax.plot([p[0] for p in rotated_tank], [p[1] for p in rotated_tank], 
                   color=color, lw=1.5)
                   
            # Toilet seat
            seat_points = []
            for i in range(30):
                angle = np.pi * i / 29
                seat_points.append((r_x * 0.8 * np.cos(angle), r_z * 0.8 * np.sin(angle)))
            
            rotated_seat = [rotate_point(p) for p in seat_points]
            ax.plot([p[0] for p in rotated_seat], [p[1] for p in rotated_seat], 
                   color=color, lw=1, linestyle='-')
            
        elif shape == 'sink':
            # Sink as circle with faucet
            r = 0.3*size
            theta = np.linspace(0, 2*np.pi, 50)
            x = r * np.cos(theta)
            z = r * np.sin(theta)
            
            # Rotate points
            rotated_points = [rotate_point((x[i], z[i])) for i in range(len(x))]
            
            # Draw sink
            ax.plot([p[0] for p in rotated_points], [p[1] for p in rotated_points], 
                   color=color, lw=1.5)
            
            # Draw faucet
            faucet_h = 0.2*size
            faucet_base = rotate_point((0, -r*0.7))
            faucet_top = rotate_point((0, -r*0.7-faucet_h))
            ax.plot([faucet_base[0], faucet_top[0]], 
                   [faucet_base[1], faucet_top[1]], 
                   color=color, lw=1.5)
            
            # Draw water tap
            tap_w = 0.15*size
            tap_left = rotate_point((-tap_w, -r*0.7-faucet_h))
            tap_right = rotate_point((tap_w, -r*0.7-faucet_h))
            ax.plot([tap_left[0], tap_right[0]], [tap_left[1], tap_right[1]], 
                   color=color, lw=1.5)
            
        elif shape == 'bathtub':
            # Bathtub as rectangle with rounded ends
            w, h = 1.7*size, 0.8*size
            
            # Main rectangle
            rect_points = [
                (-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2), (-w/2, -h/2)
            ]
            rotated_rect = [rotate_point(p) for p in rect_points]
            ax.plot([p[0] for p in rotated_rect], [p[1] for p in rotated_rect], 
                   color=color, lw=1.5)
            
            # Inner rectangle (tub interior)
            inner_margin = 0.1*size
            inner_points = [
                (-w/2+inner_margin, -h/2+inner_margin),
                (w/2-inner_margin, -h/2+inner_margin),
                (w/2-inner_margin, h/2-inner_margin),
                (-w/2+inner_margin, h/2-inner_margin),
                (-w/2+inner_margin, -h/2+inner_margin)
            ]
            rotated_inner = [rotate_point(p) for p in inner_points]
            ax.plot([p[0] for p in rotated_inner], [p[1] for p in rotated_inner], 
                   color=color, lw=1.5)
            
            # Drain
            drain_center = rotate_point((0, -h/4))
            drain_r = 0.05*size
            drain = Circle(drain_center, drain_r, facecolor='none', 
                          edgecolor=color, lw=1)
            ax.add_patch(drain)
            
            # Faucet at one end
            faucet_base = rotate_point((w/3, h/2-inner_margin/2))
            faucet_h = 0.15*size
            faucet_top = rotate_point((w/3, h/2-inner_margin/2-faucet_h))
            ax.plot([faucet_base[0], faucet_top[0]], 
                   [faucet_base[1], faucet_top[1]], 
                   color=color, lw=1.5)
            
        elif shape == 'shower':
            # Shower as square with shower head
            w = 0.9*size
            
            # Shower base
            base_points = [
                (-w/2, -w/2), (w/2, -w/2), (w/2, w/2), (-w/2, w/2), (-w/2, -w/2)
            ]
            rotated_base = [rotate_point(p) for p in base_points]
            ax.plot([p[0] for p in rotated_base], [p[1] for p in rotated_base], 
                   color=color, lw=1.5)
            
            # Shower drain
            drain_center = rotate_point((0, 0))
            drain_r = 0.05*size
            drain = Circle(drain_center, drain_r, facecolor='none', 
                          edgecolor=color, lw=1)
            ax.add_patch(drain)
            
            # Shower head on wall
            head_pos = rotate_point((w/2-0.1*size, w/2-0.1*size))
            head_r = 0.08*size
            head = Circle(head_pos, head_r, facecolor='none', 
                         edgecolor=color, lw=1.5)
            ax.add_patch(head)
            
            # Water drops from shower head
            for i in range(5):
                angle = np.pi/4 + i*np.pi/16
                drop_len = 0.12*size
                drop_start = (head_pos[0] - head_r*np.cos(angle), 
                             head_pos[1] - head_r*np.sin(angle))
                drop_end = (drop_start[0] - drop_len*np.cos(angle),
                           drop_start[1] - drop_len*np.sin(angle))
                ax.plot([drop_start[0], drop_end[0]], [drop_start[1], drop_end[1]], 
                       color='#6495ED', lw=1, linestyle=':')
            
        elif shape == 'fridge':
            # Fridge as tall rectangle
            w, d, h = 0.7*size, 0.7*size, 1.6*size
            
            # Main body
            main_points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_main = [rotate_point(p) for p in main_points]
            ax.plot([p[0] for p in rotated_main], [p[1] for p in rotated_main], 
                   color=color, lw=1.5)
            
            # Door handle
            handle_x = w/2 - 0.1*size
            handle_len = 0.4*size
            handle_start = rotate_point((handle_x, -handle_len/2))
            handle_end = rotate_point((handle_x, handle_len/2))
            ax.plot([handle_start[0], handle_end[0]], 
                   [handle_start[1], handle_end[1]], 
                   color=color, lw=2)
            
            # Freezer/fridge divider
            divider_y = d/5
            divider_start = rotate_point((-w/2, divider_y))
            divider_end = rotate_point((w/2, divider_y))
            ax.plot([divider_start[0], divider_end[0]], 
                   [divider_start[1], divider_end[1]], 
                   color=color, lw=1, linestyle='--')
            
        elif shape == 'stove':
            # Stove as rectangle with burners
            w, d = 0.8*size, 0.7*size
            
            # Main body
            main_points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_main = [rotate_point(p) for p in main_points]
            ax.plot([p[0] for p in rotated_main], [p[1] for p in rotated_main], 
                   color=color, lw=1.5)
            
            # Four burners in a grid
            burner_r = 0.1*size
            burner_positions = [
                (-w/4, -d/4), (w/4, -d/4),
                (-w/4, d/4), (w/4, d/4)
            ]
            
            for pos in burner_positions:
                burner_center = rotate_point(pos)
                burner = Circle(burner_center, burner_r, facecolor='none', 
                               edgecolor=color, lw=1)
                ax.add_patch(burner)
                
                # Inner circle for burner
                inner = Circle(burner_center, burner_r/2, facecolor='none', 
                              edgecolor=color, lw=1)
                ax.add_patch(inner)
            
            # Control knobs
            knob_y = -d/2 + 0.1*size
            knob_r = 0.05*size
            knob_positions = [
                (-w/3, knob_y), (-w/9, knob_y), 
                (w/9, knob_y), (w/3, knob_y)
            ]
            
            for pos in knob_positions:
                knob_center = rotate_point(pos)
                knob = Circle(knob_center, knob_r, facecolor='none', 
                             edgecolor=color, lw=1)
                ax.add_patch(knob)
            
        elif shape == 'counter':
            # Counter as rectangle
            w, d = 1.4*size, 0.7*size
            
            # Main rectangle
            rect_points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_rect = [rotate_point(p) for p in rect_points]
            ax.plot([p[0] for p in rotated_rect], [p[1] for p in rotated_rect], 
                   color=color, lw=1.5)
            
            # Counter pattern
            for i in range(1, int(w/0.2)):
                x = -w/2 + i*0.2*size
                line_start = rotate_point((x, -d/2))
                line_end = rotate_point((x, d/2))
                ax.plot([line_start[0], line_end[0]], 
                       [line_start[1], line_end[1]], 
                       color=color, lw=0.5, linestyle=':')
            
        elif shape == 'cabinet':
            # Cabinet as rectangle
            w, d = 0.8*size, 0.6*size
            
            # Main rectangle
            rect_points = [
                (-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2), (-w/2, -d/2)
            ]
            rotated_rect = [rotate_point(p) for p in rect_points]
            ax.plot([p[0] for p in rotated_rect], [p[1] for p in rotated_rect], 
                   color=color, lw=1.5)
            
            # Cabinet doors
            door_margin = 0.05*size
            door_points = [
                (-w/2+door_margin, -d/2+door_margin),
                (0-door_margin/2, -d/2+door_margin),
                (0-door_margin/2, d/2-door_margin),
                (-w/2+door_margin, d/2-door_margin),
                (-w/2+door_margin, -d/2+door_margin)
            ]
            rotated_door = [rotate_point(p) for p in door_points]
            ax.plot([p[0] for p in rotated_door], [p[1] for p in rotated_door], 
                   color=color, lw=1)
            
            door2_points = [
                (0+door_margin/2, -d/2+door_margin),
                (w/2-door_margin, -d/2+door_margin),
                (w/2-door_margin, d/2-door_margin),
                (0+door_margin/2, d/2-door_margin),
                (0+door_margin/2, -d/2+door_margin)
            ]
            rotated_door2 = [rotate_point(p) for p in door2_points]
            ax.plot([p[0] for p in rotated_door2], [p[1] for p in rotated_door2], 
                   color=color, lw=1)
            
            # Door handles
            handle1 = rotate_point((0-door_margin, 0))
            handle1_r = 0.03*size
            handle_1 = Circle(handle1, handle1_r, facecolor=color, 
                             edgecolor=color, lw=1)
            ax.add_patch(handle_1)
            
            handle2 = rotate_point((0+door_margin, 0))
            handle2_r = 0.03*size
            handle_2 = Circle(handle2, handle2_r, facecolor=color, 
                             edgecolor=color, lw=1)
            ax.add_patch(handle_2)
            
        elif shape == 'plant':
            # Plant as circle with leaves
            pot_r = 0.2*size
            pot_h = 0.15*size
            
            # Pot base
            base_center = rotate_point((0, 0))
            base_left = rotate_point((-pot_r, 0))
            base_right = rotate_point((pot_r, 0))
            ax.plot([base_left[0], base_right[0]], 
                   [base_left[1], base_right[1]], 
                   color='#8B4513', lw=1.5)
            
            # Pot sides
            side_left_top = rotate_point((-pot_r*0.8, pot_h))
            side_right_top = rotate_point((pot_r*0.8, pot_h))
            ax.plot([base_left[0], side_left_top[0]], 
                   [base_left[1], side_left_top[1]], 
                   color='#8B4513', lw=1.5)
            ax.plot([base_right[0], side_right_top[0]], 
                   [base_right[1], side_right_top[1]], 
                   color='#8B4513', lw=1.5)
            ax.plot([side_left_top[0], side_right_top[0]], 
                   [side_left_top[1], side_right_top[1]], 
                   color='#8B4513', lw=1.5)
            
            # Plant leaves
            leaf_h = 0.4*size
            for angle in range(0, 360, 45):
                rad = np.radians(angle)
                leaf_vec = np.array([np.cos(rad), np.sin(rad)]) * leaf_h
                leaf_end = rotate_point((leaf_vec[0], leaf_vec[1] + pot_h/2))
                leaf_mid = rotate_point((leaf_vec[0]*0.7, leaf_vec[1]*0.7 + pot_h/2))
                
                # Curve the leaf
                ctrl_offset = np.array([-leaf_vec[1], leaf_vec[0]]) * 0.2
                ctrl_point = rotate_point((leaf_vec[0]*0.5 + ctrl_offset[0],
                                          leaf_vec[1]*0.5 + ctrl_offset[1] + pot_h/2))
                
                leaf_start = rotate_point((0, pot_h))
                
                # Create a curved path for the leaf
                leaf_path = Path([leaf_start, ctrl_point, leaf_end],
                                [Path.MOVETO, Path.CURVE3, Path.CURVE3])
                
                leaf_patch = PathPatch(leaf_path, facecolor='none', 
                                      edgecolor='#228B22', lw=1.5)
                ax.add_patch(leaf_patch)
                
        else:
            # Generic object as circle with label
            circle = Circle((center_x, center_z), 0.3*size, facecolor='none', 
                           edgecolor=color, lw=1.5)
            ax.add_patch(circle)
    
    # Plot furniture based on object types
    for obj in house_data['objects']:
        obj_id = obj['assetId'].lower()
        obj_x = obj['position']['x']
        obj_z = obj['position']['z']
        rotation = obj.get('rotation', {}).get('y', 0)
        
        # Determine furniture type from object ID
        furniture_type = 'generic'
        for key in furniture_symbols.keys():
            if key in obj_id:
                furniture_type = key
                break
                
        draw_furniture(obj_x, obj_z, furniture_type, rotation)
    
    # Plot doors with door swing
    for door in house_data['doors']:
        # Get door polygon
        hole = door['holePolygon']
        if len(hole) >= 2:
            # Find midpoint of the door
            x_coords = [p['x'] for p in hole]
            z_coords = [p['z'] for p in hole]
            x_min, x_max = min(x_coords), max(x_coords)
            z_min, z_max = min(z_coords), max(z_coords)
            
            # Determine if door is horizontal or vertical
            width = x_max - x_min
            height = z_max - z_min
            
            # Door center point
            center_x = (x_min + x_max) / 2
            center_z = (z_min + z_max) / 2
            
            # Door frame (thin rectangle)
            rect = Rectangle((x_min, z_min), width, height,
                           facecolor='none', edgecolor=wall_color, lw=2)
            ax.add_patch(rect)
            
            # Door swing arc
            swing_radius = max(width, height) * 0.9
            
            # Determine the swing direction (inward/outward)
            # For simplicity, alternate directions
            if (x_min + z_min) % 2 == 0:
                start_angle = 0
                if width > height:  # horizontal door
                    start_angle = 90 if z_min < center_z else 270
                else:  # vertical door
                    start_angle = 0 if x_min < center_x else 180
            else:
                start_angle = 180
                if width > height:  # horizontal door
                    start_angle = 270 if z_min < center_z else 90
                else:  # vertical door
                    start_angle = 180 if x_min < center_x else 0
            
            # Create arc for door swing
            swing_arc = Arc((center_x, center_z), swing_radius, swing_radius,
                          angle=0, theta1=start_angle, theta2=start_angle+90,
                          linewidth=1, color='#d62728', linestyle='-')
            ax.add_patch(swing_arc)
            
            # Add a small circle to indicate hinge point
            hinge_x, hinge_z = center_x, center_z
            if width > height:  # horizontal door
                hinge_x = x_min if start_angle == 90 or start_angle == 270 else x_max
            else:  # vertical door
                hinge_z = z_min if start_angle == 0 or start_angle == 180 else z_max
                
            hinge = Circle((hinge_x, hinge_z), 0.05, facecolor='#d62728',
                          edgecolor='#d62728', lw=1)
            ax.add_patch(hinge)
    
    # Plot windows
    window_positions = []
    
    # For simplicity, place windows on external walls
    # Algorithm: Find points with only one adjacent room (likely external walls)
    for wall in all_walls:
        # Check if this wall segment is on an external wall
        # For demonstration, place windows randomly
        if np.random.random() < 0.3:  # 30% chance of a window on each wall
            # Get midpoint of wall
            mid_x = (wall[0][0] + wall[1][0]) / 2
            mid_z = (wall[0][1] + wall[1][1]) / 2
            
            # Calculate wall length
            wall_length = np.sqrt((wall[1][0] - wall[0][0])**2 + (wall[1][1] - wall[0][1])**2)
            
            # Only place windows on walls of sufficient length
            if wall_length > 1.0:
                window_positions.append((mid_x, mid_z, wall))
                
    # Draw windows
    for wx, wz, wall in window_positions:
        # Calculate wall direction
        wall_dx = wall[1][0] - wall[0][0]
        wall_dz = wall[1][1] - wall[0][1]
        wall_length = np.sqrt(wall_dx**2 + wall_dz**2)
        
        # Normalize direction
        if wall_length > 0:
            wall_dx /= wall_length
            wall_dz /= wall_length
            
            # Perpendicular direction
            perp_dx = -wall_dz
            perp_dz = wall_dx
            
            # Window dimensions
            window_width = 0.8
            window_thickness = 0.2
            
            # Calculate window corners
            half_width = window_width / 2
            corner1 = (wx - half_width * wall_dx - window_thickness/2 * perp_dx,
                      wz - half_width * wall_dz - window_thickness/2 * perp_dz)
            corner2 = (wx + half_width * wall_dx - window_thickness/2 * perp_dx,
                      wz + half_width * wall_dz - window_thickness/2 * perp_dz)
            corner3 = (wx + half_width * wall_dx + window_thickness/2 * perp_dx,
                      wz + half_width * wall_dz + window_thickness/2 * perp_dz)
            corner4 = (wx - half_width * wall_dx + window_thickness/2 * perp_dx,
                      wz - half_width * wall_dz + window_thickness/2 * perp_dz)
            
            # Draw window
            window_poly = Polygon([corner1, corner2, corner3, corner4], closed=True,
                                edgecolor=wall_color, facecolor='white', alpha=0.7, lw=1.5)
            ax.add_patch(window_poly)
            
            # Add window panes (crossbars)
            mid_h = (corner1[0] + corner2[0])/2, (corner1[1] + corner2[1])/2
            mid_v = (corner1[0] + corner4[0])/2, (corner1[1] + corner4[1])/2
            mid_h2 = (corner3[0] + corner4[0])/2, (corner3[1] + corner4[1])/2
            mid_v2 = (corner2[0] + corner3[0])/2, (corner2[1] + corner3[1])/2
            
            # Horizontal divider
            ax.plot([mid_v[0], mid_v2[0]], [mid_v[1], mid_v2[1]], 
                   color=wall_color, lw=1)
            
            # Vertical divider
            ax.plot([mid_h[0], mid_h2[0]], [mid_h[1], mid_h2[1]], 
                   color=wall_color, lw=1)
    
    # Add compass rose
    compass_size = 1.0
    compass_x = max([p[0] for wall in all_walls for p in wall]) + 2
    compass_z = min([p[1] for wall in all_walls for p in wall]) + 2
    
    # Draw compass circle
    compass_circle = Circle((compass_x, compass_z), compass_size/2, 
                           facecolor='none', edgecolor='black', lw=1.5)
    ax.add_patch(compass_circle)
    
    # North line and label
    ax.plot([compass_x, compass_x], 
           [compass_z, compass_z + compass_size/2], 
           color='black', lw=1.5)
    ax.text(compass_x, compass_z + compass_size/2 + 0.2, 'N', 
           ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # East line and label
    ax.plot([compass_x, compass_x + compass_size/2], 
           [compass_z, compass_z], 
           color='black', lw=1.5)
    ax.text(compass_x + compass_size/2 + 0.2, compass_z, 'E', 
           ha='left', va='center', fontsize=10, fontweight='bold')
    
    # South line and label
    ax.plot([compass_x, compass_x], 
           [compass_z, compass_z - compass_size/2], 
           color='black', lw=1.5)
    ax.text(compass_x, compass_z - compass_size/2 - 0.2, 'S', 
           ha='center', va='top', fontsize=10, fontweight='bold')
    
    # West line and label
    ax.plot([compass_x, compass_x - compass_size/2], 
           [compass_z, compass_z], 
           color='black', lw=1.5)
    ax.text(compass_x - compass_size/2 - 0.2, compass_z, 'W', 
           ha='right', va='center', fontsize=10, fontweight='bold')
    
    # Add a title with house info
    house_id = house_data.get('id', 'Unknown')
    num_rooms = len(house_data['rooms'])
    ax.set_title(f'Floor Plan - House {house_id} - {num_rooms} Rooms', 
                fontsize=16, fontweight='bold')
    
    # Add some dimensions to walls for scale
    scale_factor = 0.3048  # Meters to feet conversion
    
    # Find some longer walls to label
    long_walls = []
    for wall in all_walls:
        length = np.sqrt((wall[1][0]-wall[0][0])**2 + (wall[1][1]-wall[0][1])**2)
        if length > 2.0:  # Only label walls longer than 2 units
            long_walls.append((wall, length))
    
    # Sort by length and label the top few
    long_walls.sort(key=lambda x: x[1], reverse=True)
    for i, (wall, length) in enumerate(long_walls[:5]):  # Label top 5 longest walls
        # Convert to feet for display
        length_feet = length / scale_factor
        feet = int(length_feet)
        inches = int((length_feet - feet) * 12)
        
        # Calculate midpoint and perpendicular offset for dimension line
        mid_x = (wall[0][0] + wall[1][0]) / 2
        mid_z = (wall[0][1] + wall[1][1]) / 2
        
        # Direction vector of the wall
        wall_dx = wall[1][0] - wall[0][0]
        wall_dz = wall[1][1] - wall[0][1]
        wall_len = np.sqrt(wall_dx**2 + wall_dz**2)
        
        if wall_len > 0:
            # Normalize and get perpendicular vector
            wall_dx /= wall_len
            wall_dz /= wall_len
            perp_dx = -wall_dz
            perp_dz = wall_dx
            
            # Offset the dimension line from the wall
            offset = 0.3
            dim_mid_x = mid_x + perp_dx * offset
            dim_mid_z = mid_z + perp_dz * offset
            
            # Create dimension line
            dim_start_x = dim_mid_x - wall_dx * wall_len/2
            dim_start_z = dim_mid_z - wall_dz * wall_len/2
            dim_end_x = dim_mid_x + wall_dx * wall_len/2
            dim_end_z = dim_mid_z + wall_dz * wall_len/2
            
            # Draw dimension line
            ax.plot([dim_start_x, dim_end_x], [dim_start_z, dim_end_z], 
                   color='red', lw=1, linestyle='--')
            
            # Add dimension text
            text_x = dim_mid_x + perp_dx * 0.2
            text_z = dim_mid_z + perp_dz * 0.2
            
            # Determine text rotation to align with wall
            angle_deg = np.degrees(np.arctan2(wall_dz, wall_dx))
            if angle_deg > 90 or angle_deg < -90:
                angle_deg += 180  # Flip text for readability
                
            # Add dimension text with rotation
            ax.text(text_x, text_z, f"{feet}'{inches}\"", 
                   color='red', fontsize=8, fontweight='bold',
                   rotation=angle_deg, ha='center', va='center',
                   rotation_mode='anchor',
                   bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
    
    # Remove axes ticks for a cleaner look
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Add a scale bar
    scale_bar_length = 3.0  # 3 meters
    scale_bar_feet = int(scale_bar_length / scale_factor)
    
    # Position scale bar at bottom left
    scale_x = min([p[0] for wall in all_walls for p in wall]) + 1
    scale_z = min([p[1] for wall in all_walls for p in wall]) + 1
    
    # Draw scale bar
    ax.plot([scale_x, scale_x + scale_bar_length], 
           [scale_z, scale_z], 
           color='black', lw=2)
    
    # Add tick marks
    for i in range(4):
        tick_x = scale_x + i * scale_bar_length/3
        ax.plot([tick_x, tick_x], [scale_z, scale_z - 0.1], 
               color='black', lw=2)
    
    # Add scale text
    ax.text(scale_x + scale_bar_length/2, scale_z - 0.3, 
           f"Scale: {scale_bar_feet} feet", 
           ha='center', va='top', fontsize=10)
    
    # Adjust figure dimensions
    plt.tight_layout()
    if return_image:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
        buf.seek(0)
        img = Image.open(buf)
        plt.close(fig)  # Don't display when returning
        return img
    else:
        plt.savefig('floor_plan.png', dpi=300, bbox_inches='tight')
        plt.show()
        return fig

if __name__ == "__main__":   

    # If 'HOME' is not set, fallback to 'USERPROFILE' (for Windows)
    if 'HOME' not in os.environ:
        os.environ['HOME'] = os.environ.get('USERPROFILE', 'C:\\Users\\YourUsername')
        
    dataset = prior.load_dataset("procthor-10k")

    with open("output.json", "r") as f:
        data = json.load(f)

    scene_id = data.get("id", "")

    match = re.search(r"scene_(\d+)", scene_id)
    scene_number = int(match.group(1))
    # Usage with your dataset

    house = dataset["train"][scene_number]
    # print(house)
    plot_enhanced_floor_plan(house)
                         
