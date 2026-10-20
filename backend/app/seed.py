"""ILLUSTRATIVE seed network - NOT survey data.

Place coordinates are approximate and elevations are rough estimates so the prototype and tests have
a believable hilly graph. `in_caz` flags are placeholders: production derives them from
ST_Contains(official CAZ polygon, node) in PostGIS using the boundary published by Bristol City Council.
Replace this module with an OSM + terrain import (see db/schema.sql and docs/).
"""
from .engine import Graph, Node


def build_demo_graph() -> Graph:
    g = Graph()
    nodes = [
        # id, name, lat, lon, elev(m), in_caz
        ("M32J", "M32 / A4320 approach", 51.4660, -2.5700, 25, False),
        ("MARSH", "St Philip's Marsh depot (candidate hub)", 51.4470, -2.5740, 8, False),
        ("TMEADS", "Temple Meads area", 51.4496, -2.5813, 11, False),
        ("OLDMKT", "Old Market", 51.4565, -2.5800, 15, False),
        ("CENTRE", "Centre / Colston Ave", 51.4540, -2.5960, 10, True),
        ("QSQ", "Queen Square", 51.4510, -2.5920, 8, True),
        ("PARKST", "Park Street (lower)", 51.4530, -2.6010, 14, True),
        ("PARKTOP", "Park Street (top)", 51.4562, -2.6040, 55, True),
        ("WHITELADIES", "Whiteladies Rd", 51.4640, -2.6150, 62, False),
        ("CLIFTONV", "Clifton Village", 51.4545, -2.6208, 75, False),
        ("HOTWELLS", "Hotwells", 51.4500, -2.6170, 6, False),
        ("A38N", "A38 Stokes Croft", 51.4615, -2.5930, 30, False),
    ]
    for i, n, la, lo, el, caz in nodes:
        g.add_node(Node(i, n, la, lo, el, caz))
    E = g.add_edge
    E("M32J", "OLDMKT", congestion=1.8)          # M32 approach, peak congestion
    E("M32J", "A38N", congestion=1.6)
    E("A38N", "WHITELADIES", congestion=1.4)
    E("A38N", "CENTRE", congestion=1.5)
    E("OLDMKT", "CENTRE", congestion=1.3)
    E("OLDMKT", "TMEADS")
    E("MARSH", "TMEADS")
    E("TMEADS", "QSQ", congestion=1.2)
    E("QSQ", "CENTRE")
    E("CENTRE", "PARKST")
    E("PARKST", "PARKTOP", length_m=380)           # ~11% climb
    E("PARKTOP", "CLIFTONV")
    E("PARKTOP", "WHITELADIES")
    E("WHITELADIES", "CLIFTONV")
    E("QSQ", "HOTWELLS")
    E("HOTWELLS", "CLIFTONV", length_m=450)        # ~15% climb out of Hotwells (too steep for cargo bike)
    E("TMEADS", "HOTWELLS", road_type="bike_only") # illustrative harbourside bike link
    return g
