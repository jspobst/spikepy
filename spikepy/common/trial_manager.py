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
from collections import defaultdict
import copy
import datetime
import os
import uuid

import wx
import numpy
import scipy.io

try:
    from callbacks import supports_callbacks
except ImportError:
    from spikepy.other.callbacks.callbacks import supports_callbacks

from spikepy.common import program_text as pt
from spikepy.common import utils
from spikepy.common.utils import SubstringDict 
from spikepy.common.errors import *
from spikepy.utils.frequency_analysis import psd

class TrialManager(object):
    """
        The TrialManager keeps track of all the trials currently in the
    session.  It handles marking/unmarking, adding/removing trials, and 
    assigning unique display names to trials.
    """
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._trial_index = {}
        self._display_names = set()

    @supports_callbacks 
    def mark_trial(self, name, status):
        """Mark trial with display_name=<name> according to <status>."""
        trial = self.get_trial_with_name(name)

        if self.marked_trials:
            num_channels = self.marked_trials[0].num_channels
            if trial.num_channels != num_channels and status:
                raise CannotMarkTrialError('Cannot mark a trial with %d channels, since trials with %d channels are already marked.' % (trial.num_channels, num_channels))
        trial.mark(status=status)
        return trial.trial_id, trial.is_marked

    def mark_all_trials(self, status):
        """Mark all trials according to <status>"""
        for trial in self._trial_index.values():
            try:
                self.mark_trial(trial.name, status)
            except CannotMarkTrialError:
                pass

    def add_trials(self, trial_list, marked=True):
        """
            Add all the trials in <trial_list> and ensure they have unique
        names.
        """
        new_names = []
        for trial in trial_list:
            if trial.trial_id in self._trial_index.keys():
                self.remove_trial(trial)
            new_name = self._get_unique_display_name(trial.display_name)
            trial.display_name = new_name
            new_names.append(new_name)
            self._trial_index[trial.trial_id] = trial

        for name in new_names:
            try:
                self.mark_trial(name, marked)
            except CannotMarkTrialError:
                pass

    def remove_trial_with_name(self, name):
        """Remove the trial with display_name=<name>."""
        trial = self.get_trial_with_name(name)
        self.remove_trial(trial)

    @supports_callbacks 
    def remove_trial(self, trial):
        self._display_names.remove(trial.display_name)
        del self._trial_index[trial.trial_id]
        return trial.trial_id

    def remove_marked_trials(self):
        """Remove all currently marked trials."""
        marked_trials = self.marked_trials
        for trial in marked_trials:
            self.remove_trial(trial)

    def _get_unique_display_name(self, proposed_display_name):
        count = 1
        new_display_name = proposed_display_name
        while new_display_name in self._display_names:
            new_display_name = '%s(%d)' % (proposed_display_name, count)
            count += 1
        self._display_names.add(new_display_name)
        return new_display_name

    @property
    def all_display_names(self):
        return self._display_names 

    @supports_callbacks
    def rename_trial(self, old_name, proposed_name):
        """Find trial named <old_name> and rename it to <proposed_name>."""
        trial = self.get_trial_with_name(old_name)
        self._display_names.remove(trial.display_name)
        trial.display_name = self._get_unique_display_name(proposed_name)
        return trial

    @property
    def marked_trials(self):
        '''Return all currently marked trials.'''
        return [trial for trial in self._trial_index.values()
                if trial.is_marked]

    @property
    def marked_trial_ids(self):
        """Return the trial_ids for all currently marked trials"""
        marked_ids = [trial.trial_id for trial in self.get_marked_trials()]
        return marked_ids

    @property
    def trials(self):
        '''Return all currently marked and unmarked trials.'''
        return self._trial_index.values()

    def get_trial_with_id(self, trial_id):
        """
        Find the trial with trial_id=<trial_id> and return it.
        Raises MissingTrialError if trial cannot be found.
        """
        try:
            return self._trial_index[trial_id]
        except KeyError:
            raise MissingTrialError('No trial with id "%s" found.' % 
                    str(trial_id))

    @property
    def _trial_name_index(self):
        tni = SubstringDict()
        for trial in self._trial_index.values():
            tni[trial.display_name] = trial
        return tni

    def get_trial_with_name(self, name):
        """
        Find the trial with display_name=<name> and return it.
        Raises MissingTrialError if trial cannot be found.
        """
        try:
            return self._trial_name_index[name]
        except KeyError:
            raise MissingTrialError('No trial named "%s" found.' % name)

    def __str__(self):
        return_str =     ['Trial Manager with trials:']
        return_str.append('    Marked  Display Name')
        return_str.append('    ------  ------------')
        marked = {False:' ', True:'X'}
        for trial in self._trial_index.values():
            return_str.append('       [%s]  %s' % 
                    (marked[trial.is_marked], trial.display_name))
        return '\n'.join(return_str) 
    

class Trial(object):
    """
        The Trial class carries attributes and resources pertaining to one
    recording.  The resources can be locked(checked out) and unlocked
    (checked in) allowing only one process access at a time.
    """
    def __init__(self, origin=None, display_name="DEFAULT_DISPLAY_NAME"):
        self._marked = False
        self.display_name = display_name
        self._id = uuid.uuid4() 
        self.origin = origin

    @property
    def num_channels(self):
        if hasattr(self, 'raw_traces'):
            return self.raw_traces.shape[0]
        else:
            return 0

    def get_times(self, signal, sampling_freq):
        return numpy.arange(0, signal.shape[1], 
                dtype=signal.dtype)/sampling_freq*1000.0

    def _setup_basic_attributes(self, raw_traces, sampling_freq):
        self.raw_traces = utils.format_traces(raw_traces)
        self.raw_times = self.get_times(self.raw_traces, sampling_freq)
        self.sampling_freq = sampling_freq

        # -------------------------------------
        # -- main processing stage resources --
        # pf_traces is a 2D numpy array where (pre-filtering)
        #    len(pf_traces) == num_channels
        self.add_resource(Resource('pf_traces', data=self.raw_traces))
        self.add_resource(Resource('pf_sampling_freq', data=self.sampling_freq))
        
        pf_psd, pf_freqs = psd(self.raw_traces.flatten(), sampling_freq, 10)
        self.add_resource(Resource('pf_psd', data=pf_psd))
        self.add_resource(Resource('pf_freqs', data=pf_freqs))

        # df_traces is a 2D numpy array where (detection-filtering)
        #    len(df_traces) == num_channels
        self.add_resource(Resource('df_traces'))
        self.add_resource(Resource('df_sampling_freq'))

        self.add_resource(Resource('df_psd'))
        self.add_resource(Resource('df_freqs'))

        # events is a list of "list of times" where 
        #    len(event_times) == num_channels
        #    len(event_times[i]) == number of events on the ith channel
        #    events[i][j] == time of jth event on the ith channel
        self.add_resource(Resource('event_times'))

        # ef_traces is a 2D numpy array where (extraction-filtering)
        #    len(ef_traces) == num_channels
        self.add_resource(Resource('ef_traces'))
        self.add_resource(Resource('ef_sampling_freq'))

        self.add_resource(Resource('ef_psd'))
        self.add_resource(Resource('ef_freqs'))

        # features is 2D numpy array with shape = (n, m) where
        #    n == the total number of events with features
        #    m == the number of features describing each event
        #    features[k][l] == feature l of event k
        self.add_resource(Resource('features'))
        self.add_resource(Resource('feature_times'))

        # clusters is a 1D numpy array of integers (cluster ids).
        #   clusters[k] == id of cluster to which the kth feature belongs.
        self.add_resource(Resource('clusters'))

    @classmethod
    def from_raw_traces(cls, sampling_freq=None, raw_traces=None, 
            origin=None, display_name=None):
        '''Create a trial object using the raw voltage traces.'''
        result = cls(origin=origin, display_name=display_name)
        result._setup_basic_attributes(raw_traces, sampling_freq)
        return result

    @classmethod
    def from_spike_windows(cls, sampling_freq=None, spike_windows=None,
            spike_times=None):
        '''
            Create a trial object using just spike_windows and the times when
        they were gathered.  The only stages which still make sense after
        that are feature_extraction and clustering.
        '''
        raise NotImplementedError

    @classmethod
    def from_dict(cls, info_dict):
        '''Create a trial from a dictionary, likely from an archive.'''
        new_trial = cls()
        for key, value in info_dict.items():
            if not isinstance(value, dict):
                setattr(new_trial, key, value)
            else: # is a resource
                setattr(new_trial, key, Resource.from_dict(value))
        return new_trial

    @property
    def as_dict(self):
        '''
            Create the dictionary that has all data from this trial, 
        for archiving.
        '''
        info_dict = {}
        info_dict['_id'] = self.trial_id
        info_dict['origin'] = self.origin
        info_dict['display_name'] = self.display_name
        for resource in self.resources:
            info_dict[resource.name] = resource.as_dict
        return info_dict

    def cluster_data(self, data):
        adict = defaultdict(list)
        if self.clusters.data is not None:
            clusters = self.clusters.data
            for cluster_id, thing in zip(clusters, data):
                adict[cluster_id].append(thing)
        else:
            raise NoClustersError('Cannot fetch clustered data, clustering not yet run.')

        # give name to cluster based on size, excluding clusters with id==-1
        sorting_list = []
        for cluster_id, cluster in adict.items():
            size = len(cluster)
            if cluster_id != -1:
                sorting_list.append( (size, -cluster_id) )

        sorting_list.sort(reverse=True)
        
        results = {}
        new_id = 'A'
        for size, cluster_id in sorting_list:
            results[new_id] = adict[-cluster_id]
            new_id = chr(ord(new_id) + 1)

        try: # put rejected features in special cluster.
            results['RC'] = adict[-1]
        except KeyError:
            pass

        return results
        
    @property
    def clustered_features(self):
        return self.cluster_data(self.features.data)

    @property
    def clustered_feature_times(self):
        return self.cluster_data(self.feature_times.data)

    @property
    def clustered_features_as_list(self):
        return self._clustered_thing_as_list(self.clustered_features)

    @property
    def clustered_feature_times_as_list(self):
        return self._clustered_thing_as_list(self.clustered_feature_times)

    def _clustered_thing_as_list(self, thing):
        return_list = []
        for cluster_id in sorted(thing.keys()):
            return_list.append(thing[cluster_id])
        return return_list

    @property
    def resources(self):
        '''Return all resources this trial contains in a list.'''
        result = []
        for key, value in self.__dict__.items():
            if isinstance(value, Resource):
                result.append(value)
        return result
        
    def add_resource(self, resource):
        '''Add <resource> to this trial.'''
        if hasattr(self, resource.name):
            raise AddResourceError(pt.RESOURCE_EXISTS % resource.name)
        else:
            setattr(self, resource.name, resource)

    @property
    def trial_id(self):
        return self._id

    @property
    def is_marked(self):
        return self._marked

    def mark(self, status=True):
        """Mark this trial according to <status>"""
        self._marked = status

    def export(self, path=None, stages_selected=[], file_format=None):
        # TODO refactor into another file using the new resources idea.
        '''
        Store the results of the stages in <stage_list> to files in <path>.
        Inputs:
            path            : The export directory (must exist)
            stage_list      : A list of strings denoting the stages results to
                              export.
            rows_or_cols    : Should sequences be stored as rows or columns.
            format          : The file format
        Returns:
            None
        '''
        for stage_name in stages_selected:
            extention = format_extentions[file_format]
            base_name = '%s-%s' % (self.display_name, stage_name)
            filename = '%s.%s' % (base_name, extention)
            fullpath = os.path.join(path, filename)
            times = self.times
            if 'raw_traces' == stage_name:
                if (file_format == pt.PLAIN_TEXT_TABS or
                    file_format == pt.PLAIN_TEXT_SPACES or
                    file_format == pt.CSV ):
                    results = [times]
                    for trace in self.raw_traces:
                        results.append(trace)
                    delimiter = text_delimiters[file_format]
                    utils.save_list_txt(fullpath, results, 
                                  delimiter=delimiter)
                elif file_format == pt.NUMPY_BINARY:
                    numpy.savez(fullpath, times=times, 
                                raw_traces=self.raw_traces)
                elif file_format == pt.MATLAB:
                    results = {'times': times,
                               'raw_traces': self.raw_traces}
                    scipy.io.savemat(fullpath, results)
                continue
            stage_data = self.get_stage_data(stage_name)
            if stage_data.results is None:
                continue # this stage hasn't been run.
            # EXPORT FILTER STAGE
            if 'filter' in stage_name:
                if (file_format == pt.PLAIN_TEXT_TABS or
                    file_format == pt.PLAIN_TEXT_SPACES or
                    file_format == pt.CSV ):
                    results = [times]
                    for trace in stage_data.results['traces']:
                        results.append(trace)
                    delimiter = text_delimiters[file_format]
                    utils.save_list_txt(fullpath, results, 
                                        delimiter=delimiter)
                elif file_format == pt.NUMPY_BINARY:
                    numpy.savez(fullpath, **stage_data.results)
                elif file_format == pt.MATLAB:
                    scipy.io.savemat(fullpath, stage_data.results)
            # EXPORT DETECTION STAGE
            if stage_name == 'detection':
                spike_times        = stage_data.results['spike_times']
                if (file_format == pt.PLAIN_TEXT_TABS or
                    file_format == pt.PLAIN_TEXT_SPACES or
                    file_format == pt.CSV ):
                    delimiter = text_delimiters[file_format]
                    results = [spike_times]
                    utils.save_list_txt(fullpath, results, 
                                  delimiter=delimiter)
                elif file_format == pt.NUMPY_BINARY:
                    numpy.savez(fullpath, **stage_data.results)
                elif file_format == pt.MATLAB:
                    scipy.io.savemat(fullpath, stage_data.results)
            # EXPORT EXTRACTION STAGE
            if stage_name == 'extraction':
                features = numpy.array(stage_data.results['features'])
                feature_times = numpy.array(stage_data.results['feature_times'])
                feature_times = feature_times.reshape(1,-1)
                if (file_format == pt.PLAIN_TEXT_TABS or
                    file_format == pt.PLAIN_TEXT_SPACES or
                    file_format == pt.CSV ):
                    for f, ft in zip(features, feature_times):
                        results.append([ft, f])
                    delimiter = text_delimiters[file_format]
                    utils.save_list_txt(fullpath, results, 
                                  delimiter=delimiter)
                elif file_format == pt.NUMPY_BINARY:
                    numpy.savez(fullpath, **stage_data.results)
                elif file_format == pt.MATLAB:
                    scipy.io.savemat(fullpath, stage_data.results)
            # EXPORT CLUSTERING STAGE
            if stage_name == 'clustering':
                sr = stage_data.results
                # store results the way you should for .mat files.
                results_dict = {}
                st_dict = sr['clustered_spike_times']
                for cluster_id, spike_times in st_dict.items():
                    key = 'cluster_%s_spike_times' % cluster_id
                    results_dict[key] = spike_times
                f_dict = sr['clustered_features']
                for cluster_id, features in f_dict.items():
                    key = 'cluster_%s_features' % cluster_id
                    results_dict[key] = features
                sw_dict = self.get_clustered_spike_windows()
                for cluster_id, sw in sw_dict.items():
                    key = 'cluster_%s_spike_windows'% cluster_id
                    results_dict[key] = sw
                # format results for .txt files.
                clustered_spike_times = sr['clustered_spike_times']
                cluster_keys = sorted(clustered_spike_times.keys())
                results = [clustered_spike_times[key] for key in cluster_keys]
                string_dict = {}
                if (file_format == pt.PLAIN_TEXT_TABS or
                    file_format == pt.PLAIN_TEXT_SPACES or
                    file_format == pt.CSV ):
                    delimiter = text_delimiters[file_format]
                    utils.save_list_txt(fullpath, results, 
                                        delimiter=delimiter)
                elif file_format == pt.NUMPY_BINARY:
                    numpy.savez(fullpath, **sr)
                elif file_format == pt.MATLAB:
                    scipy.io.savemat(fullpath, results_dict)


class Resource(object):
    """
        The Resource class handles locking(checkout) and unlocking(checkin)
    allowing only one process to access the resource at a time.  Additionally,
    resources store metadata about how and when they were last changed and 
    by whom.
    """
    def __init__(self, name, data=None):
        self.name = name
        self._id = uuid.uuid4()
        self._locked = False
        self._locking_key = None
        self._change_info = {'by':None, 'at':datetime.datetime.now(), 
                'with':None, 'using':None, 'change_id':None}

        self._data = data

    def __hash__(self):
        return hash(self._id)

    @classmethod
    def from_dict(cls, info_dict):
        name = info_dict['name']
        data = info_dict['data']
        change_info = info_dict['change_info']
        new_resource = cls(name, data=data)
        new_resource._change_info = change_info
        return new_resource

    @property
    def as_dict(self):
        info_dict = {'name':self.name}
        info_dict['data'] = self.data
        info_dict['change_info'] = self.change_info
        return info_dict

    def checkout(self):
        '''
            Check out this resource, locking it so that noone else can check it
        out until you've checked it in via <checkin>.
        '''
        if self.is_locked:
            raise ResourceLockedError(pt.RESOURCE_LOCKED % self.name)
        else:
            self._locking_key = uuid.uuid4()
            self._locked = True
            return {'name':self.name, 
                    'data':self._data, 
                    'locking_key':self._locking_key}

    def checkin(self, data_dict=None, key=None):
        '''
            Check in resource so others may use it.  If <data_dict> is
        supplied it should be a dictionary with:
            'data': the data 
            'change_info': see docstring on self.change_info
                           NOTE: This function adds 'at' and 'change_id' to
                                 'change_info' automatically, so those can
                                 be left out of the 'change_info' dictionary.
        '''
        if not self.is_locked:
            raise ResourceNotLockedError(pt.RESOURCE_NOT_LOCKED % self.name)
        else:
            if key == self._locking_key:
                if data_dict is not None:
                    self._commit_change_info(data_dict['change_info'])
                    self._data = data_dict['data']
                self._locking_key = None
                self._locked = False
            else:
                raise InvalidLockingKeyError(pt.RESOURCE_KEY_INVALID % 
                        (str(key), self.name))

    def _commit_change_info(self, change_info):
        assert "by" in change_info.keys()
        assert isinstance(change_info['with'], dict)
        assert isinstance(change_info['using'], list)
        # so doesn't point back to strategy's settings dict.
        change_info['with'] = copy.copy(change_info['with']) 

        change_info['at'] = datetime.datetime.now()
        change_info['change_id'] = uuid.uuid4()
        self._change_info = change_info

    @property
    def is_locked(self):
        return self._locked

    @property
    def data(self):
        return self._data

    @property
    def change_info(self):
        '''
            Information describing how this resource was last changed.
        Keys:
            by : string, name of the plugin function that changed this resource.
            at : datetime, the date/time of the last change to this resource.
            with : dict, a dictionary of keyword args for the <by> function.
            using : list, a list of (trial_id, resource_name, change_id) that 
                    were used as arguments to the <by> function.  If any 
                    arguments to <by> were not resources, then entry will be 
                    (trial_id, attribute_name).
            change_id : a uuid generated when this resource was last changed.
        '''
        return self._change_info

    

