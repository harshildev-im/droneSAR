import tkinter as tk        
from tkinter import messagebox 
from tkintermapview import TkinterMapView
from database import Database
from tkinter import filedialog
import json 
import rasterio
import geopandas as gpd 
from rasterio.mask import mask
import numpy as np 
from rasterio.transform import xy 
import math 
from pyproj import Transformer
from rasterio.windows import from_bounds
from tkinter import ttk 
import re 
import os 
from rasterio.windows import Window
from rasterio.windows import bounds
from rasterio.transform import rowcol
from rasterio.merge import merge
from rasterio.warp import reproject , Resampling 
from rasterio.enums import Resampling
import zipfile
import tempfile
import shutil
from shapely.geometry import box
import pandas as pd 
import threading 
from datetime import datetime 
from pathlib import Path
import csv
from login import LoginWindow
import mysql.connector
import uuid 
import secrets
from sitl import Drone

class Display:
    def __init__(self , root ,userid):
        self.root = root
        self.userid = userid
        self.root.title("White cloud DMS 1.0")
        self.root.geometry("1920x1080")
        self.root.configure(bg='black')
        self.satte_mode = False
        self.tables_list = [] 
        self.geojson_polygons = []
        self.locations_on_screen = [] #for selected locations for the analysis 
        self.connected_drones = []
        #disaster data thread
        #self.stop_event = threading.Event()
        #self.disaster_thread = threading.Thread(target=self.disaster_worker,daemon=True)

        #frames
        header_toolbar = tk.Frame(root , bg='#e0e0e0' ,height=40)
        header_toolbar.pack(fill='x')
        footer_toolbar = tk.Frame(root, height=50)
        footer_toolbar.pack(fill='x' , side='bottom')

        #buttons
        add_location_btn = tk.Button(header_toolbar , text='add location' , command=self.add_location)
        add_location_btn.pack(side='left' , padx=10)
        select_location_btn = tk.Button(header_toolbar , text='select location' , command=self.select_location)
        select_location_btn.pack(side='left' , padx=10)
        toggle_mode = tk.Button(header_toolbar , text='toggle map' ,command=self.toggle_map)
        toggle_mode.pack(side='left' , padx=10)
        add_drones = tk.Button(header_toolbar , text='add drones' , command=self.add_drones)
        add_drones.pack(side='left' , padx=10)
        connect_drone = tk.Button(header_toolbar , text='connect drone' , command=self.connect_drone)
        connect_drone.pack(side='left' , padx=10)
        disconnect_drone = tk.Button(header_toolbar , text='disconnect drone' , command=self.disconnect_drones)
        disconnect_drone.pack(side='left' , padx=10)
        start_mission_btn = tk.Button(header_toolbar , text='start mission ' , command=self.start_mission)
        start_mission_btn.pack(side='left' , padx=10)

        #map functions 
        self.map_widget = TkinterMapView(root, width=1920, height=100)
        self.map_widget.pack(fill='both', expand=True)
        self.map_widget.set_tile_server("https://tile.openstreetmap.org/{z}/{x}/{y}.png")
        self.map_widget.set_position(24.9818, 121.5036)
        osm_label = tk.Label(
            self.map_widget,
            text="© OpenStreetMap contributors",
            bg="white",
            fg="black",
            font=("Arial", 9)
        )
        osm_label.place(relx=1.0, rely=1.0, anchor="se")
        #labels
        bottom_label = tk.Label(footer_toolbar , text='this software is made by harshil jain , this is a prototype not an actual product\n. Elevation data derived from Copernicus DEM GLO-30, © European Union\n.Population data provided by WorldPop, School of Geography and Environmental Science, University of Southampton. The data are used under the Creative Commons Attribution 4.0 International License (CC BY 4.0)\n.Disaster data source: Global Disaster Alert and Coordination System (GDACS). All rights reserved by the respective data providers.' , anchor='e')
        bottom_label.pack(side='left' , padx=10)
        #self.disaster_thread.start()
        #self.root.protocol("WM_DELETE_WINDOW", self.on_close)  
        
    def start_mission(self):
        mission_window = tk.Toplevel(self.root)
        mission_window.title("Mission Planner")
        mission_window.geometry("650x650")
        mission_window.configure(bg="black")

        locations = self.locations_on_screen.copy()

        if not locations:
            label = tk.Label(
                mission_window,
                text="No locations selected",
                fg="white",
                bg="black"
            )
            label.pack(padx=10, pady=10)
            return

        selection_frame = tk.Frame(
            mission_window,
            bg="black"
        )
        selection_frame.pack(fill="both", expand=True, pady=10)

        selection_label = tk.Label(
            selection_frame,
            text="Select the location",
            fg="white",
            bg="black"
        )
        selection_label.pack(anchor="w", padx=10, pady=10)

        options = ["all"] + locations
        self.location_vars = {}

        def toggle_all():
            value = self.location_vars["all"].get()
            for location in locations:
                self.location_vars[location].set(value)

        def toggle_location(location):
            if not self.location_vars[location].get():
                self.location_vars["all"].set(False)
            else:
                all_selected = all(
                    self.location_vars[loc].get()
                    for loc in locations
                )
                self.location_vars["all"].set(all_selected)

        for option in options:
            var = tk.BooleanVar(value=False)
            self.location_vars[option] = var

            if option == "all":
                command = toggle_all
            else:
                command = lambda loc=option: toggle_location(loc)

            checkbox = tk.Checkbutton(
                selection_frame,
                text=option,
                variable=var,
                command=command,
                fg="white",
                bg="black",
                selectcolor="gray20",
                activebackground="black",
                activeforeground="white"
            )
            checkbox.pack(anchor="w", padx=10, pady=3)

        # Define this function outside the loop
        def save_selection():
            if self.location_vars["all"].get():
                selected = locations.copy()
            else:
                selected = [
                    loc for loc in locations
                    if self.location_vars[loc].get()
                ]

            self.selected_missions = selected

        # Create only ONE confirmation button
        confirm_button = tk.Button(
            selection_frame,
            text="Confirm Selection",
            command=save_selection,
            fg="black",
            bg="gray20",
            activebackground="gray40",
            activeforeground="white"
        )
        confirm_button.pack(pady=20)


    def connect_drone(self):
        connect_drone_window = tk.Toplevel(self.root)
        connect_drone_window.title("Connect to Drone")
        connect_drone_window.geometry("850x700")
        connect_drone_window.configure(bg="black")
        # ---------------------------------------------------------
        # Header
        # ---------------------------------------------------------
        title_label = tk.Label(
            connect_drone_window,
            text="Available Drones",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="black"
        )
        title_label.pack(pady=15)

        # ---------------------------------------------------------
        # Main container
        # ---------------------------------------------------------
        container = tk.Frame(connect_drone_window, bg="black")
        container.pack(fill="both", expand=True, padx=20, pady=10)

        # ---------------------------------------------------------
        # Canvas + scrollbar
        # ---------------------------------------------------------
        canvas = tk.Canvas(
            container,
            bg="black",
            highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        # Frame inside canvas
        drone_list_frame = tk.Frame(
            canvas,
            bg="black"
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=drone_list_frame,
            anchor="nw"
        )

        # Make the inner frame width follow the canvas
        def configure_canvas(event):
            canvas.itemconfig(
                canvas_window,
                width=event.width
            )

        canvas.bind("<Configure>", configure_canvas)

        # Update scroll region whenever the frame changes
        def configure_scroll_region(event):
            canvas.configure(
                scrollregion=canvas.bbox("all")
            )

        drone_list_frame.bind(
            "<Configure>",
            configure_scroll_region
        )

        # ---------------------------------------------------------
        # Database
        # ---------------------------------------------------------
        db = Database()
        db.connect_db(self.userid)

        try:
            # Use a parameter-free query here because there is
            # nothing being supplied by the user.
            db.cursor.execute(
                "SELECT drone_id FROM drones ORDER BY drone_id"
            )

            data = db.cursor.fetchall()

            # -----------------------------------------------------
            # No drones found
            # -----------------------------------------------------
            if not data:
                no_drone_label = tk.Label(
                    drone_list_frame,
                    text="No drones found.",
                    font=("Arial", 14),
                    fg="white",
                    bg="black"
                )
                no_drone_label.pack(pady=30)

            # -----------------------------------------------------
            # Display drones
            # -----------------------------------------------------
            for row in data:

                drone_id = row[0]

                drone_frame = tk.Frame(
                    drone_list_frame,
                    bg="#202020",
                    bd=1,
                    relief="solid"
                )

                drone_frame.pack(
                    fill="x",
                    padx=10,
                    pady=5
                )

                # Drone name / ID
                drone_label = tk.Label(
                    drone_frame,
                    text=drone_id,
                    font=("Arial", 14, "bold"),
                    fg="white",
                    bg="#202020",
                    anchor="w"
                )

                drone_label.pack(
                    side="left",
                    fill="x",
                    expand=True,
                    padx=15,
                    pady=12
                )

                # Connect button
                connect_button = tk.Button(
                    drone_frame,
                    text="Connect",
                    font=("Arial", 11),
                    command=lambda drone=drone_id: self.connect_selected_drone(
                        drone,
                        connect_drone_window
                    )
                )

                connect_button.pack(
                    side="right",
                    padx=15,
                    pady=8
                )

        except Exception as dbconnectionerror:

            Database.log_file(dbconnectionerror)

            messagebox.showerror(
                "Error",
                str(dbconnectionerror),
                parent=connect_drone_window
            )

        finally:
            db.disconnect_db()

        # ---------------------------------------------------------
        # Mouse wheel scrolling
        # ---------------------------------------------------------
        def mouse_wheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            mouse_wheel
        )

        # Remove the binding when the window closes
        def close_window():
            canvas.unbind_all("<MouseWheel>")
            connect_drone_window.destroy()

        connect_drone_window.protocol(
            "WM_DELETE_WINDOW",
            close_window
        )
    def connect_selected_drone(self, drone_id, window):
        # Prevent duplicate connections
        for drone in self.connected_drones:
            if drone.drone_id == drone_id:
                messagebox.showwarning(
                    "Already Connected",
                    f"Drone '{drone_id}' is already connected."
                )
                window.destroy()
                return

        # Create latitude and longitude dialog
        drone_location = tk.Toplevel(self.root)
        drone_location.title("Add Drone Latitude and Longitude")
        drone_location.geometry("300x250")
        drone_location.resizable(False, False)

        # Latitude input
        lat_frame = tk.Frame(drone_location)
        lat_frame.pack(fill="x", padx=15, pady=(15, 5))

        tk.Label(
            lat_frame,
            text="Latitude (-90 to 90):"
        ).pack(anchor="w")

        lat_entry = tk.Entry(lat_frame)
        lat_entry.pack(fill="x", pady=5)

        # Longitude input
        lon_frame = tk.Frame(drone_location)
        lon_frame.pack(fill="x", padx=15, pady=5)

        tk.Label(
            lon_frame,
            text="Longitude (-180 to 180):"
        ).pack(anchor="w")

        lon_entry = tk.Entry(lon_frame)
        lon_entry.pack(fill="x", pady=5)

        # This function MUST be inside connect_selected_drone
        def submit_location():
            # Read coordinates
            try:
                lat = float(lat_entry.get().strip())
                lon = float(lon_entry.get().strip())
            except ValueError:
                messagebox.showerror(
                    "Invalid Input",
                    "Please enter valid numeric coordinates.",
                    parent=drone_location
                )
                return

            # Validate latitude
            if not -90 <= lat <= 90:
                messagebox.showerror(
                    "Invalid Latitude",
                    "Latitude must be between -90 and 90.",
                    parent=drone_location
                )
                return

            # Validate longitude
            if not -180 <= lon <= 180:
                messagebox.showerror(
                    "Invalid Longitude",
                    "Longitude must be between -180 and 180.",
                    parent=drone_location
                )
                return

            # Close the coordinate dialog
            drone_location.destroy()

            # Check for duplicate drone again
            for drone in self.connected_drones:
                if drone.drone_id == drone_id:
                    messagebox.showwarning(
                        "Already Connected",
                        f"Drone '{drone_id}' is already connected."
                    )
                    window.destroy()
                    return

            # Create the drone using the submitted coordinates
            instance_id = len(self.connected_drones)

            drone_new = Drone(
                drone_id,
                self.userid,
                instance_id,
                lat,
                lon
            )

            # Connect the drone
            if drone_new.connect_drone():
                self.connected_drones.append(drone_new)

                messagebox.showinfo(
                    "Success",
                    f"Drone '{drone_id}' connected successfully."
                )

                print(
                    "Connected drones:",
                    [drone.drone_id for drone in self.connected_drones]
                )

            else:
                messagebox.showerror(
                    "Connection Failed",
                    f"Could not connect to drone '{drone_id}'."
                )

            # Close the original selection window
            window.destroy()

        # Submit button MUST also be inside connect_selected_drone
        submit_button = tk.Button(
            drone_location,
            text="Submit",
            command=submit_location
        )
        submit_button.pack(pady=15)

        # Make the coordinate dialog modal
        drone_location.transient(self.root)
        drone_location.grab_set()


    def disconnect_drones(self):
        window = tk.Toplevel(self.root)
        window.title("Disconnect Drone")
        window.geometry("600x500")
        window.configure(bg="black")

        title_label = tk.Label(
            window,
            text="Connected Drones",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="black"
        )
        title_label.pack(pady=15)

        container = tk.Frame(window, bg="black")
        container.pack(fill="both", expand=True, padx=20, pady=10)

        if not self.connected_drones:
            tk.Label(
                container,
                text="No drones are currently connected.",
                font=("Arial", 14),
                fg="white",
                bg="black"
            ).pack(pady=20)
            return

        for drone in self.connected_drones:
            drone_frame = tk.Frame(
                container,
                bg="#202020",
                bd=1,
                relief="solid"
            )
            drone_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(
                drone_frame,
                text=str(drone.drone_id),
                font=("Arial", 14, "bold"),
                fg="white",
                bg="#202020",
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=15,
                pady=12
            )

            tk.Button(
                drone_frame,
                text="Disconnect",
                command=lambda selected=drone:
                    self.disconnect_selected_drone(selected, window)
            ).pack(side="right", padx=15, pady=8)


    def disconnect_selected_drone(self, drone, window):
        # Stop the selected drone's SITL process
        if drone.disconnect_drone():
            # Remove the exact Drone object from the list
            if drone in self.connected_drones:
                self.connected_drones.remove(drone)

            messagebox.showinfo(
                "Disconnected",
                f"Drone '{drone.drone_id}' disconnected successfully."
            )

            window.destroy()

            # Refresh the list if other drones remain
            self.disconnect_drones()
    def add_drones(self):
        """
        Open the Add Drone window.
        Every field that exists in the drones table is collected here.
        Empty string fields -> ''
        Empty numeric fields -> 0
        drone_id and mav_sys_id are generated automatically.
        """

        add_drones_window = tk.Toplevel(self.root)
        add_drones_window.title("Add New Drone")
        add_drones_window.geometry("850x700")
        add_drones_window.configure(bg="black")

        # ============================================================
        # ALL USER INPUT FIELDS
        #
        # (database_column, display_name, data_type)
        #
        # data_type:
        #   "str"    -> empty value becomes ''
        #   "number" -> empty value becomes 0
        # ============================================================
        fields = [

            # --------------------------------------------------------
            # BASIC DRONE INFORMATION
            # --------------------------------------------------------
            ("connection_type", "Connection Type (udp/tcp)", "str"),
            ("ip_address", "IP Address / IP:Port", "str"),

            # --------------------------------------------------------
            # LIDAR
            # --------------------------------------------------------
            ("lidar", "Lidar", "str"),
            ("lidar_company", "Lidar Company", "str"),
            ("lidar_model", "Lidar Model", "str"),
            ("lidar_type", "Lidar Type", "str"),
            ("lidar_measuring_dist", "Lidar Measuring Distance", "number"),
            ("lidar_accuracy", "Lidar Accuracy", "number"),
            ("lidar_horizontal_fov", "Lidar Horizontal FOV", "number"),
            ("lidar_vertical_fov", "Lidar Vertical FOV", "number"),
            ("lidar_scan_rate_hz", "Lidar Scan Rate (Hz)", "number"),
            ("lidar_point_rate_hz", "Lidar Point Rate (Hz)", "number"),
            ("lidar_wavelength_nm", "Lidar Wavelength (nm)", "number"),
            ("lidar_beam_divergence", "Lidar Beam Divergence", "number"),
            ("lidar_info", "Lidar Information", "str"),

            # --------------------------------------------------------
            # RGB CAMERA
            # --------------------------------------------------------
            ("camera_rgb", "RGB Camera", "str"),
            ("camera_rgb_company", "RGB Camera Company", "str"),
            ("camera_rgb_model", "RGB Camera Model", "str"),
            ("camera_rgb_info", "RGB Camera Information", "str"),
            ("camera_rgb_resolution", "RGB Camera Resolution", "str"),
            ("camera_rgb_sensor_size", "RGB Camera Sensor Size", "str"),
            ("camera_rgb_spatial_resolution", "RGB Spatial Resolution", "str"),
            ("camera_rgb_ground_sampling_distance",
            "RGB Ground Sampling Distance", "number"),
            ("camera_rgb_optical_zoomscale",
            "RGB Optical Zoom Scale", "number"),
            ("camera_rgb_digital_zoomscale",
            "RGB Digital Zoom Scale", "number"),
            ("camera_rgb_fov_wide_or_narrow",
            "RGB FOV Wide/Narrow", "str"),
            ("camera_rgb_horizontal_fov",
            "RGB Horizontal FOV", "number"),
            ("camera_rgb_vertical_fov",
            "RGB Vertical FOV", "number"),
            ("camera_rgb_shutter_type",
            "RGB Shutter Type", "str"),
            ("camera_rgb_frame_rate_hz",
            "RGB Frame Rate (Hz)", "number"),
            ("camera_rgb_iso_range",
            "RGB ISO Range", "str"),
            ("camera_rgb_aperture",
            "RGB Aperture", "str"),

            # --------------------------------------------------------
            # IR / THERMAL CAMERA
            # --------------------------------------------------------
            ("ir_camera", "IR Camera", "str"),
            ("ir_camera_company", "IR Camera Company", "str"),
            ("ir_camera_model", "IR Camera Model", "str"),
            ("ir_camera_info", "IR Camera Information", "str"),
            ("ir_camera_resolution", "IR Camera Resolution", "str"),
            ("ir_camera_NETD_milli_kelvin",
            "IR Camera NETD (mK)", "number"),
            ("ir_camera_radiometric_sensor_cap",
            "IR Radiometric Sensor Capability", "str"),
            ("ir_camera_spectral_band_type",
            "IR Spectral Band Type", "str"),
            ("ir_camera_spectral_band_min_nm",
            "IR Spectral Band Minimum (nm)", "number"),
            ("ir_camera_spectral_band_max_nm",
            "IR Spectral Band Maximum (nm)", "number"),
            ("ir_camera_spectral_band_value",
            "IR Spectral Band Value", "number"),
            ("ir_camera_fov_wide_or_narrow",
            "IR FOV Wide/Narrow", "str"),
            ("ir_camera_horizontal_fov",
            "IR Horizontal FOV", "number"),
            ("ir_camera_vertical_fov",
            "IR Vertical FOV", "number"),
            ("ir_camera_frame_rate_hz",
            "IR Frame Rate (Hz)", "number"),
            ("ir_camera_ground_sampling_distance",
            "IR Ground Sampling Distance", "number"),
            ("ir_camera_temperature_range",
            "IR Temperature Range", "str"),
            ("ir_camera_accuracy",
            "IR Camera Accuracy", "number"),

            # --------------------------------------------------------
            # THERMAL CAMERA
            # --------------------------------------------------------
            ("camera_thermal", "Thermal Camera", "str"),
            ("camera_thermal_company", "Thermal Camera Company", "str"),
            ("camera_thermal_model", "Thermal Camera Model", "str"),
            ("camera_thermal_info", "Thermal Camera Information", "str"),
            ("camera_thermal_resolution", "Thermal Camera Resolution", "str"),
            ("camera_thermal_fov_wide_or_narrow",
            "Thermal FOV Wide/Narrow", "str"),
            ("camera_thermal_horizontal_fov",
            "Thermal Horizontal FOV", "number"),
            ("camera_thermal_vertical_fov",
            "Thermal Vertical FOV", "number"),
            ("camera_thermal_frame_rate_hz",
            "Thermal Frame Rate (Hz)", "number"),
            ("camera_thermal_NETD_milli_kelvin",
            "Thermal NETD (mK)", "number"),
            ("camera_thermal_radiometric_sensor_cap",
            "Thermal Radiometric Sensor Capability", "str"),
            ("camera_thermal_spectral_band_type",
            "Thermal Spectral Band Type", "str"),
            ("camera_thermal_spectral_band_min_nm",
            "Thermal Spectral Band Minimum (nm)", "number"),
            ("camera_thermal_spectral_band_max_nm",
            "Thermal Spectral Band Maximum (nm)", "number"),
            ("camera_thermal_spectral_band_value",
            "Thermal Spectral Band Value", "number"),
            ("camera_thermal_ground_sampling_distance",
            "Thermal Ground Sampling Distance", "number"),
            ("camera_thermal_temperature_range",
            "Thermal Temperature Range", "str"),
            ("camera_thermal_accuracy",
            "Thermal Camera Accuracy", "number"),

            # --------------------------------------------------------
            # MULTISPECTRAL CAMERA
            # --------------------------------------------------------
            ("multispectral_camera", "Multispectral Camera", "str"),
            ("multispectral_camera_company",
            "Multispectral Camera Company", "str"),
            ("multispectral_camera_model",
            "Multispectral Camera Model", "str"),
            ("multispectral_camera_info",
            "Multispectral Camera Information", "str"),
            ("multispectral_ground_sampling_distance",
            "Multispectral Ground Sampling Distance", "number"),
            ("multispectral_resolution",
            "Multispectral Resolution", "str"),
            ("multispectral_bands",
            "Multispectral Bands", "str"),
            ("multispectral_red_band_nm",
            "Multispectral Red Band (nm)", "str"),
            ("multispectral_green_band_nm",
            "Multispectral Green Band (nm)", "str"),
            ("multispectral_blue_band_nm",
            "Multispectral Blue Band (nm)", "str"),
            ("multispectral_nir_band_nm",
            "Multispectral NIR Band (nm)", "str"),
            ("multispectral_rededge_band_nm",
            "Multispectral Red Edge Band (nm)", "str"),
            ("multispectral_thermal_band_nm",
            "Multispectral Thermal Band (nm)", "str"),
            ("multispectral_camera_wide_or_narrow",
            "Multispectral Camera Wide/Narrow", "str"),
            ("multispectral_horizontal_fov",
            "Multispectral Horizontal FOV", "number"),
            ("multispectral_vertical_fov",
            "Multispectral Vertical FOV", "number"),
            ("multispectral_camera_frame_rate_hz",
            "Multispectral Frame Rate (Hz)", "number"),
            ("multispectral_sensor_type",
            "Multispectral Sensor Type", "str"),

            # --------------------------------------------------------
            # HYPERSPECTRAL CAMERA
            # --------------------------------------------------------
            ("hyperspectral_camera", "Hyperspectral Camera", "str"),
            ("hyperspectral_company", "Hyperspectral Company", "str"),
            ("hyperspectral_model", "Hyperspectral Model", "str"),
            ("hyperspectral_info", "Hyperspectral Information", "str"),
            ("hyperspectral_resolution", "Hyperspectral Resolution", "str"),
            ("hyperspectral_number_of_bands",
            "Hyperspectral Number of Bands", "number"),
            ("hyperspectral_spectral_range_nm",
            "Hyperspectral Spectral Range (nm)", "str"),
            ("hyperspectral_spectral_resolution_nm",
            "Hyperspectral Spectral Resolution (nm)", "number"),
            ("hyperspectral_spatial_resolution",
            "Hyperspectral Spatial Resolution", "str"),
            ("hyperspectral_frame_rate_hz",
            "Hyperspectral Frame Rate (Hz)", "number"),

            # --------------------------------------------------------
            # RADAR
            # --------------------------------------------------------
            ("radar", "Radar", "str"),
            ("radar_company", "Radar Company", "str"),
            ("radar_model", "Radar Model", "str"),
            ("radar_type", "Radar Type", "str"),
            ("radar_frequency_ghz", "Radar Frequency (GHz)", "number"),
            ("radar_measuring_range_m",
            "Radar Measuring Range (m)", "number"),
            ("radar_accuracy_m", "Radar Accuracy (m)", "number"),
            ("radar_horizontal_fov", "Radar Horizontal FOV", "number"),
            ("radar_vertical_fov", "Radar Vertical FOV", "number"),
            ("radar_detection_capability",
            "Radar Detection Capability", "str"),
            ("radar_info", "Radar Information", "str"),

            # --------------------------------------------------------
            # ULTRASONIC
            # --------------------------------------------------------
            ("ultrasonic", "Ultrasonic", "str"),
            ("ultrasonic_company", "Ultrasonic Company", "str"),
            ("ultrasonic_model", "Ultrasonic Model", "str"),
            ("ultrasonic_measuring_range_m",
            "Ultrasonic Measuring Range (m)", "number"),
            ("ultrasonic_accuracy_m",
            "Ultrasonic Accuracy (m)", "number"),
            ("ultrasonic_frequency_khz",
            "Ultrasonic Frequency (kHz)", "number"),
            ("ultrasonic_fov", "Ultrasonic FOV", "number"),
            ("ultrasonic_info", "Ultrasonic Information", "str"),

            # --------------------------------------------------------
            # SONAR
            # --------------------------------------------------------
            ("sonar", "Sonar", "str"),
            ("sonar_company", "Sonar Company", "str"),
            ("sonar_model", "Sonar Model", "str"),
            ("sonar_type", "Sonar Type", "str"),
            ("sonar_frequency_khz", "Sonar Frequency (kHz)", "number"),
            ("sonar_range_m", "Sonar Range (m)", "number"),
            ("sonar_depth_m", "Sonar Depth (m)", "number"),
            ("sonar_accuracy_m", "Sonar Accuracy (m)", "number"),
            ("sonar_info", "Sonar Information", "str"),

            # --------------------------------------------------------
            # GNSS / GPS
            # --------------------------------------------------------
            ("gps_and_gnss_cap", "GPS/GNSS Capability", "str"),
            ("gps_and_gnss_company_and_model",
            "GPS/GNSS Company and Model", "str"),
            ("gnss_constellations", "GNSS Constellations", "str"),
            ("gnss_gps_supported", "GPS Supported", "str"),
            ("gnss_glonass_supported", "GLONASS Supported", "str"),
            ("gnss_galileo_supported", "Galileo Supported", "str"),
            ("gnss_beidou_supported", "BeiDou Supported", "str"),
            ("gnss_qzss_supported", "QZSS Supported", "str"),
            ("gnss_rtk_supported", "RTK Supported", "str"),
            ("gnss_ppk_supported", "PPK Supported", "str"),
            ("gnss_horizontal_accuracy_m",
            "GNSS Horizontal Accuracy (m)", "number"),
            ("gnss_vertical_accuracy_m",
            "GNSS Vertical Accuracy (m)", "number"),
            ("gnss_update_rate_hz",
            "GNSS Update Rate (Hz)", "number"),

            # --------------------------------------------------------
            # IMU
            # --------------------------------------------------------
            ("imu", "IMU", "str"),
            ("imu_company", "IMU Company", "str"),
            ("imu_model", "IMU Model", "str"),
            ("imu_accelerometer_range_g",
            "IMU Accelerometer Range (g)", "number"),
            ("imu_accelerometer_accuracy",
            "IMU Accelerometer Accuracy", "number"),
            ("imu_gyro_range_dps",
            "IMU Gyro Range (dps)", "number"),
            ("imu_gyro_accuracy",
            "IMU Gyro Accuracy", "number"),
            ("imu_sampling_rate_hz",
            "IMU Sampling Rate (Hz)", "number"),
            ("imu_info", "IMU Information", "str"),

            # --------------------------------------------------------
            # MAGNETOMETER
            # --------------------------------------------------------
            ("magnetometer", "Magnetometer", "str"),
            ("magnetometer_company", "Magnetometer Company", "str"),
            ("magnetometer_model", "Magnetometer Model", "str"),
            ("magnetometer_range_ut",
            "Magnetometer Range (uT)", "number"),
            ("magnetometer_accuracy_ut",
            "Magnetometer Accuracy (uT)", "number"),
            ("magnetometer_sampling_rate_hz",
            "Magnetometer Sampling Rate (Hz)", "number"),
            ("magnetometer_info", "Magnetometer Information", "str"),

            # --------------------------------------------------------
            # BAROMETER
            # --------------------------------------------------------
            ("barometer", "Barometer", "str"),
            ("barometer_company", "Barometer Company", "str"),
            ("barometer_model", "Barometer Model", "str"),
            ("barometer_pressure_range",
            "Barometer Pressure Range", "str"),
            ("barometer_accuracy_pa",
            "Barometer Accuracy (Pa)", "number"),
            ("barometer_sampling_rate_hz",
            "Barometer Sampling Rate (Hz)", "number"),
            ("barometer_info", "Barometer Information", "str"),

            # --------------------------------------------------------
            # MICROPHONE
            # --------------------------------------------------------
            ("microphone", "Microphone", "str"),
            ("microphone_company", "Microphone Company", "str"),
            ("microphone_model", "Microphone Model", "str"),
            ("microphone_frequency_range",
            "Microphone Frequency Range", "str"),
            ("microphone_sampling_rate_hz",
            "Microphone Sampling Rate (Hz)", "number"),
            ("microphone_channels",
            "Microphone Channels", "number"),
            ("microphone_info", "Microphone Information", "str"),

            # --------------------------------------------------------
            # ENVIRONMENTAL SENSORS
            # --------------------------------------------------------
            ("temperature_sensor", "Temperature Sensor", "str"),
            ("temperature_sensor_range",
            "Temperature Sensor Range", "str"),
            ("temperature_sensor_accuracy",
            "Temperature Sensor Accuracy", "number"),

            ("humidity_sensor", "Humidity Sensor", "str"),
            ("humidity_sensor_range",
            "Humidity Sensor Range", "str"),
            ("humidity_sensor_accuracy",
            "Humidity Sensor Accuracy", "number"),

            ("pressure_sensor", "Pressure Sensor", "str"),
            ("pressure_sensor_range",
            "Pressure Sensor Range", "str"),
            ("pressure_sensor_accuracy",
            "Pressure Sensor Accuracy", "number"),

            ("air_quality_sensor", "Air Quality Sensor", "str"),
            ("gas_sensor", "Gas Sensor", "str"),
            ("gas_sensor_type", "Gas Sensor Type", "str"),

            # --------------------------------------------------------
            # SPEAKER
            # --------------------------------------------------------
            ("speaker", "Speaker", "str"),
            ("speaker_company", "Speaker Company", "str"),
            ("speaker_model", "Speaker Model", "str"),
            ("speaker_power_w", "Speaker Power (W)", "number"),
            ("speaker_frequency_range",
            "Speaker Frequency Range", "str"),

            # --------------------------------------------------------
            # PAYLOAD
            # --------------------------------------------------------
            ("payload_capable", "Payload Capable", "str"),
            ("payload_capacity_kg",
            "Payload Capacity (kg)", "number"),

            # --------------------------------------------------------
            # FLIGHT CONTROLLER / PROPULSION
            # --------------------------------------------------------
            ("flightcontroller", "Flight Controller", "str"),
            ("motor_kv_model", "Motor KV / Model", "str"),
            ("props_inch", "Propellers (inch)", "str"),
            ("prop_material", "Propeller Material", "str"),
            ("esc_rating_and_info", "ESC Rating / Information", "str"),

            # --------------------------------------------------------
            # FRAME
            # --------------------------------------------------------
            ("frame_type", "Frame Type", "str"),
            ("frame_material", "Frame Material", "str"),
            ("frame_name", "Frame Name", "str"),

            # --------------------------------------------------------
            # BATTERY / TELEMETRY
            # --------------------------------------------------------
            ("battery_rating_s", "Battery Rating (S)", "str"),
            ("battery_capacity_c", "Battery Capacity (C)", "str"),

            ("telemetry_type", "Telemetry Type", "str"),
            ("telemetry_range", "Telemetry Range", "str"),
            ("telemetry_info", "Telemetry Information", "str"),

            ("bvlos_capable", "BVLOS Capable", "str"),

            # --------------------------------------------------------
            # WEIGHT
            # --------------------------------------------------------
            ("weight_drone", "Drone Weight", "number"),
            ("weight_drone_along_payload",
            "Drone Weight With Payload", "number"),

           # --------------------------------------------------------
           # FLIGHT PERFORMANCE
           # --------------------------------------------------------
           ("flight_time_min", "Flight Time (minutes)", "number"),
           ("cruise_speed_mps", "Cruise Speed (m/s)", "number"),
           ("max_speed_mps", "Maximum Speed (m/s)", "number"),

           # --------------------------------------------------------
           # BATTERY CAPACITY
           # --------------------------------------------------------
           ("battery_capacity_mah", "Battery Capacity (mAh)", "number"),
           ("battery_capacity_wh", "Battery Capacity (Wh)", "number"),

           # --------------------------------------------------------
           # OPERATING ENVIRONMENT
           # --------------------------------------------------------
           ("wind_limit_mps", "Maximum Wind Limit (m/s)", "number"),
           ("operating_temperature_range",
            "Operating Temperature Range", "str"),
           ("ip_rating", "IP Rating", "str"),
           ("night_capable", "Night Capable (yes/no)", "str"),

           # --------------------------------------------------------
           # ALTITUDE AND LAUNCH
           # --------------------------------------------------------
           ("max_altitude_m", "Maximum Operating Altitude (m)", "number"),
           ("launch_type", "Launch Type (VTOL/runway/hand launch)", "str"),

           # --------------------------------------------------------
           # CAMERA MOUNT
           # --------------------------------------------------------
           ("camera_mount_type", "Camera Mount (gimbal/fixed)", "str"),

           # --------------------------------------------------------
           # POWER CONSUMPTION
           # --------------------------------------------------------
           ("hover_power_draw_w", "Hover Power Draw (W)", "number"),
           ("cruise_power_draw_w", "Cruise Power Draw (W)", "number"),

        ]

        # Store the entries so add_dronedb() can access them.
        self.drone_entries = {}

        # ============================================================
        # SCROLLABLE FORM
        # ============================================================

        outer_frame = tk.Frame(add_drones_window, bg="black")
        outer_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer_frame,
            bg="black",
            highlightthickness=0
        )

        scrollbar = tk.Scrollbar(
            outer_frame,
            orient="vertical",
            command=canvas.yview
        )

        form_frame = tk.Frame(canvas, bg="black")

        form_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window(
            (0, 0),
            window=form_frame,
            anchor="nw"
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # Mouse wheel support
        def mouse_wheel(event):
            canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )

        canvas.bind_all(
            "<MouseWheel>",
            mouse_wheel
        )

        # ============================================================
        # FORM TITLE
        # ============================================================

        title_label = tk.Label(
            form_frame,
            text="ADD NEW DRONE",
            bg="black",
            fg="white",
            font=("Arial", 16, "bold")
        )

        title_label.grid(
            row=0,
            column=0,
            columnspan=2,
            pady=15
        )

        # ============================================================
        # AUTOMATIC INFORMATION
        # ============================================================

        auto_label = tk.Label(
            form_frame,
            text="Drone ID and MAV System ID will be generated automatically.",
            bg="black",
            fg="yellow"
        )

        auto_label.grid(
            row=1,
            column=0,
            columnspan=2,
            pady=(0, 15)
        )

        # ============================================================
        # CREATE INPUTS
        # ============================================================

        for row_number, (column_name, display_name, data_type) in enumerate(
            fields,
            start=2
        ):

            label = tk.Label(
                form_frame,
                text=display_name + ":",
                bg="black",
                fg="white",
                anchor="w",
                width=35
            )

            label.grid(
                row=row_number,
                column=0,
                padx=10,
                pady=4,
                sticky="w"
            )

            entry = tk.Entry(
                form_frame,
                width=45
            )

            entry.grid(
                row=row_number,
                column=1,
                padx=10,
                pady=4,
                sticky="w"
            )

            self.drone_entries[column_name] = (
                entry,
                data_type
            )

        # ============================================================
        # SUBMIT BUTTON
        # ============================================================

        submit_row = len(fields) + 3

        submit_button = tk.Button(
            form_frame,
            text="SUBMIT DRONE",
            command=self.add_dronedb,
            width=25
        )

        submit_button.grid(
            row=submit_row,
            column=0,
            columnspan=2,
            pady=25
        )
    def add_dronedb(self):
        """
        Save a drone and its sensor/equipment information.

        The old design stored every sensor and camera field in one enormous
        drones table. That caused MySQL error 1118:

            Row size too large (> 8126)

        This version splits the data into several related tables while keeping
        the existing Tkinter form unchanged.
        """

        db = Database()

        try:
            db.connect_db(self.userid)

            # ============================================================
            # 1. MAIN DRONES TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drones (
                    drone_id VARCHAR(40) NOT NULL,
                    mav_sys_id VARCHAR(40) NOT NULL,

                    connection_type VARCHAR(20) NOT NULL,
                    ip_address VARCHAR(60) NOT NULL,

                    flightcontroller VARCHAR(50) NOT NULL,
                    motor_kv_model VARCHAR(40) NOT NULL,
                    props_inch VARCHAR(30) NOT NULL,
                    prop_material VARCHAR(30) NOT NULL,
                    esc_rating_and_info VARCHAR(100) NOT NULL,

                    frame_type VARCHAR(20) NOT NULL,
                    frame_material VARCHAR(30) NOT NULL,
                    frame_name VARCHAR(30) NOT NULL,

                    battery_rating_s VARCHAR(20) NOT NULL,
                    battery_capacity_c VARCHAR(40) NOT NULL,

                    telemetry_type VARCHAR(30) NOT NULL,
                    telemetry_range VARCHAR(50) NOT NULL,
                    telemetry_info TEXT NOT NULL,

                    bvlos_capable VARCHAR(30) NOT NULL,

                    weight_drone DECIMAL(15,7) NOT NULL,
                    weight_drone_along_payload DECIMAL(15,7) NOT NULL,

                    PRIMARY KEY (drone_id),
                    UNIQUE KEY uk_mav_sys_id (mav_sys_id)
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

           # ============================================================
           # DRONE PERFORMANCE TABLE
           # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_performance (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    flight_time_min DECIMAL(15,6) NOT NULL DEFAULT 0,
                    cruise_speed_mps DECIMAL(15,6) NOT NULL DEFAULT 0,
                    max_speed_mps DECIMAL(15,6) NOT NULL DEFAULT 0,

                    battery_capacity_mah DECIMAL(15,6) NOT NULL DEFAULT 0,
                    battery_capacity_wh DECIMAL(15,6) NOT NULL DEFAULT 0,

                    wind_limit_mps DECIMAL(15,6) NOT NULL DEFAULT 0,
                    operating_temperature_range VARCHAR(100) NOT NULL DEFAULT '',
                    ip_rating VARCHAR(20) NOT NULL DEFAULT '',
                    night_capable VARCHAR(7) NOT NULL DEFAULT '',

                    max_altitude_m DECIMAL(15,6) NOT NULL DEFAULT 0,
                    launch_type VARCHAR(30) NOT NULL DEFAULT '',
                    camera_mount_type VARCHAR(30) NOT NULL DEFAULT '',

                    hover_power_draw_w DECIMAL(15,6) NOT NULL DEFAULT 0,
                    cruise_power_draw_w DECIMAL(15,6) NOT NULL DEFAULT 0,

                    CONSTRAINT fk_drone_performance_drone
                        FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)


            # ============================================================
            # 2. LIDAR TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_lidar (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    lidar VARCHAR(7) NOT NULL,
                    lidar_company VARCHAR(50) NOT NULL,
                    lidar_model VARCHAR(50) NOT NULL,
                    lidar_type VARCHAR(30) NOT NULL,

                    lidar_measuring_dist DECIMAL(15,6) NOT NULL,
                    lidar_accuracy DECIMAL(15,6) NOT NULL,
                    lidar_horizontal_fov DECIMAL(15,6) NOT NULL,
                    lidar_vertical_fov DECIMAL(15,6) NOT NULL,
                    lidar_scan_rate_hz DECIMAL(15,6) NOT NULL,
                    lidar_point_rate_hz DECIMAL(15,6) NOT NULL,
                    lidar_wavelength_nm DECIMAL(15,6) NOT NULL,
                    lidar_beam_divergence DECIMAL(15,6) NOT NULL,

                    lidar_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 3. RGB CAMERA TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_rgb_camera (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    camera_rgb VARCHAR(7) NOT NULL,
                    camera_rgb_company VARCHAR(50) NOT NULL,
                    camera_rgb_model VARCHAR(50) NOT NULL,
                    camera_rgb_info TEXT NOT NULL,

                    camera_rgb_resolution VARCHAR(35) NOT NULL,
                    camera_rgb_sensor_size VARCHAR(30) NOT NULL,
                    camera_rgb_spatial_resolution VARCHAR(35) NOT NULL,

                    camera_rgb_ground_sampling_distance DECIMAL(15,6) NOT NULL,
                    camera_rgb_optical_zoomscale DECIMAL(15,6) NOT NULL,
                    camera_rgb_digital_zoomscale DECIMAL(15,6) NOT NULL,

                    camera_rgb_fov_wide_or_narrow VARCHAR(30) NOT NULL,
                    camera_rgb_horizontal_fov DECIMAL(15,6) NOT NULL,
                    camera_rgb_vertical_fov DECIMAL(15,6) NOT NULL,

                    camera_rgb_shutter_type VARCHAR(30) NOT NULL,
                    camera_rgb_frame_rate_hz DECIMAL(15,6) NOT NULL,

                    camera_rgb_iso_range VARCHAR(30) NOT NULL,
                    camera_rgb_aperture VARCHAR(30) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 4. IR CAMERA TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_ir_camera (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    ir_camera VARCHAR(7) NOT NULL,
                    ir_camera_company VARCHAR(50) NOT NULL,
                    ir_camera_model VARCHAR(50) NOT NULL,
                    ir_camera_info TEXT NOT NULL,

                    ir_camera_resolution VARCHAR(30) NOT NULL,
                    ir_camera_NETD_milli_kelvin DECIMAL(15,6) NOT NULL,

                    ir_camera_radiometric_sensor_cap VARCHAR(20) NOT NULL,
                    ir_camera_spectral_band_type VARCHAR(30) NOT NULL,

                    ir_camera_spectral_band_min_nm DECIMAL(15,6) NOT NULL,
                    ir_camera_spectral_band_max_nm DECIMAL(15,6) NOT NULL,
                    ir_camera_spectral_band_value DECIMAL(15,6) NOT NULL,

                    ir_camera_fov_wide_or_narrow VARCHAR(30) NOT NULL,
                    ir_camera_horizontal_fov DECIMAL(15,6) NOT NULL,
                    ir_camera_vertical_fov DECIMAL(15,6) NOT NULL,

                    ir_camera_frame_rate_hz DECIMAL(15,6) NOT NULL,
                    ir_camera_ground_sampling_distance DECIMAL(15,6) NOT NULL,

                    ir_camera_temperature_range VARCHAR(50) NOT NULL,
                    ir_camera_accuracy DECIMAL(15,6) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 5. THERMAL CAMERA TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_thermal_camera (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    camera_thermal VARCHAR(7) NOT NULL,
                    camera_thermal_company VARCHAR(50) NOT NULL,
                    camera_thermal_model VARCHAR(50) NOT NULL,
                    camera_thermal_info TEXT NOT NULL,

                    camera_thermal_resolution VARCHAR(30) NOT NULL,
                    camera_thermal_fov_wide_or_narrow VARCHAR(30) NOT NULL,

                    camera_thermal_horizontal_fov DECIMAL(15,6) NOT NULL,
                    camera_thermal_vertical_fov DECIMAL(15,6) NOT NULL,
                    camera_thermal_frame_rate_hz DECIMAL(15,6) NOT NULL,

                    camera_thermal_NETD_milli_kelvin DECIMAL(15,6) NOT NULL,
                    camera_thermal_radiometric_sensor_cap VARCHAR(20) NOT NULL,
                    camera_thermal_spectral_band_type VARCHAR(30) NOT NULL,

                    camera_thermal_spectral_band_min_nm DECIMAL(15,6) NOT NULL,
                    camera_thermal_spectral_band_max_nm DECIMAL(15,6) NOT NULL,
                    camera_thermal_spectral_band_value DECIMAL(15,6) NOT NULL,

                    camera_thermal_ground_sampling_distance DECIMAL(15,6) NOT NULL,
                    camera_thermal_temperature_range VARCHAR(50) NOT NULL,
                    camera_thermal_accuracy DECIMAL(15,6) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 6. MULTISPECTRAL CAMERA TABLE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_multispectral (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    multispectral_camera VARCHAR(7) NOT NULL,
                    multispectral_camera_company VARCHAR(50) NOT NULL,
                    multispectral_camera_model VARCHAR(50) NOT NULL,
                    multispectral_camera_info TEXT NOT NULL,

                    multispectral_ground_sampling_distance DECIMAL(15,6) NOT NULL,
                    multispectral_resolution VARCHAR(30) NOT NULL,
                    multispectral_bands TEXT NOT NULL,

                    multispectral_red_band_nm VARCHAR(30) NOT NULL,
                    multispectral_green_band_nm VARCHAR(30) NOT NULL,
                    multispectral_blue_band_nm VARCHAR(30) NOT NULL,
                    multispectral_nir_band_nm VARCHAR(30) NOT NULL,
                    multispectral_rededge_band_nm VARCHAR(30) NOT NULL,
                    multispectral_thermal_band_nm VARCHAR(30) NOT NULL,

                    multispectral_camera_wide_or_narrow VARCHAR(30) NOT NULL,
                    multispectral_horizontal_fov DECIMAL(15,6) NOT NULL,
                    multispectral_vertical_fov DECIMAL(15,6) NOT NULL,

                    multispectral_camera_frame_rate_hz DECIMAL(15,6) NOT NULL,
                    multispectral_sensor_type VARCHAR(50) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 7. HYPERSPECTRAL CAMERA
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_hyperspectral (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    hyperspectral_camera VARCHAR(7) NOT NULL,
                    hyperspectral_company VARCHAR(50) NOT NULL,
                    hyperspectral_model VARCHAR(50) NOT NULL,
                    hyperspectral_info TEXT NOT NULL,

                    hyperspectral_resolution VARCHAR(30) NOT NULL,
                    hyperspectral_number_of_bands INT NOT NULL,

                    hyperspectral_spectral_range_nm VARCHAR(50) NOT NULL,
                    hyperspectral_spectral_resolution_nm DECIMAL(15,6) NOT NULL,

                    hyperspectral_spatial_resolution VARCHAR(30) NOT NULL,
                    hyperspectral_frame_rate_hz DECIMAL(15,6) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 8. RADAR
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_radar (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    radar VARCHAR(7) NOT NULL,
                    radar_company VARCHAR(50) NOT NULL,
                    radar_model VARCHAR(50) NOT NULL,
                    radar_type VARCHAR(30) NOT NULL,

                    radar_frequency_ghz DECIMAL(15,6) NOT NULL,
                    radar_measuring_range_m DECIMAL(15,6) NOT NULL,
                    radar_accuracy_m DECIMAL(15,6) NOT NULL,

                    radar_horizontal_fov DECIMAL(15,6) NOT NULL,
                    radar_vertical_fov DECIMAL(15,6) NOT NULL,

                    radar_detection_capability TEXT NOT NULL,
                    radar_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 9. ULTRASONIC
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_ultrasonic (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    ultrasonic VARCHAR(7) NOT NULL,
                    ultrasonic_company VARCHAR(50) NOT NULL,
                    ultrasonic_model VARCHAR(50) NOT NULL,

                    ultrasonic_measuring_range_m DECIMAL(15,6) NOT NULL,
                    ultrasonic_accuracy_m DECIMAL(15,6) NOT NULL,
                    ultrasonic_frequency_khz DECIMAL(15,6) NOT NULL,
                    ultrasonic_fov DECIMAL(15,6) NOT NULL,

                    ultrasonic_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 10. SONAR
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_sonar (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    sonar VARCHAR(7) NOT NULL,
                    sonar_company VARCHAR(50) NOT NULL,
                    sonar_model VARCHAR(50) NOT NULL,
                    sonar_type VARCHAR(30) NOT NULL,

                    sonar_frequency_khz DECIMAL(15,6) NOT NULL,
                    sonar_range_m DECIMAL(15,6) NOT NULL,
                    sonar_depth_m DECIMAL(15,6) NOT NULL,
                    sonar_accuracy_m DECIMAL(15,6) NOT NULL,

                    sonar_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 11. GNSS
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_gnss (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    gps_and_gnss_cap VARCHAR(20) NOT NULL,
                    gps_and_gnss_company_and_model VARCHAR(50) NOT NULL,
                    gnss_constellations TEXT NOT NULL,

                    gnss_gps_supported VARCHAR(7) NOT NULL,
                    gnss_glonass_supported VARCHAR(7) NOT NULL,
                    gnss_galileo_supported VARCHAR(7) NOT NULL,
                    gnss_beidou_supported VARCHAR(7) NOT NULL,
                    gnss_qzss_supported VARCHAR(7) NOT NULL,

                    gnss_rtk_supported VARCHAR(7) NOT NULL,
                    gnss_ppk_supported VARCHAR(7) NOT NULL,

                    gnss_horizontal_accuracy_m DECIMAL(15,6) NOT NULL,
                    gnss_vertical_accuracy_m DECIMAL(15,6) NOT NULL,
                    gnss_update_rate_hz DECIMAL(15,6) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 12. IMU
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_imu (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    imu VARCHAR(7) NOT NULL,
                    imu_company VARCHAR(50) NOT NULL,
                    imu_model VARCHAR(50) NOT NULL,

                    imu_accelerometer_range_g DECIMAL(15,6) NOT NULL,
                    imu_accelerometer_accuracy DECIMAL(15,6) NOT NULL,

                    imu_gyro_range_dps DECIMAL(15,6) NOT NULL,
                    imu_gyro_accuracy DECIMAL(15,6) NOT NULL,

                    imu_sampling_rate_hz DECIMAL(15,6) NOT NULL,

                    imu_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 13. MAGNETOMETER
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_magnetometer (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    magnetometer VARCHAR(7) NOT NULL,
                    magnetometer_company VARCHAR(50) NOT NULL,
                    magnetometer_model VARCHAR(50) NOT NULL,

                    magnetometer_range_ut DECIMAL(15,6) NOT NULL,
                    magnetometer_accuracy_ut DECIMAL(15,6) NOT NULL,
                    magnetometer_sampling_rate_hz DECIMAL(15,6) NOT NULL,

                    magnetometer_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 14. BAROMETER
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_barometer (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    barometer VARCHAR(7) NOT NULL,
                    barometer_company VARCHAR(50) NOT NULL,
                    barometer_model VARCHAR(50) NOT NULL,

                    barometer_pressure_range VARCHAR(50) NOT NULL,
                    barometer_accuracy_pa DECIMAL(15,6) NOT NULL,
                    barometer_sampling_rate_hz DECIMAL(15,6) NOT NULL,

                    barometer_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 15. MICROPHONE
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_microphone (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    microphone VARCHAR(7) NOT NULL,
                    microphone_company VARCHAR(50) NOT NULL,
                    microphone_model VARCHAR(50) NOT NULL,

                    microphone_frequency_range VARCHAR(50) NOT NULL,
                    microphone_sampling_rate_hz DECIMAL(15,6) NOT NULL,
                    microphone_channels INT NOT NULL,

                    microphone_info TEXT NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 16. ENVIRONMENTAL SENSORS
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_environmental (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    temperature_sensor VARCHAR(7) NOT NULL,
                    temperature_sensor_range VARCHAR(50) NOT NULL,
                    temperature_sensor_accuracy DECIMAL(15,6) NOT NULL,

                    humidity_sensor VARCHAR(7) NOT NULL,
                    humidity_sensor_range VARCHAR(50) NOT NULL,
                    humidity_sensor_accuracy DECIMAL(15,6) NOT NULL,

                    pressure_sensor VARCHAR(7) NOT NULL,
                    pressure_sensor_range VARCHAR(50) NOT NULL,
                    pressure_sensor_accuracy DECIMAL(15,6) NOT NULL,

                    air_quality_sensor VARCHAR(7) NOT NULL,

                    gas_sensor VARCHAR(7) NOT NULL,
                    gas_sensor_type VARCHAR(50) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 17. SPEAKER
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_speaker (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    speaker VARCHAR(7) NOT NULL,
                    speaker_company VARCHAR(50) NOT NULL,
                    speaker_model VARCHAR(50) NOT NULL,

                    speaker_power_w DECIMAL(15,6) NOT NULL,
                    speaker_frequency_range VARCHAR(50) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)

            # ============================================================
            # 18. PAYLOAD
            # ============================================================

            db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drone_payload (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    drone_id VARCHAR(40) NOT NULL,

                    payload_capable VARCHAR(7) NOT NULL,
                    payload_capacity_kg DECIMAL(15,6) NOT NULL,

                    FOREIGN KEY (drone_id)
                        REFERENCES drones(drone_id)
                        ON DELETE CASCADE
                )
                ENGINE=InnoDB
                ROW_FORMAT=DYNAMIC
            """)


            # ============================================================
            # GENERATE IDS
            # ============================================================

            drone_id = str(uuid.uuid4())

            mav_sys_id = None

            for _ in range(255):

                candidate = str(secrets.randbelow(255) + 1)

                db.cursor.execute(
                    """
                    SELECT 1
                    FROM drones
                    WHERE mav_sys_id = %s
                    LIMIT 1
                    """,
                    (candidate,)
                )

                if db.cursor.fetchone() is None:
                    mav_sys_id = candidate
                    break

            if mav_sys_id is None:
                raise RuntimeError(
                    "No available MAV system ID remains in the range 1-255."
                )

            # ============================================================
            # COLLECT FORM DATA
            # ============================================================

            values = {
                "drone_id": drone_id,
                "mav_sys_id": mav_sys_id
            }

            integer_columns = {
                "hyperspectral_number_of_bands",
                "microphone_channels"
            }

            for column_name, (entry, data_type) in self.drone_entries.items():

                raw_value = entry.get().strip()

                if data_type == "number":

                    if raw_value == "":
                        value = 0

                    else:

                        try:

                            if column_name in integer_columns:
                                value = int(raw_value)
                            else:
                                value = float(raw_value)

                        except ValueError:

                            raise ValueError(
                                f"'{raw_value}' is not a valid number "
                                f"for {column_name}."
                            )

                else:

                    value = raw_value

                values[column_name] = value

            # ============================================================
            # HELPER FUNCTION
            # ============================================================

            def insert_from_values(table_name, column_names):

                columns = ", ".join(
                    f"`{column}`"
                    for column in column_names
                )

                placeholders = ", ".join(
                    ["%s"] * len(column_names)
                )

                query = f"""
                    INSERT INTO `{table_name}`
                    (`drone_id`, {columns})
                    VALUES (%s, {placeholders})
                """

                data = [drone_id]

                for column in column_names:
                    data.append(values[column])

                db.cursor.execute(
                    query,
                    tuple(data)
                )

            # ============================================================
            # INSERT MAIN DRONE
            # ============================================================

            insert_from_values(
                "drones",
                [
                    "mav_sys_id",
                    "connection_type",
                    "ip_address",

                    "flightcontroller",
                    "motor_kv_model",
                    "props_inch",
                    "prop_material",
                    "esc_rating_and_info",

                    "frame_type",
                    "frame_material",
                    "frame_name",

                    "battery_rating_s",
                    "battery_capacity_c",

                    "telemetry_type",
                    "telemetry_range",
                    "telemetry_info",

                    "bvlos_capable",

                    "weight_drone",
                    "weight_drone_along_payload"
                ]
            )

            # ============================================================
            # INSERT LIDAR
            # ============================================================

            insert_from_values(
                "drone_lidar",
                [
                    "lidar",
                    "lidar_company",
                    "lidar_model",
                    "lidar_type",
                    "lidar_measuring_dist",
                    "lidar_accuracy",
                    "lidar_horizontal_fov",
                    "lidar_vertical_fov",
                    "lidar_scan_rate_hz",
                    "lidar_point_rate_hz",
                    "lidar_wavelength_nm",
                    "lidar_beam_divergence",
                    "lidar_info"
                ]
            )

            # ============================================================
            # INSERT RGB CAMERA
            # ============================================================

            insert_from_values(
                "drone_rgb_camera",
                [
                    "camera_rgb",
                    "camera_rgb_company",
                    "camera_rgb_model",
                    "camera_rgb_info",
                    "camera_rgb_resolution",
                    "camera_rgb_sensor_size",
                    "camera_rgb_spatial_resolution",
                    "camera_rgb_ground_sampling_distance",
                    "camera_rgb_optical_zoomscale",
                    "camera_rgb_digital_zoomscale",
                    "camera_rgb_fov_wide_or_narrow",
                    "camera_rgb_horizontal_fov",
                    "camera_rgb_vertical_fov",
                    "camera_rgb_shutter_type",
                    "camera_rgb_frame_rate_hz",
                    "camera_rgb_iso_range",
                    "camera_rgb_aperture"
                ]
            )

            # ============================================================
            # INSERT IR CAMERA
            # ============================================================

            insert_from_values(
                "drone_ir_camera",
                [
                    "ir_camera",
                    "ir_camera_company",
                    "ir_camera_model",
                    "ir_camera_info",
                    "ir_camera_resolution",
                    "ir_camera_NETD_milli_kelvin",
                    "ir_camera_radiometric_sensor_cap",
                    "ir_camera_spectral_band_type",
                    "ir_camera_spectral_band_min_nm",
                    "ir_camera_spectral_band_max_nm",
                    "ir_camera_spectral_band_value",
                    "ir_camera_fov_wide_or_narrow",
                    "ir_camera_horizontal_fov",
                    "ir_camera_vertical_fov",
                    "ir_camera_frame_rate_hz",
                    "ir_camera_ground_sampling_distance",
                    "ir_camera_temperature_range",
                    "ir_camera_accuracy"
                ]
            )

            # ============================================================
            # INSERT THERMAL CAMERA
            # ============================================================

            insert_from_values(
                "drone_thermal_camera",
                [
                    "camera_thermal",
                    "camera_thermal_company",
                    "camera_thermal_model",
                    "camera_thermal_info",
                    "camera_thermal_resolution",
                    "camera_thermal_fov_wide_or_narrow",
                    "camera_thermal_horizontal_fov",
                    "camera_thermal_vertical_fov",
                    "camera_thermal_frame_rate_hz",
                    "camera_thermal_NETD_milli_kelvin",
                    "camera_thermal_radiometric_sensor_cap",
                    "camera_thermal_spectral_band_type",
                    "camera_thermal_spectral_band_min_nm",
                    "camera_thermal_spectral_band_max_nm",
                    "camera_thermal_spectral_band_value",
                    "camera_thermal_ground_sampling_distance",
                    "camera_thermal_temperature_range",
                    "camera_thermal_accuracy"
                ]
            )

            # ============================================================
            # INSERT MULTISPECTRAL
            # ============================================================

            insert_from_values(
                "drone_multispectral",
                [
                    "multispectral_camera",
                    "multispectral_camera_company",
                    "multispectral_camera_model",
                    "multispectral_camera_info",
                    "multispectral_ground_sampling_distance",
                    "multispectral_resolution",
                    "multispectral_bands",
                    "multispectral_red_band_nm",
                    "multispectral_green_band_nm",
                    "multispectral_blue_band_nm",
                    "multispectral_nir_band_nm",
                    "multispectral_rededge_band_nm",
                    "multispectral_thermal_band_nm",
                    "multispectral_camera_wide_or_narrow",
                    "multispectral_horizontal_fov",
                    "multispectral_vertical_fov",
                    "multispectral_camera_frame_rate_hz",
                    "multispectral_sensor_type"
                ]
            )

            # ============================================================
            # INSERT HYPERSPECTRAL
            # ============================================================

            insert_from_values(
                "drone_hyperspectral",
                [
                    "hyperspectral_camera",
                    "hyperspectral_company",
                    "hyperspectral_model",
                    "hyperspectral_info",
                    "hyperspectral_resolution",
                    "hyperspectral_number_of_bands",
                    "hyperspectral_spectral_range_nm",
                    "hyperspectral_spectral_resolution_nm",
                    "hyperspectral_spatial_resolution",
                    "hyperspectral_frame_rate_hz"
                ]
            )

            # ============================================================
            # INSERT RADAR
            # ============================================================

            insert_from_values(
                "drone_radar",
                [
                    "radar",
                    "radar_company",
                    "radar_model",
                    "radar_type",
                    "radar_frequency_ghz",
                    "radar_measuring_range_m",
                    "radar_accuracy_m",
                    "radar_horizontal_fov",
                    "radar_vertical_fov",
                    "radar_detection_capability",
                    "radar_info"
                ]
            )

            # ============================================================
            # INSERT ULTRASONIC
            # ============================================================

            insert_from_values(
                "drone_ultrasonic",
                [
                    "ultrasonic",
                    "ultrasonic_company",
                    "ultrasonic_model",
                    "ultrasonic_measuring_range_m",
                    "ultrasonic_accuracy_m",
                    "ultrasonic_frequency_khz",
                    "ultrasonic_fov",
                    "ultrasonic_info"
                ]
            )

            # ============================================================
            # INSERT SONAR
            # ============================================================

            insert_from_values(
                "drone_sonar",
                [
                    "sonar",
                    "sonar_company",
                    "sonar_model",
                    "sonar_type",
                    "sonar_frequency_khz",
                    "sonar_range_m",
                    "sonar_depth_m",
                    "sonar_accuracy_m",
                    "sonar_info"
                ]
            )

            # ============================================================
            # INSERT GNSS
            # ============================================================

            insert_from_values(
                "drone_gnss",
                [
                    "gps_and_gnss_cap",
                    "gps_and_gnss_company_and_model",
                    "gnss_constellations",
                    "gnss_gps_supported",
                    "gnss_glonass_supported",
                    "gnss_galileo_supported",
                    "gnss_beidou_supported",
                    "gnss_qzss_supported",
                    "gnss_rtk_supported",
                    "gnss_ppk_supported",
                    "gnss_horizontal_accuracy_m",
                    "gnss_vertical_accuracy_m",
                    "gnss_update_rate_hz"
                ]
            )

            # ============================================================
            # INSERT IMU
            # ============================================================

            insert_from_values(
                "drone_imu",
                [
                    "imu",
                    "imu_company",
                    "imu_model",
                    "imu_accelerometer_range_g",
                    "imu_accelerometer_accuracy",
                    "imu_gyro_range_dps",
                    "imu_gyro_accuracy",
                    "imu_sampling_rate_hz",
                    "imu_info"
                ]
            )

            # ============================================================
            # INSERT MAGNETOMETER
            # ============================================================

            insert_from_values(
                "drone_magnetometer",
                [
                    "magnetometer",
                    "magnetometer_company",
                    "magnetometer_model",
                    "magnetometer_range_ut",
                    "magnetometer_accuracy_ut",
                    "magnetometer_sampling_rate_hz",
                    "magnetometer_info"
                ]
            )

            # ============================================================
            # INSERT BAROMETER
            # ============================================================

            insert_from_values(
                "drone_barometer",
                [
                    "barometer",
                    "barometer_company",
                    "barometer_model",
                    "barometer_pressure_range",
                    "barometer_accuracy_pa",
                    "barometer_sampling_rate_hz",
                    "barometer_info"
                ]
            )

            # ============================================================
            # INSERT MICROPHONE
            # ============================================================

            insert_from_values(
                "drone_microphone",
                [
                    "microphone",
                    "microphone_company",
                    "microphone_model",
                    "microphone_frequency_range",
                    "microphone_sampling_rate_hz",
                    "microphone_channels",
                    "microphone_info"
                ]
            )

            # ============================================================
            # INSERT ENVIRONMENTAL
            # ============================================================

            insert_from_values(
                "drone_environmental",
                [
                    "temperature_sensor",
                    "temperature_sensor_range",
                    "temperature_sensor_accuracy",

                    "humidity_sensor",
                    "humidity_sensor_range",
                    "humidity_sensor_accuracy",

                    "pressure_sensor",
                    "pressure_sensor_range",
                    "pressure_sensor_accuracy",

                    "air_quality_sensor",

                    "gas_sensor",
                    "gas_sensor_type"
                ]
            )

            # ============================================================
            # INSERT SPEAKER
            # ============================================================

            insert_from_values(
                "drone_speaker",
                [
                    "speaker",
                    "speaker_company",
                    "speaker_model",
                    "speaker_power_w",
                    "speaker_frequency_range"
                ]
            )

            # ============================================================
            # INSERT PAYLOAD
            # ============================================================

            insert_from_values(
                "drone_payload",
                [
                    "payload_capable",
                    "payload_capacity_kg"
                ]
            )

           # ============================================================
           # INSERT DRONE PERFORMANCE
           # ============================================================

            insert_from_values(
               "drone_performance",
               [
                   "flight_time_min",
                   "cruise_speed_mps",
                   "max_speed_mps",

                   "battery_capacity_mah",
                   "battery_capacity_wh",

                   "wind_limit_mps",
                   "operating_temperature_range",
                   "ip_rating",
                   "night_capable",

                   "max_altitude_m",
                   "launch_type",
                   "camera_mount_type",

                   "hover_power_draw_w",
                   "cruise_power_draw_w"
               ]
            )

            # ============================================================
            # COMMIT EVERYTHING
            # ============================================================

            db.conn.commit()

            messagebox.showinfo(
                "Success",
                f"Drone has been added successfully.\n\n"
                f"Drone ID: {drone_id}\n"
                f"MAV System ID: {mav_sys_id}"
            )

        except Exception as error:

            try:
                db.conn.rollback()
            except Exception:
                pass

            try:
                Database.log_file(error)
            except Exception:
                pass

            messagebox.showerror(
                "Error",
                f"Cannot enter the drone into the database.\n\n{error}"
            )

        finally:

            try:
                db.disconnect_db()
            except Exception:
                pass
    def on_close(self):
        print("Closing application...")
        self.stop_event.set()
        self.root.destroy()
    # Paste inside your class in main.py (replaces the existing disaster_worker).
    # Needs in main.py:  from datetime import datetime
    #                    from another import Disaster   (your existing import)
    #
    # Date control (optional): set these attributes anywhere, e.g. from a UI/test:
    #     self.disaster_from_date = "2024-04-01"
    #     self.disaster_to_date   = "2024-04-10"
    # If both are None (default) -> today..today.

    def disaster_worker(self):
        while not self.stop_event.is_set():
            try:
                # ---------------------------------------------
                # Get currently selected locations
                # ---------------------------------------------
                locations = list(self.locations_on_screen)

                if not locations:
                    self.stop_event.wait(5)
                    continue

                print()
                print("=" * 70)
                print("CHECKING DISASTER DATA")
                print("LOCATIONS:", locations)
                print("=" * 70)

                # ---------------------------------------------
                # Create Disaster object
                # ---------------------------------------------
                #disaster_data = Disaster(locations)

                # ---------------------------------------------
                # Dates: user-selected if set, otherwise today
                # (Disaster.resolve_date_range handles the default)
                # ---------------------------------------------
                from_date = getattr(self, "disaster_from_date", None)
                to_date = getattr(self, "disaster_to_date", None)

                '''from_date, to_date = disaster_data.resolve_date_range(
                    from_date,
                    to_date,
                )'''

                print("FROM:", from_date)
                print("TO:", to_date)

                # ---------------------------------------------
                # Get disaster data
                # ---------------------------------------------
                '''data = disaster_data.get_disaster_data(
                    fromdate=from_date,
                    todate=to_date,
                    save=True,
                )'''

                # ---------------------------------------------
                # Process results
                # ---------------------------------------------
                '''for city, disasters in data.items():

                    print()
                    print("-" * 70)
                    print("LOCATION:", city)
                    print("EVENT COUNT:", len(disasters))
                    print("-" * 70)

                    for disaster in disasters:

                        print("TYPE:", disaster.get("event_type"))
                        print("EVENT ID:", disaster.get("event_id"))
                        print("NAME:", disaster.get("name"))
                        print("ALERT:", disaster.get("alert_level"))
                        print("SEVERITY:", disaster.get("severity"))
                        print("COUNTRY:", disaster.get("country"))
                        print("FROM:", disaster.get("from_date"))
                        print("TO:", disaster.get("to_date"))
                        print("COORDINATES:", disaster.get("coordinates"))
                        print("-" * 40)

                # ---------------------------------------------
                # Store latest data
                # ---------------------------------------------
                self.disaster_data = data

                print()
                print("DISASTER CHECK COMPLETE")'''

            except Exception as error:
                Database.log_file(error)

            # Optional polling interval
            self.stop_event.wait(300)

    '''def disaster_worker(self):
        while not self.stop_event.is_set():
            try:
                # ---------------------------------------------
                # Get currently selected locations
                # ---------------------------------------------
                locations = list(self.locations_on_screen)

                if not locations:
                    self.stop_event.wait(5)
                    continue

                print()
                print("=" * 70)
                print("CHECKING DISASTER DATA")
                print("LOCATIONS:", locations)
                print("=" * 70)

                # ---------------------------------------------
                # Create Disaster object
                # ---------------------------------------------
                disaster_data = Disaster(locations)

                # ---------------------------------------------
                # Current date ONLY
                # ---------------------------------------------
                today = datetime.now().strftime("%Y-%m-%d")

                from_date = today
                to_date = today

                print("FROM:", from_date)
                print("TO:", to_date)

                # ---------------------------------------------
                # Get today's disaster data
                # ---------------------------------------------
                data = disaster_data.get_disaster_data(
                    fromdate=from_date,
                    todate=to_date,
                    save=True,
                )

                # ---------------------------------------------
                # Process results
                # ---------------------------------------------
                for city, disasters in data.items():

                    print()
                    print("-" * 70)
                    print("LOCATION:", city)
                    print("EVENT COUNT:", len(disasters))
                    print("-" * 70)

                    for disaster in disasters:

                        print("TYPE:", disaster.get("event_type"))
                        print("EVENT ID:", disaster.get("event_id"))
                        print("NAME:", disaster.get("name"))
                        print("ALERT:", disaster.get("alert_level"))
                        print("SEVERITY:", disaster.get("severity"))
                        print("COUNTRY:", disaster.get("country"))
                        print("FROM:", disaster.get("from_date"))
                        print("TO:", disaster.get("to_date"))
                        print("COORDINATES:", disaster.get("coordinates"))
                        print("-" * 40)

                # ---------------------------------------------
                # Store latest data
                # ---------------------------------------------
                self.disaster_data = data

                print()
                print("DISASTER CHECK COMPLETE")

            except Exception as error:
                Database.log_file(error)

            # Optional polling interval
            self.stop_event.wait(300)  # check every 5 minutes
        '''

    def select_location(self):
        selection_window = tk.Toplevel(self.root)
        selection_window.title('select the location')
        selection_window.geometry('720x420')
        selection_window.configure(bg='black')
        #frames 
        selection_frame = tk.Frame(selection_window , height=40)
        selection_frame.pack(fill='x' , pady=10)
        #labels
        selection_label = tk.Label(selection_frame , text='Select the location')
        selection_label.pack(side='left' , padx=10)
        #btn
        select_btn = tk.Button(selection_frame , text='submit' , command=self.show_selection)
        select_btn.pack(side='left')
        db = Database()
        db.connect_db()
        try:
            db.cursor.execute(f'show tables from {self.userid}')
            data = db.cursor.fetchall()
            table_lst = []
            for tables in data:
                 if not tables[0].startswith(('drone', 'Drones')) and tables[0]!= 'location_metadata':
                    table_lst.append(tables[0])
            self.selected_location = tk.StringVar()
            dropdown = ttk.Combobox(selection_frame , textvariable=self.selected_location , values=table_lst , state='readonly')
            dropdown.pack(side='left' , padx=10)
        except Exception as dberror:
                Database.log_file(dberror)
        finally:
            db.disconnect_db()
    def show_selection(self):
        location = self.selected_location.get()
        db = Database()
        db.connect_db()
        try:
            db.cursor.execute('select * from location_metadata where table_name = %s',(location,))
            data = db.cursor.fetchone()
            geojson_file = data[3]
            center_lat = float(data[1])
            center_lon = float(data[2]) 
            with open(geojson_file, "r", encoding="utf-8") as f:
                geojson = json.load(f)
            latitudes = []
            longitudes = []
            for feature in geojson["features"]:
            
                geometry = feature["geometry"]
            
                if geometry["type"] == "Polygon":
                        polygons = [geometry["coordinates"]]
            
                elif geometry["type"] == "MultiPolygon":
                        polygons = geometry["coordinates"]
            
                else:
                        continue
                for polygon in polygons:
            
                    outer_ring = polygon[0]
                    points = []
            
                    for lon, lat in outer_ring:
                        points.append((lat, lon))
                        latitudes.append(lat)
                        longitudes.append(lon)
            
                    poly = self.map_widget.set_polygon(points)
                    self.geojson_polygons.append(poly)
            if location not in self.locations_on_screen: 
                self.locations_on_screen.append(location) 
            print("Selected locations:", self.locations_on_screen)
                    # ---------- Center map ----------
            if latitudes and longitudes:            
                self.map_widget.set_position(center_lat, center_lon)
                self.map_widget.set_zoom(12)
        except Exception as dbs:
            Database.log_file(dbs)
        finally:
            db.disconnect_db()
    
    def add_location(self):
        location_window = tk.Toplevel(self.root)
        location_window.title('add new location')
        location_window.geometry("720x420")
        location_window.configure(bg='black')

        #frames
        country_frame = tk.Frame(location_window , height=40)
        country_frame.pack(fill='x' , pady=10)
        state_frame = tk.Frame(location_window , height=40)
        state_frame.pack(fill='x' , pady=10)
        city_frame = tk.Frame(location_window , height=40)
        city_frame.pack(fill='x' , pady=10)
        submit_frame = tk.Frame(location_window , height=30)
        submit_frame.pack(side='bottom' , fill='x')

        #labels 
        country_label = tk.Label(country_frame , text='Enter the name of the country: ')
        country_label.pack(side='left' , padx=10) 
        state_label = tk.Label(state_frame , text='Enter the name of the state: ')
        state_label.pack(side='left' , padx=10)
        city_label = tk.Label(city_frame , text="Enter the name of the city: ")
        city_label.pack(side='left' , padx=10)
        #entryboxes 
        self.country_text = tk.Entry(country_frame)
        self.country_text.pack(side='left' , padx=10)
        self.state_text = tk.Entry(state_frame)
        self.state_text.pack(side='left' , padx=10)
        self.city_text = tk.Entry(city_frame)
        self.city_text.pack(side='left' , padx=10)


        #buttons
        submit_btn = tk.Button(submit_frame , text='Submit' , command=self.get_database_data)
        submit_btn.pack(side='right' , padx=10)
    def make_pattern(self , lat, lon):
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        lat_str = f"{abs(lat):02d}"
        lon_str = f"{abs(lon):03d}"
        return re.compile(
            rf'^Copernicus_DSM_10_{lat_dir}{lat_str}_00_{lon_dir}{lon_str}_00_DEM'
        )
    def load_datasets(self, file_path_tiff, file_path_geojson, table_name):
   
           # ---------- Load and clip raster ----------
           with rasterio.open(file_path_tiff) as raster:
   
               gdf = gpd.read_file(file_path_geojson)
   
               clipped, transform = mask(
                   raster,
                   gdf.geometry,
                   crop=True
               )
   
               self.population = clipped[0].astype(float)
               self.transform = transform
               self.nodata = raster.nodata
               self.crs = raster.crs
   
           # ---------- Replace NoData with 0 ----------
           self.population[self.population == self.nodata] = 0
   
           print(f"Population raster shape : {self.population.shape}")
           print(f"Total grids            : {self.population.size}")
   
           # ---------- Remove previously drawn polygons ----------
           for polygon in self.geojson_polygons:
               polygon.delete()
   
           self.geojson_polygons.clear()
   
           # ---------- Draw GeoJSON ----------
           with open(file_path_geojson, "r", encoding="utf-8") as f:
               geojson = json.load(f)
   
           latitudes = []
           longitudes = []
   
           for feature in geojson["features"]:
   
               geometry = feature["geometry"]
   
               if geometry["type"] == "Polygon":
                   polygons = [geometry["coordinates"]]
   
               elif geometry["type"] == "MultiPolygon":
                   polygons = geometry["coordinates"]
   
               else:
                   continue
   
               for polygon in polygons:
   
                   outer_ring = polygon[0]
                   points = []
   
                   for lon, lat in outer_ring:
                       points.append((lat, lon))
                       latitudes.append(lat)
                       longitudes.append(lon)
   
                   poly = self.map_widget.set_polygon(points)
                   self.geojson_polygons.append(poly)
   
           # ---------- Center map ----------
           if latitudes and longitudes:
               center_lat = sum(latitudes) / len(latitudes)
               center_lon = sum(longitudes) / len(longitudes)
   
               self.map_widget.set_position(center_lat, center_lon)
               self.map_widget.set_zoom(12)
   
           # ---------- Generate database records ----------
           db = Database()
           db.connect_db(self.userid)
           batch_size = 5000
           records = []
           query = f"""INSERT INTO {table_name} (grid_no,zone_no,active_search_grid_no,center_lat,center_lon,population_density,elevation_m,slope_angle_deg,building_count,average_building_area,total_building_area) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
           metadata_query = f"""
                CREATE TABLE IF NOT EXISTS location_metadata (
                    `table_name` VARCHAR(100) NOT NULL PRIMARY KEY,
                    `center_lat` DECIMAL(10,6) NOT NULL,
                    `center_lon` DECIMAL(10,6) NOT NULL,
                    `geojson_path` TEXT NOT NULL,
                    `population_raster_path` TEXT NOT NULL
                )
            """
           db.cursor.execute(metadata_query)
           metadata_insert = f"""
                INSERT INTO location_metadata
                (
                    `table_name`,
                    `center_lat`,
                    `center_lon`,
                    `geojson_path`,
                    `population_raster_path`
                )
                VALUES (%s, %s, %s, %s, %s)
            """
           db.cursor.execute(metadata_insert,(table_name,center_lat,center_lon,file_path_geojson,file_path_tiff))
           db.conn.commit()
           geo4326 = gdf.to_crs(epsg=4326)
   
           min_lon, min_lat, max_lon, max_lat = geo4326.total_bounds
   
           lat_start = math.floor(min_lat)
           lat_end = math.floor(max_lat)
   
           lon_start = math.floor(min_lon)
           lon_end = math.floor(max_lon)
   
           tiles = []
   
           for tile_lat in range(lat_start, lat_end + 1):
               for tile_lon in range(lon_start, lon_end + 1):
                   tiles.append((tile_lat, tile_lon))
           tiles = sorted(set(tiles))
           tile_list_path = Path("required_dem_tiles.csv")
           with tile_list_path.open("w", newline="", encoding="utf-8") as csvfile:
               writer = csv.writer(csvfile)
               writer.writerow(["latitude", "longitude"])
               for tile_lat, tile_lon in tiles:
                   writer.writerow([tile_lat, tile_lon])
           print(f"Tile list saved to: {tile_list_path.resolve()}")
           output = "Required DEM Tiles\n\n"
           for tile_lat, tile_lon in tiles:
               output += f"Latitude {tile_lat}°, Longitude {tile_lon}°\n"
   
           output += f"\nTotal Tiles : {len(tiles)}"
           windows = tk.Toplevel(self.root)
           windows.title("Required DEM Tiles")
           windows.geometry("600x600")
           windows.resizable(True, True)
           windows.transient(self.root)
           windows.lift()
           windows.focus_force()
           frame = ttk.Frame(windows, padding=10)
           frame.pack(fill="both", expand=True)
           scrollbar = ttk.Scrollbar(frame, orient="vertical")
           scrollbar.pack(side="right", fill="y")
           text_area = tk.Text(
                frame,
                wrap="word",
                yscrollcommand=scrollbar.set,
                font=("Arial", 11),
                padx=8,
                pady=8
            )
           text_area.pack(side="left", fill="both", expand=True)
           scrollbar.config(command=text_area.yview) 

           text_area.insert("1.0", output)
           text_area.config(state="disabled")
           windows.wait_window()
           selected_files = []
          #SELECT ALL REQUIRED DEM TILES

           while len(selected_files) < len(tiles):

                file_tiff = filedialog.askopenfilename(
                    title=f"Select DEM Tile {len(selected_files)+1} of {len(tiles)}",
                    filetypes=[("TIFF Files", "*.tif *.tiff")]
                )

                if not file_tiff:
                    messagebox.showwarning(
                        "Selection Required",
                        "Please select a DEM file."
                    )
                    continue

                # Prevent duplicate selection
                if any(tile["path"] == file_tiff for tile in selected_files):
                    messagebox.showwarning(
                        "Duplicate",
                        "DEM already selected."
                    )
                    continue

                # Check the DEM file
                with rasterio.open(file_tiff) as dem:

                    selected_files.append({
                        "path": file_tiff,
                        "crs": dem.crs,
                        "bounds": dem.bounds,
                        "transform": dem.transform,
                        "nodata": dem.nodata
                    })
            # MATCH SELECTED FILES TO REQUIRED TILES
       

           matched_dem_files = []

           for lat_tiles, lon_tiles in tiles:

                pattern = self.make_pattern(lat_tiles, lon_tiles)

                matched = None

                for tile in selected_files:

                    filename = os.path.basename(tile["path"])

                    if pattern.match(filename):
                        matched = tile["path"]
                        break

                if matched is None:

                    raise Exception(
                        f"Required DEM tile not found for "
                        f"Latitude {lat_tiles}, Longitude {lon_tiles}"
                    )

                matched_dem_files.append(matched)

                print(
                    f"Matched DEM tile: "
                    f"{os.path.basename(matched)}"
                )


           print(f"\nTotal DEM tiles matched: {len(matched_dem_files)}")


            # MERGE ALL DEM TILES
          

           print("\nMerging DEM tiles...")

           dem_sources = []

           try:

                for dem_path in matched_dem_files:

                    src = rasterio.open(dem_path)
                    dem_sources.append(src)

                # Check CRS compatibility
                first_dem_crs = dem_sources[0].crs

                for src in dem_sources:

                    if src.crs != first_dem_crs:

                        raise Exception(
                            "All DEM tiles must have the same CRS."
                        )

                dem_nodata = dem_sources[0].nodata

                merged_dem, merged_transform = merge(
                    dem_sources,
                    nodata=dem_nodata
                )

           finally:

                for src in dem_sources:
                    src.close()


           print("DEM merge completed.")

           print(
                "Merged DEM shape:",
                merged_dem.shape
            )

           print(
                "DEM CRS:",
                first_dem_crs
            )

            #  RESAMPLE DEM TO WORLDPOP 100m GRID
          
           print("\nCalculating average elevation for WorldPop grid...")

           n_rows, n_cols = self.population.shape
           average_elevation_grid = np.full(
                (n_rows, n_cols),
                np.nan,
                dtype=np.float32
            )

           reproject(
                source=merged_dem[0],
                destination=average_elevation_grid,

                src_transform=merged_transform,
                src_crs=first_dem_crs,

                dst_transform=self.transform,
                dst_crs=self.crs,

                src_nodata=dem_nodata,
                dst_nodata=np.nan,

                resampling=Resampling.average
            )


           print("Elevation resampling completed.")

           valid_elevation = np.count_nonzero(
                ~np.isnan(average_elevation_grid)
            )

           print(
                f"Valid elevation cells: "
                f"{valid_elevation:,}"
            )
           print("\nCalculating slope from merged DEM...")
           dem_array = merged_dem[0].astype(np.float64)
           if dem_nodata is not None:
                dem_array = np.where(dem_array == dem_nodata, np.nan, dem_array)
           pixel_size_x_deg = merged_transform.a          
           pixel_size_y_deg = -merged_transform.e       
           if first_dem_crs.is_geographic:
                n_rows_dem, n_cols_dem = dem_array.shape
                rows = np.arange(n_rows_dem)
                lat_of_row = merged_transform.f + (rows + 0.5) * merged_transform.e
                meters_per_deg_lat = 111_320.0
                meters_per_deg_lon = 111_320.0 * np.cos(np.radians(lat_of_row))
                pixel_size_y_m = pixel_size_y_deg * meters_per_deg_lat 
                pixel_size_x_m = pixel_size_x_deg * meters_per_deg_lon
                dz_dy, _ = np.gradient(dem_array, pixel_size_y_m, 1)
                dz_dx = np.empty_like(dem_array)
                for i in range(n_rows_dem):
                    dz_dx[i, :] = np.gradient(dem_array[i, :], pixel_size_x_m[i])
           else:
                pixel_size_x_m = pixel_size_x_deg  
                pixel_size_y_m = pixel_size_y_deg
                dz_dy, dz_dx = np.gradient(dem_array, pixel_size_y_m, pixel_size_x_m)
           slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
           slope_deg = np.degrees(slope_rad).astype(np.float32)
           slope_deg = np.where(np.isnan(dem_array), np.nan, slope_deg)
           print("Slope calculation completed.")
           print("Slope range (deg):", np.nanmin(slope_deg), "-", np.nanmax(slope_deg))
           print("\nResampling slope to WorldPop grid...")
           average_slope_grid = np.full((n_rows, n_cols),np.nan,dtype=np.float32)
           reproject(source=slope_deg,destination=average_slope_grid,src_transform=merged_transform,src_crs=first_dem_crs,dst_transform=self.transform,dst_crs=self.crs,src_nodata=np.nan,dst_nodata=np.nan,resampling=Resampling.average)
           print("Slope resampling completed.")
           valid_slope = np.count_nonzero(~np.isnan(average_slope_grid))
           print(f"Valid slope cells: {valid_slope:,}")

            # building density files 

            # ==============================================================
            # LOAD VIDA BUILDING FOOTPRINTS FROM ZIP
            # ==============================================================
            # The ZIP can contain many S2-partitioned GeoParquet files.
            # We process every .parquet/.geoparquet file, regardless of
            # whether bf_source contains Google, Microsoft, OSM, or a mix.
            # Each building is assigned to ONE WorldPop cell using its
            # centroid. The entire area_in_meters goes to that cell.
            # ==============================================================
           file_path_buildings_zip = filedialog.askopenfilename(title="Select VIDA Open Buildings ZIP file",filetypes=[("ZIP Files", "*.zip")])
           if not file_path_buildings_zip:
               raise Exception("Building ZIP file is required.")
           print("\nLoading VIDA building footprints...")
           # (WorldPop row, col) -> [building area, building area, ...]
           building_areas_by_pixel = {}
           building_source_counts = {"Google": 0,"Microsoft": 0,"OSM": 0, "Other": 0}
           total_buildings_read = 0
           total_buildings_assigned = 0
           #building_temp_dir = tempfile.mkdtemp(prefix="vida_buildings_")
                # ----------------------------------------------------------
        # AUTOMATICALLY FIND EXTERNAL DRIVE
        # ----------------------------------------------------------

# ----------------------------------------------------------
# FIND EXTERNAL DRIVE ON MACOS
# ----------------------------------------------------------
           volumes_dir = "/Volumes"

           print("\nMounted volumes:")
           for name in os.listdir(volumes_dir):
                print("  -", name)

# Ignore common macOS/system volumes
           ignored = {
                "Macintosh HD",
                "Macintosh HD - Data",
                "Preboot",
                "Recovery","VM"}

           external_drives = []

           for name in os.listdir(volumes_dir):
                path = os.path.join(volumes_dir, name)

           if name not in ignored and os.path.isdir(path):
                external_drives.append(path)

           if not external_drives:
            raise Exception(
                "\nNo external drive detected in /Volumes.\n"
                "Check that the drive appears in Finder under Locations."
            )

# Show detected drives
           print("\nExternal drives detected:")
           for drive in external_drives:
                print("  -", drive)

# Use the first external drive
           external_drive = external_drives[0]

# Create temporary folder on external drive
           external_temp_root = os.path.join(external_drive,"vida_temp")

           os.makedirs(external_temp_root, exist_ok=True)

           building_temp_dir = tempfile.mkdtemp(
                prefix="vida_buildings_",
                dir=external_temp_root)

           print("\nUsing external storage:")
           print(building_temp_dir)

        # Create temporary VIDA folder on external drive
           external_temp_root = os.path.join(external_drive, "vida_temp")
           os.makedirs(external_temp_root, exist_ok=True)

           building_temp_dir = tempfile.mkdtemp(prefix="vida_buildings_",dir=external_temp_root)

           print(f"Building files will be extracted to:")
           print(building_temp_dir)
           try:
               # ----------------------------------------------------------
                # EXTRACT ZIP AND FIND ALL S2 GEOPARQUET FILES
                # ----------------------------------------------------------
                print(f"Extracting building ZIP:\n",f"{file_path_buildings_zip}")
                with zipfile.ZipFile(file_path_buildings_zip,"r") as  zip_ref:
                    zip_ref.extractall(building_temp_dir)
                parquet_files = []
                for root, dirs, files in os.walk(building_temp_dir):
                    dirs[:] = [d for d in dirs if d not in {"__MACOSX"} and not d.startswith(".")]
                    for filename in files:
                        if filename.lower().endswith((".parquet", ".geoparquet")):
                            parquet_files.append( os.path.join(root, filename))
                parquet_files.sort()
                print( f"Found {len(parquet_files):,} ",f"GeoParquet/S2 files.")
                if not parquet_files:
                     raise Exception("No GeoParquet files were found inside ","the building ZIP file.")
                raster_left, raster_bottom, raster_right, raster_top = (rasterio.transform.array_bounds(n_rows,n_cols,self.transform))
                raster_bbox = box(raster_left,raster_bottom , raster_right , raster_top)
                # ----------------------------------------------------------
                # PROCESS EACH S2 FILE ONE AT A TIME
                # ----------------------------------------------------------
                for file_index, parquet_file in enumerate(parquet_files,start=1):
                    print(f"\nProcessing building file ",f"{file_index:,}/{len(parquet_files):,}: ",f"{os.path.basename(parquet_file)}")
                    buildings = gpd.read_parquet(parquet_file)
                    if buildings.empty:
                        print("  Empty file - skipped.")
                        continue
                    total_buildings_read += len(buildings)
                    # geometry and area_in_meters are the only required fields.
                    # bf_source is deliberately optional.
                    if "geometry" not in buildings.columns:
                        print("  geometry column missing - skipped.")
                        continue
                    if "area_in_meters" not in buildings.columns:
                        print("  area_in_meters column missing - skipped.")
                        continue
                    if buildings.crs is None:
                        print("  CRS missing - skipped.")
                        continue
                    #Remove invalid/empty geometry.
                    buildings = buildings[
                        buildings.geometry.notna()
                        & ~buildings.geometry.is_empty
                    ].copy()
                    if buildings.empty:
                        continue
                    # Clean VIDA footprint area.
                    buildings["area_in_meters"] = pd.to_numeric(
                        buildings["area_in_meters"],
                        errors="coerce"
                    )
                    buildings = buildings[
                        buildings["area_in_meters"].notna()
                        & np.isfinite(buildings["area_in_meters"])
                        & (buildings["area_in_meters"] > 0)
                    ].copy()
                    if buildings.empty:
                        continue
                     # Optional source statistics only; source does not control
                    # whether a building is processed.
                    if "bf_source" in buildings.columns:
                        source_counts = (
                            buildings["bf_source"]
                            .fillna("Other")
                            .value_counts()
                        )
                        for source, count in source_counts.items():
                             source_name = str(source)
                             if source_name in building_source_counts:
                                building_source_counts[source_name] += int(count)
                             else:
                                building_source_counts["Other"] += int(count)
                   # Keep a copy in WorldPop CRS for the spatial filtering
                    buildings_worldpop = buildings
                    if buildings_worldpop.crs != self.crs:
                        buildings_worldpop = buildings_worldpop.to_crs(self.crs)
                    buildings_worldpop = buildings_worldpop[ buildings_worldpop.geometry.intersects(raster_bbox)].copy()
                    if buildings_worldpop.empty:
                        continue
                    # ----------------------------------------------------------
                    # Calculate centroid in a projected CRS
                    # ----------------------------------------------------------
                    if self.crs.is_geographic:
                        raster_center_lon = (raster_left + raster_right) / 2
                        raster_center_lat = (raster_bottom + raster_top ) / 2
                        utm_zone = int((raster_center_lon + 180) / 6) + 1
                        if raster_center_lat >= 0:
                            utm_epsg = 32600 + utm_zone
                        else:
                            utm_epsg = 32700 + utm_zone
                        buildings_projected = buildings_worldpop.to_crs(epsg=utm_epsg)
                        centroids_projected = buildings_projected.geometry.centroid
                        # Convert centroid back to WorldPop CRS
                        centroids = centroids_projected.to_crs(self.crs)
                    else:
                        centroids = buildings_worldpop.geometry.centroid
                     # Performance filter. Final assignment is still centroid-based.
                    buildings = buildings[buildings.geometry.intersects(raster_bbox)].copy()
                    if buildings.empty:
                        continue
                     # ------------------------------------------------------
                    # CENTROID -> WORLDPOP ROW/COL
                    # ------------------------------------------------------
                    centroids = buildings.geometry.centroid
                    for centroid, area in zip(centroids,buildings["area_in_meters"]):
                        if centroid is None or centroid.is_empty:
                            continue
                        area = float(area)
                        if not np.isfinite(area) or area <= 0:
                            continue
                        # rasterio.rowcol returns (row, col).
                        building_row, building_col = rowcol(
                            self.transform,
                            centroid.x,
                            centroid.y
                        )
                        if (
                            building_row < 0
                            or building_row >= n_rows
                            or building_col < 0
                            or building_col >= n_cols
                        ):
                            continue
                        pixel_key = (
                            int(building_row),
                            int(building_col)
                        )
                        if pixel_key not in building_areas_by_pixel:
                            building_areas_by_pixel[pixel_key] = []
                         # WHOLE building footprint area goes to the centroid cell.
                        building_areas_by_pixel[pixel_key].append(area)
                        total_buildings_assigned += 1
                    del centroids 
                    del buildings
                    if (
                        file_index == 1
                        or file_index % 10 == 0
                        or file_index == len(parquet_files)
                    ):
                         print(
                            f"  Buildings assigned so far: "
                            f"{total_buildings_assigned:,}"
                        )
                print("\nBuilding processing completed.")
                print( f"S2/GeoParquet files processed: {len(parquet_files):,}")
                print(f"Building records read: {total_buildings_read:,}")
                print( f"Building centroids assigned: {total_buildings_assigned:,}")
                print(f"WorldPop cells containing buildings: ",f"{len(building_areas_by_pixel):,}")
                print("\nBuilding source counts:")
                print(f"  Google    : {building_source_counts['Google']:,}")
                print(f"  Microsoft : {building_source_counts['Microsoft']:,}")
                print(f"  OSM       : {building_source_counts['OSM']:,}")
                print(f"  Other     : {building_source_counts['Other']:,}")
           finally:
                shutil.rmtree(building_temp_dir,ignore_errors=True)
                print("Temporary VIDA building files removed.")

            #creating database records 
           active_search_grid_no = 0 
           district_rows = (n_rows + 99) // 100

           districts_per_row = (n_cols + 99) // 100
           try:

                # -----------------------------------------------------
                # DISTRICT
                # 100 x 100 WorldPop pixels
                # = 10 km x 10 km
                # -----------------------------------------------------

                for district_row in range(district_rows):

                    for district_col in range(districts_per_row):

                        grid_no = (
                            district_row * districts_per_row
                            + district_col
                            + 1
                        )

                        zone_no = 0

                        # -------------------------------------------------
                        # ZONE
                        # 10 x 10 WorldPop pixels
                        # = 1 km x 1 km
                        # -------------------------------------------------

                        for zone_row in range(10):

                            for zone_col in range(10):

                                zone_no += 1

                                # -----------------------------------------
                                # 100m PIXELS
                                # -----------------------------------------

                                for local_row in range(10):

                                    for local_col in range(10):

                                        row = (
                                            district_row * 100
                                            + zone_row * 10
                                            + local_row
                                        )

                                        col = (
                                            district_col * 100
                                            + zone_col * 10
                                            + local_col
                                        )

                                        # Skip pixels outside raster
                                        if row >= n_rows or col >= n_cols:
                                            continue

                                       
                                        # WORLDPOP VALUE
                                      

                                        value = float(
                                            self.population[row][col]
                                        )

                                  
                                        # CENTER COORDINATES
                                       

                                        lon, lat = xy(
                                            self.transform,
                                            row,
                                            col,
                                            offset="center"
                                        )

                                        # AVERAGE ELEVATION
                           

                                        elevation_value = (
                                            average_elevation_grid[row][col]
                                        )

                                        if np.isnan(elevation_value):

                                            average_elevation = None

                                        else:

                                            average_elevation = float(
                                                elevation_value
                                            )
                                    
                                        slope_value = (average_slope_grid[row][col])
                                        if np.isnan(slope_value):
                                            slope_angle = None
                                        else:
                                            slope_angle = float(slope_value)
                                        # =================================
                                        # BUILDING INFORMATION
                                        # =================================
                                        building_areas = (building_areas_by_pixel.get((row, col),[]))
                                        building_count = len(building_areas)
                                        if building_count > 0:
                                             total_building_area = sum(building_areas)
                                             average_building_area = (total_building_area/building_count)
                                        else:
                                            total_building_area = 0.0
                                            average_building_area = 0.0
                                        
                                        # GLOBAL GRID NUMBER
                                        active_search_grid_no += 1

                                        records.append(
                                            (
                                                int(grid_no),
                                                int(zone_no),
                                                int(active_search_grid_no),

                                                round(float(lat), 6),
                                                round(float(lon), 6),

                                                round(float(value), 3),


                                                None if average_elevation is None else round(average_elevation, 3),
                                                None if slope_angle is None else round(slope_angle, 3),
                                                int(building_count),
                                                round(float(average_building_area),3),
                                                round(float(total_building_area),3)
                                            )
                                        )

                                        # ---------------------------------
                                        # BATCH INSERT
                                        # ---------------------------------

                                        if len(records) >= batch_size:

                                            db.cursor.executemany(
                                                query,
                                                records
                                            )

                                            db.conn.commit()

                                            print(
                                                f"Inserted "
                                                f"{active_search_grid_no:,} "
                                                f"grids"
                                            )

                                            records.clear()

                                    
                                        # PROGRESS
                                     

                                        if (
                                            active_search_grid_no
                                            % 50000
                                            == 0
                                        ):

                                            print(
                                                f"Processed "
                                                f"{active_search_grid_no:,} "
                                                f"grids..."
                                            )



                # INSERT REMAINING RECORDS
              

                if records:

                    db.cursor.executemany(
                        query,
                        records
                    )

                    db.conn.commit()

                    print(
                        f"Inserted final "
                        f"{len(records):,} records."
                    )

                    records.clear()


                print(
                    f"\nCompleted successfully."
                )

                print(
                    f"Total grids: "
                    f"{active_search_grid_no:,}"
                )
                multipliers = {
                    "population_density": 4,
                    "average_building_area": 3,
                    "slope_angle_deg": 2,
                    "elevation_m": 1
                }
                cursor = db.conn.cursor()

                # ---------------------------------------------------------
                # 1. Get maximum value of each field
                # ---------------------------------------------------------

                max_sql = f"""
                SELECT
                    MAX(population_density) AS max_population_density,
                    MAX(average_building_area) AS max_average_building_area,
                    MAX(slope_angle_deg) AS max_slope_angle_deg,
                    MAX(elevation_m) AS max_elevation_m
                FROM {table_name}
                """

                cursor.execute(max_sql)

                max_values = cursor.fetchone()

                max_population_density = max_values[0] or 0
                max_average_building_area = max_values[1] or 0
                max_slope_angle_deg = max_values[2] or 0
                max_elevation_m = max_values[3] or 0

                # ---------------------------------------------------------
                # 2. Calculate maximum possible weighted score
                # ---------------------------------------------------------

                max_score = (
                    max_population_density * 4
                    + max_average_building_area * 3
                    + max_slope_angle_deg * 2
                    + max_elevation_m * 1
                )

                print("Maximum possible score:", max_score)

                # ---------------------------------------------------------
                # 3. Update priority_score for every row
                # ---------------------------------------------------------

                if max_score > 0:

                    update_sql = f"""
                    UPDATE {table_name}
                    SET priority_score =
                        (
                            COALESCE(population_density, 0) * 4
                            + COALESCE(average_building_area, 0) * 3
                            + COALESCE(slope_angle_deg, 0) * 2
                            + COALESCE(elevation_m, 0) * 1
                        ) / %s
                    """

                cursor.execute(update_sql, (max_score,))
                db.conn.commit()
            
           except Exception as e:

                db.conn.rollback()

                db.log_file(str(e))

                messagebox.showerror(
                    "Database Error",
                    str(e)
                )

           finally:

                db.disconnect_db()
           
    
    def get_database_data(self):
        country_name = str(self.country_text.get())
        state_name = str(self.state_text.get())
        city_name = str(self.city_text.get())
        final_name = country_name+state_name+city_name
        db = Database()
        db.connect_db(self.userid)
        query = f"show tables from {self.userid}"
        db.cursor.execute(query)
        data = db.cursor.fetchall()
        for i in data:
            self.tables_list.append(i[0])
        if final_name not in self.tables_list:
            try:
                query = query = f"CREATE TABLE {final_name} (grid_no INT NOT NULL,zone_no INT NOT NULL,active_search_grid_no INT NOT NULL,center_lat DECIMAL(10,6),center_lon DECIMAL(10,6), population_density DECIMAL(10,3),elevation_m DECIMAL(10,3),slope_angle_deg DECIMAL(10,3),building_count INT ,  average_building_area DECIMAL(12,3), total_building_area DECIMAL(14,3),priority_score DECIMAL(5,3),PRIMARY KEY (active_search_grid_no), UNIQUE KEY grid_zone_idx (grid_no, zone_no, active_search_grid_no));"
                db.cursor.execute(query)
                db.conn.commit()
                file_path = filedialog.askopenfilename(
                title="Select a GeoJSON file",
                filetypes=[("GeoJSON files", "*.geojson")]) 
                if file_path:
                    messagebox.showinfo("success" , "geojson file has been added successfully")
                    file_tiff = filedialog.askopenfilename(title="Select the population dataset file name" , filetypes=[("TIFF Files", "*.tif *.tiff")])
                    if file_tiff:
                        messagebox.showinfo("Success" , "population files loaded successfully")
                        self.load_datasets(file_tiff,file_path,final_name)
                    else:
                        messagebox.showwarning("warning", "no location file is selected")
                    messagebox.showinfo("Success" , "database created successfully")
                else:
                    messagebox.showinfo("warning" , "no geojson file was selected")
            except Exception as databasecreationerror:
                db.log_file(databasecreationerror)
        else:
            messagebox.showerror("warning" , "database data already exists")
        db.disconnect_db()
    def toggle_map(self):
        if self.satte_mode == False:
            self.map_widget.set_tile_server("https://server.arcgisonline.com/ArcGIS/rest/services/"
                "World_Imagery/MapServer/tile/{z}/{y}/{x}",
                max_zoom=19)
            self.satte_mode = True 
        else:
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
            self.satte_mode = False

def start_main_application(userid):
        root = tk.Tk()
        app = Display(root , userid)
        root.mainloop()
if __name__ == '__main__':
    app = tk.Tk()
    login = LoginWindow(app , start_main_application)
    app.mainloop()