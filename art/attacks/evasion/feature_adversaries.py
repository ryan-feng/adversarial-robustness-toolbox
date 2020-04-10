# MIT License
#
# Copyright (C) IBM Corporation 2020
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""
This module implements the Feature Adversaries attack.

| Paper link: https://arxiv.org/abs/1511.05122
"""
import logging

import numpy as np

from art.classifiers.classifier import ClassifierGradients
from art.attacks.attack import EvasionAttack
from art.exceptions import ClassifierError

logger = logging.getLogger(__name__)


class FeatureAdversaries(EvasionAttack):
    """
    This class represent a Feature Adversaries evasion attack.

    | Paper link: https://arxiv.org/abs/1511.05122
    """

    attack_params = EvasionAttack.attack_params + [
        "delta",
        "layer",
        "batch_size",
    ]

    def __init__(
        self, classifier, delta, layer, batch_size=32,
    ):
        """
        Create a :class:`.FeatureAdversaries` instance.

        :param classifier: A trained classifier.
        :type classifier: :class:`.Classifier`
        :param delta: The maximum deviation between source and guide images.
        :type delta: `float`
        :param layer: Index of the representation layer.
        :type layer: `int`
        :param batch_size: Batch size.
        :type batch_size: `int`
        """
        super(FeatureAdversaries, self).__init__(classifier)

        if not isinstance(classifier, ClassifierGradients):
            raise ClassifierError(self.__class__, [ClassifierGradients], classifier)

        kwargs = {
            "delta": delta,
            "layer": layer,
            "batch_size": batch_size,
        }

        FeatureAdversaries.set_params(self, **kwargs)

        self.norm = np.inf

    def generate(self, x, y=None, **kwargs):
        """Generate adversarial samples and return them in an array.

        :param x: Source samples.
        :type x: `np.ndarray`
        :param y: Guide samples.
        :type y: `np.ndarray`
        :return: Adversarial examples.
        :rtype: `np.ndarray`
        """

        from scipy.optimize import minimize, Bounds
        from scipy.linalg import norm

        lb = x.flatten() - self.delta
        lb[lb < 0.0] = 0.0

        ub = x.flatten() + self.delta
        ub[ub > 1.0] = 1.0

        bound = Bounds(lb=lb, ub=ub, keep_feasible=False)

        guide_representation = self.classifier.get_activations(
            x=y.reshape(-1, *self.classifier.input_shape), layer=self.layer, batch_size=self.batch_size
        )

        def func(x_i):
            source_representation = self.classifier.get_activations(
                x=x_i.reshape(-1, *self.classifier.input_shape), layer=self.layer, batch_size=self.batch_size
            )

            n = norm(source_representation.flatten() - guide_representation.flatten(), ord=2) ** 2

            return n

        x_0 = x.copy()

        res = minimize(func, x_0, method="L-BFGS-B", bounds=bound, options={"eps": 1e-3, "ftol": 1e-2})
        logger.info(res)

        x_adv = res.x

        return x_adv

    def set_params(self, **kwargs):
        """
        Take in a dictionary of parameters and applies attack-specific checks before saving them as attributes.

        :param delta: The maximum deviation between source and guide images.
        :type delta: `float`
        :param layer: Index of the representation layer.
        :type layer: `int`
        :param batch_size: Batch size.
        :type batch_size: `int`
        """
        # Save attack-specific parameters
        super(FeatureAdversaries, self).set_params(**kwargs)

        if self.delta <= 0:
            raise ValueError("The maximum deviation `delta` has to be positive.")

        if not isinstance(self.layer, int):
            raise ValueError("The index of the representation layer `layer` has to be integer.")

        if self.batch_size <= 0:
            raise ValueError("The batch size `batch_size` has to be positive.")
