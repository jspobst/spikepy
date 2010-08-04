import traceback 
import sys
from multiprocessing import Pool
import copy

import wx
from wx.lib.pubsub import Publisher as pub
from wx.lib.delayedresult import startWorker

from .open_data_file import open_data_file
from ..stages import filtering, detection, extraction, clustering
from .trial import format_traces

class Model(object):
    def __init__(self):
        self.trials = {}

    def setup_subscriptions(self):
        pub.subscribe(self._open_data_file,        "OPEN_DATA_FILE")
        pub.subscribe(self._close_data_file,       "CLOSE_DATA_FILE")
        pub.subscribe(self._filter,                "FILTER")
        pub.subscribe(self._detection,             "DETECTION")
        pub.subscribe(self._extraction,            "EXTRACTION")
        pub.subscribe(self._clustering,            "CLUSTERING")

    # ---- OPEN FILE ----
    def _open_data_file(self, message):
        fullpath = message.data
        if fullpath not in self.trials.keys():
            startWorker(self._open_file_consumer, self._open_file_worker, 
                        wargs=(fullpath,))
        else:
            pub.sendMessage(topic='FILE_ALREADY_OPENED',data=fullpath)

    def _open_file_worker(self, fullpath):
        try:
            if wx.Platform == '__WXMAC__':
                trial = open_data_file(fullpath)
            else:
                processing_pool = Pool()
                result = processing_pool.apply_async(open_data_file, 
                                                     args=(fullpath,))
                trial = result.get()
                processing_pool.close()
            self.trials[fullpath] = trial
        except:
            traceback.print_exc()
            sys.exit(1)
        return fullpath

    def _open_file_consumer(self, delayed_result):
        fullpath = delayed_result.get()
        pub.sendMessage(topic='TRIAL_ADDED', data=self.trials[fullpath])
        pub.sendMessage(topic='FILE_OPENED', data=fullpath)

    # ---- CLOSE FILE ----
    def _close_data_file(self, message):
        fullpath = message.data
        if fullpath in self.trials.keys():
            del self.trials[fullpath]
            pub.sendMessage(topic='FILE_CLOSED', data=fullpath)

    # ---- FILTER ----
    def _filter(self, message):
        stage_name, method_name, method_parameters = message.data
        for trial in self.trials.values():
            stage_data = getattr(trial, stage_name.lower().replace(' ','_'))
            stage_data.method   = method_name
            stage_data.settings = copy.deepcopy(method_parameters)
            stage_data.reset_results()
        trace_type = stage_name.split()[0] # removes ' filter' from name
        startWorker(self._filter_consumer, self._filter_worker,
                        wargs=(stage_name, method_name, method_parameters, 
                               trace_type),
                        cargs=(trace_type, stage_name))

    def _filter_worker(self, stage_name, method_name, 
                             method_parameters, trace_type):
        try:
            for trial in self.trials.values():
                raw_traces = trial.raw_traces
                filtered_traces = []
                method = filtering.get_method(method_name)
                method_parameters['sampling_freq'] = trial.sampling_freq
                if wx.Platform == '__WXMAC__':
                    filtered_traces = method.run(raw_traces, 
                                                 **method_parameters)
                else:
                    processing_pool = Pool()
                    result = processing_pool.apply_async(method.run, 
                                                         args=(raw_traces,),
                                                         kwds=method_parameters)
                    filtered_traces = result.get()
                    processing_pool.close()

                stage_data = getattr(trial, stage_name.lower().replace(' ','_'))
                stage_data.results = format_traces(filtered_traces)
        except:
            traceback.print_exc()
            sys.exit(1)

    def _filter_consumer(self, delayed_result, trace_type, stage_name):
        for trial in self.trials.values():
            pub.sendMessage(topic='TRIAL_%s_FILTERED' % trace_type.upper(),
                            data=trial)
        pub.sendMessage(topic='RUNNING_COMPLETED')


    # ---- DETECTION ----
    def _detection(self, message):
        stage_name, method_name, method_parameters = message.data
        for trial in self.trials.values():
            trial.detection.method   = method_name
            trial.detection.settings = copy.deepcopy(method_parameters)
            trial.detection.reset_results()

        startWorker(self._detection_consumer, self._detection_worker,
                        wargs=(method_name, method_parameters),
                        cargs=(stage_name,))

    def _detection_worker(self, method_name, method_parameters):
        try:
            for trial in self.trials.values():
                filtered_traces = trial.detection_filter.results
                method = detection.get_method(method_name)
                method_parameters['sampling_freq'] = trial.sampling_freq
                if wx.Platform == '__WXMAC__':
                    results = method.run(filtered_traces, **method_parameters)
                else: # osx doesn't do well with multiprocessing.
                    processing_pool = Pool()
                    result = processing_pool.apply_async(method.run, 
                            args=(filtered_traces,),
                            kwds=method_parameters)
                    results = result.get()
                    processing_pool.close()
                if len(results[0]) > 0: # ensure at least one spike was found.
                    trial.detection.results = results
        except:
            traceback.print_exc()
            sys.exit(1)

    def _detection_consumer(self, delayed_result, stage_name):
        for trial in self.trials.values():
            pub.sendMessage(topic='TRIAL_DETECTIONED', data=trial)
        pub.sendMessage(topic='RUNNING_COMPLETED')

    # ---- EXTRACTION ----
    def _extraction(self, message):
        stage_name, method_name, method_parameters = message.data
        for trial in self.trials.values():
            trial.extraction.method   = method_name
            trial.extraction.settings = copy.deepcopy(method_parameters)
            trial.extraction.reset_results()
        startWorker(self._extraction_consumer, self._extraction_worker,
                        wargs=(method_name, method_parameters),
                        cargs=(stage_name,))

    def _extraction_worker(self, method_name, method_parameters):
        try:
            for trial in self.trials.values():
                filtered_traces = trial.extraction_filter.results
                method = extraction.get_method(method_name)
                method_parameters['sampling_freq'] = trial.sampling_freq
                method_parameters['spike_list'] = trial.detection.results[0]
                if len(method_parameters['spike_list']) == 0:
                    return # no spikes from detection = no extraction
                if wx.Platform == '__WXMAC__':
                    results = method.run(filtered_traces, **method_parameters)
                else:
                    processing_pool = Pool()
                    result = processing_pool.apply_async(method.run, 
                            args=(filtered_traces,),
                            kwds=method_parameters)
                    results = result.get()
                    processing_pool.close()
                trial.extraction.results = results
        except:
            traceback.print_exc()
            sys.exit(1)

    def _extraction_consumer(self, delayed_result, stage_name):
        for trial in self.trials.values():
            pub.sendMessage(topic='TRIAL_EXTRACTIONED', data=trial)
        pub.sendMessage(topic='RUNNING_COMPLETED')

    # ---- CLUSTERING ----
    def _clustering(self, message):
        stage_name, method_name, method_parameters = message.data
        for trial in self.trials.values():
            trial.clustering.method   = method_name
            trial.clustering.settings = copy.deepcopy(method_parameters)
            trial.clustering.reset_results()
        startWorker(self._clustering_consumer, self._clustering_worker,
                        wargs=(method_name, method_parameters),
                        cargs=(stage_name,))

    def _clustering_worker(self, method_name, method_parameters):
        try:
            # get all feature_sets from all trials in a single long list.
            feature_set_list = []
            feature_time_list = []
            master_key_list = []
            trial_keys = sorted(self.trials.keys())
            for key in trial_keys:
                features = self.trials[key].extraction.results['features']
                feature_times = (self.trials[key].extraction.
                                 results['feature_times'])
                key_list = [key for i in xrange(len(features))]
                feature_set_list.extend(features)
                feature_time_list.extend(feature_times)
                master_key_list.extend(key_list)

            method = clustering.get_method(method_name)
            if len(feature_set_list) == 0:
                return # no spikes = no clustering
            if True or wx.Platform == '__WXMAC__':
                results = method.run(feature_set_list, **method_parameters)
            else:
                processing_pool = Pool()
                result = processing_pool.apply_async(method.run, 
                        args=(feature_set_list,),
                        kwds=method_parameters)
                results = result.get()
                processing_pool.close()

            # initialize clustering results to empty_list_dictionaries
            cluster_identities = set(results)
            for trial in self.trials.values():
                empty_dict = {}
                for ci in cluster_identities:
                    empty_dict[ci] = []
                trial.clustering.results = empty_dict 
            # unpack results from run back into trial results.
            for mkey, result, feature_time in \
                    zip(master_key_list, results, feature_time_list):
                trial_results = self.trials[mkey].clustering.results[result]
                trial_results.append(feature_time)
        except:
            traceback.print_exc()
            sys.exit(1)

    def _clustering_consumer(self, delayed_result, stage_name):
        for trial in self.trials.values():
            pub.sendMessage(topic='TRIAL_CLUSTERINGED', data=trial)
        pub.sendMessage(topic='RUNNING_COMPLETED')
