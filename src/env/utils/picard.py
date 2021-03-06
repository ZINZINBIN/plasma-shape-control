import numpy as np
import math
from typing import Optional
from src.env.utils.physical_constant import EPS

def SORper1Epoch(A, x, b, w = 1.0, eps = EPS):
    '''
    - solve linear algebra with SOR algorithm per 1 epoch
    - method : SOR(Successive Over Relaxation)
    - A : numpy.ndarray, (m,n), Grad-Shafranov Operator
    - x : numpy.ndarray or numpy.array, (n,) or (n,1), psi
    - b : numpy.ndarray or numpy.array, (m,) or (m,1), Poloidal Current
    - w : Relaxation Factor, w > 1
    '''
    A_diag = A.diagonal()
    D = np.diag(A_diag)
    P = A - D
    
    # SOR alogorithm per 1 epoch
    x_new = np.zeros_like(x)

    for idx in range(0, A.shape[1]):
        sig = P[idx,0:idx]@x_new[0:idx] + P[idx,idx+1:]@x[idx+1:]
        x_new[idx] = (1-w) * x[idx] + w * (b[idx] - sig) / (A_diag[idx] + eps) 

    return x_new

def calculate_spectral_radius(A : np.ndarray):
    try:
        eigens = np.linalg.eigvals(A)
        rho = np.max(np.abs(eigens))
        return rho
    except:
        rho = -1
        return rho

def calculate_optimal_w(rho : float):
    '''calculate the optimal relaxation factor that makes GS equation converged
    rho : spectral radius, maximum value of eigen-vector
    '''
    if np.abs(rho) > 1:
        w = 1
    else:
        w = 1 + (rho / (1 + np.sqrt(1 - rho ** 2))) ** 2

    return w

def SORsolver(A : np.ndarray,b : np.array, w :Optional[float] = 1.0, eps : float = EPS, iters : int = 64, conv : float = EPS, is_print : bool = False):
    '''
    - solve linear algebra with SOR algorithm
    - method : SOR(Successive Over Relaxation)
    - A : numpy.ndarray, (m,n), Grad-Shafranov Operator
    - x : numpy.ndarray or numpy.array, (n,) or (n,1), psi
    - b : numpy.ndarray or numpy.array, (m,) or (m,1), Poloidal Current
    - w : Relaxation Factor, w > 1
    - eps : epsilon value for preventing non zero division
    - iters : iterations for SOR iterative method
    - conv : convergence criteria
    '''
    x = np.zeros_like(b)
    loss = 0
    loss_list = []
    is_converge = 0

    rho = calculate_spectral_radius(A)

    if rho != -1 and w is None:
        w = calculate_optimal_w(rho)
 
    for iter in range(iters):
        x_new = SORper1Epoch(A,x,b,w,eps)
        loss = np.sqrt(np.linalg.norm(A@x_new - b) / (A.shape[0] * A.shape[1]))

        loss_list.append(loss)

        if math.isnan(loss) or math.isinf(loss):
            is_converge = -1
            break

        if loss < conv:
            is_converge = 1
            break

        x = x_new

    if is_converge == 1 and is_print:
        print("steps : {} / {}, loss : {:.3f}, converged".format(iter+1, iters, loss))
    elif is_converge == 0 and is_print:
        print("steps : {} / {}, loss : {:.3f}, not converged".format(iter+1, iters, loss))
    elif is_converge == -1 and is_print:
        print("steps : {} / {}, loss : {:.3f}, diverged".format(iter+1, iters, loss))

    return x_new, loss_list
