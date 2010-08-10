"""
A collection of utility functions for the spikepy gui.
"""
import os
import copy
import cPickle

import wx
from wx.lib.pubsub import Publisher as pub

from . import program_text as pt

gui_folder  = os.path.split(__file__)[0]
icon_folder = os.path.join(gui_folder, 'icons')


def adjust_axes_edges(axes, canvas_size_in_pixels=None, 
                            top=0.0, 
                            bottom=0.0, 
                            left=0.0, 
                            right=0.0):
    '''
    Adjusts the axes edge positions relative to the center of the axes.
    If canvas_size_in_pixels is provided and not None then adjustments
        are in pixels, otherwise they are in percentage of the figure size.
    Returns:
        box         : the bbox for the axis after it has been adjusted.
    '''
    # adjust to percentages of canvas size.
    if canvas_size_in_pixels is not None: 
        left  /= canvas_size_in_pixels[0]
        right /= canvas_size_in_pixels[0]
        top    /= canvas_size_in_pixels[1]
        bottom /= canvas_size_in_pixels[1]
        
    'Moves given edge of axes by a fraction of the figure size.'
    box = axes.get_position()
    if top is not None:
        box.p1 = (box.p1[0], box.p1[1]+top)
    if bottom is not None:
        box.p0 = (box.p0[0], box.p0[1]-bottom)
    if left is not None:
        box.p0 = (box.p0[0]-left, box.p0[1])
    if right is not None:
        box.p1 = (box.p1[0]+right, box.p1[1])
    axes.set_position(box)
    return box
    
def recursive_layout(panel):
    if panel is not None:
        panel.Layout()
        recursive_layout(panel.GetParent())

def named_color(name):
    '''return a color given its name, in normalized rgb format.'''
    color = [chanel/255. for chanel in wx.NamedColor(name).Get()]
    return color

def rgb_to_matplotlib_color(r, g, b, a=0):
    '''return a color given its rgb values, in normalized rgb format.'''
    color = [chanel/255. for chanel in [r, g, b, a]]
    return color

def get_bitmap_icon(name):
    icon_files = os.listdir(icon_folder)
    for file in icon_files:
        if os.path.splitext(file)[0].lower() == name.lower():
            image = wx.Image(os.path.join(icon_folder, file))
            return image.ConvertToBitmap()
    raise RuntimeError(pt.MISSING_IMAGE_ERROR % name)

class HashableDict(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def __hash__(self):
        sorted_keys = sorted(self.keys())
        key_value_list = [(key, self[key]) 
                          for key in sorted_keys]
        hashable_thing = tuple(key_value_list)
        return hash(hashable_thing)


def make_dict_hashable(unhashable_dict):
    for key in unhashable_dict.keys():
        if (isinstance(unhashable_dict[key], dict) and 
            not isinstance(unhashable_dict[key], HashableDict)):
            unhashable_dict[key] = HashableDict(unhashable_dict[key])
            make_dict_hashable(unhashable_dict[key])

def strip_unicode(dictionary):
    striped_dict = {}
    for key, value in dictionary.items():
        striped_dict[str(key)] = copy.deepcopy(value)
    return striped_dict 

def load_pickle(path):
    with open(path) as ifile:
        pickled_thing = cPickle.load(ifile)
    return pickled_thing
    
class SinglePanelFrame(wx.Frame):
    # After creating an instance of this class, create a panel with the frame
    # instance as its parent.
    def __init__(self, parent, id=wx.ID_ANY, title='', size=(50, 50), 
                 style=wx.DEFAULT_FRAME_STYLE, is_modal=True):
        wx.Frame.__init__(self, parent, title=title, size=size, style=style)
        if is_modal:
            self.MakeModal(True)
        self.Bind(wx.EVT_CLOSE, self._close_frame)
    
    def _close_frame(self, message=None):
        self.MakeModal(False)
        self.Destroy()
