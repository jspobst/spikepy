import os

from wx.lib.pubsub import Publisher as pub
import wx
import numpy

from .multi_plot_panel import MultiPlotPanel
from .plot_panel import PlotPanel
from .utils import wx_to_matplotlib_color

class FilterPlotPanel(MultiPlotPanel):
    def __init__(self, parent, name):
        self._figsize   = (8.9, 2.0)
        window_color = wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW)
        self.facecolor = wx_to_matplotlib_color(*window_color.Get(True))
        self.dpi       = 72.0
        self.name      = name
        MultiPlotPanel.__init__(self, parent, figsize=self._figsize,
                                              facecolor=self.facecolor,
                                              edgecolor=self.facecolor,
                                              dpi=self.dpi)
        pub.subscribe(self._trial_added, topic='TRIAL_ADDED')
        pub.subscribe(self._trial_filtered, 
                      topic='TRIAL_%s_FILTERED' % name.upper())
        pub.subscribe(self._show_psd, topic='SHOW_PSD')
        pub.subscribe(self._zoom_plot, topic='ZOOM_PLOT')
        pub.subscribe(self._remove_trial, topic="REMOVE_PLOT")

        self._psd_shown = False
        self._trials = {}
        self._trace_axes = {}
        self._psd_axes = {}

    def _remove_trial(self, message=None):
        full_path = message.data
        del self._trials[full_path]
        del self._trace_axes[full_path]
        try: 
            self._psd_axes[full_path]
        except KeyError:
            pass

    def _show_psd(self, message=None):
        name, psd_shown = message.data
        if name == self.name:
            if psd_shown == self._psd_shown:
                return
            self._psd_shown = psd_shown
            trials = self._trials.values()
            for trial in trials:
                self._plot_panels[trial.fullpath].figure.clear()
                self._trial_added(trial=trial)
                self._show_plot(new_panel_key=trial.fullpath)
    
    def _zoom_plot(self, message=None):
        name, factor = message.data
        if name != self.name:
            return
        self.zoom(factor)

    def _trial_added(self, message=None, trial=None):
        if message is not None:
            trial = message.data

        fullpath = trial.fullpath
        self._trials[fullpath] = trial
        traces = trial.traces['raw']

        if self._psd_shown: psd = 1
        else: psd = 0
        _figsize = (self._figsize[0], self._figsize[1]*len(traces)+psd)
        self.add_plot(PlotPanel(self, figsize=_figsize,
                                      facecolor=self.facecolor,
                                      edgecolor=self.facecolor,
                                      dpi=self.dpi), fullpath)

        figure = self._plot_panels[fullpath].figure

        for i, trace in enumerate(traces):
            if i==0:
                self._trace_axes[fullpath] = [
                        figure.add_subplot(len(traces)+psd, 1, i+1+psd)]
                top_axes = self._trace_axes[fullpath][0]
            else:
                self._trace_axes[fullpath].append(
                        figure.add_subplot(len(traces)+psd, 
                                           1, i+1+psd,
                                           sharex=top_axes,
                                           sharey=top_axes))
            axes = self._trace_axes[fullpath][-1]
            axes.plot(trace, color='black', linewidth=1.3, label='Raw')
            axes.set_ylabel('Trace #%d' % (i+1))
            if i+1 < len(traces): #all but the last trace
                # make the x/yticklabels dissapear
                axes.set_xticklabels([''],visible=False)
                axes.set_yticklabels([''],visible=False)

        axes.set_xlabel('Sample Number')
        # bottom is in percent, how big is text there in percent?
        factor = len(traces)+psd
        original_bottom = 0.2
        figure.subplots_adjust(hspace=0.025, left=0.10, right=0.95, 
                               bottom=original_bottom/factor+0.01)

        #add psd plot
        if self._psd_shown:
            # concat all traces
            traces = numpy.hstack(traces)
            self._psd_axes[fullpath] = figure.add_subplot(
                    len(self._trace_axes[fullpath])+psd, 1, 1)
            psd_axes = self._psd_axes[fullpath]
            psd_axes.psd(traces, Fs=trial.sampling_freq, label='Raw',
                               linewidth=2.0, color='black')
            psd_axes.set_ylabel('PSD (dB/Hz)')
            # move psd plot's bottom edge up a bit
            box = psd_axes.get_position()
            box.p0 = (box.p0[0], box.p0[1]+0.065)
            box.p1 = (box.p1[0], 0.99)
            psd_axes.set_position(box)

        if self.name.lower() in trial.traces.keys():
            self._trial_filtered(trial=trial)
        self.SetupScrolling()
        self.Layout()
        figure.canvas.draw()
            
    def _trial_filtered(self, message=None, trial=None):
        if message is not None:
            trial = message.data
        fullpath = trial.fullpath
        traces = trial.traces[self.name.lower()]
        figure = self._plot_panels[fullpath].figure
        for trace, axes in zip(traces, self._trace_axes[fullpath]):
            axes.set_autoscale_on(False)
            lines = axes.get_lines()
            if len(lines) == 2:
                filtered_line = lines[1]
                filtered_line.set_ydata(trace)
            else:
                axes.plot(trace, color='blue', linewidth=1.0, label='Filtered')

        #add psd plot
        if self._psd_shown:
            # concat all traces
            traces = numpy.hstack(traces)
            axes = self._psd_axes[fullpath]
            lines = axes.get_lines()
            if len(lines) == 2:
                del(axes.lines[1])
            axes.psd(traces, Fs=trial.sampling_freq, 
                                       label='Filtered', 
                                       linewidth=1.5, color='blue')
            axes.set_ylabel('PSD (dB/Hz)')
            axes.legend()
        else:
            self._trace_axes[fullpath][0].legend()

        figure.canvas.draw()

