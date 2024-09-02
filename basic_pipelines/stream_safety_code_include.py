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
import supervision as sv
from collections import Counter
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
    
    print("in call_back")
    
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    # Using the user_data to count the number of frames
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"
    
    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)
    
    
    #print(f"format {format}, width {height}, height {width}")
     
    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = None
    if user_data.use_frame:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)
    else :
        print("no frame")

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    
    
    # ---------------------------------------------------------------------------------------------------------------------
    # Specify the classes to track 
    person_class = 1
    violation_classes = [4, 5]  # Classes to check for violation
    
    
    # Initialize variables
    violation = False
    previous_person_ids = []
    frame_count_without_id_change = 0
    violation_frame_count = 0
    id_counts = Counter()  # Counter to keep track of ID occurrences
    tracked_ids = set()  # Set to store IDs for which violations have been recorded
    generated_violations = set()  # Set to store IDs for which violations have been generated
    frame_counter = 0
    
    
    
    

    
    
    # Create or open the CSV file
    '''csv_file = "violations.csv"
    with open(csv_file, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)'''
    
    
    # Check if there are any IDs 
    person_results = [detection for detection in detections if detection.get_class_id() == person_class]
    
    
    
    violation_results = [detection for detection in detections if detection.get_class_id() in violation_classes]
    
    
    
    if user_data.use_frame and format is not None and width is not None and height is not None:
        # Get video frame
        frame = get_numpy_from_buffer(buffer, format, width, height)
    
    
    
    #person_results = [detection.get_class_id() for detection in detections]
    
    
    # Get the IDs of tracked persons
    current_person_ids = [int(result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()) for result in person_results if result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id() is not None]
    
    # Get the IDs of tracked violations
    current_violation_ids = [int(result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()) for result in violation_results if (result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()) is not None]
    
    #print(detections)
    #print(person_results)
    print(current_person_ids)
    
    
    print("tracked ids are : ", user_data.tracker_ids)
    
    image_dir = "captured"
    if len(violation_results) > 0 :
        for violation_result in violation_results : 
            if violation_result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id() not in user_data.tracker_ids : 
                if not any(person_id in user_data.tracker_ids for person_id in current_person_ids):
                    img_filename = os.path.join(image_dir, f"image_{cv2.getTickCount()}.jpg")
                    
                    
                    print(f"violation id : {violation_result.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()}")
                    if frame is not None and not frame.size == 0:
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        cv2.imwrite(img_filename, frame)
                        user_data.tracker_ids.update(current_person_ids)
                        user_data.tracker_ids.update(current_violation_ids)
                    else:
                        print("Error: The image frame is empty.")

                    #cv2.imwrite(img_filename, frame)
                    print(f"Image saved to {img_filename}.")
    
    
    
    
    
    
    
    
    
    """if current_person_ids:
        # Check if IDs have changed
        if previous_person_ids != current_person_ids:
            frame_count_without_id_change = 0
            previous_person_ids = current_person_ids
        else:
            frame_count_without_id_change += 1

        # Check if IDs have not changed for 25 frames
        if frame_count_without_id_change >= 12:
            # Check if any of the current IDs are not already tracked for violation
            if not all(id in tracked_ids for id in current_person_ids):
                violation = True"""
                
                
                
     # Check for violation conditions
    """if violation and current_violation_ids:
        violation_frame_count += 1
        for id in current_violation_ids:
            id_counts[id] += 1
            if id_counts[id] >= 18:
                # Check if violation for current IDs is already generated
                if not any(person_id in generated_violations for person_id in current_person_ids):
                    #print("Saved")
                    img_filename = os.path.join(image_dir, f"image_{cv2.getTickCount()}.jpg")
                    cv2.imwrite(img_filename, frame)
                    writer.writerow([str(current_person_ids), str(current_violation_ids), img_filename])
                    print(f"Image saved to {img_filename} and recorded in CSV file.")
                    tracked_ids.update(current_person_ids)  # Add current person IDs to tracked IDs
                    generated_violations.update(current_person_ids)  # Add current person IDs to generated violations
                    violation = False
                    violation_frame_count = 0
                    id_counts = Counter()
                    break
    else:
        violation_frame_count = 0
    # Visualize the results on the frame
    annotated_frame = results[0].plot(boxes=person_results, conf=None)
    a_frame = results[0].plot(boxes=violation_results, conf=None)


    # Add text to the frame
    status_text = f"Violation Status: {'True' if violation else 'False'}"
    person_ids_text = f"Person IDs: {current_person_ids}"
    violation_ids_text = f"Violation IDs: {current_violation_ids}"""
    
    # ---------------------------------------------------------------------------------------------------------------------
    
    
    
    
    
    # Parse the detections
    detection_count = 0
    for detection in detections:
        #print(detection)
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        tracker_id = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)[0].get_id()
        #if label == "person":
        class_id_of_person = detection.get_class_id()
        #string_to_print += f"Detection: {label} {confidence:.2f}\n tracker_id : {tracker_id} \n person_class_id : {class_id_of_person}"
        string_to_print += f"Detection: {label} {confidence:.2f}\n "
        detection_count += 1
    if user_data.use_frame:
        #print("yes")
        # Note: using imshow will not work here, as the callback function is not running in the main thread
        # Let's print the detection count to the frame
        #cv2.putText(frame, "Hey QT", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 0), 2)
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Example of how to use the new_variable and new_function from the user_data
        # Let's print the new_variable and the result of the new_function to the frame
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)
    else :
        print("no user frame")
        
        
    """textoverlay  = app.pipeline.get_by_name("hailo_text")
    textoverlay.set_property('text', f'OUT: {line_zone.in_count}     |      IN: {line_zone.out_count}')
    textoverlay.set_property('font-desc', 'Sans 36')"""


    print(string_to_print)
    #print("yehhhhhhhhhhhhhhhhh")
    return Gst.PadProbeReturn.OK 
    

# -----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------














# This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        # Call the parent class constructor
        super().__init__(args, user_data)
        
        
        
        self.rtsp_sources1 = {
            #0: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1101/",
            #1: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/201/",
            0: "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/1101/",
            #1: "rtsp://192.168.1.21:8555/live",
            #1: "rtsp://192.168.1.9:8556/live"
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
        }
       
       
       
        '''  self.rtsp_sources1 = {
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
             
        }'''
        
        
        '''self.rtsp_sources1 = {
             0 : "resources/detection0.mp4",
             1 : "resources/detection0.mp4",
        }'''
        
        # Other settings
        self.postprocess_so = "resources/libyolo_hailortpp_post.so"
        self.stream_display_size = 640
        self.hef_path = "safety.hef"
        self.labels_config = "safety.json"

        # Initial values
        self.num_of_src = 1
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
                f"rtspsrc location={src_url} name=source_{n} message-forward=true ! "
               # f"filesrc location={src_url} name=source_{n}"
                f"rtph264depay ! "
               # f"decodebin ! "
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
            + QUEUE("queue_hailotracker")
            #+ "hailotracker keep-tracked-frames=3 class-id=1 keep-new-frames=3 keep-lost-frames=3 ! "
            + "hailotracker keep-tracked-frames=3 keep-new-frames=3 keep-lost-frames=3 ! "
            + QUEUE("queue_hailo_python")
            + QUEUE("queue_user_callback")
            #+ "hailopython module=python_call.py qos=false !"
            + "identity name=identity_callback ! "
            + QUEUE("hailo_draw0", max_size_buffers=30)
            + "hailooverlay ! "
            + f"hailostreamrouter name=sid {self.streamrouter_input_streams} "
            + f"compositor name=comp start-time-selection=0 {self.compositor_locations} ! "
            "videoscale n-threads=8 name=disp_scale ! "
            #+ QUEUE("queue_textoverlay")
            #+ "textoverlay name=hailo_text text='' valignment=top halignment=center ! "
            f"video/x-raw,width={self.screen_width},height={self.screen_height} ! "
            f"fpsdisplaysink video-sink='{self.video_sink_element}' name=hailo_display sync=false text-overlay=false "
            f"{self.rtsp_sources} {self.additional_parameters}"
        )
        
        print(pipeline_string)
        return pipeline_string

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    user_data.use_frame = True
    
    
    # Directory to save images
    image_dir = "captured"
    os.makedirs(image_dir, exist_ok=True)
    
    
    
    START = sv.Point(0, 340)
    END = sv.Point(640, 340)

    line_zone = sv.LineZone(start=START, end=END, triggering_anchors=(sv.Position.BOTTOM_LEFT, sv.Position.BOTTOM_RIGHT))
    
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
