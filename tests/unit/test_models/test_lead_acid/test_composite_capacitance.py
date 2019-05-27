#
# Tests for the lead-acid composite model
#
import pybamm
import unittest


class TestLeadAcidCompositeCapacitance(unittest.TestCase):
    def test_well_posed(self):
        model = pybamm.lead_acid.CompositeCapacitance()
        model.check_well_posedness()

    def test_well_posed_no_capacitance(self):
        model = pybamm.lead_acid.CompositeCapacitance(use_capacitance=False)
        model.check_well_posedness()

    def test_default_solver(self):
        model = pybamm.lead_acid.CompositeCapacitance(use_capacitance=True)
        self.assertIsInstance(model.default_solver, pybamm.ScikitsOdeSolver)
        model = pybamm.lead_acid.CompositeCapacitance(use_capacitance=False)
        self.assertIsInstance(model.default_solver, pybamm.ScikitsDaeSolver)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
