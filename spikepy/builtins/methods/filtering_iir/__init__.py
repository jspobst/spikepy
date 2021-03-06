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

from spikepy.developer.methods import FilteringMethod
from spikepy.common.valid_types import ValidOption, \
        ValidInteger, ValidBoolean
from .simple_iir import butterworth, bessel

class FilteringIIR(FilteringMethod):
    '''
    This class implements an infinte impulse response filtering method.
    '''
    name = 'Infinite Impulse Response'
    description = 'Butterworth and bessel filters.  Can be high/low/band pass types.'
    is_stochastic = False

    function_name = ValidOption('butterworth', 'bessel', default='butterworth')
    acausal = ValidBoolean(default=True)
    low_cutoff_frequency = ValidInteger(min=10, default=300)
    high_cutoff_frequency = ValidInteger(min=10, default=3000)
    kind = ValidOption('low pass', 'high pass', 'band pass', 
            'band stop', default='band pass')
    order = ValidInteger(2, 8, default=3)

    def run(self, signal, sampling_freq, **kwargs):
        if kwargs['function_name'].lower() == 'butterworth':
            filter_function = butterworth
        elif kwargs['function_name'].lower() == 'bessel':
            filter_function = bessel
        del kwargs['function_name']

        kind = kwargs['kind'] = kwargs['kind'].replace(' ', '')
        if kind == 'low':
            critical_freq = kwargs['low_cutoff_frequency']
        elif kind == 'high':
            critical_freq = kwargs['high_cutoff_frequency']
        else:
            critical_freq = (kwargs['low_cutoff_frequency'],
                    kwargs['high_cutoff_frequency'])
        del kwargs['low_cutoff_frequency']
        del kwargs['high_cutoff_frequency']
        kwargs['critical_freq'] = critical_freq

        filtered_signal = filter_function(signal, sampling_freq, **kwargs)
        return [filtered_signal, sampling_freq]
    
