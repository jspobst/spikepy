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

from spikepy.gui.look_and_feel_settings import lfs
from spikepy.gui.named_controls import NamedSpinCtrl, NamedFloatCtrl


class ControlPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        iterations = NamedSpinCtrl(self, name="Iterations:")
        threshold = NamedFloatCtrl(self, name="Threshold:")
        number_of_clusters = NamedSpinCtrl(self, name="Number of clusters:")

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        flag = wx.ALIGN_LEFT|wx.ALL|wx.EXPAND
        border = lfs.CONTROL_PANEL_BORDER
        sizer.Add(iterations, proportion=0, flag=flag, border=border)
        sizer.Add(threshold, proportion=0, flag=flag, border=border)
        sizer.Add(number_of_clusters, proportion=0, flag=flag, border=border)
        self.SetSizer(sizer)

        self.iterations = iterations
        self.threshold = threshold
        self.number_of_clusters = number_of_clusters
        
        # --- SET DEFAULTS ---
        iterations.SetRange((10,10000))
        iterations.SetValue(30)
        threshold.SetValue(str(1.0e-8))
        number_of_clusters.SetRange((1, 15))
        number_of_clusters.SetValue(2)

    def set_parameters(self, iterations=30, threshold=str(1.0e-8), 
                       number_of_clusters=2):
        self.iterations.SetValue(iterations)
        self.threshold.SetValue(str(threshold))
        self.number_of_clusters.SetValue(number_of_clusters)

    def get_parameters(self):
        parameters = {}
        parameters["iterations"] = self.iterations.GetValue()
        parameters["threshold"] = float(self.threshold.GetValue())
        parameters["number_of_clusters"] = self.number_of_clusters.GetValue()
        return parameters
