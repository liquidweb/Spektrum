"""
Selecting tests can be done using regex by adding the prefix 're:' to the test

    ex:
        spektrum -s tests -p select_tests --select-tests "test"

            Selects no tests

        spektrum -s tests -p select_tests --select-tests "this_is_a_first_test"

            Selects non-dataset "this_is_a_first_test" tests in this file

        spektrum -s tests -p select_tests --select-tests "re:.*that.*"

            Selects no tests in this file

        spektrum -s tests -p select_tests --select-tests "re:.*"

            Selects all tests in this file

        spektrum -s tests -p select_tests --select-tests "re:.*first.*","re:.*second.*"

            Selects all tests in this file

        spektrum -s tests -p select_tests --select-tests "this_is_a_first_test","re:.*second.*"

            Selects non-dataset "this_is_a_first_test" tests,
            "this_is_a_second_test" tests,
            "this_is_a_second_test_1" tests,
            "this_is_a_second_test_2" tests in this file

        spektrum -s tests -p select_tests --select-tests "re:this_is_a_first_test.*"

            Selects all "this_is_a_first_test" tests,
            "this_is_a_first_test_1" tests,
            "this_is_a_first_test_2" tests in this file
"""


from spektrum import Spec, DataSpec


class SpecTest(Spec):
    def this_is_a_first_test(self):
        pass

    def this_is_a_second_test(self):
        pass

    class SpecDatasetChild(DataSpec):
        DATASET = {
            '1': {'sample': 1},
            '2': {'args': {'sample': 2}, 'meta': {'test': 'sample'}}
        }

        def this_is_a_first_test(self, sample):
            pass

        def this_is_a_second_test(self, sample):
            pass

    class SpecNestedChild(Spec):
        def this_is_a_first_test(self):
            pass

        def this_is_a_second_test(self):
            pass
