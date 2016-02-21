from __future__ import print_function, division, absolute_import

import numpy as np

from .. import tensor as T
from ..base import OdinFunction

class Summation(OdinFunction):

    def __init__(self, incoming, unsupervised=False, **kwargs):
        super(Summation, self).__init__(
            incoming, unsupervised=unsupervised, **kwargs)

    @property
    def output_shape(self):
        return self.input_shape[0]

    def _call(self, training, inputs, **kwargs):
        return sum(x for x in inputs)

    def get_optimization(self, objective=None, optimizer=None,
                         globals=True, training=True):
        return self._deterministic_optimization_procedure(
            objective, optimizer, globals, training)
