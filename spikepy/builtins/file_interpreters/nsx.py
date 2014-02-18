"""
Written by Jeff Pobst 2012 while referencing code by Kaushik Ghose 2009
David, if you end up using this, feel free to update this section as appropriate.
"""
#NOTE get_recording_length and read_data_file work if there is only one data 
# packet (i.e. there were no pauses during the recording).  These could be made 
# more general by heading in metadata from the data packets to know when 
# subsequent data packets start

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
        
class Nsx(FileInterpreter):
    def __init__(self):
        self.name = 'Nsx'
        self.extentions = ['.ns1','.ns2','.ns3','.ns4','.ns5','.ns6','.ns7',
                '.ns8','.ns9']
        # higher priority means will be used in ambiguous cases
        self.priority = 10 
        self.description = '''Data acquired from Blackrock systems saved as an nsx.'''

    def read_data_file(self, fullpath, channels=None, start_time_s=None,
            end_time_s=None, skip_points=0):
        with open(fullpath) as infile:
            open_dlg = (channels == None or start_time_s == None or 
                    end_time_s == None)
            if open_dlg:
                # allow user to choose channels and times
                settings_dialog = SettingsDialog(wx.GetApp().GetTopWindow(), -1,
                        'Specify settings')
                if settings_dialog.ShowModal() == wx.ID_OK:
                    info_dict = settings_dialog.get_info()
                    start_time_s = info_dict['start_time_s']
                    end_time_s = info_dict['end_time_s']
                    channels = info_dict['channels']
            
            infile.seek(286)
            period = struct.unpack('<I', infile.read(4))[0]
            sampling_freq = 30000.0/period
            recording_length_s = self.get_recording_length(infile, 
                    sampling_freq)
            end_time_s = min(end_time_s, recording_length_s)
            infile.seek(310)
            num_channels = struct.unpack('<I', infile.read(4))[0]
            vtrace_arrays = []
            for channel in channels:
                vtrace_arrays.append(self.read_channel(infile, channel, 
                        start_time_s, end_time_s, sampling_freq, num_channels, 
                        skip_points=skip_points))

        voltage_traces = numpy.vstack(vtrace_arrays)/1000.0

        display_name = os.path.splitext(os.path.split(fullpath)[-1])[0]
        new_sampling_freq = sampling_freq/float(skip_points+1)
        trial = Trial.from_raw_traces(new_sampling_freq, voltage_traces, 
                origin=fullpath, display_name=display_name)
        return [trial]

    def read_channel(self, infile, channel, start_time_s, end_time_s, 
            sampling_freq, num_channels, skip_points=0):

        data_bytes_per_channel = 2 # (per time step)
        metadata_bytes_per_data_packet = 9
        bytes_per_time_step = data_bytes_per_channel * num_channels
        start_index = int(start_time_s * sampling_freq - 0.5)
        end_index = int(end_time_s * sampling_freq - 0.5)

        offset_from_data_packet = (data_bytes_per_channel * (channel - 1) + 
                metadata_bytes_per_data_packet)
        start_byte = start_index * bytes_per_time_step + offset_from_data_packet
        skip_bytes = (bytes_per_time_step * (skip_points + 1) - 
                data_bytes_per_channel)

        num_bytes_in_main_header = 314
        num_bytes_in_extended_headers = 66
        data_start_pos_in_bytes = (num_bytes_in_main_header +
                num_bytes_in_extended_headers * num_channels)

        infile.seek(data_start_pos_in_bytes)
        infile.seek(start_byte, 1)
        trace_length = int(end_index - start_index + 1)/int(skip_points+1)
        vtrace = numpy.zeros(trace_length, dtype='short')
        for i in range(trace_length):
            vtrace[i] = struct.unpack('h', 
                    infile.read(data_bytes_per_channel))[0]
            infile.seek(skip_bytes,1)
        
        return vtrace

    
    def get_recording_length(self, infile, sampling_freq):
        bytes_before_data_bytes = 6721 #NOTE this is true when there are 97
                                       # channels
        infile.seek(bytes_before_data_bytes)
        num_timesteps = struct.unpack('I', infile.read(4))[0]
        rec_length_s = num_timesteps/sampling_freq

        return rec_length_s
