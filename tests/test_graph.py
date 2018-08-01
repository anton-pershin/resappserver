import unittest

from resappserver.graph import *

def plus_edge(data):
    data['a'] += 1

def nonzero_predicate(data):
    return True if data['a'] != 0 else False

class GraphGoodCheck(unittest.TestCase):
    def test_primitive_serial_graph(self):
        spp = SerialParallelizationPolicy()
        oosp = OnlyOneSelectionPolicy()
        init_state = State('init_state', parallelization_policy=ssp, parallel_branches_selection_policy=oosp)
        state_1 = State('state_1', parallelization_policy=ssp, parallel_branches_selection_policy=oosp)
        term_state = State('term_state', parallelization_policy=ssp, parallel_branches_selection_policy=oosp)
        init_state.connect_to(state_1, edge=Edge(nonzero_predicate, plus_edge))
        state_1.connect_to(term_state, edge=Edge(nonzero_predicate, plus_edge))

if __name__ == '__main__':
    unittest.main()
