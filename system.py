# -*- coding: utf-8 -*-
"""
Created on Sat Nov 19 15:54:06 2016

@author: Alexander Kuhn-Regnier

Solving Laplace's equation in order to calculate the electric potential for a
variety of different source conditions. The field can then be calculated
from this potential.

Elliptic Equation
Solved by iterative successive over-relaxation method (SOR)
Dirichlet boundary conditions
Equation solved in 2D - grid spacing h

Pictorial operator arises from 2nd order central finite difference
(divided by h^2). Applied to every gridpoint, calculates next iteration
using the value at the current gridpoint as well as the four closest
gridpoints around it (includes boundary conditions if needed).
Can be combined into a matrix so that the entire system can be solved
using the relaxation method.

"""
from __future__ import print_function
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from numba import jit
# np.set_printoptions(threshold=np.inf)

class Shape:
    def __init__(self,Ns,potential,origin,*args,**kwargs):
        '''
        'Ns' is the number of gridpoints along an axis, so the
        grid spacing h is the inverse of this, since the axes range from 0 to 1
        '''
        assert type(Ns)==int, 'Ns should be an integer'
        self.Ns = Ns
        self.h = 1./Ns
        self.potential = potential
        self.grid = np.mgrid[0:1:complex(0, self.Ns), 0:1:complex(0, self.Ns)]
        self.potentials = np.zeros(self.grid.shape[1:])
        self.sources = np.zeros(self.potentials.shape,dtype=np.bool)
        self.source_potentials = np.zeros(self.sources.shape)
        self.add_source(origin,*args,**kwargs)
    def find_closest_gridpoint(self,coords):
        '''
        Find closest point on grid to coords
        '''
        coords = np.array(coords).reshape(-1,)
        # make sure coords have correct shape for next step
        # really necessary (could have assert)?
        coords = coords[(slice(None),)+(None,)*coords.shape[0]]
        # reshape to (2,1,1) or (3,1,1,1) etc. for correct
        # broadcasting
        abs_diff = np.abs(self.grid - coords)
        diff_list = []
        for i in range(self.grid.shape[0]):
            '''
            find row number of minimum (absolute) differences in
            grid[0] which stores the x coordinates, and find the
            min column for grid[1], which stores the y coords
            '''
            diff = np.where(abs_diff[i]==np.min(abs_diff[i]))
            diff_list.append(np.vstack(diff))
        diffs = np.hstack(diff_list).T
        # .T so the rows can be iterrated over in order to find the
        # duplicated indices - which will then reveal where the overlap is
        diff_tuples = map(tuple,diffs)
        counts = Counter(diff_tuples).most_common()
        match = counts[0][0]
        # desired coordinates (grid coordinates)
        return match
    def add_source(self,origin,*args,**kwargs):
        '''
        *args: coord1[,coord2]
        **kwargs: 'shape':'circle' or 'rectangle'

        In 2D, a regular shape can be specified by 3 parameters, the centre
        (origin) of the shape, and two additional coordinates (could be more
        if irregular shapes would be implemented).
        The centre of the shapes described below is specified by the
        'origin' argument, with the top left corner of the simulated space
        defined as (0,0), and the bottom left corner as (1,1).
        (Note: These positions only pertain to the position in say, a matrix,
        where the x and y positions increase from the top left to the
        bottom right - this is also apparent in visualisation generated using
        imshow, for example.)
        If only origin is given (ie. no non-keyword args), then a point source
        at the grid point closest to the origin is created.
        implemented here:
            'rectangle':origin is the centre of the rectangle
                        coord1 is width
                        coord2 is height
                (square as special case (coord1 = coord2),
                 would be orientated with edges vertical & horizontal)
            'circle':   origin is the centre of the circle
                        coord1 is the radius
        '''
        if not args: #if only origin is specified
            source_coords = self.find_closest_gridpoint(origin)
            self.potentials[source_coords] = self.potential
            self.sources[source_coords] = True
            self.source_potentials[source_coords] = self.potential
            # terminate function here, since the necessary action has been
            # performed.
            return None
        # shape selection
        if 'shape' in kwargs:
            # shape specified explicitly
            shape = kwargs['shape']
        else:
            shape = 'rectangle'
        # select whether the shape should be filled or not
        if 'filled' in kwargs:
            filled = kwargs['filled']
        else:
            filled = True

        not_implemented_message = (
"""{:} args not implemented for shape: {:}
No shape has been added, please refer to function
documentation""".format(len(args),shape))

        if shape == 'rectangle':
            if len(args) == 2:
                print ("Adding rectangle centred at {:} with "
                       "width: {:}, height: {:}".format(origin,args[0],args[1]))
                width = args[0]
                height = args[1]
                vertices = []
                min_x = origin[0]-width/2.
                max_x = origin[0]+width/2.
                min_y = origin[1]-height/2.
                max_y = origin[1]+height/2.
                for x,y in zip((min_x,min_x,max_x,max_x,min_x),
                                (min_y,max_y,max_y,min_y,min_y)):
                    vertices.append((x,y))
                for vertex1,vertex2 in zip(vertices[:-1],vertices[1:]):
                    x1 = vertex1[0]
                    x2 = vertex2[0]
                    y1 = vertex1[1]
                    y2 = vertex2[1]
                    if x1==x2:
                        for y in np.arange(min((y1,y2)),max((y1,y2)),self.h):
                            self.add_source((x1,y))
                    elif y1==y2:
                        for x in np.arange(min((x1,x2)),max((x1,x2)),self.h):
                            self.add_source((x,y1))
                    else:
                        print("vertices do not lie along straight lines!")
                if filled:
                    self.fill()
            else:
                print(not_implemented_message)
        if shape == 'circle':
            if len(args) == 1:
                print("Adding circle centred at {:} with radius {:}".format(
                origin,args[0]))
                # interval of angles calculated so that every grid point
                # should be covered ~1-2 times for a given radius, to make
                # sure that every grid point is covered
                r = args[0]
                d_theta = self.h/(2*r)
                for theta in np.arange(0,2*np.pi,d_theta):
                    self.add_source((origin[0]+r*np.sin(theta),
                                     origin[1]+r*np.cos(theta)))
                if filled:
                    self.fill()
            else:
                print(not_implemented_message)
    def fill(self):
        '''
        fill shape row-wise, assigning the same potential throughout
        if 2 or more (should just be 2 maximum) grid points are marked
        as being a source, mark the grid points in between these as
        sources too, with the same potential
        '''
        for i,row in enumerate(self.sources):
            indices = np.where(row==True)[0]
            if indices.shape[0]>1:
                min_index = indices[0]
                max_index = indices[-1]
                for index in range(min_index+1,max_index):
                    self.potentials[i,index] = self.potential
                    self.sources[i,index] = True
                    self.source_potentials[i,index] = self.potential

class System:
    def __init__(self,Ns):
        '''
        'Ns' is the number of gridpoints along an axis, so the
        grid spacing h is the inverse of this, since the axes range from 0 to 1
        '''
        assert type(Ns)==int, 'Ns should be an integer'
        self.Ns = Ns
        self.h = 1./Ns
        self.grid = np.mgrid[0:1:complex(0, self.Ns), 0:1:complex(0, self.Ns)]
        self.potentials = np.zeros(self.grid.shape[1:])
        self.sources = np.zeros(self.potentials.shape,dtype=np.bool)
        self.source_potentials = np.zeros(self.sources.shape)
    def add(self,shape_instance):
        '''
        Add sources to the system using instances of the 'Shape' class.
        Note: Potentials of overlapping shapes are added. Once a grid point
            has been assigned to a source, its potential will remain fixed
            throughout.
        '''
        assert shape_instance.Ns == self.Ns, 'Grids should be the same'
        self.potentials += shape_instance.potentials
        self.sources += shape_instance.sources
        self.source_potentials += shape_instance.source_potentials
    def show_setup(self):
        '''
        Show the sources in the system
        '''
        plt.figure()
        plt.title('Sources')
        plt.imshow(self.source_potentials)
        plt.colorbar()
        plt.tight_layout()
        plt.show()
    def show(self,title=''):
        '''
        Show the calculated potential
        '''
        plt.figure()
        plt.title('Potential')
        plt.imshow(self.potentials)
        plt.colorbar()
        plt.tight_layout()
        if title:
            plt.title(title)
        plt.show()
    def create_method_matrix(self):
        N = self.Ns**2
        self.A = np.zeros((N, N))
        boundary_conditions = []
        for i in range(N):
            boundaries_row = []
            coord1 = int(float(i)/self.Ns)
            coord2 = i%self.Ns
            self.A[i,i] = -4
            for c1,c2 in zip([coord1,coord1,coord1-1,coord1+1],
                             [coord2-1,coord2+1,coord2,coord2]):
                try:
                    if c1==-1 or c2==-1 or c1>self.Ns-1 or c2>self.Ns-1:
                        raise IndexError
                    elif c1 == coord1-1:
                        '''
                        row has changed, need to move 'cell'
                        column cannot have changed, so move
                        by Ns along row
                        '''
                        self.A[i,i-self.Ns] = 1
                    elif c1 == coord1+1:
                        self.A[i,i+self.Ns] = 1
                    elif c2 == coord2-1:
                        self.A[i,i-1]=1
                    elif c2 == coord2+1:
                        self.A[i,i+1]=1
                    else:
                        print("error",c1,c2)
                except IndexError:
                    boundaries_row.append((c1,c2))
            boundary_conditions.append(boundaries_row)
        self.boundary_conditions = boundary_conditions
    def jacobi(self, tol=1e-3, max_iter=5000, verbose=True):
        N = self.Ns**2
        self.create_method_matrix()
        b = np.zeros(N)
        #get diagonal, D
        D = np.diag(np.diag(self.A)) #but these are all just -4
        L = np.tril(self.A,k=-1)
        U = np.triu(self.A,k=1)
        x = self.potentials.reshape(-1,)
        orig_x = x.copy()
        sources = self.sources.reshape(-1,)
        #randomise starting potential
        x = np.random.random(x.shape)
        x[sources] = orig_x[sources]    
        #randomise starting potential
        D_inv = np.linalg.inv(D)
        L_U = L+U
        T = - np.dot(D_inv, L_U)
        D_inv_b = np.dot(D_inv, b).reshape(-1,)
        print("Jacobi: finished creating matrices")
        for i in range(max_iter):
            initial_norm = np.linalg.norm(x)
            x = np.dot(T,x).reshape(-1,) + D_inv_b
            x[sources] = orig_x[sources]
            final_norm = np.linalg.norm(x)
            diff = np.abs(initial_norm-final_norm)
            if verbose:
                print("i,diff:",i,diff)
            if diff < tol:
                break
        self.potentials = x.reshape(self.Ns,-1)
    def gauss_seidel(self, tol=1e-3, max_iter=5000, verbose=True):
        N = self.Ns**2
        #create array (matrix) A
        self.create_method_matrix()
        b = np.zeros(N)

        #get diagonal, D
        D = np.diag(np.diag(self.A)) #but these are all just -4
        L = np.tril(self.A,k=-1)
        U = np.triu(self.A,k=1)
        L_D_inv = np.linalg.inv(L+D)
        L_D_inv_b = np.dot(L_D_inv,b)
        T = -np.dot(L_D_inv,U)
        print("Gauss Seidel: finished creating matrices")
        x = self.potentials.reshape(-1,)
        orig_x = x.copy()
        sources = self.sources.reshape(-1,)
        #randomise starting potential
        x = np.random.random(x.shape)
        x[sources] = orig_x[sources]    
        #randomise starting potential

        for i in range(max_iter):
            #print "before\n",x.reshape(self.Ns,-1)
            initial_norm = np.linalg.norm(x)
            x = np.dot(T,x).reshape(-1,) + L_D_inv_b
            x[sources] = orig_x[sources]
            #print "sources",x[sources]
            final_norm = np.linalg.norm(x)
            diff = np.abs(initial_norm-final_norm)
            #print "after\n",x.reshape(self.Ns,-1)
            if verbose:
                print("i,diff:",i,diff)
            if diff < tol:
                break
            #print ''
        self.potentials = x.reshape(self.Ns, -1)
    def SOR(self, w=1.5, tol=1e-3, max_iter=5000, verbose=True):
        '''
        A = L + D + U
        A x = b - b are the boundary conditions

        x is arranged like:
            u_1,1
            u_1,2
            u_2,1
            u_2,2

        D is of length N^2, every element is -4, N is the number of gridpoints
        '''
        N = self.Ns**2
        w = float(w)
        # create array (matrix) A
        self.create_method_matrix()
        b = np.zeros(N) #boundary conditions around edges
        # get diagonal, D
        D = np.diagonal(self.A) #but these are all just -4
        L = np.tril(self.A,k=-1)
        U = np.triu(self.A,k=1)
        x = self.potentials.reshape(-1,)
        orig_x = x.copy()
        sources = self.sources.reshape(-1,)
        '''
        better choice than random initial state needs to be found!
        could use pre-conditioning with coarse grid, which is initialised
        with
        '''
        #randomise starting potential
        x = np.random.random(x.shape)
        x[sources] = orig_x[sources]    
        #randomise starting potential
        '''
        for i in range(max_iter):
            initial_norm = np.linalg.norm(x)
            for k in range(N):
                if sources[k]:
                    continue
                s1 = 0
                s2 = 0
                for j in range(0,k):
                    s1 += L[k,j]*x[j]
                for j in range(k+1,N):
                    s2 += U[k,j]*x[j]
                x[k] = (1-w)*x[k] + (w/D[k]) * (b[k] -s1 -s2)
            final_norm = np.linalg.norm(x)
            diff = np.abs(initial_norm-final_norm)
            if verbose:
                print("i,diff:",i,diff)
            if diff < tol:
                break
        '''
        x = self.SOR_sub_func(max_iter,x,N,sources,L,U,w,D,b,tol,verbose)
        self.potentials = x.reshape(self.Ns,-1)
        
    @staticmethod 
    @jit(nopython=True)
    def SOR_sub_func(max_iter,x,N,sources,L,U,w,D,b,tol,verbose):
        for i in range(max_iter):
            initial_norm = np.linalg.norm(x)
            for k in range(N):
                if sources[k]:
                    continue
                s1 = 0
                s2 = 0
                for j in range(0,k):
                    s1 += L[k,j]*x[j]
                for j in range(k+1,N):
                    s2 += U[k,j]*x[j]
                x[k] = (1-w)*x[k] + (w/D[k]) * (b[k] -s1 -s2)
            final_norm = np.linalg.norm(x)
            diff = np.abs(initial_norm-final_norm)
            if verbose:
                print("i,diff:",i,diff)
            if diff < tol:
                break  
        return x

if __name__ == '__main__':        
    Ns = 60
    test = System(Ns)
    # test.add(Shape(30,1,(0.01,0.01)))
    # test.add(Shape(30,1.2,(0.9,0.9)))
    test.add(Shape(Ns,-1.3,(0.5,0.5),0.18,shape='circle',filled=False))
    test.add(Shape(Ns,1.8,(0.5,0.5),0.1,shape='circle',filled=False))
    test.add(Shape(Ns,1,(0.5,0.5),0.3,shape='circle',filled=False))
    # print test.potentials
    
    #plt.close('all')
    
    calc = 1
    tol = 1e-14
    max_iter = 4000
    show = True
    methods = [test.SOR,test.jacobi,test.gauss_seidel]
    #methods = [test.SOR]
    names = [f.__name__ for f in methods]
    if calc:
        for name,f in zip(names,methods):
            print(name)
            f(tol=tol,max_iter=max_iter)
            if show:
                test.show(title=name)