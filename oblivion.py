import requests
import json
import time
import threading
import yaml
import logging
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, Optional
import sys
import os

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base_path, relative_path)

# Set up logging to provide clear, timestamped output in the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OblivionGUI:
    """A GUI application for sending Discord webhook pings in Normal or Switch mode."""
    
    # Default configuration values for the application
    DEFAULT_CONFIG = {
        'message': '@everyone',  # Default message content
        'username': 'Oblivion V1',  # Default username for webhook
        'avatar_url': 'https://media.discordapp.net/attachments/1329536982237319239/1375174292303773876/blob-cat-ping.gif',  # Default avatar image URL
        'delay': 2.5,  # Default delay between messages (in seconds)
        'rate_limit_backoff': 60,  # Default wait time after hitting a rate limit (in seconds)
        'max_retries': 3,  # Default maximum number of retry attempts for failed requests
        'message_limit': 9000,  # Default maximum messages per webhook
        'total_pings': 450000  # Default total pings for a shard in Switch mode
    }

    def __init__(self, root: tk.Tk, config_file: str):
        """Initialize the Oblivion V1 GUI with a config file."""
        # Set AppUserModelID for Windows taskbar icon before anything else
        if sys.platform == "win32":
            try:
                import ctypes
                myappid = 'oblivion.v1'  # Generic AppUserModelID
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception as e:
                print(f"Warning: Could not set AppUserModelID: {e}")
        self.root = root
        self.root.title("Oblivion V1")
        self.config_file = resource_path(config_file)
        
        # Load configuration and webhooks from files
        self.config = self._load_config(self.config_file)
        self.webhook_groups = self._load_webhooks(resource_path(self.config['webhooks_file']))
        
        # State variables for tracking running shards, message counts, threads, and mode
        self.shard_status = {shard: False for shard in self.webhook_groups}  # Tracks whether each shard is running
        self.message_counts = {}  # Tracks the number of messages sent per webhook URL
        self.threads = {}  # Stores threads for each shard
        self.mode = tk.StringVar(value="parallel")  # Stores the current mode: 'parallel' or 'sequential'
        self.current_switch_shard = None  # The currently active shard in Switch mode
        self.rate_limit_backoff = self.config.get('rate_limit_backoff', self.DEFAULT_CONFIG['rate_limit_backoff'])
        self.max_retries = self.config.get('max_retries', self.DEFAULT_CONFIG['max_retries'])
        self.message_limit = self.config.get('message_limit', self.DEFAULT_CONFIG['message_limit'])
        self.total_pings = self.config.get('total_pings', self.DEFAULT_CONFIG['total_pings'])
        # Define settings fields: (label, variable name, type, config key)
        self._settings_fields = [
            ("Message:", 'message_var', tk.StringVar, 'message'),
            ("Username:", 'username_var', tk.StringVar, 'username'),
            ("Avatar URL:", 'avatar_var', tk.StringVar, 'avatar_url'),
            ("Delay (seconds):", 'delay_var', tk.DoubleVar, 'delay'),
            ("Rate Limit Backoff (seconds):", 'backoff_var', tk.DoubleVar, 'rate_limit_backoff'),
            ("Max Retries:", 'retries_var', tk.IntVar, 'max_retries'),
            ("Message Limit per Webhook:", 'limit_var', tk.IntVar, 'message_limit'),
            ("Total Pings per Shard (Sequential Mode):", 'total_pings_var', tk.IntVar, 'total_pings'),
        ]
        # Create all settings variables as attributes
        for _, varname, vartype, key in self._settings_fields:
            value = self.config.get(key, self.DEFAULT_CONFIG[key])
            setattr(self, varname, vartype(value=value))
        # Set the window and taskbar icon
        self._set_window_icon(resource_path("icon.ico"))
        
        # Load themes from JSON
        self.themes = self._load_themes(resource_path('themes.json'))
        self.theme_options = ["Default"] + sorted(self.themes.keys()) + ["Custom"]
        self.theme_var = tk.StringVar(value='Default')
        self.config['theme'] = self.config.get('theme', 'Default')
        
        # Build the GUI layout and widgets
        self._setup_gui()

    def _load_file_with_error_handling(self, path, loader, filetype):
        """Generic file loader with error handling for config and webhooks."""
        try:
            with open(path, 'r') as file:
                data = loader(file)
                if not data:
                    raise ValueError(f"Empty {filetype} file")
                return data
        except FileNotFoundError:
            logger.error(f"{filetype.capitalize()} file {path} not found")
            messagebox.showerror("Error", f"{filetype.capitalize()} file {path} not found")
            exit(1)
        except Exception as e:
            logger.error(f"Invalid {filetype} in {path}: {e}")
            messagebox.showerror("Error", f"Invalid {filetype} in {path}: {e}")
            exit(1)

    def _load_config(self, config_file: str) -> Dict:
        """Load and validate the YAML configuration file. Show an error and exit if invalid."""
        return self._load_file_with_error_handling(config_file, yaml.safe_load, "config")

    def _load_webhooks(self, json_file: str) -> Dict:
        """Load and validate webhook groups from a JSON file. Show an error and exit if invalid."""
        return self._load_file_with_error_handling(json_file, json.load, "webhook")

    def _load_themes(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load themes from {path}: {e}")
            return {}

    def _set_window_icon(self, icon_path: str):
        """Set the window and taskbar icon. Show a warning if the icon cannot be loaded."""
        try:
            if sys.platform == "win32":
                self.root.iconbitmap(icon_path)
            else:
                # For other platforms, fallback to PhotoImage if possible
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
            logger.info(f"Loaded icon: {icon_path}")
        except Exception as e:
            logger.warning(f"Failed to load icon {icon_path}: {e}")
            messagebox.showwarning("Warning", f"Failed to load icon: {e}")

    def _setup_gui(self):
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # Create a notebook widget to hold the different tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, columnspan=3, sticky="nsew", pady=5)

        # Control tab: for selecting shards and mode
        self.control_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.control_tab, text="Control")
        self._setup_control_tab()

        # Settings tab: for configuring message and other parameters
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        self._setup_settings_tab()

        # Info tab: for guidelines, license, and warnings
        self.info_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.info_tab, text="Info")
        self._setup_info_tab()

        # Log display: shows logs in a scrollable text widget
        self.log_text = scrolledtext.ScrolledText(self.main_frame, height=10, width=60, state='disabled')
        self.log_text.grid(row=1, column=0, columnspan=3, pady=10, sticky="ew")
        logger.addHandler(TextHandler(self.log_text))

        # Button to hide/show logs
        self.toggle_logs_button = ttk.Button(self.main_frame, text="Hide Logs", command=self._toggle_logs)
        self.toggle_logs_button.grid(row=2, column=0, columnspan=3, pady=2, sticky="ew")
        self.logs_visible = True

        # Footer label: credits the author
        footer_label = ttk.Label(self.main_frame, text="Created with ♥ by @Sewaeth")
        footer_label.grid(row=3, column=0, columnspan=3, pady=5, sticky=tk.S)

        # Configure grid weights for responsive resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # Now that all widgets and variables are initialized, apply the theme
        theme = self.config.get('theme', 'Default')
        self._apply_theme(theme)

    def _set_start_stop_state(self, start_enabled: bool, stop_enabled: bool):
        """Helper to set the state of start and stop buttons."""
        self.start_button.config(state="normal" if start_enabled else "disabled")
        self.stop_button.config(state="normal" if stop_enabled else "disabled")

    def _setup_control_tab(self):
        """Set up the Control tab, including mode selection, shard selection, and control buttons."""
        # Mode selection dropdown (Parallel or Sequential)
        ttk.Label(self.control_tab, text="Mode:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        # Use a mapping for display names to internal values
        self.mode_display_map = {"Parallel": "parallel", "Sequential": "sequential"}
        self.mode_reverse_map = {v: k for k, v in self.mode_display_map.items()}
        mode_combo = ttk.Combobox(
            self.control_tab,
            textvariable=tk.StringVar(value=self.mode_reverse_map[self.mode.get()]),
            state="readonly",
            values=list(self.mode_display_map.keys())
        )
        mode_combo.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        def on_mode_selected(event):
            selected_display = mode_combo.get()
            self.mode.set(self.mode_display_map[selected_display])
            self._update_shard_ui()
        mode_combo.bind("<<ComboboxSelected>>", on_mode_selected)
        # Set the initial value
        mode_combo.set(self.mode_reverse_map[self.mode.get()])
        self.mode_combo = mode_combo

        # Frame for shard selection widgets
        self.shard_frame = ttk.LabelFrame(self.control_tab, text="Shards", padding="5")
        self.shard_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5, padx=5)

        # Status label for Switch mode (shows current shard and progress)
        self.switch_status_var = tk.StringVar(value="Sequential Mode: Idle")
        self.switch_status_label = ttk.Label(self.control_tab, textvariable=self.switch_status_var)
        self.switch_status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)

        # Start and Stop buttons for controlling the process
        self.start_button = ttk.Button(self.control_tab, text="Start", command=self._start_action)
        self.start_button.grid(row=3, column=0, pady=10, padx=5)
        self.stop_button = ttk.Button(self.control_tab, text="Kill", command=self._kill_action, state="disabled")
        self.stop_button.grid(row=3, column=1, pady=10, padx=5)

        # Initialize the shard selection UI
        self._update_shard_ui()

        # Make the second column expand to fill available space
        self.control_tab.columnconfigure(1, weight=1)

    def _setup_settings_tab(self):
        """Set up the Settings tab with configuration fields and action buttons."""
        def add_row(frame, label, var, row):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew", pady=3, padx=5)
        # Ping Farm Settings
        ping_frame = ttk.LabelFrame(self.settings_tab, text="Ping Farm Settings", padding="10")
        ping_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
        essentials = [0, 1, 2, 3, 7]
        for idx, (label, varname, _, _) in enumerate(self._settings_fields):
            if idx in essentials:
                add_row(ping_frame, label, getattr(self, varname), idx)
        ping_frame.columnconfigure(1, weight=1)
        # Advanced Options
        self.advanced_visible = tk.BooleanVar(value=False)
        def toggle_advanced():
            self.advanced_visible.set(not self.advanced_visible.get())
            if self.advanced_visible.get():
                advanced_frame.grid()
                adv_btn.config(text="Hide Advanced Options")
            else:
                advanced_frame.grid_remove()
                adv_btn.config(text="Show Advanced Options")
        adv_btn = ttk.Button(self.settings_tab, text="Show Advanced Options", command=toggle_advanced)
        adv_btn.grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        advanced_frame = ttk.LabelFrame(self.settings_tab, text="Advanced Options", padding="10")
        advanced_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
        advanced_frame.grid_remove()
        for i, idx in enumerate([4, 5, 6]):
            label, varname, _, _ = self._settings_fields[idx]
            add_row(advanced_frame, label, getattr(self, varname), i)
        advanced_frame.columnconfigure(1, weight=1)
        # Preferences
        pref_frame = ttk.LabelFrame(self.settings_tab, text="Preferences", padding="10")
        pref_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
        ttk.Label(pref_frame, text="Theme:").grid(row=0, column=0, sticky=tk.W, pady=3, padx=5)
        theme_combo = ttk.Combobox(pref_frame, textvariable=self.theme_var, state="readonly", values=self.theme_options)
        theme_combo.grid(row=0, column=1, sticky="ew", pady=3, padx=5)
        theme_combo.bind("<<ComboboxSelected>>", lambda e: self._on_theme_selected())
        pref_frame.columnconfigure(1, weight=1)
        self.custom_color_vars = {
            'bg': tk.StringVar(value=self.config.get('custom_theme', {}).get('bg', '#181818')),
            'fg': tk.StringVar(value=self.config.get('custom_theme', {}).get('fg', '#f8f8f2')),
            'accent': tk.StringVar(value=self.config.get('custom_theme', {}).get('accent', '#6c3483')),
            'entry_bg': tk.StringVar(value=self.config.get('custom_theme', {}).get('entry_bg', '#23272e')),
            'entry_fg': tk.StringVar(value=self.config.get('custom_theme', {}).get('entry_fg', '#f8f8f2')),
        }
        self.custom_color_labels = {}
        self.custom_color_entries = {}
        row = 1
        for key, label in zip(['bg', 'fg', 'accent', 'entry_bg', 'entry_fg'], ["Background", "Foreground", "Accent", "Entry Background", "Entry Foreground"]):
            lbl = ttk.Label(pref_frame, text=label+':')
            ent = ttk.Entry(pref_frame, textvariable=self.custom_color_vars[key], width=10)
            self.custom_color_labels[key] = lbl
            self.custom_color_entries[key] = ent
            lbl.grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
            ent.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
            ent.bind('<KeyRelease>', lambda e: self._apply_custom_theme(save=True))
            row += 1
        self._show_hide_custom_colors()
        # Save/Reset buttons
        button_frame = ttk.Frame(self.settings_tab)
        button_frame.grid(row=4, column=1, sticky=tk.E, pady=10, padx=5)
        ttk.Button(button_frame, text="Save Config", command=self._save_config).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Reset to Default", command=self._reset_config).grid(row=0, column=1, padx=5)
        self.settings_tab.columnconfigure(1, weight=1)
        # Manage Shards (add/delete) in settings, side by side
        self._setup_manage_shards_in_settings(self.settings_tab)

    def _on_theme_selected(self):
        self._show_hide_custom_colors()
        self._apply_theme(self.theme_var.get(), save=True)

    def _show_hide_custom_colors(self):
        show = self.theme_var.get() == 'Custom'
        for key in self.custom_color_labels:
            if show:
                self.custom_color_labels[key].grid()
                self.custom_color_entries[key].grid()
            else:
                self.custom_color_labels[key].grid_remove()
                self.custom_color_entries[key].grid_remove()
        if show:
            self._apply_custom_theme(save=False)

    def _apply_theme(self, theme_name, save=False):
        if theme_name == "Default":
            self._apply_default_theme()
        elif theme_name == "Custom":
            self._apply_custom_theme(save=save)
        elif theme_name in self.themes:
            self._apply_json_theme(theme_name)
        else:
            self._apply_default_theme()
        if save:
            self.config['theme'] = theme_name
        self._refresh_theme_widgets()

    def _apply_json_theme(self, theme_name):
        style = ttk.Style()
        style.theme_use('clam')
        t = self.themes[theme_name]
        bg = t['bg']
        fg = t['fg']
        accent = t['accent']
        entry_bg = t['entry_bg']
        entry_fg = t['entry_fg']
        button_bg = t.get('button_bg', entry_bg)
        button_fg = t.get('button_fg', entry_fg)
        style.configure('.', background=bg, foreground=fg)
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, foreground=fg)
        style.configure('TButton', background=button_bg, foreground=button_fg, borderwidth=1, focusthickness=2, focuscolor=accent)
        style.map('TButton',
            background=[('active', button_bg), ('pressed', accent), ('!active', button_bg)],
            foreground=[('active', button_fg), ('pressed', button_fg), ('!active', button_fg)])
        style.configure('TCheckbutton', background=bg, foreground=fg, indicatorcolor=accent, indicatordiameter=12, bordercolor=accent, focuscolor=accent)
        style.map('TCheckbutton',
            background=[('active', bg), ('selected', bg), ('!active', bg)],
            foreground=[('active', fg), ('selected', fg), ('!active', fg)])
        style.configure('TNotebook', background=bg)
        style.configure('TNotebook.Tab', background=button_bg, foreground=button_fg, lightcolor=accent, borderwidth=0)
        style.map('TNotebook.Tab',
            background=[('selected', accent), ('active', button_bg), ('!selected', button_bg)],
            foreground=[('selected', fg), ('active', fg), ('!selected', button_fg)])
        style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg, background=entry_bg, bordercolor=accent, lightcolor=accent, darkcolor=bg, highlightcolor=accent, selectbackground=accent, selectforeground=button_fg)
        style.map('TEntry',
            fieldbackground=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            background=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            foreground=[('readonly', entry_fg), ('!readonly', entry_fg), ('active', entry_fg)],
            bordercolor=[('focus', accent), ('!focus', accent)],
            highlightcolor=[('focus', accent), ('!focus', accent)])
        style.configure('TCombobox', fieldbackground=entry_bg, foreground=entry_fg, background=entry_bg, selectbackground=entry_bg, selectforeground=entry_fg, bordercolor=accent, lightcolor=accent, darkcolor=bg, highlightcolor=accent)
        style.map('TCombobox',
            fieldbackground=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            background=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            foreground=[('readonly', entry_fg), ('!readonly', entry_fg), ('active', entry_fg)],
            bordercolor=[('focus', accent), ('!focus', accent)],
            highlightcolor=[('focus', accent), ('!focus', accent)])
        style.configure('Horizontal.TProgressbar', background=accent, troughcolor=bg)
        self.root.option_add('*TCombobox*Listbox.background', entry_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', entry_fg)
        self.root.option_add('*Entry.background', entry_bg)
        self.root.option_add('*Entry.foreground', entry_fg)
        self.root.option_add('*Entry.highlightBackground', accent)
        self.root.option_add('*Entry.highlightColor', accent)
        self.root.option_add('*Text.background', entry_bg)
        self.root.option_add('*Text.foreground', entry_fg)
        self.root.option_add('*foreground', fg)
        self.root.option_add('*background', bg)
        if hasattr(self, 'log_text'):
            self.log_text.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)

    def _apply_default_theme(self):
        style = ttk.Style()
        style.theme_use('default')
        # Remove any custom option_adds for widgets
        self.root.option_clear()
        if hasattr(self, 'log_text'):
            self.log_text.config(bg='white', fg='black', insertbackground='black')

    def _apply_custom_theme(self, save=False):
        style = ttk.Style()
        style.theme_use('clam')
        bg = self.custom_color_vars['bg'].get()
        fg = self.custom_color_vars['fg'].get()
        accent = self.custom_color_vars['accent'].get()
        entry_bg = self.custom_color_vars['entry_bg'].get()
        entry_fg = self.custom_color_vars['entry_fg'].get()
        button_bg = entry_bg
        button_fg = entry_fg
        style.configure('.', background=bg, foreground=fg)
        style.configure('TFrame', background=bg)
        style.configure('TLabel', background=bg, foreground=fg)
        style.configure('TButton', background=button_bg, foreground=button_fg, borderwidth=1, focusthickness=2, focuscolor=accent)
        style.map('TButton',
            background=[('active', button_bg), ('pressed', accent), ('!active', button_bg)],
            foreground=[('active', button_fg), ('pressed', button_fg), ('!active', button_fg)])
        style.configure('TCheckbutton', background=bg, foreground=fg, indicatorcolor=accent, indicatordiameter=12, bordercolor=accent, focuscolor=accent)
        style.map('TCheckbutton',
            background=[('active', bg), ('selected', bg), ('!active', bg)],
            foreground=[('active', fg), ('selected', fg), ('!active', fg)])
        style.configure('TNotebook', background=bg)
        style.configure('TNotebook.Tab', background=button_bg, foreground=button_fg, lightcolor=accent, borderwidth=0)
        style.map('TNotebook.Tab',
            background=[('selected', accent), ('active', button_bg), ('!selected', button_bg)],
            foreground=[('selected', fg), ('active', fg), ('!selected', button_fg)])
        style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg, background=entry_bg, bordercolor=accent, lightcolor=accent, darkcolor=bg, highlightcolor=accent, selectbackground=accent, selectforeground=button_fg)
        style.map('TEntry',
            fieldbackground=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            background=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            foreground=[('readonly', entry_fg), ('!readonly', entry_fg), ('active', entry_fg)],
            bordercolor=[('focus', accent), ('!focus', accent)],
            highlightcolor=[('focus', accent), ('!focus', accent)])
        style.configure('TCombobox', fieldbackground=entry_bg, foreground=entry_fg, background=entry_bg, selectbackground=entry_bg, selectforeground=entry_fg, bordercolor=accent, lightcolor=accent, darkcolor=bg, highlightcolor=accent)
        style.map('TCombobox',
            fieldbackground=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            background=[('readonly', entry_bg), ('!readonly', entry_bg), ('active', entry_bg)],
            foreground=[('readonly', entry_fg), ('!readonly', entry_fg), ('active', entry_fg)],
            bordercolor=[('focus', accent), ('!focus', accent)],
            highlightcolor=[('focus', accent), ('!focus', accent)])
        style.configure('Horizontal.TProgressbar', background=accent, troughcolor=bg)
        self.root.option_add('*TCombobox*Listbox.background', entry_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', entry_fg)
        self.root.option_add('*Entry.background', entry_bg)
        self.root.option_add('*Entry.foreground', entry_fg)
        self.root.option_add('*Entry.highlightBackground', accent)
        self.root.option_add('*Entry.highlightColor', accent)
        self.root.option_add('*Text.background', entry_bg)
        self.root.option_add('*Text.foreground', entry_fg)
        self.root.option_add('*foreground', fg)
        self.root.option_add('*background', bg)
        if hasattr(self, 'log_text'):
            self.log_text.config(bg=entry_bg, fg=entry_fg, insertbackground=entry_fg)
        if save:
            self.config['custom_theme'] = {k: v.get() for k, v in self.custom_color_vars.items()}

    def _setup_info_tab(self):
        """Set up the Info tab with a modern, visually appealing layout, icons, and a warning box."""
        # Clear any existing widgets
        for widget in self.info_tab.winfo_children():
            widget.destroy()

        # Banner frame with app name (no image)
        banner = ttk.Frame(self.info_tab)
        banner.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        banner.columnconfigure(0, weight=1)
        title_label = ttk.Label(banner, text="Oblivion V1", font=("Segoe UI", 20, "bold"))
        title_label.grid(row=0, column=0, sticky="w", pady=0)
        subtitle = ttk.Label(banner, text="Ultimate Discord Webhook Tool", font=("Segoe UI", 12, "italic"))
        subtitle.grid(row=1, column=0, sticky="w", pady=(0, 5))

        # Section: Control Tab
        ctl_frame = ttk.Frame(self.info_tab)
        ctl_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(ctl_frame, text="[Control Tab]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(ctl_frame, text="• Select mode and shards\n• Start/Kill process", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: Settings Tab
        set_frame = ttk.Frame(self.info_tab)
        set_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(set_frame, text="[Settings Tab]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(set_frame, text="• Edit message, delay, limits\n• Save or reset config", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: Themes
        theme_frame = ttk.Frame(self.info_tab)
        theme_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(theme_frame, text="[Themes]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(theme_frame, text="• Choose or customize appearance", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: Preferences
        pref_frame = ttk.Frame(self.info_tab)
        pref_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(pref_frame, text="[Preferences Tab]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(pref_frame, text="• Change theme and colors", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: Logs
        log_frame = ttk.Frame(self.info_tab)
        log_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(log_frame, text="[Log Area]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(log_frame, text="• View logs\n• Hide/Show logs", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: License
        lic_frame = ttk.Frame(self.info_tab)
        lic_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=(0, 2))
        ttk.Label(lic_frame, text="[License]", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(lic_frame, text="Non-commercial use only", wraplength=520, justify="left").grid(row=1, column=0, sticky="w", padx=(20,0))

        # Section: Discord TOS Warning (highlighted)
        warn_frame = ttk.Frame(self.info_tab)
        warn_frame.grid(row=7, column=0, sticky="ew", padx=10, pady=(6, 2))
        warn_box = tk.Label(warn_frame, text="[Discord TOS Warning]\nUse responsibly. Excessive use or TOS violations may result in bans. See discord.com/terms.",
                            bg="#ffe4e1", fg="#a94442", font=("Segoe UI", 10, "bold"), wraplength=500, justify="left", relief="solid", bd=2, padx=10, pady=6)
        warn_box.grid(row=0, column=0, sticky="ew")

        # Make the info tab expand to fill available space
        self.info_tab.columnconfigure(0, weight=1)
        self.info_tab.rowconfigure(8, weight=1)

    def _reset_config(self):
        for _, varname, _, key in self._settings_fields:
            getattr(self, varname).set(self.DEFAULT_CONFIG[key])
        self.theme_var.set('Default')
        self._apply_theme('Default', save=True)
        messagebox.showinfo("Success", "Configuration reset to default values")

    def _update_shard_ui(self):
        """Update the shard selection UI based on the selected mode (Parallel or Sequential)."""
        for widget in self.shard_frame.winfo_children():
            widget.destroy()
        if self.mode.get() == "parallel":
            # In Parallel mode, show checkboxes for each shard
            self.shard_states = {shard: tk.BooleanVar(value=False) for shard in self.webhook_groups}
            self.shard_checkbuttons = {}
            for row, (shard, var) in enumerate(self.shard_states.items()):
                cb = ttk.Checkbutton(self.shard_frame, text=shard, variable=var)
                cb.grid(row=row, column=0, sticky=tk.W, pady=2, padx=5)
                self.shard_checkbuttons[shard] = cb
            self.switch_status_label.grid_remove()
            self.switch_shard_combo = None
        else:
            # In Sequential mode, show a dropdown to select the starting shard
            ttk.Label(self.shard_frame, text="Starting Shard:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
            self.switch_shard_var = tk.StringVar()
            combo = ttk.Combobox(self.shard_frame, textvariable=self.switch_shard_var, state="readonly")
            combo['values'] = list(self.webhook_groups.keys())
            combo.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
            if combo['values']:
                combo.current(0)
            self.switch_status_label.grid()
            self.switch_shard_combo = combo

    def _setup_manage_shards_in_settings(self, parent):
        from tkinter import filedialog
        def add_row(frame, label, var, row):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=3, padx=5)
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew", pady=3, padx=5)
        manage_frame = ttk.Frame(parent)
        manage_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=10)
        manage_frame.columnconfigure(0, weight=1)
        manage_frame.columnconfigure(1, weight=1)
        # Add Shard Group (left)
        add_frame = ttk.LabelFrame(manage_frame, text="Add Shard Group", padding="10")
        add_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.add_group_name_var = tk.StringVar()
        self.add_json_path_var = tk.StringVar()
        add_row(add_frame, "Group Name:", self.add_group_name_var, 0)
        add_row(add_frame, "Webhooks JSON File:", self.add_json_path_var, 1)
        def browse_json():
            path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
            if path:
                self.add_json_path_var.set(path)
        ttk.Button(add_frame, text="Browse", command=browse_json).grid(row=1, column=2, sticky="ew", pady=3, padx=5)
        ttk.Button(add_frame, text="Add Group", command=self._add_shard_group).grid(row=2, column=0, columnspan=3, pady=8)
        add_frame.columnconfigure(1, weight=1)
        # Delete Shard Group (right)
        del_frame = ttk.LabelFrame(manage_frame, text="Delete Shard Group", padding="10")
        del_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.del_group_var = tk.StringVar()
        self.del_group_combo = ttk.Combobox(del_frame, textvariable=self.del_group_var, state="readonly")
        self._refresh_shard_group_combo()
        self.del_group_combo.grid(row=0, column=1, sticky="ew", pady=3, padx=5)
        ttk.Label(del_frame, text="Select Group:").grid(row=0, column=0, sticky=tk.W, pady=3, padx=5)
        ttk.Button(del_frame, text="Delete Group", command=self._delete_shard_group).grid(row=1, column=0, columnspan=2, pady=8)
        del_frame.columnconfigure(1, weight=1)

    def _refresh_shard_group_combo(self):
        # Helper to refresh the delete group dropdown
        if hasattr(self, 'del_group_combo'):
            self.del_group_combo['values'] = list(self.webhook_groups.keys())
            if self.webhook_groups:
                self.del_group_combo.current(0)
            else:
                self.del_group_var.set("")

    def _add_shard_group(self):
        import json
        group_name = self.add_group_name_var.get().strip()
        json_path = self.add_json_path_var.get().strip()
        if not group_name:
            messagebox.showerror("Error", "Please enter a group name.")
            return
        if not json_path or not os.path.exists(json_path):
            messagebox.showerror("Error", "Please select a valid JSON file.")
            return
        try:
            with open(json_path, 'r') as f:
                webhooks = json.load(f)
            if not isinstance(webhooks, list) or not all(isinstance(url, str) for url in webhooks):
                raise ValueError("JSON must be a list of webhook URLs.")
            # Load current webhooks.json
            with open(resource_path(self.config['webhooks_file']), 'r') as f:
                all_groups = json.load(f)
            if group_name in all_groups:
                messagebox.showerror("Error", f"Group '{group_name}' already exists.")
                return
            all_groups[group_name] = webhooks
            with open(resource_path(self.config['webhooks_file']), 'w') as f:
                json.dump(all_groups, f, indent=2)
            self.webhook_groups = all_groups
            self._refresh_shard_group_combo()
            self._update_shard_ui()
            messagebox.showinfo("Success", f"Group '{group_name}' added successfully.")
        except Exception as e:
            logger.error(f"Failed to add shard group: {e}")
            messagebox.showerror("Error", f"Failed to add group: {e}")

    def _delete_shard_group(self):
        import json
        group_name = self.del_group_var.get().strip()
        if not group_name:
            messagebox.showerror("Error", "Please select a group to delete.")
            return
        try:
            with open(resource_path(self.config['webhooks_file']), 'r') as f:
                all_groups = json.load(f)
            if group_name not in all_groups:
                messagebox.showerror("Error", f"Group '{group_name}' does not exist.")
                return
            del all_groups[group_name]
            with open(resource_path(self.config['webhooks_file']), 'w') as f:
                json.dump(all_groups, f, indent=2)
            self.webhook_groups = all_groups
            self._refresh_shard_group_combo()
            self._update_shard_ui()
            messagebox.showinfo("Success", f"Group '{group_name}' deleted successfully.")
        except Exception as e:
            logger.error(f"Failed to delete shard group: {e}")
            messagebox.showerror("Error", f"Failed to delete group: {e}")

    def _set_shard_checkboxes_state(self, enabled: bool):
        """Enable or disable all shard checkboxes in Parallel mode."""
        if hasattr(self, 'shard_checkbuttons'):
            state = "normal" if enabled else "disabled"
            for cb in self.shard_checkbuttons.values():
                cb.config(state=state)

    def _set_switch_combo_state(self, enabled: bool):
        """Enable or disable the starting shard dropdown in Sequential mode."""
        if hasattr(self, 'switch_shard_combo') and self.switch_shard_combo is not None:
            state = "readonly" if enabled else "disabled"
            self.switch_shard_combo.config(state=state)

    def _save_config(self):
        """Save the current configuration values to the YAML config file and update runtime variables."""
        try:
            for _, varname, _, key in self._settings_fields:
                self.config[key] = getattr(self, varname).get()
            self.config['theme'] = self.theme_var.get()
            if self.theme_var.get() == 'Custom':
                self.config['custom_theme'] = {k: v.get() for k, v in self.custom_color_vars.items()}
            with open(self.config_file, 'w') as file:
                yaml.safe_dump(self.config, file)
            messagebox.showinfo("Success", "Configuration saved successfully")
            # Update runtime variables to reflect new settings
            self.rate_limit_backoff = getattr(self, 'backoff_var').get()
            self.max_retries = getattr(self, 'retries_var').get()
            self.message_limit = getattr(self, 'limit_var').get()
            self.total_pings = getattr(self, 'total_pings_var').get()
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            messagebox.showerror("Error", f"Failed to save config: {e}")

    def _send_webhook(self, webhook_url: str, message: str, username: Optional[str], 
                     avatar_url: Optional[str], shard_name: str) -> bool:
        """Send a single webhook message, handling rate limits and retries as needed."""
        payload = {"content": message}
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url

        headers = {"Content-Type": "application/json"}

        for attempt in range(self.max_retries):
            try:
                response = requests.post(webhook_url, json=payload, headers=headers)
                if response.status_code == 204:
                    # Message sent successfully; increment the count
                    self.message_counts[webhook_url] = self.message_counts.get(webhook_url, 0) + 1
                    logger.info(f"Sent message to {webhook_url} (Count: {self.message_counts[webhook_url]})")
                    # Update Switch mode status if applicable
                    if self.mode.get() == "sequential" and shard_name == self.current_switch_shard:
                        self._update_switch_status()
                    return True
                elif response.status_code == 429:
                    # Rate limited; wait for the specified retry_after time
                    retry_after = response.json().get('retry_after', self.rate_limit_backoff) / 1000
                    logger.warning(f"Rate limited on {webhook_url}. Waiting {retry_after}s")
                    time.sleep(retry_after)
                else:
                    # Other error; log and return failure
                    logger.error(f"Failed to send to {webhook_url}. Status: {response.status_code}, Response: {response.text}")
                    return False
            except requests.RequestException as e:
                # Network or request error; retry if attempts remain
                logger.error(f"Error sending to {webhook_url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.rate_limit_backoff)
        logger.error(f"Max retries reached for {webhook_url}")
        return False

    def _webhook_loop(self, webhook_url: str, message: str, username: str, avatar_url: str, 
                     delay: float, shard_name: str):
        """Continuously send messages to a webhook until stopped or the message limit is reached."""
        while self.shard_status.get(shard_name, False) and self.message_counts.get(webhook_url, 0) < self.message_limit:
            self._send_webhook(webhook_url, message, username, avatar_url, shard_name)
            time.sleep(delay)

    def _start_shard(self, shard_name: str):
        """Start sending messages for a shard by launching threads for each webhook URL."""
        self.shard_status[shard_name] = True
        self.threads[shard_name] = []
        webhook_urls = self.webhook_groups[shard_name]
        message = getattr(self, 'message_var').get()
        username = getattr(self, 'username_var').get()
        avatar_url = getattr(self, 'avatar_var').get()
        delay = getattr(self, 'delay_var').get()

        for webhook_url in webhook_urls:
            # Initialize message count if not already set
            self.message_counts[webhook_url] = self.message_counts.get(webhook_url, 0)
            thread = threading.Thread(
                target=self._webhook_loop,
                args=(webhook_url, message, username, avatar_url, delay, shard_name),
                daemon=False
            )
            self.threads[shard_name].append(thread)
            thread.start()
        logger.info(f"Started shard: {shard_name}")

    def _stop_shard(self, shard_name: str):
        """Stop sending messages for a shard and join its threads before clearing."""
        if not self.shard_status.get(shard_name, False):
            return
        self.shard_status[shard_name] = False
        threads = self.threads.get(shard_name, [])
        for thread in threads:
            if thread.is_alive():
                thread.join(timeout=5)
        self.threads[shard_name] = []
        logger.info(f"Stopped shard: {shard_name}")

    def _start_action(self):
        """Handle the Start button action based on the selected mode."""
        if self.mode.get() == "parallel":
            self._start_parallel_mode()
        else:
            self._start_sequential_mode()

    def _start_parallel_mode(self):
        selected_shards = [shard for shard, var in self.shard_states.items() if var.get()]
        if not selected_shards:
            messagebox.showerror("Error", "Select at least one shard")
            return
        if any(self.shard_status.get(shard, False) for shard in selected_shards):
            messagebox.showwarning("Warning", "One or more selected shards are already running")
            return
        for shard in selected_shards:
            self._start_shard(shard)
        self._set_start_stop_state(False, True)
        self._set_shard_checkboxes_state(False)

    def _start_sequential_mode(self):
        if any(self.shard_status.values()):
            messagebox.showwarning("Warning", "A shard is already running")
            return
        shard_name = self.switch_shard_var.get()
        if not shard_name:
            messagebox.showerror("Error", "Select a starting shard")
            return
        self.current_switch_shard = shard_name
        self._start_shard(shard_name)
        threading.Thread(target=self._monitor_sequential_mode, daemon=True).start()
        self._set_start_stop_state(False, True)
        self._set_switch_combo_state(False)

    def _monitor_sequential_mode(self):
        """Monitor the current shard in Sequential mode and switch to the next shard when the total pings are reached."""
        shard_names = list(self.webhook_groups.keys())
        while self.shard_status.get(self.current_switch_shard, False):
            webhook_urls = self.webhook_groups[self.current_switch_shard]
            total_messages = sum(self.message_counts.get(url, 0) for url in webhook_urls)
            if total_messages >= self.total_pings:
                # Stop the current shard and switch to the next one in the list
                if self.current_switch_shard is not None:
                    self._stop_shard(self.current_switch_shard)
                current_idx = shard_names.index(self.current_switch_shard)
                next_idx = (current_idx + 1) % len(shard_names)  # Loop back to the first shard if at the end
                self.current_switch_shard = shard_names[next_idx]
                self._start_shard(self.current_switch_shard)
                logger.info(f"Switched to shard: {self.current_switch_shard}")
            time.sleep(5)

    def _update_switch_status(self):
        """Update the status label in Sequential mode to show current shard and progress."""
        if self.current_switch_shard:
            webhook_urls = self.webhook_groups[self.current_switch_shard]
            total_messages = sum(self.message_counts.get(url, 0) for url in webhook_urls)
            self.switch_status_var.set(
                f"Sequential Mode: {self.current_switch_shard} ({total_messages}/{self.total_pings} pings)"
            )

    def _stop_action(self):
        """Handle the Stop button action based on the selected mode."""
        if self.mode.get() == "parallel":
            self._stop_parallel_mode()
        else:
            self._stop_sequential_mode()

    def _stop_parallel_mode(self):
        selected_shards = [shard for shard, var in self.shard_states.items() if var.get()]
        if not any(self.shard_status.get(shard, False) for shard in selected_shards):
            messagebox.showwarning("Warning", "No selected shards are running")
            return
        for shard in selected_shards:
            self._stop_shard(shard)
        if not any(self.shard_status.values()):
            self._set_start_stop_state(True, False)
            self._set_shard_checkboxes_state(True)

    def _stop_sequential_mode(self):
        if not self.shard_status.get(self.current_switch_shard, False):
            messagebox.showwarning("Warning", "No shard is running")
            return
        if self.current_switch_shard is not None:
            self._stop_shard(self.current_switch_shard)
        self.current_switch_shard = None
        self.switch_status_var.set("Sequential Mode: Idle")
        self._set_start_stop_state(True, False)
        self._set_switch_combo_state(True)

    def _kill_action(self):
        """Immediately destroy the window and kill the program."""
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def _toggle_logs(self):
        """Show or hide the log display widget."""
        if self.logs_visible:
            self.log_text.grid_remove()
            self.toggle_logs_button.config(text="Show Logs")
            self.logs_visible = False
        else:
            self.log_text.grid()
            self.toggle_logs_button.config(text="Hide Logs")
            self.logs_visible = True

    def _refresh_theme_widgets(self):
        # Force redraw of all widgets to apply new theme
        self.root.update_idletasks()
        # For scrolledtext, set manually
        if hasattr(self, 'log_text'):
            theme = self.theme_var.get() if hasattr(self, 'theme_var') else self.config.get('theme', 'Default')
            if theme == "Default":
                self.log_text.config(bg='white', fg='black', insertbackground='black')
            elif theme == "Custom":
                c = self.config.get('custom_theme', {})
                self.log_text.config(bg=c.get('entry_bg', '#23272e'), fg=c.get('entry_fg', '#f8f8f2'), insertbackground=c.get('entry_fg', '#f8f8f2'))
            elif theme in self.themes:
                t = self.themes[theme]
                self.log_text.config(bg=t['entry_bg'], fg=t['entry_fg'], insertbackground=t['entry_fg'])
            else:
                self.log_text.config(bg='white', fg='black', insertbackground='black')

class TextHandler(logging.Handler):
    """Custom logging handler to display logs in the GUI's text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.configure(state='disabled')

if __name__ == "__main__":
    # Entry point: create the main window and start the GUI application
    root = tk.Tk()
    app = OblivionGUI(root, resource_path("config.yaml"))
    root.mainloop()
