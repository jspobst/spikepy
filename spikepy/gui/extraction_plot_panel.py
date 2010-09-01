import os

from wx.lib.pubsub import Publisher as pub
import wx

from .multi_plot_panel import MultiPlotPanel
from .look_and_feel_settings import lfs
from . import program_text as pt
from .utils import adjust_axes_edges

class ExtractionPlotPanel(MultiPlotPanel):
    def __init__(self, parent, name):
        self._dpi       = lfs.PLOT_DPI
        self._figsize   = lfs.PLOT_FIGSIZE
        self._facecolor = lfs.PLOT_FACECOLOR
        self.name       = name
        MultiPlotPanel.__init__(self, parent, figsize=self._figsize,
                                              facecolor=self._facecolor,
                                              edgecolor=self._facecolor,
                                              dpi=self._dpi)
        pub.subscribe(self._remove_trial,  topic="REMOVE_PLOT")
        pub.subscribe(self._trial_added,   topic='TRIAL_ADDED')
        pub.subscribe(self._trial_altered, topic='TRIAL_FEATURE_EXTRACTED')
        pub.subscribe(self._trial_altered, topic='STAGE_REINITIALIZED')
        pub.subscribe(self._trial_renamed,  topic='TRIAL_RENAMED')

        self._trials       = {}
        self._feature_axes = {}

    def _remove_trial(self, message=None):
        trial_id = message.data
        del self._trials[trial_id]
        if trial_id in self._feature_axes.keys():
            del self._feature_axes[trial_id]

    def _trial_added(self, message=None, trial=None):
        if message is not None:
            trial = message.data

        trial_id = trial.trial_id
        self._trials[trial_id] = trial
        self.add_plot(trial_id, figsize=self._figsize, 
                                facecolor=self._facecolor,
                                edgecolor=self._facecolor,
                                dpi=self._dpi)
        figure = self._plot_panels[trial_id].figure
        self._create_axes(trial, figure, trial_id)
        self._replot_panels.add(trial_id)

    def _trial_renamed(self, message=None):
        trial = message.data
        trial_id = trial.trial_id
        new_name = trial.display_name
        axes = self._feature_axes[trial_id]
        axes.set_title(pt.TRIAL_NAME+new_name)
        self.draw_canvas(trial_id)

    def _trial_altered(self, message=None):
        trial, stage_name = message.data
        if stage_name != self.name:
            return
        trial_id = trial.trial_id
        if trial_id == self._currently_shown:
            self.plot(trial_id)
            if trial_id in self._replot_panels:
                self._replot_panels.remove(trial_id)
        else:
            self._replot_panels.add(trial_id)

    def plot(self, trial_id):
        trial = self._trials[trial_id]
        figure = self._plot_panels[trial_id].figure
        
        self._plot_features(trial, figure, trial_id)

        self.draw_canvas(trial_id)

    def _create_axes(self, trial, figure, trial_id):
        axes = self._feature_axes[trial_id] = figure.add_subplot(1,1,1)
        canvas_size = self._plot_panels[trial_id].GetMinSize()
        lfs.default_adjust_subplots(figure, canvas_size)

    def _plot_features(self, trial, figure, trial_id):
        axes = self._feature_axes[trial_id]
        axes.clear()
        trial = self._trials[trial_id]
        new_name = trial.display_name
        axes.set_title(pt.TRIAL_NAME+new_name)
        axes.set_ylabel(pt.FEATURE_AMPLITUDE)
        axes.set_xlabel(pt.FEATURE_INDEX)

        if trial.extraction.results is not None:
            features = trial.extraction.results['features']
        else:
            return
        num_excluded_features = len(
                trial.extraction.results['excluded_features'])

        axes.set_autoscale_on(True)
        for feature in features:
            axes.plot(feature, linewidth=lfs.PLOT_LINEWIDTH_4,
                               marker='.', color="k", alpha=.2)
        axes.set_xlim((0,len(features[0])-1))

        # EXTRACTED FEATURE INFO
        center = 0.70
        axes.text(center, 0.95, pt.FEATURE_SETS, 
                  verticalalignment='center',
                  horizontalalignment='center',
                  transform=axes.transAxes)
        axes.text(center-0.01, 0.91, "%s%d" % (pt.FOUND, len(features)),
                  verticalalignment='center',
                  horizontalalignment='right',
                  transform=axes.transAxes)
        axes.text(center+0.01, 0.91, "%s%d" % (pt.EXCLUDED, 
                                               num_excluded_features),
                  verticalalignment='center',
                  horizontalalignment='left',
                  transform=axes.transAxes)
