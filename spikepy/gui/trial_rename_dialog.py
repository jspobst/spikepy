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

import string

import wx
from .validators import FilenameValidator
from spikepy.common import program_text as pt
from .named_controls import NamedTextCtrl 

valid_filename_characters = ('-_.,)(%s%s' % 
                             (string.ascii_letters, string.digits))

class TrialRenameDialog(wx.TextEntryDialog):
    def __init__(self, parent, trial_name, fullpath, 
                       all_other_trials, *args, **kwargs):
        self.all_other_trials = all_other_trials
        message =  'Fullpath: %s' % fullpath
        self._valid_characters = valid_filename_characters
        wx.TextEntryDialog.__init__(self, parent, message, 
                caption='Enter New Trial Name',
                defaultValue=trial_name, **kwargs)

        self.warning_text = wx.StaticText(self)
        sizer = self.GetSizer()
        sizer.Insert(2, self.warning_text, proportion=0, 
                        flag=wx.ALIGN_LEFT|wx.ALL, border=8)
        self.Layout()
        self.Fit()

        # if you add validator too early, it won't accept the defaultValue
        wx.CallLater(300, self._add_validator)

    def _add_validator(self):
        # add a validator to the textctrl
        for child in self.GetChildren():
            if isinstance(child, wx.TextCtrl):
                # for some reason after dlg closes dlg.GetValue() will always
                # be the original value, but dlg._text_ctrl.GetValue() will
                # get the correct value.
                self._text_ctrl = child
                child.SetValidator(FilenameValidator(valid_filename_characters))
                child.Bind(wx.EVT_TEXT, self._text_ctrl_validate)

    def _text_ctrl_validate(self, event=None):
        validator = self._text_ctrl.GetValidator()
        validator.Validate(dlg=self, can_exit=False)
