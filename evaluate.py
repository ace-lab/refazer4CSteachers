import sys
import signal
from multiprocessing import Manager, Process
from io import StringIO
import time
import inspect


PROCESS_TIMEOUT = .5


PREREQUISITE_CODE = """
from operator import add, mul

def identity(x):
    return x

def increment(x):
    return x + 1

def triple(x):
    return x * 3

def square(x):
    return x * x

def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)

"""


# Tests can be defined either as pairs of input and output (see 0 and 1 below),
# as test code run after the code has been run (see 2 below),
# or as assertions that are run after the student's function is initialized (see comment in 2 below).
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
        # Some student submissions call "product" for this, so we include a correct implementation
        'pre_code': '\n'.join([
            PREREQUISITE_CODE,
            "",
            "def product(n, term):",
            "    total = 1",
            "    for i in range(1, n + 1):",
            "        total *= term(i)",
            "    return total",
            "",
        ]),
    },
    1: {
        'function_name': 'product',
        'input_value_tuples': [
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
        'pre_code': PREREQUISITE_CODE,
    },
    2: {
        'function_name': 'repeated',
        # Tests specified as test code need to provide test code to run after the student's
        # code is run, along with an expected output from each one.
        # Each string of test code needs to define the variable "output", which will be
        # returned from the test code, and checked against the expected output value.
        'test_code': [
            "add_three = repeated(lambda x: x + 1, 3); output = add_three(5)",
            "output = repeated(lambda x: x * 3, 5)(1)",
            "output = repeated(lambda x: x * x, 2)(5)",
            "output = repeated(lambda x: x * x, 4)(5)",
            "output = repeated(lambda x: x * x, 0)(5)"
        ],
        'expected_outputs': [
            8,
            243,
            625,
            152587890625,
            5,
        ],
        # This test used to be run as assertions.
        # We leave the code here as future reference.
        # If you provide assertions, you don't need to specify input values and expected output.
        # Each assertion is an 'assert' that is run after the code has finished running.
        # 'assertions': [
        #      "assert repeated(lambda x: x * x, 0)(5) == 5;",
        # ],
        # Some student submissions call "product" and "accumulate", so we include correct implementations
        'pre_code': '\n'.join([
            PREREQUISITE_CODE,
            "",
            "def product(n, term):",
            "    total = 1",
            "    for i in range(1, n + 1):",
            "        total *= term(i)",
            "    return total",
            "",
            "",
            "def accumulate(combiner, base, n, term):",
            "    total = base",
            "    for i in range(1, n + 1):",
            "        total = combiner(total, term(i))",
            "    return total",
            "",
        ]),
    }
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
        if result['test_type'] == 'assertion':
            stringified = True
        else:
            stringified = str(result['returned'])
    elif not result['compile_success']:
        stringified = 'N/A'
    elif result['timeout']:
        stringified = 'Timeout'
    elif not result['exec_success']:
        stringified = result['exec_exception']['type']
    elif not result['runtime_success']:
        if result['test_type'] == 'assertion' and result['runtime_exception']['type'] == "AssertionError":
            stringified = False
        else:
            stringified = result['runtime_exception']['type']
    else:
        stringified = "Unknown error"

    return stringified


def evaluate_function(
    code_text, function_name, input_value_tuples, expected_outputs,
    assertions=None, test_code=None, pre_code=None):

    results = {
        'overall_success': False,
        'test_cases': []
    }

    # Compute the result of each individual test
    if input_value_tuples is not None:
        for test_index in range(len(input_value_tuples)):
            results['test_cases'].append(evaluate_function_once(
                code_text=code_text,
                function_name=function_name,
                input_values=input_value_tuples[test_index],
                expected_output=expected_outputs[test_index],
                pre_code=pre_code,
            ))
    elif test_code is not None:
        for test_index in range(len(test_code)):
            results['test_cases'].append(evaluate_function_once(
                code_text=code_text,
                function_name=function_name,
                test_code=test_code[test_index],
                expected_output=expected_outputs[test_index],
                pre_code=pre_code,
            ))
    elif assertions is not None:
        for test_index in range(len(assertions)):
            results['test_cases'].append(evaluate_function_once(
                code_text=code_text,
                function_name=function_name,
                assertion_code=assertions[test_index],
                pre_code=pre_code,
            ))
    
    # Compute the overall success across all tests
    results['overall_success'] = all(r['success'] for r in results['test_cases'])

    return results


def evaluate_function_once(
        code_text, function_name, input_values=None, expected_output=None,
        assertion_code=None, test_code=None, pre_code=None):

    input_values = [] if input_values is None else input_values
    test_type = 'assertion' if assertion_code is not None else\
                'test_code' if test_code is not None else\
                'input-output'

    cant_run_code = False
    result = {
        'input_values': input_values,
        'expected': expected_output,
        'success': False,  # we assume the test case failed until it completely succeeds
        'exec_success': False,
        'timeout': False,
        'runtime_success': False,
        'test_type': test_type,
    }
    if result['test_type'] == 'assertion':
        result['assertion'] = assertion_code
    elif result['test_type'] == 'test_code':
        result['test_code'] = test_code

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

        def run_function(function, function_name, input_values, result, test_code, pre_code):

            # It's critical to do a few things here:
            # 1. Transfer the input values into the sandbox scope
            # 2. Transfer the function name into the sandbox global scope so it can be called
            #    recursively (otherwise, it can't be found for recursive calls)
            # 3. Store the output in a sandbox variable and retrieve it later.
            local_scope['input_values'] = input_values
            global_scope.update(local_scope)  # transfers functions and other locals to global scope

            # The test condition may specify code that needs to be run before the
            # test case is run, for instance to populate the environment with other functions
            # that can be run.  Here we run that prerequisite code.
            if pre_code is not None:
                pre_local_scope = {}
                exec(pre_code, global_scope, pre_local_scope)

                # We have found that functions defined in the local scope can't be called
                # in exec later.  So we transfer everything defined into the local scope
                # of the prerequisite code into the global scope
                global_scope.update(pre_local_scope)

            # Create a new version of stdout to capture what gets printed
            capturable_stdout = StringIO()
            sys.stdout = capturable_stdout

            # If this is an assertion, run the assertion code.
            # If the test spec included a line of test code that returns output,
            # then run the test code.
            # Otherwise, pass in the input and check the output
            if result['test_type'] == 'assertion':
                code = assertion_code
            elif result['test_type'] == 'input-output':
                code = 'output = ' + function_name + '(*input_values)'
            elif result['test_type'] == 'test_code':
                code = test_code

            # Run the code!  Watch for assertion errors, timeout errors, and others
            try:
                exec(code, global_scope, local_scope)
            # If we catch a TimeoutError, this is probably from the timer that we built
            # to keep programs from executing for too long.  Propagate it up to the next
            # level, where we can catch it and include the exception in the results.
            except TimeoutError as te:
                raise te
            except AssertionError as ae:
                result['runtime_exception'] = {
                    'type': AssertionError,
                    'args': ae.args,
                }
            except Exception as e:
                result['runtime_exception'] = {
                    'type': type(e),
                    'args': e.args,
                }
            else:
                if result['test_type'] in ['input-output', 'test_code']:
                    output = local_scope['output']
                    result['returned'] = output
                result['stdout'] = capturable_stdout.getvalue()
                result['runtime_success'] = True

        # Create a new process to run the test function, so we can terminate it if it loops
        try:
            with timeout(seconds=.5):
                run_function(
                    local_scope[function_name], function_name,
                    input_values, result, test_code, pre_code
                )
        except TimeoutError:
            result['timeout'] = True

        # Compute the success of the test by inspecting assertions and input-output results
        if result['test_type'] == 'assertion':
            result['success'] = 'runtime_exception' not in result
        elif result['test_type'] in ['input-output', 'test_code']:
            result['success'] = (result['returned'] == expected_output) if 'returned' in result else False

        # Return stdout to original
        sys.stdout = original_stdout
    
    return result
