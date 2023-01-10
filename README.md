
# THIS LIBRARY IS CURRENTLY BROKEN!! IT IS PRE-ALPHA STAGE

# pyapes

**PY**thon **A**wesome **P**artial differential **E**quation **S**olver (general purpose finite difference PDE solver)

![python](http://ForTheBadge.com/images/badges/made-with-python.svg)

## Description

`pyapes` is designed to solve various engineering problems in rectangular grid.

`pyapes` (should be/have) is/has

- Cross-platform
  - Both tested on Mac and Linux (Arch)
  - Windows support is under testing
- GPU acceleration in a structured grid with [PyTorch](https://pytorch.org)
  - Use of `torch.Tensor`. User can choose either `torch.device("cpu")` or `torch.device("cuda")`.
- Generically expressed (OpenFOAM-like, human-readable formulation)

  ```python3
  # Set discretizer and solver. *_config should be dictionary
  fdm = FDM(fdm_config)
  solver = Solver(solver_config)

  # Set Fields
  var_i = Field(...)
  var_j = Field(...)
  rhs = Field(...) # or torch.Tensor (shape should match with Field()) or float

  # Construct equation
  dt = 0.01
  var_i.set_dt(dt)
  solver.set_eq(
    fdm.ddt(var_i)
    + fdm.div(var_i, var_j) - fdm.laplacian(c, var_i), var_i)
    == fdm.rhs(var)
  )
  # solve the equation
  solver.solve()
  ```

## Installation

We recommend to use `poetry` to manage all dependencies.

```bash
git clone git@gitlab.ethz.ch:kchung/pyapes.git
cd pyapes
poetry install
```

> Later, `pip` install via pypi.org will be supported.

## Dependencies

- Core dependency
  - `python >= 3.10`
  - `numpy >= 1.21.0`
  - `torch >= 1.10.0`
  - `pyevtk >= 1.2.0`
  - `tensorboard >= 2.7.0`
- Misc dependency (Aesthetic)
  - `tqdm >= 4.62.3`
  - `rich >= 10.12.0`

## Features (Planning)

- GPU enabled computation (using `torch`)
- ~~Finite Volume Method~~ → FDM
  - ~~Support spatial discretization in `FVC` and `FVM` manner~~
    - `Grad`, `Laplacian`, `Div` (`FVM` only)
  - Implicit time integration in `Ddt`
    - The backward Euler and the Crank-Nicolson
  - Flux limiters for advection term: `QUICK` and `Upwind`
  - Immersed body boundary conditions
  - Linear system solvers
    - Supports one or all of Jacobi, Conjugated gradient (CG), CG-Newton, and Gauss-Seidel (need verification) method.
  - Distributed computing

## Examples

### The 1D Poisson equation

For the clarity, below code snippet is vastly simplified. See `./demos/poisson.py` file for more details

```python
# Only shows relevant modules
from pyapes.core.geometry import Box
from pyapes.core.mesh import Mesh
from pyapes.core.solver.fdm import FDM
from pyapes.core.solver.ops import Solver
from pyapes.core.variables import Field
...

# Construct mesh
mesh = Mesh(Box[0:1], None, [0.02])

# Construct scalar field to be solved
var = Field("p", 1, mesh, {"domain": f_bc, "obstacle": None})
# Set RHS of PDE
rhs = torch.Tensor(...)

# Set solver and FDM discretizer
solver = Solver({"fdm": {"method": "cg", "tol": 1e-6, "max_it": 1000, "report" True}})
fdm = FDM()

# ∇^2 p = r
solver.set_eq(fdm.laplacian(1.0, var) == fdm.rhs(rhs))
# Solve for var
report = solver.solve() # report contains information regarding solver convergence
```

Resulting in

![1d-poisson-result](./assets/demo_figs/poisson_1d.png)

## Todos

- Refactoring the code:
  - Better data structure
    - [x] Revised `FDM`
    - ~~Flux class~~
    - ~~`FVC` for explicit discretization~~
    - ~~`FVM` for implicit discretization~~
  - BCs
    - [x] Dirichlet
    - [ ] Neumann
    - [ ] Symmetry
    - [ ] Periodic
    - [ ] Inflow/Outflow
  - Discretizations
    - Spatial
      - [x] `Grad`
      - [x] `Laplacian`
      - [x] `Div`
    - Temporal
      - [x] `Ddt`
- Need different derivative order at the cell face
  - Additional features
    - [ ] High order time discretization
    - [ ] Immersed body BC
    - [x] Flux limiters
      - High-order flux limiter (`quick`) is WIP.
- Testing and validation
  - Create test files
    - [x] `test_mesh.py`
    - [x] `test_variables.py`
    - [x] `test_fdm.py`: Check all operators
    - [ ] `test_solver.py`: Check with practical examples
  - Test with examples
    - [x] The Poisson equation
    - [ ] The advection-diffusion equation
    - [ ] The Euler equation
    - [ ] The Navier-Stokes equation at low Reynolds numbers
    - [ ] The Black-Scholes equation
- Publish to pypi.org
