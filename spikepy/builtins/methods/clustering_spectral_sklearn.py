"""
Copyright (C) 2012  David Morton

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
from sklearn.cluster import SpectralClustering
from sklearn.metrics.pairwise import euclidean_distances
import numpy

from spikepy.developer.methods import ClusteringMethod
from spikepy.common.valid_types import ValidInteger, ValidOption, ValidBoolean
from spikepy.common.valid_types import ValidFloat

class ClusteringSpectralSKLearn(ClusteringMethod):
    '''
        This class implements a spectral clustering method using the sklearn 
    package.
    '''
    name = 'Spectral (sklearn)'
    description = 'Spectral clustering from the sklearn package.'
    is_stochastic = True
    
    restarts = ValidInteger(1, 10000, default=10)
    number_of_clusters = ValidInteger(1, 30, default=2, description=
            'The number of clusters that will be identified.')
    delta = ValidFloat(0.01, 100, default=3, 
            description='Scaling term for the similarity matrix')

    def run(self, features, number_of_clusters=2, restarts=10, delta=3.0):
        if number_of_clusters == 1:
            result = numpy.zeros(len(features), dtype=numpy.int32)
            return [result]
        classifier = SpectralClustering(k=number_of_clusters, n_init=restarts)
        similarity = get_similarity(features, delta)
        classifier.fit(similarity)
        return [classifier.labels_]

def get_similarity(features, delta):
    distances = euclidean_distances(features)
    std = numpy.std(distances)
    return numpy.exp(-distances**2 / (2.0 * (delta*std)**2))
    
