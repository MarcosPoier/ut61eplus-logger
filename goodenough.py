import hid
import time
import sys
import csv
import datetime
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Import the protocol logic from your existing file
from read_ut161b import VID, PID, handle_request, parse_meas_result

# --- CONFIGURATION ---
LOG_FILE = "ut61e_log.csv"
UPDATE_INTERVAL_MS = 250  # 4 times a second (Adjust if beep is annoying)

class MultimeterPlotter:
    def __init__(self):
        self.device = self.setup_meter()
        self.paused = False
        self.start_time = time.time()

        # Data Storage
        self.times = []
        self.values = []
        self.units = []

        # Setup CSV Logging
        self.csv_file = open(LOG_FILE, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(["Timestamp", "Elapsed_Seconds", "Value", "Unit", "Mode"])
        print(f"Logging data to {LOG_FILE}...")

        # Setup Graph
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], color='#00ff00', linewidth=1.5)

        # Styling for "Industrial" look
        self.fig.patch.set_facecolor('#222222')
        self.ax.set_facecolor('#1a1a1a')
        self.ax.grid(True, color='#444444', linestyle='--')
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['left'].set_color('white')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.title_text = self.ax.set_title("Waiting for data...", color='white', fontsize=14)
        self.ax.set_xlabel("Time (seconds)", color='white')

        # Connect Keyboard Event (Space to Pause)
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

    def setup_meter(self):
        try:
            device = hid.device()
            device.open(VID, PID)
            print(f"Connected to {device.get_product_string()}")
            # Initialization
            handle_request(device, 0x5f)
            handle_request(device, 0x30)
            handle_request(device, 0x42)
            return device
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    def on_key(self, event):
        if event.key == ' ':
            self.paused = not self.paused
            state = "PAUSED" if self.paused else "RUNNING"
            self.title_text.set_text(f"Status: {state}")
            print(f"\n[System] Graph {state}")

    def update(self, frame):
        if self.paused:
            return self.line,

        # 1. Request Data
        try:
            resp = handle_request(self.device, 0x5e)
            result = parse_meas_result(resp)
        except Exception as e:
            print(f"Read Error: {e}")
            return self.line,

        if result and result['value']:
            try:
                # 2. Parse Data
                val = float(result['value'])
                unit = result['unit']
                mode = result['mode']
                elapsed = round(time.time() - self.start_time, 2)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 3. Store Data
                self.times.append(elapsed)
                self.values.append(val)
                self.units.append(unit)

                # 4. Save to CSV
                self.csv_writer.writerow([timestamp, elapsed, val, unit, mode])

                # 5. Update Graph
                self.line.set_data(self.times, self.values)

                # Smart Axis Resizing
                self.ax.relim()
                self.ax.autoscale_view()

                # Dynamic Title
                status = f"[{mode}] {val} {unit}"
                self.title_text.set_text(status)

                # Terminal Output (so you know it's alive)
                sys.stdout.write(f"\r{status}   ")
                sys.stdout.flush()

            except ValueError:
                # Handle "O.L" (Over Limit)
                pass

        return self.line, self.title_text

    def start(self):
        # Interval determines beep speed. 250ms is fast, 1000ms is slow.
        ani = animation.FuncAnimation(self.fig, self.update, interval=UPDATE_INTERVAL_MS, blit=False)
        plt.show()
        # Cleanup on close
        self.csv_file.close()
        self.device.close()

if __name__ == "__main__":
    app = MultimeterPlotter()
    app.start()
