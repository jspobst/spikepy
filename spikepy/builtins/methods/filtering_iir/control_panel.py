"""
Copyright (C) 2011  David Morton

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import wx

from spikepy.gui.named_controls import (NamedChoiceCtrl, NamedTextCtrl,
                                        NamedSpinCtrl)
from spikepy.gui.utils import recursive_layout
from spikepy.gui.look_and_feel_settings import lfs

class ControlPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        function_chooser = NamedChoiceCtrl(self, name="Filter function:",
                                           choices=["Butterworth", "Bessel"])
        passband_chooser = NamedChoiceCtrl(self, name="Passband Type:", 
                                           choices=["High Pass", "Low Pass", 
                                                    "Band Pass"])
        low_cutoff_spinctrl = NamedSpinCtrl(self, name="Low cutoff frequency:",
                                                  min=10, max=100000)
        high_cutoff_spinctrl = NamedSpinCtrl(self, 
                                             name="High cutoff frequency:",
                                             min=10, max=100000)
        cutoff_spinctrl = NamedSpinCtrl(self, name="Cutoff frequency:", 
                                              min=10, max=100000)
        order_spinctrl = NamedSpinCtrl(self, name="Order:", min=1, max=12)

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        flag = wx.ALIGN_LEFT|wx.ALL|wx.EXPAND
        border = lfs.CONTROL_PANEL_BORDER
        sizer.Add(function_chooser, proportion=0, 
                  flag=flag, border=border)
        sizer.Add(passband_chooser, proportion=0, 
                  flag=flag, border=border)
        sizer.Add(low_cutoff_spinctrl, proportion=0, 
                  flag=flag, border=border)
        sizer.Add(high_cutoff_spinctrl, proportion=0, 
                  flag=flag, border=border)
        sizer.Add(cutoff_spinctrl, proportion=0, 
                  flag=flag, border=border)
        sizer.Add(order_spinctrl,   proportion=0, 
                  flag=flag, border=border)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_CHOICE, self._passband_choice_made, 
                  passband_chooser.choice)
        self.low_cutoff_spinctrl = low_cutoff_spinctrl
        self.high_cutoff_spinctrl = high_cutoff_spinctrl
        self.cutoff_spinctrl = cutoff_spinctrl
        self.function_chooser = function_chooser
        self.passband_chooser = passband_chooser
        self.order_spinctrl = order_spinctrl

        # --- SET DEFAULTS ---
        self.function_chooser.SetStringSelection('Butterworth')
        self._passband_choice_made(band_type='High Pass')
        high_cutoff_spinctrl.SetValue(3000)
        low_cutoff_spinctrl.SetValue(300)
        cutoff_spinctrl.SetValue(300)
        order_spinctrl.SetValue(3)

    def set_parameters(self, function_name='Butterworth', critical_freq=300, 
                             order=3, kind='High Pass'):
        self.function_chooser.SetStringSelection(function_name)
        self._passband_choice_made(band_type=kind)
        if "Band" in kind:
            self.low_cutoff_spinctrl.SetValue( critical_freq[0])
            self.high_cutoff_spinctrl.SetValue(critical_freq[1])
        else:
            self.cutoff_spinctrl.SetValue(critical_freq)
        self.order_spinctrl.SetValue(order)

    def get_parameters(self):
        function_chosen = self.function_chooser.choice.GetStringSelection()
        passband_chosen = self.passband_chooser.choice.GetStringSelection()
        if passband_chosen == "Band Pass":
            low_cutoff_freq = float(self.low_cutoff_spinctrl.GetValue())
            high_cutoff_freq = float(self.high_cutoff_spinctrl.GetValue())
            critical_freq = (low_cutoff_freq, high_cutoff_freq)
        else:
            critical_freq = float(self.cutoff_spinctrl.GetValue())
        order = int(self.order_spinctrl.GetValue())

        kind = passband_chosen 
        settings = {'function_name':function_chosen, 
                    'critical_freq':critical_freq, 
                    'order':order, 
                    'kind':kind}
        return settings

    def _passband_choice_made(self, event=None, band_type=None):
        if event is not None:
            band_type = event.GetString()
        self.passband_chooser.SetStringSelection(band_type)
        self.low_cutoff_spinctrl.Show(False)
        self.high_cutoff_spinctrl.Show(False)
        self.cutoff_spinctrl.Show(False)
        if ("High" in band_type or
            "Low" in band_type):
            self.cutoff_spinctrl.Show(True)
        else:
            self.high_cutoff_spinctrl.Show(True)
            self.low_cutoff_spinctrl.Show(True)
        recursive_layout(self)
