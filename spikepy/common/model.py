import os

from wx.lib.pubsub import Publisher as pub

from .open_data_file import open_data_file
from ..filtering.simple_iir import butterworth, bessel
from ..filtering.simple_fir import fir_filter

class Model(object):
    def __init__(self):
        self.trials = {}

    def setup_subscriptions(self):
        pub.subscribe(self._open_data_file, "OPEN DATA FILE")
        pub.subscribe(self._close_data_file, "CLOSE DATA FILE")

    def _open_data_file(self, message):
        fullpath = message.data
        filename = os.path.split(fullpath)[1]
        if filename not in self.trials.keys():
            self.trials[filename] = open_data_file(fullpath)
            pub.sendMessage(topic='FILE OPENED', data=fullpath)

    def _close_data_file(self, message):
        filename = message.data
        print filename
        print self.trials.keys()
        if filename in self.trials.keys():
            del self.trials[filename]
            pub.sendMessage(topic='FILE CLOSED', data=filename)
    