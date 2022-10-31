#!/usr/bin/env python3
"""Discretization of explicit field.
Results of discretization always returns torch.Tensor.
"""
from typing import Union

import torch
from torch import Tensor

from pyapes.core.geometry.basis import DIR
from pyapes.core.variables import Field
from pyapes.core.variables import Flux


class FVC:
    """Collection of the operators for explicit finite volume discretizations."""

    @staticmethod
    def tensor(val: Tensor) -> Tensor:
        """Simply assign a given tensor and return. Mostly used for the RHS in `FVM`."""

        return val

    @staticmethod
    def source(val: Union[float, Tensor], var: Field) -> Tensor:

        source = Flux(var.mesh)

        for i in range(var.dim):
            for j in range(var.mesh.dim):
                source.to_center(
                    i,
                    DIR[j],
                    val
                    if isinstance(val, Tensor)
                    else val * torch.ones_like(var()),
                )
        return source.tensor()

    # WIP: Need implementation soon
    @staticmethod
    def div(var_i: Field, var_j: Field) -> Tensor:
        pass

    @staticmethod
    def grad(var: Field) -> Tensor:
        r"""Explicit discretization: Gradient

        Args:
            var: Field object to be discretized ($\Phi$).

        Returns:
            dict[int, dict[str, Tensor]]: resulting `torch.Tensor`. `int` represents variable dimension, and `str` indicates `Mesh` dimension.

        """
        grad = Flux(var.mesh)

        for i in range(var.dim):
            for j in range(var.mesh.dim):

                grad.to_face(
                    i,
                    DIR[j],
                    "l",
                    (var()[i] + torch.roll(var()[i], 1, j)) / 2,
                )
                grad.to_face(
                    i,
                    DIR[j],
                    "r",
                    (var()[i] + torch.roll(var()[i], -1, j)) / 2,
                )

        for bc in var.bcs:
            bc.apply(var(), grad, var.mesh.grid, 0)

        grad.sum()

        return grad.tensor()

    @staticmethod
    def laplacian(gamma: float, var: Field) -> Tensor:
        r"""Explicit discretization: Laplacian

        Args:
            var: Field object to be discretized ($\Phi$).

        Returns:
            dict[int, dict[str, Tensor]]: resulting `torch.Tensor`. `int` represents variable dimension, and `str` indicates `Mesh` dimension.

        """

        laplacian = Flux(var.mesh)

        dx = var.dx

        for i in range(var.dim):
            for j in range(var.mesh.dim):

                laplacian.to_face(
                    i,
                    DIR[j],
                    "l",
                    (var()[i] - torch.roll(var()[i], 1, j)) / dx[j],
                )
                laplacian.to_face(
                    i,
                    DIR[j],
                    "r",
                    (torch.roll(var()[i], -1, j) - var()[i]) / dx[j],
                )

        for bc in var.bcs:
            bc.apply(var(), laplacian, var.mesh.grid, 1)

        laplacian.sum_all()
        laplacian *= gamma

        return laplacian.tensor()
