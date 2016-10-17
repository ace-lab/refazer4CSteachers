import sys
import signal
from multiprocessing import Manager, Process
from io import StringIO
import time
import inspect


PROCESS_TIMEOUT = .5


TEST_CONDITIONS = {
    0: {
        'function_name': 'accumulate',
        'input_value_tuples': [
            (lambda x, y: x + y, 11, 5, lambda x: x),
            (lambda x, y: x + y, 0, 5, lambda x: x),
            (lambda x, y: x * y, 2, 3, lambda x: x * x),
            (lambda x, y: x + y, 11, 0, lambda x: x),
            (lambda x, y: x + y, 11, 3, lambda x: x * x),
        ],
        'expected_outputs': [
            26,
            15,
            72,
            11,
            25,
        ],
    },
    1: {
        'function_name': 'product',
        'input_values_tuples': [
            (3, lambda x: x),
            (5, lambda x: x),
            (3, lambda x: x * x),
            (5, lambda x: x * x),
        ],
        'expected_outputs': [
            6,
            120,
            36,
            14400,
        ],
    },
}

class timeout(object):
    ''' REUSE: Adapted from source code for UC Berkeley CS 61A auto-grader. '''

    def __init__(self, seconds, error_message="Timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)



"""
def repeated(f, n):\n    \"\"\"Return the function that computes the nth application of f.\n\n    >>> add_three = repeated(increment, 3)\n    >>> add_three(5)\n    8\n    >>> repeated(triple, 5)(1) # 3 * 3 * 3 * 3 * 3 * 1\n    243\n    >>> repeated(square, 2)(5) # square(square(5))\n    625\n    >>> repeated(square, 4)(5) # square(square(square(square(5))))\n    152587890625\n    >>> repeated(square, 0)(5)\n    5\n    \"\"\"\n    d
        'function_name': 'repeated',
        'input_values_tuples': [
            (lambda x: x + 1, 3),

        ],
        'expected_outputs': [

        ],
    }
}
"""


def stringify_input(input_values):
    ''' Expects input_values to be provided as a list. '''

    for input_value in input_values:
        # We use a heuristic if there are lambdas:
        # Just find the source code of the line where this set of examples
        # was defined, and add that source code line here.
        if callable(input_value):
            return inspect.getsource(input_value).strip()

    return str(input_values)


def stringify_output(result):

    if not result['compile_success']:
        pass
    elif result['timeout']:
        pass
    elif not result['exec_success']:
        result['exec_exception']['type'] = result['exec_exception']['type'].__name__
    elif not result['runtime_success']:
        result['runtime_exception']['type'] = result['runtime_exception']['type'].__name__

    if result['runtime_success']:
        stringified = result['returned']
    elif not result['compile_success']:
        stringified = 'N/A'
    elif result['timeout']:
        stringified = 'Timeout'
    elif not result['exec_success']:
        stringified = result['exec_exception']['type']
    elif not result['runtime_success']:
        stringified = result['runtime_exception']['type']

    return stringified


def evaluate_function(code_text, function_name, input_value_tuples, expected_outputs):

    results = {
        'overall_success': False,
        'test_cases': []
    }

    # Compute the result of each individual test
    for test_index in range(len(input_value_tuples)):
        results['test_cases'].append(evaluate_function_once(
            code_text=code_text,
            function_name=function_name,
            input_values=input_value_tuples[test_index],
            expected_output=expected_outputs[test_index],
        ))
    
    # Compute the overall success across all tests
    results['overall_success'] = all(r['success'] for r in results['test_cases'])

    return results


def evaluate_function_once(code_text, function_name, input_values, expected_output):

    cant_run_code = False
    result = {
        'input_values': input_values,
        'expected': expected_output,
        'success': False,  # we assume the test case failed until it completely succeeds
        'exec_success': False,
        'timeout': False,
        'runtime_success': False,
    }

    # Save the original stdout so we can resume them after this function runs
    original_stdout = sys.stdout

    # Compile the code to runnable form
    try:
        code = compile(code_text, '<string>', 'exec')
        result['compile_success'] = True
    except SyntaxError as s:
        result['compile_success'] = False
        result['syntax_error'] = {
            'lineno': s.lineno,
            'offset': s.offset,
            'msg': s.msg,
            'text': s.text,
        }
        cant_run_code = True

    # Set up fresh scopes for the code to run within
    local_scope = {}
    global_scope = {}

    if cant_run_code is False:

        # Run the code to capture the function definition
        try:
            exec(code, global_scope, local_scope)
            result['exec_success'] = True
        except Exception as e:
            result['exec_exception'] = {
                'type': type(e),
                'args': e.args,
            }
            cant_run_code = True

    if cant_run_code is False:

        def run_function(function, function_name, input_values, result):

            # It's critical to do a few things here:
            # 1. Transfer the input values into the sandbox scope
            # 2. Transfer the function name into the sandbox global scope so it can be called
            #    recursively (otherwise, it can't be found for recursive calls)
            # 3. Store the output in a sandbox variable and retrieve it later.
            local_scope['input_values'] = input_values
            global_scope[function_name] = local_scope[function_name]

            # Create a new version of stdout to capture what gets printed
            capturable_stdout = StringIO()
            sys.stdout = capturable_stdout

            try:
                exec('output = ' + function_name + '(*input_values)', global_scope, local_scope)
                output = local_scope['output']
                result['returned'] = output
                result['stdout'] = capturable_stdout.getvalue()
                result['runtime_success'] = True
            # If we catch a TimeoutError, this is probably from the timer that we built
            # to keep programs from executing for too long.  Propagate it up to the next
            # level, where we can catch it and include the exception in the results.
            except TimeoutError as te:
                raise te
            except Exception as e:
                result['runtime_exception'] = {
                    'type': type(e),
                    'args': e.args,
                }

        # Create a new process to run the test function, so we can terminate it if it loops
        result_shared_data = {}
        try:
            with timeout(seconds=.5):
                run_function(local_scope[function_name], function_name, input_values, result_shared_data)
        except TimeoutError:
            result['timeout'] = True

        '''
        result_shared_data = Manager().dict()
        process = Process(
            target=run_function,
            args=(
                local_scope[function_name],
                function_name,
                input_values,
                result_shared_data,
            )
        )a

        # Run the function, and terminate it if it runs too long
        process.start()
        start = time.time()
        while time.time() < start + PROCESS_TIMEOUT:
            if process.is_alive():
                time.sleep(.1)
            else:
                result['timeout'] = False
                break

        process.terminate()
        '''

        # Merge the results from the function that was run with the  main results
        result.update(result_shared_data)
        result['success'] = (result['returned'] == expected_output) if 'returned' in result else False

        # Return stdout to original
        sys.stdout = original_stdout
    
    return result
