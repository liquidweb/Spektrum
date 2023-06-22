"""
When selecting a child the literal path needs to be used regardless of depth:
    ex:
        module.rootClass.childClass
    ex:
        spektrum -s tests/example_data -p "select_module.ChildTest.DepthOne.DepthTwo"

    The following will NOT work because it is missing the root class 'ChildTest':
        ex:
            spektrum -s tests/example_data -p "select_module.DepthOne"

Selecting class children can also be done using regex by adding the prefix 're:' to the module

    Select all FixtureTests to run
        ex:
            spektrum -s tests/example_data -p "re:select_module\\..*Fixture"


    Select all Depth tests:
        ex:
            spektrum -s tests/example_data -p "re:select_module\\.ChildTest\\.Depth.*"
            spektrum -s tests/example_data -p "re:select_module\\..*Depth.*"
"""

from spektrum import Spec, fixture


@fixture
class FixtureTest(Spec):
    def fixture_one_test(self):
        pass


class ChildTest(Spec):
    def root_test(self):
        pass

    class DepthOne(Spec):
        def depth_one_test(self):
            pass

        class DepthOneFixture(FixtureTest):
            pass

        class DepthTwo(Spec):
            def depth_two_test(self):
                pass

            class DepthTwoFixture(FixtureTest):
                pass

            class DepthThree(Spec):
                def depth_three_test(self):
                    pass

                class DepthThreeFixture(FixtureTest):
                    pass
