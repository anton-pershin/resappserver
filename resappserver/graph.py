import collections

class Graph:
    def __init__(self, init_state):
        self._init_state = init_state

    def run(self, data):
        cur_state = self._init_state
        while cur_state is not None:
            morph = cur_state.run(data)
            cur_state = morph(data)

class State:
    __slots__ = [
        'name',
        'input_edges_number', 
        'activated_input_edges_number',
        'is_looped',
        'output_edges', 
        'parallelization_policy',
        'parallel_branches_selection_policy',
        ]
    def __init__(self, name, **kwargs):
        self.name = name
        self.input_edges_number = 0
        self.activated_input_edges_number = 0
        self.is_looped = False
        self.output_edges = []
        self.parallelization_policy = None
        if 'parallelization_policy' in kwargs:
            self.parallelization_policy = kwargs['parallelization_policy']
        self.parallel_branches_selection_policy = None
        if 'parallel_branches_selection_policy' in kwargs:
            self.parallel_branches_selection_policy = kwargs['parallel_branches_selection_policy']

    def idle_run(self, initialize_state=False):
        if initialize_state:
            if self.input_edges_number != 0:
                if not self.is_looped:
                    self.is_looped = True
                else:
                    raise BadGraphStructure('Multiple loops in a single state are not allowed')
            self.input_edges_number += 1
        else:
            self.activated_input_edges_number += 1
        for edge in edges:
            edge.identity().idle_run(initialize_state)

    def connect_to(self, term_state, edge):
        edge.set_output_state(term_state)
        self.output_edges.append(edge)

    def run(self, data):
        self.activated_input_edges_number += 1
        if self._ready_to_morph():
            predicate_values = []
            for edge in self.output_edges:
                predicate_values.append(edge.predicate(data))
            selected_edge_indices = self.parallel_branches_selection_policy.select(predicate_values)
            if not selected_edge_indices:
                raise GraphUnexpectedTermination(
                    'State {}: Predicate values {} do not conform selection policy'.format(self.name, predicate_values))
            selected_edges = [self.output_edges[i] for i in selected_edge_indices]
            return self.parallelization_policy.make_morphism(edges)
        else:
            return None

    def _ready_to_morph(self):
        required_activated_input_edges_number = self.input_edges_number
        if self.is_looped:
            required_activated_input_edges_number -= 1
        return self.activated_input_edges_number == self.required_activated_input_edges_number

class Edge:
    __slots__ = [
        '_predicate', 
        '_morphism', 
        '_output_state', 
        ]
    def __init__(self, predicate, morphism, output_state=None):
        self._predicate = predicate
        self._morphism = morphism
        self._output_state = output_state

    def set_output_state(self, output_state):
        self._output_state = output_state

    def predicate(self, data):
        return self._predicate(data)

    def morph(self, data):
        self._morphism(data)
        return self._output_state

    def identity(self):
        return self._output_state

class SerialParallelizationPolicy:
    def __init__(self, data):
        self.data = data

    def make_morphism(self, edges):
        def _morph(data):
            next_morphisms = [edge.morph for edge in edges]
            cur_morphisms = []
            while len(next_morphisms) != 1:
                cur_morphisms[:] = next_morphisms[:]
                del next_morphisms[:]
                for morph in cur_morphisms:
                    next_state = morph(data)
                    next_morphism = next_state.run()
                    if next_morphism is not None:
                        next_morphisms.append(next_morphism)
            next_state = next_morphisms[0](data)
            return next_state
        return _morph

class OnlyOneSelectionPolicy:
    def __init__(self):
        pass

    def select(predicate_values):
        if predicate_values.count(True)
        trues_indices = _get_trues(predicate_values)
        if len(trues_indices) != 1:
            return None
        return trues_indices

class BadGraphStructure(Exception):
    pass

class GraphUnexpectedTermination(Exception):
    pass

def _get_trues(boolean_list):
    return [i for i, val in enumerate(boolean_list) if val == True]
