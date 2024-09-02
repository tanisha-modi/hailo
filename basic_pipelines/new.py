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
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example
    
    def new_function(self):  # New function example
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------
def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK
        
    user_data.increment()
    string_to_print = f"Frame count: {user_data.get_count()}\n"
    
    format, width, height = get_caps_from_pad(pad)
    frame = None
    if user_data.use_frame and format is not None and width is not None and height is not None:
        frame = get_numpy_from_buffer(buffer, format, width, height)

    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "person":
            string_to_print += f"Detection: {label} {confidence:.2f}\n"
            detection_count += 1
    if user_data.use_frame:
        cv2.putText(frame, f"Detections: {detection_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"{user_data.new_function()} {user_data.new_variable}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

# -----------------------------------------------------------------------------------------------
# User GStreamer Application
# -----------------------------------------------------------------------------------------------
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        super().__init__(args, user_data)
        self.batch_size = 2
        self.network_width = 640
        self.network_height = 640
        self.network_format = "RGB"
        nms_score_threshold = 0.3 
        nms_iou_threshold = 0.45
        
        new_postprocess_path = os.path.join(self.current_path, '../resources/libyolo_hailortpp_post.so')
        if os.path.exists(new_postprocess_path):
            self.default_postprocess_so = new_postprocess_path
        else:
            self.default_postprocess_so = os.path.join(self.postprocess_dir, 'libyolo_hailortpp_post.so')

        if args.hef_path is not None:
            self.hef_path = args.hef_path
        elif args.network == "yolov6n":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov6n.hef')
        elif args.network == "yolov8s":
            self.hef_path = os.path.join(self.current_path, '../resources/yolov8s_h8l.hef')
        elif args.network == "yolox_s_leaky":
            self.hef_path = os.path.join(self.current_path, '../resources/yolox_s_leaky_h8l_mz.hef')
        else:
            assert False, "Invalid network type"

        if args.labels_json is not None:
            self.labels_config = f' config-path={args.labels_json} '
            if not os.path.exists(new_postprocess_path):
                print("New postprocess so file is missing. It is required to support custom labels. Check documentation for more information.")
                exit(1)
        else:
            self.labels_config = ''

        self.app_callback = app_callback
    
        self.thresholds_str = (
            f"nms-score-threshold={nms_score_threshold} "
            f"nms-iou-threshold={nms_iou_threshold} "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )

        setproctitle.setproctitle("Hailo Detection App")

        self.create_pipeline()

    def get_pipeline_string(self):
        rtsp_sources = ""
        for i, rtsp_link in enumerate(self.rtsp_links):
            rtsp_sources += (
                f"rtspsrc location={rtsp_link} name=source_{i} message-forward=true ! "
                "rtph264depay ! "
                "queue name=hailo_preprocess_q_{i} leaky=no max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
                "decodebin ! videoscale n-threads=2 ! "
                "video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height} ! "
                "videoconvert ! "
                f"tee name=t_{i} ! "
                f"queue name=queue_{i} ! "
                f"hailonet hef-path={self.hef_path} batch-size={self.batch_size} {self.thresholds_str} force-writable=true ! "
                f"queue name=queue_hailofilter_{i} ! "
                f"hailofilter so-path={self.default_postprocess_so} {self.labels_config} qos=false ! "
                f"queue name=queue_hailooverlay_{i} ! "
                "hailooverlay ! "
                f"queue name=queue_videoconvert_{i} ! "
                "videoconvert n-threads=2 ! "
                f"fpsdisplaysink video-sink={self.video_sink} name=hailo_display_{i} sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true "
                " "
            )
        
        pipeline_string = (
            f"{rtsp_sources} "
            "hailoroundrobin mode=0 name=fun ! "
            "queue name=hailo_pre_infer_q_0 leaky=downstream max-size-buffers=5 max-size-bytes=0 max-size-time=0 ! "
            f"hailonet hef-path={self.hef_path} output-format-type=HAILO_FORMAT_TYPE_FLOAT32 ! "
            "queue name=hailo_postprocess0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
            f"hailofilter so-path={self.default_postprocess_so} {self.labels_config} qos=false ! "
            "queue name=hailo_draw0 leaky=no max-size-buffers=30 max-size-bytes=0 max-size-time=0 ! "
            "hailooverlay ! hailostreamrouter name=sid "
            "compositor name=comp start-time-selection=0 ! videoscale n-threads=8 ! video/x-raw ! "
            f"fpsdisplaysink video-sink={self.video_sink} name=hailo_display sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true "
        )
        print("Generated pipeline string:")
        print(pipeline_string)
        return pipeline_string

    def set_rtsp_links(self, rtsp_links):
        self.rtsp_links = rtsp_links

if __name__ == "__main__":
    user_data = user_app_callback_class()
    parser = get_default_parser()
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
    parser.add_argument(
        "--rtsp-links",
        nargs='+',
        default=[
            "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/801/",
            "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/801/",
            "rtsp://admin:admin123@192.168.1.2:554/Streaming/Channels/801/",
            # Add more default RTSP links here
        ],
        help="List of RTSP links to stream"
    )
