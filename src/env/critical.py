from logging import critical
from re import T
import numpy as np
from numpy.linalg import inv
from scipy import interpolate
from src.env.utils.physical_constant import MU
from warnings import warn

CRITERIA = 1e-6
MAX_COUNT = 1024


def find_critical(R : np.ndarray, Z : np.ndarray, psi : np.ndarray, discard_xpoints : bool = True):
    '''Find critical points of psi
    Argument 
    R : R(nr, nz) 2D array of major radii
    Z : Z(nr, nz) 2D array of heights
    psi : psi(nr,nz) 2D array of magnetic flux 

    Returns
    opoint : tuple type (R,Z,psi), primary 0-point (magnetic axis)
    xpoint : tuple type (R.Z,psi), primary x-point (separatrix)
    
    '''

    f = interpolate.RectBivariateSpline(R[:,0],Z[0,:], psi)

    Bp2 = (f(R,Z,dx = 1, grid = False)**2 + f(R,Z,dy = 1, grid = False) ** 2) / R ** 2

    dR = R[1,0] - R[0,0]
    dZ = Z[0,1] - Z[0,0]

    radius_sq = 9 * (dR ** 2 + dZ ** 2)

    # find local minimum
    J = np.zeros([2,2])

    xpoint = []
    opoint = []

    nx, ny = Bp2.shape

    for i in range(2,nx-2):
        for j in range(2,ny-2):
            if (
                (Bp2[i, j] < Bp2[i + 1, j + 1])
                and (Bp2[i, j] < Bp2[i + 1, j])
                and (Bp2[i, j] < Bp2[i + 1, j - 1])
                and (Bp2[i, j] < Bp2[i - 1, j + 1])
                and (Bp2[i, j] < Bp2[i - 1, j])
                and (Bp2[i, j] < Bp2[i - 1, j - 1])
                and (Bp2[i, j] < Bp2[i, j + 1])
                and (Bp2[i, j] < Bp2[i, j - 1])
            ):

                # Found local minimum
                R0 = R[i,j]
                Z0 = Z[i,j]

                R1 = R0
                Z1 = Z0

                count = 0

                while True:
                    Br = -f(R1,Z1, dy = 1, grid = False) / R1
                    Bz = f(R1,Z1, dx = 1, grid = False) / R1

                    if Br ** 2 + Bz ** 2 < CRITERIA:
                        d2dr2 = (psi[i+2, j] - 2.0 * psi[i,j] + psi[i-2, j]) / (2.0 * dR) ** 2
                        d2dz2 = (psi[i, j+2] - 2.0 * psi[i,j] + psi[i, j-2]) / (2.0 * dZ) ** 2

                        d2drdz = (
                            (psi[i+2,j+2] - psi[i+2,j-2]) / (4.0 * dZ) -
                            (psi[i-2,j+2] - psi[i-2,j-2]) / (4.0 * dZ)
                        ) / (4.0 * dR)
                        D = d2dr2 * d2dz2 - d2drdz ** 2

                        if D < 0:
                            # Found x-point
                            xpoint.append((R1,Z1,f(R1,Z1)[0][0]))
                        else:
                            opoint.append((R1,Z1,f(R1,Z1)[0][0]))

                        break

                    # J : Jacobian matrix
                    # J : [[dBr/dR, dBr/dZ],[dBz/dR, dBz/dZ]]
                    J[0,0] = -Br / R1 - f(R1,Z1,dy=1,dx=1)[0][0] / R1
                    J[0,1] = -f(R1,Z1,dy=2)[0][0] / R1
                    J[1,0] = -Bz / R1 + f(R1,Z1,dx = 2) / R1
                    J[1,1] = f(R1,Z1,dx = 1, dy = 1)[0][0] / R1

                    d = np.dot(inv(J), [Br,Bz])

                    R1 = R1 - d[0]
                    Z1 = Z1 - d[1]

                    count += 1

                    if((R1-R0) ** 2 + (Z1-Z0)**2 > radius_sq) or (count > MAX_COUNT)):
                        # discard this point
                        break

    
    # Remove duplicates
    def remove_dup(points):
        result = []
        for n,p in enumerate(points):
            dup = False
            for p2 in result:
                if(p[0] - p2[0]) ** 2 + (p[1] - p2[1]) ** 2 < CRITERIA * 1e1:
                    dup = True
                    break
                    
            if not dup:
                result.append(p)
        return result

    xpoint = remove_dup(xpoint)
    opoint = remove_dup(opoint)

    if len(opoint) == 0:
        print("Warning : no 0-point found")
        return opoint, xpoint

    # Find primary 0point by sorting by distance from middle of domain
    Rmid = 0.5 * (R[-1,0] - R[0,0])
    Zmid = 0.5 * (Z[0,-1] - Z[0,0])

    opoint.sort(key = lambda x : (x[0] - Rmid) ** 2 + (x[1] - Zmid) ** 2)

    if discard_xpoints:
        Ro,Zo,Po = opoint[0]

        xpt_keep = []

        for xpt in xpoint:
            Rx,Zx,Px = xpt

            rline = np.linspace(Ro,Rx,num=50)
            zline = np.linspace(Zo,Zx,num=50)

            pline = f(rline, zline, grid = False)

            if Px < Po:
                pline *= -1.0 # psi 값 가운데 o-point > x-point일 경우 reverse하여 x-point가 더 크도록 한다
            
            maxp = np.amax(pline)
            
            if (maxp - pline[-1]) / (maxp - pline[0]) > 0.001:
                # more than 0.1% drop in psi from maximum to x-point
                continue
        
            ind = np.argmin(pline) # should be at o-point

            if(rline[ind] - Ro) ** 2 + (zline[ind] - Zo) ** 2 > 1e-4:
                # too far, discard this point
                continue
        
            xpt_keep.append(xpt)
        xpoint = xpt_keep

    # Sort x-points by distance to primary o-point in psi space
    psi_axis = opoint[0][2]
    xpoint.sort(key = lambda x : (x[2] - psi_axis) ** 2)

    return opoint, xpoint


def core_mask(R,Z,psi,opoint, xpoint = [], psi_bndry = None):
    '''Mark the parts of the domain which are in the core
    Arguments:
    R[nx,ny] : 2D array of major radii
    Z[nx,ny] : 2D array of height
    psi[nx,ny] : 2D array of poloidal flux

    opoint, xpoint : values returned by find_critical

    Returns:
    2D array [nx,ny] which is 1 inside the core, 0 outside
    '''

    mask = np.zeros(psi.shape)
    nx, ny = psi.shape

    # Start and end points
    Ro, Zo, psi_axis = opoint[0]
    if psi_bndry is None:
        _, _, psi_bndry = xpoint[0]

    # Normalise psi
    psin = (psi - psi_axis) / (psi_bndry - psi_axis)

    # Need some care near X-points to avoid flood filling through saddle point
    # Here we first set the x-points regions to a value, to block the flood fill
    # then later return to handle these more difficult cases
    #
    xpt_inds = []
    for rx, zx, _ in xpoint:
        # Find nearest index
        ix = np.argmin(abs(R[:, 0] - rx))
        jx = np.argmin(abs(Z[0, :] - zx))
        xpt_inds.append((ix, jx))
        # Fill this point and all around with '2'
        for i in np.clip([ix - 1, ix, ix + 1], 0, nx - 1):
            for j in np.clip([jx - 1, jx, jx + 1], 0, ny - 1):
                mask[i, j] = 2

    # Find nearest index to start
    rind = np.argmin(abs(R[:, 0] - Ro))
    zind = np.argmin(abs(Z[0, :] - Zo))

    stack = [(rind, zind)]  # List of points to inspect in future

    while stack:  # Whilst there are any points left
        i, j = stack.pop()  # Remove from list

        # Check the point to the left (i,j-1)
        if (j > 0) and (psin[i, j - 1] < 1.0) and (mask[i, j - 1] < 0.5):
            stack.append((i, j - 1))

        # Scan along a row to the right
        while True:
            mask[i, j] = 1  # Mark as in the core

            if (i < nx - 1) and (psin[i + 1, j] < 1.0) and (mask[i + 1, j] < 0.5):
                stack.append((i + 1, j))
            if (i > 0) and (psin[i - 1, j] < 1.0) and (mask[i - 1, j] < 0.5):
                stack.append((i - 1, j))

            if j == ny - 1:  # End of the row
                break
            if (psin[i, j + 1] >= 1.0) or (mask[i, j + 1] > 0.5):
                break  # Finished this row
            j += 1  # Move to next point along

    # Now return to X-point locations
    for ix, jx in xpt_inds:
        for i in np.clip([ix - 1, ix, ix + 1], 0, nx - 1):
            for j in np.clip([jx - 1, jx, jx + 1], 0, ny - 1):
                if psin[i, j] < 1.0:
                    mask[i, j] = 1
                else:
                    mask[i, j] = 0

    return mask