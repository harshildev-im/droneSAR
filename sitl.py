import time 
from pymavlink import mavutil
from database import Database
from tkinter import messagebox
import subprocess
from pymavlink import mavutil 
import tempfile
import signal
import os 
import sys 

class Drone:
    def __init__(self , drone_id , db_name , instance_id , lat , lon ):
        self.drone_id = drone_id
        self.ardupilot_dir = os.path.expanduser("~/ardupilot")
        self.sim_vehicle_dir =  os.path.join(self.ardupilot_dir, "Tools","autotest","sim_vehicle.py")
        self.ip = None 
        self.drone_mav_sys_id = None
        self.connection_type = None 
        self.db_name = db_name
        self.sitl_process = None 
        self.instance_id = instance_id
        self.latitude = lat 
        self.longitude = lon 

    def connect_drone(self):
        db = Database()
        db.connect_db(self.db_name)
        try:
            db.cursor.execute('SELECT mav_sys_id, connection_type, ip_address FROM drones WHERE drone_id = %s', (self.drone_id,))
            drone = db.cursor.fetchone()
            if drone is None:
                messagebox.showinfo("Drone add status","drone not found")
                return False
            self.drone_mav_sys_id , self.connection_type , self.ip = drone 
            param_file = tempfile.NamedTemporaryFile(mode="w",suffix=".parm",delete=False)
            param_file.write(f"MAV_SYSID,{int(self.drone_mav_sys_id)}\n")
            param_file.close()
            print("PARAM FILE:", param_file.name)
            print("MAV SYS ID:", self.drone_mav_sys_id)
            final_lat = float(self.latitude)
            final_lon = float(self.longitude)
            custom_location = f"{final_lat},{final_lon},10,0"
            command = [sys.executable,self.sim_vehicle_dir,"-v", "ArduCopter","-I", str(self.instance_id), "-w","--add-param-file",param_file.name, "--out", f"udp:{self.ip}" , f"--custom-location={custom_location}" , "--no-extra-ports"]
            self.sitl_process = subprocess.Popen(command , cwd=self.ardupilot_dir , env = os.environ.copy(), start_new_session=True)
            #,stdout=subprocess.DEVNULL , stderr=subprocess.DEVNULL 
            if self.sitl_process:
                return True 
        except Exception as e:
            Database.log_file(e)
            return False
        finally:
            db.disconnect_db()
    def print_details(self):
        print(self.drone_mav_sys_id)
        print(self.connection_type)
        print(self.ip)
    def disconnect_drone(self):
        if self.sitl_process is None:
            return False
        try:
            # Terminate the process group created for this drone
            os.killpg(self.sitl_process.pid, signal.SIGTERM)

            try:
                self.sitl_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(self.sitl_process.pid, signal.SIGKILL)
                self.sitl_process.wait(timeout=5)

            return True

        except ProcessLookupError:
            return True

        except Exception as e:
            Database.log_file(e)
            return False

        finally:
            self.sitl_process = None


            

                

                