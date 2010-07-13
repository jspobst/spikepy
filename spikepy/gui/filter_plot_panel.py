import os

from wx.lib.pubsub import Publisher as pub
import wx
import numpy

from .multi_plot_panel import MultiPlotPanel
from .plot_panel import PlotPanel
from .utils import rgb_to_matplotlib_color
from .look_and_feel_settings import lfs
from .program_text import (TRACE_TEXT, SAMPLE_NUMBER_TEXT, RAW_TEXT, 
                           PSD_AXIS_TEXT, 
                           FILTERED_TRACE_GRAPH_LABEL)

class FilterPlotPanel(MultiPlotPanel):
    def __init__(self, parent, name):
        self._dpi       = lfs.PLOT_DPI
        self._figsize  = lfs.PLOT_FIGSIZE
        self._facecolor = lfs.PLOT_FACECOLOR
        self.name      = name
        MultiPlotPanel.__init__(self, parent, figsize=self._figsize,
                                              facecolor=self._facecolor,
                                              edgecolor=self._facecolor,
                                              dpi=self._dpi)
        pub.subscribe(self._remove_trial, topic="REMOVE_PLOT")
        pub.subscribe(self._trial_added, topic='TRIAL_ADDED')
        pub.subscribe(self._trial_filtered, 
                      topic='TRIAL_%s_FILTERED' % name.upper())

        if name.lower() == 'detection':
            self.line_color = lfs.PLOT_COLOR_2
            self.line_width = lfs.PLOT_LINEWIDTH_2
        if name.lower() == 'extraction':
            self.line_color = lfs.PLOT_COLOR_3
            self.line_width = lfs.PLOT_LINEWIDTH_3

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

    def _trial_added(self, message=None, trial=None):
        if message is not None:
            trial = message.data

        fullpath = trial.fullpath
        self._trials[fullpath] = trial
        num_traces = len(trial.traces['raw'])
        # make room for multiple traces and a psd plot.
        figsize = (self._figsize[0], self._figsize[1]*(num_traces+1))
        self.add_plot(fullpath, figsize=figsize, 
                                facecolor=self._facecolor,
                                edgecolor=self._facecolor,
                                dpi=self._dpi)
        self._replot_panels.add(fullpath)

    def _trial_filtered(self, message=None):
        trial = message.data
        fullpath = trial.fullpath
        if fullpath == self._currently_shown:
            self.plot(fullpath)
            if fullpath in self._replot_panels:
                self._replot_panels.remove(fullpath)
        else:
            self._replot_panels.add(fullpath)

    def plot(self, fullpath):
        trial = self._trials[fullpath]
        figure = self._plot_panels[fullpath].figure

        if fullpath not in self._trace_axes.keys():
            self._plot_raw_traces(trial, figure, fullpath)
        self._plot_filtered_traces(trial, figure, fullpath)

        old_shown_state = self._plot_panels[fullpath].IsShown()
        self._plot_panels[fullpath].Show(False)
        figure.canvas.draw()
        self._plot_panels[fullpath].Show(old_shown_state)
        self.SetupScrolling()
        self.Layout()

    def _plot_raw_traces(self, trial, figure, fullpath):
        traces = trial.traces['raw']
        for i, trace in enumerate(traces):
            if i==0:
                self._trace_axes[fullpath] = [
                        figure.add_subplot(len(traces)+1, 1, i+2)]
                top_axes = self._trace_axes[fullpath][0]
            else:
                self._trace_axes[fullpath].append(
                        figure.add_subplot(len(traces)+1, 
                                           1, i+2,
                                           sharex=top_axes,
                                           sharey=top_axes))
            axes = self._trace_axes[fullpath][-1]
            axes.plot(trace, color=lfs.PLOT_COLOR_1, 
                             linewidth=lfs.PLOT_LINEWIDTH_1, 
                             label=RAW_TEXT)
            axes.set_ylabel('%s #%d' % (TRACE_TEXT, (i+1)))
            if i+1 < len(traces): #all but the last trace
                # make the x/yticklabels dissapear
                axes.set_xticklabels([''],visible=False)
                axes.set_yticklabels([''],visible=False)

        axes.set_xlabel(SAMPLE_NUMBER_TEXT)
        # bottom is in percent, how big is text there in percent?
        factor = len(traces)+1
        original_bottom = 0.2
        figure.subplots_adjust(hspace=0.025, left=0.10, right=0.95, 
                               bottom=original_bottom/factor+0.01)

        # --- add psd plot ---
        all_traces = numpy.hstack(traces)
        self._psd_axes[fullpath] = figure.add_subplot(
                len(self._trace_axes[fullpath])+1, 1, 1)
        psd_axes = self._psd_axes[fullpath]
        psd_axes.psd(all_traces, Fs=trial.sampling_freq, label=RAW_TEXT,
                                 linewidth=lfs.PLOT_LINEWIDTH_1, 
                                 color=lfs.PLOT_COLOR_1)
        psd_axes.set_ylabel(PSD_AXIS_TEXT)
        # move psd plot's bottom edge up a bit
        box = psd_axes.get_position()
        box.p0 = (box.p0[0], box.p0[1]+0.065)
        box.p1 = (box.p1[0], 0.99)
        psd_axes.set_position(box)


    def _plot_filtered_traces(self, trial, figure, fullpath):
        if self.name.lower() in trial.traces.keys():
            traces = trial.traces[self.name.lower()]
        else:
            return # this trial has never been filtered.

        for trace, axes in zip(traces, self._trace_axes[fullpath]):
            axes.set_autoscale_on(False)
            lines = axes.get_lines()
            if len(lines) == 2:
                filtered_line = lines[1]
                filtered_line.set_ydata(trace)
            else:
                axes.plot(trace, color=self.line_color, 
                                 linewidth=self.line_width, 
                                 label=FILTERED_TRACE_GRAPH_LABEL)

        all_traces = numpy.hstack(traces)
        axes = self._psd_axes[fullpath]
        lines = axes.get_lines()
        if len(lines) == 2:
            del(axes.lines[1])
        axes.psd(all_traces, Fs=trial.sampling_freq, 
                                   label=FILTERED_TRACE_GRAPH_LABEL, 
                                   linewidth=self.line_width, 
                                   color=self.line_color)
        axes.set_ylabel(PSD_AXIS_TEXT)
        axes.legend(loc='lower right')


