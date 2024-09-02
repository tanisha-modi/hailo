#!/usr/bin/env python3
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import sys
import hailo

def app_callback(pad, info, user_data):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK
    
    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)
    
    # Parse the detections
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        confidence = detection.get_confidence()
        if label == "person":
            print(f"Detection: {label} {confidence:.2f}")
            detection_count += 1
    
    print(f"Total detections: {detection_count}")
    return Gst.PadProbeReturn.OK

def main(args):
    Gst.init(None)
    pipeline = Gst.parse_launch(sys.argv[1])
    element = pipeline.get_by_name("identity_callback")
    if element:
        element.get_static_pad("src").add_probe(Gst.PadProbeType.BUFFER, app_callback, None)
    else:
        print("Error: Could not find 'identity_callback' element in the pipeline.")
        return

    pipeline.set_state(Gst.State.PLAYING)
    
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    main(sys.argv)