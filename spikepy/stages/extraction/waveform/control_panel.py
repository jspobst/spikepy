import wx

from spikepy.gui.named_controls import NamedTextCtrl, OptionalNamedTextCtrl
from spikepy.gui.look_and_feel_settings import lfs


class ControlPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        wx.Panel.__init__(self, parent, **kwargs)

        pre_window_ctrl = NamedTextCtrl(self, name='Window Prepadding (ms)')
        spike_centered_checkbox = wx.CheckBox(self, 
                label='Window centered on spike.')
        post_window_ctrl = NamedTextCtrl(self, name='Window Postpadding (ms)')
        exclude_overlappers_checkbox = wx.CheckBox(self, 
                label='Exclude windows that overlap.')

        self.Bind(wx.EVT_CHECKBOX, self._spike_centered, 
                spike_centered_checkbox)

        sizer = wx.BoxSizer(orient=wx.VERTICAL)
        flag = wx.ALIGN_LEFT|wx.ALL|wx.EXPAND
        border = lfs.CONTROL_PANEL_BORDER
        sizer.Add(pre_window_ctrl,              proportion=0, flag=flag, 
                border=border)
        sizer.Add(spike_centered_checkbox,      proportion=0, flag=flag, 
                border=border)
        sizer.Add(post_window_ctrl,             proportion=0, flag=flag, 
                border=border)
        sizer.Add(exclude_overlappers_checkbox, proportion=0, flag=flag, 
                border=border)
        self.SetSizer(sizer)

        self.spike_centered_checkbox      = spike_centered_checkbox
        self.exclude_overlappers_checkbox = exclude_overlappers_checkbox
        self.pre_window_ctrl              = pre_window_ctrl
        self.post_window_ctrl             = post_window_ctrl

        # --- SET DEFAULTS ---
        pre_window_ctrl.SetValue('0.5')
        self._spike_centered(should_center_spike=True)
        post_window_ctrl.SetValue('1.0')
        exclude_overlappers_checkbox.SetValue(False)

    def _spike_centered(self, event=None, should_center_spike=None):
        if event is not None:
            should_center_spike = event.IsChecked()
        self.spike_centered_checkbox.SetValue(should_center_spike)
        self.post_window_ctrl.Enable(not should_center_spike)

    def get_parameters(self):
        pre_window = float(self.pre_window_ctrl.GetValue())
        if self.spike_centered_checkbox.IsChecked():
            post_window = pre_window
        else:
            post_window = float(self.post_window_ctrl.GetValue())
        exclude_overlappers = self.exclude_overlappers_checkbox.IsChecked()
        return {'pre_padding':pre_window, 'post_padding':post_window, 
                'exclude_overlappers':exclude_overlappers}