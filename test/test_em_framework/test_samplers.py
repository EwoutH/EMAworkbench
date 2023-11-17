"""
Created on 21 jan. 2013

.. codeauthor:: jhkwakkel <j.h.kwakkel (at) tudelft (dot) nl>
"""
import unittest.mock as mock
import unittest

from ema_workbench.em_framework.samplers import (
    LHSSampler,
    MonteCarloSampler,
    FullFactorialSampler,
    determine_parameters,
)
from ema_workbench.em_framework.parameters import (
    RealParameter,
    IntegerParameter,
    CategoricalParameter,
)
from ema_workbench.em_framework.points import Scenario
from ema_workbench.em_framework import Model


class SamplerTestCase(unittest.TestCase):
    uncertainties = [
        RealParameter("1", 0, 10),
        IntegerParameter("2", 0, 10),
        CategoricalParameter("3", ["a", "b", "c"]),
    ]

    def _test_generate_designs(self, sampler):
        designs = sampler.generate_designs(self.uncertainties, 10)
        designs.kind = Scenario
        msg = f"tested for {type(sampler)}"

        actual_nr_designs = 0
        for design in designs:
            actual_nr_designs += 1

        self.assertIn("1", design, msg)
        self.assertIn("2", design, msg)
        self.assertIn("3", design, msg)
        self.assertEqual(designs.n, actual_nr_designs, msg)

    def test_lhs_sampler(self):
        sampler = LHSSampler()
        self._test_generate_designs(sampler)

    def test_mc_sampler(self):
        sampler = MonteCarloSampler()
        self._test_generate_designs(sampler)

    def test_ff_sampler(self):
        sampler = FullFactorialSampler()
        self._test_generate_designs(sampler)

    def test_determine_parameters(self):
        function = mock.Mock()
        model_a = Model("A", function)
        model_a.uncertainties = [
            RealParameter("a", 0, 1),
            RealParameter("b", 0, 1),
        ]
        function = mock.Mock()
        model_b = Model("B", function)
        model_b.uncertainties = [
            RealParameter("b", 0, 1),
            RealParameter("c", 0, 1),
        ]

        models = [model_a, model_b]

        parameters = determine_parameters(models, "uncertainties", union=True)
        for model in models:
            for unc in model.uncertainties:
                self.assertIn(unc.name, parameters.keys())

        parameters = determine_parameters(models, "uncertainties", union=False)
        self.assertIn("b", parameters.keys())
        self.assertNotIn("c", parameters.keys())
        self.assertNotIn("a", parameters.keys())


if __name__ == "__main__":
    unittest.main()
