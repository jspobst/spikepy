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
import os 
import multiprocessing

import wx
from wx.lib.pubsub import Publisher as pub
from wx.lib.delayedresult import startWorker

from spikepy import session

from spikepy.common.errors import *
from spikepy.common import program_text as pt
from spikepy.gui.view import View
from spikepy.gui.utils import named_color, load_pickle
from spikepy.gui.process_progress_dialog import ProcessProgressDialog
from spikepy.gui.trial_rename_dialog import TrialRenameDialog
from spikepy.gui.pyshell import locals_dict
from spikepy.gui.export_dialog import ExportDialog

def make_version_float(version_number_string):
    """
        Makes version numbers for matplotlib a float
    so they can be easily compared.
    """
    nums = version_number_string.split('.')
    result = 0.0
    for i, num in enumerate(nums):
        result += float(num)*10**(-3*i)
    return result

class Controller(object):
    def __init__(self):
        self.session = session.Session()
        self.session.open_files.add_callback(self._files_opened, 
                takes_target_results=True)
        self.session.remove_trial.add_callback(
                self._trial_closed, 
                takes_target_results=True)
        self.session.rename_trial.add_callback(self._trial_renamed,
                takes_target_results=True)
        self.session.mark_trial.add_callback(self._trial_marked,
                takes_target_results=True)

        self.view = View(self.session)
        self.results_notebook = self.view.frame.results_notebook
        self.results_panels = self.results_notebook.results_panels

        self._selected_trial = None

        # save for locals in pyshell
        locals_dict['session'] = self.session
        locals_dict['results_panels'] = self.results_panels
        locals_dict['view'] = self.view
        locals_dict['controller'] = self
        self._setup_subscriptions()

    def warn_for_matplotlib_version(self):
        import matplotlib
        version = matplotlib.__version__
        min_version = '0.99.1.1'

        if make_version_float(version) < make_version_float(min_version):
            msg = pt.MATPLOTLIB_VERSION % (min_version, version)
            dlg = wx.MessageDialog(self.view.frame, msg, 
                                   style=wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def _setup_subscriptions(self):
        pub.subscribe(self._open_open_file_dialog, 
                      topic="OPEN_OPEN_FILE_DIALOG")
        pub.subscribe(self._close_trial, topic='CLOSE_TRIAL')
        pub.subscribe(self._mark_trial, topic='MARK_TRIAL')
        pub.subscribe(self._trial_selection_changed, 
                      topic='TRIAL_SELECTION_CHANGED')
        pub.subscribe(self._results_notebook_page_changed,
                      topic='RESULTS_NOTEBOOK_PAGE_CHANGED')
        pub.subscribe(self._visualization_panel_changed, 
                      topic='VISUALIZATION_PANEL_CHANGED')
        pub.subscribe(self._save_session, topic='SAVE_SESSION')
        pub.subscribe(self._close_application,  topic="CLOSE_APPLICATION")
        pub.subscribe(self._open_rename_trial_dialog,
                      topic='OPEN_RENAME_TRIAL_DIALOG')
        pub.subscribe(self._export_trials,  topic="EXPORT_TRIALS")
        pub.subscribe(self._run, topic="RUN_STRATEGY")
        pub.subscribe(self._run, topic="RUN_STAGE")

    # UTILITY FNS
    def _plot_results(self, trial_id):
        if trial_id is not None:
            trial = self.session.get_trial(trial_id)
        else:
            trial = None
        stage_name = self.results_notebook.get_current_stage_name()
        results_panel = self.results_panels[stage_name]
        results_panel.plot(trial)

    # CALLBACK HANDLERS
    def _trial_marked(self, args):
        trial_id, status = args
        pub.sendMessage(topic='TRIAL_MARKED', data=(trial_id, status))

    def _trial_renamed(self, trial):
        pub.sendMessage(topic='TRIAL_RENAMED', data=trial)

    def _trial_closed(self, trial_id):
        self._selected_trial = None
        pub.sendMessage(topic='TRIAL_CLOSED', data=trial_id)

    def _files_opened(self, trials):
        for trial in trials:
            pub.sendMessage(topic='TRIAL_ADDED', data=trial)

    # MESSAGING RELATED FNS
    def start_debug_subscriptions(self):
        pub.subscribe(self._print_messages) # subscribes to all topics

    def stop_debug_subscriptions(self):
        pub.unsubscribe(self._print_messages) # unsubscribes from all

    # MESSAGE HANDLERS
    def _close_application(self, message):
        pub.unsubAll()
        wx.Yield()
        # deinitialize the frame manager
        self.view.frame.Destroy()
        
    def _close_trial(self, message):
        self.session.remove_trial(message.data)

    def _export_trials(self, message):
        fullpaths = []
        caption=pt.EXPORT_MARKED

        dlg = ExportDialog(self.view.frame, 
                self.session.plugin_manager.data_interpreters, 
                self.session.marked_trials, title=caption)
        if dlg.ShowModal() == wx.ID_OK:
            settings = dlg.pull()
            ep = settings['path']
            if not os.path.exists(ep):
                os.mkdirs(ep)

            dii = settings['data_interpreters_info']
            for plugin_name, kwargs in dii.items():
                self.session.export(plugin_name, base_path=ep, **kwargs)
        dlg.Destroy()

    def _mark_trial(self, message):
        try:
            self.session.mark_trial(*message.data)
        except CannotMarkTrialError as e:
            msg = e.args[0]
            dlg = wx.MessageDialog(self.view.frame, msg, 
                                   style=wx.OK|wx.ICON_EXCLAMATION)
            dlg.ShowModal()
            dlg.Destroy()

    def _open_open_file_dialog(self, message):
        frame = message.data

        paths = []
        dlg = wx.FileDialog(frame, message=pt.OPEN_FILE_DLG_MESSAGE,
                            defaultDir=os.getcwd(),
                            style=wx.OPEN|wx.MULTIPLE) 
        if dlg.ShowModal() == wx.ID_OK:
            paths = dlg.GetPaths()
        dlg.Destroy()

        self.session.open_files(paths)

    def _open_rename_trial_dialog(self, message):
        trial_id = message.data
        this_trial = self.session.get_trial(trial_id)
        this_trial_name = this_trial.display_name
        origin = this_trial.origin
        all_display_names = self.session.trial_manager.all_display_names
        dlg = TrialRenameDialog(self.view.frame, this_trial_name, origin,
                all_display_names)
        if dlg.ShowModal() == wx.ID_OK:
            new_name = dlg._text_ctrl.GetValue()
            if new_name != this_trial_name:
                self.session.rename_trial(this_trial_name, new_name)
        dlg.Destroy()

    def _print_messages(self, message):
        topic = message.topic
        data = message.data
        print topic, data

    def _results_notebook_page_changed(self, message):
        self._plot_results(self._selected_trial)

    def _run(self, message):
        message_queue = multiprocessing.Queue()
        locals_dict['mq'] = message_queue

        if 'stage_name' in message.data.keys():
            stage_name = message.data['stage_name']
        else:
            stage_name = None

        strategy = message.data['strategy']
        self.session.run(strategy=strategy, stage_name=stage_name, 
                message_queue=message_queue, async=True)

        dlg = ProcessProgressDialog(self.view.frame, message_queue)
        dlg.ShowModal()
        self._plot_results(self._selected_trial)

    def _save_session(self, message):
        save_path = message.data
        self.session.save(save_path)

    def _trial_selection_changed(self, message):
        self._selected_trial = message.data
        self._plot_results(self._selected_trial)

    def _visualization_panel_changed(self, message):
        visualization_control_panel = message.data
        if self._selected_trial is not None:
            trial = self.session.get_trial(self._selected_trial)
        else:
            trial = None
        visualization_control_panel.plot(trial)

