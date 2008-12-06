#!/usr/bin/env python3.0

import os
import sys
import doctest
import unittest

sys.path.append('../lib')

import test_functools
import test_scheduler

# -----------------------------------------------------------------------------

def main():
    suite = unittest.TestSuite()

    # Load the doctests
    prefix = os.path.join('..', 'lib')
    for root, dirs, files in os.walk(prefix):
        root = root[len(prefix + os.sep):].replace(os.sep, '.')

        for file in files:
            if file == '__init__.py':
                module = root
            elif file.endswith('.py'):
                module = root + '.' + file[:-len('.py')]
            else:
                continue

            try:
                test = doctest.DocTestSuite(__import__(module, {}, {}, ['']))
            except ValueError as e:
                # no doc test exists
                pass
            else:
                suite.addTest(test)

    suite.addTest(test_functools.suite())
    suite.addTest(test_scheduler.suite())

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

    return 0

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    sys.exit(main())
