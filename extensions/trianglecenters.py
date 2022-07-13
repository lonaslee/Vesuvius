def get_inputs() -> tuple:
    in1 = clean_inputs(input("A:\n"))
    in2 = clean_inputs(input("B:\n"))
    in3 = clean_inputs(input("C:\n"))
    if len(in1) != 2 or len(in2) != 2 or len(in3) != 2:
        raise IndexError("the inputs are not correctly formatted")
    a = {"x": float(in1[0]), "y": float(in1[1])}
    b = {"x": float(in2[0]), "y": float(in2[1])}
    c = {"x": float(in3[0]), "y": float(in3[1])}
    return a, b, c


def clean_inputs(inp: str) -> list:
    inp = inp.strip("()")
    inp = inp.replace(",", " ")
    while "  " in inp:
        inp = inp.replace("  ", " ")
    inp = inp.strip()
    return inp.split(" ")


def slope(x1, y1, x2, y2) -> float | str:
    if x2 - x1 == 0:
        return ""
    elif y2 - y1 == 0:
        return 0
    else:
        m_val = (y2 - y1) / (x2 - x1)
        return m_val


def solve(eq1, eq2) -> tuple:
    x1m, x2m = find_m(eq1, eq2)
    x1b, x2b = find_b(eq1, eq2)
    m, x_side = one_side_x(x1m, x2m)
    b = one_side_b(x1b, x2b, x_side)
    final_x = b / m
    final_y1 = plug_in(x1m, final_x, x1b)
    final_y2 = plug_in(x2m, final_x, x2b)
    return final_x, average(final_y1, final_y2)


def find_m(eq1: str, eq2: str) -> tuple:
    x1_m, x2_m = eq1[0: eq1.index("x")], eq2[0: eq2.index("x")]
    if x1_m == "-":
        x1_m = "-1.0"
    if x2_m == "-":
        x2_m = "-1.0"
    if x1_m == "":
        x1_m = "1.0"
    if x2_m == "":
        x2_m = "1.0"
    return float(x1_m), float(x2_m)


def find_b(eq1: str, eq2: str) -> tuple:
    x1_b, x2_b = eq1[eq1.index("x") + 1:], eq2[eq2.index("x") + 1:]
    if x1_b == "":
        x1_b = "0.0"
    if x2_b == "":
        x2_b = "0.0"
    return float(x1_b), float(x2_b)


def one_side_x(x1_m, x2_m) -> tuple:  # why
    if x1_m > 0 and x2_m > 0:  # pos pos
        if x1_m > x2_m:
            m = x1_m - x2_m
            m_side = "L"
        else:
            m = x2_m - x1_m
            m_side = "R"
    elif x1_m < 0:
        if x2_m > 0:           # neg pos
            m = x2_m + x1_m * -1
            m_side = "R"
        else:                  # neg neg
            if x1_m < x2_m:
                m = x1_m + x2_m * -1
                m_side = "L"
            else:
                m = x2_m + x1_m * -1
                m_side = "R"
    else:                      # pos neg
        m = x1_m + x2_m * -1
        m_side = "L"
    return m, m_side


def one_side_b(x1_b, x2_b, x_side) -> float:
    if x1_b > 0 and x2_b > 0:
        if x_side == "L":      # pos pos left
            b = x2_b - x1_b
        else:                  # pos pos right
            b = x1_b - x2_b
    elif x1_b < 0:
        if x2_b > 0:
            if x_side == "L":  # neg pos left
                b = x1_b * -1 + x2_b
            else:              # neg pos right
                b = x1_b - x2_b
        else:
            if x_side == "L":  # neg neg left
                b = x2_b + x1_b * -1
            else:              # neg neg right
                b = x1_b + x2_b * -1
    else:
        if x_side == "L":      # pos neg left
            b = x2_b - x1_b
        else:                  # pos neg right
            b = x1_b + x2_b * -1
    return b


def plug_in(m, x_value, b) -> float:
    return m * x_value + b


def average(*nums: float) -> float:
    sum_ = 0
    for one_num in nums:
        sum_ += one_num
    return sum_ / len(nums)


def clean(dusty: str) -> str:
    dusty = dusty.replace("--", "+")
    dusty = dusty.removesuffix("-0.0")
    dusty = dusty.removesuffix("+0.0")
    dusty = dusty.replace("x0.0", "x")
    dusty = dusty.replace("0.0x+", "")
    dusty = dusty.replace("0.0x-", "")
    return dusty


def decimate(num) -> float:
    return round(num, 2)


def coords(point="O", **kpoints) -> tuple:
    if point == "O":  # in hindsight I realize that half of this is unneccesary since
        h_line = (    # if a vertical or horizontal line exists we know the x or y value
            "A"
            if kpoints["eq1"]["pr"] == f'y={kpoints["a"]["y"]}'
            else "B"
            if kpoints["eq2"]["pr"] == f'y={kpoints["b"]["y"]}'
            else "C"
            if kpoints["eq3"]["pr"] == f'y={kpoints["c"]["y"]}'
            else None
        )
        v_line = (
            "A"
            if kpoints["eq1"]["pr"] == f'x={kpoints["a"]["x"]}'
            else "B"
            if kpoints["eq2"]["pr"] == f'x={kpoints["b"]["x"]}'
            else "C"
            if kpoints["eq3"]["pr"] == f'x={kpoints["c"]["x"]}'
            else None
        )
    else:
        h_line = (
            "A"
            if "x+" not in kpoints["eq1"]["pr"]
               and "x-" not in kpoints["eq1"]["pr"]
               and "y=" in kpoints["eq1"]["pr"]
            else "B"
            if "x+" not in kpoints["eq2"]["pr"]
               and "x-" not in kpoints["eq2"]["pr"]
               and "y=" in kpoints["eq2"]["pr"]
            else "C"
            if "x+" not in kpoints["eq3"]["pr"]
               and "x-" not in kpoints["eq3"]["pr"]
               and "y=" in kpoints["eq3"]["pr"]
            else None
        )
        v_line = (
            "A"
            if "x=" in kpoints["eq1"]["pr"]
            else "B"
            if "x=" in kpoints["eq2"]["pr"]
            else "C"
            if "x=" in kpoints["eq3"]["pr"]
            else None
        )
    if h_line is None:
        if v_line is None:  # straight to solve
            solve1 = solve(kpoints["eq1"]["eq"], kpoints["eq2"]["eq"])
            solve2 = solve(kpoints["eq2"]["eq"], kpoints["eq3"]["eq"])
            solve3 = solve(kpoints["eq3"]["eq"], kpoints["eq1"]["eq"])
            return (
                average(solve1[0], solve2[0], solve3[0]),
                average(solve1[1], solve2[1], solve3[1]),
            )
        elif v_line == "A":  # solve with B and C
            return solve(kpoints["eq2"]["eq"], kpoints["eq3"]["eq"])
        elif v_line == "B":  # sw A C
            return solve(kpoints["eq1"]["eq"], kpoints["eq3"]["eq"])
        else:  # 'C' sw A B
            return solve(kpoints["eq1"]["eq"], kpoints["eq2"]["eq"])
    elif h_line == "A":
        if v_line is None:
            return solve(kpoints["eq2"]["eq"], kpoints["eq3"]["eq"])
        elif v_line == "B":  # y of A, x of B
            return (
                (kpoints["b"]["x"]), (kpoints["a"]["y"])
                if point == "O"
                else (float(kpoints["eq2"]["eq"])), (float(kpoints["eq1"]["eq"]))
            )
        else:  # 'C'
            return (
                ((kpoints["c"]["x"]), (kpoints["a"]["y"]))
                if point == "O"
                else (float(kpoints["eq3"]["eq"])), (float(kpoints["eq1"]["eq"]))
            )
    elif h_line == "B":
        if v_line is None:
            return solve(kpoints["eq1"]["eq"], kpoints["eq3"]["eq"])
        elif v_line == "A":  # y of b
            return (
                (kpoints["a"]["x"]), (kpoints["b"]["y"])
                if point == "O"
                else (float(kpoints["eq1"]["eq"])), (float(kpoints["eq2"]["eq"]))
            )
        else:  # 'C'
            return (
                (kpoints["c"]["x"]), (kpoints["b"]["y"])
                if point == "O"
                else (float(kpoints["eq3"]["eq"])), (float(kpoints["eq2"]["eq"]))
            )
    else:  # 'C'
        if v_line is None:
            return solve(kpoints["eq1"]["eq"], kpoints["eq2"]["eq"])
        elif v_line == "A":  # y of c
            return (
                (kpoints["a"]["x"]), (kpoints["c"]["y"])
                if point == "O"
                else (float(kpoints["eq1"]["eq"])), (float(kpoints["eq3"]["eq"]))
            )
        else:  # 'B'
            return (
                (kpoints["b"]["x"]), (kpoints["c"]["y"])
                if point == "O"
                else (float(kpoints["eq2"]["eq"])), (float(kpoints["eq3"]["eq"]))
            )


def slope_equation(m, x1, y1, per=False) -> dict:
    if m == "":
        if per is False:
            for_print, for_eq = f"y={y1}", f"{y1}"
        else:
            for_print, for_eq = f"x={x1}", f"{x1}"
    elif m == 0:
        if per is False:
            for_print, for_eq = f"x={x1}", f"{x1}"
        else:
            for_print, for_eq = f"y={y1}", f"{y1}"
    else:
        if per is False:
            m = (m * -1) ** -1  # perpendicular
        if m * x1 * -1 + y1 < 0:
            for_print = f"y={decimate(m)}x{decimate(m * x1 * -1 + y1)}"
            for_eq = f"{m}x{m * x1 * -1 + y1}"
        else:
            for_print = f"y={decimate(m)}x+{decimate(m * x1 * -1 + y1)}"
            for_eq = f"{m}x+{m * x1 * -1 + y1}"
    for_print, for_eq = clean(for_print), clean(for_eq)
    return {"pr": for_print, "eq": for_eq}


def orthocenter(a, b, c) -> dict:
    alt_a = slope_equation(sl1 := slope(b["x"], b["y"], c["x"], c["y"]), a["x"], a["y"])
    alt_b = slope_equation(sl2 := slope(a["x"], a["y"], c["x"], c["y"]), b["x"], b["y"])
    alt_c = slope_equation(sl3 := slope(a["x"], a["y"], b["x"], b["y"]), c["x"], c["y"])
    ortho = coords(eq1=alt_a, eq2=alt_b, eq3=alt_c, a=a, b=b, c=c)
    ortho = decimate(ortho[0]), decimate(ortho[1])
    return {
        "words": f'Altitude A: {alt_a["pr"]}\nAltitude B: {alt_b["pr"]}\n'
                 f'Altitude C: {alt_c["pr"]}\nOrthocenter: {ortho}\n\n',
        "nowords": f'{alt_a["pr"]}\n{alt_b["pr"]}\n{alt_c["pr"]}\n{ortho}\n',
        "args": (sl1, sl2, sl3, ortho),
    }


def circumcenter(a, b, c) -> dict:
    per_a = slope_equation(
        sl1 := slope(b["x"], b["y"], c["x"], c["y"]),
        average(b["x"], c["x"]),
        average(b["y"], c["y"]),
    )
    per_b = slope_equation(
        sl2 := slope(a["x"], a["y"], c["x"], c["y"]),
        average(a["x"], c["x"]),
        average(a["y"], c["y"]),
    )
    per_c = slope_equation(
        sl3 := slope(a["x"], a["y"], b["x"], b["y"]),
        average(a["x"], b["x"]),
        average(a["y"], b["y"]),
    )
    circum = coords("C", eq1=per_a, eq2=per_b, eq3=per_c, a=a, b=b, c=c)
    circum = decimate(circum[0]), decimate(circum[1])
    return {
        "words": f'Perpendicular Bisector of AB: {per_c["pr"]}\n'
                 f'Perpendicular Bisector of AC: {per_b["pr"]}\n'
                 f'Perpendicular Bisector of BC: {per_a["pr"]}\n'
                 f"Circumcenter: {circum}\n\n",
        "nowords": f'{per_c["pr"]}\n{per_b["pr"]}\n{per_a["pr"]}\n{circum}\n',
        "args": (sl1, sl2, sl3, circum),
    }


def centroid(a, b, c) -> dict:
    med_a = slope_equation(
        sl1 := slope((b["x"] + c["x"]) / 2, (b["y"] + c["y"]) / 2, a["x"], a["y"]),
        a["x"],
        a["y"],
        True,
    )
    med_b = slope_equation(
        sl2 := slope((a["x"] + c["x"]) / 2, (a["y"] + c["y"]) / 2, b["x"], b["y"]),
        b["x"],
        b["y"],
        True,
    )
    med_c = slope_equation(
        sl3 := slope((a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2, c["x"], c["y"]),
        c["x"],
        c["y"],
        True,
    )
    centro = (average(a["x"], b["x"], c["x"]), average(a["y"], b["y"], c["y"]))
    centro = decimate(centro[0]), decimate(centro[1])
    return {
        "words": f'Median A: {med_a["pr"]}\nMedian B: {med_b["pr"]}\n'
                 f'Median C: {med_c["pr"]}\nCentroid: {centro}',
        "nowords": f'{med_a["pr"]}\n{med_b["pr"]}\n{med_c["pr"]}\n{centro}',
        "args": (sl1, sl2, sl3, centro),
    }


Slope = float | str
PointDict = dict[str, int]
MatPlotArg = tuple[Slope, Slope, Slope, tuple[float, float]]


def main(a: PointDict, b: PointDict, c: PointDict) -> tuple[str, str, list[MatPlotArg]]:
    # a, b, c = get_inputs()   <- original trianglecenters was a cmd application,
    #                             get inputs invokes input() which we don't want
    ab_slope = slope_equation(slope(a["x"], a["y"], b["x"], b["y"]), a["x"], a["y"], True)["pr"]
    ac_slope = slope_equation(slope(a["x"], a["y"], c["x"], c["y"]), a["x"], a["y"], True)["pr"]
    bc_slope = slope_equation(slope(b["x"], b["y"], c["x"], c["y"]), b["x"], b["y"], True)["pr"]
    final_string = (
        f'A({a["x"]}, {a["y"]}) B({b["x"]}, {b["y"]}) C({c["x"]}, {c["y"]})\n'
        f"Slope of AB: {ab_slope}\nSlope of AC: {ac_slope}\n"
        f"Slope of BC: {bc_slope}\n\n"
    )
    final_string_nowords = (
        f'\n\n{a["x"], a["y"]}\n{b["x"], b["y"]}\n{c["x"], c["y"]}\n'
        f"{ab_slope}\n{ac_slope}\n{bc_slope}\n"
    )
    matplotargs = []
    for cent in (orthocenter, circumcenter, centroid):
        returned = cent(a, b, c)
        matplotargs.append(returned["args"])
        final_string += returned["words"]
        final_string_nowords += returned["nowords"]
    return final_string, final_string_nowords, matplotargs
