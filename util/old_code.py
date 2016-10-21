''' Old code that needs a rewrite. '''

import json


class Rule_and_test:

    def __init__(self, test, rule):
        self.test = test
        self.rule = rule

    def __hash__(self):
        return hash((self.test[0]['input'], self.test[0]['output'], self.rule))

    def __eq__(self, other):
        return (self.test, self.rule) == (other.test, other.rule)


class Rule_based_cluster:
    def __init__(self, rule, size, fixes):
        self.rule = rule
        self.size = size
        self.fixes = fixes


class Test_based_cluster:
    def __init__(self, test, size, fixes):
        self.test = test
        self.size = size
        self.fixes = fixes


class Rule_and_test_based_cluster:
    def __init__(self, rule, test, size, fixes):
        self.rule = rule
        self.test = test
        self.size = size
        self.fixes = fixes


class Question:
    def __init__(self, question_id, rule_based_cluster, test_based_cluster, rule_and_test_based_cluster,
                 question_instructions, submissions):
        self.question_id = question_id
        self.rule_based_cluster = rule_based_cluster
        self.test_based_cluster = test_based_cluster
        self.rule_and_test_based_cluster = rule_and_test_based_cluster
        self.question_instructions = question_instructions
        self.submissions = submissions


def get_test(failed):
    expected_value = ''
    output_value = ''
    previous_line = ''
    testcases = []
    for line in failed:
        if previous_line == '# Error: expected':
            expected_value = line[1:].strip()
        if previous_line == '# but got':
            output_value = line[1:].strip()
        if line.startswith('>>>'):
            line_no_comment = line[4:].split('#')[0] #removes comments
            if not line_no_comment.startswith('check(') and not line_no_comment.startswith('from construct_check import check'):
                testcases.append(line_no_comment)
        previous_line = line
    if len(testcases)>0:
        failed_test = testcases[-1]
    else:
        failed_test = ''

    results = [{
        'input': failed_test,
        'output': output_value,
        'expected': expected_value
    }]

    return results


def create_grader_question(filename, question_number):

    ordered_clusters = []

    with open(filename) as data_file:
        submission_pairs = json.load(data_file)

    clustered_fixes_by_rule = {}
    clustered_fixes_by_test = {}
    clustered_fixes_by_rule_and_test = {}
    group_id_to_test_for_a_question = {}
    fixes = []

    group_id = -1
    checked_tests = []

    rule_and_test_based_cluster = []

    no_sequence_diff = []
    def_seq_diff = []
    num_fixed = []

    for submission_pair in submission_pairs:
        submission_pair['IsFixed'] = False #initialized to false
        #submission_pair['SynthesizedAfter'] =  ''
        num_fixed.append(submission_pair)
        rule = submission_pair['UsedFix']
        # rule = rule.replace('\\', '')

        fix = submission_pair
        code_before = submission_pair['before']
        code_after = '' #submission_pair['SynthesizedAfter'] #old correctino is erased
        code_student_after = submission_pair['after']
        filename = 'filename-' + str(submission_pair['Id'])

        # fix['diff_lines'] = highlight.diff_file(filename, code_before, code_after, 'full')
        # fix['diff_student_lines'] = highlight.diff_file(filename, code_before, code_student_after, 'full')
        # fix['diff_but_not_a_diff'] = highlight.diff_file(filename, code_before, code_before, 'full')

        test = get_test(submission_pair['failed'])
        
        fix['tests'] = test
        fix['before'] = code_before
        fix['input_output_before'] = {} #submission_pair['augmented_tidy_before_testcase_to_output']
        fix['synthesized_after'] = submission_pair['SynthesizedAfter']
        try:
            fix['dynamic_diff'] = submission_pair['sequence_comparison_diff']
        except:
            no_sequence_diff.append(submission_pair)

        id = submission_pair['Id']

        if (rule in clustered_fixes_by_rule.keys()):
            clustered_fixes_by_rule[rule].append(fix)
        else:
            clustered_fixes_by_rule[rule] = [fix]

        if (test in checked_tests):
            group_id = checked_tests.index(test)
            clustered_fixes_by_test[checked_tests.index(test)].append(fix)
        else:
            checked_tests.append(test)
            group_id = len(checked_tests)
            clustered_fixes_by_test[checked_tests.index(test)] = [fix]

        key = Rule_and_test(test=test,rule=rule)
        if key in clustered_fixes_by_rule_and_test.keys():
            clustered_fixes_by_rule_and_test[key].append(fix)
        else:
            clustered_fixes_by_rule_and_test[key] = [fix]

        fix['group_id'] = group_id
        group_id_to_test_for_a_question[group_id] = test
        fixes.append(fix)

    for key,value in clustered_fixes_by_rule.items():
        cluster = Rule_based_cluster(rule=key, fixes = value, size=len(value))
        ordered_clusters.append(cluster)

    test_based_clusters = []
    for key,value in clustered_fixes_by_test.items():
        cluster = Test_based_cluster(test=checked_tests[key], fixes = value, size=len(value))
        test_based_clusters.append(cluster)

    for key,value in clustered_fixes_by_rule_and_test.items():
        cluster = Rule_and_test_based_cluster(test=key.test, rule=key.rule, fixes = value, size = len(value))
        rule_and_test_based_cluster.append(cluster)

    ordered_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    test_based_clusters.sort(key = lambda x : len(x.fixes), reverse= True)
    rule_and_test_based_cluster.sort(key = lambda  x : len(x.fixes), reverse=True)
    question = Question(question_id=question_number, rule_based_cluster = ordered_clusters,
                        test_based_cluster = test_based_clusters, rule_and_test_based_cluster=rule_and_test_based_cluster,
                        question_instructions = None, submissions= fixes)

    return question
