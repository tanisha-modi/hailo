import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import setproctitle
import cv2
import time
import hailo
from hailo_rpi_common import (
    get_default_parser,
    QUEUE,
    get_caps_from_pad,
    get_numpy_from_buffer,
    GStreamerApp,
    app_callback_class,
)

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example
    
    def new_function(self):  # New function example
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"
    
    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # Parse the detections
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "person":
            string_to_print += f"Detection: {label} {confidence:.2f}\n"
            detection_count += 1
    if user_data.use_frame:
        # Note: using imshow will not work here, as the callback function is not running in the main thread
        # Let's print the detection count to the frame
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Example of how to use the new_variable and new_function from the user_data
        # Let's print the new_variable and the result of the new_function to the frame
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    print("yehhhhhhhhhhhhhhhhh")
    return Gst.PadProbeReturn.OK
    

# -----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------














# This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        # Call the parent class constructor
        super().__init__(args, user_data)
        
        
        
       # self.rtsp_sources1 = {
          #  0: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1101/",
          #  1: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/201/",
          #  2: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/301/",
          #  3: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/401/",
          #  4: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/501/",
          #  5: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/601/",
          #  6: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/701/",
          #  7: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/801/",
          #  8: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/901/",
          #  9: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1001/",
          #  10: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1101/",
          #  11: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1201/",
          #  12: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1301/",
          #  13: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1401/",
          #  14: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1501/"
       # }
       
       
       
        self.rtsp_sources1 = {
             0 : "resources/detection0.mp4",
             1 : "resources/detection0.mp4",
             2 : "resources/detection0.mp4",
             3 : "resources/detection0.mp4",
             4 : "resources/detection0.mp4",
             5 : "resources/detection0.mp4",
             6 : "resources/detection0.mp4",
             7 : "resources/detection0.mp4",
             8 : "resources/detection0.mp4",
             9 : "resources/detection0.mp4",
             10 : "resources/detection0.mp4",
             11 : "resources/detection0.mp4",
             12 : "resources/detection0.mp4",
             13 : "resources/detection0.mp4",
             14 : "resources/detection0.mp4",
             
        }
        
        # Other settings
        self.postprocess_so = "resources/libyolo_hailortpp_post.so"
        self.stream_display_size = 320
        self.hef_path = "safety.hef"
        self.labels_config = "safety.json"

        # Initial values
        self.num_of_src = 15
        self.debug = False
        self.gst_top_command = ""
        self.additional_parameters = ""
        self.screen_width = 0
        self.screen_height = 0
        self.fpsdisplaysink_element = ""
        self.rtsp_sources = ""
        self.compositor_locations = ""
        self.print_gst_launch_only = False
        self.decode_scale_elements = (
            "decodebin ! queue leaky=downstream max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
            "videoscale n-threads=8 ! video/x-raw,pixel-aspect-ratio=1/1"
        )
        self.video_sink_element ="ximagesink"
        
        self.screen_width, self.screen_hegiht, self.compositor_locations =  self.determine_screen_size(self.num_of_src, self.stream_display_size)
        
        self.rtsp_sources, self.streamrouter_input_streams = self.create_rtsp_sources(self.num_of_src, self.decode_scale_elements)


        self.app_callback = app_callback

        # Set the process title
        setproctitle.setproctitle("Hailo Detection App")

        self.create_pipeline()
        
    def determine_screen_size(self, num_of_src, stream_display_size):
        if num_of_src <= 4:
            self.screen_width = num_of_src * stream_display_size
            self.screen_height = stream_display_size
        elif num_of_src <= 8:
            self.screen_width = 4 * stream_display_size
            self.screen_height = 2 * stream_display_size
        elif num_of_src <= 12:
            self.screen_width = 4 * stream_display_size
            self.screen_height = 3 * stream_display_size
        else:
            self.screen_width = 4 * stream_display_size
            self.screen_height = 4 * stream_display_size

        compositor_locations = []
        for i in range(num_of_src):
            xpos = (i % 4) * stream_display_size
            ypos = (i // 4) * stream_display_size
            compositor_locations.append(f"sink_{i}::xpos={xpos} sink_{i}::ypos={ypos}")

        # Join all locations into a single string separated by spaces
        self.compositor_locations = ' '.join(compositor_locations)
        
        
        return self.screen_width, self.screen_height, self.compositor_locations
        #self.video_sink_element = "xvimagesink" if self.is_xv_supported() else "ximagesink"
        
        
        
    def create_rtsp_sources(self, num_of_src, decode_scale_elements):
        rtsp_sources = ""
        streamrouter_input_streams = ""

        for n, src_url in self.rtsp_sources1.items():
            if not src_url:
                raise ValueError(f"Source URL for index {n} is not defined or empty.")
                
            # print({src_url}, {n})
            rtsp_sources += (
               # f"rtspsrc location={src_url} name=source_{n} message-forward=true ! "
                f"filesrc location={src_url} name=source_{n}"
               # f"rtph264depay ! "
                f"decodebin ! "
                f"queue name=hailo_preprocess_q_{n} leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
                f"{decode_scale_elements} ! videoconvert n-threads=8 ! "
                f"video/x-raw,pixel-aspect-ratio=1/1 ! "
                f"fun.sink_{n} sid.src_{n} ! "
                f"queue name=comp_q_{n} leaky=downstream max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
                f"comp.sink_{n} "
            )
            
            
            streamrouter_input_streams += f" src_{n}::input-streams=\"<sink_{n}>\""
            
            
        # print(rtsp_sources, "\n")

        return rtsp_sources, streamrouter_input_streams
    
    # + QUEUE("hailo_pre_infer_q_0", leaky='downstream', max_size_buffers=5)

    def get_pipeline_string(self):
        pipeline_string = (
            #f"gst-launch-1.0 "
            "hailoroundrobin mode=0 name=fun ! "
            
            + f"hailonet hef-path={self.hef_path} output-format-type=HAILO_FORMAT_TYPE_FLOAT32 ! "
            + QUEUE("hailo_postprocess0", max_size_buffers=30)
            + f"hailofilter so-path={self.postprocess_so} config-path={self.labels_config} qos=false ! "
            + QUEUE("queue_hailo_python")
            + QUEUE("queue_user_callback")
            #+ "hailopython module=python_call.py qos=false !"
            + "identity name=identity_callback ! "
            + QUEUE("hailo_draw0", max_size_buffers=30)
            + "hailooverlay ! "
            + f"hailostreamrouter name=sid {self.streamrouter_input_streams} "
            + f"compositor name=comp start-time-selection=0 {self.compositor_locations} ! "
            "videoscale n-threads=8 name=disp_scale ! "
            f"video/x-raw,width={self.screen_width},height={self.screen_height} ! "
            f"fpsdisplaysink video-sink='{self.video_sink_element}' name=hailo_display sync=false text-overlay=false "
            f"{self.rtsp_sources} {self.additional_parameters}"
        )
        
        print(pipeline_string)
        return pipeline_string

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    parser = get_default_parser()
    # Add additional arguments here
    parser.add_argument(
        "--network",
        default="yolov6n",
        choices=['yolov6n', 'yolov8s', 'yolox_s_leaky'],
        help="Which Network to use, default is yolov6n",
    )
    parser.add_argument(
        "--hef-path",
        default=None,
        help="Path to HEF file",
    )
    parser.add_argument(
        "--labels-json",
        default=None,
        help="Path to costume labels JSON file",
    )
    args = parser.parse_args()
    app = GStreamerDetectionApp(args, user_data)
    app.run()
