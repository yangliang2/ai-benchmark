# pyright: basic
'''Optional snapshot/restore helpers for pysm state machines.'''
from .pysm import State, StateMachine, StateMachineException, deque


SNAPSHOT_VERSION = 1


def rebuild(data):
    '''Build a fresh state machine graph out of a snapshot.

    Where :func:`restore` needs the graph the snapshot came from, this makes
    one: the states and machines the snapshot names, wired up in the shape
    their paths describe, initialized, and left in the configuration that was
    recorded — so that ``snapshot(rebuild(data))`` gives ``data`` back.

    A snapshot does not record which of a machine's states is its initial
    one, and the graph needs one to initialize at all. Any of a machine's own
    states will do, since the recorded configuration is written over the
    initial one before the graph is handed back; this picks the first in name
    order so that one snapshot always rebuilds into the same graph.

    Transitions are not part of a snapshot and are not rebuilt: what comes
    back is a graph in the recorded configuration, not a working machine.
    '''
    if data.get('version') != SNAPSHOT_VERSION:
        raise StateMachineException('Unsupported snapshot version: {0}'.format(
            data.get('version')))

    root_path = tuple(data['root'])
    paths = [tuple(path) for path in data.get('states', [])]
    machine_paths = set(
        tuple(item['path']) for item in data.get('machines', []))
    known = set(paths)
    if root_path not in machine_paths:
        raise StateMachineException(
            'Snapshot root is not one of its machines: {0}'.format(
                list(root_path)))
    for path in sorted(machine_paths):
        if path not in known:
            raise StateMachineException(
                'Snapshot machine is not one of its states: {0}'.format(
                    list(path)))
    for path in sorted(paths):
        if path[:len(root_path)] != root_path:
            raise StateMachineException(
                'Snapshot state does not start at root {0}: {1}'.format(
                    root_path[0], list(path)))
        if len(path) > len(root_path) and path[:-1] not in known:
            raise StateMachineException(
                'Snapshot state has no parent state: {0}'.format(list(path)))

    states = {}
    for path in sorted(paths, key=len):
        states[path] = (StateMachine(path[-1]) if path in machine_paths
                        else State(path[-1]))
    children = {}
    for path in sorted(paths):
        if len(path) > len(root_path):
            children.setdefault(path[:-1], []).append(path)
    for parent_path in sorted(children):
        parent = states[parent_path]
        for index, child_path in enumerate(children[parent_path]):
            parent.add_state(states[child_path], initial=(index == 0))

    root = states[root_path]
    root.initialize()
    restore(root, data)
    return root


def snapshot(machine, metadata=None):
    '''Return a plain-data snapshot of a configured state machine graph.'''
    root = machine.root_machine
    _validate_unique_sibling_names(root)
    machines = _iter_machines(root)
    data = {
        'version': SNAPSHOT_VERSION,
        'root': _state_path(root),
        'states': [_state_path(state) for state in _iter_states(root)],
        'machines': [],
        'leaf_state': _state_path(root.leaf_state)
        if root.leaf_state is not None else None,
        'leaf_state_stack': [
            _state_path(state) for state in root.leaf_state_stack.deque
        ],
    }
    if metadata is not None:
        data['metadata'] = metadata

    for item in machines:
        data['machines'].append({
            'path': _state_path(item),
            'state': _state_path(item.state) if item.state is not None else None,
            'state_stack': [
                _state_path(state) for state in item.state_stack.deque
            ],
        })

    data['states'].sort()
    data['machines'].sort(key=lambda item: item['path'])
    return data


def restore(machine, data):
    '''Restore ``machine`` from a snapshot created by :func:`snapshot`.

    The machine graph must already be constructed and initialized. Restore is
    strict about topology so stale snapshots fail loudly instead of silently
    restoring to the wrong state.
    '''
    root = machine.root_machine
    if data.get('version') != SNAPSHOT_VERSION:
        raise StateMachineException('Unsupported snapshot version: {0}'.format(
            data.get('version')))
    if data.get('root') != _state_path(root):
        raise StateMachineException('Snapshot root does not match machine root')

    _validate_topology(root, data)
    _validate_active_state_paths(root, data)

    for machine_data in data.get('machines', []):
        item = _resolve_machine_path(root, machine_data['path'])
        state_path = machine_data.get('state')
        item.state = (_resolve_state_path(root, state_path)
                      if state_path is not None else None)
        _replace_stack(
            item.state_stack,
            [_resolve_state_path(root, path)
             for path in machine_data.get('state_stack', [])])

    leaf_path = data.get('leaf_state')
    root._leaf_state = (_resolve_state_path(root, leaf_path)
                        if leaf_path is not None else None)
    _replace_stack(
        root.leaf_state_stack,
        [_resolve_state_path(root, path)
         for path in data.get('leaf_state_stack', [])])
    return machine


def _iter_states(root):
    queue = deque([root])
    while queue:
        state = queue.popleft()
        yield state
        if isinstance(state, StateMachine):
            children = sorted(state.states, key=lambda item: item.name)
            queue.extend(children)


def _iter_machines(root):
    return [state for state in _iter_states(root)
            if isinstance(state, StateMachine)]


def _state_path(state):
    path = []
    item = state
    while item is not None:
        path.append(item.name)
        item = item.parent
    return list(reversed(path))


def _resolve_machine_path(root, path):
    state = _resolve_state_path(root, path)
    if not isinstance(state, StateMachine):
        raise StateMachineException(
            'Path does not point to a state machine: {0}'.format(path))
    return state


def _resolve_state_path(root, path):
    if not path:
        raise StateMachineException('State path cannot be empty')
    if path[0] != root.name:
        raise StateMachineException(
            'State path {0} does not start at root {1}'.format(
                path, root.name))

    state = root
    for name in path[1:]:
        if not isinstance(state, StateMachine):
            raise StateMachineException(
                'State path descends through non-machine state: {0}'.format(
                    path))
        matches = [child for child in state.states if child.name == name]
        if not matches:
            raise StateMachineException('Unknown state path: {0}'.format(path))
        if len(matches) > 1:
            raise StateMachineException('Ambiguous state path: {0}'.format(
                path))
        state = matches[0]
    return state


def _replace_stack(stack, states):
    maxlen = getattr(stack.deque, 'maxlen', StateMachine.STACK_SIZE)
    stack.deque = deque(maxlen=maxlen)
    for state in states:
        stack.push(state)


def _validate_topology(root, data):
    expected_states = sorted(data.get('states', []))
    actual_states = sorted(_state_path(state) for state in _iter_states(root))
    if expected_states != actual_states:
        raise StateMachineException('Snapshot topology does not match machine')

    expected_machines = sorted(item['path']
                               for item in data.get('machines', []))
    actual_machines = sorted(_state_path(item) for item in _iter_machines(root))
    if expected_machines != actual_machines:
        raise StateMachineException('Snapshot machines do not match machine')

    _validate_unique_sibling_names(root)


def _validate_active_state_paths(root, data):
    machines = {}
    for machine_data in data.get('machines', []):
        path = tuple(machine_data['path'])
        machine = _resolve_machine_path(root, machine_data['path'])
        machines[path] = machine_data

        state_path = machine_data.get('state')
        if state_path is not None:
            state = _resolve_state_path(root, state_path)
            if state.parent is not machine:
                raise StateMachineException(
                    'Snapshot state is not a child of machine: {0}'.format(
                        state_path))

        for stack_path in machine_data.get('state_stack', []):
            state = _resolve_state_path(root, stack_path)
            if state.parent is not machine:
                raise StateMachineException(
                    'Snapshot stack state is not a child of machine: {0}'
                    .format(stack_path))

    expected_leaf = _expected_leaf_path_from_machine_states(
        tuple(data['root']), machines)
    actual_leaf = data.get('leaf_state')
    if ((actual_leaf is None and expected_leaf is not None) or
            (actual_leaf is not None and tuple(actual_leaf) != expected_leaf)):
        raise StateMachineException(
            'Snapshot leaf state does not match active machine states')


def _expected_leaf_path_from_machine_states(root_path, machines):
    machine_data = machines[root_path]
    state_path = machine_data.get('state')
    if state_path is None:
        return None

    leaf_path = tuple(state_path)
    while leaf_path in machines:
        child_data = machines[leaf_path]
        child_state_path = child_data.get('state')
        if child_state_path is None:
            break
        leaf_path = tuple(child_state_path)
    return leaf_path


def _validate_unique_sibling_names(root):
    for state in _iter_states(root):
        if not isinstance(state, StateMachine):
            continue
        names = {}
        for child in state.states:
            names.setdefault(child.name, 0)
            names[child.name] += 1
        duplicates = [name for name, count in names.items() if count > 1]
        if duplicates:
            raise StateMachineException(
                'Ambiguous sibling state names under {0}: {1}'.format(
                    _state_path(state), duplicates))
