import cv2 as cv

# Replace the following URL with your RTSP URL
#rtsp_url = "rtsp://192.168.1.24:8555/Stream"
rtsp_url = "rtsp://admin:akshit_9977@192.168.1.3:554/Streaming/channels/101"
# Create a VideoCapture object to get the video stream from the RTSP URL
vcap = cv.VideoCapture(rtsp_url)

# Check if the connection to the stream was successful
if not vcap.isOpened():
    print(f"Error: Could not open video stream from {rtsp_url}")
    exit()

# Loop to continuously capture frames from the video stream
while True:
    # Read a frame from the video stream
    ret, frame = vcap.read()

    # Check if the frame was successfully captured
    if not ret:
        print("Error: Failed to capture frame from the video stream")
        break

    # Display the frame in a window named 'VIDEO'
    cv.imshow('VIDEO', frame)

    # Wait for 1 millisecond and check if the 'q' key was pressed to exit the loop
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

# Release the VideoCapture object and close all OpenCV windows
vcap.release()
cv.destroyAllWindows()
