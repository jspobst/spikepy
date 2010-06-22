import wx

from spikepy.gui.utils import NamedChoiceCtrl
from spikepy.gui.utils import NamedTextCtrl

class ControlPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        function_chooser = NamedChoiceCtrl(self, name="Filter function:",
                                           choices=["Butterworth", "Bessel"])
        passband_chooser = NamedChoiceCtrl(self, name="Passband Type:", 
                                           choices=["High Pass", "Low Pass", 
                                                    "Band Pass"])
        low_cutoff_textctrl = NamedTextCtrl(self, name="Low cutoff frequency:")
        high_cutoff_textctrl = NamedTextCtrl(self, 
                                             name="High cutoff frequency:")
        cutoff_textctrl = NamedTextCtrl(self, name="Cutoff frequency:")
        order_textctrl = NamedTextCtrl(self, name="Order:")
        filter_button = wx.Button(self, label="Run filter")

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        sizer.Add(function_chooser, proportion=0, 
                  flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
        sizer.Add(passband_chooser, proportion=0, 
                  flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
        sizer.Add(order_textctrl, proportion=0, 
                  flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
        sizer.Add(filter_button, proportion=0, 
                  flag=wx.ALIGN_RIGHT|wx.ALL, border=2)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self._run_filter, filter_button)
        self.Bind(wx.EVT_CHOICE, self._passband_choice_made, 
                  passband_chooser.choice)
        self.low_cutoff_textctrl = low_cutoff_textctrl
        self.high_cutoff_textctrl = high_cutoff_textctrl
        self.cutoff_textctrl = cutoff_textctrl
        self.function_chooser = function_chooser
        self.passband_chooser = passband_chooser
        self.order_textctrl = order_textctrl
        self._passband_choice_made()

    def _run_filter(self, event=None):
        function_chosen = self.function_chooser.choice.GetStringSelection()
        passband_chosen = self.passband_chooser.choice.GetStringSelection()
        if passband_chosen == "Band Pass":
            low_cutoff_freq = float(
                                  self.low_cutoff_textctrl.text_ctrl.GetValue())
            high_cutoff_freq = float(
                                 self.high_cutoff_textctrl.text_ctrl.GetValue())
            critical_freq = (low_cutoff_freq, high_cutoff_freq)
        else:
            critical_freq = float(self.cutoff_textctrl.text_ctrl.GetValue())
        order = int(self.order_textctrl.text_ctrl.GetValue())
        print function_chosen
        print passband_chosen
        print critical_freq
        print order


    def _passband_choice_made(self, event=None):
        self.low_cutoff_textctrl.Show(False)
        self.high_cutoff_textctrl.Show(False)
        self.cutoff_textctrl.Show(False)
        sizer = self.GetSizer()
        sizer.Detach(self.low_cutoff_textctrl)
        sizer.Detach(self.high_cutoff_textctrl)
        sizer.Detach(self.cutoff_textctrl)
        if (event==None or event.GetString() == "High Pass" or
            event.GetString() == "Low Pass"):
            sizer.Insert(2, self.cutoff_textctrl, proportion=0, 
                         flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
            self.cutoff_textctrl.Show(True)
        else:
            sizer.Insert(2, self.high_cutoff_textctrl, proportion=0, 
                         flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
            sizer.Insert(2, self.low_cutoff_textctrl, proportion=0, 
                         flag=wx.ALIGN_LEFT|wx.ALL|wx.EXPAND, border=2)
            self.high_cutoff_textctrl.Show(True)
            self.low_cutoff_textctrl.Show(True)
        self.Layout()