"""
Written by Jeff Pobst 2012 while referencing code by Kaushik Ghose 2009
David, if you end up using this, feel free to update this section as appropriate.
"""

import os

import numpy
import struct
import wx

from spikepy.developer.file_interpreter import FileInterpreter, Trial
from spikepy.gui.named_controls import NamedTextCtrl

class SettingsDialog(wx.Dialog):
    def __init__(self, parent, id_, title, **kwargs):
        wx.Dialog.__init__(self, parent, id_, title, **kwargs)

        channels_input = NamedTextCtrl(self, 
                name='Specify channels to open [list]:')
        start_time_input = NamedTextCtrl(self,
                name='Specify start time (seconds):')
        end_time_input = NamedTextCtrl(self,
                name='Specify end time (seconds):')
        
        self.ok_button = wx.Button(self, id=wx.ID_OK)
        cancel_button = wx.Button(self, id=wx.ID_CANCEL)
        buttons_sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        buttons_sizer.Add(cancel_button)
        buttons_sizer.Add(self.ok_button)
        
        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer.Add(channels_input)
        sizer.Add(start_time_input)
        sizer.Add(end_time_input)
        sizer.Add(buttons_sizer)

        self.channels_input = channels_input
        self.start_time_input = start_time_input
        self.end_time_input = end_time_input

        self.SetSizerAndFit(sizer)

    def get_info(self):
        channels = eval('[' + self.channels_input.GetValue() + ']')
        channels = [int(channel) for channel in channels]
        info_dict = {'channels':channels,
                'start_time_s':float(self.start_time_input.GetValue()),
                'end_time_s':float(self.end_time_input.GetValue())}
        return info_dict
        
class Ns5(FileInterpreter):
    def __init__(self):
        self.name = 'Ns5'
        self.extentions = ['.ns5']
        # higher priority means will be used in ambiguous cases
        self.priority = 10 
        self.description = '''Data acquired from Blackrock systems saved as an ns5.'''

    def read_data_file(self, fullpath):
        infile = open(fullpath)

        # allow user to choose channels and times
        settings_dialog = SettingsDialog(wx.GetApp().GetTopWindow(), -1, 
                'Specify settings')
        if settings_dialog.ShowModal() == wx.ID_OK:
            info_dict = settings_dialog.get_info()
        
        infile.seek(286)
        period = struct.unpack('<I', infile.read(4))[0]
        sampling_freq = 30000.0/period
        infile.seek(310)
        num_channels = struct.unpack('<I', infile.read(4))[0]
        start_time_s = info_dict['start_time_s']
        end_time_s = info_dict['end_time_s']
        vtrace_arrays = []
        for channel in info_dict['channels']:
            vtrace_arrays.append(self.read_channel(infile, channel, 
                    start_time_s, end_time_s, sampling_freq, num_channels))

        voltage_traces = numpy.vstack(vtrace_arrays)

        display_name = os.path.splitext(os.path.split(fullpath)[-1])[0]
        trial = Trial.from_raw_traces(sampling_freq, voltage_traces, 
                origin=fullpath, display_name=display_name)
        print 'used ns5 file interpreter'
        return [trial]

    def read_channel(self, infile, channel, start_time_s, end_time_s, 
            sampling_freq, num_channels):

        bytes_per_channel = 2 # (per time step)
        start_index = int(start_time_s * sampling_freq)
        end_index = int(end_time_s * sampling_freq)

        offset = bytes_per_channel * (channel - 1)
        start_byte = start_index * bytes_per_channel * num_channels + offset
        skip_bytes = bytes_per_channel * (num_channels - 1)

        num_bytes_in_main_header = 314
        num_bytes_in_extended_headers = 66

        infile.seek(num_bytes_in_main_header + 
                num_bytes_in_extended_headers * num_channels)
        infile.seek(start_byte, 1)
        vtrace = numpy.zeros(end_index - start_index + 1, dtype='short')
        for i in range(end_index - start_index + 1):
            vtrace[i] = struct.unpack('h', infile.read(bytes_per_channel))[0]
            infile.seek(skip_bytes,1)
        
        return vtrace
