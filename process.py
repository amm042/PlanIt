import math


def calculate_ber(entry):
    T1 = 24
    GT = 3
    T = T1 + GT
    NJ = -84 - 30
    G = 3
    NF = 7
    fb = 1200
    B = 12500
    rho = 9600


    if "ITWOM Version 3.0 ph loss" in entry:
        loss = float(entry["ITWOM Version 3.0 ph loss"].split()[0])
    elif "Free space ph loss" in entry:
        loss = float(entry["Free space ph loss"].split()[0])
    else:
        return (-100, 1)
    SNR = T - NJ - loss + G - NF
    EbN0 = SNR - 10 * math.log(fb / B, 10) 
    EbN0 = 10 ** (EbN0 / 10)
    P = 0.5 * math.exp(-EbN0 / 2)

    return (SNR, P)
