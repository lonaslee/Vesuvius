def get_inputs() -> tuple[dict[float, float], dict, dict]: ...
def clean_inputs(inp: str) -> list[str, str]: ...
def slope(x1, y1, x2, y2) -> float | str: ...
def solve(eq1, eq2) -> tuple[float, float]: ...
def find_m(eq1: str, eq2: str) -> tuple[float, float]: ...
def find_b(eq1: str, eq2: str) -> tuple[float, float]: ...
def one_side_x(x1_m, x2_m) -> tuple[float, str]: ...
def one_side_b(x1_b, x2_b, x_side) -> float: ...
def plug_in(m, x_value, b) -> float: ...
def average(*nums: float) -> float: ...
def clean(dusty: str) -> str: ...
def decimate(num) -> float: ...
def coords(point="O", **kpoints) -> tuple: ...
def slope_equation(m, x1, y1, per=False) -> dict: ...
def orthocenter(a, b, c) -> dict: ...
def circumcenter(a, b, c) -> dict: ...
def centroid(a, b, c) -> dict: ...
def main(a, b, c) -> tuple[str, str, list]: ...
  