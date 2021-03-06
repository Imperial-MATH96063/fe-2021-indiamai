# Cause division to always mean floating point division.
from __future__ import division
import numpy as np
from .reference_elements import ReferenceInterval, ReferenceTriangle
import itertools
np.seterr(invalid='ignore', divide='ignore')


def lagrange_points(cell, degree):
    """Construct the locations of the equispaced Lagrange nodes on cell.

    :param cell: the :class:`~.reference_elements.ReferenceCell`
    :param degree: the degree of polynomials for which to construct nodes.

    :returns: a rank 2 :class:`~numpy.array` whose rows are the
        coordinates of the nodes.

    The implementation of this function is left as an :ref:`exercise
    <ex-lagrange-points>`.

    """
    dim = cell.dim
    if dim == 1:
        return np.array([[0],[1]] + [[i/degree] for i in range(1,degree)])
    
    # Generates in order of entity
    interior = [x for x in range(1, degree)]
    zeros = [0 for x in range(1, degree)]
    vertices = [(0,0), (degree,0), (0,degree)]

    edges = list(zip(list(reversed(interior))+ zeros + interior , interior + interior + zeros )) 
    faces = [(i,j) for i in interior for j in interior if i+j < degree]
    indices = np.array(vertices + edges + faces)
    return indices / degree

def vandermonde_matrix(cell, degree, points, grad=False):
    """Construct the generalised Vandermonde matrix for polynomials of the
    specified degree on the cell provided.

    :param cell: the :class:`~.reference_elements.ReferenceCell`
    :param degree: the degree of polynomials for which to construct the matrix.
    :param points: a list of coordinate tuples corresponding to the points.
    :param grad: whether to evaluate the Vandermonde matrix or its gradient.

    :returns: the generalised :ref:`Vandermonde matrix <sec-vandermonde>`

    The implementation of this function is left as an :ref:`exercise
    <ex-vandermonde>`.
    """
    
    dim = cell.dim
    assert dim <= 2
    inner_range = lambda k : zip(range(k,-1,-1),range(k+1))

    if not grad:
        if dim == 1:
            a = lambda x : [x**i for i in range(degree + 1)]
            return np.array([a(x) for (x,) in points])

        a = lambda x,y : np.concatenate([[x**i*y**j for i,j in inner_range(k)] for k in range(degree+1)])
        return np.array([a(x,y) for (x,y) in points])
    else:
        if dim == 1:
            grad_x = lambda x : np.array([(i*x**(i-1),) if i != 0 else (0,) for i in range(degree + 1)])
            return np.array([grad_x(x) for (x,) in points])

        grad_x = lambda x,y : np.concatenate([[i*x**(i-1)*y**j if i != 0 else 0  for i,j in inner_range(k)] for k in range(degree+1)])
        grad_y = lambda x,y : np.concatenate([[(x**i)*j*y**(j-1) if j != 0 else 0 for i,j in inner_range(k)] for k in range(degree+1)])
        
        return np.array([np.array([grad_x(x,y),grad_y(x,y)]).T for (x,y) in points])



class FiniteElement(object):
    def __init__(self, cell, degree, nodes, entity_nodes=None):
        """A finite element defined over cell.

        :param cell: the :class:`~.reference_elements.ReferenceCell`
            over which the element is defined.
        :param degree: the
            polynomial degree of the element. We assume the element
            spans the complete polynomial space.
        :param nodes: a list of coordinate tuples corresponding to
            the nodes of the element.
        :param entity_nodes: a dictionary of dictionaries such that
            entity_nodes[d][i] is the list of nodes associated with entity `(d, i)`.

        Most of the implementation of this class is left as exercises.
        """

        #: The :class:`~.reference_elements.ReferenceCell`
        #: over which the element is defined.
        self.cell = cell
        #: The polynomial degree of the element. We assume the element
        #: spans the complete polynomial space.
        self.degree = degree
        #: The list of coordinate tuples corresponding to the nodes of
        #: the element.
        self.nodes = nodes
        #: A dictionary of dictionaries such that ``entity_nodes[d][i]``
        #: is the list of nodes associated with entity `(d, i)`.
        self.entity_nodes = entity_nodes

        if entity_nodes:
            #: ``nodes_per_entity[d]`` is the number of entities
            #: associated with an entity of dimension d.
            self.nodes_per_entity = np.array([len(entity_nodes[d][0])
                                              for d in range(cell.dim+1)])

        # Replace this exception with some code which sets
        # self.basis_coefs
        # to an array of polynomial coefficients defining the basis functions.
        self.basis_coefs = np.linalg.inv(vandermonde_matrix(cell, degree, nodes))

        #: The number of nodes in this element.
        self.node_count = nodes.shape[0]

    def tabulate(self, points, grad=False):
        """Evaluate the basis functions of this finite element at the points
        provided.

        :param points: a list of coordinate tuples at which to
            tabulate the basis.
        :param grad: whether to return the tabulation of the basis or the
            tabulation of the gradient of the basis.

        :result: an array containing the value of each basis function
            at each point. If `grad` is `True`, the gradient vector of
            each basis vector at each point is returned as a rank 3
            array. The shape of the array is (points, nodes) if
            ``grad`` is ``False`` and (points, nodes, dim) if ``grad``
            is ``True``.

        The implementation of this method is left as an :ref:`exercise
        <ex-tabulate>`.

        """
        if grad:
            grad_vander = vandermonde_matrix(self.cell, self.degree, points, grad)
            return np.einsum("ijk,jl->ilk", grad_vander, self.basis_coefs)
            
        return np.matmul(vandermonde_matrix(self.cell, self.degree, points), self.basis_coefs)

    def interpolate(self, fn):
        """Interpolate fn onto this finite element by evaluating it
        at each of the nodes.

        :param fn: A function ``fn(X)`` which takes a coordinate
           vector and returns a scalar value.

        :returns: A vector containing the value of ``fn`` at each node
           of this element.

        The implementation of this method is left as an :ref:`exercise
        <ex-interpolate>`.

        """
        
        return [fn(node) for node in self.nodes]

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               self.cell,
                               self.degree)

def compute_entity_nodes(lagrange_points, cell, degree):
    # Lagrange points are in entity order so just need to allocate correct numbers
    dim = cell.dim
    entity_nodes = {}
    # All indices that need to be allocated
    indices = [x for x in range(len(lagrange_points))]

    entity_nodes[0] = {i: [i] for i in range(dim+1)}
    indices = indices[dim+1:]

    if dim > 1:
        entity_nodes[1] = {}
        for i in range(dim+1):
            entity_nodes[1][i] = indices[:(degree-1)]
            indices = indices[degree-1:]

    entity_nodes[dim] = {0 : indices}
    return entity_nodes
        


class LagrangeElement(FiniteElement):
    def __init__(self, cell, degree):
        """An equispaced Lagrange finite element.

        :param cell: the :class:`~.reference_elements.ReferenceCell`
            over which the element is defined.
        :param degree: the
            polynomial degree of the element. We assume the element
            spans the complete polynomial space.

        The implementation of this class is left as an :ref:`exercise
        <ex-lagrange-element>`.
        """

        nodes = lagrange_points(cell, degree)
        # Use lagrange_points to obtain the set of nodes.  Once you
        # have obtained nodes, the following line will call the
        # __init__ method on the FiniteElement class to set up the
        # basis coefficients.
        entity_nodes = compute_entity_nodes(nodes, cell, degree)
        super(LagrangeElement, self).__init__(cell, degree, nodes, entity_nodes)

def compute_vector_entity_nodes(lagrange_points, cell, degree):
    # Lagrange points are in entity order so just need to allocate correct number pairs
    dim = cell.dim
    # if vector dimension is 1, entity nodes list is normal
    if dim == 1:
        return compute_entity_nodes(lagrange_points, cell, degree)

    # If not, we need to allocate new numbering in a similar way
    entity_nodes = {}
    indices = [x for x in range(dim*len(lagrange_points))]
    entity_nodes[0] = {i: [dim*i, dim*i + 1] for i in range(dim+1)}
    indices = indices[dim*(dim+1):]

    if dim > 1:
        entity_nodes[1] = {}
        for i in range(dim+1):
            entity_nodes[1][i] = indices[:dim*(degree-1)]
            indices = indices[dim*(degree-1):]

    entity_nodes[dim] = {0 : indices}
    return entity_nodes

class VectorFiniteElement(FiniteElement):
    def __init__(self, finite_element):
        self.finite_element = finite_element

        cell = finite_element.cell
        degree = finite_element.degree
        d = cell.dim
        nodes = finite_element.nodes
        entity_nodes = compute_vector_entity_nodes(nodes, cell, degree)
        
        super(VectorFiniteElement, self).__init__(cell, degree, nodes, entity_nodes)

        # Add node weights containing the required basis functions
        self.node_weights = np.array([[[1,0],[0,1]] for i in range(len(nodes))]).reshape((len(nodes)*d, d))
        # Redefine self.nodes to be the correct length
        self.nodes = np.array([[node for i in range(d)] for node in nodes]).reshape((len(nodes)*d, d))
        

        

    def tabulate(self, points, grad=False):
        # Create the Vector Element tabulation based off the underlying element
        tab = self.finite_element.tabulate(points, grad)
        d = self.cell.dim
        n = tab.shape[1]

        if grad:
            new_tab = np.zeros((tab.shape[0],  d, n*d, tab.shape[2]))
        else:
            new_tab = np.zeros((tab.shape[0],  d, n*d))

        # This performs the equivalent of multiplication by e_i by inserting elements in the correct place
        for i in range(d):
            elems = [2*j + i for j in range(n)]
            new_tab[:,i, elems] = tab
        return new_tab

    def interpolate(self, fn):
        """Interpolate fn onto this finite element by evaluating it
        at each of the nodes and multiplying by the correct basis function

        :param fn: A function ``fn(X)`` which takes a coordinate
           vector and returns a scalar value.

        :returns: A vector containing the value of ``fn`` at each node
           of this element.

        """
        return [self.node_weights[i] @ fn(self.nodes[i]) for i in range(len(self.nodes))]