import tkinter
from tkinter import ttk
import customtkinter
import pandas as pd
from tkinter import filedialog, messagebox
import os
import json

# --- Set Application Appearance ---
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


# --- Helper classes for Accordion UI ---
class AccordionManager:
    """Manages the state of all accordion frames."""

    def __init__(self):
        self.frames = []
        self.currently_open = None

    def add_frame(self, frame):
        self.frames.append(frame)

    def toggle(self, frame_to_toggle):
        is_currently_open = (frame_to_toggle == self.currently_open)
        if self.currently_open:
            self.currently_open.collapse()
        if not is_currently_open:
            frame_to_toggle.expand()
            self.currently_open = frame_to_toggle
        else:
            self.currently_open = None


class AccordionFrame(customtkinter.CTkFrame):
    """A single collapsible frame for the accordion menu."""

    def __init__(self, parent, title, manager):
        super().__init__(parent, fg_color="transparent")
        self.manager = manager
        self.manager.add_frame(self)
        self.pack(fill="x", expand=True, pady=(0, 5))
        self.title_button = customtkinter.CTkButton(self, text=title, anchor="w", fg_color="gray25",
                                                    hover_color="gray35", command=self.toggle)
        self.title_button.pack(fill="x", expand=True)
        self.content_frame = customtkinter.CTkFrame(self)

    def toggle(self): self.manager.toggle(self)

    def expand(self):
        self.content_frame.pack(fill="x", expand=True, pady=(0, 5), padx=2)
        self.title_button.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

    def collapse(self):
        self.content_frame.pack_forget()
        self.title_button.configure(fg_color="gray25")


# --- Main Application Window ---
class CSVRefinerApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("CSV Refiner Pro")
        self.geometry("1400x800")
        self.df, self.original_df, self.source_file_path = None, None, None
        self.processing_pipeline = []
        self.is_streaming_mode = False

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = customtkinter.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(3, weight=1)
        customtkinter.CTkLabel(self.sidebar_frame, text="CSV Refiner",
                               font=customtkinter.CTkFont(size=20, weight="bold")).grid(row=0, column=0, columnspan=2,
                                                                                        padx=20, pady=(20, 10))

        # --- Load File Frame (with Info button) ---
        self.load_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.load_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.load_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkButton(self.load_frame, text="Load File(s)", command=self.load_files).grid(row=0, column=0,
                                                                                                    sticky="ew")
        customtkinter.CTkButton(self.load_frame, text="i", command=self.show_combine_info, width=30).grid(row=0,
                                                                                                          column=1,
                                                                                                          padx=(5, 0))

        self.mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Mode: Interactive",
                                                 font=customtkinter.CTkFont(size=12))
        self.mode_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")
        self.operations_scroll_frame = customtkinter.CTkScrollableFrame(self.sidebar_frame, label_text="Operations")

        # --- Main Frame ---
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.table_header_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.table_header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.table_header_frame.grid_columnconfigure(0, weight=1)
        self.stats_label = customtkinter.CTkLabel(self.table_header_frame, text="Load a file to begin.", anchor="w")
        self.stats_label.grid(row=0, column=0, sticky="w")
        self.download_button = customtkinter.CTkButton(self.table_header_frame, text="Save to New CSV",
                                                       command=self.save_file, state="disabled")
        self.download_button.grid(row=0, column=1, sticky="e")

        # --- Data Table ---
        self.style = ttk.Style()
        self.tree_frame = customtkinter.CTkFrame(self.main_frame, border_width=0)
        self.tree_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(self.tree_frame, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb, hsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview), ttk.Scrollbar(
            self.tree_frame, orient="horizontal", command=self.tree.xview)
        vsb.grid(row=0, column=1, sticky='ns');
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # --- Progress Bar for Streaming ---
        self.progress_bar = customtkinter.CTkProgressBar(self.main_frame)
        self.progress_label = customtkinter.CTkLabel(self.main_frame, text="")

        # --- Theme Switcher ---
        self.theme_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.theme_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="sw")
        self.theme_frame.grid_columnconfigure((0, 1), weight=1)
        customtkinter.CTkLabel(self.theme_frame, text="Theme:").pack(side="left", padx=(0, 10))
        customtkinter.CTkButton(self.theme_frame, text="Light", command=self.set_light_mode).pack(side="left",
                                                                                                  expand=True, padx=2)
        customtkinter.CTkButton(self.theme_frame, text="Dark", command=self.set_dark_mode).pack(side="left",
                                                                                                expand=True, padx=2)

        # Set the default theme upon initialization to prevent white flash
        self.set_dark_mode()

    def create_operations_widgets(self):
        """Creates the dynamic accordion menu for all operations."""
        for widget in self.operations_scroll_frame.winfo_children(): widget.destroy()
        self.operations_scroll_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.accordion_manager = AccordionManager()

        apply_text = "Add to Pipeline" if self.is_streaming_mode else "Apply"

        # Feature 1: Remove Duplicates
        dup_accordion = AccordionFrame(self.operations_scroll_frame, "1. Remove Duplicates", self.accordion_manager)
        self.unique_column_var = customtkinter.StringVar()
        self.unique_column_menu = customtkinter.CTkOptionMenu(dup_accordion.content_frame,
                                                              variable=self.unique_column_var, values=[])
        self.unique_column_menu.pack(padx=5, pady=5, fill="x")
        customtkinter.CTkButton(dup_accordion.content_frame, text=apply_text, command=self.remove_duplicates).pack(
            padx=5, pady=5, fill="x")

        # Feature 2: Filter Rows by Value
        filter_accordion = AccordionFrame(self.operations_scroll_frame, "2. Filter Rows by Value",
                                          self.accordion_manager)
        self.filter_column_var = customtkinter.StringVar()
        self.filter_column_menu = customtkinter.CTkOptionMenu(filter_accordion.content_frame,
                                                              variable=self.filter_column_var, values=[])
        self.filter_column_menu.pack(padx=5, pady=5, fill="x")
        self.filter_value_entry = customtkinter.CTkEntry(filter_accordion.content_frame,
                                                         placeholder_text="Value to remove")
        self.filter_value_entry.pack(padx=5, pady=5, fill="x")
        customtkinter.CTkButton(filter_accordion.content_frame, text=apply_text, command=self.filter_rows).pack(padx=5,
                                                                                                                pady=5,
                                                                                                                fill="x")

        # New Feature: Filter by Column Match
        filter_match_accordion = AccordionFrame(self.operations_scroll_frame, "3. Filter by Column Match",
                                                self.accordion_manager)
        customtkinter.CTkLabel(filter_match_accordion.content_frame,
                               text="Remove rows where values in two columns are identical.").pack(padx=5, pady=5)
        self.match_col1_var = customtkinter.StringVar()
        self.match_col2_var = customtkinter.StringVar()
        customtkinter.CTkLabel(filter_match_accordion.content_frame, text="Column 1:").pack(padx=5, anchor="w")
        self.match_col1_menu = customtkinter.CTkOptionMenu(filter_match_accordion.content_frame,
                                                           variable=self.match_col1_var, values=[])
        self.match_col1_menu.pack(padx=5, pady=(0, 5), fill="x")
        customtkinter.CTkLabel(filter_match_accordion.content_frame, text="Column 2:").pack(padx=5, anchor="w")
        self.match_col2_menu = customtkinter.CTkOptionMenu(filter_match_accordion.content_frame,
                                                           variable=self.match_col2_var, values=[])
        self.match_col2_menu.pack(padx=5, pady=(0, 5), fill="x")
        customtkinter.CTkButton(filter_match_accordion.content_frame, text=apply_text,
                                command=self.filter_by_column_match).pack(padx=5, pady=5, fill="x")

        # Feature 3: Drop Columns
        drop_accordion = AccordionFrame(self.operations_scroll_frame, "4. Drop Columns", self.accordion_manager)
        self.drop_col_checkboxes = {}
        self.drop_col_scroll_frame = customtkinter.CTkScrollableFrame(drop_accordion.content_frame, height=150)
        self.drop_col_scroll_frame.pack(fill="x", expand=True, padx=5, pady=5)
        customtkinter.CTkButton(drop_accordion.content_frame, text=apply_text, command=self.drop_column).pack(padx=5,
                                                                                                              pady=5,
                                                                                                              fill="x")

        # Features 4, 5, 6: Replace Values
        replace_accordion = AccordionFrame(self.operations_scroll_frame, "5. Replace Values", self.accordion_manager)
        self.replace_column_var = customtkinter.StringVar()
        self.replace_column_menu = customtkinter.CTkOptionMenu(replace_accordion.content_frame,
                                                               variable=self.replace_column_var, values=[],
                                                               dynamic_resizing=False)
        self.replace_column_menu.pack(padx=5, pady=5, fill="x")
        self.old_value_entry = customtkinter.CTkEntry(replace_accordion.content_frame, placeholder_text="Old Value")
        self.old_value_entry.pack(padx=5, pady=5, fill="x")
        self.new_value_entry = customtkinter.CTkEntry(replace_accordion.content_frame, placeholder_text="New Value")
        self.new_value_entry.pack(padx=5, pady=5, fill="x")
        self.replace_all_var = customtkinter.StringVar(value="off")
        customtkinter.CTkCheckBox(replace_accordion.content_frame, text="Replace in all columns",
                                  variable=self.replace_all_var, onvalue="on", offvalue="off").pack(padx=5, pady=5,
                                                                                                    anchor="w")
        self.substring_var = customtkinter.StringVar(value="off")
        customtkinter.CTkCheckBox(replace_accordion.content_frame, text="Replace as substring",
                                  variable=self.substring_var, onvalue="on", offvalue="off").pack(padx=5, pady=5,
                                                                                                  anchor="w")
        customtkinter.CTkButton(replace_accordion.content_frame, text=apply_text, command=self.replace_values).pack(
            padx=5, pady=5, fill="x")

        # Feature 9: Extract Column
        extract_accordion = AccordionFrame(self.operations_scroll_frame, "6. Extract Column", self.accordion_manager)
        self.extract_column_var = customtkinter.StringVar()
        self.extract_column_menu = customtkinter.CTkOptionMenu(extract_accordion.content_frame,
                                                               variable=self.extract_column_var, values=[])
        self.extract_column_menu.pack(padx=5, pady=5, fill="x")
        customtkinter.CTkButton(extract_accordion.content_frame, text="Extract & Save",
                                command=self.extract_column).pack(padx=5, pady=5, fill="x")

        # New Feature 7: Convert to JSON
        json_accordion = AccordionFrame(self.operations_scroll_frame, "7. Convert to JSON", self.accordion_manager)
        customtkinter.CTkLabel(json_accordion.content_frame, text="Convert the final data to a JSON file.").pack(padx=5,
                                                                                                                 pady=5)
        customtkinter.CTkLabel(json_accordion.content_frame, text="Note: This is a final export action.",
                               font=customtkinter.CTkFont(size=10)).pack(padx=5, pady=(0, 10))
        customtkinter.CTkButton(json_accordion.content_frame, text="Convert & Save to JSON",
                                command=self.convert_and_save_json).pack(padx=5, pady=5, fill="x")

        self.reset_button = customtkinter.CTkButton(self.sidebar_frame, text="Reset All Changes",
                                                    command=self.reset_data, fg_color="#D32F2F", hover_color="#B71C1C")
        self.reset_button.grid(row=4, column=0, columnspan=2, padx=20, pady=20, sticky="sew")

    def load_files(self):
        file_paths = filedialog.askopenfilenames(title="Select CSV or Text File(s)",
                                                 filetypes=(("CSV/Text files", "*.csv *.txt"), ("All files", "*.*")))
        if not file_paths: return
        self.source_file_path = file_paths[0]
        file_size_mb = os.path.getsize(self.source_file_path) / (1024 * 1024)
        self.is_streaming_mode = file_size_mb > 200 or len(file_paths) > 1

        try:
            if len(file_paths) > 1:  # Combine Files
                messagebox.showinfo("Combine Files", f"{len(file_paths)} files will be combined in Streaming Mode.")
                self.source_file_path = file_paths
                with open(file_paths[0], 'r', errors='ignore') as f:
                    preview_df = pd.read_csv(f)
                    self.df = preview_df.head(100)  # Load only a preview
            else:  # Single file
                if not self.is_streaming_mode:
                    self.df = pd.read_csv(self.source_file_path)
                else:
                    messagebox.showinfo("Large File Mode",
                                        "Large file detected. Switched to Streaming Mode. Only a preview is shown.")
                    self.df = pd.read_csv(self.source_file_path, nrows=500)

            self.original_df = self.df.copy() if not self.is_streaming_mode else None
            self.update_ui_on_new_file()
        except Exception:
            self.handle_parsing_error()

    def handle_parsing_error(self):
        """Handles cases where standard CSV parsing fails."""
        dialog = DelimiterDialog(self)
        self.wait_window(dialog)
        options = dialog.get_options()
        if not (options and options["delimiter"]): return

        header_option = 0 if options["header"] else None
        try:
            if not self.is_streaming_mode:
                self.df = pd.read_csv(self.source_file_path, delimiter=options["delimiter"], header=header_option,
                                      engine='python')
            else:
                self.df = pd.read_csv(self.source_file_path, delimiter=options["delimiter"], header=header_option,
                                      engine='python', nrows=500)

            self.original_df = self.df.copy() if not self.is_streaming_mode else None
            self.update_ui_on_new_file()
            messagebox.showinfo("Text File Converted", "Text file was successfully parsed.")
        except Exception as e:
            messagebox.showerror("Parsing Error", f"Could not parse file with the specified options.\nError: {e}")

    def update_ui_on_new_file(self):
        self.mode_label.configure(text=f"Mode: {'Streaming' if self.is_streaming_mode else 'Interactive'}")
        self.create_operations_widgets()
        self.update_table()
        self.download_button.configure(state="normal")
        columns = list(self.df.columns)
        if not columns: return

        # Populate standard option menus
        menus_to_populate = [
            (self.unique_column_menu, self.unique_column_var),
            (self.filter_column_menu, self.filter_column_var),
            (self.match_col1_menu, self.match_col1_var),
            (self.match_col2_menu, self.match_col2_var),
            (self.replace_column_menu, self.replace_column_var),
            (self.extract_column_menu, self.extract_column_var)
        ]
        for menu, var in menus_to_populate:
            menu.configure(values=columns)
            if columns: var.set(columns[0])

        # Populate multi-select checklist for dropping columns
        for widget in self.drop_col_scroll_frame.winfo_children(): widget.destroy()
        self.drop_col_checkboxes = {}
        for col in columns:
            var = customtkinter.StringVar(value="off")
            cb = customtkinter.CTkCheckBox(self.drop_col_scroll_frame, text=col, variable=var, onvalue="on",
                                           offvalue="off")
            cb.pack(padx=10, pady=2, anchor="w")
            self.drop_col_checkboxes[col] = var

    def update_table(self):
        self.tree.delete(*self.tree.get_children())
        if self.df is None: return self.stats_label.configure(text="Load a file to begin.")
        self.tree["columns"] = list(self.df.columns)
        for col in self.df.columns:
            self.tree.heading(col, text=col, anchor='w')
            self.tree.column(col, width=120, anchor='w')
        for _, row in self.df.iterrows():
            self.tree.insert("", "end", values=[str(v) for v in row.values])
        if not self.is_streaming_mode:
            rows, cols = self.df.shape
            self.stats_label.configure(text=f"{rows} rows, {cols} columns")
        else:
            self.stats_label.configure(text=f"Showing preview ({len(self.df)} rows), {len(self.df.columns)} columns")

    def reset_data(self):
        if self.is_streaming_mode:
            self.processing_pipeline.clear()
            messagebox.showinfo("Pipeline Cleared", "All queued operations have been cleared.")
        elif self.original_df is not None and messagebox.askyesno("Confirm Reset", "Discard all changes?"):
            self.df = self.original_df.copy()
            self.update_ui_on_new_file()
            messagebox.showinfo("Success", "Data has been reset to its original state.")

    def save_file(self):
        if self.df is None: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
                                                 title="Save Refined File")
        if not file_path: return
        if self.is_streaming_mode:
            self.run_processing_pipeline(file_path)
        else:
            try:
                self.df.to_csv(file_path, index=False)
                messagebox.showinfo("Success", f"File saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error Saving File", f"An error occurred: {e}")

    def add_to_pipeline(self, op_name, params):
        self.processing_pipeline.append({'op': op_name, 'params': params})
        messagebox.showinfo("Pipeline Updated", f"Operation '{op_name}' added to the processing pipeline.")

    # --- UI Helpers ---
    def show_combine_info(self):
        messagebox.showinfo("Combine Files Info",
                            "To combine files, click 'Load File(s)' and select multiple files in the dialog box.\n\nThe application will automatically enter Streaming Mode to handle the combined data.")

    def set_light_mode(self):
        customtkinter.set_appearance_mode("light")
        self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
        self.style.configure("Treeview.Heading", background="#E1E1E1", foreground="black", relief="flat")
        self.style.map("Treeview.Heading", background=[('active', '#D1D1D1')])

    def set_dark_mode(self):
        customtkinter.set_appearance_mode("dark")
        self.style.configure("Treeview", background="#2B2B2B", foreground="white", fieldbackground="#2B2B2B")
        self.style.configure("Treeview.Heading", background="#3C3C3C", foreground="white", relief="flat")
        self.style.map("Treeview.Heading", background=[('active', '#565656')])

    # --- Operation Handlers ---
    def remove_duplicates(self):
        params = {'subset': [self.unique_column_var.get()], 'keep': 'first'}
        if self.is_streaming_mode: self.add_to_pipeline('drop_duplicates', params); return
        initial_rows = len(self.df)
        self.df.drop_duplicates(**params, inplace=True)
        messagebox.showinfo("Success", f"{initial_rows - len(self.df)} duplicate rows removed.")
        self.update_table()

    def filter_rows(self):
        column = self.filter_column_var.get()
        value = self.filter_value_entry.get()
        if not value: return messagebox.showwarning("Input Needed", "Please enter a value to filter by.")

        value_exists = self.df[column].astype(str).str.lower().eq(value.lower()).any()
        if not value_exists and not self.is_streaming_mode:
            messagebox.showinfo("Not Found", f"Value '{value}' not found in column '{column}'. 0 rows affected.")
            return

        params = {'column': column, 'value': value}
        if self.is_streaming_mode: self.add_to_pipeline('filter_rows', params); return

        initial_rows = len(self.df)
        self.df = self.df[self.df[params['column']].astype(str).str.lower() != params['value'].lower()]
        messagebox.showinfo("Success", f"{initial_rows - len(self.df)} rows removed.")
        self.update_table()

    def filter_by_column_match(self):
        col1 = self.match_col1_var.get()
        col2 = self.match_col2_var.get()
        if col1 == col2:
            messagebox.showwarning("Invalid Selection", "Please select two different columns to compare.")
            return

        params = {'col1': col1, 'col2': col2}
        if self.is_streaming_mode: self.add_to_pipeline('filter_by_column_match', params); return

        initial_rows = len(self.df)
        self.df = self.df[self.df[col1] != self.df[col2]]
        rows_removed = initial_rows - len(self.df)
        messagebox.showinfo("Success", f"{rows_removed} rows removed where '{col1}' matched '{col2}'.")
        self.update_table()

    def drop_column(self):
        columns_to_drop = [col for col, var in self.drop_col_checkboxes.items() if var.get() == "on"]
        if not columns_to_drop:
            messagebox.showwarning("No Selection", "Please select at least one column to drop.")
            return

        if not messagebox.askyesno("Confirm Drop",
                                   f"Are you sure you want to permanently drop {len(columns_to_drop)} column(s)?\n\n({', '.join(columns_to_drop)})"):
            return

        params = {'columns': columns_to_drop}
        if self.is_streaming_mode: self.add_to_pipeline('drop_column', params); return

        self.df.drop(**params, inplace=True, axis=1)
        messagebox.showinfo("Success", f"Successfully dropped {len(columns_to_drop)} column(s).")
        self.update_ui_on_new_file()

    def replace_values(self):
        old_val, new_val = self.old_value_entry.get(), self.new_value_entry.get()
        if not old_val: return messagebox.showwarning("Input Needed", "Please provide the 'Old Value' to replace.")
        params = {'old': old_val, 'new': new_val, 'all_cols': self.replace_all_var.get() == "on",
                  'is_substr': self.substring_var.get() == "on", 'col': self.replace_column_var.get()}
        if self.is_streaming_mode: self.add_to_pipeline('replace_values', params); return
        cols_to_scan = list(self.df.columns) if params['all_cols'] else [params['col']]
        total_replacements = 0
        for col in cols_to_scan:
            mask = self.df[col].astype(str).str.contains(params['old'], na=False) if params['is_substr'] else self.df[
                                                                                                                  col].astype(
                str).str.lower() == params['old'].lower()
            total_replacements += mask.sum()
            if params['is_substr']:
                self.df[col] = self.df[col].astype(str).str.replace(params['old'], params['new'])
            else:
                self.df.loc[mask, col] = params['new']
        messagebox.showinfo("Success", f"{total_replacements} value(s) replaced.")
        self.update_table()

    def extract_column(self):
        column = self.extract_column_var.get()
        params = {'column': column}
        if self.is_streaming_mode:
            messagebox.showinfo("Info",
                                "Extract Column in Streaming mode will create a separate file during processing.")
            self.add_to_pipeline('extract_column', params)
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"extracted_{column}.csv",
                                                 filetypes=[("CSV files", "*.csv")], title="Save Extracted Column")
        if not file_path: return
        try:
            self.df[[column]].to_csv(file_path, index=False)
            messagebox.showinfo("Success", f"Column '{column}' extracted and saved.")
        except Exception as e:
            messagebox.showerror("Error Saving File", f"An error occurred: {e}")

    def run_processing_pipeline(self, output_path):
        if not self.processing_pipeline: return messagebox.showwarning("Empty Pipeline",
                                                                       "No operations have been added to the pipeline.")

        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        self.progress_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        self.progress_bar.set(0)

        chunksize = 10 ** 6

        try:
            files_to_process = self.source_file_path if isinstance(self.source_file_path, list) else [
                self.source_file_path]
            total_rows = sum(sum(1 for row in open(f, 'r', errors='ignore')) for f in files_to_process)
            rows_processed = 0

            with open(output_path, 'w', newline='', encoding='utf-8') as f_out:
                is_header = True

                for file_path in files_to_process:
                    reader = pd.read_csv(file_path, chunksize=chunksize, iterator=True)
                    for chunk in reader:
                        for op in self.processing_pipeline:
                            params = op['params']
                            if op['op'] == 'drop_duplicates':
                                chunk.drop_duplicates(**params, inplace=True)
                            elif op['op'] == 'filter_rows':
                                chunk = chunk[
                                    chunk[params['column']].astype(str).str.lower() != params['value'].lower()]
                            elif op['op'] == 'filter_by_column_match':
                                chunk = chunk[chunk[params['col1']] != chunk[params['col2']]]
                            elif op['op'] == 'drop_column':
                                chunk.drop(**params, inplace=True, axis=1)
                            elif op['op'] == 'replace_values':
                                cols = list(chunk.columns) if params['all_cols'] else [params['col']]
                                for col in cols:
                                    if params['is_substr']:
                                        chunk[col] = chunk[col].astype(str).str.replace(params['old'], params['new'])
                                    else:
                                        chunk.loc[chunk[col].astype(str).str.lower() == params['old'].lower(), col] = \
                                        params['new']
                            elif op['op'] == 'extract_column':
                                extracted_path = os.path.join(os.path.dirname(output_path),
                                                              f"extracted_{params['column']}.csv")
                                chunk[[params['column']]].to_csv(extracted_path, mode='a', header=is_header,
                                                                 index=False)

                        chunk.to_csv(f_out, header=is_header, index=False)
                        is_header = False

                        rows_processed += len(chunk)
                        progress = rows_processed / total_rows if total_rows > 0 else 0
                        self.progress_bar.set(progress)
                        self.progress_label.configure(text=f"Processing... {rows_processed:,} / {total_rows:,} rows")
                        self.update_idletasks()

            messagebox.showinfo("Processing Complete", f"Successfully processed and saved file to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during streaming:\n{e}")
        finally:
            self.progress_bar.grid_forget()
            self.progress_label.grid_forget()

    def convert_and_save_json(self):
        """Handles the logic for converting the current data (interactive or streaming) to JSON."""
        if self.df is None:
            messagebox.showwarning("No Data", "Please load a file first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Convert and Save to JSON"
        )
        if not file_path:
            return

        if self.is_streaming_mode:
            # For streaming mode, run the full pipeline and convert chunk by chunk
            self.run_json_pipeline(file_path)
        else:
            # For interactive mode, convert the in-memory DataFrame
            try:
                records = self.df.to_dict('records')
                json_data = []
                for row_dict in records:
                    cleaned_dict = {}
                    for key, value in row_dict.items():
                        # Skip keys with None, NaN, or empty/whitespace values
                        if value is not None and pd.notna(value) and str(value).strip() != '':
                            cleaned_dict[str(key).strip()] = str(value).strip()

                    if cleaned_dict:
                        json_data.append(cleaned_dict)

                with open(file_path, 'w', encoding='utf-8') as f_out:
                    json.dump(json_data, f_out, indent=2, ensure_ascii=False)

                messagebox.showinfo("Success", f"Successfully converted and saved file to:\n{file_path}")

            except Exception as e:
                messagebox.showerror("Error During JSON Conversion", f"An error occurred: {e}")

    def run_json_pipeline(self, output_path):
        """
        Processes source files in chunks, applies the operation pipeline,
        and saves the final output as a single, well-formatted JSON file.
        """
        if self.is_streaming_mode and not self.processing_pipeline:
            if not messagebox.askyesno("Empty Pipeline",
                                       "No operations are in the pipeline. Do you want to convert the original file(s) to JSON directly?"):
                return

        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        self.progress_label.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=5)
        self.progress_bar.set(0)

        chunksize = 10 ** 6

        try:
            files_to_process = self.source_file_path if isinstance(self.source_file_path, list) else [
                self.source_file_path]
            total_rows = sum(sum(1 for row in open(f, 'r', errors='ignore')) for f in files_to_process)
            rows_processed = 0
            first_record_written = False

            with open(output_path, 'w', encoding='utf-8') as f_out:
                f_out.write('[\n')  # Start of the JSON array

                for file_path in files_to_process:
                    reader = pd.read_csv(file_path, chunksize=chunksize, iterator=True)
                    for chunk in reader:
                        # 1. Apply all existing operations from the pipeline
                        for op in self.processing_pipeline:
                            params = op['params']
                            if op['op'] == 'drop_duplicates':
                                chunk.drop_duplicates(**params, inplace=True)
                            elif op['op'] == 'filter_rows':
                                chunk = chunk[
                                    chunk[params['column']].astype(str).str.lower() != params['value'].lower()]
                            elif op['op'] == 'filter_by_column_match':
                                chunk = chunk[chunk[params['col1']] != chunk[params['col2']]]
                            elif op['op'] == 'drop_column':
                                chunk.drop(**params, inplace=True, axis=1)
                            elif op['op'] == 'replace_values':
                                cols = list(chunk.columns) if params['all_cols'] else [params['col']]
                                for col in cols:
                                    if params['is_substr']:
                                        chunk[col] = chunk[col].astype(str).str.replace(params['old'], params['new'])
                                    else:
                                        chunk.loc[chunk[col].astype(str).str.lower() == params['old'].lower(), col] = \
                                        params['new']

                        # 2. Convert the processed chunk to clean JSON records
                        records = chunk.to_dict('records')
                        for row_dict in records:
                            cleaned_dict = {}
                            for key, value in row_dict.items():
                                if value is not None and pd.notna(value) and str(value).strip() != '':
                                    cleaned_dict[str(key).strip()] = str(value).strip()

                            if cleaned_dict:
                                if first_record_written:
                                    f_out.write(',\n')

                                json.dump(cleaned_dict, f_out, indent=2)
                                first_record_written = True

                        # 3. Update progress
                        rows_processed += len(chunk)
                        progress = rows_processed / total_rows if total_rows > 0 else 0
                        self.progress_bar.set(progress)
                        self.progress_label.configure(text=f"Processing... {rows_processed:,} / {total_rows:,} rows")
                        self.update_idletasks()

                f_out.write('\n]')  # End of the JSON array

            messagebox.showinfo("Processing Complete", f"Successfully processed and saved JSON file to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during JSON streaming:\n{e}")
        finally:
            self.progress_bar.grid_forget()
            self.progress_label.grid_forget()


class DelimiterDialog(customtkinter.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = None
        self.title("Text File Options")
        self.geometry("350x220")
        customtkinter.CTkLabel(self, text="This looks like a text file. Please provide parsing options:").pack(padx=20,
                                                                                                               pady=10)
        self.delimiter_entry = customtkinter.CTkEntry(self, placeholder_text="Delimiter (e.g., ';' or '\\t' for tab)")
        self.delimiter_entry.pack(padx=20, pady=5, fill="x")
        self.header_var = customtkinter.StringVar(value="on")
        customtkinter.CTkCheckBox(self, text="File has a header row", variable=self.header_var, onvalue="on",
                                  offvalue="off").pack(padx=20, pady=10)
        customtkinter.CTkButton(self, text="Parse File", command=self.on_ok).pack(padx=20, pady=10)
        self.lift();
        self.attributes('-topmost', True);
        self.after(10, self.attributes, '-topmost', False)
        self.protocol("WM_DELETE_WINDOW", self.on_cancel);
        self.grab_set()

    def on_ok(self):
        self.options = {"delimiter": self.delimiter_entry.get(), "header": self.header_var.get() == "on"}
        self.grab_release();
        self.destroy()

    def on_cancel(self):
        self.options = None;
        self.grab_release();
        self.destroy()

    def get_options(self): return self.options


if __name__ == "__main__":
    app = CSVRefinerApp()
    app.mainloop()