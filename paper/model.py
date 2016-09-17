import numpy
import matplotlib.pyplot as plt
import matplotlib.colors as colors

def population(x, y):
    ''' this function gives the population of the region.
        it will be normalized later
    '''
    return 50 / ((x-0.5) ** 2 + (y - 0.5)** 2 + 0.00001) # plus this small number just to prevent it to explode

def elevation(x, y):
    ''' this function gives the population of the region.
        it will be normalized later
    '''

    return 1 / ((x-0.3) ** 1.5 + (y - 0.3)** 1.5 + 0.000001) # plus this small number just to prevent it to explode
#return numpy.exp(-((x - 0.5)** 2 + (y - 0.5) ** 2))

def populate_points(density_map, num_points, d):
    ''' this function will gives an array of test points based on normalized density map
        d is the smallest distance. 
        notice the values of the points are offsets. hence you need to add them to your base coordinates
    '''
    Y_RANGE = len(density_map)
    X_RANGE = len(density_map[0])
    points = []
    for j in range(Y_RANGE):
        for i in range(X_RANGE):
            num = numpy.random.poisson(density_map[j][i] * num_points)
            #num = int(density_map[j][i] * num_points)
            for k in range(num):
                x = numpy.random.uniform(i * d, (i + 1) * d)
                y = numpy.random.uniform(j * d, (j + 1) * d)
                points.append((x, y))
    return points


def main():
    d = 0.05
    RANGE = int(1 / d)
    G = (20, 20)
    pop = numpy.array([[population(i * d, j * d) for i in range(RANGE)] for j in range(RANGE)])
    geo = numpy.array([[elevation(i * d, j * d) for i in range(RANGE)] for j in range(RANGE)])

    geo_gradient_x, geo_gradient_y = numpy.gradient(geo)

    geo_effect = abs(geo_gradient_x * G[0]) + abs(geo_gradient_y * G[1])

    total_effect = pop - geo_effect

    # counter balance the negative ones
    total_effect[numpy.where(total_effect <= 0)] = 0.000000001
    # normalize the effect
    p_iot = total_effect / total_effect.sum()
    pop_norm = pop / pop.sum()
    geo_effect_norm = geo_effect / geo_effect.sum()
    #geo_effect_norm[numpy.where(geo_effect_norm <= 0)] = 0.000000001

    TOTAL = 2500
    points = populate_points(p_iot, TOTAL, d)

    # plot the result
    side = numpy.linspace(0,1, RANGE)
    X,Y = numpy.meshgrid(side,side)


    fig = plt.figure(figsize=(17,3.5))

    plt.subplot(1, 4, 1)
    ax = plt.pcolor(X,Y, pop_norm, norm=colors.Normalize(vmin=0,vmax=0.01), cmap = 'gray')
    plt.title("Density map for $\\rho$")
    #plt.colorbar()
    #plt.savefig("test.png")

    plt.subplot(1, 4, 2)
    plt.pcolor(X,Y, geo_effect_norm,norm=colors.Normalize(vmin=0,vmax=0.01), cmap = 'gray')
    plt.title("Impact from elevation")
    #plt.colorbar()

    plt.subplot(1, 4, 3)
    plt.pcolor(X,Y, p_iot, norm=colors.Normalize(vmin=0,vmax=0.01), cmap = 'gray')
    #plt.colorbar()
    plt.title("Density map for $P_{IoT}$")

    plt.subplot(1, 4, 4)
    points_x = [p[0] for p in points]
    points_y = [p[1] for p in points]
    plt.scatter(points_x, points_y, s=1, c='b')
    plt.xlim((0, 1))
    plt.ylim((0, 1)) 
    plt.title("{0} IoT test points".format(TOTAL))

    cbaxes = fig.add_axes([0.09, 0.1, 0.01, 0.8])
    cb = plt.colorbar(ax, cax = cbaxes)
    cb.ax.yaxis.set_ticks_position('left')
    
    
    plt.savefig("example.eps") 
    plt.show()
if __name__ == "__main__":
    main()
