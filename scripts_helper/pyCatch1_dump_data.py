import sys
import threading
import time
import random
import paho.mqtt.client as mqtt

# Dummy data configuration
NUM_CAMERAS = 5
DUMMY_DATA_INTERVAL = 2  # Send dummy data every 2 seconds


class DummyDataThread(threading.Thread):
    def __init__(self, camera_index, mqtt_client):
        super().__init__()
        self.camera_index = camera_index
        self.mqtt_client = mqtt_client
        self.running = False
        self.paused = False
        self.condition = threading.Condition()
        self.detecting = False  # Flag to control dummy data sending

    def run(self):
        self.running = True
        print(f"🎯 Dummy data thread {self.camera_index} started")

        while self.running:
            with self.condition:
                if self.paused:
                    self.condition.wait()
                    continue
            
            # Only send dummy data if detecting is enabled
            if self.detecting:
                self.send_dummy_data()

            time.sleep(DUMMY_DATA_INTERVAL)

    def send_dummy_data(self):
        """Send random dummy numbers to MQTT topic"""
        # Generate random dummy data (0-100 range)
        dummy_value = random.randint(0, 100)
        
        try:
            # Publish dummy data to MQTT topic
            topic = f"FalconGrasp/camera/{self.camera_index}"
            self.mqtt_client.publish(topic, dummy_value)
            print(f"📡 Camera {self.camera_index} - Sent dummy data: {dummy_value}")
        except Exception as e:
            print(f"❌ Error publishing dummy data for camera {self.camera_index}: {e}")

    def stop(self):
        self.running = False
        with self.condition:
            self.condition.notify()

    def pause(self):
        with self.condition:
            self.paused = True

    def resume(self):
        with self.condition:
            self.paused = False
            self.condition.notify()

    def start_detection(self):
        self.detecting = True
        print(f"🎯 Camera {self.camera_index} dummy data sending started")

    def stop_detection(self):
        self.detecting = False
        print(f"🎯 Camera {self.camera_index} dummy data sending stopped")


class DummyDataManager:
    def __init__(self, mqtt_client):
        self.dummy_threads = []
        for i in range(NUM_CAMERAS):
            thread = DummyDataThread(i, mqtt_client)
            self.dummy_threads.append(thread)

    def start_all(self):
        for thread in self.dummy_threads:
            if not thread.is_alive():
                thread.running = True
                thread.paused = False
                thread.start()
            else:
                thread.resume()

    def stop_all(self):
        for thread in self.dummy_threads:
            thread.stop()
        for thread in self.dummy_threads:
            thread.join()

    def pause_all(self):
        for thread in self.dummy_threads:
            if thread.is_alive():
                thread.pause()
            else:
                print(f"Thread {thread.camera_index} is not alive and cannot be paused.")

    def resume_all(self):
        for thread in self.dummy_threads:
            thread.resume()


def on_mqtt_message(client, userdata, message):
    if message.topic == "FalconGrasp/game/start":
        print(f"🎮 Received MQTT message to start: {message.payload.decode()}")
        for thread in manager.dummy_threads:
            thread.start_detection()  # Start dummy data sending for all threads
        print("🎯 All dummy data threads started sending data")
    elif message.topic == "FalconGrasp/game/stop":
        print(f"🛑 Received MQTT message to stop: {message.payload.decode()}")
        for thread in manager.dummy_threads:
            thread.stop_detection()  # Stop dummy data sending for all threads
        print("🎯 All dummy data threads stopped sending data")


def on_mqtt_disconnect(client, userdata, rc):
    print("Disconnected from MQTT broker. Attempting to reconnect...")
    while True:
        try:
            client.reconnect()
            print("Reconnected to MQTT broker.")
            break
        except Exception as e:
            print(f"Reconnect failed: {e}")
            time.sleep(5)  # Wait before retrying


if __name__ == "__main__":
    print("🎯 Starting MQTT Dummy Data Dumper for FalconGrasp")
    print("📡 This script will send dummy numbers to MQTT topics without opening cameras")
    print("🎮 Send 'start' to 'FalconGrasp/game/start' to begin dummy data transmission")
    print("🛑 Send 'stop' to 'FalconGrasp/game/stop' to stop dummy data transmission")
    print("=" * 60)

    # Set up MQTT client
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.subscribe("FalconGrasp/game/start")
    mqtt_client.subscribe("FalconGrasp/game/stop")
    mqtt_client.loop_start()

    # Initialize the DummyDataManager
    manager = DummyDataManager(mqtt_client)
    manager.start_all()

    print(f"🎯 Started {NUM_CAMERAS} dummy data threads")
    print(f"📊 Dummy data will be sent every {DUMMY_DATA_INTERVAL} seconds when activated")
    print("⏳ Waiting for MQTT start/stop commands...")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Stopping dummy data dumper...")
    finally:
        manager.stop_all()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("✅ Dummy data dumper stopped successfully")