import os
import skia
import tkinter as tk
from PIL import Image, ImageTk
import logging
import platform
import subprocess
from tkinter import ttk  # Import ttk for Combobox
from tkinter import messagebox
from tkinter import simpledialog
import shutil

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class FileSelector(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("File Selector")

        # Ensure the bookmarks folder exists
        self.root_directory = os.path.dirname(os.path.abspath(__file__))
        self.bookmarks_folder = os.path.join(self.root_directory, "bookmarks")
        os.makedirs(self.bookmarks_folder, exist_ok=True)

        # Last used bookmark folder
        self.last_bookmark_folder = ""

        # Start the application in fullscreen mode
        self.attributes('-fullscreen', True)
        self.bind("<Escape>", self.toggle_fullscreen)  # Press Escape to exit fullscreen

        # MIDI device list
        self.midi_devices = self.list_midi_devices()  # Get connected MIDI devices
        self.selected_midi_device = tk.StringVar(value=self.midi_devices[0] if self.midi_devices else "No MIDI Device")  # Default

        self.current_path = os.path.abspath('.')  # Initialize as absolute path
        self.files = os.listdir(self.current_path)

        self.selected_index = 0
        self.canvas_size = (self.winfo_width(), self.winfo_height())
        self.base_font_size = 5
        self.max_font_size = 30
        self.offset_y = 0

        self.selection_color = skia.ColorRED
        self.active_color = skia.ColorGREEN
        self.default_color = skia.ColorBLACK
        self.clicked_index = -1

        # Set the black background
        self.configure(bg="black")

        # Create a frame for the controls at the top
        self.control_frame = tk.Frame(self, bg="black")
        self.control_frame.pack(side=tk.TOP, fill=tk.X)

        # Dropdown for MIDI devices on the left
        style = ttk.Style()
        style.configure("TCombobox", fieldbackground="black", background="black", foreground="white", width=5)
        self.midi_dropdown = ttk.Combobox(self.control_frame, textvariable=self.selected_midi_device, values=self.midi_devices, font="Verdana 15 bold", style="TCombobox")
        self.midi_dropdown.pack(side=tk.LEFT, padx=(3, 0), pady=5)  # Add some padding for aesthetics

        # Label to display the current path
        self.path_label = tk.Label(self.control_frame, text=self.current_path, font="Verdana 12", anchor="w", bg="black", fg="white",width=9)
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5), pady=5)

        # Add button for parent folder navigation on the right
        button_style = {"bg": "grey20", "fg": "white", "activebackground": "grey30"}
        self.parent_button = tk.Button(self.control_frame, text="Parent Folder", command=self.go_to_parent_folder, height=2, width=10, **button_style)
        self.parent_button.pack(side=tk.RIGHT, padx=(0, 0), pady=0)

        # Add a Bookmarks button to navigate to the bookmarks folder
        self.bookmarks_button = tk.Button(self.control_frame, text="Bookmarks", command=self.go_to_bookmarks, height=2, width=10, **button_style)
        self.bookmarks_button.pack(side=tk.RIGHT, padx=(0, 0), pady=0)

        # Add "Add to Bookmarks" button
        self.add_to_bookmarks_button = tk.Button(self.control_frame, text="Add to Bookmarks", command=self.add_to_bookmarks, height=2, width=15, **button_style)
        self.add_to_bookmarks_button.pack(side=tk.RIGHT, padx=(0, 0), pady=0)

        # Add buttons for "New Folder" and "Delete"
        self.new_folder_button = tk.Button(self.control_frame, text="New Folder", command=self.create_new_folder, height=2, width=9, **button_style)
        self.new_folder_button.pack(side=tk.RIGHT, padx=0, pady=0)

        self.delete_button = tk.Button(self.control_frame, text="Delete", command=self.delete_selected_item, height=2, width=8, **button_style)
        self.delete_button.pack(side=tk.RIGHT, padx=0, pady=0)

        # Create a Canvas for drawing
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Enable dragging, scrolling, and keyboard input
        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.bind("<Up>", self.move_selection_up)
        self.bind("<Down>", self.move_selection_down)
        self.bind("<space>", self.click_selection)
        self.bind("<Return>", self.click_selection)
        self.bind("<BackSpace>", self.go_to_parent_folder)
        self.bind("<Configure>", self.on_resize)  # Bind resizing of the window

        self.is_dragging = False
        self.is_animating = False
        self.start_y = 0
        self.drag_threshold = 5
        self.drag_start_y = 0
        self.target_offset_y = 0

        self.update_canvas()  # Initial canvas update

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        current_state = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current_state)

    def go_to_parent_folder(self, event=None):
        """Navigate to the parent folder of the current path."""
        parent_path = os.path.dirname(self.current_path)  # Get the parent directory
        if parent_path:
            self.current_path = parent_path  # Change current path to parent
            self.selected_file = 0
            self.offset_y = 0
            logging.info(f"Navigating to parent folder: {self.current_path}")
            self.update_file_list()  # Update the file list

    def go_to_bookmarks(self):
        """Navigate to the bookmarks folder."""
        self.current_path = self.bookmarks_folder
        self.selected_file = 0
        self.offset_y = 0
        logging.info(f"Navigating to the bookmarks folder: {self.bookmarks_folder}")
        self.update_file_list()

    def update_file_list(self):
        """Update the list of files in the current directory."""
        try:
            self.files = os.listdir(self.current_path)  # List files in the new current directory
            self.selected_index = 0  # Reset selected index
            self.update_path_label()  # Update the path label
            self.update_canvas()  # Refresh the canvas to show the updated file list
            logging.debug(f"Updated files list: {self.files}")  # Log updated file list
        except Exception as e:
            logging.error(f"Failed to list files in {self.current_path}: {e}")

    def update_path_label(self):
        """Update the label displaying the current path."""
        self.path_label.config(text=self.current_path)

    def list_midi_devices(self):
        """List connected MIDI devices."""
        try:
            import mido
            return mido.get_input_names()  # Get connected MIDI input devices
        except Exception as e:
            logging.error("Could not list MIDI devices: " + str(e))
            return []

    def draw(self):
        # Create a surface to draw on
        self.canvas_size = (self.winfo_width(), self.winfo_height())

        # Prevent division by zero if canvas size is not valid
        if self.canvas_size[1] == 0:
            return skia.Surface(1, 1)  # Return a minimal canvas if height is zero

        surface = skia.Surface(self.canvas_size[0], self.canvas_size[1])
        canvas = surface.getCanvas()
        canvas.clear(skia.ColorBLACK)

        # Center position for the selected item
        center_y = self.canvas_size[1] // 2
        item_height = 60
        num_items = len(self.files)

        # Draw lines above and below the selected item
        line_x1 = 100  # Starting X position for lines
        line_x2 = self.canvas_size[0] - 100  # Ending X position for lines
        canvas.drawLine(line_x1, center_y - item_height // 2, line_x2, center_y - item_height // 2, skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))
        canvas.drawLine(line_x1, center_y + item_height // 2, line_x2, center_y + item_height // 2, skia.Paint(AntiAlias=True, Color=skia.ColorWHITE))

        # Draw items based on current selection and offset
        for index in range(num_items):
            x = self.canvas_size[0] // 2
            # Calculate the y position for each item based on the scrolling offset
            y = (index) * item_height + center_y + self.offset_y

            # Only draw if within canvas bounds
            if 0 <= y <= self.canvas_size[1]:
                # Calculate distance from center and adjust font size proportionally
                distance_from_center = abs(y - center_y)  # Distance from center position

                # Handle case where canvas height is small
                normalized_distance = max(1, self.canvas_size[1] // 2)  # Prevent zero division
                font_size = self.base_font_size + (self.max_font_size - self.base_font_size) * (1 - min(distance_from_center / normalized_distance, 1))

                # Create font for the current item
                font = skia.Font(None, int(font_size))

                # Determine the color of the item based on its state
                if index == self.clicked_index:  # If it was clicked
                    color = self.active_color
                elif index == self.selected_index:  # If it is selected
                    color = skia.ColorWHITE
                else:
                    color = skia.ColorGRAY

                paint = skia.Paint(AntiAlias=True, Color=color)

                # Draw the focused item in bold
                if index == self.selected_index:
                    font.setEmbolden(True)    # Set embolden for the selected item
                else:
                    font.setEmbolden(False)    # Ensure it's normal for others

                text_width = font.measureText(self.files[index])
                canvas.drawString(self.files[index], x - text_width // 2, y + 10, font, paint)

        return surface

    def on_resize(self, event):
        """Handle window resizing."""
        self.update_canvas()

    def update_canvas(self):
        surface = self.draw()
        img = surface.makeImageSnapshot()

        # Convert Skia image to PIL image
        img_pil = Image.frombytes('RGBA', (img.width(), img.height()), img.tobytes())
        self.tk_image = ImageTk.PhotoImage(img_pil)

        # Draw the photo image onto the Tkinter Canvas
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def on_mouse_wheel(self, event):
        scroll_amount = 3  # Reduced scroll amount
        if event.delta > 0:
            self.move_selection_up(event)
        else:
            self.move_selection_down(event)   # Scroll down

    def on_click(self, event):
        self.start_y = event.y
        self.is_dragging = True
        self.drag_start_y = event.y

        # Log the debug information
        logging.debug(f"Click started at y={event.y}")

    def on_item_chosen(self):
        logging.debug(f"Item chosen: {self.files[self.selected_index]}")

        if 0 <= self.selected_index < len(self.files):
            selected_file = self.files[self.selected_index]
            selected_file_path = os.path.join(self.current_path, selected_file)  
            logging.debug(f"Selected file path: {selected_file_path}")

            if os.path.isdir(selected_file_path):
                logging.info(f"Selected item is a folder: {selected_file_path}")
                self.current_path = selected_file_path
                try:
                    os.chdir(self.current_path)
                    self.files = os.listdir(self.current_path)
                    self.selected_index = 0
                    self.update_path_label()  # Update the path label
                    logging.debug(f"Updated files list: {self.files}")
                except Exception as e:
                    logging.error(f"Failed to change directory to {self.current_path}: {e}")
            elif selected_file.lower().endswith('.syx'):
                midi_device = self.selected_midi_device.get()
                port_number = self.midi_devices.index(midi_device) if midi_device in self.midi_devices else 0
                logging.debug(f"Executing command: python get_soundmondo_voice.py -m {selected_file_path} -p {port_number}")
                try:
                    os.chdir(self.root_directory)
                    subprocess.call(f"python get_soundmondo_voice.py -m {selected_file_path} -p {port_number}", shell=True)
                except Exception as e:
                    logging.error(f"Failed to execute command for file {selected_file_path}: {e}")
            else:
                try:
                    if platform.system() == "Windows":
                        os.startfile(selected_file_path)
                    elif platform.system() == "Darwin":
                        subprocess.call(['open', selected_file_path])
                    else:
                        subprocess.call(['xdg-open', selected_file_path])
                except Exception as e:
                    logging.error(f"Failed to open file {selected_file_path}: {e}")

    def on_release(self, event):
        """Handle mouse release event."""
        self.is_dragging = False
        delta_y = event.y - self.drag_start_y

        center_y = self.canvas_size[1] // 2
        distance_from_center = event.y - center_y

        # If click was near the center and minimal drag occurred
        if abs(delta_y) < self.drag_threshold and (distance_from_center < 30 and distance_from_center > -30 ):
            self.update_selected_through_closest_item()
            self.clicked_index = self.selected_index
            self.on_item_chosen()
        else:
            if abs(delta_y) < self.drag_threshold:
                # Select index based on where the user clicked
                self.selected_index = self.selected_index + int(((distance_from_center+20)//60))
            else:
                # Select index based on the item closest to the center
                self.update_selected_through_closest_item()

        # Ensure the selected index is within valid bounds
        self.selected_index = max(0, min(self.selected_index, len(self.files) - 1))

        # Trigger the animation to center the selected item
        if not self.is_animating:
            self.animate_settle()

    def animate_settle(self):
        """Smoothly animate the offset to center the selected item."""
        self.is_animating = True
        self.target_offset_y = -self.selected_index * 60
        step = (self.target_offset_y - self.offset_y) * 0.4

        if abs(step) > 1:
            self.offset_y += step
            self.update_canvas()
            if not self.is_dragging:
                self.after(3, self.animate_settle)
        else:
            self.offset_y = self.target_offset_y
            self.update_canvas()
            self.is_animating = False

    def on_drag(self, event):
        if self.is_dragging:
            delta_y = event.y - self.start_y
            self.offset_y += delta_y
            self.start_y = event.y
            self.update_canvas()

    def update_selected_through_closest_item(self):
        center_y = self.canvas_size[1] // 2
        closest_index = -1
        closest_distance = float('inf')

        for index in range(len(self.files)):
            y = (index) * 60 + center_y + self.offset_y
            distance_from_center = abs(y - center_y)

            if distance_from_center < closest_distance:
                closest_distance = distance_from_center
                closest_index = index

        self.selected_index = max(0, min(closest_index, len(self.files) - 1))

    def move_selection_up(self, event):
        """Move the selection up."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self.target_offset_y = -self.selected_index * 60
            if not self.is_animating:
                self.animate_settle()
            self.update_canvas()

    def move_selection_down(self, event):
        """Move the selection down."""
        if self.selected_index < len(self.files) - 1:
            self.selected_index += 1
            self.target_offset_y = -self.selected_index * 60
            if not self.is_animating:
                self.animate_settle()
            self.update_canvas()

    def click_selection(self, event):
        """Simulate clicking the selected item."""
        self.clicked_index = self.selected_index
        self.update_selected_through_closest_item()
        self.target_offset_y = 0
        if not self.is_animating:
            self.animate_settle()
        self.on_item_chosen()
        self.update_canvas()

    def create_new_folder(self):
        """Prompt the user for a folder name and create a new folder."""
        new_folder_name = tk.simpledialog.askstring("New Folder", "Enter folder name:")

        if not new_folder_name:
            return

        new_folder_path = os.path.join(self.current_path, new_folder_name)

        counter = 1
        original_folder_name = new_folder_name
        while os.path.exists(new_folder_path):
            new_folder_name = f"{original_folder_name} ({counter})"
            new_folder_path = os.path.join(self.current_path, new_folder_name)
            counter += 1

        try:
            os.mkdir(new_folder_path)
            logging.info(f"Created new folder: {new_folder_path}")
            self.update_file_list()
        except Exception as e:
            logging.error(f"Failed to create folder: {e}")
            tk.messagebox.showerror("Error", f"Could not create folder: {e}")

    def delete_selected_item(self):
        """Delete the selected file or folder with confirmation."""
        if 0 <= self.selected_index < len(self.files):
            selected_file = self.files[self.selected_index]
            selected_file_path = os.path.join(self.current_path, selected_file)

            if tk.messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{selected_file}'?"):
                try:
                    if os.path.isdir(selected_file_path):
                        os.rmdir(selected_file_path)
                    else:
                        os.remove(selected_file_path)

                    logging.info(f"Deleted: {selected_file_path}")
                    self.update_file_list()
                except Exception as e:
                    logging.error(f"Failed to delete {selected_file}: {e}")
                    tk.messagebox.showerror("Error", f"Could not delete {selected_file}: {e}")

    def add_to_bookmarks(self):
        """Add a file to the bookmarks."""
        if self.selected_index < 0 or self.selected_index >= len(self.files):
            return

        selected_file = self.files[self.selected_index]
        selected_file_path = os.path.join(self.current_path, selected_file)

        if not os.path.isfile(selected_file_path):
            tk.messagebox.showerror("Error", "Cannot bookmark a folder.")
            return

        folders = [name for name in os.listdir(self.bookmarks_folder) if os.path.isdir(os.path.join(self.bookmarks_folder, name))]

        # Pre-fill the input box with the last entered bookmark folder name
        folder_name = tk.simpledialog.askstring(
            "Bookmark Folder",
            f"Enter a folder name to save bookmark in:\n(Current folders: {', '.join(folders)})",
            initialvalue=self.last_bookmark_folder
        )

        if not folder_name:
            return

        folder_path = os.path.join(self.bookmarks_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        try:
            link_name = os.path.join(folder_path, selected_file)
            if not os.path.exists(link_name):
                shutil.copy(selected_file_path, link_name)
                self.last_bookmark_folder = folder_name
                tk.messagebox.showinfo("Success", f"{selected_file} bookmarked in {folder_name}.")
            else:
                tk.messagebox.showwarning("Warning", "Bookmark already exists.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to bookmark file: {e}")

if __name__ == '__main__':
    file_selector = FileSelector()
    file_selector.mainloop()  # Start the Tkinter event loop