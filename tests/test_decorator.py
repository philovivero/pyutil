from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six
import sys
import threading
import time

import wizzat.decorators
from wizzat.decorators import *
from wizzat.testutil   import *

class MemoizeTest(TestCase):
    options = {
        'disable_kw'   : (False, True),
        'ignore_nulls' : (False, True),
        'threads'      : (False, True),
        'obj'          : (False, True),
        'max_bytes'    : (None, 100),
        'max_size'     : (None, 2),
        'until'        : (False, lambda: time.time() + .01),
    }

    def test_option__until(self):
        self.called = 0
        @memoize(until=lambda: time.time() + .01)
        def func(*args, **kwargs):
            self.called += 1

        func(1,2,3,a=1,b=2) # called
        func(1,2,3,a=1,b=2) # cached
        func(1,2,4,a=1,b=2) # called

        self.assertEqual(self.called, 2)
        self.assertEqual(func.stats['call'], 3)
        self.assertEqual(func.stats['miss'], 2)

        time.sleep(0.2)
        func(1,2,3,a=1,b=2) # called
        func(1,2,3,a=1,b=2) # cached
        func(1,2,4,a=1,b=2) # called

        self.assertEqual(self.called, 4)
        self.assertEqual(func.stats['call'], 6)
        self.assertEqual(func.stats['miss'], 4)

    def test_option__disable_kw(self):
        self.called = 0

        @memoize(disable_kw=True)
        def func(*args, **kwargs):
            self.called += 1
            return True

        func(1, 2, 3, a = 1, b = 2) # Called
        func(1, 2, 3, a = 2, b = 3) # Cached
        func(1, 2, 4, a = 3, b = 4) # Cached
        func(1, 2, 3, a = 4, b = 5) # Cached

        self.assertEqual(self.called, 2)
        self.assertEqual(func.stats['call'], 4)
        self.assertEqual(func.stats['miss'], 2)

    def test_option__ignore_nulls(self):
        @memoize(ignore_nulls = True)
        def func(*args, **kwargs):
            return args[0]

        func(1)
        func(1)
        func(2)
        func(None)

        self.assertEqual(func.stats['call'], 4)
        self.assertEqual(func.stats['miss'], 3)

    def test_option__max_bytes(self):
        try:
            sys.getsizeof(5)
        except TypeError:
            self.skipTest("Unsupported in pypy")

        payload_size = sys.getsizeof("abc")

        # We can concurrently store two calls, but not 3
        @memoize(max_bytes = payload_size * 3-1, verbose=True)
        def func(*args, **kwargs):
            return "".join([ 'a', 'b', 'c' ])

        func(1) # LRU=1
        self.assertEqual(func.cache.current_size / payload_size, 1)
        self.assertEqual(func.stats['miss'], 1)

        func(1) # LRU=1
        self.assertEqual(func.cache.current_size / payload_size, 1)
        self.assertEqual(func.stats['miss'], 1)

        func(2) # LRU=2,1
        self.assertEqual(func.cache.current_size / payload_size, 2)
        self.assertEqual(func.stats['miss'], 2)

        func(2) # LRU=2,1
        self.assertEqual(func.cache.current_size / payload_size, 2)
        self.assertEqual(func.stats['miss'], 2)

        func(3) # LRU=3,2
        self.assertEqual(func.cache.current_size / payload_size, 2)
        self.assertEqual(func.stats['miss'], 3)

        func(1) # LRU=3,1
        self.assertEqual(func.cache.current_size / payload_size, 2)
        self.assertEqual(func.stats['miss'], 4)

    def test_option__max_size(self):
        @memoize(max_size = 2)
        def func(*args, **kwargs):
            return True

        func(1) # LRU=1
        self.assertEqual(len(func.cache), 1)
        self.assertEqual(func.stats['miss'], 1)

        func(1) # LRU=1
        self.assertEqual(len(func.cache), 1)
        self.assertEqual(func.stats['miss'], 1)

        func(2) # LRU=2,1
        self.assertEqual(len(func.cache), 2)
        self.assertEqual(func.stats['miss'], 2)

        func(2) # LRU=2,1
        self.assertEqual(len(func.cache), 2)
        self.assertEqual(func.stats['miss'], 2)

        func(3) # LRU=3,2
        self.assertEqual(len(func.cache), 2)
        self.assertEqual(func.stats['miss'], 3)

        func(1) # LRU=3,1
        self.assertEqual(len(func.cache), 2)
        self.assertEqual(func.stats['miss'], 4)

    def test_option__obj(self):
        class F(object):
            @memoize(obj=True)
            def f(self, *args, **kwargs):
                pass

            @classmethod
            @memoize(obj=True)
            def g(self, *args, **kwargs):
                pass

        F.g(1)
        F.g(1)
        F.g(2)

        self.assertEqual(F.g.stats['miss'], 2)

        f1 = F()
        f2 = F()

        f1.f(1)
        f1.f(1)
        f1.f(2)
        f2.f(1)
        self.assertEqual(F.f.stats['miss'], 3)

        f1.__memoize_cache__.clear()
        f1.f(1)

        self.assertEqual(F.f.stats['miss'], 4)

    def test_option__threads(self):
        start = time.time()

        class T(threading.Thread):
            def run(self):
                self.f()

            @memoize(threads=True)
            def f(*args, **kwargs):
                time.sleep(.25)

        threads = [ T() for _ in range(3) ]
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertTrue(time.time() - start > .75)

    def test_option__disabled(self):
        @memoize(disabled = True)
        def func(*args, **kwargs):
            return True

        self.assertTrue(not hasattr(func, 'cache'))
        self.assertTrue(not hasattr(func, 'stats'))

    def test_option__verbose(self):
        # This test intentionally empty because verbose is primarily useful
        # for debugging purposes and breaking it will be ~obvious~.
        pass

    def test_all_options_have_tests(self):
        for k, v in six.iteritems(wizzat.decorators.memoize_default_options):
            self.assertTrue(
                hasattr(self, 'test_option__{}'.format(k)),
                "Test for {} does not exist".format(k)
            )

    def gen_options(self, **kw):
        for k in kw:
            if k not in self.options:
                raise ValueError(k)

        if len(kw) == len(self.options):
            yield kw
        else:
            for k, v in sorted(six.iteritems(self.options)):
                if k in kw:
                    continue

                for opt_value in v:
                    kw[k] = opt_value
                    for option in self.gen_options(**kw):
                        yield option
                break

    def test_compiles_for_all_options(self):
        class F(object):
            pass
        f=F()

        for option in self.gen_options():
            @memoize(**option)
            def func(*args, **kwargs):
                return range(3)

            if not option['obj']:
                func()
            func(f, 2, 3, a = 1, b = 2)
            func(f, 2, 3, a = 1, b = 3)
            func(f, 2, 4, a = 1, b = 2)
            if option['until']:
                time.sleep(0.2)
            func(f, 2, 3, a = 1, b = 3)

    def test_memoize_results(self):
        @memoize()
        def func(*args, **kwargs):
            return True

        self.assertNotEqual(MemoizeResults.format_csv(), None)
        self.assertNotEqual(MemoizeResults.format_stats(), None)
