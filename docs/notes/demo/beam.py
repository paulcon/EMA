"""The demo's model with no spec yet (docs/notes/demo_mcp.md, prompt 11): a cantilever beam's tip deflection.

A cantilever of length L, fixed at one end and loaded with P at the other, of elastic modulus E and a rectangular
cross-section b × h, deflects at its tip by P·L³ / (3·E·I), with I = b·h³ / 12. The section is fixed here: b = 50 mm,
h = 100 mm. At P = 1000 N, L = 2 m, and E = 200 GPa, the deflection is 3.2 mm.
"""

B_M = 0.05  # the section's width, m
H_M = 0.10  # the section's height, m
I_M4 = B_M * H_M**3 / 12.0  # the section's second moment of area, m^4


def f(P, L, E):
    """Return the tip deflection in mm, for the load P in N, the length L in m, and the elastic modulus E in GPa."""
    return 1000.0 * P * L**3 / (3.0 * E * 1e9 * I_M4)
