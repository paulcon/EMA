# Designs

**Status:** empty. **Updated:** <YYYY-MM-DD>. **Depends on:** OD-13, OD-14.

> The design generators in v2.0, from `../notes/v1/ema-redesign.md`. For each: what the user provides, the
> points it makes, how it uses the seed, its size in closed form, and whether a smaller design is a subset
> of a larger one (which is what lets stored runs be reused).

## Shared rules

- **Seeds:** <each generator takes a seed; uniform designs with the same seed share their first points>.
- **Log-scale parameters:** <points are spread evenly in the logarithm>.
- **Size:** <every generator computes its size before building, and refuses more than <N> points>.
- **Units:** <points are in parameter units; `Box.to_unit` maps them to [-1, 1]>.

## Generators

| Generator | User provides | Points | Size | Nested? | Seeded? |
|---|---|---|---|---|---|
| point | a point (nominal), repeats | the point, repeated | repeats + 1 | | no |
| uniform | box, n | n uniform random points | n | yes: the first n of one stream | yes |
| convergent | box, n_min, alpha, level | nested uniform designs of n_min·alphaᵏ points | <…> | yes | yes |
| line | box, anchor, direction, n | n evenly spaced points on the line, inside the box | n | <…> | no |
| coordinate lines | box, n, anchor | one line per parameter through the anchor | d·n | <…> | no |
| random lines | box, m, n | m lines through random anchors in random directions | m·n | <…> | yes |
| plane | TODO | | | | |

## Requirements

| Id | Requirement | Test |
|---|---|---|
| G1 | The same request gives the same points, bit for bit. | <…> |
| G2 | Every point is inside the box. | <…> |
| G3 | The size computed before building equals the number of points built. | <…> |
| G4 | Where nesting is claimed, the smaller design's points are the first points of the larger. | <…> |
| G… | <…> | <…> |

## Open questions

- OD-13: own stream or `scipy.stats.qmc`?
- OD-14: quadrature and sparse grids?
