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

import itertools

import numpy

from spikepy.utils.fast_thresh_detect import fast_thresh_detect

def spike_find(input_array, t, max_spike_width):
    '''
    Find the spikes in the input_array.
    Inputs:
        input_array              : a numpy array (1-dimensional) holding 
                                   floats.
        t                        : threshold for spike detection
        max_spike_width          : crossings further apart than this will 
                                   disqualify the spike
    Returns:
        spikes                   : a numpy array (1-dimensional) holding
                                   integers (spike index values)
    '''
    crossings = fast_thresh_detect(input_array, threshold=t)
    spikes = []
    if len(crossings) > 1:
        if t > 0.0:
            # find first positive crossing then pair up crossings
            first_p = numpy.argwhere( input_array[crossings]<t )[0][0]
            for p, n in itertools.izip( crossings[first_p::2], 
                                        crossings[first_p+1::2] ):
                if abs(p - n) <= max_spike_width:
                    peak_index = numpy.argsort(input_array[p:n+1])[-1]+p
                    spikes.append(peak_index)
        else:
            # find first negative crossing then pair up crossings
            first_n = numpy.argwhere( input_array[crossings]>t )[0][0]
            for n, p in itertools.izip( crossings[first_n::2], 
                                        crossings[first_n+1::2] ):
                if abs(p - n) <= max_spike_width:
                    peak_index = numpy.argsort(input_array[n:p+1])[0]+n
                    spikes.append(peak_index)
    return numpy.array(spikes)
    
def two_threshold_spike_find(input_array, threshold_1, threshold_2=None, 
                             max_spike_width=2, refractory_period=0):
    '''
    Find spikes given two thresholds.
    Inputs:
        input_array              : a numpy array (1-dimensional) holding 
                                   floats.
        threshold_1              : a threshold for spike detection
        --kwargs--
        threshold_2              : a threshold for spike detection
        max_spike_width          : crossings further apart than this will 
                                   disqualify the spike
        refractory_period        : after clumping, if spikes are closer 
                                   than this, the second will be excluded.
    Returns:
        spikes                   : a numpy array (1-dimensional) holding
                                   integers (spike index values)

    '''
    t1 = max(threshold_1, threshold_2)
    t2 = min(threshold_1, threshold_2)
    s1 = spike_find(input_array, t1, max_spike_width)
    if t2 == t1 or t2 is None:
        all_spikes = list(s1)
    else:
        s2 = spike_find(input_array, t2, max_spike_width)
        all_spikes = sorted(list(s1) + list(s2))

    # enforce refractory period
    if len(all_spikes) > 1:
        kept_spikes = [all_spikes[0]]
        for spike in all_spikes[1:]:
             if abs(kept_spikes[-1]-spike) > refractory_period:
                    kept_spikes.append(spike)
    else:
        kept_spikes = all_spikes
    return numpy.array(kept_spikes)
