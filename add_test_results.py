import json
import sys
from io import StringIO

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

    if cant_run_code is False:

        # Set up fresh scopes for the code to run within
        local_scope = {}
        global_scope = {}

        # Run the code to capture the function definition
        try:
            exec(code, global_scope, local_scope)
            result['exec_success'] = True
            local_scope['accumulate'](lambda x, y: x + y, 0, 5, lambda x: x)
            print("test")
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
            output = local_scope[function_name](*input_values)
            print(output)
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

with open('data/accumulate_all_attempts.json') as data:
    attempts = json.load(data)


for attempt in attempts :
    result = evaluate_function(attempt['before'], "accumulate",
     input_value_tuples, expected_outputs)
    print (attempt['before'])
    failure = {}
    for test in result['test_cases']: 
        if test['success'] is False:
            print (test)
            failure['expected'] = test['expected']
#            if test['runtime_success']:
#                failure['output'] = test['returned']
#            else :
#                failure['output'] = test['runtime_exception']['args']
            break
    attempt['failed'] = failure
    #print(attempt['failed'])
    break



