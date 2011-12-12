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
import pylab

from spikepy.common.config_manager import config_manager as config
from spikepy.plotting_utils.plot_panel import PlotPanel
from spikepy.common.valid_types import ValidType

class Visualization(object):
    """
    This class should be subclassed in order for developers to add a new
visualization to spikepy (non-interactive plots and graphs and such).
There is no need ot instantiate (create an object from) the subclass,
spikepy will handle that internally.  Therefore it is important to have an
__init__ method that requires no arguments.
    """
    name = ''
    requires = []
    # one of 'detection_filter', 'detection', 'extraction_filter',
    #        'extraction', 'clustering', or 'summary' **only used with gui**
    found_under_tab = 'detection_filter'

    def __init__(self):
        self._change_ids = {}
        for resource_name in self.requires:
            self._change_ids[resource_name] = None 

    def _plot(self, trial, figure, **kwargs):
        '''
            Plot the results from <trial> onto the <figure>.  This is most 
        likely all you'll need to redefine in your subclasses.
        '''
        raise NotImplementedError

    def draw(self, trial, parent_panel=None, **kwargs):
        # are we running within the gui?
        if parent_panel is not None:
            parent_panel.plot_panel.figure.clear()
            self._plot(trial, parent_panel.plot_panel.figure, **kwargs)

            canvas = parent_panel.plot_panel.canvas
            canvas.draw()
        else:
            figsize = config.get_size('figure')
            figure = pylab.figure(figsize=figsize)
            figure.canvas.set_window_title(self.name)
            self._plot(trial, figure, **kwargs)
            pylab.show()
            # reset change_ids so the visualization is forced to plot again
            #  next time.
            for resource_name in self.requires:
                self._change_ids[resource_name] = None 

    def get_parameter_attributes(self):
        ''' Return a dictionary of ValidType attributes. '''
        attrs = {}
        attribute_names = dir(self)
        for name in attribute_names:
            value = getattr(self, name)
            if isinstance(value, ValidType):
                attrs[name] = value
        return attrs
    
    def get_parameter_defaults(self):
        ''' Return a dictionary containing the default parameter values.  '''
        kwargs = {}
        for attr_name, attr in self.get_parameter_attributes().items():
            kwargs[attr_name] = attr()
        return kwargs

    def validate_parameters(self, parameter_dict):
        '''
            Attempts to validate parameters in a dictionary.  If parameters are 
        invalid an exception is raised.  If parameters are valid, None is 
        returned.
        '''
        for key, value in parameter_dict.items():
            getattr(self, key)(value)
        