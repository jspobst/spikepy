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

from spikepy.common.valid_types import ValidType
from spikepy.common.errors import *

class DataInterpreter(object):
    '''
    This class should be subclassed in order for developers to add a new way to
export data from spikepy.  
    There is no need to instantiate (create an object from) the subclass, 
spikepy will handle that internally.  Therefore it is important to have 
an __init__ method which requires no arguments (asside from 'self' of course).
    '''
    name = 'Some Name'
    description = 'Some description.'

    requires = []

    def construct_filenames(self, trials, base_path):
        """
            Returns a dictionary keyed on the trial_id with values that are
        the base filenames of the exported data.
        """
        return_dict = {}
        for trial in trials:
            filename = '%s__%s' % (trial.display_name, 
                    self.name.replace(' ', '_'))
            return_dict[trial.trial_id] = os.path.join(base_path, filename)
        return return_dict

    def is_available(self, trials):
        try:
            self._check_requirements(trials)
            return True
        except DataUnavailableError:
            return False

    def _check_requirements(self, trials):
        '''
            Raises DataUnavailableError if requirements are not met for this
        data_interpreter.  Returns None.
        '''
        for trial in trials:
            for req in self.requires:
                if not hasattr(trial, req):
                    raise DataUnavailableError("Trial '%s' does not have resource '%s'." % (trial.display_name, req))
                else:
                    resource = getattr(trial, req)
                    if resource.data is None:
                        raise DataUnavailableError("Trial '%s' has not yet set resource '%s'." % (trial.display_name, req))
                        

    def write_data_file(self, trials, **kwargs):
        """
        Will accept keyword args that are ValidType class variables, in
        much the same way that Method classes do.

        Should raise DataUnavailableError if trials do not have what is
        required.

        Should return a list of written filenames.
        """
        raise NotImplementedError

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
