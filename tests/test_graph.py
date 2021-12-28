import unittest

from resappserver.graph import *

def dummy_edge(data):
    pass

def increment_a_edge(data):
    data['a'] += 1

def increment_b_edge(data):
    data['b'] += 1

def decrement_a_edge(data):
    data['a'] -= 1

def dummy_predicate(data):
    return True

def nonzero_predicate(data):
    return True if data['a'] != 0 else False

def positiveness_predicate(data):
    return True if data['a'] > 0 else False

def nonpositiveness_predicate(data):
    return True if data['a'] <= 0 else False

def print_exception(exc_data, data):
    print('exception data: {}'.format(exc_data))
    print('current state of data: {}'.format(data))

class GraphGoodCheck(unittest.TestCase):
    initial_conditions = range(-10, 10)

    def test_trivial_serial_graph(self):
        initial_state, term_state, correct_outputs = self._get_trivial_serial_graph([{'a': ic} for ic in self.initial_conditions])
        self._run_graph(initial_state, ('a',), (-1, 0), correct_outputs)

    def test_trivial_parallel_graph(self):
        initial_state, term_state, correct_outputs = self._get_trivial_parallel_graph([{'a': ic, 'b': ic} for ic in self.initial_conditions])
        self._run_graph(initial_state, ('a', 'b'), (-1, 0), correct_outputs)

    def test_trivial_cycled_graph(self):
        initial_state, term_state, correct_outputs = self._get_trivial_cycled_graph([{'a': ic} for ic in self.initial_conditions])
        self._run_graph(initial_state, ('a',), (), correct_outputs)

    def test_complex_graph_made_from_trivial_ones(self):
        '''
        serial graph + parallel graph + cycled graph
        '''
        s_1, s_2, correct_outputs = self._get_trivial_serial_graph([{'a': ic, 'b': ic} for ic in self.initial_conditions])
        s_3, s_4, correct_outputs = self._get_trivial_parallel_graph(correct_outputs)
        s_5, s_6, correct_outputs = self._get_trivial_cycled_graph(correct_outputs)
        s_2.connect_to(s_3, edge=Edge(dummy_predicate, dummy_edge))
        s_4.connect_to(s_5, edge=Edge(dummy_predicate, dummy_edge))
        self._run_graph(s_1, ('a', 'b'), (-3, -2, -1, 0), correct_outputs)

    def _get_trivial_serial_graph(self, initial_conditions):
        '''
        s_1 -> s_2 -> s_3,
        p_12 = p_23 := a not 0
        f_12 = f_23 := a + 1
        '''

        spp = SerialParallelizationPolicy()
        oosp = OnlyOneSelectionPolicy()
        s_1 = State('serial_s_1', parallelization_policy=spp,
                           parallel_branches_selection_policy=oosp)
        s_2 = State('serial_s_2', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_3 = State('serial_s_3', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_1.connect_to(s_2, edge=Edge(nonzero_predicate, increment_a_edge))
        s_2.connect_to(s_3, edge=Edge(nonzero_predicate, increment_a_edge))
        #correct_outputs = [{'a': ic + 2} for ic in initial_conditions]
        correct_outputs = []
        for ic in initial_conditions:
            ic['a'] += 2
            correct_outputs.append(ic)
        return s_1, s_3, correct_outputs

    def _get_trivial_parallel_graph(self, initial_conditions):
        '''
        s_1 -> s_2 -> s_4
            -> s_3 ->
        p_12 = p_24 = p_13 = p_34 := a not 0
        f_12 = f_24 := a + 1
        f_13 = f_34 := b + 1
        '''

        spp = SerialParallelizationPolicy()
        oosp = OnlyOneSelectionPolicy()
        asp = AllSelectionPolicy()
        s_1 = State('parallel_s_1', parallelization_policy=spp,
                           parallel_branches_selection_policy=asp)
        s_2 = State('parallel_s_2', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_3 = State('parallel_s_3', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_4 = State('parallel_s_4', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_1.connect_to(s_2, edge=Edge(nonzero_predicate, increment_a_edge))
        s_2.connect_to(s_4, edge=Edge(nonzero_predicate, increment_a_edge))
        s_1.connect_to(s_3, edge=Edge(nonzero_predicate, increment_b_edge))
        s_3.connect_to(s_4, edge=Edge(nonzero_predicate, increment_b_edge))
        #correct_outputs = [{'a': ic + 2, 'b': ic + 2} for ic in self.initial_conditions]
        correct_outputs = []
        for ic in initial_conditions:
            ic['a'] += 2
            ic['b'] += 2
            correct_outputs.append(ic)
        return s_1, s_4, correct_outputs

    def _get_trivial_cycled_graph(self, initial_conditions):
        '''
        s_1 -> s_2 -> s_3
            <-
        p_12 := True
        p_23 := a > 0
        p_23 := a <= 0
        f_12 = f_23 = f_24 := a + 1
        '''

        spp = SerialParallelizationPolicy()
        oosp = OnlyOneSelectionPolicy()
        s_1 = State('cycled_s_1', parallelization_policy=spp,
                           parallel_branches_selection_policy=oosp)
        s_2 = State('cycled_s_2', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_3 = State('cycled_s_3', parallelization_policy=spp, 
                           parallel_branches_selection_policy=oosp)
        s_1.connect_to(s_2, edge=Edge(dummy_predicate, increment_a_edge))
        s_2.connect_to(s_3, edge=Edge(positiveness_predicate, increment_a_edge))
        s_2.connect_to(s_1, edge=Edge(nonpositiveness_predicate, increment_a_edge))
#        correct_outputs = [{'a': ic + 2} if ic >=0 else {'a': ic%2 + 2} for ic in self.initial_conditions]
        correct_outputs = []
        for ic in initial_conditions:
            if ic['a'] >= 0:
                ic['a'] += 2
            else:
                ic['a'] = ic['a']%2 + 2
            correct_outputs.append(ic)
        return s_1, s_3, correct_outputs

    def _run_graph(self, initial_state, vars_to_initialize, invalid_ics, correct_outputs):
        graph = Graph(initial_state)
        for ic, correct_output in zip(self.initial_conditions, correct_outputs):
            print('Doing ic = {}...'.format(ic))
            gotten_output, okay = graph.run({var: ic for var in vars_to_initialize})
            if ic in invalid_ics:
                print(gotten_output['__EXCEPTION__'])
                self.assertEqual('__EXCEPTION__' in gotten_output, True)
                self.assertEqual(okay, False)
            else:
                self.assertEqual(okay, True)
                self.assertEqual(gotten_output, correct_output)

if __name__ == '__main__':
    unittest.main()
