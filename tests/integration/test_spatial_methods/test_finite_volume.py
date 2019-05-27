#
# Test for the operator class
#
import pybamm
from tests import get_mesh_for_testing, get_p2d_mesh_for_testing

import numpy as np
import unittest


class TestFiniteVolumeConvergence(unittest.TestCase):
    def test_cartesian_spherical_grad_convergence(self):
        # note that grad function is the same for cartesian and spherical
        spatial_methods = {"macroscale": pybamm.FiniteVolume}
        whole_cell = ["negative electrode", "separator", "positive electrode"]

        # Define variable
        var = pybamm.Variable("var", domain=whole_cell)
        grad_eqn = pybamm.grad(var)
        boundary_conditions = {
            var.id: {
                "left": (pybamm.Scalar(0), "Dirichlet"),
                "right": (pybamm.Scalar(np.sin(1) ** 2), "Dirichlet"),
            }
        }

        # Function for convergence testing
        def get_error(n):
            # create mesh and discretisation
            mesh = get_mesh_for_testing(n)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            disc.bcs = boundary_conditions
            disc.set_variable_slices([var])

            # Define exact solutions
            combined_submesh = mesh.combine_submeshes(*whole_cell)
            x = combined_submesh[0].nodes
            y = np.sin(x) ** 2
            # var = sin(x)**2 --> dvardx = 2*sin(x)*cos(x)
            x_edge = combined_submesh[0].edges
            grad_exact = 2 * np.sin(x_edge) * np.cos(x_edge)

            # Discretise and evaluate
            grad_eqn_disc = disc.process_symbol(grad_eqn)
            grad_approx = grad_eqn_disc.evaluate(y=y)

            # Return difference between approx and exact
            return grad_approx[:, 0] - grad_exact

        # Get errors
        ns = 100 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect quadratic convergence at internal points
        errs_internal = np.array([np.linalg.norm(errs[n][1:-1], np.inf) for n in ns])
        rates = np.log2(errs_internal[:-1] / errs_internal[1:])
        np.testing.assert_array_less(1.99 * np.ones_like(rates), rates)
        # expect linear convergence at the boundaries
        for idx in [0, -1]:
            err_boundary = np.array([errs[n][idx] for n in ns])
            rates = np.log2(err_boundary[:-1] / err_boundary[1:])
            np.testing.assert_array_less(0.98 * np.ones_like(rates), rates)

    def test_cartesian_div_convergence(self):
        whole_cell = ["negative electrode", "separator", "positive electrode"]
        spatial_methods = {"macroscale": pybamm.FiniteVolume}

        # Function for convergence testing
        def get_error(n):
            # create mesh and discretisation
            mesh = get_mesh_for_testing(n)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            combined_submesh = mesh.combine_submeshes(*whole_cell)
            x = combined_submesh[0].nodes
            x_edge = combined_submesh[0].edges

            # Define flux and bcs
            N = pybamm.Vector(x_edge ** 2 * np.cos(x_edge), domain=whole_cell)
            div_eqn = pybamm.div(N)
            # Define exact solutions
            # N = x**2 * cos(x) --> dNdx = x*(2cos(x) - xsin(x))
            div_exact = x * (2 * np.cos(x) - x * np.sin(x))

            # Discretise and evaluate
            div_eqn_disc = disc.process_symbol(div_eqn)
            div_approx = div_eqn_disc.evaluate()

            # Return difference between approx and exact
            return div_approx[:, 0] - div_exact

        # Get errors
        ns = 10 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect quadratic convergence everywhere
        err_norm = np.array([np.linalg.norm(errs[n], np.inf) for n in ns])
        rates = np.log2(err_norm[:-1] / err_norm[1:])
        np.testing.assert_array_less(1.99 * np.ones_like(rates), rates)

    def test_spherical_div_convergence_quadratic(self):
        # test div( r**2 * sin(r) ) == 4*r*sin(r) - r**2*cos(r)
        spatial_methods = {"negative particle": pybamm.FiniteVolume}

        # Function for convergence testing
        def get_error(n):
            # create mesh and discretisation (single particle)
            mesh = get_mesh_for_testing(n)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            submesh = mesh["negative particle"]
            r = submesh[0].nodes
            r_edge = submesh[0].edges

            # Define flux and bcs
            N = pybamm.Vector(
                r_edge ** 2 * np.sin(r_edge), domain=["negative particle"]
            )
            div_eqn = pybamm.div(N)
            # Define exact solutions
            # N = r**3 --> div(N) = 5 * r**2
            div_exact = 4 * r * np.sin(r) + r ** 2 * np.cos(r)

            # Discretise and evaluate
            div_eqn_disc = disc.process_symbol(div_eqn)
            div_approx = div_eqn_disc.evaluate()

            # Return difference between approx and exact
            return div_approx[:, 0] - div_exact

        # Get errors
        ns = 10 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect quadratic convergence everywhere
        err_norm = np.array([np.linalg.norm(errs[n], np.inf) for n in ns])
        rates = np.log2(err_norm[:-1] / err_norm[1:])
        np.testing.assert_array_less(1.99 * np.ones_like(rates), rates)

    def test_spherical_div_convergence_linear(self):
        # test div( r*sin(r) ) == 3*sin(r) + r*cos(r)
        spatial_methods = {"negative particle": pybamm.FiniteVolume}

        # Function for convergence testing
        def get_error(n):
            # create mesh and discretisation (single particle)
            mesh = get_mesh_for_testing(n)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            submesh = mesh["negative particle"]
            r = submesh[0].nodes
            r_edge = submesh[0].edges

            # Define flux and bcs
            N = pybamm.Vector(r_edge * np.sin(r_edge), domain=["negative particle"])
            div_eqn = pybamm.div(N)
            # Define exact solutions
            # N = r*sin(r) --> div(N) = 3*sin(r) + r*cos(r)
            div_exact = 3 * np.sin(r) + r * np.cos(r)

            # Discretise and evaluate
            div_eqn_disc = disc.process_symbol(div_eqn)
            div_approx = div_eqn_disc.evaluate()

            # Return difference between approx and exact
            return div_approx[:, 0] - div_exact

        # Get errors
        ns = 10 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect linear convergence everywhere
        err_norm = np.array([np.linalg.norm(errs[n], np.inf) for n in ns])
        rates = np.log2(err_norm[:-1] / err_norm[1:])
        np.testing.assert_array_less(0.99 * np.ones_like(rates), rates)

    def test_p2d_spherical_convergence_quadratic(self):
        # test div( r**2 * sin(r) ) == 4*r*sin(r) - r**2*cos(r)
        spatial_methods = {"negative particle": pybamm.FiniteVolume}

        # Function for convergence testing
        def get_error(m):
            # create mesh and discretisation p2d, uniform in x
            mesh = get_p2d_mesh_for_testing(3, m)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            submesh = mesh["negative particle"]
            r = submesh[0].nodes
            r_edge = submesh[0].edges

            N = pybamm.Matrix(
                np.kron(np.ones(len(submesh)), r_edge ** 2 * np.sin(r_edge)),
                domain=["negative particle"],
            )
            div_eqn = pybamm.div(N)
            # Define exact solutions
            # N = r**2*sin(r) --> div(N) = 4*r*sin(r) - r**2*cos(r)
            div_exact = 4 * r * np.sin(r) + r ** 2 * np.cos(r)
            div_exact = np.kron(np.ones(len(submesh)), div_exact)

            # Discretise and evaluate
            div_eqn_disc = disc.process_symbol(div_eqn)
            div_approx = div_eqn_disc.evaluate()

            return div_approx[:, 0] - div_exact

        # Get errors
        ns = 10 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect quadratic convergence everywhere
        err_norm = np.array([np.linalg.norm(errs[n], np.inf) for n in ns])
        rates = np.log2(err_norm[:-1] / err_norm[1:])
        np.testing.assert_array_less(1.99 * np.ones_like(rates), rates)

    def test_p2d_with_x_dep_bcs_spherical_convergence(self):
        # test div_r( (r**2 * sin(r)) * x ) == (4*r*sin(r) - r**2*cos(r)) * x
        spatial_methods = {"negative particle": pybamm.FiniteVolume}

        # Function for convergence testing
        def get_error(m):
            # create mesh and discretisation p2d, x-dependent
            mesh = get_p2d_mesh_for_testing(6, m)
            disc = pybamm.Discretisation(mesh, spatial_methods)
            submesh_r = mesh["negative particle"]
            r = submesh_r[0].nodes
            r_edge = submesh_r[0].edges
            x = pybamm.Vector(mesh["negative electrode"][0].nodes)

            N = pybamm.Matrix(
                np.kron(x.entries[:, 0], r_edge ** 2 * np.sin(r_edge)),
                domain=["negative particle"],
            )
            div_eqn = pybamm.div(N)
            # Define exact solutions
            # N = r**2*sin(r) --> div(N) = 4*r*sin(r) - r**2*cos(r)
            div_exact = 4 * r * np.sin(r) + r ** 2 * np.cos(r)
            div_exact = np.kron(x.entries[:, 0], div_exact)

            # Discretise and evaluate
            div_eqn_disc = disc.process_symbol(div_eqn)
            div_approx = div_eqn_disc.evaluate()

            return div_approx[:, 0] - div_exact

        # Get errors
        ns = 10 * 2 ** np.arange(6)
        errs = {n: get_error(int(n)) for n in ns}
        # expect quadratic convergence everywhere
        err_norm = np.array([np.linalg.norm(errs[n], np.inf) for n in ns])
        rates = np.log2(err_norm[:-1] / err_norm[1:])
        np.testing.assert_array_less(1.99 * np.ones_like(rates), rates)


if __name__ == "__main__":
    print("Add -v for more debug output")
    import sys

    if "-v" in sys.argv:
        debug = True
    unittest.main()
