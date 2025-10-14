import os
import logging
import platform
import subprocess
import shutil
import tkinter as tk
from PIL import ImageTk, Image
from tkinter import messagebox
from ttkbootstrap import Style
from ttkbootstrap.widgets import Frame, Combobox, Button, Label


# Set up logging
logging.basicConfig(level=logging.DEBUG)


class FileSelector(tk.Tk):
    def __init__(self):
        super().__init__()

        self.style = Style('solar')
        self.title("File Selector")
        self.root_directory = os.path.dirname(os.path.abspath(__file__))

        self.home_folder = os.path.join(self.root_directory, "Home")
        self.bookmarks_folder = os.path.join(self.home_folder, "Bookmarks")

        os.makedirs(self.bookmarks_folder, exist_ok=True)

        self.downloads_folder = os.path.join(self.home_folder, "Downloads")

        os.makedirs(self.downloads_folder, exist_ok=True)

        self.attributes('-fullscreen', True)
        self.bind("&lt;Escape&gt;", self.toggle_fullscreen)

        self.update_idletasks()
        self.geometry("480x640+0+0")

        self.config(cursor="none")

        self.midi_devices = self.list_midi_devices()

        # Select the default MIDI device that starts with "reface"
        default_midi_device = next((device for device in self.midi_devices if device.lower().startswith("reface")), None)

        # Set the selected MIDI device to the default "reface" device, or the first device if no such device is found
        self.selected_midi_device = tk.StringVar(value=default_midi_device if default_midi_device else (self.midi_devices[0] if self.midi_devices else "No MIDI Device"))

        self.current_path = self.home_folder
        self.file_names = []         # Array to store file names
        self.file_paths = []         # Array to store full file paths

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

        self.control_frame = Frame(self, bootstyle="default")
        self.control_frame.pack(side=tk.TOP, fill=tk.X, ipady=3)

        self.style.configure(
            'Custom.TCombobox',
            arrowsize=40,
            padding=10
        )

        self.midi_dropdown = Combobox(
            self.control_frame,
            textvariable=self.selected_midi_device,
            values=self.midi_devices,
            font="Verdana 11 bold",
            bootstyle="success",
            style='Custom.TCombobox'
        )
        self.midi_dropdown.pack(side=tk.LEFT, padx=(5, 5), pady=5)

        # Bind the event to update MIDI devices when the dropdown is clicked
        self.midi_dropdown.bind("&lt;Button-1&gt;", self.update_midi_devices_list)

        self.path_label = Label(
            self.control_frame,
            text=self.current_path,
            font="Verdana 10",
            anchor="w",
            bootstyle="info"
        )
        self.path_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(3, 0), pady=0)

        self.button_frame = Frame(self, bootstyle="default")
        self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

        self.parent_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_undo.png"))
        self.home_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_home.png"))
        self.bookmarks_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_bookmarks.png"))
        self.bookmark_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_grade.png"))
        self.new_folder_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_create_new_folder.png"))
        self.delete_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_delete.png"))
        self.patch_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_save.png"))
        self.downloads_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_get_app.png"))
        self.edit_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_edit.png"))

        # Search icon for the search button
        self.search_icon = ImageTk.PhotoImage(Image.open("res/drawable-mdpi/ic_search.png"))

        buttons = [
            (self.parent_icon, "Parent", self.go_to_parent_folder),
            (self.home_icon, "Home", self.go_to_home_folder),
            (self.bookmarks_icon, "Bookmarks", self.go_to_bookmarks),
            (self.bookmark_icon, "Add Bookmark", self.add_to_bookmarks),
            (self.new_folder_icon, "New Folder", self.create_new_folder),
            (self.delete_icon, "Delete", self.delete_selected_item),
            (self.patch_icon, "Request Patch", self.request_patch),
            (self.downloads_icon, "Saved Patches", self.go_to_downloads),
            (self.edit_icon, "Rename", self.rename),
            (self.search_icon, "Search", self.search_files)
        ]

        self.style.configure(
            'Monospace.TButton',
            font=('Courier bold', 10)
        )

        for i in range(2):
            for j in range(5):
                icon, text, command = buttons[i * 5 + j]
                button = Button(
                    self.button_frame,
                    text=text,
                    compound="top",
                    image=icon,
                    command=command,
                    bootstyle="info-outline-button"
                )
                button.grid(row=i, column=j, padx=2, pady=2, ipady=0, ipadx=0, sticky="nsew")

        for i in range(2):
            self.button_frame.grid_rowconfigure(i, weight=1)
        for j in range(5):
            self.button_frame.grid_columnconfigure(j, weight=1, minsize=90)

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

        self.search_results = []  # To store search results

        self.update_file_list()  # Initial population

    def update_midi_devices_list(self, event):
        """Update the MIDI devices list just before showing the dropdown."""
        new_midi_devices = self.list_midi_devices()
        if new_midi_devices:
            self.midi_devices = new_midi_devices
            self.midi_dropdown['values'] = self.midi_devices

            current_selection = self.selected_midi_device.get()
            if current_selection not in self.midi_devices:
                # Auto-select the first available device if the current selection is no longer valid
                self.selected_midi_device.set(self.midi_devices[0])

        logging.debug(f"Updated MIDI devices list: {self.midi_devices}")

    def list_midi_devices(self):
        try:
            import mido
            return mido.get_input_names()
        except Exception as e:
            logging.error("Could not list MIDI devices: " + str(e))
            return []

    def search_files(self):
        """Prompt for a search query and display matching files."""
        search_query = self.create_dialog("Search Files", "Enter search query:")
        if not search_query:
            return

        # Walk the directory tree to find matching files
        matches = []
        for root, _, files in os.walk(self.root_directory):
            for file in files:
                if search_query.lower() in file.lower():
                    matches.append(os.path.join(root, file))

        if matches:
            self.populate_files(matches)
            self.update_canvas()
            self.path_label.config(text="Search Results")
            messagebox.showinfo("Search Results", f"Found {len(matches)} matching files.")
        else:
            self.search_results = []
            messagebox.showwarning("No Results", "No files found matching the search query.")

    def rename(self):
        """Rename the selected file, folder, or link."""
        if 0 <= self.selected_index < len(self.file_paths):
            selected_file_name = self.file_names[self.selected_index]
            selected_file_path = self.file_paths[self.selected_index]

            # Ask for the new name
            new_name = self.create_dialog("Rename Item", f"Enter a new name for '{selected_file_name}':")

            if new_name:
                new_file_path = os.path.join(os.path.dirname(selected_file_path), new_name)
                try:
                    os.rename(selected_file_path, new_file_path)
                    logging.info(f"Renamed '{selected_file_name}' to '{new_name}'")
                    self.update_file_list()  # Update the file list
                except Exception as e:
                    logging.error(f"Failed to rename '{selected_file_name}': {e}")
                    messagebox.showerror("Error", f"Could not rename '{selected_file_name}': {e}")

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

    def go_to_home_folder(self):
        self.current_path = self.home_folder
        self.selected_file = 0
        self.offset_y = 0
        logging.info(f"Navigating to the home folder: {self.home_folder}")
        self.update_file_list()

    def go_to_downloads(self):
        self.current_path = self.downloads_folder
        self.selected_file = 0
        self.offset_y = 0
        logging.info(f"Navigating to the downloads folder: {self.downloads_folder}")
        self.update_file_list()

    def update_file_list(self):
        # Restore files to display initial directory files instead of search results
        try:
            self.populate_files(list(map(lambda x: os.path.join(self.current_path, x), sorted(os.listdir(self.current_path)))))
            self.update_path_label()
            self.update_canvas()
            logging.debug(f"Updated files list: {self.file_names}")
        except Exception as e:
            logging.error(f"Failed to list files in {self.current_path}: {e}")

    def update_path_label(self):
        self.path_label.config(text=os.path.basename(self.current_path))

    def list_midi_devices(self):
        try:
            import mido
            return mido.get_input_names()
        except Exception as e:
            logging.error("Could not list MIDI devices: " + str(e))
            return []

    def draw(self):
        self.canvas.delete("all")

        center_y = self.canvas_size[1] // 2 - 150
        num_items = len(self.file_names)

        line_x1 = 0
        line_x2 = self.canvas_size[0]

        self.canvas.create_line(line_x1, center_y - self.item_height // 2, line_x2, center_y - self.item_height // 2, fill="#81a2b8")
        self.canvas.create_line(line_x1, center_y + self.item_height // 2, line_x2, center_y + self.item_height // 2, fill="#81a2b8")

        if num_items == 0:
            x = self.canvas_size[0] // 2
            font = ("Helvetica", 14, "bold")
            self.canvas.create_text(x, center_y, text="Empty Folder", fill="red", font=font)

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
                    color = "#edf0f2"
                else:
                    color = "#81a2b8"

                self.canvas.create_text(x, y + 5, text=self.file_names[index], fill=color, font=font)

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
        logging.debug(f"Item chosen: {self.file_names[self.selected_index]}")

        if 0 <= self.selected_index < len(self.file_names):
            selected_file = self.file_names[self.selected_index]
            selected_file_path = self.file_paths[self.selected_index]
            logging.debug(f"Selected file path: {selected_file_path}")

            if os.path.isdir(selected_file_path):
                logging.info(f"Selected item is a folder: {selected_file_path}")
                self.current_path = selected_file_path
                try:
                    os.chdir(self.current_path)
                    self.update_file_list()
                    logging.debug(f"Updated files list: {self.file_names}")
                except Exception as e:
                    logging.error(f"Failed to change directory to {self.current_path}: {e}")
            elif selected_file.lower().endswith('.syx'):
                midi_device = self.selected_midi_device.get()
                port_number = self.midi_devices.index(midi_device) if midi_device in self.midi_devices else 0
                logging.debug(f"Executing command: python -m tools.get_soundmondo_voice -m {selected_file_path} -p {port_number}")
                try:
                    os.chdir(self.root_directory)
                    subprocess.call(f"python -m tools.get_soundmondo_voice -m {selected_file_path} -p {port_number}", shell=True)
                except Exception as e:
                     logging.error(f"Failed to execute command for file {selected_file_path}: {e}")
            # else:
            #     try:
            #         if platform.system() == "Windows":
            #             os.startfile(selected_file_path)
            #         elif platform.system() == "Darwin":
            #             subprocess.call(['open', selected_file_path])
            #         else:
            #             subprocess.call(['xdg-open', selected_file_path])
            #     except Exception as e:
            #         logging.error(f"Failed to open file {selected_file_path}: {e}")

    def on_release(self, event):
        self.is_dragging = False
        delta_y = event.y - self.drag_start_y

        center_y = self.canvas_size[1] // 2 - 150
        distance_from_center = event.y - center_y

        if abs(delta_y) < self.drag_threshold and (distance_from_center < (self.item_height) and distance_from_center > -(self.item_height)):
            self.update_selected_through_closest_item()
            self.clicked_index = self.selected_index
            self.update_canvas()
            self.on_item_chosen()
        else:
            if abs(delta_y) < self.drag_threshold:
                self.selected_index = self.selected_index + int(((distance_from_center + 20) // self.item_height))
            else:
                self.update_selected_through_closest_item()

        self.selected_index = max(0, min(self.selected_index, len(self.file_names) - 1))

        if not self.is_animating:
            self.animate_settle()

        self.canvas.focus_set()

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
        center_y = self.canvas_size[1] // 2 - 150
        closest_index = -1
        closest_distance = float('inf')

        for index in range(len(self.file_names)):
            y = (index) * self.item_height + center_y + self.offset_y
            distance_from_center = abs(y - center_y)

            if distance_from_center < closest_distance:
                closest_distance = distance_from_center
                closest_index = index

        self.selected_index = max(0, min(closest_index, len(self.file_names) - 1))

    def move_selection_up(self, event):
        if self.selected_index > 0:
            self.selected_index -= 1
            self.target_offset_y = -self.selected_index * self.item_height
            if not self.is_animating:
                self.animate_settle()
            self.update_canvas()

    def move_selection_down(self, event):
        if self.selected_index < len(self.file_names) - 1:
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
        new_folder_name = self.create_dialog("New Folder", "Enter folder name:")

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
        if 0 <= self.selected_index < len(self.file_names):
            selected_file = self.file_names[self.selected_index]
            selected_file_path = self.file_paths[self.selected_index]

            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{selected_file}'?"):
                try:
                    if os.path.isdir(selected_file_path):
                        if os.path.islink(selected_file_path):
                            os.unlink(selected_file_path)
                        else:
                            shutil.rmtree(selected_file_path)
                    else:
                        os.remove(selected_file_path)

                    logging.info(f"Deleted: {selected_file_path}")
                    self.update_file_list()
                except Exception as e:
                    logging.error(f"Failed to delete {selected_file}: {e}")
                    messagebox.showerror("Error", f"Could not delete {selected_file}: {e}")

    def request_patch(self):
        os.chdir(self.root_directory)
        midi_device = self.selected_midi_device.get()
        port_number = self.midi_devices.index(midi_device) if midi_device in self.midi_devices else 0

        folder = self.downloads_folder + "/"

        command = f"python -m tools.request_patch -i {port_number} -o {port_number} -p {folder}"
        logging.debug(f"Executing command: {command}")

        try:
            subprocess.run(command, shell=True, check=True)
            messagebox.showinfo("Success", "Patch saved to " + self.downloads_folder)
            logging.info("Patch request completed successfully.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to execute patch request: {e}")
            messagebox.showerror("Error", f"Failed to request patch: {e}")


    def add_to_bookmarks(self):
        if self.selected_index < 0 or self.selected_index >= len(self.file_names):
            return

        selected_file = self.file_names[self.selected_index]
        selected_file_path = self.file_paths[self.selected_index]
        bookmark_type = "folder" if os.path.isdir(selected_file_path) else "file"

        folders = [name for name in os.listdir(self.bookmarks_folder) if os.path.isdir(os.path.join(self.bookmarks_folder, name))]

        def show_folders_dialog():
            dialog = tk.Toplevel(self)
            dialog.title("Select or Create Bookmark Folder")
            dialog.configure(bg='dark blue')
            dialog.geometry("400x400")
            dialog.transient(self)
            dialog.grab_set()
            dialog.update_idletasks()

            x = (self.winfo_rootx() + (self.winfo_width() // 2)) - (dialog.winfo_width() // 2)
            y = (self.winfo_rooty() + (self.winfo_height() // 2)) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")

            frame = tk.Frame(dialog, bg='dark blue')
            frame.pack(fill="both", expand=True)

            tk.Label(frame, text="Select a folder to save the bookmark in:", bg='light blue').pack(pady=5)

            tk.Button(frame, text="Bookmarks Root", command=lambda: save_bookmark("")).pack(fill=tk.X, pady=2)

            for folder in folders:
                tk.Button(frame, text=folder, command=lambda folder=folder: save_bookmark(folder)).pack(fill=tk.X, pady=2)

            ttk_button = Button(frame, text="Create New Folder", command=lambda: create_new_folder_in_dialog(dialog), bootstyle="secondary")
            ttk_button.pack(fill=tk.X, pady=5)

            ttk_close = Button(frame, text="Close", command=dialog.destroy, bootstyle="danger")
            ttk_close.pack(fill=tk.X, pady=5)

        def create_new_folder_in_dialog(dialog):
            dialog.destroy()  # Close the current dialog

            #os.system(self.matchbox_keyboard_command)  # Launch Matchbox keyboard
            new_folder_name = self.create_dialog("New Folder", "Enter new folder name for bookmarks:")

            if not new_folder_name:
                return

            folder_path = os.path.join(self.bookmarks_folder, new_folder_name)
            os.makedirs(folder_path, exist_ok=True)
            save_bookmark(new_folder_name)

        def save_bookmark(folder_name):
            folder_path = os.path.join(self.bookmarks_folder, folder_name)
            os.makedirs(folder_path, exist_ok=True)

            try:
                link_name = os.path.join(folder_path, os.path.basename(selected_file))
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


    def create_dialog(self, title, prompt):
        dialog = InputDialog(self, title=title, prompt=prompt)
        self.wait_window(dialog)
        return dialog.result

    def populate_files(self, files):
        self.file_names = [os.path.basename(fp) for fp in files]
        self.file_paths = files
        self.selected_index = 0
        self.offset_y = 0
        logging.debug(f"Files populated: {self.file_names}, Paths: {self.file_paths}")


class InputDialog(tk.Toplevel):
    def __init__(self, parent, title=None, prompt=None):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()

        if title:
            self.title(title)

        self.result = None

        frame = tk.Frame(self)
        frame.pack(padx=20, pady=20)

        if prompt:
            tk.Label(frame, text=prompt).pack(padx=5, pady=5)

        self.entry = tk.Entry(frame)
        self.entry.pack(padx=5, pady=5)
        self.entry.focus()

        self.keyboard = Keyboard(self, self.entry)

        button_box = tk.Frame(self)
        button_box.pack()

        Button(button_box, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=10, pady=5)
        Button(button_box, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=10, pady=5)

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_cancel())

        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (480 // 2) - (width // 2)
        y = (640 // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_ok(self):
        self.result = self.entry.get()
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()


class Keyboard(tk.Toplevel):
    def __init__(self, parent, target_entry):
        super().__init__(parent)
        self.title("On-Screen Keyboard")
        self.target_entry = target_entry
        self.configure(bg='gray')
        self.config(cursor="none")
        self.resizable(False, False)
        self.create_buttons()
        self.center()
        self.attributes('-topmost', True)

    def create_buttons(self):
        layout = [
            '1 2 3 4 5 6 7 8 9 0',
            'q w e r t y u i o p',
            'a s d f g h j k l',
            'z x c v b n m',
            'Backspace Space - +'
        ]

        for row_index, row in enumerate(layout):
            frame = tk.Frame(self)
            frame.pack()

            for char in row.split():
                if char == 'Space':
                    button = Button(frame, text='␣', width=9, command=lambda c=' ': self.on_click(c) , bootstyle = "solid-toolbutton")
                elif char == 'Backspace':
                    button = Button(frame, text='Backspace', width=8, command=lambda c='Backspace': self.on_click(c), bootstyle = "solid-toolbutton")
                else:
                    button = Button(frame, text=char, width=2, command=lambda c=char: self.on_click(c), bootstyle = "solid-toolbutton")
                button.pack(side=tk.LEFT, padx=1, pady=1)

    def on_click(self, char):
        if char == "Backspace":
            current_text = self.target_entry.get()
            if current_text:
                self.target_entry.delete(len(current_text) - 1, tk.END)
        else:
            self.target_entry.insert(tk.END, char)

    def center(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (480 // 2) - (width // 2)
        y = (640 // 2) - (height // 2) + 200
        self.geometry(f"{width}x{height}+{x}+{y}")


if __name__ == '__main__':
    file_selector = FileSelector()
    file_selector.mainloop()