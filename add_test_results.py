import json
import sys
from io import StringIO
from flaskr import evaluate_function_once
from concurrent.futures import ThreadPoolExecutor


input_value_tuples=[
(lambda x, y: x + y, 11, 5, lambda x: x),
(lambda x, y: x + y, 0, 5, lambda x: x),
(lambda x, y: x * y, 2, 3, lambda x: x * x),
(lambda x, y: x + y, 11, 0, lambda x: x),
(lambda x, y: x + y, 11, 3, lambda x: x * x),
]

expected_outputs=[
26,
15,
72,
11,
25,
]

def evaluate_function(code_text, function_name, input_value_tuples, expected_outputs):

    results = {
        'overall_success': False,
        'test_cases': []
    }

    # XXX: This is super hacky as we are sparking off a bunch of threads that will then
    # create a bunch of processes.  To speed this up, we should find a way to optimize the
    # creation of processes in the `evaluate_function_once` function.
    pool = ThreadPoolExecutor(max_workers=10)
    results['test_cases'] = pool.map(
        lambda io: evaluate_function_once(code_text, function_name, io[0], io[1]),
        zip(input_value_tuples, expected_outputs)
    )

    # Compute the overall success across all tests
    results['overall_success'] = all(r['success'] for r in results['test_cases'])

    return results


'''
def evaluate_function_once(code_text, function_name, input_values, expected_output):

    cant_run_code = False
    result = {
        'input_values': input_values,
        'expected': expected_output,
        'success': False,  # we assume the test case failed until it completely succeeds
        'runtime_success': False,
        'exec_success': False,
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
        # Create a new version of stdout to capture what gets printed
        capturable_stdout = StringIO()
        sys.stdout = capturable_stdout                
        # Execute the code with the test inputs        
        try:
            local_scope['input_values'] = input_values
            global_scope[function_name] = local_scope[function_name]
            exec('output = ' + function_name + '(*input_values)', global_scope, local_scope)
            output = local_scope['output']
            result['runtime_success'] = True
        except Exception as e:
            result['runtime_exception'] = {
                'type': type(e),
                'args': e.args,
            }

        # Transfer the results to the return value
        if result['runtime_success']:
            result['returned'] = output
            result['success'] = (output == expected_output)

        result['stdout'] = capturable_stdout.getvalue()

    # Return stdout to original
    sys.stdout = original_stdout
    
    return result
'''

with open('data/accumulate_all_attempts.json') as data:
    attempts = json.load(data)


for attempt in attempts :
    result = evaluate_function(attempt['before'], "accumulate",
     input_value_tuples, expected_outputs)
    failure = {}
    for test in result['test_cases']: 

        if test['success'] is False:
            # print (test)
            failure['expected'] = test['expected']
            if test['runtime_success']:
                failure['output'] = test['returned']
            elif 'runtime_exception' in test:
                failure['output'] = test['runtime_exception']['args']
            elif test['timeout']:
                failure['output'] = "Timeout"
            else:
                failure['output'] = "Other"
            # break

        else:
            print("Success!")

    attempt['failed'] = failure
    print(attempt['failed'])
    # break
