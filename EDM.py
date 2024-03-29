# -*- coding: utf-8 -*-
"""
Created on Wed Dec 07 14:20:14 2016

@author: Alexander Kuhn-Regnier
"""
from __future__ import print_function
from system import Shape,System
import numpy as np
import matplotlib.pyplot as plt
from time import clock
import os

def create_EDM_system(Ns,kx,ky=None,size=None,dust_pos=None,
                      dust_size=1e-4,small_sources=True):
    '''
    Create the shapes needed to model the EDM experiment and then add
    these shapes to a system, both with the given grid size.
    kx and ky describe the space left between the end of the experimental
    setup and the boundary, which will be held at 0V.
    This distance is described as a multiple of the length of the 
    experimental setup in that axis.
    '''
    if size == None:
        size = (1.,1.) 
    if not hasattr(size,'__iter__'):
        size = (size,size) 
        
    if ky == None:
        ky = kx
    if not hasattr(Ns,'__iter__'):
        Ns = (Ns,Ns)
        
    A = Ns[1]/float(Ns[0])
    hx = 1./(26*(2*kx+1))
    hy = A/(3*(2*ky+1))
    Sx = kx * 26*hx
    Sy = ky * 3*hy
    shapes = []
    
    print('hy',hy)
    print('hx',hx)
    print('size',size)
    print('A',A)
    shapes.append(Shape(Ns,1.,  (Sx+13.*hx,Sy+5.*hy/2.),20*hx,hy,
                        shape='rectangle', filled=True))
    
    shapes.append(Shape(Ns,-1.,  (Sx+13.*hx,Sy+hy/2.),20*hx,hy,
                        shape='rectangle', filled=True))

    if small_sources:    
        shapes.append(Shape(Ns,0.25,(Sx+hx,    Sy+5.*hy/2.),2*hx,hy,
                            shape='rectangle', filled=True))
        shapes.append(Shape(Ns,0.25,(Sx+25.*hx,Sy+5.*hy/2.),2*hx,hy,
                            shape='rectangle', filled=True))
        
        shapes.append(Shape(Ns,-0.25,(Sx+hx,    Sy+hy/2.),2*hx,hy,
                            shape='rectangle', filled=True))
        shapes.append(Shape(Ns,-0.25,(Sx+25.*hx,Sy+hy/2.),2*hx,hy,
                            shape='rectangle', filled=True))
    
    system = System(Ns,size=size)
    for shape in shapes:
        system.add(shape)
        
    if dust_pos:
        if not hasattr(dust_size,'__iter__'):
            dust_size = (dust_size,dust_size)  
        #scale dust size by x-length, since the scaled length
        #in x is always 1, not so for y
        dust_size = (dust_size[0]/size[0],dust_size[1]/size[0])
        #same as system.Nsx, inverse of number of grid points
        #along an axis
        grid_spacing = 1./Ns[0]
        #using the grid spacing, determine the number of 
        #grid points covered by the dust particle
        nr_of_points_x = int(dust_size[0]/grid_spacing)
        nr_of_points_y = int(dust_size[1]/grid_spacing)        
        
        #determine where the dust particle will sit along the 
        #x axis based on the scaled position (assumed to be along x)
        #and the size of the dust particle
        lowest_x_grid = int((dust_pos/size[0] - dust_size[0]/2.)*Ns[0])    
        highest_x_grid = lowest_x_grid+nr_of_points_x

        #lowest 'real' coordinate in scaled coordinates of the
        #top sources, which all lie along one horizontal line
        y_source = Sy+2.*hy
        #translate this to an index on the grid
        y_source_grid = int(y_source/grid_spacing)
        
        #lowest position on grid of top source should be given by
        #*y_source_grid* above. If not, then no potential will be
        #assigned there, so we should start assigning at this point
        #as opposed to the point below
        if np.any(system.sources[:,y_source_grid]):
            #source already assigned, so the empty space must
            #start at the grid point below this
            top_dust_grid = y_source_grid-1
        else:
            top_dust_grid = y_source_grid
                
        #grab source potential from above grid point, which makes
        #the method more general, if a 'small' potential were
        #to be investigated, for example. This would have a 
        #potential of +0.25, not +1.
        #We are only interested in placing the dust particle
        #on the top sources, since the setup is symmetric
        assert system.sources[lowest_x_grid,top_dust_grid+1],(
               'Dust particle should be in contact with source!')
        potential = system.source_potentials[lowest_x_grid,
                                             top_dust_grid+1]
        for x_grid in np.arange(lowest_x_grid,highest_x_grid):
            for j in range(nr_of_points_y):
                y_grid = top_dust_grid-j
                index = (x_grid,y_grid)
#                print('index:',index)
                system.source_potentials[index] = potential
                system.potentials[index] = potential
                system.sources[index] = True
        return system,(nr_of_points_x*grid_spacing*size[0],
                       nr_of_points_y*grid_spacing*size[0])
    return system,()
    
if __name__ == '__main__':
    factor = 301
    k = 0.9
    test,dust_size = create_EDM_system((26*factor,3*factor),k,
                             size=(260*(1+2*k),30*(1+2*k)),
                             small_sources=False,dust_pos=350.,
                             dust_size=4)
#    test.show_setup()
    print('Dust Size:',dust_size)
#    test.SOR_single(w=1.5,tol=1e-10,max_time=60)
#    test.show(quiver=False)