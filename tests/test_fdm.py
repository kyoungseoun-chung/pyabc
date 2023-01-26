#!/usr/bin/env python3
"""Test fvc (finite difference - volume centered) solver module.

Need to be revised. I comfused concept of fvc and fvm.
"""
from math import pi

import pytest
import torch
from torch.testing import assert_close  # type: ignore

from pyapes.core.geometry import Box
from pyapes.core.mesh import Mesh
from pyapes.core.solver.fdm import FDM
from pyapes.core.solver.ops import Solver
from pyapes.core.variables import Field
from pyapes.core.variables.bcs import homogeneous_bcs
from pyapes.testing.burgers import burger_exact_nd


def test_disc_w_bc() -> None:

    t_field = torch.rand(11)
    dx = 0.1

    # Normal Laplacian
    l_val = (
        torch.roll(t_field, -1, 0) - 2 * t_field + torch.roll(t_field, 1, 0)
    ) / (dx**2)

    # Neumann BC l-r
    bc_val = 2.0


@pytest.mark.parametrize(
    ["domain", "spacing"],
    [
        [Box[0:1], [0.2]],
        [Box[0:1, 0:1], [0.2, 0.2]],
        [Box[0:1, 0:1, 0:1], [0.2, 0.2, 0.2]],
    ],
)
def test_fdc_ops(domain: Box, spacing: list[float]) -> None:
    """Test FDC module that discretizes current field values."""

    from pyapes.core.solver.fdc import FDC

    mesh = Mesh(domain, None, spacing)

    # Field boundaries are all set to zero
    var = Field("test", 1, mesh, None)

    var.set_var_tensor(mesh.X**2)

    fdc = FDC({"div": {"limiter": "none"}})

    grad = fdc.grad(var)

    # Check interior
    target = (2 * mesh.X)[~mesh.t_mask]
    assert_close(grad[0][0][~mesh.t_mask], target)

    laplacian = fdc.laplacian(1.0, var)

    # Check interior
    target = (2 + (mesh.X) * 0.0)[~mesh.t_mask]
    assert_close(laplacian[0][~mesh.t_mask], target)

    # Test div(scalar, vector)

    # Scalar advection speed
    var_i = Field("test", 1, mesh, None)
    var_i.set_var_tensor(torch.rand(var_i().shape))
    var_j = Field("test", 1, mesh, None, init_val=2.0)

    div = fdc.div(var_j, var_i)
    dx = mesh.dx

    target = (
        (torch.roll(var_i()[0], -1, 0) - torch.roll(var_i()[0], 1, 0))
        / (2 * dx[0])
        * 2.0
    )

    assert_close(div[0][~mesh.t_mask], target[~mesh.t_mask])

    fdc.update_config("div", "limiter", "upwind")

    div = fdc.div(var_j, var_i)

    target = (var_i()[0] - torch.roll(var_i()[0], 1, 0)) / dx[0] * 2.0

    assert_close(div[0][~mesh.t_mask], target[~mesh.t_mask])


@pytest.mark.parametrize(
    ["domain", "spacing"],
    [
        [Box[0:1], [0.2]],
        [Box[0:1, 0:1], [0.2, 0.2]],
        [Box[0:1, 0:1, 0:1], [0.2, 0.2, 0.2]],
    ],
)
def test_solver_fdm_ops(domain: Box, spacing: list[float]) -> None:
    """Test FDM module."""

    mesh = Mesh(domain, None, spacing)

    # Field boundaries are all set to zero
    var_i = Field("test_Fi", 1, mesh, None)
    var_j = Field("test_Fj", 1, mesh, None, init_val=5.0)

    var_i.set_var_tensor(2 * mesh.X**2)

    solver = Solver(None)
    fdm = FDM({"div": {"limiter": "upwind"}})

    # Poisson equation.
    solver.set_eq(fdm.laplacian(2.0, var_i) == fdm.rhs(0.0))

    target = (
        (
            torch.roll(var_i()[0], -1, 0)
            - 2 * var_i()[0]
            + torch.roll(var_i()[0], 1, 0)
        )
        / (mesh.dx[0] ** 2)
        * 2.0
    )

    assert_close(solver.Aop(var_i)[0][~mesh.t_mask], target[~mesh.t_mask])
    assert_close(torch.zeros_like(solver.Aop(var_i)), solver.rhs)

    var_i.set_var_tensor(4 * mesh.X**2)

    # Test call by reference
    assert_close(solver.Aop(var_i)[0][~mesh.t_mask], target[~mesh.t_mask] * 2)

    solver.set_eq(fdm.div(var_j, var_i) + fdm.laplacian(3.0, var_i) == 2.0)

    t_div = (var_i()[0] - torch.roll(var_i()[0], 1, 0)) / mesh.dx[0] * 5.0

    t_laplacian = (
        (
            torch.roll(var_i()[0], -1, 0)
            - 2 * var_i()[0]
            + torch.roll(var_i()[0], 1, 0)
        )
        / (mesh.dx[0] ** 2)
        * 3.0
    )

    target = t_div[~mesh.t_mask] + t_laplacian[~mesh.t_mask]

    assert fdm.config["div"]["limiter"] == "upwind"
    assert_close(solver.Aop(var_i)[0][~mesh.t_mask], target)

    # Test 1D Advection Diffusion to see fdm.grad and fdm.div are interchangeable for this case.
    if mesh.dim == 1:

        solver.set_eq(fdm.grad(var_i) - fdm.laplacian(3.0, var_i) == 2.0)

        t_grad = (
            torch.roll(var_i()[0], -1, 0) - torch.roll(var_i()[0], 1, 0)
        ) / (2 * mesh.dx[0])

        t_laplacian = (
            (
                torch.roll(var_i()[0], -1, 0)
                - 2 * var_i()[0]
                + torch.roll(var_i()[0], 1, 0)
            )
            / (mesh.dx[0] ** 2)
            * 3.0
        )

        target = t_grad[~mesh.t_mask] - t_laplacian[~mesh.t_mask]
        assert_close(solver.Aop(var_i)[0][~mesh.t_mask], target)

    # Transient advection diffusion equation test
    dt = 0.01
    var_i.set_time(dt, 0.0)
    var_old = torch.rand_like(var_i())
    var_i.VARo = var_old
    rhs = torch.rand_like(var_i())

    solver.set_eq(
        fdm.ddt(var_i) + fdm.div(var_j, var_i) + fdm.laplacian(3.0, var_i)
        == rhs
    )
    t_div = (var_i()[0] - torch.roll(var_i()[0], 1, 0)) / mesh.dx[0] * 5.0

    t_laplacian = (
        (
            torch.roll(var_i()[0], -1, 0)
            - 2 * var_i()[0]
            + torch.roll(var_i()[0], 1, 0)
        )
        / (mesh.dx[0] ** 2)
        * 3.0
    )

    d_t_var = (var_i()[0] - var_old[0]) / dt

    target = d_t_var + (t_div + t_laplacian)
    t_rhs = rhs

    assert fdm.config["div"]["limiter"] == "upwind"
    assert_close(solver.Aop(var_i)[0][~mesh.t_mask], target[~mesh.t_mask])
    if solver.rhs is not None:
        assert_close(solver.rhs, t_rhs)


def test_fdm_ops_burger() -> None:
    mesh = Mesh(Box[0 : 2 * pi], None, [101])
    # Set dt to variable
    f_bc = homogeneous_bcs(1, None, "periodic")

    # Target variable
    init_val = burger_exact_nd(mesh, 0.1, 0.0)
    var = Field(
        "U", 1, mesh, {"domain": f_bc, "obstacle": None}, init_val=[init_val]
    )
    # dt is 0.1
    var.set_time(0.1, 0.0)

    solver = Solver(
        {
            "fdm": {
                "method": "bicgstab",
                "tol": 1e-5,
                "max_it": 1000,
                "report": True,
            }
        }
    )
    fdm = FDM({"div": {"limiter": "none"}})
    solver.set_eq(
        fdm.ddt(var) + fdm.div(var, var) - fdm.laplacian(0.1, var) == 0.0
    )
    div = solver.eqs[1]["Aop"](var, fdm.div.config, var)
    laplacian = solver.eqs[2]["Aop"](0.1, var)

    div_target = (
        (torch.roll(var()[0], -1, 0) - torch.roll(var()[0], 1, 0))
        / (2 * mesh.dx[0])
        * var()[0]
    )

    laplacian_target = (
        0.1
        * (
            torch.roll(var()[0], -1, 0)
            - 2 * var()[0]
            + torch.roll(var()[0], 1, 0)
        )
        / (mesh.dx[0] ** 2)
    )

    assert_close(div[0], div_target)
    assert_close(laplacian[0], laplacian_target)
