# import hailo

# Importing VideoFrame before importing GST is must
#from gsthailo import VideoFrame
#from gi.repository import Gst

# Create 'run' function, that accepts one parameter - VideoFrame, more about VideoFrame later.
# `run` is default function name if no name is provided
#def run(video_frame: VideoFrame):
#    print("My first Python postprocess!")

# return Gst.FlowReturn.OK
#import gi
#gi.require_version('Gst', '1.0')
#from gi.repository import Gst
#import hailo
#from gsthailo import VideoFrame

#def run(video_frame: VideoFrame):
#    print("My first Python postprocess!")
#    print(f"Video frame: {video_frame}")

#    return Gst.FlowReturn.OK

# Initialize GStreamer manually (if needed)
#Gst.init(None)


# test_python.py
#import gi
#gi.require_version('Gst', '1.0')
#from gi.repository import Gst

#Gst.init(None)

#pipeline = Gst.parse_launch("videotestsrc ! videoconvert ! autovideosink")
#pipeline.set_state(Gst.State.PLAYING)

#bus = pipeline.get_bus()
#msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.ERROR | Gst.MessageType.EOS)

#if msg:
#    if msg.type == Gst.MessageType.ERROR:
#        err, debug = msg.parse_error()
#        print(f"Error: {err}, {debug}")
#    elif msg.type == Gst.MessageType.EOS:
#        print("End of Stream")


try:
    import hailo
except ImportError:
    exit("Failed to import hailo python module. \
Make sure you are in hailo virtual environment.")
print("hello")
# Importing VideoFrame before importing GST is must
from gsthailo import VideoFrame
from gi.repository import Gst

# Create 'run' function, that accepts one parameter - VideoFrame, more about VideoFrame later.
# `run` is default function name if no name is provided
def run(video_frame: VideoFrame):
    print("hello")
    #for tensor in video_frame.roi.get_tensors():
    #    print(tensor.name())
    #my_tensor = roi.get_tensor("output_layer_name")
    #print(f"shape is {my_tensor.height()}X{my_tensor.width()}X{my_tensor.features()})
