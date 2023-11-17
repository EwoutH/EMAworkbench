import unittest

from ema_workbench.em_framework.util import NamedObject
from ema_workbench.em_framework import points


class TestCases(unittest.TestCase):
    def test_experiment_gemerator(self):
        scenarios = [NamedObject("scen_1"), NamedObject("scen_2")]
        model_structures = [NamedObject("model")]
        policies = [NamedObject("1"), NamedObject("2"), NamedObject("3")]

        experiments = points.experiment_generator(
            scenarios, model_structures, policies, combine="factorial"
        )
        experiments = list(experiments)
        self.assertEqual(len(experiments), 6, ("wrong number of experiments " "for factorial"))

        experiments = points.experiment_generator(
            scenarios, model_structures, policies, combine="sample"
        )
        experiments = list(experiments)
        self.assertEqual(len(experiments), 3, ("wrong number of experiments " "for zipover"))

        with self.assertRaises(ValueError):
            experiments = points.experiment_generator(
                scenarios, model_structures, policies, combine="adf"
            )
            _ = list(experiments)


if __name__ == "__main__":
    unittest.main()
