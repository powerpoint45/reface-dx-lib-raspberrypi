import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
import logging
import platform
import subprocess
import shutil

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class FileSelector(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("File Selector")
        self.root_directory = os.path.dirname(os.path.abspath(__file__))
        self.bookmarks_folder = os.path.join(self.root_directory, "bookmarks")
        os.makedirs(self.bookmarks_folder, exist_ok=True)

        self.attributes('-fullscreen', True)
        self.bind("<Escape>", self.toggle_fullscreen)

        # Force window resizing to full screen size
        self.update_idletasks()
        self.geometry(f"{self.winfo_screenwidth()}x{self.winfo_screenheight()}+0+0")
        self.last_bookmark_folder = ""

        # To hide the cursor
        self.config(cursor="none")

        self.midi_devices = self.list_midi_devices()
        self.selected_midi_device = tk.StringVar(value=self.midi_devices[0] if self.midi_devices else "No MIDI Device")

        self.current_path = self.root_directory
        self.files = sorted(os.listdir(self.current_path))

        self.selected_index = 0
        self.canvas_size = (self.winfo_width(), self.winfo_height())
        self.base_font_size = 5
        self.max_font_size = 20
        self.offset_y = 0
        self.item_height = 45

        self.selection_color = "red"
        self.active_color = "green"
        self.default_color = "black"
        self.clicked_index = -1

        self.configure(bg="black")

        # Create a frame for the controls at the top
        self.control_frame = tk.Frame(self, bg="black")
        self.control_frame.pack(side=tk.TOP, fill=tk.X)

        # Dropdown for MIDI devices on the left
        style = ttk.Style()
        style.configure("TCombobox", fieldbackground="black", background="black", foreground="white", width=8)
        self.midi_dropdown = ttk.Combobox(self.control_frame, textvariable=self.selected_midi_device, values=self.midi_devices, font="Verdana 9 bold", style="TCombobox")
        self.midi_dropdown.pack(side=tk.LEFT, padx=(0, 0), pady=0)

        # Label to display the current path
        self.path_label = tk.Label(self.control_frame, text=self.current_path, font="Verdana 9", anchor="w", bg="black", fg="white", width=9)
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 0), pady=0)

        # Create a new frame for the buttons and pack it below the control_frame
        self.button_frame = tk.Frame(self, bg="black")
        self.button_frame.pack(side=tk.TOP, fill=tk.X)

        # Add button for parent folder navigation on the right
        button_style = {"bg": "grey20", "fg": "white", "activebackground": "grey30"}
        self.parent_button = tk.Button(self.button_frame, text="Parent", command=self.go_to_parent_folder, height=1, width=5, **button_style)
        self.parent_button.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0))

        # Add a Bookmarks button to navigate to the bookmarks folder
        self.bookmarks_button = tk.Button(self.button_frame, text="Bookmarks", command=self.go_to_bookmarks, height=1, width=8, **button_style)
        self.bookmarks_button.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0))

        # Add "Add to Bookmarks" button
        self.add_to_bookmarks_button = tk.Button(self.button_frame, text="Add Bookmark", command=self.add_to_bookmarks, height=1, width=9, **button_style)
        self.add_to_bookmarks_button.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0))

        # Add buttons for "New Folder" and "Delete"
        self.new_folder_button = tk.Button(self.button_frame, text="New Folder", command=self.create_new_folder, height=1, width=8, **button_style)
        self.new_folder_button.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0))

        self.delete_button = tk.Button(self.button_frame, text="Delete", command=self.delete_selected_item, height=1, width=8, **button_style)
        self.delete_button.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0))

        # Create a Canvas for drawing
        self.canvas = tk.Canvas(self, bg="black", cursor="none")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.bind("<Up>", self.move_selection_up)
        self.bind("<Down>", self.move_selection_down)
        self.bind("<space>", self.click_selection)
        self.bind("<Return>", self.click_selection)
        self.bind("<BackSpace>", self.go_to_parent_folder)
        self.bind("<Configure>", self.on_resize)

        self.is_dragging = False
        self.is_animating = False
        self.start_y = 0
        self.drag_threshold = 5
        self.drag_start_y = 0
        self.target_offset_y = 0

        self.update_canvas()

    def toggle_fullscreen(self, event=None):
        current_state = self.attributes('-fullscreen')
        self.attributes('-fullscreen', not current_state)

    def go_to_parent_folder(self, event=None):
        parent_path = os.path.dirname(self.current_path)
        if parent_path:
            self.current_path = parent_path
            self.selected_file = 0
            self.offset_y = 0
            logging.info(f"Navigating to parent folder: {self.current_path}")
            self.update_file_list()

    def go_to_bookmarks(self):
        self.current_path = self.bookmarks_folder
        self.selected_file = 0
        self.offset_y = 0
        logging.info(f"Navigating to the bookmarks folder: {self.bookmarks_folder}")
        self.update_file_list()

    def update_file_list(self):
        try:
            self.files = sorted(os.listdir(self.current_path))
            self.selected_index = 0
            self.update_path_label()
            self.update_canvas()
            logging.debug(f"Updated files list: {self.files}")
        except Exception as e:
            logging.error(f"Failed to list files in {self.current_path}: {e}")

    def update_path_label(self):
        self.path_label.config(text=self.current_path)

    def list_midi_devices(self):
        try:
            import mido
            return mido.get_input_names()
        except Exception as e:
            logging.error("Could not list MIDI devices: " + str(e))
            return []

    def draw(self):
        self.canvas.delete("all")  # Clear the canvas

        center_y = self.canvas_size[1] // 2
        num_items = len(self.files)

        # Draw lines above and below the selected item
        line_x1 = 0
        line_x2 = self.canvas_size[0]

        self.canvas.create_line(line_x1, center_y - self.item_height // 2, line_x2, center_y - self.item_height // 2, fill="white")
        self.canvas.create_line(line_x1, center_y + self.item_height // 2, line_x2, center_y + self.item_height // 2, fill="white")

        for index in range(num_items):
            x = self.canvas_size[0] // 2
            y = (index) * self.item_height + center_y + self.offset_y

            if 0 <= y <= self.canvas_size[1]:
                distance_from_center = abs(y - center_y)
                normalized_distance = max(1, self.canvas_size[1] // 2)
                font_size = self.base_font_size + (self.max_font_size - self.base_font_size) * (1 - min(distance_from_center / normalized_distance, 1))
                font = ("Helvetica", int(font_size), "bold" if index == self.selected_index else "normal")

                if index == self.clicked_index:
                    color = self.active_color
                elif index == self.selected_index:
                    color = "white"
                else:
                    color = "gray"

                text_width = self.canvas.create_text(x, y + 5, text=self.files[index], fill=color, font=font)
                self.canvas.tag_lower(text_width)

    def on_resize(self, event):
        self.update_canvas()

    def update_canvas(self):
        self.canvas_size = (self.winfo_width(), self.winfo_height())
        self.draw()

    def on_mouse_wheel(self, event):
        scroll_amount = 3
        if event.delta > 0:
            self.move_selection_up(event)
        else:
            self.move_selection_down(event)

    def on_click(self, event):
        self.start_y = event.y
        self.is_dragging = True
        self.drag_start_y = event.y

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
                    self.files = sorted(os.listdir(self.current_path))
                    self.selected_index = 0
                    self.update_path_label()
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
        self.is_dragging = False
        delta_y = event.y - self.drag_start_y

        center_y = self.canvas_size[1] // 2
        distance_from_center = event.y - center_y

        if abs(delta_y) < self.drag_threshold and (distance_from_center < (self.item_height) and distance_from_center > -(self.item_height) ):
            self.update_selected_through_closest_item()
            self.clicked_index = self.selected_index
            self.update_canvas()
            self.on_item_chosen()
        else:
            if abs(delta_y) < self.drag_threshold:
                self.selected_index = self.selected_index + int(((distance_from_center+20)//self.item_height))
            else:
                self.update_selected_through_closest_item()

        self.selected_index = max(0, min(self.selected_index, len(self.files) - 1))

        if not self.is_animating:
            self.animate_settle()

    def animate_settle(self):
        self.target_offset_y = -self.selected_index * self.item_height
        step = (self.target_offset_y - self.offset_y) * 0.4

        if abs(step) > 1:
            self.offset_y += step
            self.update_canvas()
            if not self.is_dragging:
                self.is_animating = True
                self.after(2, self.animate_settle)
            else:
                self.is_animating = False
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
            y = (index) * self.item_height + center_y + self.offset_y
            distance_from_center = abs(y - center_y)

            if distance_from_center < closest_distance:
                closest_distance = distance_from_center
                closest_index = index

        self.selected_index = max(0, min(closest_index, len(self.files) - 1))

    def move_selection_up(self, event):
        if self.selected_index > 0:
            self.selected_index -= 1
            self.target_offset_y = -self.selected_index * self.item_height
            if not self.is_animating:
                self.animate_settle()
            self.update_canvas()

    def move_selection_down(self, event):
        if self.selected_index < len(self.files) - 1:
            self.selected_index += 1
            self.target_offset_y = -self.selected_index * self.item_height
            if not self.is_animating:
                self.animate_settle()
            self.update_canvas()

    def click_selection(self, event):
        self.clicked_index = self.selected_index
        self.update_selected_through_closest_item()
        self.target_offset_y = 0
        if not self.is_animating:
            self.animate_settle()
        self.on_item_chosen()
        self.update_canvas()

    def create_new_folder(self):
        new_folder_name = simpledialog.askstring("New Folder", "Enter folder name:", parent=self)

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
            messagebox.showerror("Error", f"Could not create folder: {e}")

    def delete_selected_item(self):
        if 0 <= self.selected_index < len(self.files):
            selected_file = self.files[self.selected_index]
            selected_file_path = os.path.join(self.current_path, selected_file)

            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{selected_file}'?"):
                try:
                    if os.path.isdir(selected_file_path):
                        os.rmdir(selected_file_path)
                    else:
                        os.remove(selected_file_path)

                    logging.info(f"Deleted: {selected_file_path}")
                    self.update_file_list()
                except Exception as e:
                    logging.error(f"Failed to delete {selected_file}: {e}")
                    messagebox.showerror("Error", f"Could not delete {selected_file}: {e}")

    def add_to_bookmarks(self):
        if self.selected_index < 0 or self.selected_index >= len(self.files):
            return

        selected_file = self.files[self.selected_index]
        selected_file_path = os.path.join(self.current_path, selected_file)

        bookmark_type = "folder" if os.path.isdir(selected_file_path) else "file"

        folders = [name for name in os.listdir(self.bookmarks_folder) if os.path.isdir(os.path.join(self.bookmarks_folder, name))]

        def show_folders_dialog():
            dialog = tk.Toplevel(self)
            dialog.title("Select or Create Bookmark Folder")
            dialog.configure(bg='light blue')
            dialog.geometry("300x400")
            dialog.transient(self)
            dialog.grab_set()
            dialog.update_idletasks()

            x = (self.winfo_rootx() + (self.winfo_width() // 2)) - (dialog.winfo_width() // 2)
            y = (self.winfo_rooty() + (self.winfo_height() // 2)) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")

            frame = tk.Frame(dialog, bg='light blue')
            frame.pack(padx=10, pady=10, fill="both", expand=True)

            tk.Label(frame, text="Select a folder to save the bookmark in:", bg='light blue').pack(pady=5)

            tk.Button(frame, text="Bookmarks Root", command=lambda: save_bookmark("")).pack(fill=tk.X, pady=2)

            for folder in folders:
                tk.Button(frame, text=folder, command=lambda folder=folder: save_bookmark(folder)).pack(fill=tk.X, pady=2)

            tk.Button(frame, text="Create New Folder", command=create_new_folder_in_dialog).pack(fill=tk.X, pady=5)

            tk.Button(frame, text="Cancel", command=dialog.destroy, bg="red", fg="white").pack(fill=tk.X, pady=5)

        def create_new_folder_in_dialog():
            new_folder_name = simpledialog.askstring("New Folder", "Enter new folder name for bookmarks:", parent=self)

            if not new_folder_name:
                return

            folder_path = os.path.join(self.bookmarks_folder, new_folder_name)
            os.makedirs(folder_path, exist_ok=True)
            save_bookmark(new_folder_name)

        def save_bookmark(folder_name):
            folder_path = os.path.join(self.bookmarks_folder, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            try:
                link_name = os.path.join(folder_path, selected_file)
                if not os.path.exists(link_name):
                    if bookmark_type == "file":
                        shutil.copy(selected_file_path, link_name)
                    elif bookmark_type == "folder":
                        # Create a symlink if possible
                        if hasattr(os, 'symlink'):
                            os.symlink(selected_file_path, link_name)
                        else:
                            shutil.copytree(selected_file_path, link_name)

                    self.last_bookmark_folder = folder_name
                    messagebox.showinfo("Success", f"{selected_file} bookmarked in {folder_name}.")
                else:
                    messagebox.showwarning("Warning", "Bookmark already exists.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to bookmark {bookmark_type}: {e}")

        show_folders_dialog()

if __name__ == '__main__':
    file_selector = FileSelector()
    file_selector.mainloop()