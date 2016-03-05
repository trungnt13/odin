# ======================================================================
# Author: TrungNT
# ======================================================================
from __future__ import print_function, division

from .. import nnet
from .. import tensor as T
from .. import logger
from .. import objectives
from .. import optimizers

import unittest

import os
import numpy as np

from six.moves import zip, range

# ===========================================================================
# Main Test
# ===========================================================================


class FunctionsTest(unittest.TestCase):

    def setUp(self):
        logger.set_enable(False)

    def tearDown(self):
        logger.set_enable(True)

    def test_dense_func(self):
        d3 = nnet.Dense((None, 10), num_units=5, nonlinearity=T.linear)
        f_pred = T.function(d3.input_var, d3())

        x = np.random.rand(16, 10)
        y = np.random.rand(16, 5)

        p = d3.get_params_value(True)[0]
        pred1 = np.round(f_pred(x)[0], 6)
        pred2 = np.round(np.dot(x, p), 6)
        self.assertLessEqual(np.sum(np.abs(pred1 - pred2)), 10e-5)

        # ====== only cost ====== #
        cost, _ = d3.get_optimization(
            objective=objectives.squared_loss,
            training=False)
        f_cost = T.function(d3.input_var + d3.output_var, cost)

        cost1 = np.round(np.mean(f_cost(x, y)), 6)
        cost2 = np.round(np.mean((np.dot(x, p) - y)**2), 6)
        self.assertLessEqual(np.sum(np.abs(cost1 - cost2)), 10e-5)

        # ====== optimization ====== #
        cost, updates = d3.get_optimization(
            objective=objectives.mean_squared_loss,
            optimizer=optimizers.sgd)
        f_updates = T.function(
            inputs=d3.input_var + d3.output_var,
            outputs=cost,
            updates=updates)
        cost = []
        for i in range(10):
            cost.append(f_updates(x, y))
        self.assertGreater(cost[:-1], cost[1:])

    def test_summation_merge(self):
        d1 = nnet.Dense((None, 10), num_units=5, nonlinearity=T.linear)
        d2 = nnet.Dense((None, 20), num_units=5, nonlinearity=T.linear)
        d3 = nnet.Summation((d1, d2))

        params = d3.get_params_value(True)
        p1 = params[0]
        p2 = params[2]

        f_pred = T.function(d3.input_var, d3()[0])

        x1 = np.random.rand(16, 10)
        x2 = np.random.rand(16, 20)

        pred1 = np.round(f_pred(x1, x2), 6)
        pred2 = np.round(np.dot(x1, p1) + np.dot(x2, p2), 6)

        self.assertLessEqual(np.sum(np.abs(pred1 - pred2)), 10e-5)

    def test_get_roots_and_children(self):
        d1a = nnet.Dense((None, 28, 28), num_units=256, name='d1a')
        d1b = nnet.Dense(d1a, num_units=128, name='d1b')
        d1c = nnet.Dense(d1b, num_units=128, name='d1c')
        d1d = nnet.Summation([(None, 128), d1c], name='Summation')

        self.assertEqual(d1d.incoming, [None, d1c])
        self.assertEqual(d1d.input_shape, [(None, 128), (None, 128)])
        self.assertEqual([T.ndim(i) for i in d1d.input_var], [2, 3])
        self.assertEqual(d1d.get_roots(), [d1d, d1a])
        self.assertEqual(d1d.get_children(), [d1c, d1b, d1a])

    def test_noise(self):
        np.random.seed(12082518)
        x = np.ones((16, 5, 8))
        f = nnet.Dropout([(16, 5, 8), (16, 5, 8)],
            p=0.5, rescale=True, noise_dims=1, seed=13, consistent=True)
        f = nnet.Ops(f, ops=lambda x: x + 0.)
        f = T.function(inputs=f.input_var, outputs=f(True))
        y = f(x, x)
        y = y[0] - y[1]
        self.assertEqual(y.ravel().tolist(), [0.] * len(y.ravel()))

        f = nnet.Noise([(16, 5, 8), (16, 5, 8)],
            sigma=0.5, noise_dims=(1, 2), uniform=True, seed=13, consistent=True)
        f = nnet.Ops(f, ops=lambda x: x + 0.)
        f = T.function(inputs=f.input_var, outputs=f(True))
        y = f(x, x)
        y = y[0] - y[1]
        self.assertEqual(y.ravel().tolist(), [0.] * len(y.ravel()))

    def test_function_as_weights(self):
        dense_in = nnet.Dense((10, 30), num_units=20, name='dense_in')
        dense = nnet.Dense((None, 28), num_units=10, name='dense1')
        dense = nnet.Dense(dense, num_units=20,
            W=dense_in, name='dense2')
        f = T.function(
            inputs=dense.input_var + dense_in.input_var,
            outputs= dense())
        shape = f(np.random.rand(13, 28),
              np.random.rand(10, 30))[0].shape
        self.assertEqual(shape, (13, 20))

    def test_rnn(self):
        # ====== simulate data ====== #
        X = np.ones((128, 28, 10))
        Xmask = np.ones((128, 28))
        X1 = np.ones((128, 20, 10))

        y = np.ones((128, 28, 5))
        y1 = np.ones((128, 20, 5))

        # ====== build model ====== #
        v1 = T.placeholder(shape=(None, 28, 10))
        hid_init1 = nnet.Dense(v1, num_units=5)
        v2 = T.placeholder(shape=(None, 20, 10))
        hid_init2 = nnet.Dense(v2, num_units=5)
        hid_init = nnet.Ops([hid_init1, hid_init2], ops=T.linear)
        f = nnet.Recurrent(
            incoming=[v1, v2], mask=[(None, 28)],
            hidden_to_hidden=5,
            hidden_init=hid_init, learn_init=True,
            nonlinearity=T.sigmoid,
            unroll_scan=False,
            backwards=False,
            grad_clipping=0.001
        )

        print('\n')
        print('Building prediction function ...')
        f_pred = T.function(
            inputs=f.input_var,
            outputs=f())
        cost, updates = f.get_optimization(
            objective=objectives.mean_squared_loss,
            optimizer=optimizers.rmsprop,
            globals=True,
            training=True)
        print('Building training function ...')
        f_train = T.function(
            inputs=f.input_var + f.output_var,
            outputs=cost,
            updates=updates)
        print('Input variables: ', f.input_var)
        print('Ouput variables: ', f.output_var)
        print('Input shape:     ', f.input_shape)
        print('Output shape:    ', f.output_shape)
        print('Params:          ', f.get_params(True))
        print('Prediction shape:', [i.shape for i in f_pred(X, Xmask, X1)])
        print('Training cost:',
            f_train(X, Xmask, X1, y, y1),
            f_train(X, Xmask, X1, y, y1),
            f_train(X, Xmask, X1, y, y1),
            f_train(X, Xmask, X1, y, y1),
            f_train(X, Xmask, X1, y, y1),
            f_train(X, Xmask, X1, y, y1))

    def test_rnn_auto_input_to_hidden(self):
        X = np.random.rand(16, 30, 3, 28, 28)
        f = nnet.Recurrent(
            incoming=(None, 30, 3, 28, 28), mask=None,
            input_to_hidden='auto',
            hidden_to_hidden=nnet.Conv2D(
                (None, 32, 28, 28), num_filters=32, filter_size=(3, 3), pad='same'),
            hidden_init=None, learn_init=True,
            nonlinearity=T.sigmoid,
            unroll_scan=False,
            backwards=False,
            grad_clipping=0.001,
            only_return_final=False
        )
        f = T.function(inputs=f.input_var, outputs=f())
        self.assertEqual(tuple(f(X)[0].shape), (16, 30, 32, 28, 28))

    def test_memory_cell(self):
        np.random.seed(1208251813)
        X = T.variable(np.random.rand(256, 128, 20))

        c = nnet.Cell(cell_init=T.zeros_var(shape=(256, 13), name='cell_init'),
                      input_dims=(None, 128, 20),
                      W_cell=T.np_normal,
                      learnable=True,
                      algorithm=nnet.simple_algorithm,
                      nonlinearity=T.tanh)
        # 1 parameter for cell_init
        c.add_gate(name='forget') # 4 params
        c.add_gate(name='input') # 4 params
        c.add_gate(name='cellin', nonlinearity=T.tanh, force_no_cell=True) # 3 params
        c.add_gate(name='output') # 4 params
        self.assertEqual(len(c.get_params(True)), 16)

        X = T.dimshuffle(X, (1, 0, 2))
        X = c.precompute(X)
        self.assertEqual(tuple(T.eval(T.shape(X))), (128, 256, 52))

        hidden_init = T.zeros_var(shape=(256, 13), name='hid_init')
        output_init = hidden_init
        cell_init = c()[0]
        cell = c.step([X[0]], hidden_init, output_init, cell_init)
        hid_new, cell_new = cell[0]
        self.assertEqual(tuple(hid_new.eval().shape), (256, 13))
        self.assertEqual(tuple(cell_new.eval().shape), (256, 13))
        self.assertEqual(T.sum(T.abs(T.eval(T.tanh(cell_new) - hid_new))).eval(),
                         0.)

# ===========================================================================
# Main
# ===========================================================================
if __name__ == '__main__':
    print(' Use nosetests to run these tests ')
