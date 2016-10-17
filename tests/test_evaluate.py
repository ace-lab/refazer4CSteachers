import logging
import unittest

from evaluate import evaluate_function_once, evaluate_function


logging.basicConfig(level=logging.INFO, format="%(message)s")


class EvaluateSolutionTest(unittest.TestCase):
    
    def test_evaluation_returns_input_values_same_as_provided(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    return 0",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['input_values'], ("test_input",))

    def test_evaluation_returns_expected_value_same_as_provided(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    return 0",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['expected'], 1)

    def test_evaluation_returns_return_value(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    return 0",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['returned'], 0)

    def test_evaluation_returns_success_of_test(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    return 0",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['success'], False)

    def test_evaluation_returns_stdout_of_test(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    print('Line 1')",
                "    print('Line 2')",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['stdout'], "Line 1\nLine 2\n")

    def test_evaluation_returns_empty_string_when_no_stdout(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    return 0",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['stdout'], "")

    def test_evaluation_returns_exceptions_encountered(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    raise KeyError",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['runtime_exception']['type'], KeyError)

    def test_evaluation_returns_syntaxerror(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_)",
                "    pass",
            ]),
            function_name='func',
            input_values=("test_input",),
            expected_output=1,
        )
        self.assertEqual(result['compile_success'], False)
        self.assertEqual(result['syntax_error']['text'], "def func(input_)\n")
        self.assertEqual(result['syntax_error']['lineno'], 1)
        self.assertEqual(result['syntax_error']['offset'], 17)

    def test_recursive_solution_works(self):
        # Earlier, we had problems running code with recursion as the name of
        # the compiled function couldn't be found in the scope of that running
        # function.  This test makes sure we can handle recursion.
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    if input_ == 0:",
                "        return 1",
                "    else:",
                "        return 1 + func(input_ - 1)",
            ]),
            function_name='func',
            input_values=(3,),
            expected_output=4,
        )
        self.assertEqual(result['success'], True)
        self.assertEqual(result['timeout'], False)
        self.assertEqual(result['runtime_success'], True)

    def test_terminate_infinite_loops(self):
        # Earlier, we had problems running code with recursion as the name of
        # the compiled function couldn't be found in the scope of that running
        # function.  This test makes sure we can handle recursion.
        result = evaluate_function_once(
            code_text='\n'.join([
                "def func(input_):",
                "    while True:",
                "        pass",
                "    return input_",
            ]),
            function_name='func',
            input_values=(3,),
            expected_output=3,
        )
        self.assertEqual(result['timeout'], True)
        self.assertEqual(result['success'], False)

    def test_return_success_when_assertion_succeeds(self):
        # For assignments where a student is asked to return a function as the result,
        # we need something more than an equality comparison.  In this case,
        # assertions run after the fact should do the trick.
        result = evaluate_function_once(
            code_text='\n'.join([
                "def make_func(input_):",
                "    return lambda x: input_ * x",
            ]),
            function_name='make_func',
            assertion_code="identity = make_func(1); assert identity(5) == 5;",
        )
        self.assertEqual(result['test_type'], "assertion")
        self.assertEqual(result['assertion'], "identity = make_func(1); assert identity(5) == 5;")
        self.assertEqual(result['success'], True)

    def test_assertion_failure(self):
        result = evaluate_function_once(
            code_text='\n'.join([
                "def make_func(input_):",
                "    return lambda x: input_ * x",
            ]),
            function_name='make_func',
            assertion_code="identity = make_func(1); assert identity(5) == 4;",
        )
        self.assertEqual(result['success'], False)


class EvaluateMultipleSolutionsTest(unittest.TestCase):

    def test_evaluate_multiple_functions(self):
        results = evaluate_function(
            code_text='\n'.join([
                "def func(input_):",
                "    print('out: ' + input_)",
                "    return 'result: ' + input_",
            ]),
            function_name='func',
            input_value_tuples=[
                ("input1",),
                ("input2",),
            ],
            expected_outputs=[
                ('result: input1'),
                ('result: will fail'),
            ],
        )
        self.assertEqual([_['input_values'] for _ in results['test_cases']], [
            ('input1',),
            ('input2',),
        ])
        self.assertEqual([_['expected'] for _ in results['test_cases']], [
            'result: input1',
            'result: will fail',
        ])
        self.assertEqual([_['returned'] for _ in results['test_cases']], [
            'result: input1',
            'result: input2',
        ])
        self.assertEqual([_['success'] for _ in results['test_cases']], [True, False])
        self.assertEqual([_['stdout'] for _ in results['test_cases']], [
            'out: input1\n',
            'out: input2\n',
        ])

    def test_no_overall_success_when_one_case_fails(self):
        results = evaluate_function(
            code_text='\n'.join([
                "def func(input_):",
                "    return 'result: ' + input_",
            ]),
            function_name='func',
            input_value_tuples=[
                ("input1",),
                ("input2",),
            ],
            expected_outputs=[
                ('result: input1'),
                ('result: will fail'),
            ],
        )
        self.assertEqual(results['overall_success'], False)

    def test_overall_success_when_all_cases_pass(self):
        results = evaluate_function(
            code_text='\n'.join([
                "def func(input_):",
                "    return 'result: ' + input_",
            ]),
            function_name='func',
            input_value_tuples=[
                ("input1",),
                ("input2",),
            ],
            expected_outputs=[
                ('result: input1'),
                ('result: input2'),
            ],
        )
        self.assertEqual(results['overall_success'], True)
