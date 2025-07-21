import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import time
import json
import os
from PIL import Image, ImageTk, ImageSequence, ImageDraw
import io
import math
import random

# Import your existing modules
from model_runner import HouseModelInference, fix_json_string, attempt_json_parse
from validator import ProcTHORValidator
from visualizer import plot_enhanced_floor_plan

# Configuration
MODEL_PATH = r"D:\CLASS NOTES\8th Sem\Project Exhibition 2\Testing_New\flan-t5-house-model-20250417-092950\checkpoint-868"
RAW_OUTPUT_PATH = "generated_house_raw.txt"
JSON_OUTPUT_PATH = r"D:\CLASS NOTES\8th Sem\Project Exhibition 2\Testing_New\output.json"
ATTEMPTED_FIX_PATH = "house_fixed.json.attempted_fix.txt"

# Modern color scheme
COLORS = {
    "primary": "#4361EE",     # Blue
    "secondary": "#3F37C9",   # Dark Blue
    "accent": "#4CC9F0",      # Light Blue
    "success": "#4CAF50",     # Green
    "warning": "#F77F00",     # Orange
    "danger": "#F72585",      # Pink
    "light": "#F8F9FA",       # Light Grey
    "dark": "#212529",        # Dark Grey
    "background": "#FFFFFF",  # White
    "card": "#F0F7FF",        # Very Light Blue
}

class ModernTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # Create a toplevel window
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        frame = tk.Frame(self.tooltip, bg=COLORS["dark"], bd=1)
        frame.pack(fill="both", expand=True)
        
        label = tk.Label(frame, text=self.text, justify="left", 
                         bg=COLORS["dark"], fg=COLORS["light"],
                         padx=10, pady=5, wraplength=250,
                         font=("Arial", 9))
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class AnimatedButton(tk.Button):
    def __init__(self, master, **kwargs):
        self.hover_color = kwargs.pop('hover_color', COLORS["secondary"])
        self.normal_color = kwargs.pop('bg', COLORS["primary"])
        self.active_color = kwargs.pop('active_color', COLORS["accent"])
        
        # Store original colors
        kwargs['bg'] = self.normal_color
        
        super().__init__(master, **kwargs)
        
        # Bind events
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def on_hover(self, event):
        self.config(bg=self.hover_color)
    
    def on_leave(self, event):
        self.config(bg=self.normal_color)
    
    def on_press(self, event):
        self.config(bg=self.active_color)
    
    def on_release(self, event):
        self.config(bg=self.hover_color)

class ModernFrame(tk.Frame):
    def __init__(self, master, **kwargs):
        self.corner_radius = kwargs.pop('corner_radius', 0)
        self.border_color = kwargs.pop('border_color', None)
        self.border_width = kwargs.pop('border_width', 0)
        
        super().__init__(master, **kwargs)
        
        # Create a canvas to draw the rounded rectangle
        self.canvas = tk.Canvas(self, highlightthickness=0, 
                              bg=self['bg'], bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas
        self.inner_frame = tk.Frame(self.canvas, bg=self['bg'])
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.inner_frame, 
                                                    anchor="nw")

    def pack(self, **kwargs):
        super().pack(**kwargs)
        self.update_idletasks()
        self.update_canvas()
        self.bind("<Configure>", self.on_resize)
    
    def grid(self, **kwargs):
        super().grid(**kwargs)
        self.update_idletasks()
        self.update_canvas()
        self.bind("<Configure>", self.on_resize)
    
    def place(self, **kwargs):
        super().place(**kwargs)
        self.update_idletasks()
        self.update_canvas()
        self.bind("<Configure>", self.on_resize)
    
    def update_canvas(self):
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width > 0 and height > 0:
            # Update the size of the inner frame and canvas frame
            self.canvas.config(width=width, height=height)
            self.canvas.coords(self.canvas_frame, 0, 0)
            self.canvas.itemconfig(self.canvas_frame, width=width, height=height)
            
            # Draw rounded rectangle if needed
            if self.corner_radius > 0 or self.border_width > 0:
                self.canvas.delete("rounded_rect")
                
                # Calculate coordinates
                x0, y0 = 0, 0
                x1, y1 = width - 1, height - 1
                radius = min(self.corner_radius, width//2, height//2)
                
                # Create rounded rectangle path
                self.canvas.create_rounded_rectangle(
                    x0, y0, x1, y1, radius=radius, 
                    fill=self['bg'], 
                    outline=self.border_color if self.border_color else "",
                    width=self.border_width,
                    tags="rounded_rect"
                )
                self.canvas.tag_lower("rounded_rect")
    
    def on_resize(self, event):
        self.update_canvas()

# Add rounded rectangle method to Canvas
def _create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
    points = [
        x1 + radius, y1,  # Top left after curve
        x2 - radius, y1,  # Top right before curve
        x2, y1,           # Top right corner point
        x2, y1 + radius,  # Top right after curve
        x2, y2 - radius,  # Bottom right before curve
        x2, y2,           # Bottom right corner point
        x2 - radius, y2,  # Bottom right after curve
        x1 + radius, y2,  # Bottom left before curve
        x1, y2,           # Bottom left corner point
        x1, y2 - radius,  # Bottom left after curve
        x1, y1 + radius,  # Top left before curve
        x1, y1            # Top left corner point
    ]
    
    # Create the polygon with smooth corners
    return self.create_polygon(points, **kwargs, smooth=True)

# Add method to Canvas class
tk.Canvas.create_rounded_rectangle = _create_rounded_rectangle

class ParticleEffect:
    def __init__(self, canvas, x, y, color=None, size=5, lifespan=30, speed=2, quantity=20):
        self.canvas = canvas
        self.particles = []
        self.colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"], 
                      COLORS["success"], COLORS["warning"]] if color is None else [color]
        
        # Create particles
        for _ in range(quantity):
            angle = random.uniform(0, math.pi * 2)
            speed_factor = random.uniform(0.5, speed)
            dx = math.cos(angle) * speed_factor
            dy = math.sin(angle) * speed_factor
            particle_size = random.uniform(size * 0.5, size * 1.5)
            color = random.choice(self.colors)
            
            particle = {
                "x": x,
                "y": y,
                "dx": dx,
                "dy": dy,
                "size": particle_size,
                "color": color,  # Store base color
                "life": lifespan,
                "max_life": lifespan,
                "id": None
            }
            self.particles.append(particle)
        
        self.animate()

    def animate(self):
        if not self.particles:
            return
        
        for particle in self.particles[:]:
            # Move particle
            particle["x"] += particle["dx"]
            particle["y"] += particle["dy"]
            particle["life"] -= 1
            
            # Calculate size factor based on remaining life
            size_factor = particle["life"] / particle["max_life"]
            
            # Delete old shape
            if particle["id"] is not None:
                self.canvas.delete(particle["id"])
            
            if particle["life"] > 0:
                # Use base color without alpha
                color = particle["color"]
                
                # Calculate final size
                size = particle["size"] * size_factor
                
                # Create particle with solid color
                particle["id"] = self.canvas.create_oval(
                    particle["x"] - size,
                    particle["y"] - size,
                    particle["x"] + size,
                    particle["y"] + size,
                    fill=color,
                    outline=""
                )
            else:
                self.particles.remove(particle)
        
        if self.particles:
            self.canvas.after(30, self.animate)

class HouseGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        
        # Variables
        self.processing = False
        self.generated_image = None
        self.animation_id = None
        
        # Image navigation variables
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.dragging = False
        self.original_image = None
        
        # Create GUI elements
        self.create_widgets()
        
        # Create loading animation
        self.create_loading_animation()
        
        # Bind theme toggling
        self.root.bind("<Control-t>", self.toggle_theme)
        
        # Set light theme initially
        self.is_dark_theme = False
    
    def setup_window(self):
        self.root.title("House Plan Creator")
        self.root.geometry("1000x800")
        self.root.configure(bg=COLORS["background"])
        
        # Center window on screen
        window_width = 1000
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Set app icon if available
        try:
            self.root.iconbitmap("house_icon.ico")
        except:
            pass
    
    def create_widgets(self):
        # Main container with some padding
        main_container = tk.Frame(self.root, bg=COLORS["background"], padx=20, pady=20)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Header with title and logo
        header_frame = ModernFrame(main_container, bg=COLORS["card"], 
                                  corner_radius=15, border_width=1, 
                                  border_color=COLORS["primary"])
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Use the inner frame
        header = header_frame.inner_frame
        
        # Create a canvas for the header with gradients
        header_canvas = tk.Canvas(header, bg=COLORS["card"], highlightthickness=0, height=80)
        header_canvas.pack(fill=tk.X)
        
        # Create gradient background
        self.draw_gradient(header_canvas, 
                          start_color=COLORS["primary"], 
                          end_color=COLORS["card"],
                          width=1000, height=80)
        
        # Title
        title_text = header_canvas.create_text(500, 40, text="🏠 House Plan Creator", 
                                              font=("Arial", 24, "bold"), 
                                              fill=COLORS["light"])
        
        # Add decorative house icons to the title
        for i in range(5):
            size = random.randint(15, 25)
            x = 100 + i * 200
            y = random.randint(15, 65)
            self.draw_house_icon(header_canvas, x, y, size, COLORS["light"], alpha=0.3)
        
        # Create section for the main content
        content_frame = tk.Frame(main_container, bg=COLORS["background"])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Input area
        left_panel = ModernFrame(content_frame, bg=COLORS["card"], 
                               corner_radius=10, border_width=1,
                               border_color=COLORS["primary"])
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), expand=False)
        
        # Use the inner frame
        input_area = left_panel.inner_frame
        
        # Title for input area with icon
        input_title_frame = tk.Frame(input_area, bg=COLORS["card"])
        input_title_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        input_icon = tk.Label(input_title_frame, text="✏️", 
                            font=("Arial", 14), bg=COLORS["card"])
        input_icon.pack(side=tk.LEFT)
        
        input_title = tk.Label(input_title_frame, text="Design Your Dream House", 
                             font=("Arial", 14, "bold"), 
                             fg=COLORS["dark"], bg=COLORS["card"])
        input_title.pack(side=tk.LEFT, padx=5)
        
        # Separator
        separator = ttk.Separator(input_area, orient="horizontal")
        separator.pack(fill=tk.X, padx=15, pady=5)
        
        # Instructions
        instructions = tk.Label(input_area, 
                              text="Describe your dream house in detail.\nBe specific about rooms, layout, and features.", 
                              font=("Arial", 10), 
                              fg=COLORS["dark"], bg=COLORS["card"],
                              justify="left")
        instructions.pack(fill=tk.X, padx=15, pady=5, anchor="w")
        
        # Input text area with improved styling
        input_frame = tk.Frame(input_area, bg=COLORS["card"], padx=15, pady=5)
        input_frame.pack(fill=tk.X)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, 
                                                  height=12,
                                                  width=30,
                                                  font=("Arial", 11),
                                                  bg=COLORS["light"],
                                                  fg=COLORS["dark"],
                                                  padx=10,
                                                  pady=10,
                                                  wrap=tk.WORD,
                                                  bd=1,
                                                  relief=tk.SOLID)
        self.input_text.pack(fill=tk.X)
        
        # Add placeholder text
        placeholder = "Example: A modern two-bedroom house with an open kitchen connected to the living room. Include a master bathroom, guest bathroom, and a home office. The house should have large windows for natural light."
        self.input_text.insert("1.0", placeholder)
        self.input_text.bind("<FocusIn>", lambda e: self.on_input_focus_in(placeholder))
        self.input_text.bind("<FocusOut>", lambda e: self.on_input_focus_out(placeholder))
        
        # Example button
        examples_frame = tk.Frame(input_area, bg=COLORS["card"], padx=15, pady=5)
        examples_frame.pack(fill=tk.X)
        
        examples_btn = AnimatedButton(examples_frame, 
                                    text="Load Examples",
                                    command=self.show_examples,
                                    bg=COLORS["secondary"],
                                    hover_color=COLORS["primary"],
                                    fg=COLORS["light"],
                                    font=("Arial", 10),
                                    bd=0,
                                    padx=10,
                                    pady=5,
                                    relief=tk.RAISED)
        examples_btn.pack(side=tk.LEFT)
        
        ModernTooltip(examples_btn, "Click to load example house descriptions")
        
        # Clear button
        clear_btn = AnimatedButton(examples_frame, 
                                 text="Clear",
                                 command=lambda: self.input_text.delete("1.0", tk.END),
                                 bg=COLORS["warning"],
                                 hover_color="#FF9800",
                                 fg=COLORS["light"],
                                 font=("Arial", 10),
                                 bd=0,
                                 padx=10,
                                 pady=5,
                                 relief=tk.RAISED)
        clear_btn.pack(side=tk.RIGHT)
        
        ModernTooltip(clear_btn, "Clear the input text")
        
        # Generate button
        btn_frame = tk.Frame(input_area, bg=COLORS["card"], padx=15, pady=15)
        btn_frame.pack(fill=tk.X)
        
        self.generate_button = AnimatedButton(btn_frame, 
                                            text="✨ Generate House Plan",
                                            command=self.start_generation,
                                            bg=COLORS["primary"],
                                            hover_color=COLORS["secondary"],
                                            active_color=COLORS["accent"],
                                            fg=COLORS["light"],
                                            font=("Arial", 12, "bold"),
                                            bd=0,
                                            padx=10,
                                            pady=10,
                                            relief=tk.RAISED)
        self.generate_button.pack(fill=tk.X)
        
        # Status information
        status_frame = tk.Frame(input_area, bg=COLORS["card"], padx=15, pady=5)
        status_frame.pack(fill=tk.X)
        
        self.status_label = tk.Label(status_frame, 
                                   text="Ready to generate your house plan",
                                   font=("Arial", 9),
                                   fg=COLORS["dark"], 
                                   bg=COLORS["card"],
                                   anchor="w")
        self.status_label.pack(fill=tk.X)
        
        # Style the progress bar
        style = ttk.Style()
        style.theme_use('default')
        style.configure("color.Horizontal.TProgressbar", 
                       background=COLORS["primary"],
                       troughcolor=COLORS["light"],
                       thickness=6)
        
        self.progress_bar = ttk.Progressbar(input_area, 
                                          style="color.Horizontal.TProgressbar",
                                          mode="indeterminate")
        
        # Theme toggle button
        theme_btn = AnimatedButton(input_area, 
                                 text="🌙 Toggle Theme",
                                 command=self.toggle_theme,
                                 bg=COLORS["secondary"],
                                 hover_color=COLORS["primary"],
                                 fg=COLORS["light"],
                                 font=("Arial", 10),
                                 bd=0,
                                 padx=10,
                                 pady=5,
                                 relief=tk.RAISED)
        theme_btn.pack(side=tk.BOTTOM, padx=15, pady=15, fill=tk.X)
        
        ModernTooltip(theme_btn, "Switch between light and dark theme (Ctrl+T)")
        
        # Create right panel for display
        right_panel = ModernFrame(content_frame, bg=COLORS["card"], 
                                corner_radius=10, border_width=1,
                                border_color=COLORS["primary"])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Use the inner frame
        display_area = right_panel.inner_frame
        
        # Title for display area with icon
        display_title_frame = tk.Frame(display_area, bg=COLORS["card"])
        display_title_frame.pack(fill=tk.X, padx=15, pady=(15, 5))
        
        display_icon = tk.Label(display_title_frame, text="🏡", 
                              font=("Arial", 14), bg=COLORS["card"])
        display_icon.pack(side=tk.LEFT)
        
        display_title = tk.Label(display_title_frame, text="House Plan Visualization", 
                               font=("Arial", 14, "bold"), 
                               fg=COLORS["dark"], bg=COLORS["card"])
        display_title.pack(side=tk.LEFT, padx=5)
        
        # Separator
        separator2 = ttk.Separator(display_area, orient="horizontal")
        separator2.pack(fill=tk.X, padx=15, pady=5)
        
        # Control panel
        control_panel = tk.Frame(display_area, bg=COLORS["card"], padx=15, pady=5)
        control_panel.pack(fill=tk.X)
        
        # Zoom controls
        zoom_frame = tk.Frame(control_panel, bg=COLORS["card"])
        zoom_frame.pack(side=tk.LEFT)
        
        zoom_out_btn = AnimatedButton(zoom_frame, 
                                    text="🔍-",
                                    command=self.zoom_out,
                                    bg=COLORS["secondary"],
                                    hover_color=COLORS["primary"],
                                    fg=COLORS["light"],
                                    font=("Arial", 10, "bold"),
                                    width=3,
                                    bd=0,
                                    padx=5,
                                    pady=2)
        zoom_out_btn.pack(side=tk.LEFT, padx=2)
        
        self.zoom_label = tk.Label(zoom_frame, 
                                 text="100%",
                                 width=5,
                                 font=("Arial", 10),
                                 bg=COLORS["card"])
        self.zoom_label.pack(side=tk.LEFT, padx=2)
        
        zoom_in_btn = AnimatedButton(zoom_frame, 
                                   text="🔍+",
                                   command=self.zoom_in,
                                   bg=COLORS["secondary"],
                                   hover_color=COLORS["primary"],
                                   fg=COLORS["light"],
                                   font=("Arial", 10, "bold"),
                                   width=3,
                                   bd=0,
                                   padx=5,
                                   pady=2)
        zoom_in_btn.pack(side=tk.LEFT, padx=2)
        
        reset_btn = AnimatedButton(zoom_frame, 
                                 text="↺ Reset",
                                 command=self.reset_view,
                                 bg=COLORS["secondary"],
                                 hover_color=COLORS["primary"],
                                 fg=COLORS["light"],
                                 font=("Arial", 10),
                                 bd=0,
                                 padx=5,
                                 pady=2)
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Navigation controls
        nav_frame = tk.Frame(control_panel, bg=COLORS["card"])
        nav_frame.pack(side=tk.RIGHT)
        
        # Create a 3x3 grid for navigation buttons
        grid_frame = tk.Frame(nav_frame, bg=COLORS["card"])
        grid_frame.pack()
        
        # Top row
        AnimatedButton(grid_frame, text="↖", command=lambda: self.move_view(-20, -20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=0, column=0)
        
        AnimatedButton(grid_frame, text="↑", command=lambda: self.move_view(0, -20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=0, column=1)
        
        AnimatedButton(grid_frame, text="↗", command=lambda: self.move_view(20, -20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=0, column=2)
        
        # Middle row
        AnimatedButton(grid_frame, text="←", command=lambda: self.move_view(-20, 0),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=1, column=0)
        
        # Center button for reset view
        AnimatedButton(grid_frame, text="⦿", command=self.reset_view,
                     bg=COLORS["accent"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=1, column=1)
        
        AnimatedButton(grid_frame, text="→", command=lambda: self.move_view(20, 0),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=1, column=2)
        
        # Bottom row
        AnimatedButton(grid_frame, text="↙", command=lambda: self.move_view(-20, 20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=2, column=0)
        
        AnimatedButton(grid_frame, text="↓", command=lambda: self.move_view(0, 20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=2, column=1)
        
        AnimatedButton(grid_frame, text="↘", command=lambda: self.move_view(20, 20),
                     bg=COLORS["secondary"], hover_color=COLORS["primary"],
                     fg=COLORS["light"], width=2, height=1, bd=0).grid(row=2, column=2)
        
        # Export button
        export_btn = AnimatedButton(control_panel, 
                                  text="💾 Export",
                                  command=self.export_image,
                                  bg=COLORS["success"],
                                  hover_color="#388E3C",
                                  fg=COLORS["light"],
                                  font=("Arial", 10),
                                  bd=0,
                                  padx=10,
                                  pady=2)
        export_btn.pack(side=tk.RIGHT, padx=5)
        
        ModernTooltip(export_btn, "Save the house plan as an image")
        
        # Canvas for displaying the house plan
        canvas_frame = tk.Frame(display_area, bg=COLORS["light"], 
                              padx=10, pady=10)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, 
                              bg=COLORS["light"],
                              bd=0,
                              highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Add welcome message and graphics to canvas
        self.display_welcome()
        
        # Bind mouse events for panning
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)
        self.canvas.bind("<ButtonRelease-1>", self.end_pan)
        
        # Bind mouse wheel for zooming
        self.canvas.bind("<MouseWheel>", self.mouse_zoom)  # For Windows
        self.canvas.bind("<Button-4>", lambda e: self.mouse_zoom(e, 1))  # For Linux/Unix
        self.canvas.bind("<Button-5>", lambda e: self.mouse_zoom(e, -1))  # For Linux/Unix
    
    def draw_gradient(self, canvas, start_color, end_color, width, height):
        """Draw a horizontal gradient"""
        for i in range(height):
            # Calculate color for this line
            ratio = i / height
            r1, g1, b1 = self.hex_to_rgb(start_color)
            r2, g2, b2 = self.hex_to_rgb(end_color)
            
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_line(0, i, width, i, fill=color)
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def draw_house_icon(self, canvas, x, y, size, color, alpha=1.0):
        """Draw a simple house icon"""
        # Remove alpha channel from color
        base_color = color  # Use original color without alpha
        
        # Draw house
        roof_height = size * 0.4
        house_width = size
        house_height = size * 0.6
        
        # Roof
        canvas.create_polygon(
            x - house_width/2, y + roof_height,  # Bottom left
            x, y,                               # Top
            x + house_width/2, y + roof_height,  # Bottom right
            fill=base_color, outline=""
        )
        
        # House body
        canvas.create_rectangle(
            x - house_width/2, y + roof_height,
            x + house_width/2, y + roof_height + house_height,
            fill=base_color, outline=""
        )
        
        # Door
        door_width = house_width * 0.3
        door_height = house_height * 0.6
        door_y = y + roof_height + house_height - door_height
        
        canvas.create_rectangle(
            x - door_width/2, door_y,
            x + door_width/2, y + roof_height + house_height,
            fill=base_color, outline=""
        )
        
        # Windows
        window_size = house_width * 0.15
        window_y = y + roof_height + house_height * 0.2
        window_x_left = x - house_width * 0.25
        window_x_right = x + house_width * 0.25
        
        canvas.create_rectangle(
            window_x_left - window_size/2, window_y - window_size/2,
            window_x_left + window_size/2, window_y + window_size/2,
            fill=base_color, outline=""
        )
        
        canvas.create_rectangle(
            window_x_right - window_size/2, window_y - window_size/2,
            window_x_right + window_size/2, window_y + window_size/2,
            fill=base_color, outline=""
        )
    
    def display_welcome(self):
        """Display welcome screen with animation"""
        self.canvas.delete("all")
        
        # Get canvas dimensions
        width = self.canvas.winfo_width() or 600
        height = self.canvas.winfo_height() or 400
        
        # Create soft background
        self.draw_gradient(self.canvas, COLORS["card"], COLORS["light"], width, height)
        
        # Draw house icons
        for i in range(5):
            x = width * (0.1 + i * 0.2)
            y = height * 0.2
            size = 30 + i * 5
            self.draw_house_icon(self.canvas, x, y, size, COLORS["primary"], alpha=0.3)
        
        # Welcome text
        welcome_text = "Welcome to House Plan Creator"
        self.canvas.create_text(
            width // 2, height * 0.4,
            text=welcome_text,
            font=("Arial", 18, "bold"),
            fill=COLORS["primary"]
        )
        
        # Instructions
        instructions = "Enter your house description in the left panel and click Generate"
        self.canvas.create_text(
            width // 2, height * 0.5,
            text=instructions,
            font=("Arial", 12),
            fill=COLORS["dark"]
        )
        
        # Add decorative elements
        self.canvas.create_oval(
            width * 0.2, height * 0.65,
            width * 0.8, height * 0.85,
            outline=COLORS["accent"],
            width=2,
            dash=(5, 5)
        )
        
        # Animated hint
        hint_text = "Your house visualization will appear here"
        self.canvas.create_text(
            width // 2, height * 0.75,
            text=hint_text,
            font=("Arial", 11, "italic"),
            fill=COLORS["secondary"],
            tags="hint_text"
        )
        
        # Create blinking animation
        self.animate_hint()
    
    def animate_hint(self):
        """Create blinking animation for hint text"""
        if hasattr(self, "hint_visible") and self.hint_visible:
            self.canvas.itemconfig("hint_text", fill=COLORS["secondary"])
            self.hint_visible = False
        else:
            self.canvas.itemconfig("hint_text", fill=COLORS["primary"])
            self.hint_visible = True
        
        # Schedule next animation frame
        self.animation_id = self.root.after(1000, self.animate_hint)
    
    def cancel_hint_animation(self):
        """Cancel the hint animation"""
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
    
    def create_loading_animation(self):
        """Create frames for loading animation"""
        # Try to load animated GIF if available
        try:
            self.loading_gif = Image.open("loading.gif")
            self.loading_frames = [ImageTk.PhotoImage(frame) for frame in ImageSequence.Iterator(self.loading_gif)]
        except Exception:
            # Create custom animation frames
            self.loading_frames = []
            size = 100
            num_frames = 12
            
            for i in range(num_frames):
                # Create frame image
                img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
                draw = ImageDraw.Draw(img)
                
                # Draw spinning circle
                angle = i * (360 / num_frames)
                for j in range(num_frames):
                    # Each dot has a different position and opacity
                    dot_angle = (angle + j * (360 / num_frames)) % 360
                    distance = size * 0.35  # Distance from center
                    
                    x = size/2 + distance * math.cos(math.radians(dot_angle))
                    y = size/2 + distance * math.sin(math.radians(dot_angle))
                    
                    # Size of dot decreases with distance from the current angle
                    angle_diff = min((dot_angle - angle) % 360, (angle - dot_angle) % 360)
                    dot_size = max(3, 10 - angle_diff / 36)
                    
                    # Color also changes with position
                    color_idx = j % len([COLORS["primary"], COLORS["secondary"], COLORS["accent"]])
                    colors = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]
                    dot_color = colors[color_idx]
                    
                    # Draw the dot
                    draw.ellipse(
                        (x-dot_size/2, y-dot_size/2, x+dot_size/2, y+dot_size/2),
                        fill=dot_color
                    )
                
                # Add frame to animation
                self.loading_frames.append(ImageTk.PhotoImage(img))
    
    def show_loading_animation(self):
        """Display the loading animation"""
        if not self.processing:
            return
        
        # Clear canvas
        self.canvas.delete("loading")
        
        # Get canvas dimensions
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Display current frame
        frame_idx = int(time.time() * 10) % len(self.loading_frames)
        self.canvas.create_image(
            width // 2, height // 2,
            image=self.loading_frames[frame_idx],
            tags="loading"
        )
        
        # Add loading text
        self.canvas.create_text(
            width // 2, height // 2 + 70,
            text="Generating your house plan...",
            font=("Arial", 12, "bold"),
            fill=COLORS["primary"],
            tags="loading"
        )
        
        # Add progress message based on current status
        self.canvas.create_text(
            width // 2, height // 2 + 100,
            text=self.status_label.cget("text"),
            font=("Arial", 10),
            fill=COLORS["secondary"],
            tags="loading"
        )
        
        # Schedule next frame
        self.root.after(100, self.show_loading_animation)
    
    def on_input_focus_in(self, placeholder):
        """Handle input field focus in event"""
        if self.input_text.get("1.0", "end-1c") == placeholder:
            self.input_text.delete("1.0", tk.END)
            self.input_text.config(fg=COLORS["dark"])
    
    def on_input_focus_out(self, placeholder):
        """Handle input field focus out event"""
        if not self.input_text.get("1.0", "end-1c").strip():
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", placeholder)
            self.input_text.config(fg="gray")
    
    def show_examples(self):
        """Show example house descriptions"""
        examples = [
            "A modern two-story house with 3 bedrooms, 2 bathrooms, a spacious kitchen with an island, an open concept living room, and a home office. Include a two-car garage and a backyard patio.",
            
            "A cozy single-story cottage with 2 bedrooms, 1 bathroom, a combined kitchen and dining area, a living room with a fireplace, and a small reading nook near a bay window. Add a covered front porch.",
            
            "A luxury villa with 4 bedrooms including a master suite, 3.5 bathrooms, a gourmet kitchen, formal dining room, large living room, game room, home theater, and a home gym. Include a three-car garage and an outdoor swimming pool."
        ]
        
        # Create example selection popup
        popup = tk.Toplevel(self.root)
        popup.title("Example Descriptions")
        popup.geometry("500x400")
        popup.configure(bg=COLORS["card"])
        
        # Make it modal
        popup.transient(self.root)
        popup.grab_set()
        
        # Add header
        header = tk.Label(popup, 
                        text="Select an Example Description", 
                        font=("Arial", 14, "bold"),
                        bg=COLORS["card"],
                        fg=COLORS["dark"])
        header.pack(pady=15)
        
        # Frame for examples
        examples_frame = tk.Frame(popup, bg=COLORS["card"], padx=20, pady=5)
        examples_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add example options
        for i, example in enumerate(examples):
            # Create a frame for each example
            ex_frame = ModernFrame(examples_frame, 
                                 bg=COLORS["light"],
                                 corner_radius=10,
                                 border_width=1,
                                 border_color=COLORS["primary"])
            ex_frame.pack(fill=tk.X, pady=10, padx=5)
            
            # Title
            title = tk.Label(ex_frame.inner_frame, 
                           text=f"Example {i+1}",
                           font=("Arial", 12, "bold"),
                           bg=COLORS["light"],
                           fg=COLORS["primary"])
            title.pack(anchor=tk.W, padx=15, pady=(10, 5))
            
            # Example text
            short_example = example[:100] + "..." if len(example) > 100 else example
            text = tk.Label(ex_frame.inner_frame, 
                          text=short_example,
                          font=("Arial", 10),
                          bg=COLORS["light"],
                          fg=COLORS["dark"],
                          wraplength=400,
                          justify=tk.LEFT)
            text.pack(fill=tk.X, padx=15, pady=5)
            
            # Use button
            use_btn = AnimatedButton(ex_frame.inner_frame, 
                                   text="Use This Example",
                                   command=lambda e=example: self.use_example(e, popup),
                                   bg=COLORS["secondary"],
                                   hover_color=COLORS["primary"],
                                   fg=COLORS["light"],
                                   font=("Arial", 10),
                                   bd=0,
                                   padx=10,
                                   pady=5)
            use_btn.pack(anchor=tk.E, padx=15, pady=10)
        
        # Cancel button
        cancel_btn = AnimatedButton(popup, 
                                  text="Cancel",
                                  command=popup.destroy,
                                  bg=COLORS["warning"],
                                  hover_color="#FF9800",
                                  fg=COLORS["light"],
                                  font=("Arial", 11),
                                  bd=0,
                                  padx=10,
                                  pady=5)
        cancel_btn.pack(pady=15)
    
    def use_example(self, example, popup):
        """Use the selected example"""
        self.input_text.delete("1.0", tk.END)
        self.input_text.insert("1.0", example)
        self.input_text.config(fg=COLORS["dark"])
        popup.destroy()
        
        # Show a fun particle effect at the input
        x = self.input_text.winfo_rootx() + self.input_text.winfo_width() // 2
        y = self.input_text.winfo_rooty() + self.input_text.winfo_height() // 2
        ParticleEffect(self.canvas, x, y, color=COLORS["accent"], quantity=30)
    
    def start_generation(self):
        """Begin house plan generation"""
        if self.processing:
            return
        
        description = self.input_text.get("1.0", tk.END).strip()
        placeholder = "Example: A modern two-bedroom house with an open kitchen connected to the living room. Include a master bathroom, guest bathroom, and a home office. The house should have large windows for natural light."
        
        if not description or description == placeholder:
            messagebox.showinfo("Input Required", "Please enter a house description.")
            return
        
        # Cancel any hint animation
        self.cancel_hint_animation()
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Start processing
        self.processing = True
        self.generate_button.config(state=tk.DISABLED, text="Generating...")
        self.status_label.config(text="Preparing to generate house plan...")
        
        # Show progress bar
        self.progress_bar.pack(fill=tk.X, padx=15, pady=10)
        self.progress_bar.start(10)
        
        # Start loading animation
        self.show_loading_animation()
        
        # Add particle effect
        x = self.generate_button.winfo_rootx() + self.generate_button.winfo_width() // 2
        y = self.generate_button.winfo_rooty() + self.generate_button.winfo_height() // 2
        ParticleEffect(self.canvas, x, y, color=COLORS["success"], quantity=40)
        
        # Start generation in a separate thread
        thread = threading.Thread(target=self.run_pipeline, args=(description,))
        thread.daemon = True
        thread.start()
    
    def run_pipeline(self, description):
        """Run the house generation pipeline"""
        try:
            # Step 1: Run model
            self.update_status("Running the model to generate your house...")
            time.sleep(0.5)  # Ensure UI updates
            
            model = HouseModelInference(model_path=MODEL_PATH)
            raw_output = model.generate_house_text(description)

            if not raw_output:
                self.update_status("[ERROR] Model output was empty.")
                self.finish_processing(success=False)
                return

            # Step 2: Try to fix and parse JSON
            self.update_status("Processing model output...")
            time.sleep(0.3)  # Ensure UI updates
            
            fixed_json_text = fix_json_string(raw_output)
            json_data = attempt_json_parse(fixed_json_text)

            if json_data:
                self.update_status("JSON parsed successfully!")
            else:
                self.update_status("Could not parse JSON. Applying fixes...")
                with open(ATTEMPTED_FIX_PATH, 'w') as f:
                    f.write(fixed_json_text)

            # Step 3: Validate
            self.update_status("Validating house structure...")
            time.sleep(0.3)  # Ensure UI updates
            
            validator = ProcTHORValidator(template_file="procthor_10k.jsonl")
            validated_json = validator.validate(json_data if json_data else fixed_json_text)

            # Step 4: Save
            with open(JSON_OUTPUT_PATH, 'w') as f:
                json.dump(validated_json, f, indent=2)
                self.update_status(f"Validated JSON saved successfully!")

            # Step 5: Visualize
            self.update_status("Creating your house visualization...")
            time.sleep(0.5)  # Ensure UI updates
            
            image_data = plot_enhanced_floor_plan(validated_json, return_image=True)
            
            # Store original image and reset view parameters
            self.original_image = image_data
            self.reset_view_params()
            
            # Display the image
            self.display_image(image_data)
            
            self.update_status("House plan generated successfully!")
            self.finish_processing(success=True)
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.finish_processing(success=False)
    
    def update_status(self, message):
        """Update status message (thread-safe)"""
        self.root.after(0, lambda: self.status_label.config(text=message))
    
    def display_image(self, image_data):
        """Display the generated house plan image (thread-safe)"""
        def _display():
            # Clear canvas
            self.canvas.delete("all")
            
            # Convert image data to PhotoImage
            if isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            else:
                img = image_data
                
            # If this is the first display, store as original
            if self.original_image is None:
                self.original_image = img
                
            # Apply zoom and pan
            self.update_displayed_image()
            
            # Add particle effect to celebrate success
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            # Create particles at various positions
            for _ in range(5):
                x = random.randint(width//4, width*3//4)
                y = random.randint(height//4, height*3//4)
                ParticleEffect(self.canvas, x, y, quantity=20)
        
        self.root.after(0, _display)
    
    def update_displayed_image(self):
        """Update the displayed image with current zoom and pan settings"""
        if self.original_image is None:
            return
            
        # Get a copy of the original image
        img = self.original_image.copy()
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate dimensions based on zoom level
        img_width, img_height = img.size
        new_width = int(img_width * self.zoom_level)
        new_height = int(img_height * self.zoom_level)
        
        # Resize the image
        if new_width > 0 and new_height > 0:  # Ensure dimensions are positive
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Keep a reference to prevent garbage collection
        self.generated_image = ImageTk.PhotoImage(img)
        
        # Calculate center position with panning offset
        x = (canvas_width - new_width) // 2 + self.pan_x
        y = (canvas_height - new_height) // 2 + self.pan_y
        
        # Display image
        self.canvas.delete("house_image")
        self.canvas.create_image(x + new_width//2, y + new_height//2, 
                                image=self.generated_image, tags="house_image")
        
        # Update zoom level indicator
        self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")
    
    def finish_processing(self, success):
        """Complete the processing and update UI (thread-safe)"""
        def _finish():
            self.processing = False
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.generate_button.config(state=tk.NORMAL, text="✨ Generate House Plan")
            
            if not success and not self.generated_image:
                # Display error message on canvas
                self.canvas.delete("all")
                
                # Create a nicer error display
                width = self.canvas.winfo_width()
                height = self.canvas.winfo_height()
                
                # Background
                self.draw_gradient(self.canvas, COLORS["light"], COLORS["card"], width, height)
                
                # Error icon
                self.canvas.create_oval(
                    width/2 - 40, height/2 - 80,
                    width/2 + 40, height/2,
                    fill=COLORS["warning"],
                    outline=""
                )
                
                # Exclamation mark
                self.canvas.create_text(
                    width/2, height/2 - 55,
                    text="!",
                    font=("Arial", 40, "bold"),
                    fill=COLORS["light"]
                )
                
                # Error message
                self.canvas.create_text(
                    width/2, height/2 + 20,
                    text="Generation failed",
                    font=("Arial", 16, "bold"),
                    fill=COLORS["danger"]
                )
                
                # Suggestion
                self.canvas.create_text(
                    width/2, height/2 + 60,
                    text="Please try again with a different description.",
                    font=("Arial", 12),
                    fill=COLORS["dark"],
                    width=400
                )
        
        self.root.after(0, _finish)
    
    # Navigation and zoom functions
    def zoom_in(self):
        """Increase zoom level"""
        self.zoom_level *= 1.2
        # Add limit to prevent excessive zoom
        if self.zoom_level > 5.0:
            self.zoom_level = 5.0
        self.update_displayed_image()
    
    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom_level /= 1.2
        # Prevent excessive zooming out
        if self.zoom_level < 0.1:
            self.zoom_level = 0.1
        self.update_displayed_image()
    
    def mouse_zoom(self, event, direction=None):
        """Handle mouse wheel zoom events"""
        # For Windows mouse wheel
        if direction is None:
            # Get the direction from the event delta
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        # For Linux/Unix mouse wheel
        else:
            if direction > 0:
                self.zoom_in()
            else:
                self.zoom_out()
    
    def move_view(self, dx, dy):
        """Pan the view"""
        self.pan_x += dx
        self.pan_y += dy
        self.update_displayed_image()
    
    def reset_view(self):
        """Reset to default view"""
        self.reset_view_params()
        self.update_displayed_image()
    
    def reset_view_params(self):
        """Reset zoom and pan parameters"""
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
    
    def start_pan(self, event):
        """Begin panning with mouse"""
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def do_pan(self, event):
        """Continue panning with mouse"""
        if not self.dragging:
            return
            
        # Calculate the difference
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # Update starting point
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        # Move the view
        self.pan_x += dx
        self.pan_y += dy
        
        # Redraw the image
        self.update_displayed_image()
    
    def end_pan(self, event):
        """End panning with mouse"""
        self.dragging = False
    
    def export_image(self):
        """Export the current image to a file"""
        if self.original_image is None:
            messagebox.showinfo("No Image", "There is no house plan to export.")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"), 
                    ("JPEG files", "*.jpg"), 
                    ("All files", "*.*")
                ],
                title="Export House Plan"
            )
            
            if filename:
                # Show options dialog
                if self.zoom_level != 1.0 or self.pan_x != 0 or self.pan_y != 0:
                    export_choice = messagebox.askyesno(
                        "Export Options", 
                        "Do you want to export the current view?\n\n"
                        "Yes - Export as currently displayed\n"
                        "No - Export original image"
                    )
                    
                    if export_choice:
                        # Export the current view
                        # Create a new image with current view
                        img = self.original_image.copy()
                        img_width, img_height = img.size
                        
                        # Apply zoom
                        new_width = int(img_width * self.zoom_level)
                        new_height = int(img_height * self.zoom_level)
                        
                        if new_width > 0 and new_height > 0:
                            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                            
                            # Calculate crop area based on canvas and pan
                            canvas_width = self.canvas.winfo_width()
                            canvas_height = self.canvas.winfo_height()
                            
                            # Calculate center position
                            center_x = (canvas_width - new_width) // 2 + self.pan_x
                            center_y = (canvas_height - new_height) // 2 + self.pan_y
                            
                            # Save the image
                            img.save(filename)
                    else:
                        # Export original
                        self.original_image.save(filename)
                else:
                    # Export original
                    self.original_image.save(filename)
                    
                self.update_status(f"Image exported to {filename}")
                
                # Show success message
                messagebox.showinfo("Export Successful", f"House plan saved to {filename}")
        except Exception as e:
            self.update_status(f"Export failed: {str(e)}")
            messagebox.showerror("Export Failed", f"Could not save image: {str(e)}")
    
    def toggle_theme(self, event=None):
        """Toggle between light and dark theme"""
        if self.is_dark_theme:
            # Switch to light theme
            COLORS.update({
                "primary": "#4361EE",     # Blue
                "secondary": "#3F37C9",   # Dark Blue
                "accent": "#4CC9F0",      # Light Blue
                "success": "#4CAF50",     # Green
                "warning": "#F77F00",     # Orange
                "danger": "#F72585",      # Pink
                "light": "#F8F9FA",       # Light Grey
                "dark": "#212529",        # Dark Grey
                "background": "#FFFFFF",  # White
                "card": "#F0F7FF",        # Very Light Blue
            })
            self.is_dark_theme = False
        else:
            # Switch to dark theme
            COLORS.update({
                "primary": "#4CC9F0",     # Light Blue
                "secondary": "#4361EE",   # Blue
                "accent": "#3A0CA3",      # Deep Purple
                "success": "#31E981",     # Green
                "warning": "#FF9F1C",     # Orange
                "danger": "#F72585",      # Pink
                "light": "#E0E1DD",       # Light Grey
                "dark": "#1B263B",        # Dark Blue
                "background": "#0D1B2A",  # Very Dark Blue
                "card": "#1B263B",        # Dark Blue
            })
            self.is_dark_theme = True
        
        # Update UI with new colors
        self.apply_theme()
    
    def apply_theme(self):
        """Apply the current theme to all UI elements"""
        # Root background
        self.root.configure(bg=COLORS["background"])
        
        # Recreate UI elements with new theme
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.create_widgets()
        
        # If we had an image, redisplay it
        if self.original_image:
            self.update_displayed_image()


def main():
    # Create the loading.gif if it doesn't exist
    if not os.path.exists("loading.gif"):
        try:
            # Create a simple loading animation
            frames = []
            size = 100
            for i in range(8):
                img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
                draw = ImageDraw.Draw(img)
                angle = i * 45
                radius = size // 3
                x = size//2 + int(radius * math.cos(math.radians(angle)))
                y = size//2 + int(radius * math.sin(math.radians(angle)))
                draw.ellipse((x-5, y-5, x+5, y+5), fill="blue")  # Draw a dot
                frames.append(img)
            
            # Save as GIF
            frames[0].save(
                "loading.gif",
                save_all=True,
                append_images=frames[1:],
                duration=100,
                loop=0
            )
            print("Created loading.gif")
        except Exception as e:
            print(f"Error creating loading animation: {e}")

    # Create and run the application
    root = tk.Tk()
    app = HouseGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()