import asyncio
import websockets
import random
import cv2
from threading import Thread
import base64
import json
import os  # For handling environment variables like PORT

pathr = "supermarket.mp4"

# Global variables to share alert status and image between OpenCV and WebSocket
alert_status = None
alert_image = None
stop_server_flag = False

def alert_generate(event, x, y, flags, param):
    global alert_status, alert_image
    if event == cv2.EVENT_LBUTTONDBLCLK:
        # Simulate a condition that generates alerts
        alert_status = f"ALERT: Threat Detected {random.randint(1, 100)}!"
        print(f"Alert generated: {alert_status}")

        # Capture the current frame and encode it as JPEG
        ret, jpeg_frame = cv2.imencode('.jpg', param)
        if ret:
            alert_image = base64.b64encode(jpeg_frame).decode('utf-8')
        else:
            alert_image = None
            print("Failed to encode image")

# Function to handle WebSocket connections
async def alert(websocket, path):
    global alert_status, alert_image
    print("Client connected")
    try:
        while True:
            if alert_status and alert_image:
                # Create a JSON message containing both the alert and the image
                message = json.dumps({
                    "alert": alert_status,
                    "image": alert_image
                })
                await websocket.send(message)
                print(f"Alert and image sent: {alert_status}")
                
                # Reset alert status and image after sending
                alert_status = None
                alert_image = None

            await asyncio.sleep(0.1)  # Avoid busy waiting
    except websockets.ConnectionClosed:
        print("Client disconnected")

# Function to run OpenCV video capture and trigger alerts
def run_opencv():
    global stop_server_flag
    cap = cv2.VideoCapture(pathr)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            stop_server_flag = True
            break

        frame = cv2.resize(frame, (800, 600))

        # Display the frame
        cv2.namedWindow("camera live feed")
        cv2.setMouseCallback("camera live feed", alert_generate, frame)  # Pass the current frame to the callback
        cv2.imshow("camera live feed", frame)

        if cv2.waitKey(60) & 0xFF == ord('q'):
            stop_server_flag = True
            break

    cap.release()
    cv2.destroyAllWindows()
    

# Start the WebSocket server
async def start_server():
    global stop_server_flag
    port = int(os.getenv("PORT", 9000))  # Use Render's dynamic port
    print(f"Starting WebSocket server on port {port}")
    server = await websockets.serve(alert, "0.0.0.0", port)  # Bind to 0.0.0.0 for external access
    
    try:
        while not stop_server_flag:
            await asyncio.sleep(0.1)  # Allow the server to run without blocking
    finally:
        server.close()
        await server.wait_closed()
        print("WebSocket server has been stopped")

if __name__ == "__main__":
    # Run OpenCV in a separate thread
    opencv_thread = Thread(target=run_opencv)
    opencv_thread.start()

    # Run WebSocket server in asyncio event loop
    asyncio.run(start_server())
