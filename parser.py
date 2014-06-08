import re

def input_parser(user_input):
    m = re.match(r"(.+)/([lcr*()0-9]*)(f[0-9]*)?", user_input)

    if m and (m.group(2) or m.group(3)):
        regex = m.group(1)
        flag = m.group(2)
        maxs = m.group(3)
    else:
        # print("No options!")
        return [user_input, [['l', 1]], 0]

    try:
        # for flag
        rParan = re.compile(r"\(([^())]*)\)\*([0-9]+)")
        while True:
            if not rParan.search(flag): break
            for r in rParan.finditer(flag):
                flag = flag.replace(r.group(0), r.group(1)*int(r.group(2)),1)

        for r in re.finditer(r"([lcr][0-9]*)\*([0-9]+)", flag):
            flag = flag.replace(r.group(0), r.group(1)*int(r.group(2)),1)

        flag = re.findall(r"[lcr][0-9]*", flag)
        flag = list(map(lambda x: [x[0], 1] if len(x)==1 \
                                    else [x[0], int(x[1:])], flag))
        flag = flag if flag else [['l', 1]]

        # for maxs
        maxs = 0 if not maxs else 1 if len(maxs)==1 else int(maxs[1:])
    except:
        [regex, flag ,maxs]= [user_input, [['l', 1]], 0]

    return [regex, flag, maxs]